"""Human evaluation results ingestion and summary.

Ingests evaluator responses, computes per-scenario and aggregate
statistics, and provides JSON persistence for results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from src.evaluation.human_eval_protocol import HumanEvalProtocol


@dataclass
class HumanEvalResponse:
    """A single evaluator's response to one scenario.

    Attributes:
        scenario_id: Identifier of the evaluated scenario.
        evaluator_id: Identifier of the human evaluator.
        ratings: Mapping of question_id to rating value (1-5).
        notes: Optional free-text notes from the evaluator.
    """

    scenario_id: str
    evaluator_id: str
    ratings: dict[str, int]
    notes: str = ""


@dataclass
class HumanEvalScenarioSummary:
    """Aggregated ratings for one scenario.

    Attributes:
        scenario_id: Identifier of the scenario.
        avg_ratings: Average rating per question_id across evaluators.
        response_count: Number of evaluator responses for this scenario.
        category_averages: Average rating per question category.
        notes: Collected evaluator notes for this scenario.
    """

    scenario_id: str
    avg_ratings: dict[str, float]
    response_count: int
    category_averages: dict[str, float]
    notes: list[str]


@dataclass
class HumanEvalSummary:
    """Aggregate summary across all scenarios.

    Attributes:
        scenario_count: Number of distinct scenarios evaluated.
        evaluator_count: Number of distinct evaluators.
        overall_avg: Grand average across all ratings.
        category_averages: Average rating per question category
            across all scenarios.
        scenario_summaries: Per-scenario summary details.
        notes: All collected evaluator notes.
    """

    scenario_count: int
    evaluator_count: int
    overall_avg: float
    category_averages: dict[str, float]
    scenario_summaries: list[HumanEvalScenarioSummary]
    notes: list[str]


# ---------------------------------------------------------------------------
# Question category lookup
# ---------------------------------------------------------------------------


def _build_question_category_map(protocol: HumanEvalProtocol) -> dict[str, str]:
    """Build a mapping from question_id to category from the protocol.

    Scans all scenarios in the protocol to collect question categories.

    Args:
        protocol: The evaluation protocol containing question definitions.

    Returns:
        Dict mapping question_id to its category string.
    """
    category_map: dict[str, str] = {}
    for scenario in protocol.scenarios:
        for q in scenario.questions:
            category_map[q.question_id] = q.category
    return category_map


# ---------------------------------------------------------------------------
# Core ingestion
# ---------------------------------------------------------------------------


def ingest_responses(
    responses: list[HumanEvalResponse],
    protocol: HumanEvalProtocol,
) -> HumanEvalSummary:
    """Ingest evaluator responses and compute aggregate summary.

    Steps:
        1. Group responses by scenario_id.
        2. Compute average rating per question per scenario.
        3. Compute category averages using question.category from protocol.
        4. Compute overall average across all ratings.
        5. Return HumanEvalSummary.

    Args:
        responses: List of evaluator responses.
        protocol: The evaluation protocol (used for question categories).

    Returns:
        HumanEvalSummary with per-scenario and aggregate statistics.
    """
    question_categories = _build_question_category_map(protocol)

    # Group responses by scenario_id
    by_scenario: dict[str, list[HumanEvalResponse]] = {}
    for resp in responses:
        by_scenario.setdefault(resp.scenario_id, []).append(resp)

    # Track all evaluator IDs
    all_evaluator_ids: set[str] = {r.evaluator_id for r in responses}

    # Per-scenario summaries
    scenario_summaries: list[HumanEvalScenarioSummary] = []
    all_notes: list[str] = []
    all_ratings_flat: list[int] = []

    # Category totals across all scenarios
    global_category_totals: dict[str, float] = {}
    global_category_counts: dict[str, int] = {}

    for scenario_id, scenario_responses in by_scenario.items():
        # Average rating per question
        question_totals: dict[str, float] = {}
        question_counts: dict[str, int] = {}

        for resp in scenario_responses:
            for qid, rating in resp.ratings.items():
                question_totals[qid] = question_totals.get(qid, 0.0) + rating
                question_counts[qid] = question_counts.get(qid, 0) + 1
                all_ratings_flat.append(rating)

            if resp.notes:
                all_notes.append(resp.notes)

        avg_ratings: dict[str, float] = {}
        for qid in question_totals:
            avg_ratings[qid] = round(
                question_totals[qid] / question_counts[qid], 4
            )

        # Category averages for this scenario
        cat_totals: dict[str, float] = {}
        cat_counts: dict[str, int] = {}
        for qid, avg in avg_ratings.items():
            cat = question_categories.get(qid, "general")
            cat_totals[cat] = cat_totals.get(cat, 0.0) + avg
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            # Also accumulate into global category tracking
            global_category_totals[cat] = (
                global_category_totals.get(cat, 0.0) + avg
            )
            global_category_counts[cat] = (
                global_category_counts.get(cat, 0) + 1
            )

        category_averages: dict[str, float] = {}
        for cat in cat_totals:
            category_averages[cat] = round(
                cat_totals[cat] / cat_counts[cat], 4
            )

        scenario_summaries.append(
            HumanEvalScenarioSummary(
                scenario_id=scenario_id,
                avg_ratings=avg_ratings,
                response_count=len(scenario_responses),
                category_averages=category_averages,
                notes=[r.notes for r in scenario_responses if r.notes],
            )
        )

    # Overall average across all ratings
    overall_avg = 0.0
    if all_ratings_flat:
        overall_avg = round(sum(all_ratings_flat) / len(all_ratings_flat), 4)

    # Global category averages
    global_cat_avgs: dict[str, float] = {}
    for cat in global_category_totals:
        global_cat_avgs[cat] = round(
            global_category_totals[cat] / global_category_counts[cat], 4
        )

    return HumanEvalSummary(
        scenario_count=len(by_scenario),
        evaluator_count=len(all_evaluator_ids),
        overall_avg=overall_avg,
        category_averages=global_cat_avgs,
        scenario_summaries=scenario_summaries,
        notes=all_notes,
    )


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------


def _scenario_summary_to_dict(s: HumanEvalScenarioSummary) -> dict:
    """Convert a HumanEvalScenarioSummary to a JSON-serializable dict.

    Args:
        s: The scenario summary to serialize.

    Returns:
        Plain dict representation.
    """
    return {
        "scenario_id": s.scenario_id,
        "avg_ratings": s.avg_ratings,
        "response_count": s.response_count,
        "category_averages": s.category_averages,
        "notes": s.notes,
    }


def _summary_to_dict(summary: HumanEvalSummary) -> dict:
    """Convert a HumanEvalSummary to a JSON-serializable dict.

    Args:
        summary: The summary to serialize.

    Returns:
        Plain dict suitable for ``json.dumps``.
    """
    return {
        "scenario_count": summary.scenario_count,
        "evaluator_count": summary.evaluator_count,
        "overall_avg": summary.overall_avg,
        "category_averages": summary.category_averages,
        "scenario_summaries": [
            _scenario_summary_to_dict(s) for s in summary.scenario_summaries
        ],
        "notes": summary.notes,
    }


def save_results_json(summary: HumanEvalSummary, output_path: str) -> None:
    """Write a human evaluation summary to a JSON file.

    Args:
        summary: The summary to save.
        output_path: File path to write the JSON output.
    """
    data = _summary_to_dict(summary)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_results_json(path: str) -> dict:
    """Load a previously saved results JSON file.

    Args:
        path: File path to the JSON file.

    Returns:
        The parsed dict containing the summary data.
    """
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
