"""Integration tests for pipeline with and without match context.

Verifies that the pipeline correctly propagates MatchContext through
to the report, and that the no-context path remains stable.
"""

import json

import pytest

from src.domain.match_context import (
    ComparativeSignals,
    MatchContext,
    TeamContextMetrics,
)
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig, run_pipeline


def _sample_match_context() -> MatchContext:
    """Build a minimal MatchContext for integration testing."""
    return MatchContext(
        home_team="TeamA",
        away_team="TeamB",
        lookback_matches=10,
        source="soccerdata",
        cache_status="miss",
        home_metrics=TeamContextMetrics(
            matches_sampled=10, wins=6, draws=2, losses=2,
            goals_for_avg=1.8, goals_against_avg=0.9,
            xg_for_avg=1.7, xg_against_avg=1.0,
            form_points=20, elo=1650.0, style_tags=["high-press"],
        ),
        away_metrics=TeamContextMetrics(
            matches_sampled=10, wins=4, draws=3, losses=3,
            goals_for_avg=1.2, goals_against_avg=1.1,
            xg_for_avg=1.3, xg_against_avg=1.2,
            form_points=15, elo=1580.0, style_tags=["counter"],
        ),
        comparative_signals=ComparativeSignals(
            stronger_team="TeamA",
            form_edge="TeamA",
            attack_edge="TeamA",
            defense_edge="TeamA",
            notes=["TeamA dominates recent form"],
        ),
    )


@pytest.fixture(scope="module")
def play_state():
    with open("data/play_states/counter_attack_midfield.json") as f:
        return dict_to_play_state(json.load(f))


@pytest.fixture(scope="module")
def config():
    return PipelineConfig(n=15, k=3, seed=42)


class TestPipelineWithContext:
    """Pipeline run with a MatchContext populates context fields."""

    def test_report_match_context_not_none(self, play_state, config):
        report = run_pipeline(play_state, config, match_context=_sample_match_context())
        assert report.match_context is not None

    def test_report_context_signals_not_none(self, play_state, config):
        report = run_pipeline(play_state, config, match_context=_sample_match_context())
        assert report.context_signals is not None

    def test_metadata_context_requested_true(self, play_state, config):
        report = run_pipeline(play_state, config, match_context=_sample_match_context())
        assert report.metadata["context_requested"] is True

    def test_metadata_context_applied_true(self, play_state, config):
        report = run_pipeline(play_state, config, match_context=_sample_match_context())
        assert report.metadata["context_applied"] is True

    def test_report_still_has_ranked_branches(self, play_state, config):
        report = run_pipeline(play_state, config, match_context=_sample_match_context())
        assert len(report.ranked_branches) > 0


class TestPipelineWithoutContext:
    """Pipeline run without MatchContext leaves context fields as None."""

    def test_report_match_context_is_none(self, play_state, config):
        report = run_pipeline(play_state, config)
        assert report.match_context is None

    def test_report_context_signals_is_none(self, play_state, config):
        report = run_pipeline(play_state, config)
        assert report.context_signals is None

    def test_metadata_context_requested_false(self, play_state, config):
        report = run_pipeline(play_state, config)
        assert report.metadata["context_requested"] is False

    def test_metadata_context_applied_false(self, play_state, config):
        report = run_pipeline(play_state, config)
        assert report.metadata["context_applied"] is False

    def test_report_still_has_ranked_branches(self, play_state, config):
        report = run_pipeline(play_state, config)
        assert len(report.ranked_branches) > 0


class TestReportSchemaStability:
    """to_dict() always includes match_context and context_signals keys."""

    def test_to_dict_includes_context_keys_with_context(self, play_state, config):
        report = run_pipeline(play_state, config, match_context=_sample_match_context())
        d = report.to_dict()
        assert "match_context" in d
        assert "context_signals" in d
        assert d["match_context"] is not None
        assert d["context_signals"] is not None

    def test_to_dict_includes_context_keys_without_context(self, play_state, config):
        report = run_pipeline(play_state, config)
        d = report.to_dict()
        assert "match_context" in d
        assert "context_signals" in d
        assert d["match_context"] is None
        assert d["context_signals"] is None
