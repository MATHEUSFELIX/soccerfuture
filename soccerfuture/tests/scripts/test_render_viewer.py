"""Tests for scripts/render_viewer.py CLI helpers and main flow.

Validates: Requirements 10.1, 10.2, 10.3, 10.4
"""

import json
import sys

import matplotlib
matplotlib.use("Agg")

import pytest

from scripts.render_viewer import load_report_from_json, save_report_to_json, main


# Minimal valid report dict that render_pipeline_report can consume.
SAMPLE_REPORT: dict = {
    "play_state": {
        "match_time": 45.0,
        "possession_team": "home",
        "ball_position": {"x": 34.0, "y": 52.5},
        "game_phase": "open_play",
        "score_differential": 0,
        "player_positions": [
            {"player_id": "ST1", "x": 26.66, "y": 49.0},
        ],
        "player_roles": {"ST1": "ST"},
        "metadata": {},
    },
    "ranked_branches": [
        {
            "branch_id": "gen-001",
            "composite_score": 0.62,
            "evaluation_report": {
                "validity_score": 0.78,
                "opportunity_score": 0.46,
                "ranking_explanation": {
                    "promoted_factors": ["Physical Speed"],
                    "penalized_factors": [],
                    "top_scoring_block": "Physical Speed",
                    "bottom_scoring_block": "Turnover Risk",
                    "near_threshold_warning": None,
                },
            },
            "branch": {
                "positions": [
                    {"player_id": "ST1", "x": 26.66, "y": 52.0, "timestamp": 2.0},
                    {"player_id": "ST1", "x": 27.0, "y": 55.0, "timestamp": 2.5},
                ],
            },
        },
    ],
    "metadata": {
        "telemetry": {
            "branches_generated": 20,
            "hard_fail_count": 0,
            "score_filtered_count": 0,
            "avg_score_by_strategy": {},
            "time_per_stage": {},
        },
    },
}


class TestLoadReportFromJson:
    """Validates: Requirements 10.1, 10.2"""

    def test_loads_valid_json(self, tmp_path: "pytest.TempPathFactory") -> None:
        """Requirement 10.1: load_report_from_json reads a valid JSON file."""
        json_file = tmp_path / "report.json"
        json_file.write_text(json.dumps(SAMPLE_REPORT), encoding="utf-8")

        result = load_report_from_json(str(json_file))
        assert result == SAMPLE_REPORT

    def test_raises_file_not_found(self) -> None:
        """Requirement 10.1: raises FileNotFoundError on missing file."""
        with pytest.raises(FileNotFoundError):
            load_report_from_json("/nonexistent/path/report.json")


class TestSaveReportToJson:
    """Validates: Requirements 10.2, 10.3"""

    def test_writes_valid_json_with_indent(self, tmp_path: "pytest.TempPathFactory") -> None:
        """Requirement 10.3: save_report_to_json writes JSON with 2-space indent."""
        out_path = tmp_path / "out" / "report.json"
        save_report_to_json(SAMPLE_REPORT, str(out_path))

        raw = out_path.read_text(encoding="utf-8")
        loaded = json.loads(raw)
        assert loaded == SAMPLE_REPORT
        # Verify 2-space indent: re-serialize with indent=2 and compare.
        expected_raw = json.dumps(SAMPLE_REPORT, indent=2)
        assert raw == expected_raw


class TestMainFromJson:
    """Validates: Requirements 10.1, 10.4"""

    def test_main_from_json_creates_png(
        self, tmp_path: "pytest.TempPathFactory", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Requirement 10.4: main() with --from-json loads JSON and produces a PNG."""
        # Write a fixture report JSON.
        json_path = tmp_path / "fixture_report.json"
        json_path.write_text(json.dumps(SAMPLE_REPORT), encoding="utf-8")

        # Redirect output directory to tmp_path so we don't pollute the repo.
        output_dir = tmp_path / "viewer_output"
        monkeypatch.setattr("scripts.render_viewer.OUTPUT_DIR", str(output_dir))

        # Monkeypatch sys.argv for argparse.
        monkeypatch.setattr(
            sys, "argv", ["render_viewer.py", "--from-json", str(json_path)]
        )

        # main() calls sys.exit(0) on success — catch it.
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        # Verify a PNG was created in the output directory.
        png_files = list(output_dir.glob("*.png"))
        assert len(png_files) == 1
        assert png_files[0].name == "fixture_report.png"
