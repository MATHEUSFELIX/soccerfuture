"""Predictive fidelity scoring module for the simulation evaluator.

Scores how well a branch's predicted outcomes match real-world patterns
in the continuation window.  Uses deterministic, rule-based comparison
logic with no machine-learning dependencies.  This module must NOT
import from any other scoring module under ``src/scoring/``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.utils.constants import SIGNIFICANT_DIVERGENCE_THRESHOLD

# Maximum reasonable distance (meters) used to normalise position accuracy.
# Roughly half a soccer field length.
_MAX_REASONABLE_DISTANCE: float = 50.0


@dataclass
class PredictiveFidelityResult:
    """Result of predictive fidelity scoring for a branch.

    Attributes:
        fidelity_score: Aggregate fidelity in [0, 1], weighted average
            of the three sub-scores.
        position_accuracy: Sub-metric measuring how close branch player
            positions are to the window outcomes, in [0, 1].
        event_timing_accuracy: Sub-metric measuring how well branch
            event timestamps match window event timestamps, in [0, 1].
        formation_consistency: Sub-metric measuring how similar the
            spatial arrangement of players is between branch and window,
            in [0, 1].
    """

    fidelity_score: float
    position_accuracy: float
    event_timing_accuracy: float
    formation_consistency: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to [*lo*, *hi*], replacing NaN/Inf with 0.0."""
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return max(lo, min(hi, value))


def _euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    """Return the Euclidean distance between two 2-D points."""
    dx = x1 - x2
    dy = y1 - y2
    return math.sqrt(dx * dx + dy * dy)


def _extract_window_positions(aligned_window: dict) -> list[list[dict]]:
    """Return a list of position lists, one per window outcome.

    Args:
        aligned_window: Aligned continuation window dict.

    Returns:
        List where each element is the ``positions`` list from one
        outcome.  Outcomes without positions are skipped.
    """
    result: list[list[dict]] = []
    for outcome in aligned_window.get("outcomes", []):
        positions = outcome.get("positions", [])
        if positions:
            result.append(positions)
    return result


def _extract_window_events(aligned_window: dict) -> list[list[dict]]:
    """Return a list of event lists, one per window outcome.

    Args:
        aligned_window: Aligned continuation window dict.

    Returns:
        List where each element is the ``events`` list from one outcome.
        Outcomes without events are skipped.
    """
    result: list[list[dict]] = []
    for outcome in aligned_window.get("outcomes", []):
        events = outcome.get("events", [])
        if events:
            result.append(events)
    return result


def _compute_position_accuracy(
    branch_positions: list[dict],
    window_outcome_positions: list[list[dict]],
) -> float:
    """Compute position accuracy between branch and window outcomes.

    For each player in the branch, find the closest matching player
    position across all window outcomes.  The score is
    ``1.0 - (avg_min_distance / _MAX_REASONABLE_DISTANCE)``, clamped
    to [0, 1].

    Args:
        branch_positions: Positions from the aligned branch.
        window_outcome_positions: List of position lists from window
            outcomes.

    Returns:
        Position accuracy score in [0, 1].
    """
    if not branch_positions or not window_outcome_positions:
        return 0.5  # neutral when nothing to compare

    # Flatten all window positions into a single list for matching
    all_window_pos: list[dict] = []
    for outcome_pos in window_outcome_positions:
        all_window_pos.extend(outcome_pos)

    if not all_window_pos:
        return 0.5

    total_min_dist = 0.0
    count = 0

    for bp in branch_positions:
        bx = bp.get("x", 0.0)
        by = bp.get("y", 0.0)

        min_dist = float("inf")
        for wp in all_window_pos:
            dist = _euclidean(bx, by, wp.get("x", 0.0), wp.get("y", 0.0))
            if dist < min_dist:
                min_dist = dist

        total_min_dist += min_dist
        count += 1

    if count == 0:
        return 0.5

    avg_distance = total_min_dist / count
    score = 1.0 - (avg_distance / _MAX_REASONABLE_DISTANCE)
    return _clamp(score)


