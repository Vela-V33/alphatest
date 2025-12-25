#!/usr/bin/env python3
"""
AlphaTest v2 - Improved Test Agent
- Better screenshot capture linked to steps
- Improved dropdown/select handling
- Acceptance criteria support
- Visual verification
"""

import asyncio
import json
import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from playwright.async_api import async_playwright, Page, Browser
import anthropic


class AlphaTestAgent:
    """AI agent that performs browser-based testing with improved reliability."""
    
    def __init__(
        self, 
        api_key: str, 
        status_callback: Callable = None,
        screenshot_callback: Callable = None
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.status = status_callback or print
        self.on_screenshot = screenshot_callback or (lambda x: None)
        
        # Test data
        self.screenshots = []
        self.issues = []
        self.suggestions = []
        self.results = []
        self.steps = []
        self.step_count = 0
        self.session_dir = None
        self.current_test = None

        # Performance and error tracking
        self.console_logs = []
        self.console_errors = []
        self.network_errors = []
        self.performance_metrics = []
        self.page_timings = {}
    
    async def initialize(self, session_dir: Path = None):
        """Start browser and prepare session."""
        self.status("🚀 Starting browser...")
        pw = await async_playwright().start()

        # Launch with args optimized for headless screenshot capture
        self.browser = await pw.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--force-device-scale-factor=1',
                '--window-size=1920,1080',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-extensions',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--force-color-profile=srgb'
            ]
        )

        # Create context with settings optimized for rendering
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
            locale='en-US',
            timezone_id='America/New_York',
            color_scheme='light',
            reduced_motion='no-preference',
            forced_colors='none',
            java_script_enabled=True,
            bypass_csp=True
        )

        self.page = await context.new_page()

        # Setup console and error listeners
        self.page.on("console", lambda msg: self._handle_console(msg))
        self.page.on("pageerror", lambda err: self._handle_page_error(err))
        self.page.on("requestfailed", lambda req: self._handle_network_error(req))

        # Setup session directory
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            self.session_dir = Path("./reports") / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        (self.session_dir / "screenshots").mkdir(parents=True, exist_ok=True)
        self.status("✓ Browser ready!")
    
    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()

    def _handle_console(self, msg):
        """Capture console messages."""
        log_entry = {
            'type': msg.type,
            'text': msg.text,
            'timestamp': datetime.now().isoformat(),
            'url': msg.location.get('url', '') if msg.location else ''
        }
        self.console_logs.append(log_entry)

        if msg.type in ['error', 'warning']:
            self.console_errors.append(log_entry)
            if msg.type == 'error':
                self.status(f"   ⚠️ Console Error: {msg.text}")

    def _handle_page_error(self, error):
        """Capture page errors."""
        error_entry = {
            'message': str(error),
            'timestamp': datetime.now().isoformat()
        }
        self.console_errors.append(error_entry)
        self.status(f"   ❌ Page Error: {error}")

    def _handle_network_error(self, request):
        """Capture failed network requests."""
        error_entry = {
            'url': request.url,
            'method': request.method,
            'failure': request.failure,
            'timestamp': datetime.now().isoformat()
        }
        self.network_errors.append(error_entry)
        self.status(f"   🌐 Network Error: {request.method} {request.url}")

    async def capture_performance_metrics(self) -> Dict:
        """Capture current page performance metrics."""
        try:
            metrics = await self.page.evaluate('''() => {
                const perf = window.performance;
                const timing = perf.timing;
                const navigation = perf.getEntriesByType('navigation')[0];

                return {
                    loadTime: timing.loadEventEnd - timing.navigationStart,
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    timeToInteractive: navigation ? navigation.domInteractive : 0,
                    resourceCount: perf.getEntriesByType('resource').length,
                    url: window.location.href
                };
            }''')
            metrics['timestamp'] = datetime.now().isoformat()
            self.performance_metrics.append(metrics)
            return metrics
        except:
            return {}

    async def wait_for_stable(self, timeout: int = 5000):
        """Wait for page to be stable (no loading, animations complete)."""
        try:
            # Wait for DOM to be loaded first
            await self.page.wait_for_load_state('domcontentloaded', timeout=timeout)
        except:
            pass

        try:
            # Wait for network to be idle
            await self.page.wait_for_load_state('networkidle', timeout=timeout)
        except:
            pass

        # Additional wait for any animations and rendering
        await asyncio.sleep(0.5)

        # Check for common loading indicators and wait for them to disappear
        loading_selectors = [
            '.loading', '.spinner', '[class*="loading"]', '[class*="spinner"]',
            '.sk-spinner', '.loader', '[aria-busy="true"]'
        ]
        for selector in loading_selectors:
            try:
                await self.page.wait_for_selector(selector, state='hidden', timeout=1000)
            except:
                pass
    
    async def screenshot(self, name: str, step_data: Dict = None) -> str:
        """Take and save screenshot with proper linking to step."""
        self.step_count += 1

        try:
            # CRITICAL: Wait for page to be fully loaded
            await self.page.wait_for_load_state('load', timeout=30000)
            await self.page.wait_for_load_state('domcontentloaded', timeout=30000)
            await self.page.wait_for_load_state('networkidle', timeout=30000)
        except Exception as e:
            self.status(f"   ⏳ Page still loading: {e}")

        # Wait for body to exist and be visible
        try:
            await self.page.wait_for_selector('body', state='visible', timeout=10000)
        except:
            self.status("   ⚠️ Body not found, page may be blank")

        # Verify page has actual content
        try:
            has_content = await self.page.evaluate('''
                () => {
                    const body = document.body;
                    if (!body) return false;
                    const text = body.innerText || '';
                    const hasText = text.trim().length > 10;
                    const hasElements = document.querySelectorAll('div, p, span, img').length > 0;
                    return hasText || hasElements;
                }
            ''')

            if not has_content:
                self.status("   ⚠️ Page appears to be blank or loading")
                # Extra wait if page seems empty
                await asyncio.sleep(3)
        except:
            pass

        # Wait for fonts
        try:
            await self.page.evaluate('() => document.fonts.ready')
        except:
            pass

        # Wait for all images
        try:
            await self.page.evaluate('''
                () => {
                    const images = Array.from(document.images);
                    return Promise.all(
                        images.filter(img => !img.complete).map(img =>
                            new Promise(resolve => {
                                img.onload = img.onerror = () => resolve();
                                setTimeout(resolve, 5000); // Timeout after 5s
                            })
                        )
                    );
                }
            ''')
        except:
            pass

        # Scroll page to force rendering
        try:
            await self.page.evaluate('''
                () => {
                    window.scrollTo(0, document.body.scrollHeight / 2);
                }
            ''')
            await asyncio.sleep(0.5)
            await self.page.evaluate('() => window.scrollTo(0, 0)')
        except:
            pass

        # CRITICAL: Long wait for rendering
        await asyncio.sleep(3)

        # Force repaints
        try:
            await self.page.evaluate('''
                () => {
                    // Force multiple reflows
                    for (let i = 0; i < 3; i++) {
                        document.body.offsetHeight;
                        document.body.style.transform = 'translateZ(0)';
                        document.body.offsetHeight;
                        document.body.style.transform = '';
                    }
                }
            ''')
        except:
            pass

        await asyncio.sleep(1)

        # Generate filename
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:40]
        filename = f"{self.step_count:03d}_{safe_name}.png"
        filepath = self.session_dir / "screenshots" / filename

        try:
            # Take screenshot
            await self.page.screenshot(
                path=str(filepath),
                full_page=True,  # Full page to ensure we capture everything
                type='png'
            )

            # Verify file
            if filepath.exists():
                file_size = filepath.stat().st_size
                self.status(f"   📸 Screenshot: {name} ({file_size} bytes)")

                if file_size < 1000:
                    self.status(f"   ⚠️ Screenshot file is very small, may be blank")

                screenshot_data = {
                    'step': self.step_count,
                    'name': name,
                    'filename': filename,
                    'path': str(filepath),
                    'timestamp': datetime.now().isoformat(),
                    'url': self.page.url,
                    'step_data': step_data,
                    'file_size': file_size
                }
                self.screenshots.append(screenshot_data)
                self.on_screenshot(str(filepath))
                return str(filepath)
            else:
                self.status(f"   ⚠️ Screenshot file not created")

        except Exception as e:
            self.status(f"   ⚠️ Screenshot failed: {e}")

        return ""

    async def generate_acceptance_criteria(self, test_command: str, context: str = "") -> List[str]:
        """Generate natural language acceptance criteria from a test command using AI."""
        self.status("🤔 Generating acceptance criteria...")

        prompt = f"""Given this test command: "{test_command}"

Context: {context if context else "A web application"}

Generate 3-5 clear, natural language acceptance criteria that define what success looks like for this test.

Format as a simple list, one per line, like:
- New asset is created successfully
- Asset appears in the asset list
- Asset details are saved correctly

Keep criteria:
- Simple and actionable
- User-focused (not technical)
- Verifiable through the UI
- Specific to the test command

Criteria:"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            criteria_text = response.content[0].text.strip()

            # Parse the criteria
            criteria = []
            for line in criteria_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                    criterion = line.lstrip('-•* ').strip()
                    if criterion:
                        criteria.append(criterion)
                elif line and not line.endswith(':'):
                    # Handle lines without bullet points
                    criteria.append(line)

            self.status(f"   ✓ Generated {len(criteria)} acceptance criteria")
            return criteria[:5]  # Limit to 5 criteria

        except Exception as e:
            self.status(f"   ⚠️ Failed to generate criteria: {e}")
            # Return default criteria
            return [
                "Test completes without errors",
                "Expected elements are visible",
                "Actions produce expected results"
            ]

    async def login(self, login_url: str, email: str, password: str) -> bool:
        """Perform login with better element detection."""
        self.status("🔐 Logging in...")
        
        try:
            await self.page.goto(login_url, wait_until='networkidle', timeout=30000)
            await self.wait_for_stable()
            await self.screenshot("01_login_page")
            
            # Try multiple email selectors
            email_filled = False
            email_selectors = [
                "input[type='email']",
                "input[name='email']",
                "input[name='username']",
                "input[id='email']",
                "input[id='username']",
                "input[placeholder*='email' i]",
                "input[placeholder*='user' i]",
                "input[autocomplete='email']",
                "input[autocomplete='username']"
            ]
            
            for sel in email_selectors:
                try:
                    elem = await self.page.wait_for_selector(sel, timeout=2000, state='visible')
                    if elem:
                        await elem.fill(email)
                        email_filled = True
                        self.status(f"   ✓ Email entered using: {sel}")
                        break
                except:
                    continue
            
            if not email_filled:
                self.status("   ⚠️ Could not find email field")
                return False
            
            # Try multiple password selectors
            password_filled = False
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input[id='password']",
                "input[placeholder*='password' i]",
                "input[autocomplete='current-password']"
            ]
            
            for sel in password_selectors:
                try:
                    elem = await self.page.wait_for_selector(sel, timeout=2000, state='visible')
                    if elem:
                        await elem.fill(password)
                        password_filled = True
                        self.status(f"   ✓ Password entered using: {sel}")
                        break
                except:
                    continue
            
            if not password_filled:
                self.status("   ⚠️ Could not find password field")
                return False
            
            await self.screenshot("02_credentials_entered")
            
            # Find and click submit
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Log in')",
                "button:has-text('Login')",
                "button:has-text('Sign in')",
                "button:has-text('Submit')",
                "form button",
                ".login-button",
                "#login-button"
            ]
            
            for sel in submit_selectors:
                try:
                    elem = await self.page.wait_for_selector(sel, timeout=2000, state='visible')
                    if elem:
                        await elem.click()
                        self.status(f"   ✓ Clicked submit: {sel}")
                        break
                except:
                    continue
            
            # Wait for navigation
            await self.wait_for_stable(5000)
            await asyncio.sleep(2)
            await self.screenshot("03_after_login")
            
            # Check if login succeeded
            current_url = self.page.url.lower()
            if 'login' not in current_url and 'signin' not in current_url:
                self.status("✓ Login successful!")
                return True
            
            self.status("⚠️ May still be on login page")
            return False
            
        except Exception as e:
            self.status(f"❌ Login error: {e}")
            self.issues.append({
                'type': 'login_error',
                'message': str(e),
                'severity': 'critical'
            })
            return False
    
    async def get_page_context(self) -> Dict:
        """Get current page state for AI with detailed element info."""
        await self.wait_for_stable()
        
        # Take screenshot for AI
        screenshot_bytes = await self.page.screenshot(full_page=False)
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        # Get detailed element information
        elements = await self.page.evaluate("""
            () => {
                const results = [];
                const interactable = document.querySelectorAll(
                    'button, a, input, select, textarea, [role="button"], [role="link"], ' +
                    '[role="menuitem"], [role="option"], [onclick], [tabindex="0"], ' +
                    '.btn, .button, [class*="dropdown"], [class*="select"]'
                );
                
                let idx = 0;
                interactable.forEach((el) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && idx < 60) {
                        const isVisible = rect.top < window.innerHeight && rect.bottom > 0;
                        if (isVisible) {
                            // Get the best selector for this element
                            let selector = '';
                            if (el.id) selector = '#' + el.id;
                            else if (el.name) selector = '[name="' + el.name + '"]';
                            else if (el.className && typeof el.className === 'string') {
                                const mainClass = el.className.split(' ')[0];
                                if (mainClass) selector = '.' + mainClass;
                            }
                            
                            // For selects, get options
                            let options = [];
                            if (el.tagName === 'SELECT') {
                                Array.from(el.options).slice(0, 10).forEach(opt => {
                                    options.push({ value: opt.value, text: opt.text.slice(0, 50) });
                                });
                            }
                            
                            results.push({
                                index: idx,
                                tag: el.tagName.toLowerCase(),
                                type: el.type || el.getAttribute('role') || '',
                                text: (el.innerText || el.value || el.placeholder || 
                                       el.getAttribute('aria-label') || el.title || '').slice(0, 100).trim(),
                                id: el.id || '',
                                name: el.name || '',
                                selector: selector,
                                classes: (el.className || '').toString().slice(0, 100),
                                options: options,
                                rect: { x: Math.round(rect.x), y: Math.round(rect.y), 
                                       w: Math.round(rect.width), h: Math.round(rect.height) }
                            });
                            idx++;
                        }
                    }
                });
                
                return results;
            }
        """)
        
        return {
            'url': self.page.url,
            'title': await self.page.title(),
            'screenshot_b64': screenshot_b64,
            'elements': elements
        }
    
    async def handle_dropdown(self, selector: str, value: str) -> Dict:
        """Handle dropdown/select with multiple strategies."""
        result = {'success': False, 'message': ''}
        
        # Strategy 1: Native select
        try:
            await self.page.select_option(selector, value=value, timeout=3000)
            result = {'success': True, 'message': f'Selected "{value}" from dropdown'}
            return result
        except:
            pass
        
        # Strategy 2: Select by label
        try:
            await self.page.select_option(selector, label=value, timeout=3000)
            result = {'success': True, 'message': f'Selected "{value}" by label'}
            return result
        except:
            pass
        
        # Strategy 3: Click to open, then select option
        try:
            await self.page.click(selector, timeout=3000)
            await asyncio.sleep(0.5)
            
            # Look for option in opened dropdown
            option_selectors = [
                f"text={value}",
                f"[role='option']:has-text('{value}')",
                f".option:has-text('{value}')",
                f"li:has-text('{value}')",
                f"[data-value='{value}']"
            ]
            
            for opt_sel in option_selectors:
                try:
                    await self.page.click(opt_sel, timeout=2000)
                    result = {'success': True, 'message': f'Clicked option "{value}"'}
                    return result
                except:
                    continue
        except:
            pass
        
        # Strategy 4: Keyboard navigation
        try:
            await self.page.click(selector, timeout=3000)
            await asyncio.sleep(0.3)
            # Type to search/filter
            await self.page.keyboard.type(value[:10])
            await asyncio.sleep(0.3)
            await self.page.keyboard.press('Enter')
            result = {'success': True, 'message': f'Selected "{value}" via keyboard'}
            return result
        except:
            pass
        
        result = {'success': False, 'message': f'Could not select "{value}" from dropdown'}
        self.issues.append({
            'type': 'dropdown_error',
            'message': f'Failed to select "{value}" from {selector}',
            'severity': 'medium'
        })
        return result
    
    async def find_element_robust(self, selector: str, text_hint: str = None) -> any:
        """Find element using multiple strategies with fallbacks."""
        strategies = []

        # Strategy 1: Direct selector
        if selector:
            strategies.append(selector)

        # Strategy 2: Text-based selectors
        if text_hint:
            strategies.extend([
                f"text='{text_hint}'",
                f"button:has-text('{text_hint}')",
                f"a:has-text('{text_hint}')",
                f"[role='button']:has-text('{text_hint}')",
                f"*:has-text('{text_hint}')"
            ])

        # Try each strategy
        for sel in strategies:
            try:
                elem = await self.page.wait_for_selector(sel, timeout=3000, state='visible')
                if elem:
                    return elem
            except:
                continue

        return None

    async def click_with_retry(self, selector: str, text_hint: str = None, max_retries: int = 3) -> Dict:
        """Click element with retry logic and multiple strategies."""
        result = {'success': False, 'message': ''}

        for attempt in range(max_retries):
            try:
                elem = await self.find_element_robust(selector, text_hint)

                if not elem:
                    # Try clicking by coordinates as last resort
                    if selector:
                        try:
                            await self.page.click(selector, timeout=5000, force=True)
                            result = {'success': True, 'message': f'Clicked (forced): {selector}'}
                            return result
                        except:
                            pass
                    continue

                # Scroll into view
                await elem.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)

                # Check if element is enabled and not obscured
                is_enabled = await elem.is_enabled()
                is_visible = await elem.is_visible()

                if not is_enabled or not is_visible:
                    await asyncio.sleep(0.5)

                # Try regular click first
                try:
                    await elem.click(timeout=5000)
                    result = {'success': True, 'message': f'Clicked: {selector}'}
                    return result
                except:
                    # Try force click
                    await elem.click(force=True)
                    result = {'success': True, 'message': f'Clicked (forced): {selector}'}
                    return result

            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                else:
                    result = {'success': False, 'message': f'Click failed after {max_retries} attempts: {str(e)}'}

        return result

    async def execute_action(self, action: Dict) -> Dict:
        """Execute a single action with improved reliability and retry logic."""
        action_type = action.get('type', 'unknown')
        selector = action.get('selector', '')
        text_hint = action.get('text_hint', action.get('text', ''))
        result = {'success': False, 'message': '', 'action': action}

        try:
            if action_type == 'click':
                # Use robust click with retry
                result = await self.click_with_retry(selector, text_hint)
                result['action'] = action

            elif action_type == 'type':
                text = action.get('text', '')
                elem = await self.find_element_robust(selector)
                if elem:
                    await elem.scroll_into_view_if_needed()
                    await asyncio.sleep(0.2)
                    # Clear and type with proper handling
                    try:
                        await elem.fill('')
                        await elem.fill(text)
                    except:
                        # Fallback: click and type
                        await elem.click()
                        await self.page.keyboard.type(text)
                    result = {'success': True, 'message': f'Typed "{text[:30]}..." into {selector}', 'action': action}
                else:
                    result = {'success': False, 'message': f'Element not found: {selector}', 'action': action}

            elif action_type == 'select':
                value = action.get('value', '')
                result = await self.handle_dropdown(selector, value)
                result['action'] = action

            elif action_type == 'navigate':
                url = action.get('url', '')
                try:
                    await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
                except:
                    # Fallback - just try to navigate
                    await self.page.goto(url, timeout=30000)
                result = {'success': True, 'message': f'Navigated to: {url}', 'action': action}

            elif action_type == 'wait':
                duration = action.get('duration', 1000)
                await asyncio.sleep(min(duration / 1000, 5))  # Max 5 second wait
                result = {'success': True, 'message': f'Waited {duration}ms', 'action': action}

            elif action_type == 'scroll':
                direction = action.get('direction', 'down')
                amount = 400 if direction == 'down' else -400
                await self.page.evaluate(f'window.scrollBy(0, {amount})')
                result = {'success': True, 'message': f'Scrolled {direction}', 'action': action}

            elif action_type == 'press':
                key = action.get('key', 'Enter')
                await self.page.keyboard.press(key)
                result = {'success': True, 'message': f'Pressed: {key}', 'action': action}

            elif action_type == 'hover':
                elem = await self.find_element_robust(selector, text_hint)
                if elem:
                    await elem.hover()
                    result = {'success': True, 'message': f'Hovered: {selector}', 'action': action}
                else:
                    result = {'success': False, 'message': f'Element not found: {selector}', 'action': action}

            elif action_type == 'back':
                await self.page.go_back()
                result = {'success': True, 'message': 'Navigated back', 'action': action}

        except Exception as e:
            result = {'success': False, 'message': str(e), 'action': action}
            self.issues.append({
                'type': 'action_error',
                'message': f'{action_type} failed on {selector}: {str(e)}',
                'severity': 'medium'
            })

        # Wait for any resulting changes
        await self.wait_for_stable()
        return result
    
    async def check_acceptance_criteria(self, criteria: List[Dict]) -> Dict:
        """Check if acceptance criteria are met."""
        results = {'passed': True, 'checks': []}
        
        for criterion in criteria:
            check_type = criterion.get('type', '')
            check = {'criterion': criterion, 'passed': False, 'message': ''}
            
            try:
                if check_type == 'url_contains':
                    expected = criterion.get('value', '')
                    actual = self.page.url
                    check['passed'] = expected.lower() in actual.lower()
                    check['message'] = f"URL {'contains' if check['passed'] else 'does not contain'} '{expected}'"
                    
                elif check_type == 'element_visible':
                    selector = criterion.get('selector', '')
                    elem = await self.page.wait_for_selector(selector, timeout=3000, state='visible')
                    check['passed'] = elem is not None
                    check['message'] = f"Element {selector} {'is' if check['passed'] else 'is not'} visible"
                    
                elif check_type == 'text_visible':
                    text = criterion.get('value', '')
                    content = await self.page.content()
                    check['passed'] = text.lower() in content.lower()
                    check['message'] = f"Text '{text}' {'found' if check['passed'] else 'not found'} on page"
                    
                elif check_type == 'element_count':
                    selector = criterion.get('selector', '')
                    expected = criterion.get('value', 1)
                    elements = await self.page.query_selector_all(selector)
                    check['passed'] = len(elements) >= expected
                    check['message'] = f"Found {len(elements)} elements (expected >= {expected})"
                    
            except Exception as e:
                check['passed'] = False
                check['message'] = f"Check failed: {str(e)}"
            
            results['checks'].append(check)
            if not check['passed']:
                results['passed'] = False
        
        return results
    
    async def analyze_and_decide(self, task: str, acceptance_criteria: List[Dict] = None) -> Dict:
        """Use AI to decide next action with acceptance criteria awareness."""
        context = await self.get_page_context()
        
        # Build criteria string
        criteria_str = ""
        if acceptance_criteria:
            criteria_str = "\n\nACCEPTANCE CRITERIA (test is complete when ALL are met):\n"
            for c in acceptance_criteria:
                criteria_str += f"- {c.get('description', c)}\n"
        
        system_prompt = """You are AlphaTest, an expert AI testing agent for web applications.

