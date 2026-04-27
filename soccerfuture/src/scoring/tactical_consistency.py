"""Tactical consistency scoring module for the simulation evaluator.

Scores whether players maintain role-consistent behavior and whether
the overall formation shape is tactically coherent throughout a branch.
This module must NOT import from any other scoring module under
``src/scoring/``.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from src.utils.constants import (
    DEFENSIVE_DENSITY_RADIUS,
    EXPECTED_DEFENDERS_NEAR_BALL,
    FIELD_WIDTH,
    IDEAL_COMPACTNESS_RATIO,
    MAX_FORMATION_AREA,
    MAX_LINE_GAP_VARIANCE,
)


@dataclass
class TacticalConsistencyResult:
    """Result of tactical consistency scoring for a branch.

    Attributes:
        consistency_score: Aggregate consistency in [0, 1], weighted
            average of all five sub-metrics (role, formation, compactness,
            defensive density, formation shape).
        role_consistency_score: Sub-metric measuring how well players
            behave according to their assigned roles, in [0, 1].
        formation_coherence_score: Sub-metric measuring whether the
            overall formation shape is maintained (players don't
            cluster or spread excessively), in [0, 1].
        compactness_score: Sub-metric measuring how tight or spread
            the team formation is relative to the play context, in [0, 1].
        defensive_density_score: Sub-metric measuring concentration of
            defensive players around key attacking players, in [0, 1].
        formation_shape_score: Sub-metric measuring whether players
            maintain the tactical formation shape (e.g. 4-3-3, 4-4-2,
            3-5-2), in [0, 1].
    """

    consistency_score: float
    role_consistency_score: float
    formation_coherence_score: float
    compactness_score: float
    defensive_density_score: float
    formation_shape_score: float


# ---------------------------------------------------------------------------
# Constants for role-based position expectations
# ---------------------------------------------------------------------------

# Expected positional zones per role.  Each entry maps a role string to
# a dict with ``x_min``, ``x_max``, ``y_min``, ``y_max`` constraints
# (in meters).
#
# Coordinate system:
#   x: 0 = left sideline, FIELD_WIDTH (68m) = right sideline
#   y: 0 = own goal line, FIELD_LENGTH (105m) = opponent goal line

_HALF_WIDTH: float = FIELD_WIDTH / 2.0
_EDGE_THRESHOLD: float = FIELD_WIDTH * 0.2  # outer 20% on each side

_ROLE_ZONES: dict[str, dict[str, float | None]] = {
    # GK — goalkeeper, near own goal
    "GK": {"x_min": 24.0, "x_max": 44.0, "y_min": 0.0, "y_max": 10.0},
    # CB — centre-back, central defensive zone
    "CB": {"x_min": 14.0, "x_max": 54.0, "y_min": 0.0, "y_max": 35.0},
    # LB — left-back, left flank
    "LB": {"x_min": 0.0, "x_max": 20.0, "y_min": 0.0, "y_max": 60.0},
    # RB — right-back, right flank
    "RB": {"x_min": 48.0, "x_max": 68.0, "y_min": 0.0, "y_max": 60.0},
    # CDM — central defensive midfielder
    "CDM": {"x_min": 20.0, "x_max": 48.0, "y_min": 25.0, "y_max": 55.0},
    # CM — central midfielder, box-to-box
    "CM": {"x_min": 14.0, "x_max": 54.0, "y_min": 20.0, "y_max": 70.0},
    # CAM — central attacking midfielder
    "CAM": {"x_min": 14.0, "x_max": 54.0, "y_min": 45.0, "y_max": 85.0},
    # LW — left winger, left offensive flank
    "LW": {"x_min": 0.0, "x_max": 25.0, "y_min": 50.0, "y_max": 105.0},
    # RW — right winger, right offensive flank
    "RW": {"x_min": 43.0, "x_max": 68.0, "y_min": 50.0, "y_max": 105.0},
    # ST — striker, attacking zone
    "ST": {"x_min": 14.0, "x_max": 54.0, "y_min": 65.0, "y_max": 105.0},
}

# Ideal pairwise distance range for formation coherence.
_MIN_PAIRWISE_DISTANCE: float = 1.0   # meters — below this players are clustered
_MAX_PAIRWISE_DISTANCE: float = 40.0  # meters — above this formation is too spread


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to [*lo*, *hi*], replacing NaN/Inf with 0.0."""
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return max(lo, min(hi, value))


