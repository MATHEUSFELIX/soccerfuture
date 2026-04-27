"""Gating module for the simulation evaluator.

Performs binary pass/fail checks that hard-reject physically impossible
branches before any scoring proceeds.  This module must NOT import from
any other scoring module under ``src/scoring/``.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from src.utils.constants import (
    CONTACT_EVENT_TYPES,
    CONTACT_SPEED_THRESHOLD,
    CONTACT_TIME_WINDOW,
    FIELD_LENGTH,
    FIELD_WIDTH,
    MAX_HUMAN_SPRINT_SPEED,
    MAX_TIMESTAMP_GAP,
)


@dataclass
class GatingResult:
    """Result of running all gating checks on a branch.

    Attributes:
        passed: True only when every gate flag is True.
        flags: Mapping of gate name to pass/fail boolean, e.g.
            ``{"field_bounds": True, "max_speed": False, ...}``.
        explanations: Human-readable failure reasons.  Non-empty only
            when ``passed`` is False.
    """

    passed: bool
    flags: dict[str, bool] = field(default_factory=dict)
    explanations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Individual gate implementations
# ---------------------------------------------------------------------------


def _check_field_bounds(positions: list[dict]) -> tuple[bool, list[str]]:
    """Check that all player positions are within field boundaries.

    Valid ranges:
        x: [0, FIELD_WIDTH]  (0 to 68.0 meters)
        y: [0, FIELD_LENGTH]  (0 to 105.0 meters)

    Args:
        positions: List of position dicts with keys ``x``, ``y``,
            ``player_id``, and ``timestamp``.

    Returns:
        Tuple of (passed, explanations).
    """
    explanations: list[str] = []
    for pos in positions:
        x = pos.get("x", 0.0)
        y = pos.get("y", 0.0)
        player_id = pos.get("player_id", "unknown")
        timestamp = pos.get("timestamp", 0.0)

        if x < 0 or x > FIELD_WIDTH:
            explanations.append(
                f"Player {player_id} at t={timestamp} has x={x} "
                f"outside field bounds [0, {FIELD_WIDTH}]"
            )
        if y < 0 or y > FIELD_LENGTH:
            explanations.append(
                f"Player {player_id} at t={timestamp} has y={y} "
                f"outside field bounds [0, {FIELD_LENGTH}]"
            )

    return (len(explanations) == 0, explanations)


def _has_contact_near(
    t_mid: float, events: list[dict] | None,
) -> bool:
    """Return True if a contact event exists within CONTACT_TIME_WINDOW of *t_mid*.

    Args:
        t_mid: Midpoint timestamp of the speed measurement.
        events: Branch event list (may be None or empty).

    Returns:
        True when at least one contact-type event is close enough.
    """
    if not events:
        return False
    for ev in events:
        ev_type = ev.get("event_type", "")
        ev_ts = ev.get("timestamp")
        if ev_ts is None:
            continue
        if ev_type in CONTACT_EVENT_TYPES and abs(ev_ts - t_mid) <= CONTACT_TIME_WINDOW:
            return True
    return False


def _check_max_speed(
    positions: list[dict], events: list[dict] | None = None,
) -> tuple[bool, list[str]]:
    """Check player speeds with context-aware thresholds.

    For each player speed measurement:
    1. Compute the midpoint timestamp ``t_mid = (t1 + t2) / 2``.
    2. Check if a contact event (tackle, foul, dispossession) exists
       within ``CONTACT_TIME_WINDOW`` seconds of *t_mid*.
    3. If contact context: apply ``CONTACT_SPEED_THRESHOLD``.
    4. If no contact context: apply ``MAX_HUMAN_SPRINT_SPEED`` (base).
    5. If speed exceeds the applicable threshold, fail with an explanation
       that includes the applied threshold and whether contact context was
       detected.

    Args:
        positions: List of position dicts with keys ``player_id``,
            ``x``, ``y``, and ``timestamp``.
        events: Optional list of event dicts with keys ``event_type``
            and ``timestamp``.  When *None* or empty, the base threshold
            is always used (v2-compatible behaviour).

    Returns:
        Tuple of (passed, explanations).
    """
    # Group positions by player_id
    by_player: dict[str, list[dict]] = defaultdict(list)
    for pos in positions:
        by_player[pos.get("player_id", "unknown")].append(pos)

    explanations: list[str] = []
    for player_id, player_positions in by_player.items():
        sorted_pos = sorted(player_positions, key=lambda p: p.get("timestamp", 0.0))
        for i in range(1, len(sorted_pos)):
            prev = sorted_pos[i - 1]
            curr = sorted_pos[i]

            t1 = prev.get("timestamp", 0.0)
            t2 = curr.get("timestamp", 0.0)
            dt = t2 - t1
            if dt <= 0:
                # Zero or negative time delta — handled by temporal gate
                continue

            dx = curr.get("x", 0.0) - prev.get("x", 0.0)
            dy = curr.get("y", 0.0) - prev.get("y", 0.0)
            distance = math.sqrt(dx * dx + dy * dy)
            speed = distance / dt

            t_mid = (t1 + t2) / 2.0
            contact = _has_contact_near(t_mid, events)
            threshold = CONTACT_SPEED_THRESHOLD if contact else MAX_HUMAN_SPRINT_SPEED

            if speed > threshold:
                context_label = "contact context" if contact else "no contact context"
                explanations.append(
                    f"Player {player_id} between t={t1} "
                    f"and t={t2} has speed={speed:.2f} m/s "
                    f"exceeding threshold {threshold} m/s ({context_label})"
                )

    return (len(explanations) == 0, explanations)


def _check_temporal_continuity(positions: list[dict]) -> tuple[bool, list[str]]:
    """Check that timestamps are ordered and gaps do not exceed tolerance.

    All positions are sorted by timestamp.  The gate fails if any
    consecutive pair has a non-increasing timestamp or a gap larger
    than ``MAX_TIMESTAMP_GAP``.

    Args:
        positions: List of position dicts with a ``timestamp`` key.

    Returns:
        Tuple of (passed, explanations).
    """
    if len(positions) <= 1:
        return (True, [])

    sorted_pos = sorted(positions, key=lambda p: p.get("timestamp", 0.0))
    explanations: list[str] = []

    for i in range(1, len(sorted_pos)):
        prev_ts = sorted_pos[i - 1].get("timestamp", 0.0)
        curr_ts = sorted_pos[i].get("timestamp", 0.0)

        if curr_ts < prev_ts:
            explanations.append(
                f"Timestamps out of order: t={prev_ts} followed by t={curr_ts}"
            )
        else:
            gap = curr_ts - prev_ts
            if gap > MAX_TIMESTAMP_GAP:
                explanations.append(
                    f"Timestamp gap of {gap:.3f}s between t={prev_ts} "
                    f"and t={curr_ts} exceeds max {MAX_TIMESTAMP_GAP}s"
                )

    return (len(explanations) == 0, explanations)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_gates(branch: dict) -> GatingResult:
    """Execute all gating checks on a branch.

    Gates:
      - field_bounds: all player positions within field boundaries
      - max_speed: no player exceeds applicable speed threshold
        (v3: context-aware — elevated threshold during contact events)
      - temporal_continuity: timestamps ordered, no gaps exceeding tolerance

    Args:
        branch: Validated branch dictionary.  Must contain a
            ``positions`` key with a list of position dicts.
            Optionally contains an ``events`` key used for
            contact-context speed thresholds.

    Returns:
        GatingResult with ``passed=True`` only if all flags are True.
        When ``passed`` is False, at least one flag is False and
        ``explanations`` is non-empty.
    """
    positions: list[dict] = branch.get("positions", [])
    events: list[dict] | None = branch.get("events")

    bounds_ok, bounds_expl = _check_field_bounds(positions)
    speed_ok, speed_expl = _check_max_speed(positions, events)
    temporal_ok, temporal_expl = _check_temporal_continuity(positions)

    flags = {
        "field_bounds": bounds_ok,
        "max_speed": speed_ok,
        "temporal_continuity": temporal_ok,
    }

    all_explanations = bounds_expl + speed_expl + temporal_expl
    passed = all(flags.values())

    return GatingResult(
        passed=passed,
        flags=flags,
        explanations=all_explanations,
    )
