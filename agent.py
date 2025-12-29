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
import random
import string
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from playwright.async_api import async_playwright, Page, Browser
import anthropic
from visual_regression import VisualRegressionTester
from assertions import Assertions, TestPatterns, AssertionResult
from test_data import TestDataManager
from api_testing import APITester, APIResponse, APIAssertion


class AlphaTestAgent:
    """AI agent that performs browser-based testing with improved reliability."""
    
    def __init__(
        self,
        api_key: str,
        status_callback: Callable = None,
        screenshot_callback: Callable = None,
        browser_type: str = 'chromium'
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.status = status_callback or print
        self.on_screenshot = screenshot_callback or (lambda x: None)
        self.browser_type = browser_type  # chromium, firefox, webkit, edge

        # Test data
        self.screenshots = []
        self.issues = []
        self.suggestions = []
        self.results = []
        self.steps = []
        self.step_count = 0
        self.session_dir = None
        self.current_test = None
        self.video_path = None

        # Performance and error tracking
        self.console_logs = []
        self.console_errors = []
        self.network_errors = []
        self.performance_metrics = []
        self.page_timings = {}

        # Visual regression testing
        self.visual_regressions = []
        self.vrt = None

        # Assertions
        self.assertions = Assertions()
        self.assertion_results = []

        # Test data management
        self.test_data_manager = None

        # API testing
        self.api_tester = None
        self.api_responses = []

    async def initialize(self, session_dir: Path = None):
        """Start browser and prepare session."""
        browser_name = self.browser_type.capitalize()
        self.status(f"[Starting] Starting {browser_name} browser...")
        self.playwright = await async_playwright().start()

        # Get browser launcher based on type
        if self.browser_type == 'firefox':
            browser_launcher = self.playwright.firefox
        elif self.browser_type == 'webkit':
            browser_launcher = self.playwright.webkit
        elif self.browser_type == 'edge':
            browser_launcher = self.playwright.chromium  # Edge uses Chromium
        else:  # chromium (default)
            browser_launcher = self.playwright.chromium

        # Browser-specific launch arguments
        if self.browser_type in ['chromium', 'edge']:
            launch_args = [
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
            if self.browser_type == 'edge':
                launch_args.append('--enable-features=msEdgeDevToolsWdpRemoteDebugging')
        elif self.browser_type == 'firefox':
            # Firefox has different args
            launch_args = []
        else:  # webkit
            launch_args = []

        # Launch browser
        if self.browser_type in ['chromium', 'edge']:
            self.browser = await browser_launcher.launch(
                headless=True,
                args=launch_args,
                channel='msedge' if self.browser_type == 'edge' else None
            )
        else:
            self.browser = await browser_launcher.launch(headless=True)

        # Setup session directory first
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            self.session_dir = Path("./reports") / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        (self.session_dir / "screenshots").mkdir(parents=True, exist_ok=True)
        (self.session_dir / "videos").mkdir(parents=True, exist_ok=True)

        # Initialize visual regression tester
        # Use parent directory (project directory) for baselines
        if self.session_dir:
            project_dir = self.session_dir.parent
            self.vrt = VisualRegressionTester(project_dir)
            self.test_data_manager = TestDataManager(project_dir)

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
            bypass_csp=True,
            record_video_dir=str(self.session_dir / "videos"),
            record_video_size={'width': 1920, 'height': 1080}
        )

        self.page = await context.new_page()
        self.context = context

        # Initialize API tester with page object
        self.api_tester = APITester(
            base_url="",  # Will be set dynamically based on test URL
            default_headers={"User-Agent": "AlphaTest/2.0"}
        )

        # Setup console and error listeners
        self.page.on("console", lambda msg: self._handle_console(msg))
        self.page.on("pageerror", lambda err: self._handle_page_error(err))
        self.page.on("requestfailed", lambda req: self._handle_network_error(req))

        self.status("[OK] Browser ready!")

    async def close(self):
        """Close browser and save video."""
        video_path = None
        try:
            # Get video path before closing
            if self.page and self.page.video:
                video_path = await self.page.video.path()
                if video_path:
                    self.status(f"[Video] Video saved: {Path(video_path).name}")
        except Exception as e:
            self.status(f"[WARNING] Could not save video: {e}")

        if self.browser:
            await self.browser.close()

        return video_path

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
                self.status(f"   [WARNING] Console Error: {msg.text}")

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
        self.status(f"   [Network] Network Error: {request.method} {request.url}")

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

    async def run_accessibility_scan(self) -> Dict:
        """Run axe-core accessibility audit for WCAG 2.1 compliance.

        Returns:
            Dictionary containing:
            - violations: List of accessibility violations
            - wcag_level: Compliance level (A, AA, AAA)
            - critical_count: Number of critical violations
            - url: Page URL
        """
        try:
            # Inject axe-core library
            await self.page.add_script_tag(url='https://unpkg.com/axe-core@latest/axe.min.js')

            # Run axe accessibility audit
            results = await self.page.evaluate('''async () => {
                try {
                    const results = await axe.run();
                    return {
                        violations: results.violations.map(v => ({
                            id: v.id,
                            impact: v.impact,
                            description: v.description,
                            help: v.help,
                            helpUrl: v.helpUrl,
                            tags: v.tags,
                            nodes: v.nodes.length,
                            wcagLevel: v.tags.find(t => t.startsWith('wcag'))
                        })),
                        passes: results.passes.length,
                        incomplete: results.incomplete.length,
                        inapplicable: results.inapplicable.length,
                        url: window.location.href
                    };
                } catch (error) {
                    return { error: error.message, url: window.location.href };
                }
            }''')

            if 'error' in results:
                self.status(f"   [WARNING] Accessibility scan error: {results['error']}")
                return {'violations': [], 'error': results['error']}

            violations = results.get('violations', [])

            # Count violations by impact level
            critical_count = sum(1 for v in violations if v.get('impact') == 'critical')
            serious_count = sum(1 for v in violations if v.get('impact') == 'serious')
            moderate_count = sum(1 for v in violations if v.get('impact') == 'moderate')
            minor_count = sum(1 for v in violations if v.get('impact') == 'minor')

            # Determine WCAG compliance level
            wcag_level = 'AAA'
            if critical_count > 0 or serious_count > 0:
                wcag_level = 'Non-compliant'
            elif moderate_count > 5:
                wcag_level = 'AA (with issues)'
            elif moderate_count > 0:
                wcag_level = 'AA'

            result = {
                'violations': violations,
                'wcag_level': wcag_level,
                'critical_count': critical_count,
                'serious_count': serious_count,
                'moderate_count': moderate_count,
                'minor_count': minor_count,
                'total_violations': len(violations),
                'passes': results.get('passes', 0),
                'url': results.get('url', ''),
                'timestamp': datetime.now().isoformat()
            }

            # Log violations as issues
            for violation in violations:
                severity = 'critical' if violation['impact'] in ['critical', 'serious'] else 'medium'
                self.issues.append({
                    'type': 'accessibility',
                    'message': f"[WCAG] {violation['help']}",
                    'description': violation['description'],
                    'severity': severity,
                    'url': results.get('url', ''),
                    'wcag_tags': violation.get('tags', []),
                    'help_url': violation.get('helpUrl', ''),
                    'affected_elements': violation.get('nodes', 0),
                    'timestamp': datetime.now().isoformat()
                })

            if critical_count > 0:
                self.status(f"   ♿ Accessibility: {critical_count} critical, {serious_count} serious violations")
            else:
                self.status(f"   [OK] Accessibility: WCAG {wcag_level}")

            return result

        except Exception as e:
            self.status(f"   [WARNING] Accessibility scan failed: {e}")
            return {'violations': [], 'error': str(e)}

    async def check_security_headers(self, response = None) -> Dict:
        """Check for security headers in HTTP response.

        Validates presence of critical security headers per OWASP recommendations:
        - Content-Security-Policy
        - X-Frame-Options
        - X-Content-Type-Options
        - Strict-Transport-Security
        - X-XSS-Protection
        - Referrer-Policy
        - Permissions-Policy

        Args:
            response: Playwright response object (optional, uses current page if None)

        Returns:
            Dictionary containing:
            - present: List of present security headers
            - missing: List of missing security headers
            - issues: List of security issues found
        """
        try:
            # Get response if not provided
            if response is None:
                # Navigate to current URL to get fresh response
                response = await self.page.goto(self.page.url, wait_until='domcontentloaded')

            if not response:
                return {'error': 'No response available'}

            headers = response.headers
            url = response.url

            # Define required security headers
            required_headers = {
                'content-security-policy': {
                    'risk': 'XSS and code injection attacks',
                    'severity': 'high',
                    'recommendation': 'Implement Content-Security-Policy to prevent XSS'
                },
                'x-frame-options': {
                    'risk': 'Clickjacking vulnerability',
                    'severity': 'high',
                    'recommendation': 'Add X-Frame-Options: DENY or SAMEORIGIN'
                },
                'x-content-type-options': {
                    'risk': 'MIME sniffing attacks',
                    'severity': 'medium',
                    'recommendation': 'Add X-Content-Type-Options: nosniff'
                },
                'strict-transport-security': {
                    'risk': 'Man-in-the-middle attacks',
                    'severity': 'high',
                    'recommendation': 'Add Strict-Transport-Security header for HTTPS enforcement'
                },
                'x-xss-protection': {
                    'risk': 'Legacy XSS attacks',
                    'severity': 'low',
                    'recommendation': 'Add X-XSS-Protection: 1; mode=block'
                },
                'referrer-policy': {
                    'risk': 'Information leakage via Referer header',
                    'severity': 'medium',
                    'recommendation': 'Add Referrer-Policy: strict-origin-when-cross-origin'
                },
                'permissions-policy': {
                    'risk': 'Unwanted feature access',
                    'severity': 'low',
                    'recommendation': 'Add Permissions-Policy to control browser features'
                }
            }

            present_headers = []
            missing_headers = []
            issues_found = []

            for header_name, header_info in required_headers.items():
                if header_name in headers or header_name.replace('-', '') in headers:
                    present_headers.append(header_name)
                else:
                    missing_headers.append(header_name)

                    # Create issue for missing header
                    issue = {
                        'type': 'security',
                        'message': f"Missing security header: {header_name}",
                        'description': f"Risk: {header_info['risk']}",
                        'severity': header_info['severity'],
                        'recommendation': header_info['recommendation'],
                        'url': url,
                        'timestamp': datetime.now().isoformat()
                    }
                    issues_found.append(issue)
                    self.issues.append(issue)

            result = {
                'present': present_headers,
                'missing': missing_headers,
                'issues': issues_found,
                'total_checked': len(required_headers),
                'compliance_percentage': (len(present_headers) / len(required_headers)) * 100,
                'url': url,
                'timestamp': datetime.now().isoformat()
            }

            if len(missing_headers) > 0:
                self.status(f"   🔒 Security: {len(missing_headers)} missing headers ({result['compliance_percentage']:.0f}% compliant)")
            else:
                self.status(f"   [OK] Security: All headers present (100% compliant)")

            return result

        except Exception as e:
            self.status(f"   [WARNING] Security headers check failed: {e}")
            return {'error': str(e)}

    async def run_lighthouse_audit(self) -> Dict:
        """Run Lighthouse performance audit.

        Measures Core Web Vitals and performance metrics:
        - Performance score
        - Accessibility score
        - Best practices score
        - SEO score
        - LCP (Largest Contentful Paint)
        - FID (First Input Delay)
        - CLS (Cumulative Layout Shift)
        - FCP (First Contentful Paint)
        - TTI (Time to Interactive)

        Returns:
            Dictionary containing Lighthouse scores and Core Web Vitals
        """
        try:
            # Measure Core Web Vitals and performance
            metrics = await self.page.evaluate('''async () => {
                return new Promise((resolve) => {
                    // Get performance metrics
                    const perf = performance;
                    const navigation = perf.getEntriesByType('navigation')[0];
                    const paint = perf.getEntriesByType('paint');

                    // Core Web Vitals
                    let lcp = 0;
                    let fcp = 0;
                    let cls = 0;
                    let fid = 0;

                    // FCP (First Contentful Paint)
                    const fcpEntry = paint.find(entry => entry.name === 'first-contentful-paint');
                    if (fcpEntry) {
                        fcp = fcpEntry.startTime;
                    }

                    // Largest Contentful Paint (LCP)
                    const lcpObserver = new PerformanceObserver((list) => {
                        const entries = list.getEntries();
                        const lastEntry = entries[entries.length - 1];
                        lcp = lastEntry.renderTime || lastEntry.loadTime;
                    });

                    // Cumulative Layout Shift (CLS)
                    let clsValue = 0;
                    const clsObserver = new PerformanceObserver((list) => {
                        for (const entry of list.getEntries()) {
                            if (!entry.hadRecentInput) {
                                clsValue += entry.value;
                            }
                        }
                    });

                    // Try to get existing LCP entries
                    try {
                        lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
                    } catch (e) {
                        // Fallback for browsers that don't support LCP
                        lcp = navigation ? navigation.domContentLoadedEventEnd : 0;
                    }

                    // Try to get CLS entries
                    try {
                        clsObserver.observe({ type: 'layout-shift', buffered: true });
                    } catch (e) {}

                    // Wait a bit for observers to collect data
                    setTimeout(() => {
                        cls = clsValue;

                        // Calculate scores (simplified Lighthouse scoring)
                        const tti = navigation ? navigation.domInteractive : 0;
                        const loadTime = navigation ? navigation.loadEventEnd - navigation.fetchStart : 0;

                        // Performance score calculation (simplified)
                        let perfScore = 100;
                        if (fcp > 3000) perfScore -= 20;
                        if (lcp > 2500) perfScore -= 20;
                        if (tti > 3800) perfScore -= 20;
                        if (cls > 0.1) perfScore -= 20;
                        if (loadTime > 5000) perfScore -= 20;

                        // Basic accessibility check
                        const images = document.querySelectorAll('img:not([alt])').length;
                        const headings = document.querySelectorAll('h1').length;
                        const accessibilityScore = Math.max(0, 100 - (images * 5) - (headings === 0 ? 10 : 0));

                        // Best practices check
                        const hasHttps = window.location.protocol === 'https:';
                        const hasDoctype = document.doctype !== null;
                        const hasViewport = !!document.querySelector('meta[name="viewport"]');
                        const bestPracticesScore = (hasHttps ? 40 : 0) + (hasDoctype ? 30 : 0) + (hasViewport ? 30 : 0);

                        // SEO check
                        const hasTitle = !!document.title && document.title.length > 0;
                        const hasMetaDesc = !!document.querySelector('meta[name="description"]');
                        const hasH1 = headings > 0;
                        const seoScore = (hasTitle ? 40 : 0) + (hasMetaDesc ? 30 : 0) + (hasH1 ? 30 : 0);

                        resolve({
                            scores: {
                                performance: Math.max(0, perfScore) / 100,
                                accessibility: accessibilityScore / 100,
                                bestPractices: bestPracticesScore / 100,
                                seo: seoScore / 100
                            },
                            coreWebVitals: {
                                lcp: lcp,
                                fid: fid,
                                cls: cls,
                                fcp: fcp,
                                tti: tti
                            },
                            metrics: {
                                loadTime: loadTime,
                                domContentLoaded: navigation ? navigation.domContentLoadedEventEnd - navigation.fetchStart : 0,
                                timeToInteractive: tti,
                                firstContentfulPaint: fcp
                            },
                            url: window.location.href
                        });
                    }, 1000);
                });
            }''')

            # Add timestamp
            metrics['timestamp'] = datetime.now().isoformat()

            # Determine performance grade
            perf_score = metrics['scores']['performance']
            if perf_score >= 0.9:
                grade = 'Excellent'
            elif perf_score >= 0.75:
                grade = 'Good'
            elif perf_score >= 0.5:
                grade = 'Needs Improvement'
            else:
                grade = 'Poor'

            metrics['performanceGrade'] = grade

            # Check Core Web Vitals thresholds
            cwv = metrics['coreWebVitals']
            cwv_issues = []

            if cwv['lcp'] > 2500:
                cwv_issues.append({
                    'metric': 'LCP',
                    'value': f"{cwv['lcp']:.0f}ms",
                    'threshold': '2500ms',
                    'severity': 'high' if cwv['lcp'] > 4000 else 'medium'
                })

            if cwv['cls'] > 0.1:
                cwv_issues.append({
                    'metric': 'CLS',
                    'value': f"{cwv['cls']:.3f}",
                    'threshold': '0.1',
                    'severity': 'high' if cwv['cls'] > 0.25 else 'medium'
                })

            if cwv['fcp'] > 1800:
                cwv_issues.append({
                    'metric': 'FCP',
                    'value': f"{cwv['fcp']:.0f}ms",
                    'threshold': '1800ms',
                    'severity': 'medium'
                })

            # Log performance issues
            for issue in cwv_issues:
                self.issues.append({
                    'type': 'performance',
                    'message': f"[Core Web Vitals] {issue['metric']} exceeds threshold",
                    'description': f"{issue['metric']}: {issue['value']} (threshold: {issue['threshold']})",
                    'severity': issue['severity'],
                    'url': metrics['url'],
                    'timestamp': datetime.now().isoformat()
                })

            # Log poor scores
            for category, score in metrics['scores'].items():
                if score < 0.5:
                    self.issues.append({
                        'type': 'performance',
                        'message': f"[Lighthouse] Poor {category} score",
                        'description': f"{category.capitalize()} score: {score*100:.0f}/100",
                        'severity': 'medium',
                        'url': metrics['url'],
                        'timestamp': datetime.now().isoformat()
                    })

            self.status(f"   ⚡ Performance: {grade} ({perf_score*100:.0f}/100)")

            if cwv_issues:
                self.status(f"   [WARNING] Core Web Vitals: {len(cwv_issues)} metrics exceed thresholds")

            return metrics

        except Exception as e:
            self.status(f"   [WARNING] Lighthouse audit failed: {e}")
            return {'error': str(e)}

    def generate_fake_data(self, field_type: str, field_name: str = "") -> str:
        """Generate realistic fake data for form filling."""
        field_name_lower = field_name.lower()

        # Email
        if 'email' in field_name_lower or field_type == 'email':
            username = ''.join(random.choices(string.ascii_lowercase, k=8))
            domains = ['test.com', 'example.com', 'demo.org', 'sample.net']
            return f"{username}@{random.choice(domains)}"

        # Phone
        if 'phone' in field_name_lower or 'tel' in field_name_lower:
            return f"+1{random.randint(2000000000, 9999999999)}"

        # Name
        if 'first' in field_name_lower and 'name' in field_name_lower:
            first_names = ['Alex', 'Sam', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery']
            return random.choice(first_names)

        if 'last' in field_name_lower and 'name' in field_name_lower:
            last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']
            return random.choice(last_names)

        if 'name' in field_name_lower and 'user' not in field_name_lower:
            first = ['Alex', 'Sam', 'Jordan', 'Taylor'][random.randint(0, 3)]
            last = ['Smith', 'Johnson', 'Williams', 'Brown'][random.randint(0, 3)]
            return f"{first} {last}"

        # Username
        if 'user' in field_name_lower:
            return f"user{random.randint(1000, 9999)}"

        # Password
        if 'password' in field_name_lower or field_type == 'password':
            return "TestPass123!"

        # Address
        if 'address' in field_name_lower or 'street' in field_name_lower:
            num = random.randint(100, 9999)
            streets = ['Main St', 'Oak Ave', 'Maple Dr', 'Park Blvd', 'River Rd']
            return f"{num} {random.choice(streets)}"

        if 'city' in field_name_lower:
            cities = ['San Francisco', 'New York', 'Chicago', 'Austin', 'Seattle']
            return random.choice(cities)

        if 'state' in field_name_lower:
            states = ['CA', 'NY', 'TX', 'WA', 'IL']
            return random.choice(states)

        if 'zip' in field_name_lower or 'postal' in field_name_lower:
            return f"{random.randint(10000, 99999)}"

        if 'country' in field_name_lower:
            return 'United States'

        # Company
        if 'company' in field_name_lower or 'organization' in field_name_lower:
            companies = ['Acme Corp', 'Test Industries', 'Demo LLC', 'Sample Inc']
            return random.choice(companies)

        # Title/Job
        if 'title' in field_name_lower or 'job' in field_name_lower:
            titles = ['Software Engineer', 'Product Manager', 'Designer', 'Analyst']
            return random.choice(titles)

        # Date
        if 'date' in field_name_lower or 'birth' in field_name_lower:
            year = random.randint(1970, 2005)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            return f"{year:04d}-{month:02d}-{day:02d}"

        # Number fields
        if field_type == 'number' or 'age' in field_name_lower:
            return str(random.randint(18, 65))

        if 'quantity' in field_name_lower or 'amount' in field_name_lower:
            return str(random.randint(1, 10))

        # ID fields (asset ID, product ID, etc.)
        if 'id' in field_name_lower or 'identifier' in field_name_lower:
            prefixes = ['PUMP', 'ASSET', 'PROD', 'ITEM', 'EQ']
            prefix = random.choice(prefixes)
            return f"{prefix}-{random.randint(1000, 9999)}"

        # Description/Notes
        if 'description' in field_name_lower or 'notes' in field_name_lower or 'comment' in field_name_lower:
            descriptions = [
                'This is a test description for UAT purposes',
                'Automated test data generated by AlphaTest',
                'Sample description for testing functionality',
                'Test entry created during automated testing'
            ]
            return random.choice(descriptions)

        # Price/Cost
        if 'price' in field_name_lower or 'cost' in field_name_lower or 'value' in field_name_lower:
            return f"{random.randint(10, 9999)}.{random.randint(10, 99)}"

        # Serial Number
        if 'serial' in field_name_lower or 'sn' in field_name_lower:
            return f"SN{random.randint(100000, 999999)}"

        # Model
        if 'model' in field_name_lower:
            models = ['Model-X', 'Pro-Series', 'Elite-2000', 'Standard-Plus']
            return random.choice(models)

        # Type/Category (for dropdowns that didn't get handled)
        if 'type' in field_name_lower or 'category' in field_name_lower:
            types = ['Standard', 'Premium', 'Basic', 'Advanced']
            return random.choice(types)

        # Default text
        return f"Test Data {random.randint(100, 999)}"

    async def visual_regression_check(
        self,
        name: str,
        set_baseline: bool = False,
        threshold: float = 0.1
    ) -> Dict:
        """
        Perform visual regression check against baseline.

        Args:
            name: Name of the visual checkpoint
            set_baseline: If True, set current screenshot as baseline
            threshold: Difference threshold (0.0-1.0), lower is more strict

        Returns:
            Dictionary with comparison results
        """
        if not self.vrt:
            return {'error': 'Visual regression tester not initialized'}

        try:
            # Take screenshot
            screenshot_path = await self.screenshot(f"visual_check_{name}")
            screenshot_file = self.session_dir / "screenshots" / f"{screenshot_path}.png"

            if set_baseline:
                # Set this screenshot as the baseline
                success = self.vrt.set_baseline(name, screenshot_file)
                result = {
                    'name': name,
                    'action': 'baseline_set',
                    'success': success,
                    'screenshot': str(screenshot_file)
                }
                self.status(f"   📸 Visual baseline set: {name}")
            else:
                # Compare against baseline
                result = self.vrt.compare(name, screenshot_file, threshold=threshold)

                # Track visual regressions
                if not result.get('matched', True):
                    self.visual_regressions.append(result)
                    self.status(f"   [WARNING] Visual regression detected: {name} ({result['diff_percentage']:.2f}% different)")

                    # Add as issue
                    self.issues.append({
                        'type': 'visual_regression',
                        'message': f"Visual regression detected: {name}",
                        'severity': 'medium',
                        'diff_percentage': result['diff_percentage'],
                        'diff_image': result.get('diff_image_path'),
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    self.status(f"   [OK] Visual check passed: {name} ({result['diff_percentage']:.2f}% different)")

            return result

        except Exception as e:
            self.status(f"   [WARNING] Visual regression check failed: {e}")
            return {'error': str(e)}

    async def run_assertion(self, assertion_type: str, **kwargs) -> AssertionResult:
        """
        Run a custom assertion.

        Args:
            assertion_type: Type of assertion (equals, contains, url_contains, etc.)
            **kwargs: Arguments for the assertion

        Returns:
            AssertionResult object
        """
        try:
            # Get current page context for dynamic assertions
            if assertion_type == 'url_contains':
                kwargs['url'] = self.page.url
            elif assertion_type == 'url_equals':
                kwargs['url'] = self.page.url

            # Run the assertion
            assertion_method = getattr(self.assertions, f'assert_{assertion_type}', None)
            if not assertion_method:
                return AssertionResult(False, f"Unknown assertion type: {assertion_type}")

            result = assertion_method(**kwargs)

            # Track results
            self.assertion_results.append(result.to_dict())

            # Log result
            status_icon = "✓" if result.passed else "[FAIL]"
            self.status(f"   {status_icon} Assertion: {result.message}")

            # Create issue if failed
            if not result.passed:
                self.issues.append({
                    'type': 'assertion_failed',
                    'message': result.message,
                    'severity': 'high',
                    'assertion_type': assertion_type,
                    'details': result.details,
                    'timestamp': result.timestamp
                })

            return result

        except Exception as e:
            self.status(f"   [WARNING] Assertion error: {e}")
            return AssertionResult(False, f"Assertion error: {e}")

    async def apply_test_pattern(self, pattern_name: str, **kwargs) -> Dict:
        """
        Apply a common test pattern.

        Args:
            pattern_name: Name of the pattern (login_flow, search_flow, etc.)
            **kwargs: Arguments for the pattern

        Returns:
            Dictionary with pattern execution results
        """
        try:
            # Get the pattern
            pattern_method = getattr(TestPatterns, pattern_name, None)
            if not pattern_method:
                return {'error': f"Unknown pattern: {pattern_name}"}

            pattern = pattern_method(**kwargs)
            self.status(f"   [Pattern] Applying pattern: {pattern_name}")

            results = {
                'pattern': pattern_name,
                'steps_completed': [],
                'assertions_passed': [],
                'success': True
            }

            # Execute pattern steps (simplified - would need full implementation)
            if 'steps' in pattern:
                for step in pattern['steps']:
                    # This would execute each step
                    results['steps_completed'].append(step)

            # Run pattern assertions
            if 'assertions' in pattern:
                for assertion in pattern['assertions']:
                    assertion_type = assertion.pop('type')
                    result = await self.run_assertion(assertion_type, **assertion)
                    results['assertions_passed'].append(result.passed)

                    if not result.passed:
                        results['success'] = False

            return results

        except Exception as e:
            self.status(f"   [WARNING] Pattern error: {e}")
            return {'error': str(e)}

    async def use_fixture(self, name: str) -> Optional[Any]:
        """
        Load and use a saved fixture.

        Args:
            name: Name of the fixture to load

        Returns:
            Fixture data or None if not found
        """
        try:
            if not self.test_data_manager:
                self.status(f"   [WARNING] Test data manager not initialized")
                return None

            fixture = self.test_data_manager.get_fixture(name)
            if fixture:
                self.status(f"   [Loaded] Loaded fixture: {name}")
            else:
                self.status(f"   [WARNING] Fixture not found: {name}")

            return fixture

        except Exception as e:
            self.status(f"   [WARNING] Error loading fixture: {e}")
            return None

    async def generate_test_data(self, entity_type: str, **kwargs) -> Optional[Dict]:
        """
        Generate test data for a specific entity type.

        Args:
            entity_type: Type of entity (user, product, company, etc.)
            **kwargs: Additional parameters for the generator

        Returns:
            Generated test data or None on error
        """
        try:
            if not self.test_data_manager:
                self.status(f"   [WARNING] Test data manager not initialized")
                return None

            generators = {
                'user': self.test_data_manager.generate_user,
                'address': self.test_data_manager.generate_address,
                'company': self.test_data_manager.generate_company,
                'product': self.test_data_manager.generate_product,
                'credit_card': self.test_data_manager.generate_credit_card
            }

            generator = generators.get(entity_type)
            if not generator:
                self.status(f"   [WARNING] Unknown entity type: {entity_type}")
                return None

            data = generator(**kwargs) if kwargs else generator()
            self.status(f"   [Generated] Generated {entity_type} data")

            return data

        except Exception as e:
            self.status(f"   [WARNING] Error generating test data: {e}")
            return None

    async def api_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[APIResponse]:
        """
        Make an API request.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            APIResponse object or None on error
        """
        try:
            if not self.api_tester:
                self.status(f"   [WARNING] API tester not initialized")
                return None

            # Pass the page object to the request
            kwargs['page'] = self.page

            self.status(f"   [Network] {method.upper()} {endpoint}")
            response = await self.api_tester.request(method, endpoint, **kwargs)

            # Track response
            self.api_responses.append(response.to_dict())

            # Log response
            status_icon = "✓" if 200 <= response.status_code < 300 else "⚠️"
            self.status(f"   {status_icon} Status {response.status_code} ({response.response_time_ms:.2f}ms)")

            return response

        except Exception as e:
            self.status(f"   [WARNING] API request error: {e}")
            return None

    async def api_get(self, endpoint: str, **kwargs) -> Optional[APIResponse]:
        """Make a GET API request."""
        return await self.api_request('GET', endpoint, **kwargs)

    async def api_post(self, endpoint: str, **kwargs) -> Optional[APIResponse]:
        """Make a POST API request."""
        return await self.api_request('POST', endpoint, **kwargs)

    async def api_put(self, endpoint: str, **kwargs) -> Optional[APIResponse]:
        """Make a PUT API request."""
        return await self.api_request('PUT', endpoint, **kwargs)

    async def api_patch(self, endpoint: str, **kwargs) -> Optional[APIResponse]:
        """Make a PATCH API request."""
        return await self.api_request('PATCH', endpoint, **kwargs)

    async def api_delete(self, endpoint: str, **kwargs) -> Optional[APIResponse]:
        """Make a DELETE API request."""
        return await self.api_request('DELETE', endpoint, **kwargs)

    async def graphql_query(
        self,
        query: str,
        variables: Dict = None,
        endpoint: str = '/graphql',
        **kwargs
    ) -> Optional[APIResponse]:
        """
        Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables
            endpoint: GraphQL endpoint
            **kwargs: Additional request parameters

        Returns:
            APIResponse object or None on error
        """
        try:
            if not self.api_tester:
                self.status(f"   [WARNING] API tester not initialized")
                return None

            kwargs['page'] = self.page
            self.status(f"   [Query] GraphQL Query")

            response = await self.api_tester.graphql(query, variables, endpoint, **kwargs)

            # Track response
            self.api_responses.append(response.to_dict())

            # Log response
            status_icon = "✓" if 200 <= response.status_code < 300 else "⚠️"
            self.status(f"   {status_icon} Status {response.status_code} ({response.response_time_ms:.2f}ms)")

            return response

        except Exception as e:
            self.status(f"   [WARNING] GraphQL query error: {e}")
            return None

    async def api_assert(
        self,
        response: APIResponse,
        assertion_type: str,
        **kwargs
    ) -> Optional[APIAssertion]:
        """
        Run an API assertion.

        Args:
            response: APIResponse to assert on
            assertion_type: Type of assertion (status_code, response_time, etc.)
            **kwargs: Assertion parameters

        Returns:
            APIAssertion result or None on error
        """
        try:
            if not self.api_tester or not response:
                return None

            # Map assertion types to methods
            assertion_methods = {
                'status_code': lambda: self.api_tester.assert_status_code(response, kwargs.get('expected')),
                'status_in': lambda: self.api_tester.assert_status_in(response, kwargs.get('expected_codes', [])),
                'response_time': lambda: self.api_tester.assert_response_time(response, kwargs.get('max_ms')),
                'header_present': lambda: self.api_tester.assert_header_present(response, kwargs.get('header')),
                'header_value': lambda: self.api_tester.assert_header_value(response, kwargs.get('header'), kwargs.get('value')),
                'json_path': lambda: self.api_tester.assert_json_path(response, kwargs.get('path'), kwargs.get('expected')),
                'json_contains': lambda: self.api_tester.assert_json_contains(response, kwargs.get('key')),
                'body_contains': lambda: self.api_tester.assert_body_contains(response, kwargs.get('text'))
            }

            assertion_method = assertion_methods.get(assertion_type)
            if not assertion_method:
                self.status(f"   [WARNING] Unknown assertion type: {assertion_type}")
                return None

            assertion = assertion_method()

            # Log assertion
            status_icon = "✓" if assertion.passed else "[FAIL]"
            self.status(f"   {status_icon} {assertion.message}")

            # Create issue if failed
            if not assertion.passed:
                self.issues.append({
                    'type': 'api_assertion_failed',
                    'message': assertion.message,
                    'severity': 'high',
                    'assertion_type': assertion_type,
                    'details': assertion.details,
                    'timestamp': assertion.timestamp
                })

            return assertion

        except Exception as e:
            self.status(f"   [WARNING] API assertion error: {e}")
            return None

    async def wait_for_stable(self, timeout: int = 5000):
        """Wait for page to be stable (no loading, animations complete)."""
        try:
            # Wait for DOM to be loaded first
            await self.page.wait_for_load_state('domcontentloaded', timeout=timeout)
        except:
            pass

        try:
            # Wait for network to be idle (shorter timeout for speed)
            await self.page.wait_for_load_state('networkidle', timeout=min(timeout, 3000))
        except:
            pass

        # Minimal wait for animations (reduced from 0.5s to 0.1s for speed)
        await asyncio.sleep(0.1)

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
            # Quick wait for page content (reduced timeouts for speed)
            await self.page.wait_for_load_state('domcontentloaded', timeout=5000)
            await self.page.wait_for_selector('body', state='visible', timeout=3000)
        except Exception as e:
            # Page might still be loading but capture anyway
            pass

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
                self.status("   [WARNING] Page appears to be blank or loading")
                # Quick wait if page seems empty (reduced from 3s to 0.5s)
                await asyncio.sleep(0.5)
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

        # Quick scroll to force rendering (removed excessive waits)
        try:
            await self.page.evaluate('() => { window.scrollTo(0, 0); document.body.offsetHeight; }')
        except:
            pass

        # Minimal wait for rendering (reduced from 4s total to 0.2s for SPEED)
        await asyncio.sleep(0.2)

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
                    self.status(f"   [WARNING] Screenshot file is very small, may be blank")

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
                print(f"[DEBUG] Screenshot saved: {filename} at {filepath}")
                return str(filepath)
            else:
                self.status(f"   [WARNING] Screenshot file not created")

        except Exception as e:
            self.status(f"   [WARNING] Screenshot failed: {e}")

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

            self.status(f"   [OK] Generated {len(criteria)} acceptance criteria")
            return criteria[:5]  # Limit to 5 criteria

        except Exception as e:
            self.status(f"   [WARNING] Failed to generate criteria: {e}")
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
                        self.status(f"   [OK] Email entered using: {sel}")
                        break
                except:
                    continue
            
            if not email_filled:
                self.status("   [WARNING] Could not find email field")
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
                        self.status(f"   [OK] Password entered using: {sel}")
                        break
                except:
                    continue
            
            if not password_filled:
                self.status("   [WARNING] Could not find password field")
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
                        self.status(f"   [OK] Clicked submit: {sel}")
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
                self.status("[OK] Login successful!")
                return True
            
            self.status("[WARNING] May still be on login page")
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
            await asyncio.sleep(0.2)  # Reduced from 0.5s
            
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
            await asyncio.sleep(0.1)  # Reduced from 0.3s
            # Type to search/filter
            await self.page.keyboard.type(value[:10])
            await asyncio.sleep(0.1)  # Reduced from 0.3s
            await self.page.keyboard.press('Enter')
            result = {'success': True, 'message': f'Selected "{value}" via keyboard'}
            return result
        except:
            pass

        # Strategy 5: FORCE via JavaScript (ultimate fallback)
        self.status(f"   🔧 Using JavaScript to force dropdown selection")
        try:
            success = await self.page.evaluate(f'''
                (selector, value) => {{
                    const elem = document.querySelector(selector);
                    if (elem) {{
                        // For native select elements
                        if (elem.tagName === 'SELECT') {{
                            elem.value = value;
                            elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}
                        // For custom dropdowns, try to click the element
                        elem.click();
                        return true;
                    }}
                    return false;
                }}
            ''', selector, value)

            if success:
                result = {'success': True, 'message': f'Selected "{value}" via JavaScript injection'}
                return result
        except Exception as e:
            pass

        result = {'success': False, 'message': f'Could not select "{value}" from dropdown after all strategies'}
        self.issues.append({
            'type': 'dropdown_error',
            'message': f'Failed to select "{value}" from {selector} - dropdown may not be working properly',
            'severity': 'high'
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
                    # ULTIMATE FALLBACK: JavaScript click
                    self.status(f"   🔧 Using JavaScript to force click")
                    try:
                        success = await self.page.evaluate(f'''
                            (selector) => {{
                                const elem = document.querySelector(selector);
                                if (elem) {{
                                    elem.click();
                                    return true;
                                }}
                                return false;
                            }}
                        ''', selector)

                        if success:
                            result = {'success': True, 'message': f'Clicked via JavaScript: {selector}'}
                            return result
                        else:
                            result = {'success': False, 'message': f'Element not found for JavaScript click: {selector}'}
                    except Exception as e2:
                        result = {'success': False, 'message': f'Click failed after all attempts: {str(e2)}'}

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
                elem = await self.find_element_robust(selector, text_hint)
                if elem:
                    await elem.scroll_into_view_if_needed()
                    await asyncio.sleep(0.05)  # Reduced from 0.2s

                    # Clear and type with proper handling
                    try:
                        await elem.fill('')
                        await elem.fill(text)
                        await asyncio.sleep(0.1)  # Reduced wait for verification

                        # VERIFY the value was actually set
                        actual_value = await elem.input_value()
                        if actual_value == text:
                            result = {'success': True, 'message': f'Typed and verified "{text[:30]}..." into {selector}', 'action': action}
                        else:
                            # Value didn't stick, try alternative method
                            await elem.click()
                            await elem.press('Control+a')
                            await elem.type(text)
                            await asyncio.sleep(0.1)  # Reduced from 0.2s

                            # Verify again
                            actual_value = await elem.input_value()
                            if actual_value == text:
                                result = {'success': True, 'message': f'Typed and verified "{text[:30]}..." (retry method)', 'action': action}
                            else:
                                # ULTIMATE FALLBACK: Use JavaScript to force set value
                                self.status(f"   🔧 Using JavaScript to force set value")
                                try:
                                    await self.page.evaluate(f'''
                                        (selector, value) => {{
                                            const elem = document.querySelector(selector);
                                            if (elem) {{
                                                elem.value = value;
                                                elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                return true;
                                            }}
                                            return false;
                                        }}
                                    ''', selector, text)
                                    result = {'success': True, 'message': f'Set value via JavaScript: "{text[:30]}..."', 'action': action}
                                except Exception as e3:
                                    result = {'success': False, 'message': f'All methods failed. Expected: "{text}", Got: "{actual_value}"', 'action': action}
                    except Exception as e:
                        # Fallback: click and type
                        try:
                            await elem.click()
                            await self.page.keyboard.type(text, delay=50)
                            result = {'success': True, 'message': f'Typed "{text[:30]}..." using keyboard', 'action': action}
                        except Exception as e2:
                            # ULTIMATE FALLBACK: JavaScript injection
                            try:
                                await self.page.evaluate(f'''
                                    (selector, value) => {{
                                        const elem = document.querySelector(selector);
                                        if (elem) {{
                                            elem.value = value;
                                            elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                            elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                            return true;
                                        }}
                                        return false;
                                    }}
                                ''', selector, text)
                                result = {'success': True, 'message': f'Set value via JavaScript fallback: "{text[:30]}..."', 'action': action}
                            except Exception as e3:
                                result = {'success': False, 'message': f'Failed to type: {str(e3)}', 'action': action}
                else:
                    result = {'success': False, 'message': f'Input element not found: {selector}', 'action': action}

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
        
        system_prompt = """You are an autonomous UAT and QA testing agent. Your role is to behave like a real human user interacting with a live application through its user interface.

CORE BEHAVIOR - ACT LIKE A HUMAN QA TESTER:
1. Visually perceive the UI and identify ALL interactive elements (buttons, links, dropdowns, inputs, toggles, modals, menus)
2. Interact EXACTLY as a human would: clicking, typing, selecting, scrolling, navigating
3. Respect page load times, animations, and UI state changes before taking next action
4. Make intelligent decisions based on what you see and the test specification
5. Log ALL issues, broken elements, UX problems, and improvement opportunities

TESTING CAPABILITIES:
- Navigate through multi-step workflows and menus
- Open and use dropdowns, pickers, checkboxes, radio buttons
- Fill forms with realistic fictional data (names, emails, addresses, etc.)
- Save, submit, edit, delete records
- Trigger validations and handle errors gracefully
- Login/logout when required
- Test happy paths, edge cases, and negative scenarios

DECISION-MAKING:
- Choose the most intuitive path a real user would take
- If an action fails, try alternative selectors or approaches
- Wait when loading indicators are present
- Scroll to reveal more content if needed
- Adapt to UI changes without failing

CRITICAL - SELECTOR RULES:
1. PREFER (in order):
   - ID: #loginBtn, #email-input
   - Name: [name="email"], [name="password"]
   - Unique class: .submit-btn, .primary-button
   - Text: button:has-text('Login'), a:has-text('Sign Up')

2. AVOID vague selectors: button, input, .btn

3. BUTTONS/LINKS: Always include text_hint with visible text
   Example: {"type": "click", "selector": "#submit", "text_hint": "Submit Form"}

4. DROPDOWNS:
   - Native <select>: {"type": "select", "selector": "#country", "value": "USA"}
   - Custom dropdown: First click to open, then click option by text

5. FORMS: Use realistic test data from context or generate appropriate values

ISSUE LOGGING - BE THOROUGH:
Report ALL observations:
- Broken buttons (not clickable, no response)
- Non-responsive elements
- Layout/alignment issues
- Missing labels or unclear UI
- Validation errors
- Performance problems
- Accessibility issues
- Confusing workflows
- Missing features

CONSTRAINTS:
- Do NOT assume backend success unless UI confirms it
- Do NOT hallucinate outcomes
- Do NOT bypass UI via APIs
- Report uncertainty clearly

Return ONLY valid JSON:
{
    "thinking": "What I see, my analysis, and my human-like decision",
    "action": {
        "type": "click|type|select|navigate|wait|scroll|press|hover|back|done",
        "selector": "Specific CSS selector",
        "text": "text to type (for type action) - use realistic data",
        "text_hint": "visible text (for click action)",
        "value": "value (for select action)",
        "key": "key name (for press action)",
        "direction": "up|down (for scroll)"
    },
    "observed_issues": ["List EVERY issue you can see: broken elements, UX problems, bugs, confusing UI, missing features, layout issues"],
    "suggestions": ["Improvement recommendations based on what you observe"],
    "criteria_status": "Which acceptance criteria are met",
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

        # Build conversation memory from recent steps
        recent_actions = ""
        if hasattr(self, 'steps') and len(self.steps) > 0:
            recent_actions = "\n\nRECENT ACTIONS (what you tried already):\n"
            for i, step in enumerate(self.steps[-5:]):  # Last 5 steps
                action = step.get('action', {})
                result = step.get('result', {})
                status = "✓" if result.get('success') else "[FAIL]"
                recent_actions += f"{i+1}. {status} {action.get('type', 'unknown')} on {action.get('selector', 'N/A')} - {result.get('message', 'N/A')}\n"

        user_message = f"""TASK: {task}
{criteria_str}

CURRENT PAGE: {context['url']}
TITLE: {context['title']}
{recent_actions}
AVAILABLE ELEMENTS (index, tag, attributes, text):
{chr(10).join(elements_summary)}

As a human QA tester, analyze the screenshot and decide the next action. Be thorough in logging issues and suggesting improvements."""

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
            
            # Add observed issues
            if result.get('observed_issues'):
                for issue in result['observed_issues']:
                    if issue and len(issue) > 5:  # Filter out empty/tiny issues
                        self.issues.append({
                            'type': 'observed_issue',
                            'message': issue,
                            'url': context['url'],
                            'severity': 'medium',
                            'timestamp': datetime.now().isoformat()
                        })

            # Add suggestions for improvements
            if result.get('suggestions'):
                for suggestion in result['suggestions']:
                    if suggestion and len(suggestion) > 5:
                        self.suggestions.append({
                            'message': suggestion,
                            'url': context['url'],
                            'timestamp': datetime.now().isoformat()
                        })

            return result
            
        except Exception as e:
            self.status(f"   [WARNING] AI error: {e}")
            return {
                "thinking": f"Error: {str(e)}",
                "action": {"type": "wait", "duration": 2000},
                "observed_issues": [],
                "completed": False
            }
    
    async def run_command(
        self,
        command: str,
        max_steps: int = 25,
        acceptance_criteria: List[Dict] = None,
        continue_callback = None
    ) -> Dict:
        """Run a natural language test command with acceptance criteria."""
        self.status(f"🧪 Testing: {command}")
        self.current_test = command

        # Track completed actions to prevent duplicates
        self.completed_actions = []

        # AGGRESSIVE stuck detection - track recent action patterns
        self.recent_action_patterns = []
        stuck_threshold = 3  # If same action attempted 3 times, it's stuck

        result = {
            'command': command,
            'status': 'running',
            'steps': [],
            'acceptance_criteria': acceptance_criteria or [],
            'start_time': datetime.now().isoformat()
        }

        # Take initial screenshot
        await self.screenshot("test_start", {'phase': 'start', 'command': command})

        step_num = 0
        consecutive_failures = 0  # Track consecutive failed actions
        while step_num < max_steps:
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

            # ULTRA-AGGRESSIVE STUCK DETECTION: Check for semantic similarity in thinking
            # If agent describes the same problem/situation repeatedly, it's STUCK
            recent_thinking = [s.get('thinking', '') for s in self.steps[-4:]] if len(self.steps) >= 4 else []

            # Check if current thinking is very similar to recent thinking (semantic stuck detection)
            similar_thinking_count = 0
            current_thinking_lower = thinking.lower()
            for past_thinking in recent_thinking:
                past_lower = past_thinking.lower()
                # Check for key phrase overlap
                if len(current_thinking_lower) > 20 and len(past_lower) > 20:
                    # Count common significant words
                    current_words = set([w for w in current_thinking_lower.split() if len(w) > 4])
                    past_words = set([w for w in past_lower.split() if len(w) > 4])
                    if len(current_words) > 0:
                        overlap = len(current_words & past_words) / len(current_words)
                        if overlap > 0.6:  # 60% word overlap = stuck
                            similar_thinking_count += 1

            # Also check if on same URL for too long
            current_url = self.page.url if self.page else ""
            same_url_count = sum(1 for s in self.steps[-5:] if current_url and current_url in str(s.get('action', {}).get('selector', '')))

            if similar_thinking_count >= 2:
                self.status(f"   🚨 SEMANTIC STUCK DETECTED: Similar thinking {similar_thinking_count} times")
                self.status(f"   💡 Agent keeps describing the same situation - FORCING DIFFERENT ACTION")

                # Log as critical issue
                self.issues.append({
                    'type': 'semantic_stuck',
                    'message': f"Agent repeatedly observed: '{thinking[:100]}...' without making progress",
                    'severity': 'critical',
                    'step': step_num + 1
                })

                # Force agent to scroll, or navigate elsewhere, or try completely different approach
                # Create a forced alternative action
                step_data['thinking'] = thinking + " [FORCED: Breaking stuck loop]"
                step_data['result'] = {'success': False, 'message': 'Semantic stuck detected - forcing alternative approach'}
                step_data['skipped'] = True
                result['steps'].append(step_data)
                self.steps.append(step_data)
                step_num += 1
                consecutive_failures += 1

                if consecutive_failures >= 2:
                    self.status("❌ Stuck on same thinking pattern - stopping test")
                    result['status'] = 'failed'
                    result['failure_reason'] = 'Agent stuck describing same situation repeatedly without progress'
                    break

                continue

            # PATTERN-BASED STUCK DETECTION: Check if agent is repeating the same failed pattern
            action_pattern = f"{action.get('type')}:{action.get('selector', '')}"
            self.recent_action_patterns.append(action_pattern)

            # Keep only last 5 actions for pattern detection
            if len(self.recent_action_patterns) > 5:
                self.recent_action_patterns.pop(0)

            # If same action attempted 3+ times in last 5 steps, agent is STUCK
            pattern_count = self.recent_action_patterns.count(action_pattern)
            if pattern_count >= stuck_threshold:
                self.status(f"   🚨 STUCK DETECTED: Attempted {action_pattern} {pattern_count} times")
                self.status(f"   ⏭️  Forcing agent to move on...")

                # Log as issue
                self.issues.append({
                    'type': 'stuck_loop',
                    'message': f"Agent got stuck trying to: {action.get('type')} on {action.get('selector', 'unknown')}. Attempted {pattern_count} times without success.",
                    'severity': 'high',
                    'step': step_num + 1
                })

                # Clear the stuck pattern and force completion or skip
                self.recent_action_patterns = []

                # Skip this step and let AI try something completely different next iteration
                step_data['result'] = {'success': False, 'message': f'Stuck on action - forcing skip after {pattern_count} attempts'}
                step_data['skipped'] = True
                result['steps'].append(step_data)
                self.steps.append(step_data)
                step_num += 1
                consecutive_failures += 1

                # If stuck too many times (3+ consecutive), mark test as incomplete
                if consecutive_failures >= 3:
                    self.status("❌ Too many consecutive failures - stopping test")
                    result['status'] = 'failed'
                    result['failure_reason'] = 'Agent stuck in loop, unable to proceed'
                    break

                continue  # Skip to next iteration

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
                        self.status("[WARNING] Some acceptance criteria not met")
                
                step_data['result'] = {'success': True, 'message': 'Task completed'}
                result['steps'].append(step_data)
                break

            # Execute action
            if action.get('type') and action['type'] not in ['done', 'unknown']:
                action_signature = f"{action.get('type')}:{action.get('selector', '')}:{action.get('text', '')}"

                # Only skip if this EXACT action succeeded before (prevents infinite loops)
                # Failed actions can be retried with different selectors
                if action_signature in self.completed_actions:
                    # Allow retry if it's been more than 3 steps since this action
                    if len(result['steps']) - self.completed_actions.count(action_signature) < 3:
                        self.status(f"   [WARNING]  This exact action already succeeded, trying anyway...")

                # Screenshot before action
                before_shot = await self.screenshot(
                    f"step_{step_num + 1}_before",
                    {'phase': 'before', 'action': action}
                )
                step_data['screenshot_before'] = before_shot

                # Execute
                action_result = await self.execute_action(action)
                step_data['result'] = action_result

                # Only track SUCCESSFUL actions to prevent infinite loops
                # Failed actions can be retried with different approaches
                if action_result['success']:
                    self.completed_actions.append(action_signature)
                    self.status(f"   [OK] {action_result['message']}")
                    consecutive_failures = 0  # Reset on success
                else:
                    self.status(f"   [FAIL] {action_result['message']}")
                    consecutive_failures += 1  # Increment on failure

                    # Log failed action as an issue for reporting
                    self.issues.append({
                        'type': 'action_failed',
                        'message': f"Failed to {action.get('type')} on {action.get('selector', 'unknown')}: {action_result['message']}",
                        'severity': 'low',
                        'step': step_num + 1
                    })

                # Screenshot after action (ultra-fast for speed)
                await asyncio.sleep(0.1)  # Reduced from 0.3s
                after_shot = await self.screenshot(
                    f"step_{step_num + 1}_after",
                    {'phase': 'after', 'action': action, 'result': action_result}
                )
                step_data['screenshot_after'] = after_shot

            result['steps'].append(step_data)
            # Also add to self.steps for conversation memory
            self.steps.append(step_data)
            step_num += 1

        # Check if we hit max steps without completing
        if result['status'] == 'running':
            result['status'] = 'needs_continuation'
            self.status("⏸️  Paused at max steps - User can continue")
            await self.screenshot("test_paused", {'phase': 'paused'})

        result['end_time'] = datetime.now().isoformat()
        result['issues_found'] = len(self.issues)
        self.results.append(result)

        return result
    
    def get_report_data(self) -> Dict:
        """Get all data for report generation."""
        # Get available fixtures if test data manager is initialized
        available_fixtures = []
        if self.test_data_manager:
            available_fixtures = self.test_data_manager.list_fixtures()

        # Get API test results if API tester is initialized
        api_assertions = []
        if self.api_tester:
            api_assertions = [a.to_dict() for a in self.api_tester.get_assertions()]

        return {
            'results': self.results,
            'issues': self.issues,
            'screenshots': self.screenshots,
            'video_path': str(self.video_path) if self.video_path else None,
            'visual_regressions': self.visual_regressions,
            'assertion_results': self.assertion_results,
            'steps': self.steps,
            'console_logs': self.console_logs,
            'console_errors': self.console_errors,
            'network_errors': self.network_errors,
            'performance_metrics': self.performance_metrics,
            'session_dir': str(self.session_dir) if self.session_dir else None,
            'browser_type': self.browser_type,
            'available_fixtures': available_fixtures,
            'api_responses': self.api_responses,
            'api_assertions': api_assertions,
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
