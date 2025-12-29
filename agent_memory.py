#!/usr/bin/env python3
"""
Agent Memory Module
Caches successful strategies and learns from test executions.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


class PageMemory:
    """Remembers page structure and successful interactions."""

    def __init__(self, url: str):
        self.url = url
        self.successful_selectors: Dict[str, List[Dict]] = defaultdict(list)
        self.page_structure: Dict[str, Any] = {}
        self.common_elements: Dict[str, str] = {}
        self.last_accessed = datetime.now()
        self.access_count = 0

    def record_successful_interaction(
        self,
        action: str,
        target: str,
        selector: str,
        strategy: str
    ) -> None:
        """Record a successful interaction for future reference."""
        self.successful_selectors[target].append({
            'action': action,
            'selector': selector,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat(),
            'success_count': 1
        })
        self.last_accessed = datetime.now()
        self.access_count += 1

    def get_best_selector(self, target: str, action: str) -> Optional[Dict]:
        """Get the most successful selector for a target."""
        if target not in self.successful_selectors:
            return None

        # Filter by action and sort by success count
        relevant = [
            s for s in self.successful_selectors[target]
            if s['action'] == action
        ]

        if not relevant:
            return None

        # Return most successful
        return max(relevant, key=lambda x: x['success_count'])

    def update_page_structure(self, structure: Dict[str, Any]) -> None:
        """Update cached page structure."""
        self.page_structure = structure
        self.last_accessed = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'url': self.url,
            'successful_selectors': dict(self.successful_selectors),
            'page_structure': self.page_structure,
            'common_elements': self.common_elements,
            'last_accessed': self.last_accessed.isoformat(),
            'access_count': self.access_count
        }


class AgentMemory:
    """Long-term memory for the agent to learn and optimize."""

    def __init__(self, memory_file: Optional[Path] = None):
        self.memory_file = memory_file or Path("agent_memory.json")
        self.page_memories: Dict[str, PageMemory] = {}
        self.global_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.successful_strategies: Dict[str, int] = defaultdict(int)
        self.error_patterns: List[Dict] = []

        # Load existing memory
        self.load()

    def remember_page(self, url: str) -> PageMemory:
        """Get or create page memory."""
        if url not in self.page_memories:
            self.page_memories[url] = PageMemory(url)
        else:
            self.page_memories[url].access_count += 1
            self.page_memories[url].last_accessed = datetime.now()

        return self.page_memories[url]

    def record_success(
        self,
        url: str,
        action: str,
        target: str,
        selector: str,
        strategy: str
    ) -> None:
        """Record a successful interaction."""
        page_mem = self.remember_page(url)
        page_mem.record_successful_interaction(action, target, selector, strategy)

        # Update global strategy statistics
        self.successful_strategies[strategy] += 1

    def get_suggested_selector(
        self,
        url: str,
        target: str,
        action: str
    ) -> Optional[str]:
        """Get a suggested selector based on memory."""
        if url in self.page_memories:
            best = self.page_memories[url].get_best_selector(target, action)
            if best:
                return best['selector']

        return None

    def get_best_strategies(self, limit: int = 3) -> List[str]:
        """Get the most successful strategies in order."""
        sorted_strategies = sorted(
            self.successful_strategies.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [s[0] for s in sorted_strategies[:limit]]

    def record_error(
        self,
        error_type: str,
        context: Dict[str, Any],
        recovery_action: Optional[str] = None
    ) -> None:
        """Record an error and how it was handled."""
        self.error_patterns.append({
            'error_type': error_type,
            'context': context,
            'recovery_action': recovery_action,
            'timestamp': datetime.now().isoformat()
        })

    def find_similar_errors(self, error_type: str, limit: int = 5) -> List[Dict]:
        """Find similar errors from history."""
        similar = [
            e for e in self.error_patterns
            if e['error_type'] == error_type
        ]
        return similar[-limit:]

    def cleanup_old_memories(self, days: int = 30) -> int:
        """Remove memories older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0

        for url in list(self.page_memories.keys()):
            if self.page_memories[url].last_accessed < cutoff:
                del self.page_memories[url]
                removed += 1

        return removed

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories."""
        total_pages = len(self.page_memories)
        total_selectors = sum(
            len(page.successful_selectors)
            for page in self.page_memories.values()
        )
        total_errors = len(self.error_patterns)

        most_visited = None
        if self.page_memories:
            most_visited = max(
                self.page_memories.values(),
                key=lambda x: x.access_count
            )

        return {
            'total_pages': total_pages,
            'total_selectors': total_selectors,
            'total_errors': total_errors,
            'total_strategies': len(self.successful_strategies),
            'most_visited_url': most_visited.url if most_visited else None,
            'most_visited_count': most_visited.access_count if most_visited else 0,
            'best_strategies': self.get_best_strategies(5)
        }

    def save(self) -> bool:
        """Save memory to file."""
        try:
            data = {
                'page_memories': {
                    url: page.to_dict()
                    for url, page in self.page_memories.items()
                },
                'global_patterns': dict(self.global_patterns),
                'successful_strategies': dict(self.successful_strategies),
                'error_patterns': self.error_patterns,
                'last_saved': datetime.now().isoformat()
            }

            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception:
            return False

    def load(self) -> bool:
        """Load memory from file."""
        try:
            if not self.memory_file.exists():
                return False

            with open(self.memory_file, 'r') as f:
                data = json.load(f)

            # Restore page memories
            for url, page_data in data.get('page_memories', {}).items():
                page_mem = PageMemory(url)
                page_mem.successful_selectors = defaultdict(
                    list,
                    page_data.get('successful_selectors', {})
                )
                page_mem.page_structure = page_data.get('page_structure', {})
                page_mem.common_elements = page_data.get('common_elements', {})
                page_mem.access_count = page_data.get('access_count', 0)
                page_mem.last_accessed = datetime.fromisoformat(
                    page_data.get('last_accessed', datetime.now().isoformat())
                )
                self.page_memories[url] = page_mem

            # Restore global data
            self.global_patterns = defaultdict(
                list,
                data.get('global_patterns', {})
            )
            self.successful_strategies = defaultdict(
                int,
                data.get('successful_strategies', {})
            )
            self.error_patterns = data.get('error_patterns', [])

            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all memories."""
        self.page_memories = {}
        self.global_patterns = defaultdict(list)
        self.successful_strategies = defaultdict(int)
        self.error_patterns = []
