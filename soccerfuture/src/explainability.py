"""Branch-level explainability for the pipeline ranking output.

Pure functions that produce human-readable ranking justifications and
filter reasons from evaluation data.  No side effects, no scoring module
imports — receives evaluation data as dicts already computed by the
evaluator.
"""

from __future__ import annotations

from src.utils.constants import DEFAULT_VALIDITY_THRESHOLD

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUB_METRIC_NAMES: dict[str, str] = {
    "speed_score": "Physical Speed",
    "acceleration_score": "Acceleration",
    "deceleration_score": "Deceleration",
    "position_accuracy": "Position Accuracy",
    "event_timing_accuracy": "Event Timing",
    "formation_consistency": "Formation Consistency",
    "plausibility_score": "Physical Plausibility",
    "fidelity_score": "Predictive Fidelity",
    "role_consistency_score": "Role Consistency",
    "formation_coherence_score": "Formation Coherence",
    "ball_progression": "Ball Progression",
    "turnover_risk_delta": "Turnover Risk",
    "scoring_probability_delta": "Scoring Probability",
    "tactical_consistency_score": "Tactical Consistency",
    "decision_value_score": "Decision Value",
    "compactness_score": "Formation Compactness",
    "defensive_density_score": "Defensive Density",
    "formation_shape_score": "Formation Shape",
    "branch_window_similarity": "Reality Similarity",
}

_VALIDITY_METRICS: list[str] = [
    "speed_score",
    "acceleration_score",
    "deceleration_score",
    "position_accuracy",
    "event_timing_accuracy",
    "formation_consistency",
    "plausibility_score",
    "fidelity_score",
]

_OPPORTUNITY_METRICS: list[str] = [
    "role_consistency_score",
    "formation_coherence_score",
    "ball_progression",
    "turnover_risk_delta",
    "scoring_probability_delta",
    "tactical_consistency_score",
    "decision_value_score",
    "compactness_score",
    "defensive_density_score",
    "formation_shape_score",
]

_PROMOTION_THRESHOLD: float = 0.6
_PENALTY_THRESHOLD: float = 0.4

# Keys used for Req 8.3 (high-validity promoted factors)
_PLAUSIBILITY_FIDELITY_KEYS: list[str] = ["plausibility_score", "fidelity_score"]

# Keys used for Req 8.4 (low-opportunity penalized factors)
_TACTICAL_DECISION_KEYS: list[str] = [
    "tactical_consistency_score",
    "decision_value_score",
]

# All metric keys considered for top/bottom scoring block
_ALL_METRIC_KEYS: list[str] = _VALIDITY_METRICS + _OPPORTUNITY_METRICS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _display_name(key: str) -> str:
    """Return the human-readable display name for a sub-metric key."""
    return _SUB_METRIC_NAMES.get(key, key)


