"""Alignment module for the simulation evaluator.

Temporally and spatially aligns a branch to its continuation window
using the decision-point timestamp as the shared anchor.  This module
must NOT import from any other scoring module under ``src/scoring/``.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass

from src.utils.constants import ALIGNMENT_RESIDUAL_TOLERANCE


@dataclass
class AlignmentResult:
    """Result of aligning a branch to a continuation window.

    Attributes:
        aligned_branch: Deep copy of the branch with timestamps and
            positions shifted to the window's coordinate frame.
        aligned_window: Deep copy of the continuation window (unchanged
            but included for downstream convenience).
        temporal_offset: Signed difference in decision-point timestamps
            (branch − window), in seconds.
        spatial_offset: Euclidean distance between the average player
            positions at the decision point in the branch vs. the window.
        residual_magnitude: Combined residual ``sqrt(temporal² + spatial²)``.
            Flagged when it exceeds ``ALIGNMENT_RESIDUAL_TOLERANCE``.
    """

    aligned_branch: dict
    aligned_window: dict
    temporal_offset: float
    spatial_offset: float
    residual_magnitude: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _average_position_at_decision_point(
    positions: list[dict], decision_ts: float
) -> tuple[float, float]:
    """Compute the mean (x, y) of all positions closest to *decision_ts*.

    For each unique player, the position whose timestamp is nearest to
    *decision_ts* is selected.  The returned tuple is the average x and
    average y across those selected positions.

    Args:
        positions: List of position dicts with keys ``player_id``,
            ``x``, ``y``, and ``timestamp``.
        decision_ts: The decision-point timestamp to anchor on.

    Returns:
        ``(avg_x, avg_y)`` tuple.  Returns ``(0.0, 0.0)`` when
        *positions* is empty.
    """
    if not positions:
        return 0.0, 0.0

    # For each player pick the position closest to the decision point
    closest: dict[str, dict] = {}
    for pos in positions:
        pid = pos.get("player_id", "unknown")
        ts = pos.get("timestamp", 0.0)
        if pid not in closest or abs(ts - decision_ts) < abs(
            closest[pid].get("timestamp", 0.0) - decision_ts
        ):
            closest[pid] = pos

    if not closest:
        return 0.0, 0.0

    avg_x = sum(p.get("x", 0.0) for p in closest.values()) / len(closest)
    avg_y = sum(p.get("y", 0.0) for p in closest.values()) / len(closest)
    return avg_x, avg_y


def _extract_window_positions(continuation_window: dict) -> list[dict]:
    """Collect all position dicts from the window's outcomes.

    Each outcome in ``continuation_window["outcomes"]`` may contain a
    ``positions`` key with a list of position dicts.  This helper
    flattens them into a single list.

    Args:
        continuation_window: Continuation window dictionary.

    Returns:
        Flat list of position dicts found across all outcomes.
    """
    positions: list[dict] = []
    for outcome in continuation_window.get("outcomes", []):
        positions.extend(outcome.get("positions", []))
    return positions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def align(branch: dict, continuation_window: dict) -> AlignmentResult:
    """Align branch to continuation window using decision-point timestamp.

    Alignment steps:
      1. Compute ``temporal_offset`` as the difference between the
         branch and window decision-point timestamps.
      2. Shift all branch position timestamps by ``-temporal_offset``
         so they sit on the window's timeline.
      3. Compute the average player position at the decision point in
         both the branch and the window.  The ``spatial_offset`` is the
         Euclidean distance between these averages.
      4. Shift all branch positions by the spatial delta so the two
         coordinate frames coincide.
      5. Compute ``residual_magnitude = sqrt(temporal² + spatial²)``.

    Neither the original *branch* nor *continuation_window* is mutated.

    Args:
        branch: Validated, gate-passed branch dictionary.  Must contain
            ``decision_point_timestamp`` and ``positions``.
        continuation_window: Corresponding real-world continuation data.
            Must contain ``decision_point_timestamp`` and ``outcomes``.

    Returns:
        AlignmentResult with aligned copies and residual sub-metrics.
    """
    # Deep-copy so originals are never mutated
    aligned_branch = copy.deepcopy(branch)
    aligned_window = copy.deepcopy(continuation_window)

    # --- Temporal alignment ---
    branch_ts: float = branch.get("decision_point_timestamp", 0.0)
    window_ts: float = continuation_window.get("decision_point_timestamp", 0.0)
    temporal_offset: float = branch_ts - window_ts

    # Shift branch timestamps
    for pos in aligned_branch.get("positions", []):
        pos["timestamp"] = pos.get("timestamp", 0.0) - temporal_offset

    # --- Spatial alignment ---
    branch_avg_x, branch_avg_y = _average_position_at_decision_point(
        branch.get("positions", []), branch_ts
    )
    window_positions = _extract_window_positions(continuation_window)
    window_avg_x, window_avg_y = _average_position_at_decision_point(
        window_positions, window_ts
    )

    dx = branch_avg_x - window_avg_x
    dy = branch_avg_y - window_avg_y
    spatial_offset: float = math.sqrt(dx * dx + dy * dy)

    # Shift branch positions by the spatial delta
    for pos in aligned_branch.get("positions", []):
        pos["x"] = pos.get("x", 0.0) - dx
        pos["y"] = pos.get("y", 0.0) - dy

    # --- Residual ---
    residual_magnitude: float = math.sqrt(
        temporal_offset * temporal_offset + spatial_offset * spatial_offset
    )

    return AlignmentResult(
        aligned_branch=aligned_branch,
        aligned_window=aligned_window,
        temporal_offset=temporal_offset,
        spatial_offset=spatial_offset,
        residual_magnitude=residual_magnitude,
    )
