"""Structured logging wrapper for deterministic, machine-readable log output.

Emits JSON-structured log entries with consistent fields for
observability without requiring external monitoring vendors.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    """A single structured log entry.

    Attributes:
        level: Log level (INFO, WARN, ERROR).
        event: Event name/type.
        message: Human-readable message.
        timestamp: ISO-8601 timestamp.
        context: Additional structured context.
    """

    level: str
    event: str
    message: str
    timestamp: str = ""
    context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()


class StructuredLogger:
    """Collects structured log entries for a run.

    Attributes:
        entries: List of log entries collected.
    """

    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def info(self, event: str, message: str, **context) -> None:
        """Log an INFO-level event."""
        self.entries.append(LogEntry(level="INFO", event=event, message=message, context=context))

    def warn(self, event: str, message: str, **context) -> None:
        """Log a WARN-level event."""
        self.entries.append(LogEntry(level="WARN", event=event, message=message, context=context))

    def error(self, event: str, message: str, **context) -> None:
        """Log an ERROR-level event."""
        self.entries.append(LogEntry(level="ERROR", event=event, message=message, context=context))

    def to_list(self) -> list[dict]:
        """Export all entries as a list of dicts."""
        return [
            {"level": e.level, "event": e.event, "message": e.message,
             "timestamp": e.timestamp, "context": e.context}
            for e in self.entries
        ]

    def to_json(self) -> str:
        """Export all entries as a JSON string."""
        return json.dumps(self.to_list(), indent=2)
