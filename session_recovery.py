#!/usr/bin/env python3
"""
Session Recovery Module
Provides checkpointing and recovery capabilities for test sessions.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from enum import Enum


class CheckpointType(Enum):
    """Types of checkpoints."""
    NAVIGATION = "navigation"
    ACTION = "action"
    ASSERTION = "assertion"
    FORM_FILL = "form_fill"
    MILESTONE = "milestone"


class Checkpoint:
    """Represents a recovery checkpoint."""

    def __init__(
        self,
        checkpoint_type: CheckpointType,
        data: Dict[str, Any],
        step_index: int
    ):
        self.checkpoint_type = checkpoint_type
        self.data = data
        self.step_index = step_index
        self.timestamp = datetime.now()
        self.id = f"{checkpoint_type.value}_{step_index}_{int(self.timestamp.timestamp())}"

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'type': self.checkpoint_type.value,
            'data': self.data,
            'step_index': self.step_index,
            'timestamp': self.timestamp.isoformat()
        }


class SessionRecovery:
    """Manages session checkpoints and recovery."""

    def __init__(self, session_dir: Optional[Path] = None):
        self.session_dir = session_dir
        self.checkpoints: List[Checkpoint] = []
        self.current_step = 0
        self.recovery_mode = False
        self.last_successful_checkpoint: Optional[Checkpoint] = None

        # Recovery state
        self.session_state: Dict[str, Any] = {
            'current_url': None,
            'cookies': [],
            'local_storage': {},
            'session_storage': {},
            'form_data': {},
            'navigation_history': []
        }

    def create_checkpoint(
        self,
        checkpoint_type: CheckpointType,
        data: Dict[str, Any]
    ) -> Checkpoint:
        """Create a new checkpoint."""
        checkpoint = Checkpoint(
            checkpoint_type=checkpoint_type,
            data=data,
            step_index=self.current_step
        )

        self.checkpoints.append(checkpoint)
        self.last_successful_checkpoint = checkpoint
        self.current_step += 1

        return checkpoint

    async def save_session_state(self, page) -> Dict[str, Any]:
        """Capture current session state from page."""
        try:
            # Get current URL
            self.session_state['current_url'] = page.url

            # Get cookies
            cookies = await page.context.cookies()
            self.session_state['cookies'] = cookies

            # Get storage (if accessible)
            try:
                local_storage = await page.evaluate('() => Object.assign({}, localStorage)')
                self.session_state['local_storage'] = local_storage
            except:
                pass

            try:
                session_storage = await page.evaluate('() => Object.assign({}, sessionStorage)')
                self.session_state['session_storage'] = session_storage
            except:
                pass

            return self.session_state

        except Exception:
            return {}

    async def restore_session_state(self, page) -> bool:
        """Restore session state to page."""
        try:
            # Restore cookies
            if self.session_state.get('cookies'):
                await page.context.add_cookies(self.session_state['cookies'])

            # Navigate to last URL
            if self.session_state.get('current_url'):
                await page.goto(self.session_state['current_url'])

            # Restore localStorage
            if self.session_state.get('local_storage'):
                for key, value in self.session_state['local_storage'].items():
                    await page.evaluate(
                        f'localStorage.setItem({json.dumps(key)}, {json.dumps(value)})'
                    )

            # Restore sessionStorage
            if self.session_state.get('session_storage'):
                for key, value in self.session_state['session_storage'].items():
                    await page.evaluate(
                        f'sessionStorage.setItem({json.dumps(key)}, {json.dumps(value)})'
                    )

            return True

        except Exception:
            return False

    def get_recovery_point(self) -> Optional[Checkpoint]:
        """Get the last successful checkpoint for recovery."""
        return self.last_successful_checkpoint

    def get_checkpoints_after(self, step_index: int) -> List[Checkpoint]:
        """Get all checkpoints after a specific step."""
        return [
            cp for cp in self.checkpoints
            if cp.step_index > step_index
        ]

    def can_recover(self) -> bool:
        """Check if recovery is possible."""
        return len(self.checkpoints) > 0

    def get_recovery_plan(self) -> Dict[str, Any]:
        """Get a plan for recovery."""
        if not self.can_recover():
            return {'recoverable': False}

        last_checkpoint = self.get_recovery_point()

        return {
            'recoverable': True,
            'last_checkpoint': last_checkpoint.to_dict() if last_checkpoint else None,
            'total_checkpoints': len(self.checkpoints),
            'steps_to_replay': self.current_step - (last_checkpoint.step_index if last_checkpoint else 0),
            'session_state_available': bool(self.session_state.get('current_url'))
        }

    def export_checkpoints(self, filepath: Path) -> bool:
        """Export checkpoints to file."""
        try:
            data = {
                'checkpoints': [cp.to_dict() for cp in self.checkpoints],
                'session_state': self.session_state,
                'current_step': self.current_step,
                'exported_at': datetime.now().isoformat()
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception:
            return False

    def import_checkpoints(self, filepath: Path) -> bool:
        """Import checkpoints from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Restore checkpoints
            self.checkpoints = []
            for cp_data in data.get('checkpoints', []):
                checkpoint = Checkpoint(
                    checkpoint_type=CheckpointType(cp_data['type']),
                    data=cp_data['data'],
                    step_index=cp_data['step_index']
                )
                checkpoint.timestamp = datetime.fromisoformat(cp_data['timestamp'])
                checkpoint.id = cp_data['id']
                self.checkpoints.append(checkpoint)

            # Restore session state
            self.session_state = data.get('session_state', {})
            self.current_step = data.get('current_step', 0)

            if self.checkpoints:
                self.last_successful_checkpoint = self.checkpoints[-1]

            self.recovery_mode = True

            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all checkpoints."""
        self.checkpoints = []
        self.current_step = 0
        self.recovery_mode = False
        self.last_successful_checkpoint = None
        self.session_state = {
            'current_url': None,
            'cookies': [],
            'local_storage': {},
            'session_storage': {},
            'form_data': {},
            'navigation_history': []
        }

    def get_checkpoint_summary(self) -> Dict[str, Any]:
        """Get summary of checkpoints."""
        by_type = {}
        for cp in self.checkpoints:
            cp_type = cp.checkpoint_type.value
            if cp_type not in by_type:
                by_type[cp_type] = 0
            by_type[cp_type] += 1

        return {
            'total_checkpoints': len(self.checkpoints),
            'current_step': self.current_step,
            'checkpoints_by_type': by_type,
            'last_checkpoint': self.last_successful_checkpoint.to_dict() if self.last_successful_checkpoint else None,
            'recovery_mode': self.recovery_mode
        }


class ErrorRecovery:
    """Handles error recovery strategies."""

    def __init__(self):
        self.recovery_strategies: Dict[str, List[str]] = {
            'element_not_found': [
                'wait_longer',
                'scroll_page',
                'dismiss_overlays',
                'refresh_page',
                'try_alternative_selector'
            ],
            'timeout': [
                'increase_timeout',
                'check_network',
                'refresh_page'
            ],
            'network_error': [
                'retry_request',
                'check_connection',
                'use_cached_data'
            ],
            'click_intercepted': [
                'dismiss_overlay',
                'scroll_into_view',
                'wait_for_stable',
                'use_javascript_click'
            ],
            'navigation_failed': [
                'retry_navigation',
                'check_url',
                'clear_cookies',
                'try_alternative_url'
            ]
        }

    def get_recovery_strategies(self, error_type: str) -> List[str]:
        """Get recommended recovery strategies for an error type."""
        return self.recovery_strategies.get(error_type, ['retry', 'skip', 'abort'])

    def suggest_recovery(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest recovery action based on error and context."""
        error_msg = str(error).lower()

        # Classify error
        if 'timeout' in error_msg:
            error_type = 'timeout'
        elif 'not found' in error_msg or 'no element' in error_msg:
            error_type = 'element_not_found'
        elif 'network' in error_msg or 'connection' in error_msg:
            error_type = 'network_error'
        elif 'intercepted' in error_msg or 'not clickable' in error_msg:
            error_type = 'click_intercepted'
        elif 'navigation' in error_msg:
            error_type = 'navigation_failed'
        else:
            error_type = 'unknown'

        strategies = self.get_recovery_strategies(error_type)

        return {
            'error_type': error_type,
            'recommended_strategies': strategies,
            'auto_recoverable': error_type in self.recovery_strategies,
            'suggested_action': strategies[0] if strategies else 'abort'
        }
