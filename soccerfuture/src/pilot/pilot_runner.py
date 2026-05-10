"""Pilot runner.

Executes a pilot plan by running batch workflows, gathering readiness
results, and producing the pilot report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.pilot.pilot_metrics import PilotMetrics, compute_pilot_metrics
from src.pilot.pilot_plan import PilotPlan
from src.pilot.pilot_report import generate_pilot_report
from src.review.demo_readiness import ReadinessResult
from src.review.review_feedback_ingest import FeedbackAggregate


@dataclass
class PilotResult:
    """Complete result of a pilot evaluation run.

    Attributes:
        pilot_id: Pilot identifier.
        metrics: Computed pilot metrics.
        report_markdown: Generated Markdown report.
        notes: Execution notes.
    """

    pilot_id: str
    metrics: PilotMetrics
    report_markdown: str
    notes: list[str] = field(default_factory=list)


def run_pilot(
    plan: PilotPlan,
    readiness_results: list[ReadinessResult],
    feedback_aggregate: FeedbackAggregate | None = None,
) -> PilotResult:
    """Execute a pilot evaluation from pre-computed results.

    In this phase, the pilot runner consumes already-generated
    readiness results and feedback rather than re-running workflows.

    Args:
        plan: The pilot plan.
        readiness_results: Readiness results for pilot scenarios.
        feedback_aggregate: Aggregated feedback, or None.

    Returns:
        A PilotResult with metrics and report.
    """
    metrics = compute_pilot_metrics(plan, readiness_results, feedback_aggregate)
    report = generate_pilot_report(plan, metrics, feedback_aggregate)

    return PilotResult(
        pilot_id=plan.pilot_id,
        metrics=metrics,
        report_markdown=report,
        notes=[f"Pilot '{plan.pilot_id}' evaluation complete."],
    )