def _compute_event_timing_accuracy(
    branch_events: list[dict],
    window_outcome_events: list[list[dict]],
) -> float:
    """Compute event timing accuracy between branch and window.

    For each branch event, find the closest matching event (by type)
    across all window outcomes and measure the timing difference.
    Score is ``1.0 - (avg_timing_diff / max_timing_diff)``, clamped
    to [0, 1].  If there are no events to compare, returns 0.5.

    Args:
        branch_events: Events from the aligned branch.
        window_outcome_events: List of event lists from window outcomes.

    Returns:
        Event timing accuracy score in [0, 1].
    """
    if not branch_events or not window_outcome_events:
        return 0.5  # default when no events to compare

    # Flatten window events
    all_window_events: list[dict] = []
    for outcome_events in window_outcome_events:
        all_window_events.extend(outcome_events)

    if not all_window_events:
        return 0.5

    # Maximum timing difference considered (seconds).  Events further
    # apart than this are treated as completely mismatched.
    max_timing_diff = 5.0

    timing_diffs: list[float] = []

    for be in branch_events:
        b_type = be.get("event_type", "")
        b_ts = be.get("timestamp", 0.0)

        # Find closest window event of the same type
        best_diff: float | None = None
        for we in all_window_events:
            if we.get("event_type", "") == b_type:
                diff = abs(b_ts - we.get("timestamp", 0.0))
                if best_diff is None or diff < best_diff:
                    best_diff = diff

        if best_diff is not None:
            timing_diffs.append(best_diff)
        else:
            # No matching event type in window — treat as max mismatch
            timing_diffs.append(max_timing_diff)

    if not timing_diffs:
        return 0.5

    avg_diff = sum(timing_diffs) / len(timing_diffs)
    score = 1.0 - (avg_diff / max_timing_diff)
    return _clamp(score)


def _compute_formation_consistency(
    branch_positions: list[dict],
    window_outcome_positions: list[list[dict]],
) -> float:
    """Compute formation consistency between branch and window.

    Compares the spatial arrangement (pairwise inter-player distances)
    of players in the branch against each window outcome.  The best-
    matching outcome is used.  Score is based on how similar the
    pairwise distance vectors are.

    Args:
        branch_positions: Positions from the aligned branch.
        window_outcome_positions: List of position lists from window
            outcomes.

    Returns:
        Formation consistency score in [0, 1].
    """
    if not branch_positions or not window_outcome_positions:
        return 0.5  # neutral when nothing to compare

    branch_pairwise = _pairwise_distances(branch_positions)
    if not branch_pairwise:
        return 0.5

    best_score = 0.0
    for outcome_pos in window_outcome_positions:
        window_pairwise = _pairwise_distances(outcome_pos)
        if not window_pairwise:
            continue
        score = _compare_pairwise(branch_pairwise, window_pairwise)
        if score > best_score:
            best_score = score

    return _clamp(best_score)


def _pairwise_distances(positions: list[dict]) -> list[float]:
    """Compute sorted pairwise Euclidean distances between positions.

    Uses the latest timestamp position for each unique player to get
    a single snapshot, then computes all pairwise distances.

    Args:
        positions: List of position dicts.

    Returns:
        Sorted list of pairwise distances.
    """
    # Pick the latest position per player for a single snapshot
    latest: dict[str, dict] = {}
    for pos in positions:
        pid = pos.get("player_id", "unknown")
        ts = pos.get("timestamp", 0.0)
        if pid not in latest or ts > latest[pid].get("timestamp", 0.0):
            latest[pid] = pos

    players = list(latest.values())
    if len(players) < 2:
        return []

    dists: list[float] = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            dists.append(
                _euclidean(
                    players[i].get("x", 0.0),
                    players[i].get("y", 0.0),
                    players[j].get("x", 0.0),
                    players[j].get("y", 0.0),
                )
            )
    dists.sort()
    return dists


