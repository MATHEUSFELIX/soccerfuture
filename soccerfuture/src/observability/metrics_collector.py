"""Metrics collector for pipeline and workflow execution.

Collects deterministic counters and gauges for observability
without requiring external monitoring infrastructure.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field


@dataclass
class MetricsSnapshot:
    """A snapshot of collected metrics.

    Attributes:
        counters: Named counter values.
        gauges: Named gauge values (last-set).
        timestamp: When the snapshot was taken.
    """

    counters: dict[str, int] = field(default_factory=dict)
    gauges: dict[str, float] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()


class MetricsCollector:
    """Collects counters and gauges during execution.

    Thread-safe is not required in this phase (single-threaded execution).
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter by value."""
        self._counters[name] = self._counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge to a specific value."""
        self._gauges[name] = value

    def get_counter(self, name: str) -> int:
        """Get current counter value (0 if not set)."""
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        """Get current gauge value (0.0 if not set)."""
        return self._gauges.get(name, 0.0)

    def snapshot(self) -> MetricsSnapshot:
        """Take a snapshot of all current metrics."""
        return MetricsSnapshot(
            counters=dict(self._counters),
            gauges=dict(self._gauges),
        )

    def to_dict(self) -> dict:
        """Export metrics as a dict."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
        }