def _is_edge_position(x: float) -> bool:
    """Return True if *x* is in the outer edge zone of the field.

    Note: Retained for potential future use but no longer used by
    soccer role zone checks which use explicit x/y bounds.
    """
    return x < _EDGE_THRESHOLD or x > (FIELD_WIDTH - _EDGE_THRESHOLD)


def _check_role_violation(role: str, x: float, y: float) -> bool:
    """Return True if the position violates the expected zone for *role*.

    Args:
        role: Player role string (e.g. "GK", "CB", "ST").
        x: Horizontal position in meters.
        y: Vertical position in meters.

    Returns:
        True if the position is inconsistent with the role.
    """
    zone = _ROLE_ZONES.get(role)
    if zone is None:
        # Unknown role — no constraint, no violation
        return False

    # Zone-based roles: check x bounds
    x_min = zone.get("x_min")
    x_max = zone.get("x_max")
    if x_min is not None and x < x_min:
        return True
    if x_max is not None and x > x_max:
        return True

    y_min = zone.get("y_min")
    y_max = zone.get("y_max")
    if y_min is not None and y < y_min:
        return True
    if y_max is not None and y > y_max:
        return True

    return False


def _compute_role_consistency(
    positions: list[dict],
    player_roles: dict[str, str],
) -> float:
    """Compute role consistency score.

    For each player position, check whether it is consistent with the
    player's assigned role.  Score = 1.0 - (violations / total_checks),
    clamped to [0, 1].

    Args:
        positions: List of position dicts with ``player_id``, ``x``,
            ``y``, ``timestamp``.
        player_roles: Mapping of player_id to role string.

    Returns:
        Role consistency score in [0, 1].
    """
    if not positions or not player_roles:
        return 1.0  # nothing to violate

    total_checks = 0
    violations = 0

    for pos in positions:
        pid = pos.get("player_id", "")
        role = player_roles.get(pid)
        if role is None:
            continue  # player has no assigned role — skip

        x = pos.get("x", 0.0)
        y = pos.get("y", 0.0)
        total_checks += 1
        if _check_role_violation(role, x, y):
            violations += 1

    if total_checks == 0:
        return 1.0

    score = 1.0 - (violations / total_checks)
    return _clamp(score)


def _compute_formation_coherence(positions: list[dict]) -> float:
    """Compute formation coherence score from pairwise distances.

    Takes the latest position snapshot (latest timestamp per player),
    computes all pairwise distances, and scores based on how many
    pairs fall within the ideal distance range.

    Args:
        positions: List of position dicts.

    Returns:
        Formation coherence score in [0, 1].
    """
    if not positions:
        return 1.0

    # Get latest position per player
    latest: dict[str, dict] = {}
    for pos in positions:
        pid = pos.get("player_id", "unknown")
        ts = pos.get("timestamp", 0.0)
        if pid not in latest or ts > latest[pid].get("timestamp", 0.0):
            latest[pid] = pos

    players = list(latest.values())
    if len(players) < 2:
        return 1.0  # single player — formation is trivially coherent

    # Compute pairwise distances
    total_pairs = 0
    good_pairs = 0

    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            dx = players[i].get("x", 0.0) - players[j].get("x", 0.0)
            dy = players[i].get("y", 0.0) - players[j].get("y", 0.0)
            dist = math.sqrt(dx * dx + dy * dy)
            total_pairs += 1
            if _MIN_PAIRWISE_DISTANCE <= dist <= _MAX_PAIRWISE_DISTANCE:
                good_pairs += 1

    if total_pairs == 0:
        return 1.0

    return _clamp(good_pairs / total_pairs)


