"""
Issue Persistence System for AlphaTest

Tracks issues across multiple test runs to enable:
- Regression detection (issues that reappear)
- Fixed issue tracking (issues that disappeared)
- New issue detection
- Historical trend analysis
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class IssueTracker:
    """Manages issue persistence and regression tracking across test runs."""

    def __init__(self, project_reports_dir: Path):
        """
        Initialize issue tracker for a project.

        Args:
            project_reports_dir: Path to project's reports directory
        """
        self.project_dir = project_reports_dir
        self.db_path = project_reports_dir / "issues_db.json"
        self.database = self._load_database()

    def _load_database(self) -> Dict[str, Any]:
        """Load issue database from disk."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {'issues': {}, 'metadata': {'created': datetime.now().isoformat()}}
        return {'issues': {}, 'metadata': {'created': datetime.now().isoformat()}}

    def _save_database(self):
        """Save issue database to disk."""
        self.database['metadata']['last_updated'] = datetime.now().isoformat()
        self.project_dir.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, 'w') as f:
            json.dump(self.database, f, indent=2)

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize URL for consistent comparison.
        Removes query parameters and fragments.
        """
        if not url:
            return ""
        # Remove query params and fragments
        if '?' in url:
            url = url.split('?')[0]
        if '#' in url:
            url = url.split('#')[0]
        # Remove trailing slash
        return url.rstrip('/')

    @staticmethod
    def _generate_fingerprint(issue: Dict[str, Any]) -> str:
        """
        Generate unique fingerprint for an issue.

        Issues with the same fingerprint are considered the same issue
        appearing in different test runs.

        Args:
            issue: Issue dictionary from test run

        Returns:
            SHA-256 hash fingerprint
        """
        issue_type = issue.get('type', '')
        message = issue.get('message', '')
        url = IssueTracker._normalize_url(issue.get('url', ''))

        # Create fingerprint based on issue characteristics
        fingerprint_parts = [issue_type, message, url]

        # Add type-specific identifiers for better matching
        if issue_type == 'accessibility':
            # Include WCAG tags for accessibility issues
            wcag_tags = sorted(issue.get('wcag_tags', []))
            fingerprint_parts.extend(wcag_tags)

        elif issue_type == 'security':
            # Include specific header name for security issues
            # Extract header name from message like "Missing security header: X-Frame-Options"
            if 'Missing security header:' in message:
                header_name = message.split('Missing security header:')[-1].strip()
                fingerprint_parts.append(header_name)

        elif issue_type == 'performance':
            # Include metric name for performance issues
            # Extract metric from message like "[Core Web Vitals] LCP exceeds threshold"
            if '[Core Web Vitals]' in message:
                metric = message.split(']')[1].strip().split()[0]
                fingerprint_parts.append(metric)
            elif '[Lighthouse]' in message:
                # Extract category from "Poor {category} score"
                if 'Poor' in message and 'score' in message:
                    category = message.split('Poor')[-1].split('score')[0].strip()
                    fingerprint_parts.append(category)

        # Create hash from fingerprint parts
        fingerprint_string = '|'.join(str(p) for p in fingerprint_parts)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()

    def process_test_run(self, test_run_id: str, current_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process issues from a new test run and update database.

        Args:
            test_run_id: Unique identifier for this test run
            current_issues: List of issues found in this test run

        Returns:
            Dictionary with categorized issues:
            {
                'new': List of new issues (first occurrence),
                'recurring': List of recurring issues (seen before, still present),
                'regressed': List of regressed issues (was fixed, now back),
                'fixed': List of fixed issues (was present, now gone),
                'all_current': List of all current issues with status markers
            }
        """
        current_fingerprints = {}
        new_issues = []
        recurring_issues = []
        regressed_issues = []

        # Process all current issues
        for issue in current_issues:
            fingerprint = self._generate_fingerprint(issue)
            current_fingerprints[fingerprint] = issue

            # Check if we've seen this issue before
            if fingerprint in self.database['issues']:
                historical_issue = self.database['issues'][fingerprint]

                # Check if this is a regression (was marked fixed, now back)
                if historical_issue.get('status') == 'fixed':
                    issue['tracking_status'] = 'regressed'
                    issue['first_seen'] = historical_issue['first_seen']
                    issue['fixed_in_run'] = historical_issue.get('fixed_in_run')
                    regressed_issues.append(issue)

                    # Update database
                    historical_issue['status'] = 'regressed'
                    historical_issue['regressed_in_run'] = test_run_id
                    historical_issue['last_seen'] = datetime.now().isoformat()

                else:
                    # Recurring issue (still active)
                    issue['tracking_status'] = 'recurring'
                    issue['first_seen'] = historical_issue['first_seen']
                    issue['seen_count'] = historical_issue.get('seen_count', 1) + 1
                    recurring_issues.append(issue)

                    # Update database
                    historical_issue['status'] = 'active'
                    historical_issue['last_seen'] = datetime.now().isoformat()
                    historical_issue['seen_count'] = historical_issue.get('seen_count', 1) + 1

                # Add to test runs history
                if 'test_runs' not in historical_issue:
                    historical_issue['test_runs'] = []
                if test_run_id not in historical_issue['test_runs']:
                    historical_issue['test_runs'].append(test_run_id)

            else:
                # New issue (first time seeing this)
                issue['tracking_status'] = 'new'
                issue['first_seen'] = datetime.now().isoformat()
                issue['seen_count'] = 1
                new_issues.append(issue)

                # Add to database
                self.database['issues'][fingerprint] = {
                    'fingerprint': fingerprint,
                    'first_seen': datetime.now().isoformat(),
                    'last_seen': datetime.now().isoformat(),
                    'seen_count': 1,
                    'status': 'active',
                    'test_runs': [test_run_id],
                    'issue_data': issue
                }

        # Check for fixed issues (in database but not in current run)
        fixed_issues = []
        for fingerprint, historical_issue in self.database['issues'].items():
            if historical_issue.get('status') == 'active' and fingerprint not in current_fingerprints:
                # Issue was active but is now gone - mark as fixed
                historical_issue['status'] = 'fixed'
                historical_issue['fixed_in_run'] = test_run_id
                historical_issue['fixed_at'] = datetime.now().isoformat()
                fixed_issues.append(historical_issue['issue_data'])

        # Save updated database
        self._save_database()

        # Return categorized issues
        return {
            'new': new_issues,
            'recurring': recurring_issues,
            'regressed': regressed_issues,
            'fixed': fixed_issues,
            'all_current': current_issues,  # All current issues now have tracking_status field
            'summary': {
                'new_count': len(new_issues),
                'recurring_count': len(recurring_issues),
                'regressed_count': len(regressed_issues),
                'fixed_count': len(fixed_issues),
                'total_current': len(current_issues),
                'test_run_id': test_run_id,
                'timestamp': datetime.now().isoformat()
            }
        }

    def get_issue_history(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Get historical data for a specific issue by fingerprint."""
        return self.database['issues'].get(fingerprint)

    def get_trend_data(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get trend data for dashboard visualization.

        Args:
            limit: Maximum number of historical runs to include

        Returns:
            Dictionary with trend metrics
        """
        all_issues = self.database['issues']

        # Calculate metrics
        total_tracked = len(all_issues)
        active_count = sum(1 for i in all_issues.values() if i.get('status') == 'active')
        fixed_count = sum(1 for i in all_issues.values() if i.get('status') == 'fixed')
        regressed_count = sum(1 for i in all_issues.values() if i.get('status') == 'regressed')

        # Get most common issues (by seen_count)
        top_issues = sorted(
            all_issues.values(),
            key=lambda x: x.get('seen_count', 0),
            reverse=True
        )[:limit]

        return {
            'total_tracked_issues': total_tracked,
            'active_issues': active_count,
            'fixed_issues': fixed_count,
            'regressed_issues': regressed_count,
            'top_recurring_issues': [
                {
                    'message': i['issue_data'].get('message', ''),
                    'type': i['issue_data'].get('type', ''),
                    'seen_count': i.get('seen_count', 0),
                    'status': i.get('status', ''),
                    'first_seen': i.get('first_seen', '')
                }
                for i in top_issues
            ],
            'last_updated': self.database.get('metadata', {}).get('last_updated', '')
        }
