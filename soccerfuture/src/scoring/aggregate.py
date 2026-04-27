"""Aggregate scoring module for the simulation evaluator.

Combines sub-scores from all upstream scoring modules into a final
``EvaluationReport`` with full sub-metric traceability.  This module
imports only result dataclasses (data types) from other scoring modules
and receives actual results via the ``AggregateInput`` dataclass.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.models.evaluation_report import EvaluationReport, SubMetrics
from src.scoring.alignment import AlignmentResult
from src.scoring.decision_value import DecisionValueResult
from src.scoring.gating import GatingResult
from src.scoring.physical_plausibility import PhysicalPlausibilityResult
from src.scoring.predictive_fidelity import PredictiveFidelityResult
from src.scoring.tactical_consistency import TacticalConsistencyResult
from src.utils.constants import (
    ALIGNMENT_RESIDUAL_TOLERANCE,
    REALITY_ANCHOR_DAMPENING_FACTOR,
    REALITY_ANCHOR_SIMILARITY_THRESHOLD,
    SIMILARITY_EVENT_TOLERANCE,
    SIMILARITY_MAX_DISTANCE,
)


# ---------------------------------------------------------------------------
# Aggregate weights
# ---------------------------------------------------------------------------

_VALIDITY_W_PLAUSIBILITY: float = 0.5
_VALIDITY_W_FIDELITY: float = 0.3
_VALIDITY_W_ALIGNMENT: float = 0.2

_OPPORTUNITY_W_TACTICAL: float = 0.4
_OPPORTUNITY_W_DECISION: float = 0.6


@dataclass
class AggregateInput:
    """Collects all upstream scoring results for aggregation.

    Attributes:
        plausibility: Physical plausibility scoring result.
        fidelity: Predictive fidelity scoring result.
        alignment: Alignment result with residual sub-metrics.
        tactical: Tactical consistency scoring result.
        decision: Decision value scoring result.
        gating: Gating result with flags and explanations.
        continuation_window: Continuation window dict, used for
            reality anchor similarity computation.
    """

    plausibility: PhysicalPlausibilityResult
    fidelity: PredictiveFidelityResult
    alignment: AlignmentResult
    tactical: TacticalConsistencyResult
    decision: DecisionValueResult
    gating: GatingResult
    continuation_window: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to [*lo*, *hi*], replacing NaN/Inf with 0.0."""
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return max(lo, min(hi, value))


def _normalize_residual(residual: float) -> float:
    """Normalize alignment residual to [0, 1].

    A residual of 0 maps to 0.0 (perfect alignment).
    A residual >= ``ALIGNMENT_RESIDUAL_TOLERANCE`` maps to 1.0.
    Values in between are linearly interpolated.

    Args:
        residual: Raw residual magnitude from alignment.

    Returns:
        Normalized residual in [0, 1].
    """
    if ALIGNMENT_RESIDUAL_TOLERANCE <= 0:
        return 1.0 if residual > 0 else 0.0
    return _clamp(residual / ALIGNMENT_RESIDUAL_TOLERANCE)


def _compute_branch_window_similarity(
    aligned_branch: dict, continuation_window: dict
) -> float:
    """Compute similarity between branch trajectory and continuation window.

    Measures:
      1. Position similarity: for each branch player position, find the
         closest matching window position (by player_id and timestamp).
         Average Euclidean distance, normalized by
         ``SIMILARITY_MAX_DISTANCE``.
      2. Event similarity: fraction of branch events that have a matching
         event type in the window within ``SIMILARITY_EVENT_TOLERANCE``
         seconds.
      3. Combined: ``0.6 * pos_sim + 0.4 * event_sim``.

    Args:
        aligned_branch: Aligned branch dict with ``positions`` and
            ``events`` keys.
        continuation_window: Continuation window dict with ``outcomes``
            containing ``positions`` and ``events``.

    Returns:
        Similarity score in [0, 1] where 1.0 = identical to reality.
    """
    pos_sim = _position_similarity(aligned_branch, continuation_window)
    event_sim = _event_similarity(aligned_branch, continuation_window)
    return _clamp(0.6 * pos_sim + 0.4 * event_sim)