Your job:
1. Look at the current page screenshot and available elements
2. Decide what action to take to complete the user's task
3. Check if acceptance criteria are met
4. Report ONLY issues you actually observe on THIS page

CRITICAL RULES FOR RELIABLE ACTIONS:
1. PREFER these selector types (in order):
   - ID selectors: #loginBtn, #submitForm
   - Name attributes: [name="email"], [name="password"]
   - Unique classes: .submit-button, .primary-btn
   - Text content: button:has-text('Submit'), a:has-text('Login')

2. AVOID vague selectors like: button, input, .btn (too generic)

3. For BUTTONS and LINKS:
   - Include text_hint with the visible button text
   - Example: {"type": "click", "selector": "#submit", "text_hint": "Submit"}

4. For DROPDOWNS/SELECTS:
   - Native select: use type="select" with value
   - Custom dropdown: first click to open, then click option text

5. NAVIGATION TIPS:
   - If stuck, try scrolling down to find more elements
   - If a click doesn't work, try a different selector for same element
   - Look for menu items, sidebar links, navigation bars

6. ONLY report issues you can SEE in the current screenshot
7. When task is complete OR acceptance criteria met, set completed=true

Return ONLY valid JSON:
{
    "thinking": "What I see on screen and my specific plan",
    "action": {
        "type": "click|type|select|navigate|wait|scroll|press|hover|back|done",
        "selector": "Specific CSS selector from elements list",
        "text": "text to type (for type action)",
        "text_hint": "visible button/link text (helps find element)",
        "value": "value to select (for select action)",
        "key": "key name (for press action)",
        "direction": "up|down (for scroll action)"
    },
    "observed_issues": ["Only real issues I can see right now"],
    "criteria_status": "Which acceptance criteria appear to be met",
    "completed": false
}"""

        # Filter elements to most relevant
        elements_summary = []
        for el in context['elements'][:40]:
            el_str = f"[{el['index']}] {el['tag']}"
            if el['type']:
                el_str += f" type={el['type']}"
            if el['id']:
                el_str += f" #{el['id']}"
            if el['name']:
                el_str += f" name={el['name']}"
            if el['text']:
                el_str += f" \"{el['text'][:50]}\""
            if el['options']:
                el_str += f" options={[o['text'] for o in el['options'][:5]]}"
            elements_summary.append(el_str)

        user_message = f"""TASK: {task}
{criteria_str}

