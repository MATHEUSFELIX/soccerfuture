"""Data models for simulation branches.

Defines the core input data structures representing a simulated play branch,
including player positions, event markers, and the branch container itself.
All models are JSON-serializable via ``dataclasses.asdict()``.
"""

from dataclasses import dataclass, field


@dataclass
class PlayerPosition:
    """A single player's position at a point in time.

    Attributes:
        player_id: Unique identifier for the player.
        x: Horizontal position in meters across the field width (0–68m).
        y: Vertical position in meters along the field length (0–105m).
        timestamp: Time in seconds from play start.
    """

    player_id: str
    x: float
    y: float
    timestamp: float


@dataclass
class EventMarker:
    """A discrete event that occurred during a branch.

    Attributes:
        event_type: Type of event, e.g. "pass", "shot", "dribble", "tackle",
            "interception", "goal", "foul", "cross", "header", "save",
            "clearance", "dispossession".
        timestamp: Time in seconds from play start when the event occurred.
        player_id: Unique identifier of the player involved.
        metadata: Event-specific key-value pairs.
    """

    event_type: str
    timestamp: float
    player_id: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Branch:
    """A simulated continuation of a real soccer play from a decision point.

    Attributes:
        branch_id: Unique identifier for this branch.
        decision_point_timestamp: Time in seconds from play start where the
            branch diverges from reality.
        positions: Ordered list of player positions throughout the branch.
        events: List of event markers that occurred during the branch.
        player_roles: Mapping of player_id to role (e.g. "ST", "CM", "GK").
        metadata: Additional branch-level information.
    """

    branch_id: str
    decision_point_timestamp: float
    positions: list[PlayerPosition] = field(default_factory=list)
    events: list[EventMarker] = field(default_factory=list)
    player_roles: dict[str, str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
