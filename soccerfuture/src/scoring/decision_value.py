"""Decision value scoring module for the simulation evaluator.

Quantifies the tactical opportunity a branch represents relative to
the real continuation window.  Branches worse than reality on all
dimensions receive an opportunity_score below 0.5.  All scoring is
deterministic and rule-based with no ML dependencies.  This module
must NOT import from any other scoring module under ``src/scoring/``.

All distances are in meters and positions use the FIFA standard
soccer field coordinate system (105 m × 68 m).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.utils.constants import FIELD_LENGTH


@dataclass
class DecisionValueResult:
    """Result of decision value scoring for a branch.

    Attributes:
        opportunity_score: Aggregate opportunity in [0, 1], weighted
            average of the three sub-metrics.
        ball_progression: Sub-metric comparing branch expected
            forward progress (in meters toward the opponent goal)
            against the window average, normalised to [0, 1].
        turnover_risk_delta: Sub-metric comparing branch turnover risk
            against the window turnover rate, normalised to [0, 1].
        scoring_probability_delta: Sub-metric comparing branch scoring
            probability against the window, normalised to [0, 1].
    """

    opportunity_score: float
    ball_progression: float
    turnover_risk_delta: float
    scoring_probability_delta: float


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum meter range used for normalisation.  A full soccer field
# length (105 m) is the theoretical maximum progression on a single play.
_MAX_METER_RANGE: float = 105.0

# Weights for the three sub-metrics in the aggregate opportunity score.
_WEIGHT_BALL_PROGRESSION: float = 0.3
_WEIGHT_TURNOVER: float = 0.5
_WEIGHT_SCORING: float = 0.2


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to [*lo*, *hi*], replacing NaN/Inf with 0.0."""
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return max(lo, min(hi, value))


def _estimate_branch_ball_progression(aligned_branch: dict) -> float:
    """Estimate the branch's expected ball progression from player positions.

    Uses the difference between the average final y-position and the
    average initial y-position of all players as a proxy for forward
    progress toward the opponent goal (in meters).

    Args:
        aligned_branch: Aligned branch data with ``positions``.

    Returns:
        Estimated ball progression in meters (can be negative for
        backward movement).
    """
    positions: list[dict] = aligned_branch.get("positions", [])
    if not positions:
        return 0.0

    # Group positions by player, find earliest and latest per player
    earliest: dict[str, dict] = {}
    latest: dict[str, dict] = {}

    for pos in positions:
        pid = pos.get("player_id", "unknown")
        ts = pos.get("timestamp", 0.0)

        if pid not in earliest or ts < earliest[pid].get("timestamp", float("inf")):
            earliest[pid] = pos
        if pid not in latest or ts > latest[pid].get("timestamp", float("-inf")):
            latest[pid] = pos

    if not earliest:
        return 0.0

    # Average y-displacement across all players
    total_dy = 0.0
    count = 0
    for pid in earliest:
        if pid in latest:
            dy = latest[pid].get("y", 0.0) - earliest[pid].get("y", 0.0)
            total_dy += dy
            count += 1

    if count == 0:
        return 0.0

    return total_dy / count


def _estimate_branch_turnover_risk(aligned_branch: dict) -> float:
    """Estimate the branch's turnover risk from events.

    Looks for turnover-related events (interception, dispossession)
    in the branch events.  Returns a probability in [0, 1].

    Args:
        aligned_branch: Aligned branch data with ``events``.

    Returns:
        Estimated turnover probability in [0, 1].
    """
    events: list[dict] = aligned_branch.get("events", [])
    if not events:
        return 0.0

    turnover_types = {"interception", "dispossession"}
    turnover_count = sum(
        1 for e in events
        if e.get("event_type", "").lower() in turnover_types
    )

    # A single turnover is catastrophic — scale aggressively.
    # 1 turnover → 0.8, 2+ → 1.0
    if turnover_count == 0:
        return 0.0
    return _clamp(0.5 + 0.3 * turnover_count)


def _estimate_branch_scoring_probability(aligned_branch: dict) -> float:
    """Estimate the branch's scoring probability from events and positions.

    Looks for scoring events (goal) or positions near the opponent
    goal line (y close to 105 m).

    Args:
        aligned_branch: Aligned branch data.

    Returns:
        Estimated scoring probability in [0, 1].
    """
    events: list[dict] = aligned_branch.get("events", [])
    positions: list[dict] = aligned_branch.get("positions", [])

    # Check for explicit scoring events
    scoring_types = {"goal"}
    has_scoring_event = any(
        e.get("event_type", "").lower() in scoring_types for e in events
    )
    if has_scoring_event:
        return 1.0

    # Estimate from final positions — how close to the opponent goal
    if not positions:
        return 0.0

    # Get latest positions per player
    latest: dict[str, dict] = {}
    for pos in positions:
        pid = pos.get("player_id", "unknown")
        ts = pos.get("timestamp", 0.0)
        if pid not in latest or ts > latest[pid].get("timestamp", float("-inf")):
            latest[pid] = pos

    if not latest:
        return 0.0

    # Average y-position relative to field length (105 m)
    avg_y = sum(p.get("y", 0.0) for p in latest.values()) / len(latest)
    # Closer to FIELD_LENGTH (105 m) = closer to scoring
    proximity = avg_y / FIELD_LENGTH if FIELD_LENGTH > 0 else 0.0
    return _clamp(proximity)


