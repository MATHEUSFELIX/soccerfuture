"""Unit tests for review pack, readiness, feedback ingest, index, and report."""

import json
import os

import pytest

from src.review.demo_readiness import ReadinessResult, evaluate_readiness
from src.review.review_feedback_ingest import (
    FeedbackAggregate,
    aggregate_to_dict,
    ingest_feedback,
)
from src.review.review_feedback_schema import ReviewFeedback
from src.review.review_index import (
    ReviewIndexEntry,
    build_review_index_entry,
    generate_review_index_json,
    generate_review_index_markdown,
    save_review_index,
)
from src.review.review_pack import ReviewPack, generate_review_pack, review_pack_to_dict
from src.review.stakeholder_report import generate_stakeholder_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_feedback(**overrides) -> ReviewFeedback:
    defaults = dict(
        scenario_id="s1",
        reviewer_id="r1",
        top_1_plausibility="yes",
        top_3_usefulness="yes",
        summary_clarity=4,
        confidence_sufficiency=4,
    )
    defaults.update(overrides)
    return ReviewFeedback(**defaults)


def _create_bundle(tmp_path, scenario_id="test_scenario"):
    """Create a minimal valid bundle directory for testing."""
    bundle = tmp_path / scenario_id
    bundle.mkdir()

    # run_status.json
    status = {
        "scenario_id": scenario_id,
        "source_type": "structured",
        "run_timestamp": "2025-01-01T00:00:00Z",
        "step_statuses": [
            {"step_name": "load", "status": "success", "started_at": "", "finished_at": "", "notes": "", "artifact_path": None},
            {"step_name": "pipeline", "status": "success", "started_at": "", "finished_at": "", "notes": "", "artifact_path": None},
        ],
        "artifact_references": {},
        "notes": "",
        "overall_status": "success",
    }
    (bundle / "run_status.json").write_text(json.dumps(status))

    # pipeline_report.json
    report = {
        "ranked_branches": [
            {"branch_id": "b1", "composite_score": 0.85, "evaluation_report": {}, "branch": {}},
        ],
        "metadata": {"execution_time_seconds": 1.5, "context_applied": False, "priors_applied": False},
    }
    (bundle / "pipeline_report.json").write_text(json.dumps(report))

    # analyst_summary.md
    (bundle / "analyst_summary.md").write_text("# Summary\nTest scenario summary.")

    # viewer_artifact.json
    (bundle / "viewer_artifact.json").write_text(json.dumps({"note": "viewer ref"}))

    # input_reference.json
    (bundle / "input_reference.json").write_text(json.dumps({"scenario_id": scenario_id}))

    return str(bundle)


# ---------------------------------------------------------------------------
# ReviewPack
# ---------------------------------------------------------------------------


class TestReviewPack:
    def test_generate_from_bundle(self, tmp_path):
        bundle = _create_bundle(tmp_path)
        pack = generate_review_pack(bundle)
        assert isinstance(pack, ReviewPack)
        assert pack.scenario_id == "test_scenario"
        assert len(pack.top_branches) == 1

    def test_missing_bundle_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            generate_review_pack(str(tmp_path / "nonexistent"))

    def test_review_pack_to_dict(self, tmp_path):
        bundle = _create_bundle(tmp_path)
        pack = generate_review_pack(bundle)
        d = review_pack_to_dict(pack)
        assert isinstance(d, dict)
        assert d["scenario_id"] == "test_scenario"

    def test_viewer_ref_populated(self, tmp_path):
        bundle = _create_bundle(tmp_path)
        pack = generate_review_pack(bundle)
        assert pack.viewer_artifact_ref == "viewer_artifact.json"


# ---------------------------------------------------------------------------
# DemoReadiness
# ---------------------------------------------------------------------------


class TestDemoReadiness:
    def test_fully_ready_bundle(self, tmp_path):
        bundle = _create_bundle(tmp_path)
        result = evaluate_readiness(bundle)
        assert result.label == "ready"
        assert len(result.checks_failed) == 0

    def test_missing_summary_partially_ready(self, tmp_path):
        bundle = _create_bundle(tmp_path, "partial")
        os.remove(os.path.join(bundle, "analyst_summary.md"))
        result = evaluate_readiness(bundle)
        assert result.label in ("partially_ready", "not_ready")
        assert "summary_present" in result.checks_failed

    def test_failed_status_not_ready(self, tmp_path):
        bundle = _create_bundle(tmp_path, "failed")
        status_path = os.path.join(bundle, "run_status.json")
        with open(status_path) as f:
            status = json.load(f)
        status["overall_status"] = "failed"
        with open(status_path, "w") as f:
            json.dump(status, f)
        result = evaluate_readiness(bundle)
        assert result.label == "not_ready"

    def test_reasons_populated_on_failure(self, tmp_path):
        bundle = _create_bundle(tmp_path, "reasons")
        os.remove(os.path.join(bundle, "viewer_artifact.json"))
        result = evaluate_readiness(bundle)
        assert len(result.reasons) > 0


