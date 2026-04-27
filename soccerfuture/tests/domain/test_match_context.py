"""Unit tests for src/domain/match_context.py.

Covers round-trip serialization, required field validation, optional field
defaults, ContextSignals round-trip and defaults, and invalid payload failures.
"""

import pytest
from dataclasses import asdict

from src.domain.match_context import (
    ComparativeSignals,
    ContextSignals,
    MatchContext,
    TeamContextMetrics,
    context_signals_to_dict,
    dict_to_context_signals,
    dict_to_match_context,
    match_context_to_dict,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_team_metrics(**overrides: object) -> TeamContextMetrics:
    """Create a TeamContextMetrics with all fields populated."""
    defaults = dict(
        matches_sampled=10,
        wins=6,
        draws=2,
        losses=2,
        goals_for_avg=1.8,
        goals_against_avg=0.9,
        xg_for_avg=1.7,
        xg_against_avg=1.0,
        form_points=20,
        elo=1650.0,
        style_tags=["high-press", "counter"],
    )
    defaults.update(overrides)
    return TeamContextMetrics(**defaults)


def _make_comparative_signals(**overrides: object) -> ComparativeSignals:
    defaults = dict(
        stronger_team="TeamA",
        form_edge="TeamA",
        attack_edge="TeamB",
        defense_edge="TeamA",
        notes=["TeamA dominates set pieces"],
    )
    defaults.update(overrides)
    return ComparativeSignals(**defaults)


def _make_match_context(**overrides: object) -> MatchContext:
    defaults = dict(
        home_team="TeamA",
        away_team="TeamB",
        lookback_matches=5,
        source="soccerdata",
        cache_status="miss",
        home_metrics=_make_team_metrics(),
        away_metrics=_make_team_metrics(wins=4, losses=4),
        comparative_signals=_make_comparative_signals(),
        competition="Premier League",
        season="2024-25",
        fetched_at="2025-01-15T12:00:00Z",
    )
    defaults.update(overrides)
    return MatchContext(**defaults)


# ---------------------------------------------------------------------------
# 1. Round-trip serialization
# ---------------------------------------------------------------------------


class TestMatchContextRoundTrip:
    """match_context_to_dict -> dict_to_match_context preserves all fields."""

    def test_full_round_trip(self) -> None:
        original = _make_match_context()
        serialized = match_context_to_dict(original)
        restored = dict_to_match_context(serialized)

        # Top-level scalars
        assert restored.home_team == original.home_team
        assert restored.away_team == original.away_team
        assert restored.lookback_matches == original.lookback_matches
        assert restored.source == original.source
        assert restored.cache_status == original.cache_status
        assert restored.competition == original.competition
        assert restored.season == original.season
        assert restored.fetched_at == original.fetched_at

        # Nested TeamContextMetrics
        for attr in (
            "matches_sampled", "wins", "draws", "losses",
            "goals_for_avg", "goals_against_avg",
            "xg_for_avg", "xg_against_avg",
            "form_points", "elo", "style_tags",
        ):
            assert getattr(restored.home_metrics, attr) == getattr(original.home_metrics, attr)
            assert getattr(restored.away_metrics, attr) == getattr(original.away_metrics, attr)

        # Nested ComparativeSignals
        for attr in ("stronger_team", "form_edge", "attack_edge", "defense_edge", "notes"):
            assert getattr(restored.comparative_signals, attr) == getattr(
                original.comparative_signals, attr
            )


    def test_round_trip_produces_correct_types(self) -> None:
        original = _make_match_context()
        restored = dict_to_match_context(match_context_to_dict(original))

        assert isinstance(restored, MatchContext)
        assert isinstance(restored.home_metrics, TeamContextMetrics)
        assert isinstance(restored.away_metrics, TeamContextMetrics)
        assert isinstance(restored.comparative_signals, ComparativeSignals)


# ---------------------------------------------------------------------------
# 2. Required field validation
# ---------------------------------------------------------------------------


REQUIRED_FIELDS = [
    "home_team",
    "away_team",
    "lookback_matches",
    "source",
    "cache_status",
    "home_metrics",
    "away_metrics",
    "comparative_signals",
]


class TestRequiredFieldValidation:
    """Removing any required field from a valid dict raises KeyError."""

    @pytest.mark.parametrize("field_name", REQUIRED_FIELDS)
    def test_missing_required_field_raises_key_error(self, field_name: str) -> None:
        valid_dict = match_context_to_dict(_make_match_context())
        del valid_dict[field_name]

        with pytest.raises(KeyError, match=field_name):
            dict_to_match_context(valid_dict)


# ---------------------------------------------------------------------------
# 3. Optional field defaults
# ---------------------------------------------------------------------------


class TestOptionalFieldDefaults:
    """Optional fields default to None when omitted."""

    def test_match_context_optional_fields_default_to_none(self) -> None:
        ctx = MatchContext(
            home_team="A",
            away_team="B",
            lookback_matches=3,
            source="test",
            cache_status="miss",
            home_metrics=_make_team_metrics(),
            away_metrics=_make_team_metrics(),
            comparative_signals=_make_comparative_signals(),
        )
        assert ctx.competition is None
        assert ctx.season is None
        assert ctx.fetched_at is None

    def test_team_metrics_optional_fields_default(self) -> None:
        metrics = TeamContextMetrics(
            matches_sampled=5, wins=2, draws=1, losses=2,
        )
        assert metrics.goals_for_avg is None
        assert metrics.goals_against_avg is None
        assert metrics.xg_for_avg is None
        assert metrics.xg_against_avg is None
        assert metrics.form_points is None
        assert metrics.elo is None
        assert metrics.style_tags == []


# ---------------------------------------------------------------------------
# 4. ContextSignals round-trip
# ---------------------------------------------------------------------------


class TestContextSignalsRoundTrip:
    """context_signals_to_dict -> dict_to_context_signals preserves values."""

    def test_full_round_trip(self) -> None:
        original = ContextSignals(
            aggression_bias=0.5,
            risk_tolerance=-0.3,
            retention_bias=0.8,
            likely_game_state_pressure=0.6,
            notes=["High press expected", "Counter likely"],
        )
        serialized = context_signals_to_dict(original)
        restored = dict_to_context_signals(serialized)

        assert restored.aggression_bias == original.aggression_bias
        assert restored.risk_tolerance == original.risk_tolerance
        assert restored.retention_bias == original.retention_bias
        assert restored.likely_game_state_pressure == original.likely_game_state_pressure
        assert restored.notes == original.notes


# ---------------------------------------------------------------------------
# 5. ContextSignals defaults
# ---------------------------------------------------------------------------


class TestContextSignalsDefaults:
    """Empty dict produces all-zero signals with empty notes."""

    def test_empty_dict_gives_defaults(self) -> None:
        signals = dict_to_context_signals({})

        assert signals.aggression_bias == 0.0
        assert signals.risk_tolerance == 0.0
        assert signals.retention_bias == 0.0
        assert signals.likely_game_state_pressure == 0.0
        assert signals.notes == []


# ---------------------------------------------------------------------------
# 6. Invalid payload failures
# ---------------------------------------------------------------------------


class TestInvalidPayloadFailures:
    """Malformed dicts raise appropriate errors."""

    def test_home_metrics_as_string_raises_type_error(self) -> None:
        valid_dict = match_context_to_dict(_make_match_context())
        valid_dict["home_metrics"] = "not-a-dict"

        with pytest.raises(TypeError):
            dict_to_match_context(valid_dict)

    def test_empty_dict_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            dict_to_match_context({})