CURRENT PAGE: {context['url']}
TITLE: {context['title']}

AVAILABLE ELEMENTS:
{chr(10).join(elements_summary)}

Based on the screenshot and elements, what's the next action?"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": context['screenshot_b64']}},
                        {"type": "text", "text": user_message}
                    ]
                }],
                system=system_prompt
            )
            
            text = response.content[0].text
            
            # Parse JSON
            try:
                # Clean up response
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                result = json.loads(text.strip())
            except:
                result = {
                    "thinking": text[:200],
                    "action": {"type": "wait", "duration": 1000},
                    "observed_issues": [],
                    "completed": False
                }
            
            # Only add issues that were actually observed
            if result.get('observed_issues'):
                for issue in result['observed_issues']:
                    if issue and len(issue) > 5:  # Filter out empty/tiny issues
                        self.issues.append({
                            'type': 'observed_issue',
                            'message': issue,
                            'url': context['url'],
                            'severity': 'medium'
                        })
            
            return result
            
        except Exception as e:
            self.status(f"   ⚠️ AI error: {e}")
            return {
                "thinking": f"Error: {str(e)}",
                "action": {"type": "wait", "duration": 2000},
                "observed_issues": [],
                "completed": False
            }
    
    async def run_command(
        self, 
        command: str, 
        max_steps: int = 15,
        acceptance_criteria: List[Dict] = None
    ) -> Dict:
        """Run a natural language test command with acceptance criteria."""
        self.status(f"🧪 Testing: {command}")
        self.current_test = command
        
        result = {
            'command': command,
            'status': 'running',
            'steps': [],
            'acceptance_criteria': acceptance_criteria or [],
            'start_time': datetime.now().isoformat()
        }
        
        # Take initial screenshot
        await self.screenshot("test_start", {'phase': 'start', 'command': command})
        
        for step_num in range(max_steps):
            step_data = {
                'step': step_num + 1,
                'timestamp': datetime.now().isoformat()
            }
            
            self.status(f"📍 Step {step_num + 1}: Analyzing...")
            
            # Get AI decision
            analysis = await self.analyze_and_decide(command, acceptance_criteria)
            thinking = analysis.get('thinking', '')
            action = analysis.get('action', {})
            
            step_data['thinking'] = thinking
            step_data['action'] = action
            
            self.status(f"   💭 {thinking[:70]}...")
            
            # Check if complete
            if analysis.get('completed', False) or action.get('type') == 'done':
                self.status("✅ Test completed!")
                result['status'] = 'passed'
                
                # Take completion screenshot
                await self.screenshot("test_complete", {'phase': 'complete', 'result': 'passed'})
                
                # Verify acceptance criteria if provided
                if acceptance_criteria:
                    criteria_result = await self.check_acceptance_criteria(acceptance_criteria)
                    step_data['criteria_result'] = criteria_result
                    if not criteria_result['passed']:
                        result['status'] = 'failed'
                        self.status("⚠️ Some acceptance criteria not met")
                
                step_data['result'] = {'success': True, 'message': 'Task completed'}
                result['steps'].append(step_data)
                break
            
            # Execute action
            if action.get('type') and action['type'] not in ['done', 'unknown']:
                # Screenshot before action
                before_shot = await self.screenshot(
                    f"step_{step_num + 1}_before", 
                    {'phase': 'before', 'action': action}
                )
                step_data['screenshot_before'] = before_shot
                
                # Execute
                action_result = await self.execute_action(action)
                step_data['result'] = action_result
                
                if action_result['success']:
                    self.status(f"   ✓ {action_result['message']}")
                else:
                    self.status(f"   ✗ {action_result['message']}")
                
                # Screenshot after action
                await asyncio.sleep(0.5)
                after_shot = await self.screenshot(
                    f"step_{step_num + 1}_after",
                    {'phase': 'after', 'action': action, 'result': action_result}
                )
                step_data['screenshot_after'] = after_shot
            
            result['steps'].append(step_data)
        
        else:
            result['status'] = 'incomplete'
            self.status("⚠️ Max steps reached - test incomplete")
            await self.screenshot("test_incomplete", {'phase': 'incomplete'})
        
        result['end_time'] = datetime.now().isoformat()
        result['issues_found'] = len(self.issues)
        self.results.append(result)
        
        return result
    
    def get_report_data(self) -> Dict:
        """Get all data for report generation."""
        return {
            'results': self.results,
            'issues': self.issues,
            'screenshots': self.screenshots,
            'steps': self.steps,
            'console_logs': self.console_logs,
            'console_errors': self.console_errors,
            'network_errors': self.network_errors,
            'performance_metrics': self.performance_metrics,
            'session_dir': str(self.session_dir) if self.session_dir else None,
            'generated_at': datetime.now().isoformat()
        }


# Direct usage for testing
if __name__ == "__main__":
    import sys
    
    async def test():
        agent = AlphaTestAgent(
            api_key="your-api-key",
            status_callback=print
        )
        await agent.initialize()
        
        url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
        await agent.page.goto(url)
        
        command = sys.argv[2] if len(sys.argv) > 2 else "Explore this page"
        
        # Example acceptance criteria
        criteria = [
            {'type': 'url_contains', 'value': 'success', 'description': 'URL contains "success"'},
            {'type': 'text_visible', 'value': 'saved', 'description': 'Page shows "saved" message'}
        ]
        
        result = await agent.run_command(command, acceptance_criteria=criteria)
        print(json.dumps(result, indent=2))
        await agent.close()
    
    asyncio.run(test())
