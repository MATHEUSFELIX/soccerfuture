"""Unit tests for consolidated trust report generation."""

from __future__ import annotations

from src.evaluation.trust_report import generate_trust_report, save_trust_report


# ---------------------------------------------------------------------------
# All-None inputs
# ---------------------------------------------------------------------------


def test_all_none_produces_report():
    """All None inputs → valid markdown with 'Not available'."""
    report = generate_trust_report()
    assert isinstance(report, str)
    assert "Not available" in report
    assert "# Consolidated Trust Report" in report


# ---------------------------------------------------------------------------
# Section presence
# ---------------------------------------------------------------------------


def test_human_eval_section_present():
    """human_eval_data provided → 'Human Evaluation Summary' in output."""
    data = {
        "overall_avg": 4.0,
        "scenario_count": 1,
        "evaluator_count": 1,
        "category_averages": {"general": 4.0},
    }
    report = generate_trust_report(human_eval_data=data)
    assert "## Human Evaluation Summary" in report
    assert "4.0" in report


def test_robustness_section_present():
    """robustness_data provided → 'Robustness Summary' in output."""
    data = {
        "summary": {
            "robust_count": 3,
            "sensitive_count": 1,
            "fragile_count": 0,
            "avg_validity_delta": 0.01,
            "avg_opportunity_delta": 0.02,
        }
    }
    report = generate_trust_report(robustness_data=data)
    assert "## Robustness Summary" in report
    assert "Robust" in report


def test_context_impact_section_present():
    """context_impact_data provided → 'Context Impact Summary' in output."""
    data = {
        "summary": {
            "scenarios_helped": ["s1"],
            "scenarios_neutral": [],
            "scenarios_degraded": [],
            "avg_validity_delta": 0.0,
            "avg_opportunity_delta": 0.0,
        }
    }
    report = generate_trust_report(context_impact_data=data)
    assert "## Context Impact Summary" in report


# ---------------------------------------------------------------------------
# Trust assessment levels
# ---------------------------------------------------------------------------


def test_high_trust_assessment():
    """overall_avg=4.0, fragile_count=0 → 'High trust'."""
    human = {"overall_avg": 4.0}
    robust = {"summary": {"fragile_count": 0}}
    report = generate_trust_report(human_eval_data=human, robustness_data=robust)
    assert "High trust" in report


def test_moderate_trust_assessment():
    """overall_avg=3.2, fragile_count=1 → 'Moderate trust'."""
    human = {"overall_avg": 3.2}
    robust = {"summary": {"fragile_count": 1}}
    report = generate_trust_report(human_eval_data=human, robustness_data=robust)
    assert "Moderate trust" in report


def test_low_trust_assessment():
    """overall_avg=2.0, fragile_count=5 → 'Low trust'."""
    human = {"overall_avg": 2.0}
    robust = {"summary": {"fragile_count": 5}}
    report = generate_trust_report(human_eval_data=human, robustness_data=robust)
    assert "Low trust" in report


# ---------------------------------------------------------------------------
# Missing stream notes
# ---------------------------------------------------------------------------


def test_missing_stream_notes():
    """Missing streams noted in assessment."""
    report = generate_trust_report()
    assert "missing Human Evaluation" in report
    assert "missing Robustness" in report
    assert "missing Context Impact" in report


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def test_recommendations_present():
    """'## Recommendations' in output."""
    report = generate_trust_report()
    assert "## Recommendations" in report
