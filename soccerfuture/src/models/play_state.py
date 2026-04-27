"""Data model for a soccer match situation at a decision point.

Defines the PlayState dataclass and serialization helpers for converting
between PlayState objects and JSON-serializable dicts.
"""

from dataclasses import asdict, dataclass, field

from src.models.branch import PlayerPosition


@dataclass
class PlayState:
    """Snapshot of a soccer match situation at a decision point.

    Attributes:
        match_time: Match time in minutes (0–90+).
        possession_team: Name of the team in possession.
        ball_position: Ball position as {"x": float, "y": float} in meters.
        game_phase: Current game phase (open_play | set_piece | transition | dead_ball).
        score_differential: Own score minus opponent score.
        game_clock: Seconds remaining in the match.
        player_positions: Player positions at the decision point.
        decision_point_timestamp: Seconds from play start anchoring divergence.
        player_roles: Mapping of player_id to role string (e.g. "GK", "ST").
        metadata: Optional additional context (formation, weather, etc.).
    """

    match_time: float
    possession_team: str
    ball_position: dict
    game_phase: str
    score_differential: int
    game_clock: float
    player_positions: list[PlayerPosition]
    decision_point_timestamp: float
    player_roles: dict[str, str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


def play_state_to_dict(ps: PlayState) -> dict:
    """Convert a PlayState to a JSON-serializable dict.

    Args:
        ps: The PlayState instance to serialize.

    Returns:
        A plain dict suitable for ``json.dumps``.
    """
    return asdict(ps)


def dict_to_play_state(data: dict) -> PlayState:
    """Reconstruct a PlayState from a JSON-deserialized dict.

    Nested ``player_positions`` entries are converted back into
    ``PlayerPosition`` objects.

    Args:
        data: A dict previously produced by ``play_state_to_dict`` or
            loaded from a JSON file.

    Returns:
        A fully reconstructed PlayState instance.

    Raises:
        KeyError: If required fields are missing from *data*.
    """
    required_fields = [
        "match_time",
        "possession_team",
        "ball_position",
        "game_phase",
        "score_differential",
        "game_clock",
        "player_positions",
        "decision_point_timestamp",
    ]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise KeyError(
            f"Missing required PlayState fields: {', '.join(missing)}"
        )

    player_positions = [
        PlayerPosition(**pp) if isinstance(pp, dict) else pp
        for pp in data["player_positions"]
    ]

    return PlayState(
        match_time=data["match_time"],
        possession_team=data["possession_team"],
        ball_position=data["ball_position"],
        game_phase=data["game_phase"],
        score_differential=data["score_differential"],
        game_clock=data["game_clock"],
        player_positions=player_positions,
        decision_point_timestamp=data["decision_point_timestamp"],
        player_roles=data.get("player_roles", {}),
        metadata=data.get("metadata", {}),
    )