def _position_similarity(
    aligned_branch: dict, continuation_window: dict
) -> float:
    """Compute position similarity between branch and window.

    For each branch player position, find the closest matching window
    position (same player_id, closest timestamp) and compute Euclidean
    distance.  Average distance is normalized by
    ``SIMILARITY_MAX_DISTANCE``.

    Returns:
        Position similarity in [0, 1].
    """
    branch_positions: list[dict] = aligned_branch.get("positions", [])
    if not branch_positions:
        return 0.5  # neutral

    # Extract window positions from outcomes
    window_positions: list[dict] = []
    for outcome in continuation_window.get("outcomes", []):
        window_positions.extend(outcome.get("positions", []))

    if not window_positions:
        return 0.5  # neutral

    total_dist = 0.0
    count = 0

    for bp in branch_positions:
        bp_pid = bp.get("player_id", "")
        bp_ts = bp.get("timestamp", 0.0)
        bp_x = bp.get("x", 0.0)
        bp_y = bp.get("y", 0.0)

        best_dist: float | None = None
        for wp in window_positions:
            if wp.get("player_id", "") != bp_pid:
                continue
            wp_x = wp.get("x", 0.0)
            wp_y = wp.get("y", 0.0)
            wp_ts = wp.get("timestamp", 0.0)
            # Weight by timestamp closeness — pick closest timestamp match
            dx = bp_x - wp_x
            dy = bp_y - wp_y
            dist = math.sqrt(dx * dx + dy * dy)
            ts_diff = abs(bp_ts - wp_ts)
            # Prefer closest timestamp; use (ts_diff, dist) as sort key
            if best_dist is None:
                best_dist = dist
                best_ts_diff = ts_diff
            elif ts_diff < best_ts_diff or (ts_diff == best_ts_diff and dist < best_dist):
                best_dist = dist
                best_ts_diff = ts_diff

        if best_dist is not None:
            total_dist += best_dist
            count += 1

    if count == 0:
        return 0.5  # no matching player_ids

    avg_dist = total_dist / count
    return _clamp(1.0 - avg_dist / SIMILARITY_MAX_DISTANCE)


