"""Unit / integration tests for the CLI entry point (src/cli.py).

Tests cover valid file processing, missing file errors, malformed JSON
errors, optional argument acceptance, and --output file writing.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import json
import subprocess
import sys

import pytest


def _make_play_state_dict() -> dict:
    """Return a minimal valid PlayState dict for CLI testing."""
    return {
        "match_time": 45.0,
        "possession_team": "home",
        "ball_position": {"x": 34.0, "y": 52.5},
        "game_phase": "open_play",
        "score_differential": 0,
        "game_clock": 2700.0,
        "player_positions": [
            {"player_id": "p1", "x": 26.0, "y": 50.0, "timestamp": 1.0},
            {"player_id": "p2", "x": 20.0, "y": 48.0, "timestamp": 1.0},
            {"player_id": "p3", "x": 30.0, "y": 52.0, "timestamp": 1.0},
            {"player_id": "p4", "x": 15.0, "y": 45.0, "timestamp": 1.0},
            {"player_id": "p5", "x": 35.0, "y": 55.0, "timestamp": 1.0},
        ],
        "decision_point_timestamp": 1.0,
        "player_roles": {"p1": "ST", "p2": "CM", "p3": "LW", "p4": "RW", "p5": "CDM"},
        "metadata": {"formation": "4-3-3"},
    }


def _write_play_state(tmp_path, data: dict | None = None) -> str:
    """Write a PlayState JSON file and return its path."""
    ps = data if data is not None else _make_play_state_dict()
    path = tmp_path / "play_state.json"
    path.write_text(json.dumps(ps), encoding="utf-8")
    return str(path)


def _run_cli(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run the CLI via ``python -m src.cli`` and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "src.cli", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestValidFileProducesJSON:
    """Test: valid file produces JSON output."""

    def test_exit_code_zero(self, tmp_path):
        path = _write_play_state(tmp_path)
        result = _run_cli(path, "--n", "10")
        assert result.returncode == 0

    def test_stdout_is_valid_json(self, tmp_path):
        path = _write_play_state(tmp_path)
        result = _run_cli(path, "--n", "10")
        report = json.loads(result.stdout)
        assert isinstance(report, dict)

    def test_report_has_expected_keys(self, tmp_path):
        path = _write_play_state(tmp_path)
        result = _run_cli(path, "--n", "10")
        report = json.loads(result.stdout)
        assert "play_state" in report
        assert "evaluated_branches" in report
        assert "ranked_branches" in report
        assert "metadata" in report
        assert "errors" in report


class TestMissingFileError:
    """Test: missing file error (exit code 1, error message to stderr)."""

    def test_exit_code_one(self):
        result = _run_cli("/nonexistent/path/to/file.json")
        assert result.returncode == 1

    def test_stderr_contains_error(self):
        result = _run_cli("/nonexistent/path/to/file.json")
        assert "Error" in result.stderr
        assert "not found" in result.stderr.lower() or "File not found" in result.stderr


class TestMalformedJSONError:
    """Test: malformed JSON error (exit code 1)."""

    def test_exit_code_one(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json!!!", encoding="utf-8")
        result = _run_cli(str(bad_file))
        assert result.returncode == 1

    def test_stderr_contains_json_error(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json!!!", encoding="utf-8")
        result = _run_cli(str(bad_file))
        assert "Invalid JSON" in result.stderr


class TestInvalidPlayState:
    """Test: invalid PlayState (missing required fields) exits with code 1."""

    def test_missing_fields_exit_code(self, tmp_path):
        incomplete = {"match_time": 45.0, "possession_team": "home"}
        path = _write_play_state(tmp_path, data=incomplete)
        result = _run_cli(path)
        assert result.returncode == 1

    def test_missing_fields_stderr(self, tmp_path):
        incomplete = {"match_time": 45.0, "possession_team": "home"}
        path = _write_play_state(tmp_path, data=incomplete)
        result = _run_cli(path)
        assert "Invalid PlayState" in result.stderr


class TestOptionalArguments:
    """Test: optional arguments accepted (--n, --k, --seed, etc.)."""

    def test_all_optional_args(self, tmp_path):
        path = _write_play_state(tmp_path)
        result = _run_cli(
            path,
            "--n", "10",
            "--k", "3",
            "--seed", "99",
            "--validity-weight", "0.7",
            "--opportunity-weight", "0.3",
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["metadata"]["seed"] == 99
        assert report["metadata"]["k_requested"] == 3


class TestOutputWritesToFile:
    """Test: --output writes to file."""

    def test_output_file_created(self, tmp_path):
        ps_path = _write_play_state(tmp_path)
        out_path = str(tmp_path / "report.json")
        result = _run_cli(ps_path, "--n", "10", "--output", out_path)
        assert result.returncode == 0
        with open(out_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        assert isinstance(report, dict)
        assert "ranked_branches" in report

    def test_stdout_empty_when_output_used(self, tmp_path):
        ps_path = _write_play_state(tmp_path)
        out_path = str(tmp_path / "report.json")
        result = _run_cli(ps_path, "--n", "10", "--output", out_path)
        assert result.stdout.strip() == ""
