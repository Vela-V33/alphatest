#!/usr/bin/env python3
"""
Performance Tracker Module
Collects and analyzes performance metrics during test execution.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from playwright.async_api import Page


class PerformanceMetric:
    """Represents a single performance metric."""

    def __init__(
        self,
        name: str,
        value: float,
        unit: str = "ms",
        threshold: Optional[float] = None
    ):
        self.name = name
        self.value = value
        self.unit = unit
        self.threshold = threshold
        self.timestamp = datetime.now()

    @property
    def is_acceptable(self) -> bool:
        """Check if metric is within acceptable threshold."""
        if self.threshold is None:
            return True
        return self.value <= self.threshold

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'threshold': self.threshold,
            'is_acceptable': self.is_acceptable,
            'timestamp': self.timestamp.isoformat()
        }


class PerformanceTracker:
    """Tracks performance metrics during test execution."""

    def __init__(self, page: Optional[Page] = None):
        self.page = page
        self.metrics: List[PerformanceMetric] = []
        self.timers: Dict[str, float] = {}

        # Performance thresholds (Web Vitals)
        self.thresholds = {
            'page_load': 3000,          # 3 seconds
            'first_contentful_paint': 1800,  # 1.8 seconds
            'largest_contentful_paint': 2500, # 2.5 seconds
            'time_to_interactive': 3800,      # 3.8 seconds
            'cumulative_layout_shift': 0.1,   # Unitless
            'first_input_delay': 100,         # 100ms
            'api_response': 1000,             # 1 second
            'click_response': 200,            # 200ms
        }

    def start_timer(self, name: str) -> None:
        """Start a performance timer."""
        self.timers[name] = time.time()

    def stop_timer(
        self,
        name: str,
        threshold: Optional[float] = None,
        unit: str = "ms"
    ) -> Optional[PerformanceMetric]:
        """Stop a timer and record the metric."""
        if name not in self.timers:
            return None

        start_time = self.timers.pop(name)
        duration = (time.time() - start_time) * 1000  # Convert to ms

        metric = PerformanceMetric(
            name=name,
            value=duration,
            unit=unit,
            threshold=threshold or self.thresholds.get(name)
        )

        self.metrics.append(metric)
        return metric

    async def collect_web_vitals(self) -> Dict[str, Any]:
        """Collect Core Web Vitals from the page."""
        if not self.page:
            return {}

        try:
            vitals = await self.page.evaluate('''
                () => {
                    return new Promise((resolve) => {
                        // Collect performance metrics
                        const perfData = performance.getEntriesByType('navigation')[0];
                        const paintEntries = performance.getEntriesByType('paint');

                        const fcp = paintEntries.find(e => e.name === 'first-contentful-paint');

                        resolve({
                            domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
                            loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
                            domInteractive: perfData.domInteractive - perfData.fetchStart,
                            firstContentfulPaint: fcp ? fcp.startTime : 0,
                            transferSize: perfData.transferSize || 0,
                            encodedBodySize: perfData.encodedBodySize || 0,
                            decodedBodySize: perfData.decodedBodySize || 0
                        });
                    });
                }
            ''')

            # Record as metrics
            if vitals.get('firstContentfulPaint'):
                self.metrics.append(PerformanceMetric(
                    'first_contentful_paint',
                    vitals['firstContentfulPaint'],
                    'ms',
                    self.thresholds['first_contentful_paint']
                ))

            if vitals.get('domInteractive'):
                self.metrics.append(PerformanceMetric(
                    'time_to_interactive',
                    vitals['domInteractive'],
                    'ms',
                    self.thresholds['time_to_interactive']
                ))

            if vitals.get('loadComplete'):
                self.metrics.append(PerformanceMetric(
                    'page_load',
                    vitals['loadComplete'],
                    'ms',
                    self.thresholds['page_load']
                ))

            return vitals

        except Exception as e:
            return {'error': str(e)}

    async def collect_resource_metrics(self) -> List[Dict]:
        """Collect resource loading metrics."""
        if not self.page:
            return []

        try:
            resources = await self.page.evaluate('''
                () => {
                    const resources = performance.getEntriesByType('resource');
                    return resources.map(r => ({
                        name: r.name,
                        type: r.initiatorType,
                        duration: r.duration,
                        size: r.transferSize || 0,
                        cached: r.transferSize === 0
                    }));
                }
            ''')

            # Calculate summary metrics
            total_size = sum(r['size'] for r in resources)
            total_duration = sum(r['duration'] for r in resources)
            cached_count = sum(1 for r in resources if r['cached'])

            self.metrics.append(PerformanceMetric(
                'total_resources',
                len(resources),
                'count'
            ))

            self.metrics.append(PerformanceMetric(
                'total_transfer_size',
                total_size / 1024,  # KB
                'KB'
            ))

            self.metrics.append(PerformanceMetric(
                'cached_resources',
                cached_count,
                'count'
            ))

            return resources

        except Exception:
            return []

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all collected metrics."""
        if not self.metrics:
            return {}

        acceptable = [m for m in self.metrics if m.is_acceptable]
        unacceptable = [m for m in self.metrics if not m.is_acceptable]

        # Group by unit
        by_unit = {}
        for metric in self.metrics:
            if metric.unit not in by_unit:
                by_unit[metric.unit] = []
            by_unit[metric.unit].append(metric)

        # Calculate averages for time-based metrics
        time_metrics = by_unit.get('ms', [])
        avg_time = sum(m.value for m in time_metrics) / len(time_metrics) if time_metrics else 0

        return {
            'total_metrics': len(self.metrics),
            'acceptable': len(acceptable),
            'unacceptable': len(unacceptable),
            'success_rate': len(acceptable) / len(self.metrics) if self.metrics else 0,
            'avg_response_time_ms': avg_time,
            'metrics_by_unit': {
                unit: {
                    'count': len(metrics),
                    'avg': sum(m.value for m in metrics) / len(metrics),
                    'min': min(m.value for m in metrics),
                    'max': max(m.value for m in metrics)
                }
                for unit, metrics in by_unit.items()
            }
        }

    def get_slow_operations(self, threshold_ms: float = 1000) -> List[Dict]:
        """Get operations that exceeded time threshold."""
        time_metrics = [m for m in self.metrics if m.unit == 'ms']
        slow = [m for m in time_metrics if m.value > threshold_ms]
        return [m.to_dict() for m in slow]

    def get_all_metrics(self) -> List[Dict]:
        """Get all metrics as dictionaries."""
        return [m.to_dict() for m in self.metrics]

    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics = []
        self.timers = {}

    def export_report(self) -> Dict[str, Any]:
        """Export a comprehensive performance report."""
        return {
            'summary': self.get_metrics_summary(),
            'slow_operations': self.get_slow_operations(),
            'all_metrics': self.get_all_metrics(),
            'thresholds': self.thresholds,
            'generated_at': datetime.now().isoformat()
        }
