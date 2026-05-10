"""Unit tests for CLI commands, renderers, and healthcheck."""

import json
import os

import pytest

from src.cli_app.commands import (
    CommandResult,
    cmd_generate_review_site,
    cmd_healthcheck,
    cmd_list_runs,
    cmd_run_demo,
    cmd_run_scenario,
)
from src.cli_app.healthcheck import HealthCheckResult, run_healthcheck
from src.cli_app.renderers import (
    render_artifacts,
    render_banner,
    render_error,
    render_healthcheck,
    render_runs_table,
    render_step_progress,
)


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------


class TestHealthcheck:
    def test_returns_result(self):
        result = run_healthcheck()
        assert isinstance(result, HealthCheckResult)
        assert result.status in ("ok", "warning", "error")

    def test_has_checks(self):
        result = run_healthcheck()
        assert len(result.checks) > 0

    def test_play_states_check_present(self):
        result = run_healthcheck()
        names = [c["name"] for c in result.checks]
        assert "play_states" in names

    def test_pipeline_import_check(self):
        result = run_healthcheck()
        pipeline_check = next(c for c in result.checks if c["name"] == "pipeline_import")
        assert pipeline_check["status"] == "ok"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


class TestCmdRunDemo:
    def test_returns_command_result(self, tmp_path):
        result = cmd_run_demo(output_root=str(tmp_path))
        assert isinstance(result, CommandResult)

    def test_demo_succeeds(self, tmp_path):
        result = cmd_run_demo(output_root=str(tmp_path))
        assert result.success is True
        assert result.scenario_id != ""

    def test_demo_creates_bundle(self, tmp_path):
        result = cmd_run_demo(output_root=str(tmp_path))
        bundle_path = os.path.join(str(tmp_path), result.scenario_id)
        assert os.path.isdir(bundle_path)

    def test_demo_has_steps(self, tmp_path):
        result = cmd_run_demo(output_root=str(tmp_path))
        assert len(result.steps) > 0

    def test_demo_has_artifacts(self, tmp_path):
        result = cmd_run_demo(output_root=str(tmp_path))
        assert len(result.artifacts) > 0


class TestCmdRunScenario:
    def test_missing_file_fails(self, tmp_path):
        result = cmd_run_scenario("/nonexistent/file.json", output_root=str(tmp_path))
        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_valid_file_succeeds(self, tmp_path):
        ps_files = [f for f in os.listdir("data/play_states") if f.endswith(".json")]
        if not ps_files:
            pytest.skip("No play state files available")
        input_path = os.path.join("data/play_states", ps_files[0])
        result = cmd_run_scenario(input_path, output_root=str(tmp_path))
        assert result.success is True

    def test_invalid_json_fails(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        result = cmd_run_scenario(str(bad_file), output_root=str(tmp_path))
        assert result.success is False


class TestCmdListRuns:
    def test_empty_dir(self, tmp_path):
        runs = cmd_list_runs(str(tmp_path))
        assert runs == []

    def test_with_runs(self, tmp_path):
        # Create a minimal run
        cmd_run_demo(output_root=str(tmp_path))
        runs = cmd_list_runs(str(tmp_path))
        assert len(runs) >= 1
        assert "scenario_id" in runs[0]


class TestCmdGenerateReviewSite:
    def test_empty_runs(self, tmp_path):
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        out_dir = str(tmp_path / "site")
        result = cmd_generate_review_site(str(runs_dir), out_dir)
        assert result.success is True


class TestCmdHealthcheck:
    def test_returns_healthcheck_result(self):
        result = cmd_healthcheck()
        assert isinstance(result, HealthCheckResult)


# ---------------------------------------------------------------------------
# Renderers (smoke tests — just verify no exceptions)
# ---------------------------------------------------------------------------


class TestRenderers:
    def test_render_banner(self, capsys):
        render_banner()
        # No exception = pass

    def test_render_step_progress(self, capsys):
        steps = [
            {"name": "load", "status": "success"},
            {"name": "pipeline", "status": "failed"},
            {"name": "viewer", "status": "skipped"},
        ]
        render_step_progress(steps)

    def test_render_artifacts(self, capsys):
        render_artifacts({"report": "output/report.json", "summary": "output/summary.md"})

    def test_render_artifacts_empty(self, capsys):
        render_artifacts({})

    def test_render_error(self, capsys):
        render_error("Something broke", "Try again")

    def test_render_healthcheck(self, capsys):
        hc = run_healthcheck()
        render_healthcheck(hc)

    def test_render_runs_table(self, capsys):
        runs = [{"scenario_id": "s1", "status": "success", "source_type": "structured"}]
        render_runs_table(runs)

    def test_render_runs_table_empty(self, capsys):
        render_runs_table([])
