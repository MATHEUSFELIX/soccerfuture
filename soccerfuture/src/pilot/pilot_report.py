"""Pilot report generator.

Produces a Markdown pilot evaluation report with observations,
metrics, and evidence-based recommendations.
"""

from __future__ import annotations

from src.pilot.pilot_metrics import PilotMetrics
from src.pilot.pilot_plan import PilotPlan
from src.review.review_feedback_ingest import FeedbackAggregate


def generate_pilot_report(
    plan: PilotPlan,
    metrics: PilotMetrics,
    feedback_aggregate: FeedbackAggregate | None = None,
) -> str:
    """Generate a Markdown pilot evaluation report.

    Args:
        plan: The pilot plan.
        metrics: Computed pilot metrics.
        feedback_aggregate: Aggregated feedback, or None.

    Returns:
        Complete Markdown report string.
    """
    lines: list[str] = []

    # Header
    lines.append(f"# Pilot Evaluation Report: {plan.pilot_id}")
    lines.append("")
    if plan.description:
        lines.append(f"_{plan.description}_")
        lines.append("")

    # Overview
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- **Scenarios:** {metrics.scenario_count}")
    lines.append(f"- **Reviewers planned:** {len(plan.reviewer_ids)}")
    lines.append(f"- **Readiness rate:** {metrics.readiness_rate:.0%}")
    lines.append(f"- **Feedback coverage:** {metrics.feedback_coverage:.0%}")
    lines.append("")

    # Readiness
    lines.append("## Readiness Distribution")
    lines.append("")
    lines.append(f"- Ready: {metrics.ready_count}")
    lines.append(f"- Partially ready: {metrics.partially_ready_count}")
    lines.append(f"- Not ready: {metrics.not_ready_count}")
    lines.append("")

    # Quality Observations
    lines.append("## Quality Observations")
    lines.append("")
    lines.append(f"- **Top-1 plausibility rate:** {metrics.avg_plausibility_rate:.0%}")
    lines.append(f"- **Avg summary clarity:** {metrics.avg_clarity:.1f}/5")
    lines.append("")

    if feedback_aggregate and feedback_aggregate.blocker_frequencies:
        lines.append("### Top Blockers")
        lines.append("")
        for blocker, count in list(feedback_aggregate.blocker_frequencies.items())[:5]:
            lines.append(f"- {blocker} ({count}×)")
        lines.append("")

    if feedback_aggregate and feedback_aggregate.improvement_frequencies:
        lines.append("### Top Requested Improvements")
        lines.append("")
        for imp, count in list(feedback_aggregate.improvement_frequencies.items())[:5]:
            lines.append(f"- {imp} ({count}×)")
        lines.append("")

    # Success Criteria
    lines.append("## Success Criteria")
    lines.append("")
    if metrics.success_criteria_met:
        for metric, met in metrics.success_criteria_met.items():
            status = "✓ Met" if met else "✗ Not met"
            target = plan.success_metrics.get(metric, "?")
            lines.append(f"- **{metric}:** {status} (target: {target})")
    else:
        lines.append("- No success criteria defined.")
    lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    recommendations: list[str] = []

    all_met = all(metrics.success_criteria_met.values()) if metrics.success_criteria_met else False

    if all_met:
        recommendations.append("All success criteria met. Consider expanding pilot scope or moving to production.")
    else:
        not_met = [k for k, v in metrics.success_criteria_met.items() if not v]
        if not_met:
            recommendations.append(f"Criteria not met: {', '.join(not_met)}. Address before expanding.")

    if metrics.not_ready_count > 0:
        recommendations.append(f"{metrics.not_ready_count} scenario(s) not ready. Fix critical failures.")

    if metrics.avg_plausibility_rate < 0.7:
        recommendations.append("Plausibility rate below 70%. Review ranking quality.")

    if metrics.avg_clarity < 3.0:
        recommendations.append("Clarity below 3.0/5. Improve summary generation.")

    if not recommendations:
        recommendations.append("No specific recommendations at this time.")

    for rec in recommendations:
        lines.append(f"- {rec}")
    lines.append("")

    return "\n".join(lines)
