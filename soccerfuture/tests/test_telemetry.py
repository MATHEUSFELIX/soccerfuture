"""Unit tests for TelemetryCollector.

Validates: Requirements 7.1, 7.2, 7.3, 7.4
"""

import json
import time

import pytest

from src.telemetry import TelemetryCollector


class TestStageTiming:
    """Tests for start_stage / end_stage timing instrumentation."""

    def test_stage_timing_records_elapsed_seconds(self) -> None:
        """start_stage + end_stage records a positive elapsed time."""
        tc = TelemetryCollector()
        tc.start_stage("generation")
        time.sleep(0.01)
        tc.end_stage("generation")

        assert tc.stage_timings["generation"] > 0

    def test_end_stage_without_start_records_zero(self) -> None:
        """end_stage called without a matching start_stage records 0.0."""
        tc = TelemetryCollector()
        tc.end_stage("evaluation")

        assert tc.stage_timings["evaluation"] == 0.0

    def test_time_per_stage_contains_all_stages_after_recording(self) -> None:
        """time_per_stage in to_dict has generation, evaluation, ranking."""
        tc = TelemetryCollector()
        for stage in ("generation", "evaluation", "ranking"):
            tc.start_stage(stage)
            tc.end_stage(stage)

        result = tc.to_dict()
        assert "generation" in result["time_per_stage"]
        assert "evaluation" in result["time_per_stage"]
        assert "ranking" in result["time_per_stage"]


class TestRecordBranchResult:
    """Tests for record_branch_result counting and averaging."""

    def test_single_branch_updates_counts(self) -> None:
        """Recording one passing branch increments branches_generated."""
        tc = TelemetryCollector()
        tc.record_branch_result("route_variation", 0.5, True, True)

        assert tc.branches_generated == 1
        assert tc.hard_fail_count == 0
        assert tc.score_filtered_count == 0

    def test_hard_fail_increments_hard_fail_count(self) -> None:
        """A branch that fails gating increments hard_fail_count."""
        tc = TelemetryCollector()
        tc.record_branch_result("route_variation", 0.2, False, False)

        assert tc.hard_fail_count == 1
        assert tc.score_filtered_count == 0

    def test_score_filtered_increments_score_filtered_count(self) -> None:
        """A branch passing gating but failing validity increments score_filtered_count."""
        tc = TelemetryCollector()
        tc.record_branch_result("speed_variation", 0.3, True, False)

        assert tc.hard_fail_count == 0
        assert tc.score_filtered_count == 1

    def test_averages_computed_correctly(self) -> None:
        """Running average per strategy is correct after multiple branches."""
        tc = TelemetryCollector()
        tc.record_branch_result("route_variation", 0.4, True, True)
        tc.record_branch_result("route_variation", 0.6, True, True)

        assert tc.avg_score_by_strategy["route_variation"] == pytest.approx(0.5)

    def test_averages_per_strategy_independent(self) -> None:
        """Each strategy maintains its own independent running average."""
        tc = TelemetryCollector()
        tc.record_branch_result("route_variation", 0.8, True, True)
        tc.record_branch_result("speed_variation", 0.2, True, True)

        assert tc.avg_score_by_strategy["route_variation"] == pytest.approx(0.8)
        assert tc.avg_score_by_strategy["speed_variation"] == pytest.approx(0.2)


class TestToDict:
    """Tests for to_dict JSON-serializable output."""

    def test_to_dict_contains_all_required_keys(self) -> None:
        """to_dict output has all six required keys."""
        tc = TelemetryCollector()
        result = tc.to_dict()

        required_keys = {
            "branches_generated",
            "hard_fail_count",
            "score_filtered_count",
            "avg_score_by_strategy",
            "avg_score_by_scenario",
            "time_per_stage",
        }
        assert required_keys == set(result.keys())

    def test_to_dict_is_json_serializable(self) -> None:
        """to_dict output can be serialized to JSON without errors."""
        tc = TelemetryCollector(scenario_id="test_scenario")
        tc.record_branch_result("route_variation", 0.5, True, True)
        tc.start_stage("generation")
        tc.end_stage("generation")

        result = tc.to_dict()
        serialized = json.dumps(result)
        assert isinstance(serialized, str)
        # Round-trip: deserialize and verify structure
        deserialized = json.loads(serialized)
        assert deserialized["branches_generated"] == 1


class TestBranchAccountingInvariant:
    """Tests for the branch accounting invariant (Req 7.3)."""

    def test_accounting_invariant_mixed_results(self) -> None:
        """hard_fail + score_filtered + gating_pass == branches_generated.

        Records a mix of gating-fail, validity-fail, and passing branches
        and verifies the invariant holds.
        """
        tc = TelemetryCollector()

        # 3 hard fails (failed gating)
        for _ in range(3):
            tc.record_branch_result("route_variation", 0.1, False, False)

        # 2 score-filtered (passed gating, failed validity)
        for _ in range(2):
            tc.record_branch_result("speed_variation", 0.3, True, False)

        # 5 passing (passed gating and validity)
        for _ in range(5):
            tc.record_branch_result("decision_variation", 0.7, True, True)

        gating_pass_count = (
            tc.branches_generated - tc.hard_fail_count - tc.score_filtered_count
        )
        assert (
            tc.hard_fail_count + tc.score_filtered_count + gating_pass_count
            == tc.branches_generated
        )
        assert tc.branches_generated == 10
        assert tc.hard_fail_count == 3
        assert tc.score_filtered_count == 2
        assert gating_pass_count == 5
