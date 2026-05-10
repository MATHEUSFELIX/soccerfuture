"""Runtime ingestion evaluation.

Evaluates the quality and robustness of runtime ingestion results,
producing a summary report for monitoring and review.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.runtime.runtime_ingestion_runner import IngestionBatchResult


@dataclass
class RuntimeIngestionEvalReport:
    """Evaluation report for a runtime ingestion batch.

    Attributes:
        total_payloads: Total payloads in the batch.
        accepted_count: Number accepted.
        rejected_count: Number rejected.
        acceptance_rate: Fraction accepted.
        grade_distribution: Count per quality grade.
        common_rejection_reasons: Most frequent rejection reasons.
        common_warnings: Most frequent warnings.
        notes: Evaluation notes.
    """

    total_payloads: int
    accepted_count: int
    rejected_count: int
    acceptance_rate: float
    grade_distribution: dict[str, int] = field(default_factory=dict)
    common_rejection_reasons: list[str] = field(default_factory=list)
    common_warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def evaluate_ingestion_batch(
    batch_result: IngestionBatchResult,
) -> RuntimeIngestionEvalReport:
    """Evaluate a runtime ingestion batch result.

    Args:
        batch_result: The batch result from run_ingestion.

    Returns:
        A RuntimeIngestionEvalReport with aggregate metrics.
    """
    total = batch_result.total
    accepted = batch_result.accepted_count
    rejected = batch_result.rejected_count
    acceptance_rate = round(accepted / total, 4) if total > 0 else 0.0

    # Grade distribution
    from collections import Counter
    grade_counter: Counter = Counter()
    for r in batch_result.results:
        grade_counter[r.quality_grade] += 1

    # Common rejection reasons
    rejection_counter: Counter = Counter()
    for r in batch_result.results:
        if not r.accepted and r.diagnostics.rejection_reason:
            rejection_counter[r.diagnostics.rejection_reason] += 1
    common_rejections = [reason for reason, _ in rejection_counter.most_common(5)]

    # Common warnings
    warning_counter: Counter = Counter()
    for r in batch_result.results:
        for w in r.diagnostics.warnings:
            warning_counter[w] += 1
    common_warnings = [w for w, _ in warning_counter.most_common(5)]

    notes = [f"Evaluated {total} runtime payload(s): {accepted} accepted, {rejected} rejected."]

    return RuntimeIngestionEvalReport(
        total_payloads=total,
        accepted_count=accepted,
        rejected_count=rejected,
        acceptance_rate=acceptance_rate,
        grade_distribution=dict(grade_counter),
        common_rejection_reasons=common_rejections,
        common_warnings=common_warnings,
        notes=notes,
    )