def _extract_window_outcomes(aligned_window: dict) -> list[dict]:
    """Extract outcome dicts from the aligned window.

    Args:
        aligned_window: Aligned continuation window data.

    Returns:
        List of outcome dicts.
    """
    return aligned_window.get("outcomes", [])


def _compute_window_avg_ball_progression(outcomes: list[dict]) -> float:
    """Compute the average ball progression across window outcomes.

    Args:
        outcomes: List of outcome dicts, each optionally containing
            a ``yard_gain`` field (meters of forward progress).

    Returns:
        Average ball progression in meters, or 0.0 if no data.
    """
    gains = [o.get("yard_gain", 0.0) for o in outcomes if "yard_gain" in o]
    if not gains:
        return 0.0
    return sum(gains) / len(gains)


def _compute_window_turnover_rate(outcomes: list[dict]) -> float:
    """Compute the turnover rate across window outcomes.

    Args:
        outcomes: List of outcome dicts, each optionally containing
            a ``turnover`` boolean field.

    Returns:
        Turnover rate in [0, 1], or 0.0 if no data.
    """
    turnover_flags = [o.get("turnover", False) for o in outcomes if "turnover" in o]
    if not turnover_flags:
        return 0.0
    return sum(1 for t in turnover_flags if t) / len(turnover_flags)


def _compute_window_scoring_rate(outcomes: list[dict]) -> float:
    """Compute the scoring rate across window outcomes.

    Args:
        outcomes: List of outcome dicts, each optionally containing
            a ``scoring_play`` boolean field.

    Returns:
        Scoring rate in [0, 1], or 0.0 if no data.
    """
    scoring_flags = [o.get("scoring_play", False) for o in outcomes if "scoring_play" in o]
    if not scoring_flags:
        return 0.0
    return sum(1 for s in scoring_flags if s) / len(scoring_flags)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_decision_value(
    aligned_branch: dict, aligned_window: dict,
) -> DecisionValueResult:
    """Score the tactical opportunity a branch represents.

    Compares branch expected outcomes against the real continuation
    window.  Branches worse than reality on all dimensions receive an
    ``opportunity_score`` below 0.5.  All scoring is deterministic and
    rule-based.

    Sub-score computation:
      - **ball_progression**: ``(branch_progression -
        window_avg_progression) / _MAX_METER_RANGE``, shifted and
        clamped to [0, 1] where 0.5 means equal to reality.
      - **turnover_risk_delta**: Compares branch turnover risk vs
        window turnover rate.  Lower branch risk → higher score.
        Normalised to [0, 1] where 0.5 means equal to reality.
      - **scoring_probability_delta**: Compares branch scoring
        probability vs window scoring rate.  Higher branch probability
        → higher score.  Normalised to [0, 1] where 0.5 means equal.
      - **opportunity_score**: Weighted average of the three sub-metrics
        (ball_progression 30%, turnover 50%, scoring 20%).

    Args:
        aligned_branch: Aligned branch data.  Expected keys:
            ``positions`` (list of dicts with ``player_id``, ``x``,
            ``y``, ``timestamp``) and ``events`` (list of dicts with
            ``event_type``, ``timestamp``, ``player_id``, ``metadata``).
            Coordinates are in meters on a 105 m × 68 m soccer field.
        aligned_window: Aligned continuation window data.  Expected
            keys: ``outcomes`` (list of dicts with optional
            ``yard_gain``, ``turnover``, ``scoring_play`` fields).

    Returns:
        DecisionValueResult with aggregate and per-dimension scores,
        all clamped to [0.0, 1.0].
    """
    outcomes = _extract_window_outcomes(aligned_window)

    # --- Branch estimates ---
    branch_ball_progression = _estimate_branch_ball_progression(aligned_branch)
    branch_turnover_risk = _estimate_branch_turnover_risk(aligned_branch)
    branch_scoring_prob = _estimate_branch_scoring_probability(aligned_branch)

    # --- Window baselines ---
    window_avg_ball_progression = _compute_window_avg_ball_progression(outcomes)
    window_turnover_rate = _compute_window_turnover_rate(outcomes)
    window_scoring_rate = _compute_window_scoring_rate(outcomes)

    # --- Ball progression ---
    # Positive differential = branch progressed further toward goal than reality
    # Normalise to [0, 1] with 0.5 as the neutral point
    raw_progression_diff = branch_ball_progression - window_avg_ball_progression
    ball_progression = _clamp(0.5 + (raw_progression_diff / (2.0 * _MAX_METER_RANGE)))

    # --- Turnover risk delta ---
    # Lower branch turnover risk than window = better = higher score
    # delta = window_rate - branch_risk (positive means branch is safer)
    # Scale aggressively: a branch with turnovers should be heavily penalised
    turnover_delta = window_turnover_rate - branch_turnover_risk
    turnover_risk_delta = _clamp(0.5 + turnover_delta)

    # --- Scoring probability delta ---
    # Higher branch scoring probability than window = better = higher score
    scoring_delta = branch_scoring_prob - window_scoring_rate
    scoring_probability_delta = _clamp(0.5 + scoring_delta / 2.0)

    # --- Aggregate opportunity score ---
    opportunity_score = _clamp(
        _WEIGHT_BALL_PROGRESSION * ball_progression
        + _WEIGHT_TURNOVER * turnover_risk_delta
        + _WEIGHT_SCORING * scoring_probability_delta
    )

    return DecisionValueResult(
        opportunity_score=opportunity_score,
        ball_progression=ball_progression,
        turnover_risk_delta=turnover_risk_delta,
        scoring_probability_delta=scoring_probability_delta,
    )