def _get_latest_snapshot(positions: list[dict]) -> dict[str, dict]:
    """Return the latest position per player from a positions list."""
    latest: dict[str, dict] = {}
    for pos in positions:
        pid = pos.get("player_id", "unknown")
        ts = pos.get("timestamp", 0.0)
        if pid not in latest or ts > latest[pid].get("timestamp", 0.0):
            latest[pid] = pos
    return latest


def _compute_compactness(positions: list[dict]) -> float:
    """Compute formation compactness from bounding box area.

    Takes the latest position snapshot, computes the bounding box area,
    and normalizes against ``MAX_FORMATION_AREA``. Formations using
    ≤ ``IDEAL_COMPACTNESS_RATIO`` of max area score 1.0; larger
    formations score proportionally lower.

    Args:
        positions: List of position dicts with ``player_id``, ``x``,
            ``y``, ``timestamp``.

    Returns:
        Compactness score in [0, 1]. Returns 1.0 for single player
        or empty positions.
    """
    if not positions:
        return 1.0

    latest = _get_latest_snapshot(positions)
    players = list(latest.values())
    if len(players) < 2:
        return 1.0

    xs = [p.get("x", 0.0) for p in players]
    ys = [p.get("y", 0.0) for p in players]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    area = width * height

    raw = area / MAX_FORMATION_AREA
    if raw <= IDEAL_COMPACTNESS_RATIO:
        return 1.0

    score = 1.0 - ((raw - IDEAL_COMPACTNESS_RATIO) / (1.0 - IDEAL_COMPACTNESS_RATIO))
    return _clamp(score)


def _compute_defensive_density(
    positions: list[dict],
    player_roles: dict[str, str],
    events: list[dict],
) -> float:
    """Compute defensive density around the key attacking player.

    Identifies the ball carrier from events or falls back to the ST
    (striker), counts defensive players (CB, LB, RB, CDM) within
    ``DEFENSIVE_DENSITY_RADIUS`` meters, and normalizes by
    ``EXPECTED_DEFENDERS_NEAR_BALL``.

    Args:
        positions: List of position dicts.
        player_roles: Mapping of player_id to role string.
        events: List of event dicts with ``event_type``, ``timestamp``,
            ``player_id``.

    Returns:
        Defensive density score in [0, 1]. Returns 0.5 if no
        defensive players exist.
    """
    if not positions or not player_roles:
        return 0.5

    latest = _get_latest_snapshot(positions)

    # Identify key attacking player: prefer ball carrier from events,
    # fall back to ST (striker).
    key_player_id: str | None = None
    ball_carrier_events = {"dribble", "pass_received", "reception"}
    for event in events:
        etype = event.get("event_type", "")
        if etype in ball_carrier_events:
            pid = event.get("player_id")
            if pid and pid in latest:
                key_player_id = pid
                break

    if key_player_id is None:
        # Fall back to ST (striker)
        for pid, role in player_roles.items():
            if role == "ST" and pid in latest:
                key_player_id = pid
                break

    if key_player_id is None or key_player_id not in latest:
        return 0.5

    key_pos = latest[key_player_id]
    key_x = key_pos.get("x", 0.0)
    key_y = key_pos.get("y", 0.0)

    # Identify defensive players and count those within radius
    defensive_roles = {"CB", "LB", "RB", "CDM"}
    defenders_within = 0
    has_defenders = False

    for pid, role in player_roles.items():
        if role not in defensive_roles:
            continue
        if pid not in latest:
            continue
        has_defenders = True
        pos = latest[pid]
        dx = pos.get("x", 0.0) - key_x
        dy = pos.get("y", 0.0) - key_y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist <= DEFENSIVE_DENSITY_RADIUS:
            defenders_within += 1

    if not has_defenders:
        return 0.5

    score = min(1.0, defenders_within / EXPECTED_DEFENDERS_NEAR_BALL)
    return _clamp(score)


