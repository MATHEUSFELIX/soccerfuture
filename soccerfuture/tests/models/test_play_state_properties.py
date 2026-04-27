"""Property-based tests for PlayState serialization.

Feature: soccer-domain-migration
- Property 1: PlayState round-trip serialization
- Property 2: PlayState validation rejects missing soccer fields

Validates: Requirements 3.4, 3.5
"""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.play_state import PlayState, dict_to_play_state, play_state_to_dict
from tests.strategies import play_state_strategy

# Required fields that dict_to_play_state checks for
_REQUIRED_FIELDS = [
    "match_time",
    "possession_team",
    "ball_position",
    "game_phase",
    "score_differential",
    "game_clock",
    "player_positions",
    "decision_point_timestamp",
]


class TestPlayStateRoundTripProperty:
    """Property 1: PlayState round-trip serialization.

    For any valid PlayState with soccer fields, serializing via
    play_state_to_dict, converting to JSON via json.dumps, deserializing
    via json.loads, and reconstructing via dict_to_play_state SHALL
    produce an equivalent PlayState.
    """

    @given(ps=play_state_strategy())
    @settings(max_examples=100)
    def test_round_trip_serialization(self, ps: PlayState) -> None:
        """**Validates: Requirements 3.4**

        Feature: soccer-domain-migration, Property 1: PlayState round-trip serialization
        """
        # Serialize
        as_dict = play_state_to_dict(ps)
        json_str = json.dumps(as_dict)

        # Deserialize
        restored_dict = json.loads(json_str)
        restored = dict_to_play_state(restored_dict)

        # Assert equivalence on all soccer fields
        assert restored.match_time == ps.match_time
        assert restored.possession_team == ps.possession_team
        assert restored.ball_position == ps.ball_position
        assert restored.game_phase == ps.game_phase
        assert restored.score_differential == ps.score_differential
        assert restored.game_clock == ps.game_clock
        assert restored.decision_point_timestamp == ps.decision_point_timestamp
        assert restored.player_roles == ps.player_roles
        assert restored.metadata == ps.metadata

        # Assert player positions match
        assert len(restored.player_positions) == len(ps.player_positions)
        for orig, rest in zip(ps.player_positions, restored.player_positions):
            assert rest.player_id == orig.player_id
            assert rest.x == orig.x
            assert rest.y == orig.y
            assert rest.timestamp == orig.timestamp


class TestPlayStateParserRejectionProperty:
    """Property 2: PlayState validation rejects missing soccer fields.

    For any dict with a random subset of required soccer PlayState fields
    removed, calling dict_to_play_state SHALL raise a KeyError.
    """

    @given(
        ps=play_state_strategy(),
        fields_to_remove=st.lists(
            st.sampled_from(_REQUIRED_FIELDS),
            min_size=1,
            max_size=len(_REQUIRED_FIELDS),
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_parser_rejects_missing_fields(
        self, ps: PlayState, fields_to_remove: list[str]
    ) -> None:
        """**Validates: Requirements 3.5**

        Feature: soccer-domain-migration, Property 2: PlayState validation rejects missing soccer fields
        """
        # Build a valid dict then remove a random subset of required fields
        as_dict = play_state_to_dict(ps)
        for field_name in fields_to_remove:
            as_dict.pop(field_name, None)

        # dict_to_play_state must raise on the incomplete dict
        with pytest.raises((KeyError, TypeError)):
            dict_to_play_state(as_dict)
