"""Pilot metrics aggregation.

Computes pilot-level metrics from readiness results and feedback
aggregates to evaluate whether success criteria are met.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.pilot.pilot_plan import PilotPlan
from src.review.demo_readiness import ReadinessResult
from src.review.review_feedback_ingest import FeedbackAggregate


@dataclass
class PilotMetrics:
    """Aggregated metrics for a pilot evaluation.

    Attributes:
        pilot_id: Pilot identifier.
        scenario_count: Number of scenarios in the pilot.
        ready_count: Scenarios classified as ready.
        partially_ready_count: Scenarios partially ready.
        not_ready_count: Scenarios not ready.
        readiness_rate: Fraction of scenarios that are ready.
        feedback_coverage: Fraction of scenarios with feedback.
        avg_plausibility_rate: Average top-1 plausibility rate.
        avg_clarity: Average summary clarity rating.
        success_criteria_met: Dict of metric name to whether target was met.
        notes: Evaluation notes.
    """

    pilot_id: str
    scenario_count: int
    ready_count: int
    partially_ready_count: int
    not_ready_count: int
    readiness_rate: float
    feedback_coverage: float
    avg_plausibility_rate: float
    avg_clarity: float
    success_criteria_met: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def compute_pilot_metrics(
    plan: PilotPlan,
    readiness_results: list[ReadinessResult],
    feedback_aggregate: FeedbackAggregate | None = None,
) -> PilotMetrics:
    """Compute pilot metrics from readiness and feedback data.

    Args:
        plan: The pilot plan defining success criteria.
        readiness_results: Readiness results for pilot scenarios.
        feedback_aggregate: Aggregated feedback, or None.

    Returns:
        A PilotMetrics instance with computed values.
    """
    scenario_count = len(readiness_results)
    ready = sum(1 for r in readiness_results if r.label == "ready")
    partial = sum(1 for r in readiness_results if r.label == "partially_ready")
    not_ready = sum(1 for r in readiness_results if r.label == "not_ready")
    readiness_rate = round(ready / scenario_count, 4) if scenario_count > 0 else 0.0

    # Feedback metrics
    feedback_coverage = 0.0
    avg_plausibility = 0.0
    avg_clarity = 0.0
    if feedback_aggregate and feedback_aggregate.total_responses > 0:
        feedback_coverage = round(
            feedback_aggregate.scenario_count / scenario_count, 4
        ) if scenario_count > 0 else 0.0
        avg_plausibility = feedback_aggregate.top_1_plausibility_rate
        avg_clarity = feedback_aggregate.avg_summary_clarity

    # Evaluate success criteria
    criteria_met: dict[str, bool] = {}
    for metric_name, target in plan.success_metrics.items():
        if metric_name == "readiness_rate":
            criteria_met[metric_name] = readiness_rate >= target
        elif metric_name == "plausibility_rate":
            criteria_met[metric_name] = avg_plausibility >= target
        elif metric_name == "clarity_avg":
            criteria_met[metric_name] = avg_clarity >= target
        elif metric_name == "feedback_coverage":
            criteria_met[metric_name] = feedback_coverage >= target
        else:
            criteria_met[metric_name] = False  # Unknown metric

    notes: list[str] = [
        f"Pilot '{plan.pilot_id}': {scenario_count} scenarios, "
        f"{ready} ready, {partial} partial, {not_ready} not ready."
    ]

    return PilotMetrics(
        pilot_id=plan.pilot_id,
        scenario_count=scenario_count,
        ready_count=ready,
        partially_ready_count=partial,
        not_ready_count=not_ready,
        readiness_rate=readiness_rate,
        feedback_coverage=feedback_coverage,
        avg_plausibility_rate=avg_plausibility,
        avg_clarity=avg_clarity,
        success_criteria_met=criteria_met,
        notes=notes,
    )
