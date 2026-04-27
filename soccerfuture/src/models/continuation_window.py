"""Data model for continuation windows.

Defines the real-world continuation data that branches are compared against.
JSON-serializable via ``dataclasses.asdict()``.
"""

from dataclasses import dataclass, field


@dataclass
class ContinuationWindow:
    """The set of plausible real-world outcomes from a decision point.

    Attributes:
        window_id: Unique identifier for this continuation window.
        decision_point_timestamp: Time in seconds from play start where the
            window originates.
        outcomes: List of observed real-world outcome snapshots, each
            represented as a plain dictionary.
        metadata: Additional window-level information.
    """

    window_id: str
    decision_point_timestamp: float
    outcomes: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
