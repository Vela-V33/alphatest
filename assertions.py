#!/usr/bin/env python3
"""
Custom Assertions Library
Provides reusable test patterns and assertions for common testing scenarios.
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import re


class AssertionResult:
    """Result of an assertion."""

    def __init__(self, passed: bool, message: str, details: Optional[Dict] = None):
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            'passed': self.passed,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp
        }


class Assertions:
    """Collection of reusable assertions for testing."""

    @staticmethod
    def assert_equals(actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """Assert that two values are equal."""
        passed = actual == expected
        msg = message or f"Expected {expected}, got {actual}"
        return AssertionResult(passed, msg, {
            'expected': expected,
            'actual': actual,
            'type': 'equals'
        })

    @staticmethod
    def assert_not_equals(actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """Assert that two values are not equal."""
        passed = actual != expected
        msg = message or f"Expected value different from {expected}, got {actual}"
        return AssertionResult(passed, msg, {
            'expected_not': expected,
            'actual': actual,
            'type': 'not_equals'
        })

    @staticmethod
    def assert_contains(haystack: str, needle: str, message: str = "") -> AssertionResult:
        """Assert that a string contains a substring."""
        passed = needle in haystack
        msg = message or f"Expected '{haystack}' to contain '{needle}'"
        return AssertionResult(passed, msg, {
            'haystack': haystack[:200],
            'needle': needle,
            'type': 'contains'
        })

    @staticmethod
    def assert_not_contains(haystack: str, needle: str, message: str = "") -> AssertionResult:
        """Assert that a string does not contain a substring."""
        passed = needle not in haystack
        msg = message or f"Expected '{haystack}' to not contain '{needle}'"
        return AssertionResult(passed, msg, {
            'haystack': haystack[:200],
            'needle': needle,
            'type': 'not_contains'
        })

    @staticmethod
    def assert_matches(text: str, pattern: str, message: str = "") -> AssertionResult:
        """Assert that a string matches a regex pattern."""
        try:
            passed = bool(re.search(pattern, text))
            msg = message or f"Expected '{text}' to match pattern '{pattern}'"
            return AssertionResult(passed, msg, {
                'text': text[:200],
                'pattern': pattern,
                'type': 'matches'
            })
        except re.error as e:
            return AssertionResult(False, f"Invalid regex pattern: {e}", {
                'pattern': pattern,
                'error': str(e)
            })

    @staticmethod
    def assert_url_contains(url: str, expected: str, message: str = "") -> AssertionResult:
        """Assert that URL contains expected string."""
        passed = expected in url
        msg = message or f"Expected URL to contain '{expected}', got '{url}'"
        return AssertionResult(passed, msg, {
            'url': url,
            'expected': expected,
            'type': 'url_contains'
        })

    @staticmethod
    def assert_url_equals(url: str, expected: str, message: str = "") -> AssertionResult:
        """Assert that URL equals expected value."""
        # Strip trailing slashes for comparison
        url_clean = url.rstrip('/')
        expected_clean = expected.rstrip('/')
        passed = url_clean == expected_clean
        msg = message or f"Expected URL '{expected}', got '{url}'"
        return AssertionResult(passed, msg, {
            'url': url,
            'expected': expected,
            'type': 'url_equals'
        })

    @staticmethod
    def assert_element_visible(element_found: bool, selector: str, message: str = "") -> AssertionResult:
        """Assert that an element is visible."""
        passed = element_found
        msg = message or f"Expected element '{selector}' to be visible"
        return AssertionResult(passed, msg, {
            'selector': selector,
            'found': element_found,
            'type': 'element_visible'
        })

    @staticmethod
    def assert_element_not_visible(element_found: bool, selector: str, message: str = "") -> AssertionResult:
        """Assert that an element is not visible."""
        passed = not element_found
        msg = message or f"Expected element '{selector}' to not be visible"
        return AssertionResult(passed, msg, {
            'selector': selector,
            'found': element_found,
            'type': 'element_not_visible'
        })

    @staticmethod
    def assert_element_count(count: int, expected: int, selector: str, message: str = "") -> AssertionResult:
        """Assert that element count matches expected."""
        passed = count == expected
        msg = message or f"Expected {expected} elements matching '{selector}', found {count}"
        return AssertionResult(passed, msg, {
            'selector': selector,
            'expected': expected,
            'actual': count,
            'type': 'element_count'
        })

    @staticmethod
    def assert_greater_than(actual: float, threshold: float, message: str = "") -> AssertionResult:
        """Assert that a value is greater than threshold."""
        passed = actual > threshold
        msg = message or f"Expected value > {threshold}, got {actual}"
        return AssertionResult(passed, msg, {
            'actual': actual,
            'threshold': threshold,
            'type': 'greater_than'
        })

    @staticmethod
    def assert_less_than(actual: float, threshold: float, message: str = "") -> AssertionResult:
        """Assert that a value is less than threshold."""
        passed = actual < threshold
        msg = message or f"Expected value < {threshold}, got {actual}"
        return AssertionResult(passed, msg, {
            'actual': actual,
            'threshold': threshold,
            'type': 'less_than'
        })

    @staticmethod
    def assert_in_range(actual: float, min_val: float, max_val: float, message: str = "") -> AssertionResult:
        """Assert that a value is within a range."""
        passed = min_val <= actual <= max_val
        msg = message or f"Expected value in range [{min_val}, {max_val}], got {actual}"
        return AssertionResult(passed, msg, {
            'actual': actual,
            'min': min_val,
            'max': max_val,
            'type': 'in_range'
        })

    @staticmethod
    def assert_response_time(duration_ms: float, max_ms: float, message: str = "") -> AssertionResult:
        """Assert that response time is below threshold."""
        passed = duration_ms <= max_ms
        msg = message or f"Expected response time ≤ {max_ms}ms, got {duration_ms}ms"
        return AssertionResult(passed, msg, {
            'duration_ms': duration_ms,
            'max_ms': max_ms,
            'type': 'response_time'
        })


class TestPatterns:
    """Common test patterns and workflows."""

    @staticmethod
    def login_flow(username: str, password: str) -> Dict:
        """Standard login flow pattern."""
        return {
            'pattern': 'login',
            'steps': [
                {'action': 'navigate', 'url': '/login'},
                {'action': 'fill', 'selector': 'input[name="email"], input[type="email"]', 'value': username},
                {'action': 'fill', 'selector': 'input[name="password"], input[type="password"]', 'value': password},
                {'action': 'click', 'selector': 'button[type="submit"], button:has-text("Log in")'},
                {'action': 'wait', 'condition': 'url_contains', 'value': 'dashboard'}
            ],
            'assertions': [
                {'type': 'url_contains', 'value': 'dashboard'},
                {'type': 'element_visible', 'selector': '.user-menu, [data-testid="user-menu"]'}
            ]
        }

    @staticmethod
    def form_submission(form_data: Dict[str, str], submit_selector: str = 'button[type="submit"]') -> Dict:
        """Generic form submission pattern."""
        steps = []

        for field_name, value in form_data.items():
            steps.append({
                'action': 'fill',
                'selector': f'input[name="{field_name}"], textarea[name="{field_name}"], select[name="{field_name}"]',
                'value': value
            })

        steps.append({
            'action': 'click',
            'selector': submit_selector
        })

        return {
            'pattern': 'form_submission',
            'steps': steps,
            'form_data': form_data
        }

    @staticmethod
    def search_flow(query: str, search_selector: str = 'input[type="search"], input[placeholder*="search" i]') -> Dict:
        """Standard search flow pattern."""
        return {
            'pattern': 'search',
            'steps': [
                {'action': 'fill', 'selector': search_selector, 'value': query},
                {'action': 'press', 'key': 'Enter'},
                {'action': 'wait', 'condition': 'network_idle'}
            ],
            'assertions': [
                {'type': 'url_contains', 'value': query.replace(' ', '+')},
                {'type': 'element_visible', 'selector': '.search-results, [data-testid="search-results"]'}
            ]
        }

    @staticmethod
    def pagination_test(items_per_page: int = 10) -> Dict:
        """Pagination testing pattern."""
        return {
            'pattern': 'pagination',
            'steps': [
                {'action': 'count_elements', 'selector': '.item, [data-testid="list-item"]'},
                {'action': 'click', 'selector': '.next, button:has-text("Next")'},
                {'action': 'wait', 'condition': 'network_idle'}
            ],
            'assertions': [
                {'type': 'element_count', 'selector': '.item, [data-testid="list-item"]', 'expected': items_per_page}
            ]
        }

    @staticmethod
    def crud_create(entity_type: str, data: Dict[str, str]) -> Dict:
        """CRUD Create pattern."""
        return {
            'pattern': 'crud_create',
            'entity': entity_type,
            'steps': [
                {'action': 'click', 'selector': f'button:has-text("New {entity_type}"), .create-{entity_type}'},
                *TestPatterns.form_submission(data)['steps'],
                {'action': 'wait', 'condition': 'url_contains', 'value': entity_type.lower()}
            ],
            'assertions': [
                {'type': 'contains', 'value': 'success'},
                {'type': 'element_visible', 'selector': f'.{entity_type}-created, .success-message'}
            ]
        }

    @staticmethod
    def accessibility_check() -> Dict:
        """Accessibility testing pattern."""
        return {
            'pattern': 'accessibility',
            'checks': [
                {'type': 'contrast', 'min_ratio': 4.5},
                {'type': 'alt_text', 'required': True},
                {'type': 'aria_labels', 'required': True},
                {'type': 'keyboard_nav', 'required': True},
                {'type': 'focus_visible', 'required': True}
            ]
        }

    @staticmethod
    def performance_check(max_load_time: float = 3000) -> Dict:
        """Performance testing pattern."""
        return {
            'pattern': 'performance',
            'metrics': [
                {'metric': 'load_time', 'max_ms': max_load_time},
                {'metric': 'first_contentful_paint', 'max_ms': 1500},
                {'metric': 'time_to_interactive', 'max_ms': 5000},
                {'metric': 'cumulative_layout_shift', 'max': 0.1}
            ]
        }


# Example usage
if __name__ == "__main__":
    # Test assertions
    result1 = Assertions.assert_equals(5, 5, "Numbers should match")
    print(result1.to_dict())

    result2 = Assertions.assert_contains("Hello World", "World", "Should contain substring")
    print(result2.to_dict())

    result3 = Assertions.assert_url_contains("https://example.com/dashboard", "dashboard")
    print(result3.to_dict())

    # Test patterns
    login = TestPatterns.login_flow("user@example.com", "password123")
    print(login)

    search = TestPatterns.search_flow("test query")
    print(search)
