"""Regression tests for match context integration.

Confirms that no-context pipeline execution preserves prior baseline
behavior and that explainability gracefully handles absent context.
"""

import json

import pytest

from src.explainability import build_context_notes
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig, run_pipeline


@pytest.fixture(scope="module")
def play_state():
    with open("data/play_states/counter_attack_midfield.json") as f:
        return dict_to_play_state(json.load(f))


@pytest.fixture(scope="module")
def config():
    return PipelineConfig(n=15, k=3, seed=42)


class TestNoContextBaselineStability:
    """Running pipeline without context is deterministic and context-free."""

    def test_deterministic_output(self, play_state, config):
        """Two runs with same seed produce identical ranked branch IDs and scores."""
        report_a = run_pipeline(play_state, config)
        report_b = run_pipeline(play_state, config)

        ids_a = [rb.branch_id for rb in report_a.ranked_branches]
        ids_b = [rb.branch_id for rb in report_b.ranked_branches]
        assert ids_a == ids_b

        scores_a = [rb.composite_score for rb in report_a.ranked_branches]
        scores_b = [rb.composite_score for rb in report_b.ranked_branches]
        assert scores_a == scores_b

    def test_no_context_keys_are_none(self, play_state, config):
        """Without context, match_context and context_signals are None."""
        report = run_pipeline(play_state, config)
        assert report.match_context is None
        assert report.context_signals is None


class TestExplainabilityNoContext:
    """build_context_notes returns the no-context message when given None."""

    def test_returns_no_context_message(self):
        notes = build_context_notes(None, None)
        assert len(notes) == 1
        assert "No external context applied" in notes[0]
