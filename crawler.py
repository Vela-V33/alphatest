#!/usr/bin/env python3
"""
AlphaTest - App Crawler
Discovers app structure, pages, forms, and suggests test specifications.
"""

import asyncio
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, Browser
import anthropic


class AppCrawler:
    """Crawls a web app to discover its structure and suggest tests."""
    
    def __init__(self, api_key: str, status_callback: Callable = None):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.status = status_callback or print
        
        # Discovered data
        self.pages = []
        self.forms = []
        self.navigation = []
        self.features = []
        self.app_context = ""
    
    async def initialize(self):
        """Start browser."""
        self.status("Starting browser...")
        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(headless=True)
        self.page = await self.browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
    
    async def login(self, login_url: str, email: str, password: str) -> bool:
        """Attempt to log in."""
        self.status("Logging in...")
        try:
            await self.page.goto(login_url, wait_until='networkidle')
            
            # Try common selectors
            email_selectors = [
                "input[type='email']", "input[name='email']", 
                "input[name='username']", "#email", "#username"
            ]
            password_selectors = [
                "input[type='password']", "input[name='password']", "#password"
            ]
            submit_selectors = [
                "button[type='submit']", "input[type='submit']",
                "button:has-text('Log in')", "button:has-text('Sign in')"
            ]
            
            # Fill email
            for sel in email_selectors:
                try:
                    await self.page.fill(sel, email, timeout=2000)
                    break
                except:
                    continue
            
            # Fill password
            for sel in password_selectors:
                try:
                    await self.page.fill(sel, password, timeout=2000)
                    break
                except:
                    continue
            
            # Submit
            for sel in submit_selectors:
                try:
                    await self.page.click(sel, timeout=2000)
                    break
                except:
                    continue
            
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            if 'login' not in self.page.url.lower():
                self.status("✓ Logged in successfully")
                return True
            
            self.status("⚠ Login may have failed")
            return False
            
        except Exception as e:
            self.status(f"Login error: {e}")
            return False
    
    async def discover_page(self, url: str = None) -> Dict:
        """Analyze current page and discover elements."""
        if url:
            await self.page.goto(url, wait_until='networkidle')
        
        page_url = self.page.url
        title = await self.page.title()
        
        # Extract all interactive elements
        elements = await self.page.evaluate("""
            () => {
                const results = {
                    links: [],
                    buttons: [],
                    forms: [],
                    inputs: [],
                    navigation: [],
                    headings: []
                };
                
                // Links
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    const text = a.innerText.trim().slice(0, 100);
                    if (href && !href.startsWith('javascript:') && !href.startsWith('#')) {
                        results.links.push({ href, text });
                    }
                });
                
                // Buttons
                document.querySelectorAll('button, [role="button"], input[type="submit"]').forEach(btn => {
                    results.buttons.push({
                        text: (btn.innerText || btn.value || '').trim().slice(0, 100),
                        type: btn.type || 'button',
                        id: btn.id,
                        name: btn.name
                    });
                });
                
                // Forms
                document.querySelectorAll('form').forEach(form => {
                    const fields = [];
                    form.querySelectorAll('input, select, textarea').forEach(input => {
                        fields.push({
                            type: input.type || input.tagName.toLowerCase(),
                            name: input.name,
                            id: input.id,
                            placeholder: input.placeholder,
                            required: input.required
                        });
                    });
                    results.forms.push({
                        action: form.action,
                        method: form.method,
                        fields: fields
                    });
                });
                
                // Standalone inputs
                document.querySelectorAll('input:not(form input), select:not(form select), textarea:not(form textarea)').forEach(input => {
                    results.inputs.push({
                        type: input.type || input.tagName.toLowerCase(),
                        name: input.name,
                        id: input.id,
                        placeholder: input.placeholder
                    });
                });
                
                // Navigation elements
                document.querySelectorAll('nav, [role="navigation"], .nav, .menu, .sidebar').forEach(nav => {
                    const items = [];
                    nav.querySelectorAll('a').forEach(a => {
                        items.push({ text: a.innerText.trim().slice(0, 50), href: a.href });
                    });
                    if (items.length > 0) {
                        results.navigation.push({ items });
                    }
                });
                
                // Headings for context
                document.querySelectorAll('h1, h2, h3').forEach(h => {
                    results.headings.push(h.innerText.trim().slice(0, 100));
                });
                
                return results;
            }
        """)
        
        return {
            'url': page_url,
            'title': title,
            'elements': elements
        }
    
    async def crawl(self, url: str, login_url: str = None, email: str = None, password: str = None) -> Dict:
        """Crawl the entire app and discover structure."""
        await self.initialize()
        
        base_domain = urlparse(url).netloc
        visited = set()
        to_visit = [url]
        discovered_pages = []
        
        # Login first if credentials provided
        if email and password:
            login = login_url or url
            await self.login(login, email, password)
            to_visit = [url]  # Start fresh after login
        else:
            await self.page.goto(url, wait_until='networkidle')
        
        # Crawl pages (limit to 10 for speed)
        self.status("Discovering app structure...")
        max_pages = 10
        
        while to_visit and len(discovered_pages) < max_pages:
            current_url = to_visit.pop(0)
            
            # Normalize URL
            parsed = urlparse(current_url)
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            if normalized in visited:
                continue
            
            # Only visit same domain
            if parsed.netloc != base_domain:
                continue
            
            visited.add(normalized)
            self.status(f"Analyzing: {parsed.path or '/'}")
            
            try:
                page_data = await self.discover_page(current_url)
                discovered_pages.append(page_data)
                
                # Add new links to visit
                for link in page_data['elements'].get('links', []):
                    href = link.get('href', '')
                    if href and urlparse(href).netloc == base_domain:
                        if href not in visited:
                            to_visit.append(href)
                
            except Exception as e:
                self.status(f"Error on {current_url}: {e}")
                continue
        
        self.status(f"Discovered {len(discovered_pages)} pages")
        
        # Analyze with AI to understand context and suggest tests
        self.status("Analyzing app with AI...")
        analysis = await self.analyze_with_ai(discovered_pages, url)
        
        return {
            'pages': discovered_pages,
            'analysis': analysis,
            'app_type': analysis.get('app_type', 'Unknown'),
            'app_description': analysis.get('description', ''),
            'features': analysis.get('features', []),
            'suggested_tests': analysis.get('suggested_tests', []),
            'sitemap': self.build_sitemap(discovered_pages),
            'crawled_at': datetime.now().isoformat()
        }
    
    async def analyze_with_ai(self, pages: List[Dict], base_url: str) -> Dict:
        """Use AI to analyze the app and suggest tests."""
        
        # Prepare summary for AI
        summary = {
            'base_url': base_url,
            'pages': []
        }
        
        for page in pages[:10]:
            summary['pages'].append({
                'url': page['url'],
                'title': page['title'],
                'headings': page['elements'].get('headings', [])[:5],
                'forms': len(page['elements'].get('forms', [])),
                'buttons': [b['text'] for b in page['elements'].get('buttons', [])][:10],
                'nav_items': [item['text'] for nav in page['elements'].get('navigation', []) for item in nav.get('items', [])][:15]
            })
        
        prompt = f"""Analyze this web application and provide:
1. What type of app is this (e.g., CRM, ERP, E-commerce, etc.)
2. Brief description of what the app does
3. Main features/modules discovered
4. Suggested test specifications

APP STRUCTURE:
{json.dumps(summary, indent=2)}

Return JSON only:
{{
    "app_type": "Type of application",
    "description": "Brief description of what this app does",
    "features": [
        {{"name": "Feature name", "description": "What it does", "pages": ["related pages"]}}
    ],
    "suggested_tests": [
        {{
            "id": "test-1",
            "name": "Test Name",
            "category": "Category (e.g., Authentication, CRUD, Navigation)",
            "description": "What to test in natural language",
            "priority": "high/medium/low",
            "enabled": true
        }}
    ]
}}

Generate 5-10 comprehensive test specifications covering:
- Authentication (login/logout)
- Main CRUD operations
- Navigation between sections
- Form validations
- Key workflows"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = response.content[0].text
            
            # Parse JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
            
        except Exception as e:
            self.status(f"AI analysis error: {e}")
            return {
                'app_type': 'Unknown',
                'description': 'Could not analyze app',
                'features': [],
                'suggested_tests': [
                    {
                        'id': 'test-1',
                        'name': 'Login Test',
                        'category': 'Authentication',
                        'description': 'Test the login functionality',
                        'priority': 'high',
                        'enabled': True
                    },
                    {
                        'id': 'test-2',
                        'name': 'Navigation Test',
                        'category': 'Navigation',
                        'description': 'Test navigation through main menu items',
                        'priority': 'high',
                        'enabled': True
                    }
                ]
            }
    
    def build_sitemap(self, pages: List[Dict]) -> List[Dict]:
        """Build a simple sitemap from discovered pages."""
        sitemap = []
        for page in pages:
            parsed = urlparse(page['url'])
            sitemap.append({
                'path': parsed.path or '/',
                'title': page['title'],
                'forms': len(page['elements'].get('forms', [])),
                'buttons': len(page['elements'].get('buttons', []))
            })
        return sitemap


# Test the crawler directly
if __name__ == "__main__":
    import sys
    
    async def test():
        crawler = AppCrawler(
            api_key="your-api-key",
            status_callback=print
        )
        result = await crawler.crawl(
            url=sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
        )
        print(json.dumps(result, indent=2))
        await crawler.close()
    
    asyncio.run(test())