def _event_similarity(
    aligned_branch: dict, continuation_window: dict
) -> float:
    """Compute event similarity between branch and window.

    For each branch event, check if the window has an event of the same
    type within ``SIMILARITY_EVENT_TOLERANCE`` seconds.

    Returns:
        Event similarity in [0, 1].  Returns 1.0 if no branch events.
    """
    branch_events: list[dict] = aligned_branch.get("events", [])
    if not branch_events:
        return 1.0

    # Extract window events from outcomes
    window_events: list[dict] = []
    for outcome in continuation_window.get("outcomes", []):
        window_events.extend(outcome.get("events", []))

    if not window_events:
        return 0.0  # branch has events but window doesn't

    matched = 0
    for be in branch_events:
        b_type = be.get("event_type", "")
        b_ts = be.get("timestamp", 0.0)
        for we in window_events:
            if we.get("event_type", "") == b_type:
                if abs(b_ts - we.get("timestamp", 0.0)) <= SIMILARITY_EVENT_TOLERANCE:
                    matched += 1
                    break

    return matched / len(branch_events)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_aggregate(inputs: AggregateInput) -> EvaluationReport:
    """Combine sub-scores into a final EvaluationReport.

    Validity = weighted combination of plausibility, fidelity, and
    alignment residual:
        ``0.5 * plausibility + 0.3 * fidelity + 0.2 * (1 - residual_norm)``

    Opportunity = weighted combination of tactical consistency and
    decision value:
        ``0.6 * tactical_consistency + 0.4 * decision_value``

    All sub-metrics are preserved in the report for full traceability.

    Args:
        inputs: All scoring results from upstream modules.

    Returns:
        EvaluationReport with validity_score, opportunity_score,
        gating_flags, sub_metrics, and explanations.
    """
    # --- Alignment residual normalization ---
    residual_normalized = _normalize_residual(inputs.alignment.residual_magnitude)

    # --- Validity score ---
    validity_score = _clamp(
        _VALIDITY_W_PLAUSIBILITY * inputs.plausibility.plausibility_score
        + _VALIDITY_W_FIDELITY * inputs.fidelity.fidelity_score
        + _VALIDITY_W_ALIGNMENT * (1.0 - residual_normalized)
    )

    # --- Opportunity score ---
    raw_opportunity = _clamp(
        _OPPORTUNITY_W_TACTICAL * inputs.tactical.consistency_score
        + _OPPORTUNITY_W_DECISION * inputs.decision.opportunity_score
    )

    # Turnover penalty: if turnover_risk_delta is very low (branch has
    # turnovers that reality didn't), cap the opportunity score.
    # turnover_risk_delta < 0.3 means branch is significantly riskier.
    turnover_delta = inputs.decision.turnover_risk_delta
    if turnover_delta < 0.3:
        # Scale opportunity down proportionally — turnovers are catastrophic
        penalty = turnover_delta / 0.3  # 0.0 at delta=0, 1.0 at delta=0.3
        opportunity_after_turnover = _clamp(raw_opportunity * penalty)
    else:
        opportunity_after_turnover = raw_opportunity

    # --- Reality anchor dampening ---
    similarity = _compute_branch_window_similarity(
        inputs.alignment.aligned_branch, inputs.continuation_window
    )

    if similarity >= REALITY_ANCHOR_SIMILARITY_THRESHOLD:
        anchor_strength = (similarity - REALITY_ANCHOR_SIMILARITY_THRESHOLD) / (
            1.0 - REALITY_ANCHOR_SIMILARITY_THRESHOLD
        ) if REALITY_ANCHOR_SIMILARITY_THRESHOLD < 1.0 else 1.0
        dampened = opportunity_after_turnover + anchor_strength * (
            0.5 - opportunity_after_turnover
        ) * REALITY_ANCHOR_DAMPENING_FACTOR

        # Guardrails: don't cross extreme directional bounds
        # Only protect clearly-better (>0.75) and clearly-worse (<0.25) branches
        if opportunity_after_turnover > 0.75:
            dampened = max(dampened, 0.6)
        if opportunity_after_turnover < 0.25:
            dampened = min(dampened, 0.4)

        opportunity_score = _clamp(dampened)
    else:
        opportunity_score = opportunity_after_turnover

    # --- Branch ID from aligned branch ---
    branch_id = inputs.alignment.aligned_branch.get("branch_id", "unknown")

    # --- Sub-metrics ---
    sub_metrics = SubMetrics(
        speed_score=_clamp(inputs.plausibility.speed_score),
        acceleration_score=_clamp(inputs.plausibility.acceleration_score),
        deceleration_score=_clamp(inputs.plausibility.deceleration_score),
        position_accuracy=_clamp(inputs.fidelity.position_accuracy),
        event_timing_accuracy=_clamp(inputs.fidelity.event_timing_accuracy),
        formation_consistency=_clamp(inputs.fidelity.formation_consistency),
        role_consistency_score=_clamp(inputs.tactical.role_consistency_score),
        formation_coherence_score=_clamp(inputs.tactical.formation_coherence_score),
        ball_progression=_clamp(inputs.decision.ball_progression),
        turnover_risk_delta=_clamp(inputs.decision.turnover_risk_delta),
        scoring_probability_delta=_clamp(inputs.decision.scoring_probability_delta),
        alignment_residual=_clamp(residual_normalized),
        plausibility_score=_clamp(inputs.plausibility.plausibility_score),
        fidelity_score=_clamp(inputs.fidelity.fidelity_score),
        tactical_consistency_score=_clamp(inputs.tactical.consistency_score),
        decision_value_score=_clamp(inputs.decision.opportunity_score),
        compactness_score=_clamp(inputs.tactical.compactness_score),
        defensive_density_score=_clamp(inputs.tactical.defensive_density_score),
        formation_shape_score=_clamp(inputs.tactical.formation_shape_score),
        branch_window_similarity=_clamp(similarity),
    )

    return EvaluationReport(
        branch_id=branch_id,
        validity_score=validity_score,
        opportunity_score=opportunity_score,
        gating_flags=dict(inputs.gating.flags),
        explanations=list(inputs.gating.explanations),
        sub_metrics=sub_metrics,
        passed_gating=inputs.gating.passed,
        passed_validity=True,
    )
