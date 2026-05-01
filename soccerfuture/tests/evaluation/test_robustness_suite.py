"""Unit tests for robustness degradation strategies."""

from __future__ import annotations

import copy
import json

import pytest

from src.evaluation.robustness_suite import (
    degrade_missing_players,
    degrade_noise,
    degrade_position_swap,
    degrade_time_shift,
)
from src.models.play_state import dict_to_play_state
from src.utils.constants import FIELD_LENGTH, FIELD_WIDTH


@pytest.fixture(scope="module")
def play_state():
    with open("data/play_states/counter_attack_midfield.json") as f:
        return dict_to_play_state(json.load(f))


# ---------------------------------------------------------------------------
# degrade_noise
# ---------------------------------------------------------------------------


def test_degrade_noise_deterministic(play_state):
    """Same seed → same output."""
    a = degrade_noise(play_state, seed=99)
    b = degrade_noise(play_state, seed=99)
    for pa, pb in zip(a.player_positions, b.player_positions):
        assert pa.x == pb.x
        assert pa.y == pb.y


def test_degrade_noise_positions_change(play_state):
    """Positions differ from original."""
    degraded = degrade_noise(play_state, seed=42, noise_scale=5.0)
    changed = False
    for orig, deg in zip(play_state.player_positions, degraded.player_positions):
        if orig.x != deg.x or orig.y != deg.y:
            changed = True
            break
    assert changed, "At least one position should change with noise"


def test_degrade_noise_within_bounds(play_state):
    """All positions within field bounds."""
    degraded = degrade_noise(play_state, seed=42, noise_scale=100.0)
    for pos in degraded.player_positions:
        assert 0.0 <= pos.x <= FIELD_WIDTH, f"x={pos.x} out of bounds"
        assert 0.0 <= pos.y <= FIELD_LENGTH, f"y={pos.y} out of bounds"


# ---------------------------------------------------------------------------
# degrade_missing_players
# ---------------------------------------------------------------------------


def test_degrade_missing_players_removes_correct_count(play_state):
    """2 players removed."""
    original_count = len(play_state.player_positions)
    degraded = degrade_missing_players(play_state, seed=42, drop_count=2)
    assert len(degraded.player_positions) == original_count - 2


def test_degrade_missing_players_removes_from_roles(play_state):
    """Roles dict also updated."""
    degraded = degrade_missing_players(play_state, seed=42, drop_count=2)
    remaining_ids = {p.player_id for p in degraded.player_positions}
    for pid in degraded.player_roles:
        assert pid in remaining_ids, (
            f"Role for {pid} still present but player was removed"
        )


# ---------------------------------------------------------------------------
# degrade_time_shift
# ---------------------------------------------------------------------------


def test_degrade_time_shift_increases_match_time(play_state):
    """match_time increases."""
    degraded = degrade_time_shift(play_state, shift_seconds=5.0)
    assert degraded.match_time == play_state.match_time + 5.0


# ---------------------------------------------------------------------------
# degrade_position_swap
# ---------------------------------------------------------------------------


def test_degrade_position_swap_swaps_two(play_state):
    """Exactly two players have swapped positions."""
    degraded = degrade_position_swap(play_state, seed=42)
    swapped_count = 0
    for orig, deg in zip(play_state.player_positions, degraded.player_positions):
        if orig.x != deg.x or orig.y != deg.y:
            swapped_count += 1
    assert swapped_count == 2, f"Expected 2 swapped, got {swapped_count}"


# ---------------------------------------------------------------------------
# Original not mutated
# ---------------------------------------------------------------------------


def test_original_not_mutated(play_state):
    """Original PlayState unchanged after degradation."""
    original_positions = [
        (p.player_id, p.x, p.y) for p in play_state.player_positions
    ]
    original_time = play_state.match_time
    original_roles = dict(play_state.player_roles)

    # Apply all degradation strategies
    degrade_noise(play_state, seed=1)
    degrade_missing_players(play_state, seed=1, drop_count=2)
    degrade_time_shift(play_state, shift_seconds=10.0)
    degrade_position_swap(play_state, seed=1)

    # Verify original is unchanged
    assert play_state.match_time == original_time
    assert dict(play_state.player_roles) == original_roles
    current_positions = [
        (p.player_id, p.x, p.y) for p in play_state.player_positions
    ]
    assert current_positions == original_positions
