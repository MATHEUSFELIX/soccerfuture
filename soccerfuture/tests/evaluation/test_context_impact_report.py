"""Unit tests for context impact Markdown report generation.

Covers section presence, recommendation logic, and viewer artifact handling.
"""

from __future__ import annotations

import pytest

from src.evaluation.context_impact_report import generate_markdown_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_analysis_data(
    *,
    scenarios_helped: list[str] | None = None,
    scenarios_neutral: list[str] | None = None,
    scenarios_degraded: list[str] | None = None,
    results: list[dict] | None = None,
) -> dict:
    """Build a minimal analysis data dict for report generation."""
    helped = scenarios_helped or []
    neutral = scenarios_neutral or []
    degraded = scenarios_degraded or []
    total = len(helped) + len(neutral) + len(degraded)

    return {
        "metadata": {
            "generated_at": "2025-01-01T00:00:00Z",
            "scenario_count": total,
        },
        "summary": {
            "scenario_count": total,
            "top_1_changed_count": len(helped),
            "top_3_changed_count": 0,
            "neutral_context_count": 0,
            "partial_context_count": 0,
            "fallback_count": 0,
            "cache_hit_count": 0,
            "cache_miss_count": 0,
            "avg_validity_delta": 0.0,
            "avg_opportunity_delta": 0.0,
            "scenarios_helped": helped,
            "scenarios_neutral": neutral,
            "scenarios_degraded": degraded,
            "notes": [],
        },
        "results": results or [],
    }


# ---------------------------------------------------------------------------
# TestGenerateMarkdownReport
# ---------------------------------------------------------------------------


class TestGenerateMarkdownReport:
    """Tests for generate_markdown_report output content."""

    def test_contains_overview_header(self):
        data = _make_analysis_data()
        md = generate_markdown_report(data)
        assert "# Context Impact Evaluation Report" in md

    def test_contains_aggregate_metrics_table(self):
        data = _make_analysis_data(scenarios_neutral=["s1"])
        md = generate_markdown_report(data)
        assert "## Aggregate Metrics" in md
        assert "| Metric | Value |" in md

    def test_contains_helped_section(self):
        data = _make_analysis_data(scenarios_helped=["s_help"])
        md = generate_markdown_report(data)
        assert "## Scenarios Helped" in md

    def test_contains_neutral_section(self):
        data = _make_analysis_data(scenarios_neutral=["s_neut"])
        md = generate_markdown_report(data)
        assert "## Scenarios Neutral" in md

    def test_contains_degraded_section(self):
        data = _make_analysis_data(scenarios_degraded=["s_deg"])
        md = generate_markdown_report(data)
        assert "## Scenarios Degraded" in md

    def test_contains_recommendations(self):
        data = _make_analysis_data()
        md = generate_markdown_report(data)
        assert "## Recommendations" in md

    def test_all_neutral_recommendation(self):
        data = _make_analysis_data(scenarios_neutral=["s1", "s2"])
        md = generate_markdown_report(data)
        assert "minimal impact" in md

    def test_degraded_recommendation(self):
        data = _make_analysis_data(scenarios_degraded=["s_deg"])
        md = generate_markdown_report(data)
        assert "review" in md.lower()
        assert "thresholds" in md.lower()

    def test_viewer_artifacts_included(self):
        result_with_artifacts = {
            "scenario_id": "s_art",
            "notes": [],
            "viewer_artifacts": {
                "no_context": "/renders/no_ctx.html",
                "with_context": "/renders/with_ctx.html",
            },
        }
        data = _make_analysis_data(
            scenarios_helped=["s_art"],
            results=[result_with_artifacts],
        )
        md = generate_markdown_report(data)
        assert "/renders/no_ctx.html" in md
        assert "/renders/with_ctx.html" in md

    def test_viewer_artifacts_absent_no_error(self):
        result_no_artifacts = {
            "scenario_id": "s_plain",
            "notes": [],
            "viewer_artifacts": None,
        }
        data = _make_analysis_data(
            scenarios_neutral=["s_plain"],
            results=[result_no_artifacts],
        )
        # Should not raise
        md = generate_markdown_report(data)
        assert "## Scenarios Neutral" in md
