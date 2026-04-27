"""Unit tests for context impact analysis.

Covers classify_impact, compare_pipeline_runs, compute_aggregate_summary,
and JSON save/load round-trip.
"""

from __future__ import annotations

import json

import pytest

from src.evaluation.context_impact_analysis import (
    ContextImpactResult,
    ContextImpactSummary,
    classify_impact,
    compare_pipeline_runs,
    compute_aggregate_summary,
    load_analysis_json,
    save_analysis_json,
)
from src.models.pipeline_report import PipelineReport, RankedBranch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    *,
    scenario_id: str = "s1",
    top_1_changed: bool = False,
    avg_validity_delta: float = 0.0,
    avg_opportunity_delta: float = 0.0,
    context_applied: bool = True,
    context_partial: bool = False,
    cache_status: str | None = None,
    fallback_used: bool = False,
    viewer_artifacts: dict[str, str] | None = None,
) -> ContextImpactResult:
    """Build a minimal ContextImpactResult for testing."""
    return ContextImpactResult(
        scenario_id=scenario_id,
        no_context_top_1="branch_a",
        with_context_top_1="branch_b" if top_1_changed else "branch_a",
        top_1_changed=top_1_changed,
        no_context_top_3=["branch_a", "branch_b", "branch_c"],
        with_context_top_3=["branch_a", "branch_b", "branch_c"],
        top_3_changed=False,
        avg_validity_delta=avg_validity_delta,
        avg_opportunity_delta=avg_opportunity_delta,
        context_applied=context_applied,
        context_partial=context_partial,
        cache_status=cache_status,
        fallback_used=fallback_used,
        notes=[],
        viewer_artifacts=viewer_artifacts,
    )


def _make_report(
    branch_ids: list[str],
    validity_scores: list[float] | None = None,
    opportunity_scores: list[float] | None = None,
    metadata: dict | None = None,
    errors: list[str] | None = None,
) -> PipelineReport:
    """Build a PipelineReport with the given ranked branches."""
    n = len(branch_ids)
    v_scores = validity_scores or [0.5] * n
    o_scores = opportunity_scores or [0.5] * n

    ranked = [
        RankedBranch(
            branch_id=bid,
            composite_score=(v + o) / 2,
            evaluation_report={"validity_score": v, "opportunity_score": o},
            branch={"branch_id": bid},
        )
        for bid, v, o in zip(branch_ids, v_scores, o_scores)
    ]
    return PipelineReport(
        play_state={},
        evaluated_branches=[],
        ranked_branches=ranked,
        metadata=metadata or {},
        errors=errors or [],
    )


# ---------------------------------------------------------------------------
# TestClassifyImpact
# ---------------------------------------------------------------------------


class TestClassifyImpact:
    """Tests for classify_impact classification logic."""

    def test_helpful_when_top1_changed_and_positive_delta(self):
        result = _make_result(top_1_changed=True, avg_opportunity_delta=0.05)
        assert classify_impact(result) == "helpful"

    def test_degrading_when_opportunity_below_threshold(self):
        result = _make_result(avg_opportunity_delta=-0.06)
        assert classify_impact(result) == "degrading"

    def test_degrading_when_validity_below_threshold(self):
        result = _make_result(avg_validity_delta=-0.06)
        assert classify_impact(result) == "degrading"

    def test_neutral_when_no_change(self):
        result = _make_result(
            top_1_changed=False,
            avg_validity_delta=0.01,
            avg_opportunity_delta=0.01,
        )
        assert classify_impact(result) == "neutral"

    def test_neutral_when_top1_changed_but_small_delta(self):
        result = _make_result(top_1_changed=True, avg_opportunity_delta=0.01)
        assert classify_impact(result) == "neutral"


# ---------------------------------------------------------------------------
# TestComparePipelineRuns
# ---------------------------------------------------------------------------


class TestComparePipelineRuns:
    """Tests for compare_pipeline_runs diff logic."""

    def test_same_reports_produce_no_change(self):
        report = _make_report(["b1", "b2", "b3"])
        result = compare_pipeline_runs(report, report, "scenario_same")
        assert result.top_1_changed is False
        assert result.avg_validity_delta == 0.0
        assert result.avg_opportunity_delta == 0.0

    def test_different_top1_detected(self):
        no_ctx = _make_report(["alpha", "beta"])
        with_ctx = _make_report(["gamma", "beta"])
        result = compare_pipeline_runs(no_ctx, with_ctx, "scenario_diff")
        assert result.top_1_changed is True
        assert result.no_context_top_1 == "alpha"
        assert result.with_context_top_1 == "gamma"

    def test_score_deltas_computed_correctly(self):
        no_ctx = _make_report(
            ["b1", "b2"],
            validity_scores=[0.4, 0.6],
            opportunity_scores=[0.3, 0.5],
        )
        with_ctx = _make_report(
            ["b1", "b2"],
            validity_scores=[0.5, 0.7],
            opportunity_scores=[0.4, 0.6],
        )
        result = compare_pipeline_runs(no_ctx, with_ctx, "scenario_scores")
        # avg validity: no_ctx = (0.4+0.6)/2=0.5, with_ctx = (0.5+0.7)/2=0.6 → delta=0.1
        assert abs(result.avg_validity_delta - 0.1) < 1e-4
        # avg opportunity: no_ctx = (0.3+0.5)/2=0.4, with_ctx = (0.4+0.6)/2=0.5 → delta=0.1
        assert abs(result.avg_opportunity_delta - 0.1) < 1e-4


# ---------------------------------------------------------------------------
# TestComputeAggregateSummary
# ---------------------------------------------------------------------------


class TestComputeAggregateSummary:
    """Tests for compute_aggregate_summary aggregation logic."""

    def test_empty_results(self):
        summary = compute_aggregate_summary([])
        assert summary.scenario_count == 0
        assert summary.scenarios_helped == []
        assert summary.scenarios_neutral == []
        assert summary.scenarios_degraded == []

    def test_single_neutral_result(self):
        result = _make_result(scenario_id="s_neutral")
        summary = compute_aggregate_summary([result])
        assert summary.scenario_count == 1
        assert summary.scenarios_neutral == ["s_neutral"]
        assert summary.scenarios_helped == []
        assert summary.scenarios_degraded == []

    def test_mixed_results(self):
        helpful = _make_result(
            scenario_id="s_help",
            top_1_changed=True,
            avg_opportunity_delta=0.05,
        )
        neutral = _make_result(scenario_id="s_neut")
        degrading = _make_result(
            scenario_id="s_deg",
            avg_opportunity_delta=-0.06,
        )
        summary = compute_aggregate_summary([helpful, neutral, degrading])
        assert summary.scenario_count == 3
        assert "s_help" in summary.scenarios_helped
        assert "s_neut" in summary.scenarios_neutral
        assert "s_deg" in summary.scenarios_degraded


# ---------------------------------------------------------------------------
# TestSaveLoadJson
# ---------------------------------------------------------------------------


class TestSaveLoadJson:
    """Tests for JSON persistence round-trip."""

    def test_round_trip(self, tmp_path):
        result = _make_result(scenario_id="rt_test")
        summary = compute_aggregate_summary([result])
        path = str(tmp_path / "analysis.json")

        save_analysis_json([result], summary, path)
        loaded = load_analysis_json(path)

        assert "results" in loaded
        assert "summary" in loaded
        assert "metadata" in loaded
        assert len(loaded["results"]) == 1
        assert loaded["results"][0]["scenario_id"] == "rt_test"
        assert loaded["summary"]["scenario_count"] == 1
