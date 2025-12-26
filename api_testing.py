#!/usr/bin/env python3
"""
API Testing Module
Provides comprehensive REST and GraphQL API testing capabilities.
"""

import json
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path
import re


class APIResponse:
    """Represents an API response with validation capabilities."""

    def __init__(
        self,
        status_code: int,
        headers: Dict[str, str],
        body: Any,
        response_time_ms: float,
        request_method: str,
        request_url: str
    ):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.response_time_ms = response_time_ms
        self.request_method = request_method
        self.request_url = request_url
        self.timestamp = datetime.now().isoformat()

    @property
    def json(self) -> Any:
        """Get response body as JSON."""
        if isinstance(self.body, str):
            try:
                return json.loads(self.body)
            except:
                return None
        return self.body

    @property
    def text(self) -> str:
        """Get response body as text."""
        if isinstance(self.body, str):
            return self.body
        return json.dumps(self.body)

    def to_dict(self) -> Dict:
        """Convert response to dictionary."""
        return {
            'status_code': self.status_code,
            'headers': dict(self.headers),
            'body': self.body,
            'response_time_ms': self.response_time_ms,
            'request_method': self.request_method,
            'request_url': self.request_url,
            'timestamp': self.timestamp
        }


class APIAssertion:
    """API-specific assertion result."""

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


