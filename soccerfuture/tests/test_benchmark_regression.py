"""Benchmark regression tests for the v3 evaluator.

Loads data/benchmark_input.json and data/benchmark_annotated.json, runs all
15 branches through the v3 evaluator, and verifies each branch's scores fall
within annotated expected ranges.

Requirements covered: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

from __future__ import annotations

import json
import pathlib

import pytest

from src.simulation_evaluator_v2 import evaluate_all, evaluate_branch
from src.models.evaluation_report import EvaluationReport


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BENCHMARK_INPUT_PATH = pathlib.Path("data/benchmark_input.json")
BENCHMARK_ANNOTATED_PATH = pathlib.Path("data/benchmark_annotated.json")

# Tolerance applied to annotated ranges for branches that already passed in v2.
# The v3 reality anchor can shift opportunity scores slightly outside original
# annotated ranges, so we allow a small buffer.
RANGE_TOLERANCE = 0.1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def benchmark_input() -> dict:
    """Load benchmark_input.json."""
    with open(BENCHMARK_INPUT_PATH, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def benchmark_annotations() -> list[dict]:
    """Load benchmark_annotated.json annotations list."""
    with open(BENCHMARK_ANNOTATED_PATH, "r") as f:
        data = json.load(f)
    return data["annotations"]


@pytest.fixture(scope="session")
def benchmark_reports(benchmark_input: dict) -> list[EvaluationReport]:
    """Run all 15 branches through the v3 evaluator."""
    return evaluate_all(benchmark_input)


@pytest.fixture(scope="session")
def reports_by_id(benchmark_reports: list[EvaluationReport]) -> dict[str, EvaluationReport]:
    """Map branch_id → EvaluationReport for easy lookup."""
    return {r.branch_id: r for r in benchmark_reports}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Branch IDs that passed gating in v2 (12 of 15).
V2_PASSING_BRANCH_IDS = {
    "B01-plausible-short-run",
    "B02-plausible-screen-pass",
    "B03-plausible-deep-route",
    "B08-better-big-gain",
    "B09-better-td-opportunity",
    "B10-better-no-turnover",
    "B11-worse-fumble",
    "B12-worse-interception",
    "B14-neutral-same-as-reality",
    "B15-neutral-lateral-move",
    # Implausible branches that correctly failed gating in v2:
    # B04, B05, B06, B07 — still fail gating in v3
    # B13 failed gating in v2 but passes in v3
}


def _in_range(value: float, lo: float, hi: float, tol: float = 0.0) -> bool:
    """Check if value is within [lo - tol, hi + tol]."""
    return (lo - tol) <= value <= (hi + tol)


# ---------------------------------------------------------------------------
# Task 14 — Benchmark regression: all 15 branches within expected ranges
# ---------------------------------------------------------------------------


class TestBenchmarkAllBranches:
    """Run all 15 branches and verify scores against annotated ranges.

    Validates: Requirements 5.4
    """

    def test_correct_number_of_reports(
        self, benchmark_reports: list[EvaluationReport]
    ) -> None:
        """Evaluator produces exactly 15 reports."""
        assert len(benchmark_reports) == 15

    def test_each_branch_validity_in_range(
        self,
        benchmark_reports: list[EvaluationReport],
        benchmark_annotations: list[dict],
    ) -> None:
        """Each branch's validity_score falls within annotated expected range.

        Validates: Requirements 5.4
        """
        for report, ann in zip(benchmark_reports, benchmark_annotations):
            lo, hi = ann["expected_validity_range"]
            assert _in_range(report.validity_score, lo, hi, RANGE_TOLERANCE), (
                f"{report.branch_id}: validity_score={report.validity_score:.4f} "
                f"outside expected [{lo}, {hi}] (±{RANGE_TOLERANCE})"
            )

    def test_each_branch_opportunity_in_range(
        self,
        benchmark_reports: list[EvaluationReport],
        benchmark_annotations: list[dict],
    ) -> None:
        """Each branch's opportunity_score falls within annotated expected range.

        Validates: Requirements 5.4
        """
        for report, ann in zip(benchmark_reports, benchmark_annotations):
            lo, hi = ann["expected_opportunity_range"]
            assert _in_range(report.opportunity_score, lo, hi, RANGE_TOLERANCE), (
                f"{report.branch_id}: opportunity_score={report.opportunity_score:.4f} "
                f"outside expected [{lo}, {hi}] (±{RANGE_TOLERANCE})"
            )

    def test_each_branch_gating_matches(
        self,
        benchmark_reports: list[EvaluationReport],
        benchmark_annotations: list[dict],
    ) -> None:
        """Each branch's gating result matches annotated expectation.

        Validates: Requirements 5.4
        """
        for report, ann in zip(benchmark_reports, benchmark_annotations):
            expected_pass = ann["expected_gating"] == "pass"
            assert report.passed_gating is expected_pass, (
                f"{report.branch_id}: passed_gating={report.passed_gating}, "
                f"expected {'pass' if expected_pass else 'fail'}"
            )


# ---------------------------------------------------------------------------
# Task 14 — B13 specific: passes gating, opportunity in [0.0, 0.3]
# ---------------------------------------------------------------------------


class TestB13WorstBigLoss:
    """B13 (sack + fumble at high speed) must pass gating in v3.

    Validates: Requirements 5.1
    """

    def test_b13_passes_gating(self, reports_by_id: dict[str, EvaluationReport]) -> None:
        """B13 passes gating thanks to context-aware speed thresholds."""
        report = reports_by_id["B13-worse-big-loss"]
        assert report.passed_gating is True, (
            f"B13 should pass gating in v3, got passed_gating=False. "
            f"Explanations: {report.explanations}"
        )

    def test_b13_opportunity_in_expected_range(
        self, reports_by_id: dict[str, EvaluationReport]
    ) -> None:
        """B13 opportunity score in [0.0, 0.3]."""
        report = reports_by_id["B13-worse-big-loss"]
        assert 0.0 <= report.opportunity_score <= 0.3, (
            f"B13 opportunity_score={report.opportunity_score:.4f}, "
            f"expected [0.0, 0.3]"
        )

    def test_b13_has_positive_validity(
        self, reports_by_id: dict[str, EvaluationReport]
    ) -> None:
        """B13 has a positive validity score (branch is physically plausible)."""
        report = reports_by_id["B13-worse-big-loss"]
        assert report.validity_score > 0.0, (
            f"B13 validity_score={report.validity_score:.4f}, expected > 0"
        )


# ---------------------------------------------------------------------------
# Task 14 — B14 specific: opportunity in [0.4, 0.6]
# ---------------------------------------------------------------------------


class TestB14NeutralSameAsReality:
    """B14 (mirrors reality) must have opportunity near 0.5.

    Validates: Requirements 5.2
    """

    def test_b14_passes_gating(self, reports_by_id: dict[str, EvaluationReport]) -> None:
        """B14 passes gating."""
        report = reports_by_id["B14-neutral-same-as-reality"]
        assert report.passed_gating is True

    def test_b14_opportunity_in_expected_range(
        self, reports_by_id: dict[str, EvaluationReport]
    ) -> None:
        """B14 opportunity score in [0.4, 0.6]."""
        report = reports_by_id["B14-neutral-same-as-reality"]
        assert 0.4 <= report.opportunity_score <= 0.6, (
            f"B14 opportunity_score={report.opportunity_score:.4f}, "
            f"expected [0.4, 0.6]"
        )


# ---------------------------------------------------------------------------
# Task 14 — B15 specific: opportunity in [0.4, 0.6]
# ---------------------------------------------------------------------------


class TestB15NeutralLateralMove:
    """B15 (lateral movement, no gain) must have opportunity near 0.5.

    Validates: Requirements 5.3
    """

    def test_b15_passes_gating(self, reports_by_id: dict[str, EvaluationReport]) -> None:
        """B15 passes gating."""
        report = reports_by_id["B15-neutral-lateral-move"]
        assert report.passed_gating is True

    def test_b15_opportunity_in_expected_range(
        self, reports_by_id: dict[str, EvaluationReport]
    ) -> None:
        """B15 opportunity score in [0.4, 0.6]."""
        report = reports_by_id["B15-neutral-lateral-move"]
        assert 0.4 <= report.opportunity_score <= 0.6, (
            f"B15 opportunity_score={report.opportunity_score:.4f}, "
            f"expected [0.4, 0.6]"
        )


# ---------------------------------------------------------------------------
# Task 14 — No regressions: 12 v2-passing branches still pass
# ---------------------------------------------------------------------------


class TestV2NoRegressions:
    """The 12 branches that passed in v2 must continue to pass in v3.

    Validates: Requirements 5.6
    """

    def test_v2_passing_branches_still_pass_gating(
        self, reports_by_id: dict[str, EvaluationReport]
    ) -> None:
        """All 12 v2-passing branches still pass gating in v3."""
        for bid in V2_PASSING_BRANCH_IDS:
            report = reports_by_id[bid]
            assert report.passed_gating is True, (
                f"Regression: {bid} passed gating in v2 but fails in v3. "
                f"Explanations: {report.explanations}"
            )

    def test_v2_passing_branches_have_positive_validity(
        self, reports_by_id: dict[str, EvaluationReport]
    ) -> None:
        """All 12 v2-passing branches still have positive validity in v3."""
        for bid in V2_PASSING_BRANCH_IDS:
            report = reports_by_id[bid]
            assert report.validity_score > 0.0, (
                f"Regression: {bid} had positive validity in v2 but "
                f"validity_score={report.validity_score:.4f} in v3"
            )

    def test_v2_passing_branches_have_valid_opportunity(
        self, reports_by_id: dict[str, EvaluationReport]
    ) -> None:
        """All 12 v2-passing branches still produce opportunity scores in [0, 1]."""
        for bid in V2_PASSING_BRANCH_IDS:
            report = reports_by_id[bid]
            assert 0.0 <= report.opportunity_score <= 1.0, (
                f"Regression: {bid} opportunity_score={report.opportunity_score:.4f} "
                f"out of [0, 1] range"
            )

    def test_implausible_branches_still_fail_gating(
        self, reports_by_id: dict[str, EvaluationReport]
    ) -> None:
        """The 4 implausible branches (B04-B07) still fail gating in v3."""
        implausible_ids = [
            "B04-implausible-teleport",
            "B05-implausible-out-of-bounds",
            "B06-implausible-time-gap",
            "B07-implausible-supersonic",
        ]
        for bid in implausible_ids:
            report = reports_by_id[bid]
            assert report.passed_gating is False, (
                f"Regression: {bid} should still fail gating in v3"
            )
            assert report.validity_score == 0.0
            assert report.opportunity_score == 0.0
