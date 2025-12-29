#!/usr/bin/env python3
"""
Navigation Tracker Module
Tracks navigation history, breadcrumbs, and page transitions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json


class NavigationBreadcrumb:
    """Represents a single navigation breadcrumb."""

    def __init__(
        self,
        url: str,
        title: str = "",
        action: str = "navigate",
        success: bool = True,
        duration_ms: float = 0
    ):
        self.url = url
        self.title = title
        self.action = action  # navigate, click, back, forward
        self.success = success
        self.duration_ms = duration_ms
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'url': self.url,
            'title': self.title,
            'action': self.action,
            'success': self.success,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp.isoformat()
        }


class NavigationTracker:
    """Tracks navigation history and provides breadcrumb trail."""

    def __init__(self):
        self.breadcrumbs: List[NavigationBreadcrumb] = []
        self.current_url: Optional[str] = None
        self.session_start = datetime.now()

    def add_breadcrumb(
        self,
        url: str,
        title: str = "",
        action: str = "navigate",
        success: bool = True,
        duration_ms: float = 0
    ) -> None:
        """Add a navigation breadcrumb."""
        breadcrumb = NavigationBreadcrumb(
            url=url,
            title=title,
            action=action,
            success=success,
            duration_ms=duration_ms
        )
        self.breadcrumbs.append(breadcrumb)

        if success:
            self.current_url = url

    def get_current_path(self) -> List[str]:
        """Get the current navigation path as a list of URLs."""
        return [b.url for b in self.breadcrumbs if b.success]

    def get_breadcrumb_trail(self, max_items: int = 10) -> List[Dict]:
        """Get recent breadcrumbs as a trail."""
        recent = self.breadcrumbs[-max_items:]
        return [b.to_dict() for b in recent]

    def get_session_summary(self) -> Dict:
        """Get summary of the navigation session."""
        successful = [b for b in self.breadcrumbs if b.success]
        failed = [b for b in self.breadcrumbs if not b.success]

        total_duration = sum(b.duration_ms for b in self.breadcrumbs)
        avg_duration = total_duration / len(self.breadcrumbs) if self.breadcrumbs else 0

        return {
            'total_navigations': len(self.breadcrumbs),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(self.breadcrumbs) if self.breadcrumbs else 0,
            'total_duration_ms': total_duration,
            'avg_duration_ms': avg_duration,
            'session_duration_seconds': (datetime.now() - self.session_start).total_seconds(),
            'current_url': self.current_url,
            'pages_visited': len(set(b.url for b in successful))
        }

    def export_breadcrumbs(self, filepath: Path) -> bool:
        """Export breadcrumbs to JSON file."""
        try:
            data = {
                'breadcrumbs': [b.to_dict() for b in self.breadcrumbs],
                'summary': self.get_session_summary()
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception:
            return False

    def can_go_back(self) -> bool:
        """Check if we can navigate back."""
        return len(self.breadcrumbs) > 1

    def get_previous_url(self) -> Optional[str]:
        """Get the previous URL in navigation history."""
        if len(self.breadcrumbs) >= 2:
            return self.breadcrumbs[-2].url
        return None

    def clear(self) -> None:
        """Clear all breadcrumbs."""
        self.breadcrumbs = []
        self.current_url = None
        self.session_start = datetime.now()
