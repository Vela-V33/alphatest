#!/usr/bin/env python3
"""
AlphaTest - Slack Integration
Send test notifications to Slack channels
"""

import os
import json
import requests
from typing import Optional, Dict
from datetime import datetime

class SlackNotifier:
    """Handle Slack notifications"""

    def __init__(self, webhook_url: Optional[str] = None, bot_token: Optional[str] = None):
        self.webhook_url = webhook_url
        self.bot_token = bot_token

    def send_test_complete(self, project_name: str, report_data: Dict, report_url: str) -> bool:
        """Send test completion notification"""
        try:
            passed = report_data.get('summary', {}).get('passed', 0)
            failed = report_data.get('summary', {}).get('failed', 0)
            total = report_data.get('summary', {}).get('total', 0)
            issues = report_data.get('summary', {}).get('issues', 0)

            success = failed == 0
            emoji = ":white_check_mark:" if success else ":x:"
            color = "#10b981" if success else "#ef4444"

            status_text = "All tests passed!" if success else f"{failed} test(s) failed"

            # Build rich message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} AlphaTest: {project_name}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{status_text}*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Passed:*\n{passed} :white_check_mark:"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Failed:*\n{failed} :x:"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Total:*\n{total}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Issues:*\n{issues} :warning:"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Report",
                                "emoji": True
                            },
                            "url": report_url,
                            "style": "primary" if success else "danger"
                        }
                    ]
                }
            ]

            # Add failed tests details if any
            if failed > 0 and 'results' in report_data:
                failed_tests = [r for r in report_data['results'] if not r.get('success')]
                if failed_tests:
                    failed_text = "\n".join([f"• {t.get('spec_name', 'Unknown test')}" for t in failed_tests[:5]])
                    if len(failed_tests) > 5:
                        failed_text += f"\n_...and {len(failed_tests) - 5} more_"

                    blocks.insert(3, {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Failed Tests:*\n{failed_text}"
                        }
                    })

            # Send via webhook
            if self.webhook_url:
                response = requests.post(
                    self.webhook_url,
                    json={
                        "blocks": blocks,
                        "attachments": [{
                            "color": color,
                            "footer": "AlphaTest - AI-powered testing",
                            "footer_icon": "https://alphatest.dev/icon.png",
                            "ts": int(datetime.now().timestamp())
                        }]
                    },
                    headers={"Content-Type": "application/json"}
                )
                return response.status_code == 200

            return False

        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            return False

    def send_test_started(self, project_name: str, test_count: int) -> bool:
        """Send test started notification"""
        try:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":rocket: *AlphaTest started* for *{project_name}*\nRunning {test_count} test(s)..."
                    }
                }
            ]

            if self.webhook_url:
                response = requests.post(
                    self.webhook_url,
                    json={"blocks": blocks},
                    headers={"Content-Type": "application/json"}
                )
                return response.status_code == 200

            return False

        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            return False

    def send_daily_summary(self, projects_summary: list, date: str) -> bool:
        """Send daily summary of all test runs"""
        try:
            total_runs = len(projects_summary)
            total_passed = sum(1 for p in projects_summary if p['failed'] == 0)
            total_failed = total_runs - total_passed

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📊 AlphaTest Daily Summary - {date}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Runs:*\n{total_runs}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Passed:*\n{total_passed} :white_check_mark:"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Failed:*\n{total_failed} :x:"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Success Rate:*\n{int(total_passed/total_runs*100) if total_runs > 0 else 0}%"
                        }
                    ]
                }
            ]

            # Add project details
            if projects_summary:
                project_lines = []
                for p in projects_summary[:10]:  # Show max 10 projects
                    emoji = ":white_check_mark:" if p['failed'] == 0 else ":x:"
                    project_lines.append(f"{emoji} *{p['name']}* - {p['passed']}/{p['total']} passed")

                if len(projects_summary) > 10:
                    project_lines.append(f"_...and {len(projects_summary) - 10} more projects_")

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Projects:*\n" + "\n".join(project_lines)
                    }
                })

            if self.webhook_url:
                response = requests.post(
                    self.webhook_url,
                    json={"blocks": blocks},
                    headers={"Content-Type": "application/json"}
                )
                return response.status_code == 200

            return False

        except Exception as e:
            print(f"Error sending Slack daily summary: {e}")
            return False

    def send_first_failure(self, project_name: str, test_name: str, error_message: str, report_url: str) -> bool:
        """Send notification on first test failure"""
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f":warning: Test Failure Alert",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Project:* {project_name}\n*Test:* {test_name}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error:*\n```{error_message[:500]}```"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Report",
                                "emoji": True
                            },
                            "url": report_url,
                            "style": "danger"
                        }
                    ]
                }
            ]

            if self.webhook_url:
                response = requests.post(
                    self.webhook_url,
                    json={"blocks": blocks},
                    headers={"Content-Type": "application/json"}
                )
                return response.status_code == 200

            return False

        except Exception as e:
            print(f"Error sending Slack first failure notification: {e}")
            return False


def send_slack_notification(webhook_url: str, project_name: str, report_data: Dict, report_url: str):
    """Helper function to send Slack notification"""
    notifier = SlackNotifier(webhook_url=webhook_url)
    return notifier.send_test_complete(project_name, report_data, report_url)