# ---------------------------------------------------------------------------
# FeedbackIngest
# ---------------------------------------------------------------------------


class TestFeedbackIngest:
    def test_empty_feedback(self):
        agg = ingest_feedback([])
        assert agg.total_responses == 0
        assert agg.top_1_plausibility_rate == 0.0

    def test_single_feedback(self):
        fb = _make_feedback()
        agg = ingest_feedback([fb])
        assert agg.total_responses == 1
        assert agg.top_1_plausibility_rate == 1.0
        assert agg.avg_summary_clarity == 4.0

    def test_multiple_feedback_averaging(self):
        fb1 = _make_feedback(summary_clarity=5, confidence_sufficiency=5)
        fb2 = _make_feedback(reviewer_id="r2", summary_clarity=3, confidence_sufficiency=3)
        agg = ingest_feedback([fb1, fb2])
        assert agg.avg_summary_clarity == 4.0
        assert agg.avg_confidence_sufficiency == 4.0

    def test_high_disagreement_detected(self):
        fb1 = _make_feedback(top_1_plausibility="yes")
        fb2 = _make_feedback(reviewer_id="r2", top_1_plausibility="no")
        agg = ingest_feedback([fb1, fb2])
        assert "s1" in agg.high_disagreement_scenarios

    def test_blocker_frequencies(self):
        fb1 = _make_feedback(blockers=["no data", "slow"])
        fb2 = _make_feedback(reviewer_id="r2", blockers=["no data"])
        agg = ingest_feedback([fb1, fb2])
        assert agg.blocker_frequencies["no data"] == 2
        assert agg.blocker_frequencies["slow"] == 1

    def test_aggregate_to_dict(self):
        fb = _make_feedback()
        agg = ingest_feedback([fb])
        d = aggregate_to_dict(agg)
        assert isinstance(d, dict)
        assert d["total_responses"] == 1


# ---------------------------------------------------------------------------
# ReviewIndex
# ---------------------------------------------------------------------------


class TestReviewIndex:
    def test_build_entry(self):
        readiness = ReadinessResult(scenario_id="s1", label="ready")
        entry = build_review_index_entry(readiness)
        assert entry.scenario_id == "s1"
        assert entry.readiness_label == "ready"

    def test_generate_json(self):
        entry = ReviewIndexEntry(
            scenario_id="s1", status="success", readiness_label="ready",
        )
        result = generate_review_index_json([entry])
        assert result["summary"]["total"] == 1
        assert result["summary"]["ready"] == 1

    def test_generate_markdown(self):
        entry = ReviewIndexEntry(
            scenario_id="s1", status="success", readiness_label="ready",
        )
        md = generate_review_index_markdown([entry])
        assert "# Review Index" in md
        assert "s1" in md

    def test_save_creates_files(self, tmp_path):
        entry = ReviewIndexEntry(
            scenario_id="s1", status="success", readiness_label="ready",
        )
        json_path, md_path = save_review_index([entry], str(tmp_path))
        assert os.path.isfile(json_path)
        assert os.path.isfile(md_path)


# ---------------------------------------------------------------------------
# StakeholderReport
# ---------------------------------------------------------------------------


class TestStakeholderReport:
    def test_basic_report_generation(self):
        results = [ReadinessResult(scenario_id="s1", label="ready")]
        report = generate_stakeholder_report(results)
        assert "# Stakeholder Review Report" in report
        assert "s1" in report

    def test_report_with_feedback(self):
        results = [ReadinessResult(scenario_id="s1", label="ready")]
        agg = FeedbackAggregate(
            total_responses=2,
            scenario_count=1,
            reviewer_count=2,
            top_1_plausibility_rate=0.5,
            top_3_usefulness_rate=1.0,
            avg_summary_clarity=4.0,
            avg_confidence_sufficiency=3.5,
            blocker_frequencies={"no data": 2},
            improvement_frequencies={"speed": 1},
            high_disagreement_scenarios=["s1"],
        )
        report = generate_stakeholder_report(results, feedback_aggregate=agg)
        assert "Feedback Observations" in report
        assert "High-Disagreement" in report
        assert "no data" in report

    def test_report_separates_observations_from_recommendations(self):
        results = [ReadinessResult(scenario_id="s1", label="not_ready", reasons=["Check failed: summary_present"])]
        report = generate_stakeholder_report(results)
        assert "## Recommendations" in report
        assert "not ready" in report.lower()

    def test_empty_results(self):
        report = generate_stakeholder_report([])
        assert "# Stakeholder Review Report" in report
        assert "Total scenarios evaluated:** 0" in report