def _extract_sub_metrics(evaluation_report: dict) -> dict[str, float]:
    """Safely extract sub_metrics from an evaluation report dict.

    Returns an empty dict when ``sub_metrics`` is missing or not a dict.
    Handles both raw dicts and dataclass-style nested dicts.
    """
    raw = evaluation_report.get("sub_metrics")
    if isinstance(raw, dict):
        return raw
    return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_ranking_explanation(
    evaluation_report: dict,
    validity_threshold: float = DEFAULT_VALIDITY_THRESHOLD,
) -> dict:
    """Build a ranking explanation for a top-K branch.

    Analyzes sub_metrics to identify promoted and penalized factors,
    determines the top and bottom scoring blocks, and flags near-threshold
    branches.

    Args:
        evaluation_report: Full evaluation report dict (from
            ``EvaluationReport``).
        validity_threshold: The validity threshold used for filtering.

    Returns:
        Dict with keys: ``promoted_factors`` (list[str]),
        ``penalized_factors`` (list[str]), ``top_scoring_block`` (str),
        ``bottom_scoring_block`` (str), and optionally
        ``near_threshold_warning`` (str).
    """
    sub_metrics = _extract_sub_metrics(evaluation_report)

    promoted_factors: list[str] = []
    penalized_factors: list[str] = []

    # Step 1-2: classify each known sub-metric
    for key in _ALL_METRIC_KEYS:
        value = sub_metrics.get(key)
        if value is None:
            continue
        if value >= _PROMOTION_THRESHOLD:
            promoted_factors.append(_display_name(key))
        if value <= _PENALTY_THRESHOLD:
            penalized_factors.append(_display_name(key))

    # Step 3-4: top / bottom scoring block
    top_scoring_block = "unknown"
    bottom_scoring_block = "unknown"

    if sub_metrics:
        # Only consider keys we know about
        known = {
            k: v for k, v in sub_metrics.items() if k in _ALL_METRIC_KEYS
        }
        if known:
            top_key = max(known, key=known.get)  # type: ignore[arg-type]
            bottom_key = min(known, key=known.get)  # type: ignore[arg-type]
            top_scoring_block = _display_name(top_key)
            bottom_scoring_block = _display_name(bottom_key)

    result: dict = {
        "promoted_factors": promoted_factors,
        "penalized_factors": penalized_factors,
        "top_scoring_block": top_scoring_block,
        "bottom_scoring_block": bottom_scoring_block,
    }

    # Step 5: near-threshold warning (Req 8.5)
    validity_score = evaluation_report.get("validity_score")
    if validity_score is not None:
        if abs(validity_score - validity_threshold) <= 0.1:
            result["near_threshold_warning"] = (
                f"Validity score ({validity_score:.2f}) is within 0.1 of "
                f"the filter threshold ({validity_threshold:.2f})."
            )

    # Step 6: high-validity → ensure plausibility/fidelity promoted (Req 8.3)
    if validity_score is not None and validity_score > 0.7:
        pf_values = {
            k: sub_metrics[k]
            for k in _PLAUSIBILITY_FIDELITY_KEYS
            if k in sub_metrics
        }
        if pf_values:
            best_pf_key = max(pf_values, key=pf_values.get)  # type: ignore[arg-type]
            best_pf_name = _display_name(best_pf_key)
            if best_pf_name not in promoted_factors:
                promoted_factors.append(best_pf_name)

    # Step 7: low-opportunity → ensure tactical/decision penalized (Req 8.4)
    opportunity_score = evaluation_report.get("opportunity_score")
    if opportunity_score is not None and opportunity_score < 0.4:
        td_values = {
            k: sub_metrics[k]
            for k in _TACTICAL_DECISION_KEYS
            if k in sub_metrics
        }
        if td_values:
            worst_td_key = min(td_values, key=td_values.get)  # type: ignore[arg-type]
            worst_td_name = _display_name(worst_td_key)
            if worst_td_name not in penalized_factors:
                penalized_factors.append(worst_td_name)

    return result


def build_filter_reason(
    evaluation_report: dict,
    passed_gating: bool,
    validity_threshold: float = DEFAULT_VALIDITY_THRESHOLD,
) -> str:
    """Build a filter reason for a rejected or filtered branch.

    Args:
        evaluation_report: Full evaluation report dict.
        passed_gating: Whether the branch passed gating.
        validity_threshold: The validity threshold used for filtering.

    Returns:
        String starting with ``"Rejected: "`` (gating failure) or
        ``"Filtered: "`` (below validity threshold).
    """
    if not passed_gating:
        explanations = evaluation_report.get("explanations")
        if isinstance(explanations, list) and explanations:
            return f"Rejected: {explanations[0]}"
        return "Rejected: branch failed gating checks"

    # Passed gating but below validity threshold
    sub_metrics = _extract_sub_metrics(evaluation_report)
    insufficient: list[str] = []
    for key in _VALIDITY_METRICS:
        value = sub_metrics.get(key)
        if value is not None and value < 0.3:
            insufficient.append(_display_name(key))

    if insufficient:
        names = ", ".join(insufficient)
        return f"Filtered: insufficient validity sub-scores ({names})"
    return "Filtered: validity score below threshold"


# ---------------------------------------------------------------------------
# Context-aware notes
# ---------------------------------------------------------------------------


def build_context_notes(
    match_context: dict | None,
    context_signals: dict | None,
) -> list[str]:
    """Build human-readable notes about the match context applied.

    Args:
        match_context: Serialized MatchContext dict, or None.
        context_signals: Serialized ContextSignals dict, or None.

    Returns:
        List of explanatory note strings.
    """
    if match_context is None:
        return [
            "No external context applied; ranking based only on play-state analysis."
        ]

    notes: list[str] = []

    # Pull notes from context_signals if available.
    if context_signals is not None:
        signal_notes = context_signals.get("notes", [])
        notes.extend(signal_notes)

        # Flag non-zero biases.
        bias_labels: dict[str, str] = {
            "aggression_bias": "aggression bias",
            "risk_tolerance": "risk tolerance",
            "retention_bias": "retention bias",
        }
        applied_biases = [
            label
            for key, label in bias_labels.items()
            if context_signals.get(key, 0.0) != 0.0
        ]
        if applied_biases:
            notes.append(
                f"Active biases: {', '.join(applied_biases)}."
            )

    # Summary line from match_context fields.
    source = match_context.get("source", "unknown")
    cache_status = match_context.get("cache_status", "unknown")
    home = match_context.get("home_team", "?")
    away = match_context.get("away_team", "?")
    lookback = match_context.get("lookback_matches", 0)
    notes.append(
        f"Context from {source} ({cache_status}): "
        f"{home} vs {away}, {lookback} matches."
    )

    return notes
