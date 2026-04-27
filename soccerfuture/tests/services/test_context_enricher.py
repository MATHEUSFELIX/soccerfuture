"""Tests for the context enricher service."""

import pytest

from src.domain.match_context import (
    ComparativeSignals,
    ContextSignals,
    MatchContext,
    TeamContextMetrics,
)
from src.services.context_enricher import enrich_context


def _make_metrics(
    *,
    goals_for_avg: float | None = 1.5,
    goals_against_avg: float | None = 1.0,
    xg_for_avg: float | None = 1.4,
    xg_against_avg: float | None = 1.1,
    form_points: int | None = 15,
) -> TeamContextMetrics:
    """Helper to build TeamContextMetrics with sensible defaults."""
    return TeamContextMetrics(
        matches_sampled=5,
        wins=2,
        draws=1,
        losses=2,
        goals_for_avg=goals_for_avg,
        goals_against_avg=goals_against_avg,
        xg_for_avg=xg_for_avg,
        xg_against_avg=xg_against_avg,
        form_points=form_points,
    )


def _make_context(
    *,
    home_metrics: TeamContextMetrics | None = None,
    away_metrics: TeamContextMetrics | None = None,
    comparative: ComparativeSignals | None = None,
) -> MatchContext:
    """Helper to build a MatchContext with defaults."""
    return MatchContext(
        home_team="HomeFC",
        away_team="AwayFC",
        lookback_matches=5,
        source="test",
        cache_status="miss",
        home_metrics=home_metrics or _make_metrics(),
        away_metrics=away_metrics or _make_metrics(),
        comparative_signals=comparative or ComparativeSignals(),
    )


class TestNeutralDefaults:
    """MatchContext with equal metrics → all signals near 0.0."""

    def test_equal_metrics_produce_neutral_signals(self) -> None:
        ctx = _make_context()
        signals = enrich_context(ctx)

        assert signals.aggression_bias == pytest.approx(0.0, abs=0.01)
        assert signals.risk_tolerance == pytest.approx(0.0, abs=0.01)
        assert signals.retention_bias == pytest.approx(0.0, abs=0.01)
        assert signals.likely_game_state_pressure == pytest.approx(0.0, abs=0.01)


class TestHomeAttackingEdge:
    """Home has attack_edge → positive aggression_bias."""

    def test_attack_edge_increases_aggression(self) -> None:
        comp = ComparativeSignals(attack_edge="HomeFC")
        ctx = _make_context(comparative=comp)
        signals = enrich_context(ctx)

        assert signals.aggression_bias > 0.0
        assert signals.aggression_bias >= 0.1

    def test_away_attack_edge_decreases_aggression(self) -> None:
        comp = ComparativeSignals(attack_edge="AwayFC")
        ctx = _make_context(comparative=comp)
        signals = enrich_context(ctx)

        assert signals.aggression_bias < 0.0


class TestFormEdge:
    """Away has form_edge → risk_tolerance stays near zero for home."""

    def test_home_form_edge_increases_risk(self) -> None:
        comp = ComparativeSignals(form_edge="HomeFC")
        ctx = _make_context(comparative=comp)
        signals = enrich_context(ctx)

        assert signals.risk_tolerance >= 0.1

    def test_away_form_edge_no_positive_risk(self) -> None:
        comp = ComparativeSignals(form_edge="AwayFC")
        ctx = _make_context(comparative=comp)
        signals = enrich_context(ctx)

        assert signals.risk_tolerance == pytest.approx(0.0, abs=0.01)


class TestPartialData:
    """Metrics with all None optional fields → neutral signals with note."""

    def test_all_none_optionals_produce_neutral_signals(self) -> None:
        none_metrics = _make_metrics(
            goals_for_avg=None,
            goals_against_avg=None,
            xg_for_avg=None,
            xg_against_avg=None,
            form_points=None,
        )
        ctx = _make_context(home_metrics=none_metrics, away_metrics=none_metrics)
        signals = enrich_context(ctx)

        assert signals.aggression_bias == pytest.approx(0.0, abs=0.01)
        assert signals.risk_tolerance == pytest.approx(0.0, abs=0.01)
        assert signals.retention_bias == pytest.approx(0.0, abs=0.01)
        assert signals.likely_game_state_pressure == pytest.approx(0.0, abs=0.01)
        assert any("Partial data" in n for n in signals.notes)


class TestNoteGeneration:
    """Verify notes list is non-empty and contains relevant descriptions."""

    def test_notes_present_with_edges(self) -> None:
        comp = ComparativeSignals(attack_edge="HomeFC", defense_edge="HomeFC")
        ctx = _make_context(comparative=comp)
        signals = enrich_context(ctx)

        assert len(signals.notes) >= 1
        assert any("attacking" in n.lower() for n in signals.notes)

    def test_notes_present_for_partial_data(self) -> None:
        none_metrics = _make_metrics(xg_for_avg=None)
        ctx = _make_context(home_metrics=none_metrics)
        signals = enrich_context(ctx)

        assert any("Partial data" in n for n in signals.notes)


class TestSignalRanges:
    """All signals stay within their valid ranges."""

    def test_aggression_in_range(self) -> None:
        comp = ComparativeSignals(attack_edge="HomeFC")
        home = _make_metrics(xg_for_avg=3.0)
        away = _make_metrics(xg_for_avg=0.5)
        ctx = _make_context(home_metrics=home, away_metrics=away, comparative=comp)
        signals = enrich_context(ctx)

        assert -1.0 <= signals.aggression_bias <= 1.0

    def test_risk_in_range(self) -> None:
        comp = ComparativeSignals(form_edge="HomeFC")
        home = _make_metrics(goals_for_avg=0.5)
        away = _make_metrics(goals_for_avg=3.0)
        ctx = _make_context(home_metrics=home, away_metrics=away, comparative=comp)
        signals = enrich_context(ctx)

        assert -1.0 <= signals.risk_tolerance <= 1.0

    def test_retention_in_range(self) -> None:
        comp = ComparativeSignals(defense_edge="HomeFC")
        home = _make_metrics(goals_against_avg=0.3)
        away = _make_metrics(goals_against_avg=2.5)
        ctx = _make_context(home_metrics=home, away_metrics=away, comparative=comp)
        signals = enrich_context(ctx)

        assert -1.0 <= signals.retention_bias <= 1.0

    def test_pressure_in_range(self) -> None:
        home = _make_metrics(form_points=30)
        away = _make_metrics(form_points=5)
        ctx = _make_context(home_metrics=home, away_metrics=away)
        signals = enrich_context(ctx)

        assert 0.0 <= signals.likely_game_state_pressure <= 1.0