def _compute_formation_shape(
    positions: list[dict],
    player_roles: dict[str, str],
) -> float:
    """Compute formation shape score from defensive and midfield line gap variance.

    Separates defensive-line players (CB, LB, RB) and midfield-line
    players (CDM, CM, CAM), sorts each group by x-coordinate, computes
    consecutive x-gap variance, and scores based on how uniform the
    gaps are.  Uniform gaps indicate the formation shape (e.g. 4-3-3,
    4-4-2) is being maintained.

    Args:
        positions: List of position dicts.
        player_roles: Mapping of player_id to role string.

    Returns:
        Formation shape score in [0, 1]. Returns 1.0 if neither
        defensive nor midfield line has ≥2 players.
    """
    if not positions or not player_roles:
        return 1.0

    latest = _get_latest_snapshot(positions)

    def_xs: list[float] = []
    mid_xs: list[float] = []

    for pid, role in player_roles.items():
        if pid not in latest:
            continue
        x = latest[pid].get("x", 0.0)
        if role in {"CB", "LB", "RB"}:
            def_xs.append(x)
        elif role in {"CDM", "CM", "CAM"}:
            mid_xs.append(x)

    def _gap_variance_score(xs: list[float]) -> float | None:
        if len(xs) < 2:
            return None
        xs_sorted = sorted(xs)
        gaps = [xs_sorted[i + 1] - xs_sorted[i] for i in range(len(xs_sorted) - 1)]
        n = len(gaps)
        mean_gap = sum(gaps) / n
        variance = sum((g - mean_gap) ** 2 for g in gaps) / n
        return _clamp(1.0 - min(1.0, variance / MAX_LINE_GAP_VARIANCE))

    def_score = _gap_variance_score(def_xs)
    mid_score = _gap_variance_score(mid_xs)

    if def_score is not None and mid_score is not None:
        return _clamp((def_score + mid_score) / 2.0)
    if def_score is not None:
        return def_score
    if mid_score is not None:
        return mid_score
    return 1.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_tactical_consistency(
    aligned_branch: dict,
) -> TacticalConsistencyResult:
    """Score tactical consistency of player roles, formations, and spatial metrics.

    v3 additions: compactness_score, defensive_density_score, formation_shape_score.
    The aggregate consistency_score is a weighted average of all five sub-metrics.

    Sub-score computation:
      - **role_consistency_score**: For each player position, check if
        the position is consistent with the player's assigned role.
      - **formation_coherence_score**: Check if the overall formation
        shape is maintained by evaluating pairwise distances.
      - **compactness_score**: Bounding box compactness of the formation.
      - **defensive_density_score**: Defenders near ball carrier / ST.
      - **formation_shape_score**: Defensive/midfield line gap variance uniformity.

    Aggregate: ``0.25 * role + 0.20 * formation + 0.20 * compactness
    + 0.20 * density + 0.15 * formation_shape``.

    Args:
        aligned_branch: Aligned branch data. Expected keys:
            ``positions``, ``player_roles``, ``events`` (for ball
            carrier detection).

    Returns:
        TacticalConsistencyResult with aggregate and per-dimension
        scores, all clamped to [0.0, 1.0].
    """
    positions: list[dict] = aligned_branch.get("positions", [])
    player_roles: dict[str, str] = aligned_branch.get("player_roles", {})
    events: list[dict] = aligned_branch.get("events", [])

    role_score = _compute_role_consistency(positions, player_roles)
    formation_score = _compute_formation_coherence(positions)
    compactness_score = _compute_compactness(positions)
    density_score = _compute_defensive_density(positions, player_roles, events)
    shape_score = _compute_formation_shape(positions, player_roles)

    consistency_score = _clamp(
        0.25 * role_score
        + 0.20 * formation_score
        + 0.20 * compactness_score
        + 0.20 * density_score
        + 0.15 * shape_score
    )

    return TacticalConsistencyResult(
        consistency_score=consistency_score,
        role_consistency_score=_clamp(role_score),
        formation_coherence_score=_clamp(formation_score),
        compactness_score=_clamp(compactness_score),
        defensive_density_score=_clamp(density_score),
        formation_shape_score=_clamp(shape_score),
    )
