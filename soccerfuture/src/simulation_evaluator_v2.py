"""Orchestration layer for the simulation evaluator v2.

Composes all scoring modules in strict pipeline order and enforces
early termination on validation failure, gating failure, or low
validity.  This is the only module that imports from multiple scoring
modules under ``src/scoring/``.
"""

from __future__ import annotations

from src.models.config import EvaluatorConfig
from src.models.evaluation_report import EvaluationReport, SubMetrics
from src.scoring.aggregate import (
    AggregateInput,
    compute_aggregate,
    _clamp,
    _normalize_residual,
)
from src.scoring.alignment import align
from src.scoring.decision_value import score_decision_value
from src.scoring.gating import run_gates
from src.scoring.physical_plausibility import score_physical_plausibility
from src.scoring.predictive_fidelity import score_predictive_fidelity
from src.scoring.tactical_consistency import score_tactical_consistency
from src.scoring.validation import validate_branch
from src.utils.constants import DEFAULT_VALIDITY_THRESHOLD


def _error_report(branch_id: str, message: str) -> EvaluationReport:
    """Build an error-state report with validity=0, opportunity=0.

    Args:
        branch_id: Identifier of the branch (or "unknown").
        message: Human-readable error description.

    Returns:
        EvaluationReport in error state.
    """
    return EvaluationReport(
        branch_id=branch_id,
        validity_score=0.0,
        opportunity_score=0.0,
        gating_flags={},
        explanations=[message],
        sub_metrics=SubMetrics(),
        passed_gating=False,
        passed_validity=False,
    )


def evaluate_branch(
    branch: dict,
    continuation_window: dict,
    config: EvaluatorConfig | None = None,
) -> EvaluationReport:
    """Run the full evaluation pipeline on a single branch.

    Pipeline order:
      1. Validation — structural correctness
      2. Gating — binary pass/fail physical checks
      3. Alignment — temporal/spatial alignment to window
      4. Physical plausibility + Predictive fidelity (validity)
      5. Tactical consistency + Decision value (opportunity)
      6. Aggregate — combine into final report

    Early termination:
      - Validation failure → error report (validity=0, opportunity=0)
      - Gating failure → gated report (validity=0, opportunity=0)
      - Low validity (below threshold) → report with opportunity=0

    Args:
        branch: Raw branch dictionary.
        continuation_window: Corresponding continuation window dictionary.
        config: Optional configuration overrides for thresholds.

    Returns:
        EvaluationReport (always JSON-serializable).
    """
    cfg = config or EvaluatorConfig()
    threshold = cfg.validity_threshold
    branch_id = branch.get("branch_id", "unknown")

    # --- Step 1: Validation ---
    try:
        validation_result = validate_branch(branch)
    except Exception as exc:
        return _error_report(branch_id, f"Validation error: {exc}")

    if not validation_result.is_valid:
        return _error_report(branch_id, validation_result.error_message)

    # --- Step 2: Gating ---
    try:
        gating_result = run_gates(branch)
    except Exception as exc:
        return _error_report(branch_id, f"Gating error: {exc}")

    if not gating_result.passed:
        return EvaluationReport(
            branch_id=branch_id,
            validity_score=0.0,
            opportunity_score=0.0,
            gating_flags=dict(gating_result.flags),
            explanations=list(gating_result.explanations),
            sub_metrics=SubMetrics(),
            passed_gating=False,
            passed_validity=False,
        )

    # --- Step 3: Alignment ---
    try:
        alignment_result = align(branch, continuation_window)
    except Exception as exc:
        return _error_report(branch_id, f"Alignment error: {exc}")

    aligned_branch = alignment_result.aligned_branch
    aligned_window = alignment_result.aligned_window

    # --- Step 4: Validity scoring (parallel dimensions) ---
    try:
        plausibility_result = score_physical_plausibility(aligned_branch)
    except Exception as exc:
        return _error_report(branch_id, f"Physical plausibility error: {exc}")

    try:
        fidelity_result = score_predictive_fidelity(aligned_branch, aligned_window)
    except Exception as exc:
        return _error_report(branch_id, f"Predictive fidelity error: {exc}")

    # Compute interim validity to decide whether to proceed
    residual_norm = _normalize_residual(alignment_result.residual_magnitude)
    interim_validity = _clamp(
        0.5 * plausibility_result.plausibility_score
        + 0.3 * fidelity_result.fidelity_score
        + 0.2 * (1.0 - residual_norm)
    )

    if interim_validity < threshold:
        # Low validity — skip opportunity scoring
        sub_metrics = SubMetrics(
            speed_score=plausibility_result.speed_score,
            acceleration_score=plausibility_result.acceleration_score,
            deceleration_score=plausibility_result.deceleration_score,
            position_accuracy=fidelity_result.position_accuracy,
            event_timing_accuracy=fidelity_result.event_timing_accuracy,
            formation_consistency=fidelity_result.formation_consistency,
            alignment_residual=residual_norm,
            plausibility_score=plausibility_result.plausibility_score,
            fidelity_score=fidelity_result.fidelity_score,
        )
        return EvaluationReport(
            branch_id=branch_id,
            validity_score=interim_validity,
            opportunity_score=0.0,
            gating_flags=dict(gating_result.flags),
            explanations=["Validity below threshold; opportunity scoring skipped."],
            sub_metrics=sub_metrics,
            passed_gating=True,
            passed_validity=False,
        )

    # --- Step 5: Opportunity scoring (parallel dimensions) ---
    try:
        tactical_result = score_tactical_consistency(aligned_branch)
    except Exception as exc:
        return _error_report(branch_id, f"Tactical consistency error: {exc}")

    try:
        decision_result = score_decision_value(aligned_branch, aligned_window)
    except Exception as exc:
        return _error_report(branch_id, f"Decision value error: {exc}")

    # --- Step 6: Aggregate ---
    try:
        aggregate_input = AggregateInput(
            plausibility=plausibility_result,
            fidelity=fidelity_result,
            alignment=alignment_result,
            tactical=tactical_result,
            decision=decision_result,
            gating=gating_result,
            continuation_window=aligned_window,
        )
        report = compute_aggregate(aggregate_input)
        # Override passed flags
        report.passed_gating = True
        report.passed_validity = True
        return report
    except Exception as exc:
        return _error_report(branch_id, f"Aggregate error: {exc}")


def evaluate_all(
    input_data: dict,
    config: EvaluatorConfig | None = None,
) -> list[EvaluationReport]:
    """Evaluate all branches in an input payload.

    Matches branches to continuation windows by index: ``branch[i]``
    pairs with ``continuation_window[i]``.

    Args:
        input_data: Full input JSON with ``branches`` (list of branch
            dicts) and ``continuation_windows`` (list of window dicts).
        config: Optional configuration overrides.

    Returns:
        List of EvaluationReports, one per branch.
    """
    branches: list[dict] = input_data.get("branches", [])
    windows: list[dict] = input_data.get("continuation_windows", [])

    reports: list[EvaluationReport] = []
    for i, branch in enumerate(branches):
        if i < len(windows):
            window = windows[i]
        else:
            window = {}
        reports.append(evaluate_branch(branch, window, config))

    return reports
