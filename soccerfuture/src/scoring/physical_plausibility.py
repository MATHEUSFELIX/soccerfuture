"""Physical plausibility scoring module for the simulation evaluator.

Scores whether player movements in a branch obey physical constraints
(speed limits, acceleration bounds).  Teleportation-like movements
receive a score of 0.0.  This module must NOT import from any other
scoring module under ``src/scoring/``.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from src.utils.constants import (
    MAX_ACCELERATION,
    MAX_DECELERATION,
    MAX_HUMAN_SPRINT_SPEED,
)


@dataclass
class PhysicalPlausibilityResult:
    """Result of physical plausibility scoring for a branch.

    Attributes:
        plausibility_score: Aggregate plausibility in [0, 1], computed
            as the average of the three sub-scores.
        speed_score: Sub-metric for speed plausibility in [0, 1].
        acceleration_score: Sub-metric for acceleration plausibility
            in [0, 1].
        deceleration_score: Sub-metric for deceleration plausibility
            in [0, 1].
    """

    plausibility_score: float
    speed_score: float
    acceleration_score: float
    deceleration_score: float


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to [*lo*, *hi*], replacing NaN with 0.0."""
    if math.isnan(value):
        return 0.0
    return max(lo, min(hi, value))


def _compute_player_kinematics(
    sorted_positions: list[dict],
) -> tuple[list[float], list[float]]:
    """Compute per-segment speeds and accelerations for one player.

    Args:
        sorted_positions: Positions for a single player, already sorted
            by timestamp.

    Returns:
        Tuple of ``(speeds, accelerations)`` where each list has one
        entry per consecutive-frame pair (speeds) or consecutive-speed
        pair (accelerations).  Segments with zero or negative dt are
        skipped.
    """
    speeds: list[float] = []
    for i in range(1, len(sorted_positions)):
        prev = sorted_positions[i - 1]
        curr = sorted_positions[i]
        dt = curr.get("timestamp", 0.0) - prev.get("timestamp", 0.0)
        if dt <= 0:
            continue
        dx = curr.get("x", 0.0) - prev.get("x", 0.0)
        dy = curr.get("y", 0.0) - prev.get("y", 0.0)
        distance = math.sqrt(dx * dx + dy * dy)
        speeds.append(distance / dt)

    accelerations: list[float] = []
    # We need timestamps between consecutive speed measurements.
    # Speed i corresponds to the interval [pos_i, pos_{i+1}].
    # Use the midpoint timestamp of each interval for acceleration calc.
    mid_timestamps: list[float] = []
    seg_idx = 0
    for i in range(1, len(sorted_positions)):
        prev = sorted_positions[i - 1]
        curr = sorted_positions[i]
        dt = curr.get("timestamp", 0.0) - prev.get("timestamp", 0.0)
        if dt <= 0:
            continue
        mid_ts = (prev.get("timestamp", 0.0) + curr.get("timestamp", 0.0)) / 2.0
        mid_timestamps.append(mid_ts)
        seg_idx += 1

    for i in range(1, len(speeds)):
        dt_mid = mid_timestamps[i] - mid_timestamps[i - 1]
        if dt_mid <= 0:
            continue
        accelerations.append((speeds[i] - speeds[i - 1]) / dt_mid)

    return speeds, accelerations


