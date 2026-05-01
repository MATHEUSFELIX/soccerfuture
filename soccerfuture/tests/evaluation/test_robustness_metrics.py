"""Unit tests for robustness classification and aggregate metrics."""

from __future__ import annotations

import pytest

from src.evaluation.robustness_metrics import (
    RobustnessSummary,
    classify_robustness,
    compute_robustness_summary,
    load_robustness_json,
    save_robustness_json,
)
from src.evaluation.robustness_suite import RobustnessResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    *,
    scenario_id: str = "s1",
    strategy: str = "noise",
    top_1_changed: bool = False,
    avg_validity_delta: float = 0.0,
    avg_opportunity_delta: float = 0.0,
) -> RobustnessResult:
    """Build a minimal RobustnessResult for testing."""
    return RobustnessResult(
        scenario_id=scenario_id,
        strategy=strategy,
        baseline_top_1="branch_a",
        degraded_top_1="branch_b" if top_1_changed else "branch_a",
        top_1_changed=top_1_changed,
        baseline_top_3=["branch_a", "branch_b", "branch_c"],
        degraded_top_3=["branch_a", "branch_b", "branch_c"],
        top_3_changed=False,
        avg_validity_delta=avg_validity_delta,
        avg_opportunity_delta=avg_opportunity_delta,
        gating_pass_delta=0,
    )


# ---------------------------------------------------------------------------
# classify_robustness
# ---------------------------------------------------------------------------


def test_classify_robust():
    """Small deltas, no top_1_change → 'robust'."""
    result = _make_result(
        avg_validity_delta=0.01,
        avg_opportunity_delta=0.01,
        top_1_changed=False,
    )
    assert classify_robustness(result) == "robust"


def test_classify_sensitive():
    """top_1_changed with moderate deltas → 'sensitive'."""
    result = _make_result(
        avg_validity_delta=-0.05,
        avg_opportunity_delta=-0.05,
        top_1_changed=True,
    )
    assert classify_robustness(result) == "sensitive"


def test_classify_fragile_validity():
    """Large negative validity delta → 'fragile'."""
    result = _make_result(avg_validity_delta=-0.15)
    assert classify_robustness(result) == "fragile"


def test_classify_fragile_opportunity():
    """Large negative opportunity delta → 'fragile'."""
    result = _make_result(avg_opportunity_delta=-0.15)
    assert classify_robustness(result) == "fragile"


# ---------------------------------------------------------------------------
# compute_robustness_summary
# ---------------------------------------------------------------------------


def test_compute_summary_empty():
    """Empty list → zero counts."""
    summary = compute_robustness_summary([])
    assert summary.robust_count == 0
    assert summary.sensitive_count == 0
    assert summary.fragile_count == 0
    assert summary.total_runs == 0


def test_compute_summary_mixed():
    """Mix of robust/sensitive/fragile → correct counts."""
    robust = _make_result(
        scenario_id="r1",
        strategy="noise",
        avg_validity_delta=0.01,
        avg_opportunity_delta=0.01,
        top_1_changed=False,
    )
    sensitive = _make_result(
        scenario_id="r2",
        strategy="time_shift",
        avg_validity_delta=-0.05,
        avg_opportunity_delta=-0.05,
        top_1_changed=True,
    )
    fragile = _make_result(
        scenario_id="r3",
        strategy="missing_players",
        avg_validity_delta=-0.15,
    )
    summary = compute_robustness_summary([robust, sensitive, fragile])

    assert summary.robust_count == 1
    assert summary.sensitive_count == 1
    assert summary.fragile_count == 1
    assert summary.total_runs == 3


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------


def test_save_load_round_trip(tmp_path):
    """save then load JSON round-trips."""
    results = [
        _make_result(scenario_id="rt1", strategy="noise"),
        _make_result(
            scenario_id="rt2",
            strategy="time_shift",
            avg_validity_delta=-0.15,
        ),
    ]
    summary = compute_robustness_summary(results)

    path = str(tmp_path / "robustness.json")
    save_robustness_json(results, summary, path)
    loaded = load_robustness_json(path)

    assert isinstance(loaded, dict)
    assert "results" in loaded
    assert "summary" in loaded
    assert "metadata" in loaded
    assert len(loaded["results"]) == 2
    assert loaded["summary"]["total_runs"] == 2