def _compare_pairwise(
    branch_dists: list[float], window_dists: list[float]
) -> float:
    """Compare two sorted pairwise-distance vectors.

    Uses the average absolute difference between corresponding entries,
    normalised by ``_MAX_REASONABLE_DISTANCE``.  If the vectors differ
    in length, the shorter one is padded with the mean of the longer.

    Args:
        branch_dists: Sorted pairwise distances from the branch.
        window_dists: Sorted pairwise distances from a window outcome.

    Returns:
        Similarity score in [0, 1].
    """
    if not branch_dists and not window_dists:
        return 1.0

    # Pad the shorter list so both have equal length
    max_len = max(len(branch_dists), len(window_dists))
    b = list(branch_dists)
    w = list(window_dists)

    if b:
        b_mean = sum(b) / len(b)
    else:
        b_mean = 0.0
    if w:
        w_mean = sum(w) / len(w)
    else:
        w_mean = 0.0

    while len(b) < max_len:
        b.append(b_mean)
    while len(w) < max_len:
        w.append(w_mean)

    total_diff = sum(abs(bv - wv) for bv, wv in zip(b, w))
    avg_diff = total_diff / max_len
    score = 1.0 - (avg_diff / _MAX_REASONABLE_DISTANCE)
    return _clamp(score)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_predictive_fidelity(
    aligned_branch: dict, aligned_window: dict
) -> PredictiveFidelityResult:
    """Score predictive fidelity by comparing branch to continuation window.

    Uses deterministic, rule-based comparison.  No ML dependencies.
    Branches diverging significantly from all window outcomes receive a
    fidelity score below ``SIGNIFICANT_DIVERGENCE_THRESHOLD`` (0.3).

    Sub-score computation:
      - **position_accuracy**: Average closest-match Euclidean distance
        between branch and window player positions, normalised by a
        maximum reasonable distance (~50 meters).
      - **event_timing_accuracy**: Average timing difference between
        matching branch and window events.  Defaults to 0.5 when no
        events are available.
      - **formation_consistency**: Similarity of pairwise inter-player
        distance vectors between branch and the best-matching window
        outcome.

    Aggregate fidelity is a weighted average:
      ``0.5 * position_accuracy + 0.3 * event_timing_accuracy
        + 0.2 * formation_consistency``

    Args:
        aligned_branch: Aligned branch data.  Expected keys:
            ``positions`` (list of dicts with ``player_id``, ``x``,
            ``y``, ``timestamp``) and ``events`` (list of dicts with
            ``event_type``, ``timestamp``, ``player_id``, ``metadata``).
        aligned_window: Aligned continuation window data.  Expected
            keys: ``outcomes`` (list of dicts, each optionally
            containing ``positions`` and ``events`` lists) and
            ``decision_point_timestamp``.

    Returns:
        PredictiveFidelityResult with aggregate and per-dimension
        scores, all clamped to [0.0, 1.0].
    """
    branch_positions: list[dict] = aligned_branch.get("positions", [])
    branch_events: list[dict] = aligned_branch.get("events", [])

    window_outcome_positions = _extract_window_positions(aligned_window)
    window_outcome_events = _extract_window_events(aligned_window)

    position_accuracy = _compute_position_accuracy(
        branch_positions, window_outcome_positions
    )
    event_timing_accuracy = _compute_event_timing_accuracy(
        branch_events, window_outcome_events
    )
    formation_consistency = _compute_formation_consistency(
        branch_positions, window_outcome_positions
    )

    # Weighted average
    fidelity_score = (
        0.5 * position_accuracy
        + 0.3 * event_timing_accuracy
        + 0.2 * formation_consistency
    )

    # Final clamp
    fidelity_score = _clamp(fidelity_score)
    position_accuracy = _clamp(position_accuracy)
    event_timing_accuracy = _clamp(event_timing_accuracy)
    formation_consistency = _clamp(formation_consistency)

    return PredictiveFidelityResult(
        fidelity_score=fidelity_score,
        position_accuracy=position_accuracy,
        event_timing_accuracy=event_timing_accuracy,
        formation_consistency=formation_consistency,
    )
