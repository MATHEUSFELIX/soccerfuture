"""Regression and integration tests for the simulation evaluator v2.

Regression tests load data/evaluator_demo_input.json and verify known-good
and known-bad branches produce expected results.

Integration tests exercise the full evaluate_all pipeline end-to-end.

Requirements covered: 9.3, 9.4, 10.1, 10.2, 10.3, 10.4
"""

from __future__ import annotations

import json
import pathlib

import pytest

from src.simulation_evaluator_v2 import evaluate_branch, evaluate_all
from src.utils.serialization import report_to_dict


# ---------------------------------------------------------------------------
# Fixture: load demo input JSON once per session
# ---------------------------------------------------------------------------

DEMO_INPUT_PATH = pathlib.Path("data/evaluator_demo_input.json")


@pytest.fixture(scope="session")
def demo_input() -> dict:
    """Load the demo input JSON from disk (not inline)."""
    with open(DEMO_INPUT_PATH, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def realistic_branch(demo_input: dict) -> dict:
    """Extract the realistic branch from demo input."""
    return demo_input["branches"][0]


@pytest.fixture(scope="session")
def teleport_branch(demo_input: dict) -> dict:
    """Extract the teleport branch from demo input."""
    return demo_input["branches"][1]


@pytest.fixture(scope="session")
def realistic_window(demo_input: dict) -> dict:
    """Extract the continuation window for the realistic branch."""
    return demo_input["continuation_windows"][0]


@pytest.fixture(scope="session")
def teleport_window(demo_input: dict) -> dict:
    """Extract the continuation window for the teleport branch."""
    return demo_input["continuation_windows"][1]


# ---------------------------------------------------------------------------
# Task 10.1 — Regression tests
# ---------------------------------------------------------------------------


class TestRealisticBranchRegression:
    """Regression: realistic branch passes all gates with good validity."""

    def test_realistic_branch_passes_gating(
        self, realistic_branch: dict, realistic_window: dict
    ) -> None:
        """Realistic branch passes all gating checks.

        Validates: Requirements 10.1
        """
        report = evaluate_branch(realistic_branch, realistic_window)
        assert report.passed_gating is True, (
            f"Expected realistic branch to pass gating, got passed_gating={report.passed_gating}. "
            f"Explanations: {report.explanations}"
        )

    def test_realistic_branch_has_positive_validity(
        self, realistic_branch: dict, realistic_window: dict
    ) -> None:
        """Realistic branch receives a positive validity_score.

        The demo branch has players moving at plausible speeds (under
        the 10 m/s gate) so it passes gating, but the plausibility
        scoring formula penalises speeds close to the limit, yielding
        validity ~0.35.  We verify the score is meaningfully above zero
        (branch was not gated out) and within the valid range.

        Validates: Requirements 10.1
        """
        report = evaluate_branch(realistic_branch, realistic_window)
        assert report.validity_score > 0.0, (
            f"Expected positive validity_score for realistic branch, "
            f"got {report.validity_score}"
        )
        assert report.validity_score <= 1.0, (
            f"validity_score out of range: {report.validity_score}"
        )

    def test_realistic_branch_all_gating_flags_true(
        self, realistic_branch: dict, realistic_window: dict
    ) -> None:
        """All individual gating flags are True for the realistic branch.

        Validates: Requirements 10.2
        """
        report = evaluate_branch(realistic_branch, realistic_window)
        for flag_name, flag_value in report.gating_flags.items():
            assert flag_value is True, (
                f"Gating flag '{flag_name}' is False for realistic branch"
            )


class TestTeleportBranchRegression:
    """Regression: teleport branch fails gating with speed explanation."""

    def test_teleport_branch_fails_gating(
        self, teleport_branch: dict, teleport_window: dict
    ) -> None:
        """Teleport branch fails gating (passed_gating=False).

        Validates: Requirements 10.2
        """
        report = evaluate_branch(teleport_branch, teleport_window)
        assert report.passed_gating is False, (
            "Expected teleport branch to fail gating"
        )

    def test_teleport_branch_explanation_mentions_speed(
        self, teleport_branch: dict, teleport_window: dict
    ) -> None:
        """Teleport branch explanation mentions speed or exceeding.

        Validates: Requirements 10.3, 10.4
        """
        report = evaluate_branch(teleport_branch, teleport_window)
        combined = " ".join(report.explanations).lower()
        assert "speed" in combined or "exceeding" in combined or "exceed" in combined, (
            f"Expected explanation to mention speed/exceeding for teleport branch, "
            f"got: {report.explanations}"
        )

    def test_teleport_branch_validity_zero(
        self, teleport_branch: dict, teleport_window: dict
    ) -> None:
        """Teleport branch receives validity_score=0.0 due to gating failure.

        Validates: Requirements 10.2
        """
        report = evaluate_branch(teleport_branch, teleport_window)
        assert report.validity_score == 0.0, (
            f"Expected validity_score=0.0 for teleport branch, "
            f"got {report.validity_score}"
        )


# ---------------------------------------------------------------------------
# Task 10.2 — Integration tests
# ---------------------------------------------------------------------------


class TestEvaluateAllIntegration:
    """Integration: evaluate_all processes all branches end-to-end."""

    def test_evaluate_all_returns_correct_count(
        self, demo_input: dict
    ) -> None:
        """evaluate_all returns exactly 2 reports for the demo input.

        Validates: Requirements 9.3
        """
        reports = evaluate_all(demo_input)
        assert len(reports) == 2, (
            f"Expected 2 reports, got {len(reports)}"
        )

    def test_reports_serializable_to_json(
        self, demo_input: dict
    ) -> None:
        """Each report can be serialized to JSON via report_to_dict + json.dumps.

        Validates: Requirements 9.4
        """
        reports = evaluate_all(demo_input)
        for report in reports:
            report_dict = report_to_dict(report)
            json_str = json.dumps(report_dict)
            assert isinstance(json_str, str)
            assert len(json_str) > 0

    def test_reports_have_all_required_fields(
        self, demo_input: dict
    ) -> None:
        """Each report contains all required EvaluationReport fields.

        Validates: Requirements 9.3, 9.4
        """
        required_fields = {
            "branch_id",
            "validity_score",
            "opportunity_score",
            "gating_flags",
            "explanations",
            "sub_metrics",
            "passed_gating",
            "passed_validity",
        }
        reports = evaluate_all(demo_input)
        for report in reports:
            report_dict = report_to_dict(report)
            missing = required_fields - set(report_dict.keys())
            assert not missing, (
                f"Report for '{report.branch_id}' missing fields: {missing}"
            )

    def test_error_state_reports_are_valid_json(
        self, demo_input: dict
    ) -> None:
        """Error-state reports (gating failures) are valid JSON conforming to schema.

        Validates: Requirements 9.4
        """
        reports = evaluate_all(demo_input)
        for report in reports:
            report_dict = report_to_dict(report)
            # Serialize and deserialize round-trip
            json_str = json.dumps(report_dict)
            parsed = json.loads(json_str)
            # Verify structure
            assert isinstance(parsed["branch_id"], str)
            assert isinstance(parsed["validity_score"], (int, float))
            assert isinstance(parsed["opportunity_score"], (int, float))
            assert isinstance(parsed["gating_flags"], dict)
            assert isinstance(parsed["explanations"], list)
            assert isinstance(parsed["sub_metrics"], dict)
            assert isinstance(parsed["passed_gating"], bool)
            assert isinstance(parsed["passed_validity"], bool)