def score_physical_plausibility(
    aligned_branch: dict,
) -> PhysicalPlausibilityResult:
    """Score physical plausibility of player movements.

    Evaluates speed, acceleration, and deceleration against configurable
    thresholds from ``src/utils/constants.py``.  Teleportation-like
    movements (displacement exceeding the maximum physically possible
    for the elapsed time) receive 0.0.

    Scoring logic per player:
      - **speed_score**: ``1.0 - (max_speed / MAX_HUMAN_SPRINT_SPEED)``,
        clamped to [0, 1].  If any segment exhibits teleportation
        (speed > MAX_HUMAN_SPRINT_SPEED), that player's speed score
        is 0.0.
      - **acceleration_score**: ``1.0 - (max_accel / MAX_ACCELERATION)``,
        clamped to [0, 1].
      - **deceleration_score**: ``1.0 - (max_decel / MAX_DECELERATION)``,
        clamped to [0, 1].

    The branch-level sub-scores are the averages across all players.
    The aggregate ``plausibility_score`` is the average of the three
    sub-scores.

    Stationary players (no movement) score 1.0 on all dimensions.

    Args:
        aligned_branch: Temporally/spatially aligned branch data.
            Must contain a ``positions`` key with a list of position
            dicts having ``player_id``, ``x``, ``y``, ``timestamp``.

    Returns:
        PhysicalPlausibilityResult with aggregate and per-dimension
        scores, all clamped to [0.0, 1.0].
    """
    positions: list[dict] = aligned_branch.get("positions", [])

    # Group positions by player_id
    by_player: dict[str, list[dict]] = defaultdict(list)
    for pos in positions:
        by_player[pos.get("player_id", "unknown")].append(pos)

    if not by_player:
        # No positions at all — treat as perfectly plausible (nothing to violate)
        return PhysicalPlausibilityResult(
            plausibility_score=1.0,
            speed_score=1.0,
            acceleration_score=1.0,
            deceleration_score=1.0,
        )

    player_speed_scores: list[float] = []
    player_accel_scores: list[float] = []
    player_decel_scores: list[float] = []

    for player_id, player_positions in by_player.items():
        sorted_pos = sorted(
            player_positions, key=lambda p: p.get("timestamp", 0.0)
        )
        speeds, accelerations = _compute_player_kinematics(sorted_pos)

        # --- Speed score ---
        if not speeds:
            # Stationary or single-frame player
            player_speed_scores.append(1.0)
        else:
            max_speed = max(speeds)
            # Teleportation check: if any speed exceeds the threshold
            has_teleportation = any(
                s > MAX_HUMAN_SPRINT_SPEED for s in speeds
            )
            if has_teleportation:
                player_speed_scores.append(0.0)
            else:
                # Quadratic curve: moderate speeds (7-9 m/s) are common
                # in soccer and shouldn't be heavily penalised.
                # Linear was too harsh: 8 m/s → 0.20.
                # Quadratic: 8 m/s → 0.38, 5 m/s → 0.72, 9.5 m/s → 0.13.
                ratio = max_speed / MAX_HUMAN_SPRINT_SPEED
                score = (1.0 - ratio) ** 0.6
                player_speed_scores.append(_clamp(score))

        # --- Acceleration / deceleration scores ---
        if not accelerations:
            player_accel_scores.append(1.0)
            player_decel_scores.append(1.0)
        else:
            # Positive acceleration values
            pos_accels = [a for a in accelerations if a > 0]
            # Negative acceleration values (deceleration magnitude)
            neg_accels = [abs(a) for a in accelerations if a < 0]

            if pos_accels:
                max_accel = max(pos_accels)
                accel_score = 1.0 - (max_accel / MAX_ACCELERATION)
                player_accel_scores.append(_clamp(accel_score))
            else:
                player_accel_scores.append(1.0)

            if neg_accels:
                max_decel = max(neg_accels)
                decel_score = 1.0 - (max_decel / MAX_DECELERATION)
                player_decel_scores.append(_clamp(decel_score))
            else:
                player_decel_scores.append(1.0)

    # Branch-level scores: average across players
    speed_score = _clamp(
        sum(player_speed_scores) / len(player_speed_scores)
    )
    acceleration_score = _clamp(
        sum(player_accel_scores) / len(player_accel_scores)
    )
    deceleration_score = _clamp(
        sum(player_decel_scores) / len(player_decel_scores)
    )

    plausibility_score = _clamp(
        (speed_score + acceleration_score + deceleration_score) / 3.0
    )

    return PhysicalPlausibilityResult(
        plausibility_score=plausibility_score,
        speed_score=speed_score,
        acceleration_score=acceleration_score,
        deceleration_score=deceleration_score,
    )
