#!/usr/bin/env python3
"""
Network Monitor Module
Monitors and tracks network requests and responses during testing.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from playwright.async_api import Page, Request, Response


class NetworkRequest:
    """Represents a captured network request."""

    def __init__(
        self,
        url: str,
        method: str,
        resource_type: str,
        headers: Dict[str, str],
        post_data: Optional[str] = None
    ):
        self.url = url
        self.method = method
        self.resource_type = resource_type
        self.headers = headers
        self.post_data = post_data
        self.timestamp = datetime.now()
        self.response: Optional['NetworkResponse'] = None
        self.duration_ms: Optional[float] = None
        self.failed = False
        self.failure_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'url': self.url,
            'method': self.method,
            'resource_type': self.resource_type,
            'headers': self.headers,
            'post_data': self.post_data,
            'timestamp': self.timestamp.isoformat(),
            'duration_ms': self.duration_ms,
            'failed': self.failed,
            'failure_reason': self.failure_reason,
            'response': self.response.to_dict() if self.response else None
        }


class NetworkResponse:
    """Represents a captured network response."""

    def __init__(
        self,
        status: int,
        status_text: str,
        headers: Dict[str, str],
        body_size: int = 0
    ):
        self.status = status
        self.status_text = status_text
        self.headers = headers
        self.body_size = body_size
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'status': self.status,
            'status_text': self.status_text,
            'headers': self.headers,
            'body_size': self.body_size,
            'timestamp': self.timestamp.isoformat()
        }


class NetworkMonitor:
    """Monitors network activity during test execution."""

    def __init__(self, page: Optional[Page] = None, status_callback: Callable = None):
        self.page = page
        self.status = status_callback or print
        self.requests: List[NetworkRequest] = []
        self.api_calls: List[NetworkRequest] = []
        self.failed_requests: List[NetworkRequest] = []
        self.monitoring = False

        # Request tracking
        self.pending_requests: Dict[str, NetworkRequest] = {}

    def start_monitoring(self, page: Page) -> None:
        """Start monitoring network activity."""
        self.page = page
        self.monitoring = True

        # Set up event listeners
        page.on("request", self._handle_request)
        page.on("response", self._handle_response)
        page.on("requestfailed", self._handle_request_failed)

        self.status("   [Network] Monitoring started")

    def stop_monitoring(self) -> None:
        """Stop monitoring network activity."""
        self.monitoring = False
        self.status("   [Network] Monitoring stopped")

    def _handle_request(self, request: Request) -> None:
        """Handle outgoing request."""
        try:
            net_request = NetworkRequest(
                url=request.url,
                method=request.method,
                resource_type=request.resource_type,
                headers=request.headers,
                post_data=request.post_data
            )

            self.requests.append(net_request)
            self.pending_requests[request.url] = net_request

            # Track API calls separately
            if self._is_api_call(request):
                self.api_calls.append(net_request)
                self.status(f"   [API] {request.method} {request.url}")

        except Exception:
            pass

    async def _handle_response(self, response: Response) -> None:
        """Handle incoming response."""
        try:
            request = response.request
            url = request.url

            if url in self.pending_requests:
                net_request = self.pending_requests[url]

                # Calculate duration
                duration = (datetime.now() - net_request.timestamp).total_seconds() * 1000
                net_request.duration_ms = duration

                # Create response object
                headers = await response.all_headers()
                net_response = NetworkResponse(
                    status=response.status,
                    status_text=response.status_text,
                    headers=headers,
                    body_size=len(await response.body()) if response.ok else 0
                )

                net_request.response = net_response

                # Log slow API calls
                if self._is_api_call(request) and duration > 1000:
                    self.status(f"   [API Slow] {request.method} {url} ({duration:.0f}ms)")

                # Remove from pending
                del self.pending_requests[url]

        except Exception:
            pass

    def _handle_request_failed(self, request: Request) -> None:
        """Handle failed request."""
        try:
            url = request.url

            if url in self.pending_requests:
                net_request = self.pending_requests[url]
                net_request.failed = True
                net_request.failure_reason = request.failure
                self.failed_requests.append(net_request)

                self.status(f"   [Network Failed] {request.method} {url}")

                del self.pending_requests[url]

        except Exception:
            pass

    def _is_api_call(self, request: Request) -> bool:
        """Determine if a request is an API call."""
        resource_type = request.resource_type

        # Check resource type
        if resource_type in ['xhr', 'fetch']:
            return True

        # Check URL patterns
        url = request.url.lower()
        api_patterns = ['/api/', '/graphql', '/rest/', '/v1/', '/v2/', '/v3/']

        return any(pattern in url for pattern in api_patterns)

    def get_api_summary(self) -> Dict[str, Any]:
        """Get summary of API calls."""
        if not self.api_calls:
            return {}

        successful = [r for r in self.api_calls if r.response and r.response.status < 400]
        failed = [r for r in self.api_calls if r.failed or (r.response and r.response.status >= 400)]

        durations = [r.duration_ms for r in self.api_calls if r.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            'total_calls': len(self.api_calls),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(self.api_calls) if self.api_calls else 0,
            'avg_duration_ms': avg_duration,
            'slowest_call': max(durations) if durations else 0,
            'fastest_call': min(durations) if durations else 0
        }

    def get_slow_api_calls(self, threshold_ms: float = 1000) -> List[Dict]:
        """Get API calls that exceeded threshold."""
        slow_calls = []

        for req in self.api_calls:
            if req.duration_ms and req.duration_ms > threshold_ms:
                slow_calls.append({
                    'url': req.url,
                    'method': req.method,
                    'duration_ms': req.duration_ms,
                    'status': req.response.status if req.response else None
                })

        return sorted(slow_calls, key=lambda x: x['duration_ms'], reverse=True)

    def get_failed_requests(self) -> List[Dict]:
        """Get all failed requests."""
        return [req.to_dict() for req in self.failed_requests]

    def get_request_by_pattern(self, pattern: str) -> List[NetworkRequest]:
        """Get requests matching a URL pattern."""
        return [
            req for req in self.requests
            if pattern.lower() in req.url.lower()
        ]

    def wait_for_api_response(
        self,
        url_pattern: str,
        timeout_ms: int = 5000
    ) -> Optional[NetworkRequest]:
        """Wait for a specific API response (simplified)."""
        # This would need async implementation in real usage
        matches = self.get_request_by_pattern(url_pattern)
        return matches[-1] if matches else None

    def get_all_requests(self) -> List[Dict]:
        """Get all captured requests."""
        return [req.to_dict() for req in self.requests]

    def get_statistics(self) -> Dict[str, Any]:
        """Get network statistics."""
        total_requests = len(self.requests)
        total_failed = len(self.failed_requests)

        # Calculate total data transferred
        total_bytes = sum(
            req.response.body_size
            for req in self.requests
            if req.response
        )

        # Group by resource type
        by_type = {}
        for req in self.requests:
            if req.resource_type not in by_type:
                by_type[req.resource_type] = 0
            by_type[req.resource_type] += 1

        return {
            'total_requests': total_requests,
            'total_failed': total_failed,
            'success_rate': (total_requests - total_failed) / total_requests if total_requests else 0,
            'total_bytes': total_bytes,
            'total_kb': total_bytes / 1024,
            'total_mb': total_bytes / (1024 * 1024),
            'requests_by_type': by_type,
            'api_summary': self.get_api_summary()
        }

    def clear(self) -> None:
        """Clear all captured data."""
        self.requests = []
        self.api_calls = []
        self.failed_requests = []
        self.pending_requests = {}
