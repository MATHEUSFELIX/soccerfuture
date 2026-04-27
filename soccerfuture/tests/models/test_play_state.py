"""Unit tests for PlayState model and serialization helpers.

Tests dataclass construction, default values, serialization via
play_state_to_dict, deserialization via dict_to_play_state, and
error handling for missing required fields.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 11.5
"""

import pytest

from src.models.branch import PlayerPosition
from src.models.play_state import PlayState, dict_to_play_state, play_state_to_dict


def _make_positions() -> list[PlayerPosition]:
    """Create a small list of PlayerPosition objects for testing."""
    return [
        PlayerPosition(player_id="P1", x=10.0, y=25.0, timestamp=1.0),
        PlayerPosition(player_id="P2", x=20.0, y=30.0, timestamp=1.0),
    ]


def _make_play_state(**overrides) -> PlayState:
    """Create a PlayState with sensible defaults, allowing field overrides."""
    defaults = dict(
        match_time=45.0,
        possession_team="home",
        ball_position={"x": 34.0, "y": 52.5},
        game_phase="open_play",
        score_differential=0,
        game_clock=2700.0,
        player_positions=_make_positions(),
        decision_point_timestamp=1.5,
        player_roles={"P1": "ST", "P2": "CM"},
        metadata={"formation": "4-3-3"},
    )
    defaults.update(overrides)
    return PlayState(**defaults)


class TestPlayStateConstruction:
    """Tests for PlayState dataclass instantiation."""

    def test_construction_with_all_fields(self) -> None:
        positions = _make_positions()
        ps = PlayState(
            match_time=75.0,
            possession_team="away",
            ball_position={"x": 50.0, "y": 80.0},
            game_phase="set_piece",
            score_differential=-1,
            game_clock=900.0,
            player_positions=positions,
            decision_point_timestamp=2.0,
            player_roles={"P1": "GK", "P2": "CB"},
            metadata={"weather": "clear"},
        )
        assert ps.match_time == 75.0
        assert ps.possession_team == "away"
        assert ps.ball_position == {"x": 50.0, "y": 80.0}
        assert ps.game_phase == "set_piece"
        assert ps.score_differential == -1
        assert ps.game_clock == 900.0
        assert ps.player_positions == positions
        assert ps.decision_point_timestamp == 2.0
        assert ps.player_roles == {"P1": "GK", "P2": "CB"}
        assert ps.metadata == {"weather": "clear"}

    def test_default_metadata_is_empty_dict(self) -> None:
        ps = PlayState(
            match_time=45.0,
            possession_team="home",
            ball_position={"x": 34.0, "y": 52.5},
            game_phase="open_play",
            score_differential=0,
            game_clock=2700.0,
            player_positions=_make_positions(),
            decision_point_timestamp=1.0,
        )
        assert ps.metadata == {}
        assert ps.player_roles == {}


class TestPlayStateToDict:
    """Tests for play_state_to_dict serialization."""

    def test_output_contains_expected_keys(self) -> None:
        ps = _make_play_state()
        result = play_state_to_dict(ps)

        expected_keys = {
            "match_time",
            "possession_team",
            "ball_position",
            "game_phase",
            "score_differential",
            "game_clock",
            "player_positions",
            "decision_point_timestamp",
            "player_roles",
            "metadata",
        }
        assert set(result.keys()) == expected_keys

    def test_player_positions_are_dicts(self) -> None:
        ps = _make_play_state()
        result = play_state_to_dict(ps)

        for pp in result["player_positions"]:
            assert isinstance(pp, dict)
            assert "player_id" in pp
            assert "x" in pp
            assert "y" in pp
            assert "timestamp" in pp


class TestDictToPlayState:
    """Tests for dict_to_play_state deserialization."""

    def test_round_trip(self) -> None:
        original = _make_play_state()
        d = play_state_to_dict(original)
        restored = dict_to_play_state(d)

        assert restored.match_time == original.match_time
        assert restored.possession_team == original.possession_team
        assert restored.ball_position == original.ball_position
        assert restored.game_phase == original.game_phase
        assert restored.score_differential == original.score_differential
        assert restored.game_clock == original.game_clock
        assert restored.decision_point_timestamp == original.decision_point_timestamp
        assert restored.player_roles == original.player_roles
        assert restored.metadata == original.metadata
        assert len(restored.player_positions) == len(original.player_positions)
        for orig_pp, rest_pp in zip(
            original.player_positions, restored.player_positions
        ):
            assert rest_pp.player_id == orig_pp.player_id
            assert rest_pp.x == orig_pp.x
            assert rest_pp.y == orig_pp.y
            assert rest_pp.timestamp == orig_pp.timestamp

    def test_raises_key_error_on_missing_required_field(self) -> None:
        ps = _make_play_state()
        d = play_state_to_dict(ps)
        del d["match_time"]

        with pytest.raises(KeyError, match="match_time"):
            dict_to_play_state(d)

    def test_raises_key_error_lists_all_missing_fields(self) -> None:
        d = {"metadata": {}, "player_roles": {}}

        with pytest.raises(KeyError, match="match_time"):
            dict_to_play_state(d)
