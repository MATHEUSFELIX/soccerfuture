"""Unit tests for src/workflows/scenario_bundle.py."""

import json
import os

import pytest

from src.workflows.scenario_bundle import (
    BundleManifest,
    StepStatus,
    bundle_dir_path,
    bundle_manifest_to_dict,
    compute_overall_status,
    dict_to_bundle_manifest,
    ensure_bundle_dir,
    make_step_status,
    step_status_to_dict,
    write_json_artifact,
    write_text_artifact,
    VALID_STEP_STATUSES,
)


# ---------------------------------------------------------------------------
# StepStatus
# ---------------------------------------------------------------------------


class TestStepStatus:
    """StepStatus creation and validation."""

    def test_valid_creation(self):
        s = StepStatus(step_name="load", status="success")
        assert s.step_name == "load"
        assert s.status == "success"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="Invalid step status"):
            StepStatus(step_name="load", status="invalid")

    @pytest.mark.parametrize("status", sorted(VALID_STEP_STATUSES))
    def test_all_valid_statuses_accepted(self, status):
        s = StepStatus(step_name="test", status=status)
        assert s.status == status

    def test_make_step_status_fills_timestamps(self):
        s = make_step_status("pipeline", "success")
        assert s.started_at != ""
        assert s.finished_at != ""

    def test_step_status_to_dict(self):
        s = StepStatus(step_name="load", status="success", notes="ok")
        d = step_status_to_dict(s)
        assert d["step_name"] == "load"
        assert d["status"] == "success"
        assert d["notes"] == "ok"


# ---------------------------------------------------------------------------
# BundleManifest
# ---------------------------------------------------------------------------


class TestBundleManifest:
    """BundleManifest creation and serialization."""

    def test_creation(self):
        m = BundleManifest(
            scenario_id="s1",
            source_type="structured",
            run_timestamp="2025-01-01T00:00:00Z",
        )
        assert m.scenario_id == "s1"
        assert m.overall_status == "success"

    def test_round_trip_serialization(self):
        steps = [
            StepStatus(step_name="load", status="success"),
            StepStatus(step_name="pipeline", status="partial", notes="warning"),
        ]
        m = BundleManifest(
            scenario_id="s2",
            source_type="video",
            run_timestamp="2025-01-01T00:00:00Z",
            step_statuses=steps,
            artifact_references={"report": "pipeline_report.json"},
            notes="test run",
            overall_status="partial",
        )
        d = bundle_manifest_to_dict(m)
        restored = dict_to_bundle_manifest(d)

        assert restored.scenario_id == "s2"
        assert restored.source_type == "video"
        assert restored.overall_status == "partial"
        assert len(restored.step_statuses) == 2
        assert restored.step_statuses[1].notes == "warning"
        assert restored.artifact_references == {"report": "pipeline_report.json"}

    def test_json_serializable(self):
        m = BundleManifest(
            scenario_id="s3",
            source_type="structured",
            run_timestamp="2025-01-01T00:00:00Z",
        )
        d = bundle_manifest_to_dict(m)
        json_str = json.dumps(d)
        assert isinstance(json_str, str)


# ---------------------------------------------------------------------------
# compute_overall_status
# ---------------------------------------------------------------------------


class TestComputeOverallStatus:
    """Overall status computation from step statuses."""

    def test_all_success(self):
        steps = [
            StepStatus(step_name="load", status="success"),
            StepStatus(step_name="pipeline", status="success"),
        ]
        assert compute_overall_status(steps) == "success"

    def test_any_failed(self):
        steps = [
            StepStatus(step_name="load", status="success"),
            StepStatus(step_name="pipeline", status="failed"),
        ]
        assert compute_overall_status(steps) == "failed"

    def test_partial_without_failed(self):
        steps = [
            StepStatus(step_name="load", status="success"),
            StepStatus(step_name="viewer", status="partial"),
        ]
        assert compute_overall_status(steps) == "partial"

    def test_skipped_without_failed(self):
        steps = [
            StepStatus(step_name="load", status="success"),
            StepStatus(step_name="extract", status="skipped"),
        ]
        assert compute_overall_status(steps) == "partial"

    def test_empty_list(self):
        assert compute_overall_status([]) == "success"


# ---------------------------------------------------------------------------
# Bundle directory utilities
# ---------------------------------------------------------------------------


class TestBundleDirectoryUtilities:
    """Bundle path generation and directory creation."""

    def test_bundle_dir_path_deterministic(self):
        path1 = bundle_dir_path("/output", "scenario_001")
        path2 = bundle_dir_path("/output", "scenario_001")
        assert path1 == path2
        assert "scenario_001" in path1

    def test_ensure_bundle_dir_creates_directory(self, tmp_path):
        path = ensure_bundle_dir(str(tmp_path), "test_scenario")
        assert os.path.isdir(path)
        assert path.endswith("test_scenario")

    def test_write_json_artifact(self, tmp_path):
        bundle = str(tmp_path / "bundle")
        os.makedirs(bundle)
        data = {"key": "value"}
        filepath = write_json_artifact(bundle, "test.json", data)
        assert os.path.isfile(filepath)
        with open(filepath) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_write_text_artifact(self, tmp_path):
        bundle = str(tmp_path / "bundle")
        os.makedirs(bundle)
        content = "# Hello\nWorld"
        filepath = write_text_artifact(bundle, "test.md", content)
        assert os.path.isfile(filepath)
        with open(filepath) as f:
            loaded = f.read()
        assert loaded == content
