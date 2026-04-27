"""Domain models for match context data.

Defines dataclasses for team metrics, comparative signals, context signals,
and the top-level MatchContext. Includes serialization helpers for
JSON round-tripping.
"""

from dataclasses import asdict, dataclass, field


@dataclass
class TeamContextMetrics:
    """Aggregated performance metrics for a single team over recent matches.

    Attributes:
        matches_sampled: Number of matches used to compute the metrics.
        wins: Total wins in the sample.
        draws: Total draws in the sample.
        losses: Total losses in the sample.
        goals_for_avg: Average goals scored per match.
        goals_against_avg: Average goals conceded per match.
        xg_for_avg: Average expected goals created per match.
        xg_against_avg: Average expected goals conceded per match.
        form_points: Points accumulated over the form window.
        elo: Current Elo rating estimate.
        style_tags: Descriptive style labels (e.g. "high-press", "counter").
    """

    matches_sampled: int
    wins: int
    draws: int
    losses: int
    goals_for_avg: float | None = None
    goals_against_avg: float | None = None
    xg_for_avg: float | None = None
    xg_against_avg: float | None = None
    form_points: int | None = None
    elo: float | None = None
    style_tags: list[str] = field(default_factory=list)


@dataclass
class ComparativeSignals:
    """Head-to-head comparative edges between the two teams.

    Attributes:
        stronger_team: Name of the team judged stronger overall, or None.
        form_edge: Name of the team with better recent form, or None.
        attack_edge: Name of the team with the attacking advantage, or None.
        defense_edge: Name of the team with the defensive advantage, or None.
        notes: Free-text analyst notes about the comparison.
    """

    stronger_team: str | None = None
    form_edge: str | None = None
    attack_edge: str | None = None
    defense_edge: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class ContextSignals:
    """Derived tactical signals that inform branch evaluation adjustments.

    Attributes:
        aggression_bias: Expected aggression level shift (-1 to 1).
        risk_tolerance: Expected risk-taking shift (-1 to 1).
        retention_bias: Expected ball-retention preference shift (-1 to 1).
        likely_game_state_pressure: Pressure level from game state (0 to 1).
        notes: Free-text notes explaining signal derivation.
    """

    aggression_bias: float = 0.0
    risk_tolerance: float = 0.0
    retention_bias: float = 0.0
    likely_game_state_pressure: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class MatchContext:
    """Top-level container for pre-match context between two teams.

    Attributes:
        home_team: Name of the home team.
        away_team: Name of the away team.
        lookback_matches: Number of historical matches considered.
        source: Data source identifier (e.g. "soccerdata").
        cache_status: Cache status string ("hit", "miss", "bypass").
        home_metrics: Aggregated metrics for the home team.
        away_metrics: Aggregated metrics for the away team.
        comparative_signals: Head-to-head comparative edges.
        competition: Competition name, if available.
        season: Season identifier, if available.
        fetched_at: ISO-8601 timestamp of when data was fetched.
    """

    home_team: str
    away_team: str
    lookback_matches: int
    source: str
    cache_status: str
    home_metrics: TeamContextMetrics
    away_metrics: TeamContextMetrics
    comparative_signals: ComparativeSignals
    competition: str | None = None
    season: str | None = None
    fetched_at: str | None = None


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def match_context_to_dict(ctx: MatchContext) -> dict:
    """Convert a MatchContext to a JSON-serializable dict.

    Args:
        ctx: The MatchContext instance to serialize.

    Returns:
        A plain dict suitable for ``json.dumps``.
    """
    return asdict(ctx)


def dict_to_match_context(data: dict) -> MatchContext:
    """Reconstruct a MatchContext from a JSON-deserialized dict.

    Args:
        data: A dict previously produced by ``match_context_to_dict``
            or loaded from a JSON file.

    Returns:
        A fully reconstructed MatchContext instance.

    Raises:
        KeyError: If any required field is missing from *data*.
        TypeError: If nested fields (home_metrics, away_metrics,
            comparative_signals) are not dicts.
    """
    required_fields = [
        "home_team",
        "away_team",
        "lookback_matches",
        "source",
        "cache_status",
        "home_metrics",
        "away_metrics",
        "comparative_signals",
    ]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise KeyError(
            f"Missing required MatchContext fields: {', '.join(missing)}"
        )

    home_raw = data["home_metrics"]
    away_raw = data["away_metrics"]
    comp_raw = data["comparative_signals"]

    if not isinstance(home_raw, dict):
        raise TypeError(
            f"home_metrics must be a dict, got {type(home_raw).__name__}"
        )
    if not isinstance(away_raw, dict):
        raise TypeError(
            f"away_metrics must be a dict, got {type(away_raw).__name__}"
        )
    if not isinstance(comp_raw, dict):
        raise TypeError(
            f"comparative_signals must be a dict, got {type(comp_raw).__name__}"
        )

    home_metrics = TeamContextMetrics(**home_raw)
    away_metrics = TeamContextMetrics(**away_raw)
    comparative_signals = ComparativeSignals(**comp_raw)

    return MatchContext(
        home_team=data["home_team"],
        away_team=data["away_team"],
        lookback_matches=data["lookback_matches"],
        source=data["source"],
        cache_status=data["cache_status"],
        home_metrics=home_metrics,
        away_metrics=away_metrics,
        comparative_signals=comparative_signals,
        competition=data.get("competition"),
        season=data.get("season"),
        fetched_at=data.get("fetched_at"),
    )


def context_signals_to_dict(signals: ContextSignals) -> dict:
    """Convert a ContextSignals instance to a JSON-serializable dict.

    Args:
        signals: The ContextSignals instance to serialize.

    Returns:
        A plain dict suitable for ``json.dumps``.
    """
    return asdict(signals)


def dict_to_context_signals(data: dict) -> ContextSignals:
    """Reconstruct a ContextSignals from a JSON-deserialized dict.

    Missing optional fields fall back to their dataclass defaults.

    Args:
        data: A dict previously produced by ``context_signals_to_dict``
            or loaded from a JSON file.

    Returns:
        A reconstructed ContextSignals instance.
    """
    return ContextSignals(
        aggression_bias=data.get("aggression_bias", 0.0),
        risk_tolerance=data.get("risk_tolerance", 0.0),
        retention_bias=data.get("retention_bias", 0.0),
        likely_game_state_pressure=data.get("likely_game_state_pressure", 0.0),
        notes=data.get("notes", []),
    )