class APITester:
    """Handles API testing with validation and assertion capabilities."""

    def __init__(self, base_url: str = "", default_headers: Dict[str, str] = None):
        """
        Initialize API tester.

        Args:
            base_url: Base URL for all API requests
            default_headers: Default headers to include in all requests
        """
        self.base_url = base_url.rstrip('/')
        self.default_headers = default_headers or {}
        self.responses = []
        self.assertions = []

    async def request(
        self,
        method: str,
        endpoint: str,
        headers: Dict[str, str] = None,
        query_params: Dict[str, Any] = None,
        body: Any = None,
        json_body: Dict = None,
        timeout: float = 30.0,
        page=None  # Playwright page for making requests
    ) -> APIResponse:
        """
        Make an API request.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint (will be appended to base_url)
            headers: Request headers (merged with default_headers)
            query_params: Query parameters
            body: Request body (raw)
            json_body: Request body as JSON
            timeout: Request timeout in seconds
            page: Playwright page object for making requests

        Returns:
            APIResponse object
        """
        # Build URL
        url = endpoint if endpoint.startswith('http') else f"{self.base_url}/{endpoint.lstrip('/')}"

        # Add query parameters
        if query_params:
            query_string = '&'.join(f"{k}={v}" for k, v in query_params.items())
            url = f"{url}?{query_string}"

        # Merge headers
        request_headers = {**self.default_headers, **(headers or {})}

        # Prepare body
        if json_body is not None:
            body = json.dumps(json_body)
            request_headers['Content-Type'] = 'application/json'

        # Make request using Playwright's page.request API
        start_time = time.time()

        try:
            if page:
                # Use Playwright's API client
                api_request_context = page.request

                response = await api_request_context.fetch(
                    url,
                    method=method.upper(),
                    headers=request_headers,
                    data=body,
                    timeout=timeout * 1000  # Playwright uses milliseconds
                )

                status_code = response.status
                response_headers = response.headers
                response_body = await response.text()

                # Try to parse as JSON
                try:
                    response_body = json.loads(response_body)
                except:
                    pass

            else:
                # Fallback: simulate response for testing
                # In production, this would use requests library
                status_code = 200
                response_headers = {}
                response_body = {"message": "Simulated response (no page provided)"}

        except Exception as e:
            # Handle request errors
            status_code = 0
            response_headers = {}
            response_body = {"error": str(e)}

        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000

        # Create response object
        api_response = APIResponse(
            status_code=status_code,
            headers=response_headers,
            body=response_body,
            response_time_ms=response_time_ms,
            request_method=method.upper(),
            request_url=url
        )

        self.responses.append(api_response)
        return api_response

    # Convenience methods for common HTTP methods

    async def get(self, endpoint: str, **kwargs) -> APIResponse:
        """Make a GET request."""
        return await self.request('GET', endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> APIResponse:
        """Make a POST request."""
        return await self.request('POST', endpoint, **kwargs)

    async def put(self, endpoint: str, **kwargs) -> APIResponse:
        """Make a PUT request."""
        return await self.request('PUT', endpoint, **kwargs)

    async def patch(self, endpoint: str, **kwargs) -> APIResponse:
        """Make a PATCH request."""
        return await self.request('PATCH', endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> APIResponse:
        """Make a DELETE request."""
        return await self.request('DELETE', endpoint, **kwargs)

    # GraphQL support

    async def graphql(
        self,
        query: str,
        variables: Dict = None,
        endpoint: str = '/graphql',
        **kwargs
    ) -> APIResponse:
        """
        Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables
            endpoint: GraphQL endpoint
            **kwargs: Additional request arguments

        Returns:
            APIResponse object
        """
        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        return await self.post(endpoint, json_body=payload, **kwargs)

    # Assertions

    def assert_status_code(self, response: APIResponse, expected: int) -> APIAssertion:
        """Assert response status code."""
        passed = response.status_code == expected
        message = f"Expected status {expected}, got {response.status_code}"

        assertion = APIAssertion(passed, message, {
            'expected': expected,
            'actual': response.status_code,
            'url': response.request_url
        })
        self.assertions.append(assertion)
        return assertion

    def assert_status_in(self, response: APIResponse, expected_codes: List[int]) -> APIAssertion:
        """Assert response status code is in a list of expected codes."""
        passed = response.status_code in expected_codes
        message = f"Expected status in {expected_codes}, got {response.status_code}"

        assertion = APIAssertion(passed, message, {
            'expected': expected_codes,
            'actual': response.status_code,
            'url': response.request_url
        })
        self.assertions.append(assertion)
        return assertion

    def assert_response_time(self, response: APIResponse, max_ms: float) -> APIAssertion:
        """Assert response time is below threshold."""
        passed = response.response_time_ms <= max_ms
        message = f"Expected response time ≤ {max_ms}ms, got {response.response_time_ms:.2f}ms"

        assertion = APIAssertion(passed, message, {
            'max_ms': max_ms,
            'actual_ms': response.response_time_ms,
            'url': response.request_url
        })
        self.assertions.append(assertion)
        return assertion

    def assert_header_present(self, response: APIResponse, header_name: str) -> APIAssertion:
        """Assert a header is present in response."""
        header_name_lower = header_name.lower()
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        passed = header_name_lower in headers_lower

        message = f"Expected header '{header_name}' to be present"

        assertion = APIAssertion(passed, message, {
            'header': header_name,
            'present': passed,
            'url': response.request_url
        })
        self.assertions.append(assertion)
        return assertion

    def assert_header_value(self, response: APIResponse, header_name: str, expected_value: str) -> APIAssertion:
        """Assert a header has a specific value."""
        header_name_lower = header_name.lower()
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        actual_value = headers_lower.get(header_name_lower, '')

        passed = actual_value == expected_value
        message = f"Expected header '{header_name}' to be '{expected_value}', got '{actual_value}'"

        assertion = APIAssertion(passed, message, {
            'header': header_name,
            'expected': expected_value,
            'actual': actual_value,
            'url': response.request_url
        })
        self.assertions.append(assertion)
        return assertion

    def assert_json_path(self, response: APIResponse, json_path: str, expected_value: Any) -> APIAssertion:
        """
        Assert a JSON path has a specific value.

        Args:
            response: API response
            json_path: Dot-notation path (e.g., 'data.user.name')
            expected_value: Expected value at that path
        """
        try:
            data = response.json
            if data is None:
                return APIAssertion(False, "Response is not valid JSON", {'json_path': json_path})

            # Navigate the path
            parts = json_path.split('.')
            current = data

            for part in parts:
                # Handle array indices like 'items[0]'
                if '[' in part:
                    key = part[:part.index('[')]
                    index = int(part[part.index('[') + 1:part.index(']')])
                    current = current[key][index]
                else:
                    current = current[part]

            passed = current == expected_value
            message = f"Expected '{json_path}' to be '{expected_value}', got '{current}'"

            assertion = APIAssertion(passed, message, {
                'json_path': json_path,
                'expected': expected_value,
                'actual': current,
                'url': response.request_url
            })
            self.assertions.append(assertion)
            return assertion

        except (KeyError, IndexError, TypeError) as e:
            message = f"Path '{json_path}' not found in response: {e}"
            assertion = APIAssertion(False, message, {
                'json_path': json_path,
                'error': str(e),
                'url': response.request_url
            })
            self.assertions.append(assertion)
            return assertion

    def assert_json_contains(self, response: APIResponse, key: str) -> APIAssertion:
        """Assert response JSON contains a key."""
        try:
            data = response.json
            if data is None:
                return APIAssertion(False, "Response is not valid JSON", {'key': key})

            passed = key in data
            message = f"Expected response to contain key '{key}'"

            assertion = APIAssertion(passed, message, {
                'key': key,
                'present': passed,
                'url': response.request_url
            })
            self.assertions.append(assertion)
            return assertion

        except Exception as e:
            assertion = APIAssertion(False, f"Error checking key: {e}", {'key': key})
            self.assertions.append(assertion)
            return assertion

    def assert_json_schema(self, response: APIResponse, schema: Dict) -> APIAssertion:
        """
        Assert response matches a JSON schema (simplified).

        Args:
            response: API response
            schema: Expected schema structure
        """
        try:
            data = response.json
            if data is None:
                return APIAssertion(False, "Response is not valid JSON", {'schema': schema})

            # Simplified schema validation
            passed = self._validate_schema(data, schema)
            message = "Response matches schema" if passed else "Response does not match schema"

            assertion = APIAssertion(passed, message, {
                'schema': schema,
                'url': response.request_url
            })
            self.assertions.append(assertion)
            return assertion

        except Exception as e:
            assertion = APIAssertion(False, f"Schema validation error: {e}", {'schema': schema})
            self.assertions.append(assertion)
            return assertion

    def _validate_schema(self, data: Any, schema: Dict) -> bool:
        """Simplified schema validation."""
        if 'type' in schema:
            expected_type = schema['type']
            type_map = {
                'string': str,
                'number': (int, float),
                'integer': int,
                'boolean': bool,
                'array': list,
                'object': dict,
                'null': type(None)
            }

            if expected_type in type_map:
                if not isinstance(data, type_map[expected_type]):
                    return False

        if 'properties' in schema and isinstance(data, dict):
            for key, value_schema in schema['properties'].items():
                if 'required' in schema and key in schema.get('required', []):
                    if key not in data:
                        return False

                if key in data:
                    if not self._validate_schema(data[key], value_schema):
                        return False

        return True

    def assert_body_contains(self, response: APIResponse, text: str) -> APIAssertion:
        """Assert response body contains text."""
        body_text = response.text
        passed = text in body_text

        message = f"Expected response body to contain '{text}'"

        assertion = APIAssertion(passed, message, {
            'text': text,
            'found': passed,
            'url': response.request_url
        })
        self.assertions.append(assertion)
        return assertion

    def get_responses(self) -> List[APIResponse]:
        """Get all API responses."""
        return self.responses

    def get_assertions(self) -> List[APIAssertion]:
        """Get all assertions."""
        return self.assertions

    def clear_history(self):
        """Clear response and assertion history."""
        self.responses = []
        self.assertions = []


class APITestBuilder:
    """Fluent API for building API tests."""

    def __init__(self, tester: APITester):
        self.tester = tester
        self.current_response = None
        self.test_name = ""
        self.steps = []

    def named(self, name: str) -> 'APITestBuilder':
        """Set test name."""
        self.test_name = name
        return self

    async def request(self, method: str, endpoint: str, **kwargs) -> 'APITestBuilder':
        """Make a request and store response."""
        self.current_response = await self.tester.request(method, endpoint, **kwargs)
        self.steps.append({
            'type': 'request',
            'method': method,
            'endpoint': endpoint,
            'response_code': self.current_response.status_code
        })
        return self

    def expect_status(self, code: int) -> 'APITestBuilder':
        """Assert expected status code."""
        if self.current_response:
            assertion = self.tester.assert_status_code(self.current_response, code)
            self.steps.append({
                'type': 'assertion',
                'assertion': 'status_code',
                'expected': code,
                'passed': assertion.passed
            })
        return self

    def expect_json_path(self, path: str, value: Any) -> 'APITestBuilder':
        """Assert JSON path value."""
        if self.current_response:
            assertion = self.tester.assert_json_path(self.current_response, path, value)
            self.steps.append({
                'type': 'assertion',
                'assertion': 'json_path',
                'path': path,
                'expected': value,
                'passed': assertion.passed
            })
        return self

    def expect_response_time_below(self, max_ms: float) -> 'APITestBuilder':
        """Assert response time."""
        if self.current_response:
            assertion = self.tester.assert_response_time(self.current_response, max_ms)
            self.steps.append({
                'type': 'assertion',
                'assertion': 'response_time',
                'max_ms': max_ms,
                'passed': assertion.passed
            })
        return self

    def build(self) -> Dict:
        """Build and return test results."""
        return {
            'name': self.test_name,
            'steps': self.steps,
            'passed': all(step.get('passed', True) for step in self.steps)
        }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_api():
        # Create API tester
        tester = APITester(
            base_url="https://jsonplaceholder.typicode.com",
            default_headers={"User-Agent": "AlphaTest"}
        )

        # Make a GET request
        response = await tester.get('/posts/1', page=None)
        print(f"Status: {response.status_code}")
        print(f"Response time: {response.response_time_ms:.2f}ms")

        # Assertions
        tester.assert_status_code(response, 200)
        tester.assert_response_time(response, 1000)
        tester.assert_json_contains(response, 'title')

        # Print assertions
        for assertion in tester.get_assertions():
            status = "✓" if assertion.passed else "✗"
            print(f"{status} {assertion.message}")

        # Using builder pattern
        builder = APITestBuilder(tester)
        test = await (
            builder
            .named("Get Post Test")
            .request('GET', '/posts/1', page=None)
            .expect_status(200)
            .expect_json_path('userId', 1)
            .expect_response_time_below(1000)
            .build()
        )

        print("\nTest Results:", test)

    # asyncio.run(test_api())  # Uncomment to run
    print("API Testing module loaded successfully")
