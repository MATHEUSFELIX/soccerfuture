"""Unit tests for human evaluation pack generation."""

from __future__ import annotations

import json

import pytest

from src.evaluation.human_eval_pack import (
    generate_eval_pack,
    load_eval_pack,
    save_eval_pack,
)
from src.evaluation.human_eval_protocol import HumanEvalProtocol
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig


@pytest.fixture(scope="module")
def play_state():
    with open("data/play_states/counter_attack_midfield.json") as f:
        return dict_to_play_state(json.load(f))


@pytest.fixture(scope="module")
def config():
    return PipelineConfig(n=10, k=3, seed=42)


@pytest.fixture(scope="module")
def scenarios(play_state):
    return [
        {
            "scenario_id": "pack_s1",
            "play_state_file": "counter_attack_midfield.json",
            "play_state": play_state,
        }
    ]


def test_generate_eval_pack_returns_protocol(scenarios, config):
    """generate_eval_pack with 1 scenario returns HumanEvalProtocol."""
    pack = generate_eval_pack(scenarios, config=config)
    assert isinstance(pack, HumanEvalProtocol)


def test_pack_has_correct_scenario_count(scenarios, config):
    """Pack has same number of scenarios as input."""
    pack = generate_eval_pack(scenarios, config=config)
    assert len(pack.scenarios) == len(scenarios)


def test_pack_has_pipeline_report(scenarios, config):
    """Each scenario has a non-empty pipeline_report dict."""
    pack = generate_eval_pack(scenarios, config=config)
    for scenario in pack.scenarios:
        assert isinstance(scenario.pipeline_report, dict)
        assert len(scenario.pipeline_report) > 0


def test_save_load_round_trip(scenarios, config, tmp_path):
    """save_eval_pack then load_eval_pack returns valid dict."""
    pack = generate_eval_pack(scenarios, config=config)
    path = str(tmp_path / "eval_pack.json")
    save_eval_pack(pack, path)
    loaded = load_eval_pack(path)

    assert isinstance(loaded, dict)
    assert "protocol_id" in loaded
    assert "scenarios" in loaded
    assert len(loaded["scenarios"]) == 1
    assert "pipeline_report" in loaded["scenarios"][0]
