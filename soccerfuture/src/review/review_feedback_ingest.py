"""Feedback ingestion and aggregation.

Ingests structured ReviewFeedback records and produces deterministic
aggregate metrics for stakeholder reporting.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from src.review.review_feedback_schema import ReviewFeedback


@dataclass
class FeedbackAggregate:
    """Aggregate metrics from multiple reviewer feedback records.

    Attributes:
        total_responses: Total number of feedback records ingested.
        scenario_count: Number of distinct scenarios reviewed.
        reviewer_count: Number of distinct reviewers.
        top_1_plausibility_rate: Fraction of "yes" responses for top-1.
        top_3_usefulness_rate: Fraction of "yes" or "partially" for top-3.
        avg_summary_clarity: Average summary clarity rating.
        avg_confidence_sufficiency: Average confidence sufficiency rating.
        blocker_frequencies: Counter of blocker strings.
        improvement_frequencies: Counter of missing capability strings.
        high_disagreement_scenarios: Scenarios where reviewers disagree on top-1.
        notes: Aggregate notes.
    """

    total_responses: int
    scenario_count: int
    reviewer_count: int
    top_1_plausibility_rate: float
    top_3_usefulness_rate: float
    avg_summary_clarity: float
    avg_confidence_sufficiency: float
    blocker_frequencies: dict[str, int] = field(default_factory=dict)
    improvement_frequencies: dict[str, int] = field(default_factory=dict)
    high_disagreement_scenarios: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def ingest_feedback(
    feedback_records: list[ReviewFeedback],
) -> FeedbackAggregate:
    """Ingest feedback records and compute aggregate metrics.

    Args:
        feedback_records: List of validated ReviewFeedback instances.

    Returns:
        A FeedbackAggregate with computed metrics.
    """
    if not feedback_records:
        return FeedbackAggregate(
            total_responses=0,
            scenario_count=0,
            reviewer_count=0,
            top_1_plausibility_rate=0.0,
            top_3_usefulness_rate=0.0,
            avg_summary_clarity=0.0,
            avg_confidence_sufficiency=0.0,
            notes=["No feedback records to aggregate."],
        )

    total = len(feedback_records)
    scenarios = {fb.scenario_id for fb in feedback_records}
    reviewers = {fb.reviewer_id for fb in feedback_records}

    # Plausibility rate
    plausible_count = sum(
        1 for fb in feedback_records if fb.top_1_plausibility == "yes"
    )
    top_1_plausibility_rate = round(plausible_count / total, 4)

    # Usefulness rate (yes or partially)
    useful_count = sum(
        1 for fb in feedback_records
        if fb.top_3_usefulness in ("yes", "partially")
    )
    top_3_usefulness_rate = round(useful_count / total, 4)

    # Average ratings
    avg_clarity = round(
        sum(fb.summary_clarity for fb in feedback_records) / total, 4
    )
    avg_confidence = round(
        sum(fb.confidence_sufficiency for fb in feedback_records) / total, 4
    )

    # Blocker frequencies
    blocker_counter: Counter = Counter()
    for fb in feedback_records:
        for blocker in fb.blockers:
            blocker_counter[blocker] += 1

    # Improvement frequencies
    improvement_counter: Counter = Counter()
    for fb in feedback_records:
        for cap in fb.missing_capabilities:
            improvement_counter[cap] += 1

    # High-disagreement scenarios: scenarios where reviewers disagree on top-1
    by_scenario: dict[str, list[str]] = {}
    for fb in feedback_records:
        by_scenario.setdefault(fb.scenario_id, []).append(fb.top_1_plausibility)

    high_disagreement: list[str] = []
    for sid, responses in sorted(by_scenario.items()):
        unique = set(responses)
        if len(unique) > 1 and len(responses) > 1:
            high_disagreement.append(sid)

    notes: list[str] = [
        f"Aggregated {total} response(s) from {len(reviewers)} reviewer(s) "
        f"across {len(scenarios)} scenario(s)."
    ]

    return FeedbackAggregate(
        total_responses=total,
        scenario_count=len(scenarios),
        reviewer_count=len(reviewers),
        top_1_plausibility_rate=top_1_plausibility_rate,
        top_3_usefulness_rate=top_3_usefulness_rate,
        avg_summary_clarity=avg_clarity,
        avg_confidence_sufficiency=avg_confidence,
        blocker_frequencies=dict(blocker_counter.most_common()),
        improvement_frequencies=dict(improvement_counter.most_common()),
        high_disagreement_scenarios=high_disagreement,
        notes=notes,
    )


def aggregate_to_dict(agg: FeedbackAggregate) -> dict:
    """Convert a FeedbackAggregate to a JSON-serializable dict."""
    return {
        "total_responses": agg.total_responses,
        "scenario_count": agg.scenario_count,
        "reviewer_count": agg.reviewer_count,
        "top_1_plausibility_rate": agg.top_1_plausibility_rate,
        "top_3_usefulness_rate": agg.top_3_usefulness_rate,
        "avg_summary_clarity": agg.avg_summary_clarity,
        "avg_confidence_sufficiency": agg.avg_confidence_sufficiency,
        "blocker_frequencies": agg.blocker_frequencies,
        "improvement_frequencies": agg.improvement_frequencies,
        "high_disagreement_scenarios": agg.high_disagreement_scenarios,
        "notes": agg.notes,
    }
