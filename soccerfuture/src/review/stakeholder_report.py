"""Stakeholder review summary report generation.

Produces a Markdown report combining review coverage, readiness
distribution, feedback aggregates, and recommendations.
"""

from __future__ import annotations

from src.review.demo_readiness import ReadinessResult
from src.review.review_feedback_ingest import FeedbackAggregate


def generate_stakeholder_report(
    readiness_results: list[ReadinessResult],
    feedback_aggregate: FeedbackAggregate | None = None,
) -> str:
    """Generate a Markdown stakeholder review report.

    Args:
        readiness_results: List of readiness evaluations for all scenarios.
        feedback_aggregate: Aggregated feedback metrics, or None if no
            feedback has been collected yet.

    Returns:
        Complete Markdown report string.
    """
    sections: list[str] = []

    # --- Header ---
    sections.append("# Stakeholder Review Report")
    sections.append("")

    # --- Review Coverage ---
    sections.append("## Review Coverage")
    sections.append("")
    total = len(readiness_results)
    ready = sum(1 for r in readiness_results if r.label == "ready")
    partial = sum(1 for r in readiness_results if r.label == "partially_ready")
    not_ready = sum(1 for r in readiness_results if r.label == "not_ready")

    sections.append(f"- **Total scenarios evaluated:** {total}")
    sections.append(f"- **Ready:** {ready}")
    sections.append(f"- **Partially ready:** {partial}")
    sections.append(f"- **Not ready:** {not_ready}")

    if feedback_aggregate is not None:
        sections.append(f"- **Feedback responses collected:** {feedback_aggregate.total_responses}")
        sections.append(f"- **Reviewers:** {feedback_aggregate.reviewer_count}")
    else:
        sections.append("- **Feedback:** Not yet collected")
    sections.append("")

    # --- Readiness Distribution ---
    sections.append("## Readiness Distribution")
    sections.append("")
    if total > 0:
        sections.append(f"- Ready: {ready}/{total} ({100*ready//total}%)")
        sections.append(f"- Partially ready: {partial}/{total} ({100*partial//total}%)")
        sections.append(f"- Not ready: {not_ready}/{total} ({100*not_ready//total}%)")
    else:
        sections.append("- No scenarios evaluated.")
    sections.append("")

    # --- Strongest Scenarios ---
    sections.append("## Strongest Scenarios")
    sections.append("")
    strongest = [r for r in readiness_results if r.label == "ready"]
    if strongest:
        for r in strongest[:5]:
            sections.append(f"- {r.scenario_id}")
    else:
        sections.append("- None fully ready yet.")
    sections.append("")

    # --- Weakest Scenarios ---
    sections.append("## Weakest Scenarios")
    sections.append("")
    weakest = [r for r in readiness_results if r.label == "not_ready"]
    if weakest:
        for r in weakest[:5]:
            reasons = "; ".join(r.reasons[:2]) if r.reasons else "No details"
            sections.append(f"- {r.scenario_id}: {reasons}")
    else:
        sections.append("- No scenarios classified as not ready.")
    sections.append("")

    # --- Feedback Insights (observations) ---
    if feedback_aggregate is not None and feedback_aggregate.total_responses > 0:
        sections.append("## Feedback Observations")
        sections.append("")
        sections.append(f"- **Top-1 plausibility rate:** {feedback_aggregate.top_1_plausibility_rate:.0%}")
        sections.append(f"- **Top-3 usefulness rate:** {feedback_aggregate.top_3_usefulness_rate:.0%}")
        sections.append(f"- **Avg summary clarity:** {feedback_aggregate.avg_summary_clarity:.1f}/5")
        sections.append(f"- **Avg confidence sufficiency:** {feedback_aggregate.avg_confidence_sufficiency:.1f}/5")
        sections.append("")

        # High disagreement
        if feedback_aggregate.high_disagreement_scenarios:
            sections.append("### High-Disagreement Scenarios")
            sections.append("")
            for sid in feedback_aggregate.high_disagreement_scenarios:
                sections.append(f"- {sid}")
            sections.append("")

        # Blockers
        if feedback_aggregate.blocker_frequencies:
            sections.append("### Most Common Blockers")
            sections.append("")
            for blocker, count in list(feedback_aggregate.blocker_frequencies.items())[:5]:
                sections.append(f"- {blocker} ({count}×)")
            sections.append("")

        # Requested improvements
        if feedback_aggregate.improvement_frequencies:
            sections.append("### Most Requested Improvements")
            sections.append("")
            for imp, count in list(feedback_aggregate.improvement_frequencies.items())[:5]:
                sections.append(f"- {imp} ({count}×)")
            sections.append("")

    # --- Recommendations ---
    sections.append("## Recommendations")
    sections.append("")
    recommendations: list[str] = []

    if not_ready > 0:
        recommendations.append(
            f"{not_ready} scenario(s) are not ready. "
            "Address critical failures before stakeholder demo."
        )
    if partial > 0:
        recommendations.append(
            f"{partial} scenario(s) are partially ready. "
            "Review missing artifacts and consider completing them."
        )
    if feedback_aggregate is not None:
        if feedback_aggregate.top_1_plausibility_rate < 0.7:
            recommendations.append(
                "Top-1 plausibility rate is below 70%. "
                "Review ranking quality and branch generation."
            )
        if feedback_aggregate.avg_summary_clarity < 3.0:
            recommendations.append(
                "Summary clarity is below 3.0/5. "
                "Improve analyst summary rendering."
            )
    if not recommendations:
        recommendations.append("No specific recommendations at this time.")

    for rec in recommendations:
        sections.append(f"- {rec}")
    sections.append("")

    return "\n".join(sections)
