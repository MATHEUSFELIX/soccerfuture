"""Integration tests for demo play state JSON files.

Verifies that each demo file loads successfully via dict_to_play_state,
contains at least 5 player positions, and produces a valid PipelineReport
when run through the pipeline.

Requirements: 11.4
"""

import json
from pathlib import Path

import pytest

from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig, run_pipeline

DEMO_DIR = Path("data/play_states")

DEMO_FILES = [
    "counter_attack_midfield.json",
    "build_up_from_defense.json",
    "set_piece_penalty_area.json",
]


def _load_play_state(filename: str):
    """Load a PlayState from a demo JSON file."""
    path = DEMO_DIR / filename
    with open(path) as f:
        data = json.load(f)
    return dict_to_play_state(data)


@pytest.mark.parametrize("filename", DEMO_FILES)
def test_demo_file_loads_successfully(filename: str) -> None:
    """Each demo file loads into a valid PlayState without errors."""
    ps = _load_play_state(filename)
    assert ps.match_time >= 0
    assert ps.possession_team
    assert ps.game_phase in ("open_play", "set_piece", "transition", "dead_ball")
    assert ps.game_clock > 0
    assert ps.decision_point_timestamp >= 0


@pytest.mark.parametrize("filename", DEMO_FILES)
def test_demo_file_has_at_least_five_positions(filename: str) -> None:
    """Each demo file contains at least 5 player positions."""
    ps = _load_play_state(filename)
    assert len(ps.player_positions) >= 5


@pytest.mark.parametrize("filename", DEMO_FILES)
def test_demo_file_produces_valid_pipeline_report(filename: str) -> None:
    """Each demo file produces a valid PipelineReport through the pipeline."""
    ps = _load_play_state(filename)
    config = PipelineConfig(n=10, k=3, seed=42)
    report = run_pipeline(ps, config)

    assert report.play_state is not None
    assert len(report.evaluated_branches) > 0
    assert report.metadata.get("n_generated") == 10
    assert report.metadata.get("k_requested") == 3
    assert "execution_time_seconds" in report.metadata

    # Verify the report is JSON-serializable
    report_dict = report.to_dict()
    json.dumps(report_dict)
