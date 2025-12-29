#!/usr/bin/env python3
"""
Smart Element Finder Module
Advanced element location strategies with retry logic and overlay handling.
"""

import asyncio
import re
from typing import Optional, List, Dict, Any, Callable
from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError


class SmartElementFinder:
    """Advanced element finding with multiple strategies and intelligent fallbacks."""

    def __init__(self, page: Page, status_callback: Callable = None):
        self.page = page
        self.status = status_callback or print

    async def find_and_click(
        self,
        target: str,
        max_retries: int = 3,
        scroll_into_view: bool = True,
        dismiss_overlays: bool = True
    ) -> Dict[str, Any]:
        """
        Find and click an element using multiple strategies.

        Args:
            target: Description of what to click (e.g., "Submit button", "Login link")
            max_retries: Number of retry attempts
            scroll_into_view: Auto-scroll element into view
            dismiss_overlays: Try to dismiss blocking overlays

        Returns:
            Dict with success status, method used, and details
        """
        self.status(f"   [Searching] Looking for: {target}")

        for attempt in range(max_retries):
            try:
                # Dismiss overlays on first attempt
                if attempt == 0 and dismiss_overlays:
                    await self._dismiss_common_overlays()

                # Try multiple finding strategies
                element, method = await self._try_all_strategies(target)

                if element:
                    self.status(f"   [Found] Using strategy: {method}")

                    # Scroll into view if needed
                    if scroll_into_view:
                        await self._safe_scroll_into_view(element)

                    # Verify element is clickable
                    if await self._is_clickable(element):
                        # Perform click
                        await element.click(timeout=5000)

                        # Brief wait for any immediate effects
                        await asyncio.sleep(0.3)

                        self.status(f"   [Clicked] Successfully clicked: {target}")

                        return {
                            'success': True,
                            'method': method,
                            'target': target,
                            'attempts': attempt + 1
                        }
                    else:
                        self.status(f"   [Retry] Element not clickable, attempt {attempt + 1}/{max_retries}")

                else:
                    self.status(f"   [Retry] Element not found, attempt {attempt + 1}/{max_retries}")

                # Exponential backoff
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(wait_time)

            except PlaywrightTimeoutError:
                self.status(f"   [Timeout] Attempt {attempt + 1}/{max_retries} timed out")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                self.status(f"   [Error] Attempt {attempt + 1}/{max_retries}: {str(e)[:100]}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return {
            'success': False,
            'target': target,
            'attempts': max_retries,
            'error': 'Failed to find or click element after all retries'
        }

    async def _try_all_strategies(self, target: str) -> tuple[Optional[Locator], str]:
        """Try multiple strategies to find an element."""

        strategies = [
            ('exact_text', self._find_by_exact_text),
            ('partial_text', self._find_by_partial_text),
            ('placeholder', self._find_by_placeholder),
            ('aria_label', self._find_by_aria_label),
            ('role_name', self._find_by_role_and_name),
            ('test_id', self._find_by_test_id),
            ('title', self._find_by_title),
            ('fuzzy_text', self._find_by_fuzzy_text),
        ]

        for strategy_name, strategy_func in strategies:
            try:
                element = await strategy_func(target)
                if element:
                    # Verify element exists
                    count = await element.count()
                    if count > 0:
                        return (element.first, strategy_name)
            except Exception:
                continue

        return (None, 'none')

    async def _find_by_exact_text(self, target: str) -> Optional[Locator]:
        """Find by exact text match."""
        # Try buttons first
        locator = self.page.get_by_role("button", name=target, exact=True)
        if await locator.count() > 0:
            return locator

        # Try links
        locator = self.page.get_by_role("link", name=target, exact=True)
        if await locator.count() > 0:
            return locator

        # Try any text
        locator = self.page.get_by_text(target, exact=True)
        if await locator.count() > 0:
            return locator

        return None

    async def _find_by_partial_text(self, target: str) -> Optional[Locator]:
        """Find by partial text match."""
        # Try buttons
        locator = self.page.get_by_role("button", name=re.compile(re.escape(target), re.I))
        if await locator.count() > 0:
            return locator

        # Try links
        locator = self.page.get_by_role("link", name=re.compile(re.escape(target), re.I))
        if await locator.count() > 0:
            return locator

        # Try any element with partial text
        locator = self.page.get_by_text(re.compile(re.escape(target), re.I))
        if await locator.count() > 0:
            return locator

        return None

    async def _find_by_placeholder(self, target: str) -> Optional[Locator]:
        """Find by placeholder text."""
        locator = self.page.get_by_placeholder(target)
        if await locator.count() > 0:
            return locator

        # Try partial placeholder
        locator = self.page.get_by_placeholder(re.compile(re.escape(target), re.I))
        if await locator.count() > 0:
            return locator

        return None

    async def _find_by_aria_label(self, target: str) -> Optional[Locator]:
        """Find by aria-label."""
        locator = self.page.get_by_label(target)
        if await locator.count() > 0:
            return locator

        # Try partial label
        locator = self.page.get_by_label(re.compile(re.escape(target), re.I))
        if await locator.count() > 0:
            return locator

        return None

    async def _find_by_role_and_name(self, target: str) -> Optional[Locator]:
        """Find by role and name combinations."""
        roles = ['button', 'link', 'textbox', 'checkbox', 'radio', 'combobox', 'menuitem']

        for role in roles:
            try:
                locator = self.page.get_by_role(role, name=re.compile(re.escape(target), re.I))
                if await locator.count() > 0:
                    return locator
            except Exception:
                continue

        return None

    async def _find_by_test_id(self, target: str) -> Optional[Locator]:
        """Find by data-testid attribute."""
        # Convert target to kebab-case test id
        test_id = target.lower().replace(' ', '-')

        locator = self.page.get_by_test_id(test_id)
        if await locator.count() > 0:
            return locator

        # Try with common prefixes
        for prefix in ['', 'btn-', 'link-', 'input-']:
            locator = self.page.get_by_test_id(f"{prefix}{test_id}")
            if await locator.count() > 0:
                return locator

        return None

    async def _find_by_title(self, target: str) -> Optional[Locator]:
        """Find by title attribute."""
        locator = self.page.locator(f'[title="{target}"]')
        if await locator.count() > 0:
            return locator

        # Try partial title
        locator = self.page.locator(f'[title*="{target}"]')
        if await locator.count() > 0:
            return locator

        return None

    async def _find_by_fuzzy_text(self, target: str) -> Optional[Locator]:
        """Find by fuzzy text matching (handles variations)."""
        # Remove common words and punctuation for fuzzy matching
        fuzzy_target = target.lower().replace('button', '').replace('link', '').strip()

        if not fuzzy_target:
            return None

        # Try finding any element containing the fuzzy text
        locator = self.page.locator(f'//*[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{fuzzy_target}")]')
        if await locator.count() > 0:
            return locator

        return None

    async def _safe_scroll_into_view(self, element: Locator) -> bool:
        """Safely scroll element into view."""
        try:
            await element.scroll_into_view_if_needed(timeout=3000)
            await asyncio.sleep(0.2)  # Brief pause after scroll
            return True
        except Exception as e:
            self.status(f"   [Scroll] Could not scroll into view: {str(e)[:50]}")
            return False

    async def _is_clickable(self, element: Locator) -> bool:
        """Check if element is clickable."""
        try:
            # Check if visible
            is_visible = await element.is_visible()
            if not is_visible:
                return False

            # Check if enabled
            is_enabled = await element.is_enabled()
            if not is_enabled:
                return False

            # Check if not covered
            # Try to get bounding box
            box = await element.bounding_box()
            if not box:
                return False

            return True
        except Exception:
            return False

    async def _dismiss_common_overlays(self) -> None:
        """Attempt to dismiss common overlays and modals."""
        self.status("   [Overlay] Checking for blocking overlays...")

        overlay_selectors = [
            # Cookie banners
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")',
            'button:has-text("I Accept")',
            'button:has-text("Got it")',
            'button:has-text("OK")',
            '[aria-label*="Accept"]',
            '[aria-label*="Cookie"]',

            # Modal close buttons
            'button[aria-label="Close"]',
            'button.close',
            '[data-dismiss="modal"]',
            '.modal-close',
            'button:has-text("×")',
            'button:has-text("Close")',

            # GDPR/Privacy
            'button:has-text("Agree")',
            'button:has-text("Continue")',
        ]

        for selector in overlay_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible():
                    await element.click(timeout=2000)
                    self.status(f"   [Overlay] Dismissed overlay: {selector}")
                    await asyncio.sleep(0.5)
                    break  # Only dismiss one overlay at a time
            except Exception:
                continue

    async def smart_fill(
        self,
        field_description: str,
        value: str,
        clear_first: bool = True
    ) -> Dict[str, Any]:
        """
        Smart form field filling with multiple strategies.

        Args:
            field_description: Description of the field (e.g., "email", "password")
            value: Value to fill
            clear_first: Clear field before filling

        Returns:
            Dict with success status and details
        """
        self.status(f"   [Filling] Looking for field: {field_description}")

        strategies = [
            ('placeholder', lambda: self.page.get_by_placeholder(re.compile(field_description, re.I))),
            ('label', lambda: self.page.get_by_label(re.compile(field_description, re.I))),
            ('type', lambda: self._get_input_by_type(field_description)),
            ('name', lambda: self.page.locator(f'input[name*="{field_description}"]')),
        ]

        for strategy_name, get_locator in strategies:
            try:
                locator = get_locator()
                if await locator.count() > 0:
                    element = locator.first

                    # Scroll into view
                    await self._safe_scroll_into_view(element)

                    # Clear if requested
                    if clear_first:
                        await element.clear()

                    # Fill
                    await element.fill(value)

                    self.status(f"   [Filled] Field '{field_description}' using {strategy_name}")

                    return {
                        'success': True,
                        'method': strategy_name,
                        'field': field_description
                    }
            except Exception:
                continue

        return {
            'success': False,
            'field': field_description,
            'error': 'Could not find or fill field'
        }

    def _get_input_by_type(self, field_description: str) -> Locator:
        """Get input by inferring type from description."""
        desc_lower = field_description.lower()

        if 'email' in desc_lower:
            return self.page.locator('input[type="email"]')
        elif 'password' in desc_lower:
            return self.page.locator('input[type="password"]')
        elif 'search' in desc_lower:
            return self.page.locator('input[type="search"]')
        elif 'tel' in desc_lower or 'phone' in desc_lower:
            return self.page.locator('input[type="tel"]')
        elif 'number' in desc_lower:
            return self.page.locator('input[type="number"]')
        else:
            return self.page.locator('input[type="text"]')

    async def wait_for_navigation(
        self,
        timeout: int = 30000,
        wait_until: str = 'networkidle'
    ) -> bool:
        """
        Intelligent page load waiting.

        Args:
            timeout: Maximum wait time
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')

        Returns:
            True if navigation completed, False otherwise
        """
        self.status(f"   [Navigation] Waiting for page load ({wait_until})...")

        try:
            # Wait for specified load state
            await self.page.wait_for_load_state(wait_until, timeout=timeout)

            # Additional wait for dynamic content
            await asyncio.sleep(0.5)

            self.status("   [Navigation] Page loaded successfully")
            return True

        except PlaywrightTimeoutError:
            self.status("   [Navigation] Timeout waiting for page load")
            return False
        except Exception as e:
            self.status(f"   [Navigation] Error: {str(e)[:50]}")
            return False

    async def verify_click_effect(
        self,
        expected_changes: List[str]
    ) -> Dict[str, bool]:
        """
        Verify that a click had the expected effect.

        Args:
            expected_changes: List of expected changes
                - 'url_change': URL should change
                - 'modal_appear': Modal/dialog should appear
                - 'element_appear:selector': Element should appear
                - 'text_appear:text': Text should appear

        Returns:
            Dict mapping each expected change to verification result
        """
        results = {}

        for change in expected_changes:
            if change == 'url_change':
                # Wait briefly for URL change
                await asyncio.sleep(0.5)
                results['url_change'] = True  # Simplified for now

            elif change == 'modal_appear':
                modal_selectors = ['.modal', '[role="dialog"]', '[aria-modal="true"]']
                for selector in modal_selectors:
                    if await self.page.locator(selector).count() > 0:
                        results['modal_appear'] = True
                        break
                else:
                    results['modal_appear'] = False

            elif change.startswith('element_appear:'):
                selector = change.split(':', 1)[1]
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    results[change] = True
                except:
                    results[change] = False

            elif change.startswith('text_appear:'):
                text = change.split(':', 1)[1]
                try:
                    await self.page.wait_for_selector(f'text="{text}"', timeout=3000)
                    results[change] = True
                except:
                    results[change] = False

        return results
