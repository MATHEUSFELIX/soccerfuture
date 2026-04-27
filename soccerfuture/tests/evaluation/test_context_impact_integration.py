"""Integration tests for context impact paired pipeline execution.

Uses the counter_attack_midfield play state and teama_teamb fixture
context to exercise the full paired analysis flow.
"""

from __future__ import annotations

import json

import pytest

from src.evaluation.context_impact_analysis import (
    ContextImpactResult,
    ContextImpactSummary,
    run_batch_analysis,
    run_paired_analysis,
    save_analysis_json,
    load_analysis_json,
)
from src.integrations.soccerdata_adapter import get_match_context
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig


@pytest.fixture(scope="module")
def play_state():
    with open("data/play_states/counter_attack_midfield.json") as f:
        return dict_to_play_state(json.load(f))


@pytest.fixture(scope="module")
def match_context():
    return get_match_context("TeamA", "TeamB", use_cache=False)


@pytest.fixture(scope="module")
def config():
    return PipelineConfig(n=15, k=3, seed=42)


# ---------------------------------------------------------------------------
# TestPairedPipelineExecution
# ---------------------------------------------------------------------------


class TestPairedPipelineExecution:
    """End-to-end paired analysis with real pipeline runs."""

    def test_paired_analysis_returns_result(
        self, play_state, match_context, config
    ):
        result = run_paired_analysis(
            play_state, match_context, "integration_test", config
        )
        assert isinstance(result, ContextImpactResult)
        assert result.scenario_id == "integration_test"

    def test_paired_analysis_deterministic(
        self, play_state, match_context, config
    ):
        result_a = run_paired_analysis(
            play_state, match_context, "det_a", config
        )
        result_b = run_paired_analysis(
            play_state, match_context, "det_b", config
        )
        assert result_a.top_1_changed == result_b.top_1_changed
        assert result_a.no_context_top_1 == result_b.no_context_top_1
        assert result_a.with_context_top_1 == result_b.with_context_top_1
        assert result_a.avg_validity_delta == result_b.avg_validity_delta
        assert result_a.avg_opportunity_delta == result_b.avg_opportunity_delta

    def test_batch_analysis_returns_results_and_summary(
        self, play_state, match_context, config
    ):
        scenarios = [
            {
                "scenario_id": "batch_s1",
                "play_state": play_state,
                "match_context": match_context,
            }
        ]
        results, summary = run_batch_analysis(scenarios, config)
        assert len(results) == 1
        assert isinstance(results[0], ContextImpactResult)
        assert isinstance(summary, ContextImpactSummary)
        assert summary.scenario_count == 1


# ---------------------------------------------------------------------------
# TestJsonOutputSchema
# ---------------------------------------------------------------------------


class TestJsonOutputSchema:
    """Verify JSON output structure from save_analysis_json."""

    def test_json_output_has_required_keys(
        self, play_state, match_context, config, tmp_path
    ):
        result = run_paired_analysis(
            play_state, match_context, "json_test", config
        )
        summary = ContextImpactSummary(
            scenario_count=1,
            top_1_changed_count=int(result.top_1_changed),
            top_3_changed_count=0,
            neutral_context_count=0,
            partial_context_count=0,
            fallback_count=0,
            cache_hit_count=0,
            cache_miss_count=0,
            avg_validity_delta=result.avg_validity_delta,
            avg_opportunity_delta=result.avg_opportunity_delta,
            scenarios_helped=[],
            scenarios_neutral=["json_test"],
            scenarios_degraded=[],
            notes=[],
        )
        path = str(tmp_path / "output.json")
        save_analysis_json([result], summary, path)
        loaded = load_analysis_json(path)

        assert "results" in loaded
        assert "summary" in loaded
        assert "metadata" in loaded

    def test_json_results_have_required_fields(
        self, play_state, match_context, config, tmp_path
    ):
        result = run_paired_analysis(
            play_state, match_context, "fields_test", config
        )
        summary = ContextImpactSummary(
            scenario_count=1,
            top_1_changed_count=0,
            top_3_changed_count=0,
            neutral_context_count=0,
            partial_context_count=0,
            fallback_count=0,
            cache_hit_count=0,
            cache_miss_count=0,
            avg_validity_delta=0.0,
            avg_opportunity_delta=0.0,
            scenarios_helped=[],
            scenarios_neutral=[],
            scenarios_degraded=[],
            notes=[],
        )
        path = str(tmp_path / "output2.json")
        save_analysis_json([result], summary, path)
        loaded = load_analysis_json(path)

        required_fields = [
            "scenario_id",
            "top_1_changed",
            "avg_validity_delta",
            "avg_opportunity_delta",
            "no_context_top_1",
            "with_context_top_1",
        ]
        for r in loaded["results"]:
            for field in required_fields:
                assert field in r, f"Missing field: {field}"
