"""Unit and integration tests for the analyst review UI."""

import json
import os

import pytest

from src.ui.review_data_loader import (
    ScenarioViewData,
    load_all_scenarios,
    load_feedback_for_scenario,
    load_scenario_data,
)
from src.ui.review_app import (
    export_feedback_template,
    generate_review_site,
    render_index_page,
    render_scenario_detail_page,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_bundle(tmp_path, scenario_id="test_scenario"):
    """Create a minimal valid bundle directory."""
    bundle = tmp_path / scenario_id
    bundle.mkdir(parents=True, exist_ok=True)

    status = {
        "scenario_id": scenario_id,
        "source_type": "structured",
        "run_timestamp": "2025-01-01T00:00:00Z",
        "step_statuses": [],
        "artifact_references": {},
        "notes": "",
        "overall_status": "success",
    }
    (bundle / "run_status.json").write_text(json.dumps(status))

    report = {
        "ranked_branches": [
            {"branch_id": "b1", "composite_score": 0.85, "evaluation_report": {}, "branch": {}},
            {"branch_id": "b2", "composite_score": 0.72, "evaluation_report": {}, "branch": {}},
        ],
        "metadata": {"execution_time_seconds": 1.5},
    }
    (bundle / "pipeline_report.json").write_text(json.dumps(report))
    (bundle / "analyst_summary.md").write_text("# Summary\nTest scenario.")
    (bundle / "viewer_artifact.json").write_text(json.dumps({"note": "viewer"}))
    (bundle / "input_reference.json").write_text(json.dumps({"scenario_id": scenario_id}))

    return str(bundle)


# ---------------------------------------------------------------------------
# ReviewDataLoader
# ---------------------------------------------------------------------------


class TestReviewDataLoader:
    def test_load_scenario_data(self, tmp_path):
        bundle = _create_bundle(tmp_path)
        data = load_scenario_data(bundle)
        assert isinstance(data, ScenarioViewData)
        assert data.scenario_id == "test_scenario"
        assert data.overall_status == "success"
        assert len(data.top_branches) == 2

    def test_load_scenario_missing_report(self, tmp_path):
        bundle = _create_bundle(tmp_path, "no_report")
        os.remove(os.path.join(bundle, "pipeline_report.json"))
        data = load_scenario_data(bundle)
        assert data.pipeline_report is None
        assert data.top_branches == []

    def test_load_all_scenarios(self, tmp_path):
        _create_bundle(tmp_path, "s1")
        _create_bundle(tmp_path, "s2")
        scenarios = load_all_scenarios(str(tmp_path))
        assert len(scenarios) == 2
        assert scenarios[0].scenario_id == "s1"
        assert scenarios[1].scenario_id == "s2"

    def test_load_all_scenarios_empty_dir(self, tmp_path):
        scenarios = load_all_scenarios(str(tmp_path))
        assert scenarios == []

    def test_load_all_scenarios_nonexistent_dir(self):
        scenarios = load_all_scenarios("/nonexistent/path")
        assert scenarios == []

    def test_load_feedback_for_scenario(self, tmp_path):
        fb_dir = tmp_path / "feedback"
        fb_dir.mkdir()
        fb = {"scenario_id": "s1", "reviewer_id": "r1", "notes": "good"}
        (fb_dir / "fb1.json").write_text(json.dumps(fb))
        records = load_feedback_for_scenario(str(fb_dir), "s1")
        assert len(records) == 1
        assert records[0]["reviewer_id"] == "r1"

    def test_load_feedback_no_match(self, tmp_path):
        fb_dir = tmp_path / "feedback"
        fb_dir.mkdir()
        fb = {"scenario_id": "other", "reviewer_id": "r1"}
        (fb_dir / "fb1.json").write_text(json.dumps(fb))
        records = load_feedback_for_scenario(str(fb_dir), "s1")
        assert records == []


# ---------------------------------------------------------------------------
# ReviewApp — Rendering
# ---------------------------------------------------------------------------


class TestRenderIndexPage:
    def test_contains_html_structure(self):
        scenarios = [ScenarioViewData(
            scenario_id="s1", bundle_path="/tmp/s1",
            overall_status="success", source_type="structured",
            top_branches=[{"branch_id": "b1", "composite_score": 0.85}],
        )]
        html = render_index_page(scenarios)
        assert "<!DOCTYPE html>" in html
        assert "Scenario Index" in html
        assert "s1" in html

    def test_empty_scenarios(self):
        html = render_index_page([])
        assert "Total scenarios:</strong> 0" in html

    def test_contains_table(self):
        scenarios = [ScenarioViewData(scenario_id="s1", bundle_path="/tmp/s1")]
        html = render_index_page(scenarios)
        assert "<table>" in html


class TestRenderScenarioDetailPage:
    def test_contains_scenario_id(self):
        s = ScenarioViewData(
            scenario_id="my_scenario", bundle_path="/tmp/my_scenario",
            top_branches=[{"branch_id": "b1", "composite_score": 0.9}],
            analyst_summary="# Test summary",
        )
        html = render_scenario_detail_page(s)
        assert "my_scenario" in html
        assert "b1" in html
        assert "Test summary" in html

    def test_no_branches_message(self):
        s = ScenarioViewData(scenario_id="s1", bundle_path="/tmp/s1")
        html = render_scenario_detail_page(s)
        assert "No ranked branches" in html

    def test_feedback_displayed(self):
        s = ScenarioViewData(
            scenario_id="s1", bundle_path="/tmp/s1",
            feedback_records=[{"reviewer_id": "r1", "notes": "looks good"}],
        )
        html = render_scenario_detail_page(s)
        assert "looks good" in html


# ---------------------------------------------------------------------------
# ReviewApp — Site Generation
# ---------------------------------------------------------------------------


class TestGenerateReviewSite:
    def test_generates_index_and_detail_pages(self, tmp_path):
        runs = tmp_path / "runs"
        runs.mkdir()
        _create_bundle(runs, "s1")
        _create_bundle(runs, "s2")

        output = tmp_path / "site"
        files = generate_review_site(str(runs), str(output))

        assert os.path.isfile(os.path.join(str(output), "index.html"))
        assert os.path.isfile(os.path.join(str(output), "s1.html"))
        assert os.path.isfile(os.path.join(str(output), "s2.html"))
        assert len(files) == 3

    def test_empty_runs_generates_index_only(self, tmp_path):
        runs = tmp_path / "runs"
        runs.mkdir()
        output = tmp_path / "site"
        files = generate_review_site(str(runs), str(output))
        assert len(files) == 1  # just index.html

    def test_deterministic_output(self, tmp_path):
        runs = tmp_path / "runs"
        runs.mkdir()
        _create_bundle(runs, "s1")

        out1 = tmp_path / "site1"
        out2 = tmp_path / "site2"
        generate_review_site(str(runs), str(out1))
        generate_review_site(str(runs), str(out2))

        with open(os.path.join(str(out1), "index.html")) as f:
            html1 = f.read()
        with open(os.path.join(str(out2), "index.html")) as f:
            html2 = f.read()
        assert html1 == html2


# ---------------------------------------------------------------------------
# Feedback Export
# ---------------------------------------------------------------------------


class TestFeedbackExport:
    def test_export_creates_file(self, tmp_path):
        path = str(tmp_path / "feedback_template.json")
        result = export_feedback_template("s1", path)
        assert os.path.isfile(result)

    def test_export_contains_scenario_id(self, tmp_path):
        path = str(tmp_path / "template.json")
        export_feedback_template("my_scenario", path)
        with open(path) as f:
            data = json.load(f)
        assert data["scenario_id"] == "my_scenario"

    def test_export_has_all_fields(self, tmp_path):
        path = str(tmp_path / "template.json")
        export_feedback_template("s1", path)
        with open(path) as f:
            data = json.load(f)
        expected_keys = {
            "scenario_id", "reviewer_id", "top_1_plausibility",
            "top_3_usefulness", "summary_clarity", "confidence_sufficiency",
            "blockers", "missing_capabilities", "priority_suggestions", "notes",
        }
        assert set(data.keys()) == expected_keys
