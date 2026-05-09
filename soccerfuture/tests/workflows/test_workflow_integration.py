"""Integration tests for analyst workflow and batch demo runner."""

import json
import os

import pytest

from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig
from src.workflows.analyst_workflow_runner import run_analyst_workflow
from src.workflows.batch_demo_runner import run_batch_demo
from src.workflows.scenario_bundle import BundleManifest


@pytest.fixture(scope="module")
def play_state():
    with open("data/play_states/counter_attack_midfield.json") as f:
        return dict_to_play_state(json.load(f))


@pytest.fixture(scope="module")
def config():
    return PipelineConfig(n=10, k=3, seed=42)


# ---------------------------------------------------------------------------
# Single-run workflow
# ---------------------------------------------------------------------------


class TestSingleRunWorkflow:
    """Full single-scenario workflow with fixture input."""

    def test_returns_bundle_manifest(self, play_state, config, tmp_path):
        manifest = run_analyst_workflow(
            scenario_id="test_single",
            play_state=play_state,
            output_root=str(tmp_path),
            pipeline_config=config,
        )
        assert isinstance(manifest, BundleManifest)

    def test_overall_status_success(self, play_state, config, tmp_path):
        manifest = run_analyst_workflow(
            scenario_id="test_success",
            play_state=play_state,
            output_root=str(tmp_path),
            pipeline_config=config,
        )
        assert manifest.overall_status in ("success", "partial")

    def test_bundle_directory_created(self, play_state, config, tmp_path):
        manifest = run_analyst_workflow(
            scenario_id="test_dir",
            play_state=play_state,
            output_root=str(tmp_path),
            pipeline_config=config,
        )
        bundle_path = os.path.join(str(tmp_path), "test_dir")
        assert os.path.isdir(bundle_path)

    def test_run_status_json_exists(self, play_state, config, tmp_path):
        run_analyst_workflow(
            scenario_id="test_status",
            play_state=play_state,
            output_root=str(tmp_path),
            pipeline_config=config,
        )
        status_path = os.path.join(str(tmp_path), "test_status", "run_status.json")
        assert os.path.isfile(status_path)

    def test_pipeline_report_json_exists(self, play_state, config, tmp_path):
        run_analyst_workflow(
            scenario_id="test_report",
            play_state=play_state,
            output_root=str(tmp_path),
            pipeline_config=config,
        )
        report_path = os.path.join(str(tmp_path), "test_report", "pipeline_report.json")
        assert os.path.isfile(report_path)

    def test_analyst_summary_md_exists(self, play_state, config, tmp_path):
        run_analyst_workflow(
            scenario_id="test_summary",
            play_state=play_state,
            output_root=str(tmp_path),
            pipeline_config=config,
        )
        summary_path = os.path.join(str(tmp_path), "test_summary", "analyst_summary.md")
        assert os.path.isfile(summary_path)

    def test_step_statuses_recorded(self, play_state, config, tmp_path):
        manifest = run_analyst_workflow(
            scenario_id="test_steps",
            play_state=play_state,
            output_root=str(tmp_path),
            pipeline_config=config,
        )
        step_names = [s.step_name for s in manifest.step_statuses]
        assert "load" in step_names
        assert "pipeline" in step_names
        assert "summary" in step_names

    def test_deterministic_output(self, play_state, config, tmp_path):
        """Two runs with same input produce same pipeline report."""
        dir1 = str(tmp_path / "run1")
        dir2 = str(tmp_path / "run2")
        run_analyst_workflow(
            scenario_id="det",
            play_state=play_state,
            output_root=dir1,
            pipeline_config=config,
        )
        run_analyst_workflow(
            scenario_id="det",
            play_state=play_state,
            output_root=dir2,
            pipeline_config=config,
        )
        with open(os.path.join(dir1, "det", "pipeline_report.json")) as f:
            r1 = json.load(f)
        with open(os.path.join(dir2, "det", "pipeline_report.json")) as f:
            r2 = json.load(f)
        # Ranked branches should be identical
        assert r1["ranked_branches"] == r2["ranked_branches"]


# ---------------------------------------------------------------------------
# Partial failure
# ---------------------------------------------------------------------------


class TestPartialFailure:
    """Workflow handles partial failures gracefully."""

    def test_no_play_state_fails_load(self, tmp_path):
        manifest = run_analyst_workflow(
            scenario_id="test_fail",
            play_state=None,
            play_state_dict=None,
            output_root=str(tmp_path),
        )
        assert manifest.overall_status == "failed"
        load_step = next(s for s in manifest.step_statuses if s.step_name == "load")
        assert load_step.status == "failed"

    def test_skip_viewer_marks_skipped(self, play_state, config, tmp_path):
        manifest = run_analyst_workflow(
            scenario_id="test_skip_viewer",
            play_state=play_state,
            output_root=str(tmp_path),
            pipeline_config=config,
            skip_viewer=True,
        )
        viewer_step = next(s for s in manifest.step_statuses if s.step_name == "viewer")
        assert viewer_step.status == "skipped"


# ---------------------------------------------------------------------------
# Batch workflow
# ---------------------------------------------------------------------------


class TestBatchWorkflow:
    """Full batch-run workflow with fixture inputs."""

    def test_batch_returns_manifests_and_entries(self, play_state, config, tmp_path):
        scenarios = [
            {"scenario_id": "batch_s1", "play_state": play_state},
            {"scenario_id": "batch_s2", "play_state": play_state},
        ]
        manifests, entries = run_batch_demo(
            scenarios, output_root=str(tmp_path), pipeline_config=config,
        )
        assert len(manifests) == 2
        assert len(entries) == 2

    def test_batch_creates_demo_index_json(self, play_state, config, tmp_path):
        scenarios = [
            {"scenario_id": "idx_s1", "play_state": play_state},
        ]
        run_batch_demo(scenarios, output_root=str(tmp_path), pipeline_config=config)
        assert os.path.isfile(os.path.join(str(tmp_path), "demo_index.json"))

    def test_batch_creates_demo_index_md(self, play_state, config, tmp_path):
        scenarios = [
            {"scenario_id": "idx_s2", "play_state": play_state},
        ]
        run_batch_demo(scenarios, output_root=str(tmp_path), pipeline_config=config)
        assert os.path.isfile(os.path.join(str(tmp_path), "demo_index.md"))

    def test_batch_per_scenario_bundles_created(self, play_state, config, tmp_path):
        scenarios = [
            {"scenario_id": "b_s1", "play_state": play_state},
            {"scenario_id": "b_s2", "play_state": play_state},
        ]
        run_batch_demo(scenarios, output_root=str(tmp_path), pipeline_config=config)
        assert os.path.isdir(os.path.join(str(tmp_path), "b_s1"))
        assert os.path.isdir(os.path.join(str(tmp_path), "b_s2"))

    def test_batch_index_has_correct_count(self, play_state, config, tmp_path):
        scenarios = [
            {"scenario_id": "cnt_s1", "play_state": play_state},
            {"scenario_id": "cnt_s2", "play_state": play_state},
        ]
        run_batch_demo(scenarios, output_root=str(tmp_path), pipeline_config=config)
        with open(os.path.join(str(tmp_path), "demo_index.json")) as f:
            data = json.load(f)
        assert data["summary"]["total"] == 2
