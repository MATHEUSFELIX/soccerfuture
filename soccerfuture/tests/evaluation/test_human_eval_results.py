"""Unit tests for human evaluation results ingestion and summary."""

from __future__ import annotations

import pytest

from src.evaluation.human_eval_protocol import (
    HumanEvalProtocol,
    HumanEvalQuestion,
    HumanEvalScenario,
)
from src.evaluation.human_eval_results import (
    HumanEvalResponse,
    ingest_responses,
    load_results_json,
    save_results_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_protocol(scenario_ids: list[str] | None = None) -> HumanEvalProtocol:
    """Build a minimal protocol with standard questions."""
    ids = scenario_ids or ["s1"]
    questions = [
        HumanEvalQuestion("q_ranking", "Ranking?", category="ranking_quality"),
        HumanEvalQuestion("q_explanation", "Explanation?", category="explanation_clarity"),
    ]
    scenarios = [
        HumanEvalScenario(
            scenario_id=sid,
            play_state_file="test.json",
            pipeline_report={},
            questions=questions,
        )
        for sid in ids
    ]
    return HumanEvalProtocol(
        protocol_id="test_protocol",
        scenarios=scenarios,
        evaluator_instructions="Rate 1-5",
        created_at="2025-01-01T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ingest_single_response():
    """One response → correct avg_ratings."""
    protocol = _make_protocol()
    responses = [
        HumanEvalResponse(
            scenario_id="s1",
            evaluator_id="eval_1",
            ratings={"q_ranking": 4, "q_explanation": 3},
        ),
    ]
    summary = ingest_responses(responses, protocol)

    assert summary.scenario_count == 1
    assert summary.evaluator_count == 1
    assert summary.scenario_summaries[0].avg_ratings["q_ranking"] == 4.0
    assert summary.scenario_summaries[0].avg_ratings["q_explanation"] == 3.0


def test_ingest_multiple_evaluators():
    """Two evaluators → averaged ratings."""
    protocol = _make_protocol()
    responses = [
        HumanEvalResponse(
            scenario_id="s1",
            evaluator_id="eval_1",
            ratings={"q_ranking": 4, "q_explanation": 2},
        ),
        HumanEvalResponse(
            scenario_id="s1",
            evaluator_id="eval_2",
            ratings={"q_ranking": 2, "q_explanation": 4},
        ),
    ]
    summary = ingest_responses(responses, protocol)

    assert summary.evaluator_count == 2
    assert summary.scenario_summaries[0].avg_ratings["q_ranking"] == 3.0
    assert summary.scenario_summaries[0].avg_ratings["q_explanation"] == 3.0


def test_category_averages_computed():
    """Category averages match expected values."""
    protocol = _make_protocol()
    responses = [
        HumanEvalResponse(
            scenario_id="s1",
            evaluator_id="eval_1",
            ratings={"q_ranking": 5, "q_explanation": 3},
        ),
    ]
    summary = ingest_responses(responses, protocol)

    cat_avgs = summary.category_averages
    assert cat_avgs["ranking_quality"] == 5.0
    assert cat_avgs["explanation_clarity"] == 3.0


def test_overall_avg_computed():
    """Overall average across all ratings."""
    protocol = _make_protocol()
    responses = [
        HumanEvalResponse(
            scenario_id="s1",
            evaluator_id="eval_1",
            ratings={"q_ranking": 4, "q_explanation": 2},
        ),
    ]
    summary = ingest_responses(responses, protocol)
    # (4 + 2) / 2 = 3.0
    assert summary.overall_avg == 3.0


def test_empty_responses():
    """Empty list → scenario_count=0."""
    protocol = _make_protocol()
    summary = ingest_responses([], protocol)
    assert summary.scenario_count == 0
    assert summary.overall_avg == 0.0
    assert summary.evaluator_count == 0


def test_save_load_round_trip(tmp_path):
    """save_results_json then load_results_json round-trips."""
    protocol = _make_protocol()
    responses = [
        HumanEvalResponse(
            scenario_id="s1",
            evaluator_id="eval_1",
            ratings={"q_ranking": 4, "q_explanation": 3},
        ),
    ]
    summary = ingest_responses(responses, protocol)

    path = str(tmp_path / "results.json")
    save_results_json(summary, path)
    loaded = load_results_json(path)

    assert isinstance(loaded, dict)
    assert loaded["scenario_count"] == 1
    assert loaded["evaluator_count"] == 1
    assert loaded["overall_avg"] == summary.overall_avg
    assert "category_averages" in loaded
    assert "scenario_summaries" in loaded
