"""Unit tests for pilot evaluation modules."""

import json

import pytest

from src.pilot.pilot_plan import PilotPlan, plan_to_dict, dict_to_plan
from src.pilot.pilot_metrics import PilotMetrics, compute_pilot_metrics
from src.pilot.pilot_report import generate_pilot_report
from src.pilot.pilot_runner import PilotResult, run_pilot
from src.review.demo_readiness import ReadinessResult
from src.review.review_feedback_ingest import FeedbackAggregate


# ---------------------------------------------------------------------------
# PilotPlan
# ---------------------------------------------------------------------------


class TestPilotPlan:
    def test_valid_creation(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1", "s2"])
        assert plan.pilot_id == "p1"

    def test_empty_pilot_id_raises(self):
        with pytest.raises(ValueError, match="pilot_id"):
            PilotPlan(pilot_id="", scenario_ids=["s1"])

    def test_empty_scenarios_raises(self):
        with pytest.raises(ValueError, match="scenario_id"):
            PilotPlan(pilot_id="p1", scenario_ids=[])

    def test_round_trip(self):
        plan = PilotPlan(
            pilot_id="p1", scenario_ids=["s1"],
            reviewer_ids=["r1"], success_metrics={"readiness_rate": 0.8},
        )
        d = plan_to_dict(plan)
        restored = dict_to_plan(d)
        assert restored.pilot_id == "p1"
        assert restored.success_metrics == {"readiness_rate": 0.8}

    def test_json_serializable(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1"])
        d = plan_to_dict(plan)
        j = json.dumps(d)
        assert isinstance(j, str)


# ---------------------------------------------------------------------------
# PilotMetrics
# ---------------------------------------------------------------------------


class TestPilotMetrics:
    def test_all_ready(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1", "s2"],
                         success_metrics={"readiness_rate": 0.5})
        results = [
            ReadinessResult(scenario_id="s1", label="ready"),
            ReadinessResult(scenario_id="s2", label="ready"),
        ]
        metrics = compute_pilot_metrics(plan, results)
        assert metrics.readiness_rate == 1.0
        assert metrics.ready_count == 2
        assert metrics.success_criteria_met["readiness_rate"] is True

    def test_mixed_readiness(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1", "s2", "s3"],
                         success_metrics={"readiness_rate": 0.8})
        results = [
            ReadinessResult(scenario_id="s1", label="ready"),
            ReadinessResult(scenario_id="s2", label="partially_ready"),
            ReadinessResult(scenario_id="s3", label="not_ready"),
        ]
        metrics = compute_pilot_metrics(plan, results)
        assert metrics.ready_count == 1
        assert metrics.readiness_rate < 0.8
        assert metrics.success_criteria_met["readiness_rate"] is False

    def test_with_feedback(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1"],
                         success_metrics={"plausibility_rate": 0.7})
        results = [ReadinessResult(scenario_id="s1", label="ready")]
        feedback = FeedbackAggregate(
            total_responses=2, scenario_count=1, reviewer_count=2,
            top_1_plausibility_rate=0.8, top_3_usefulness_rate=1.0,
            avg_summary_clarity=4.0, avg_confidence_sufficiency=3.5,
        )
        metrics = compute_pilot_metrics(plan, results, feedback)
        assert metrics.avg_plausibility_rate == 0.8
        assert metrics.success_criteria_met["plausibility_rate"] is True

    def test_empty_results(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1"])
        metrics = compute_pilot_metrics(plan, [])
        assert metrics.scenario_count == 0
        assert metrics.readiness_rate == 0.0


# ---------------------------------------------------------------------------
# PilotReport
# ---------------------------------------------------------------------------


class TestPilotReport:
    def test_basic_report(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1"],
                         description="Test pilot")
        metrics = PilotMetrics(
            pilot_id="p1", scenario_count=1, ready_count=1,
            partially_ready_count=0, not_ready_count=0,
            readiness_rate=1.0, feedback_coverage=0.0,
            avg_plausibility_rate=0.0, avg_clarity=0.0,
        )
        report = generate_pilot_report(plan, metrics)
        assert "# Pilot Evaluation Report" in report
        assert "p1" in report
        assert "Test pilot" in report

    def test_report_with_criteria(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1"],
                         success_metrics={"readiness_rate": 0.8})
        metrics = PilotMetrics(
            pilot_id="p1", scenario_count=1, ready_count=1,
            partially_ready_count=0, not_ready_count=0,
            readiness_rate=1.0, feedback_coverage=0.0,
            avg_plausibility_rate=0.0, avg_clarity=0.0,
            success_criteria_met={"readiness_rate": True},
        )
        report = generate_pilot_report(plan, metrics)
        assert "Met" in report

    def test_report_recommendations(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1"],
                         success_metrics={"readiness_rate": 0.8})
        metrics = PilotMetrics(
            pilot_id="p1", scenario_count=2, ready_count=0,
            partially_ready_count=1, not_ready_count=1,
            readiness_rate=0.0, feedback_coverage=0.0,
            avg_plausibility_rate=0.5, avg_clarity=2.5,
            success_criteria_met={"readiness_rate": False},
        )
        report = generate_pilot_report(plan, metrics)
        assert "Recommendations" in report
        assert "not ready" in report.lower()


# ---------------------------------------------------------------------------
# PilotRunner
# ---------------------------------------------------------------------------


class TestPilotRunner:
    def test_run_pilot_returns_result(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1"])
        results = [ReadinessResult(scenario_id="s1", label="ready")]
        pilot_result = run_pilot(plan, results)
        assert isinstance(pilot_result, PilotResult)
        assert pilot_result.pilot_id == "p1"
        assert "# Pilot Evaluation Report" in pilot_result.report_markdown

    def test_run_pilot_with_feedback(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1"],
                         success_metrics={"plausibility_rate": 0.7})
        results = [ReadinessResult(scenario_id="s1", label="ready")]
        feedback = FeedbackAggregate(
            total_responses=1, scenario_count=1, reviewer_count=1,
            top_1_plausibility_rate=0.9, top_3_usefulness_rate=1.0,
            avg_summary_clarity=4.5, avg_confidence_sufficiency=4.0,
        )
        pilot_result = run_pilot(plan, results, feedback)
        assert pilot_result.metrics.success_criteria_met["plausibility_rate"] is True

    def test_deterministic(self):
        plan = PilotPlan(pilot_id="p1", scenario_ids=["s1"])
        results = [ReadinessResult(scenario_id="s1", label="ready")]
        r1 = run_pilot(plan, results)
        r2 = run_pilot(plan, results)
        assert r1.report_markdown == r2.report_markdown
