"""Regression tests ensuring no-context baseline remains unchanged.

Verifies deterministic pipeline output and absence of context fields
when no MatchContext is provided.
"""

from __future__ import annotations

import json

import pytest

from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig, run_pipeline


@pytest.fixture(scope="module")
def play_state():
    with open("data/play_states/counter_attack_midfield.json") as f:
        return dict_to_play_state(json.load(f))


@pytest.fixture(scope="module")
def config():
    return PipelineConfig(n=15, k=3, seed=42)


# ---------------------------------------------------------------------------
# TestNoContextBaselineUnchanged
# ---------------------------------------------------------------------------


class TestNoContextBaselineUnchanged:
    """No-context pipeline runs must be deterministic and context-free."""

    def test_no_context_pipeline_deterministic(self, play_state, config):
        """Two runs with same seed produce identical ranked branch IDs and scores."""
        report_a = run_pipeline(play_state, config)
        report_b = run_pipeline(play_state, config)

        ids_a = [rb.branch_id for rb in report_a.ranked_branches]
        ids_b = [rb.branch_id for rb in report_b.ranked_branches]
        assert ids_a == ids_b

        scores_a = [rb.composite_score for rb in report_a.ranked_branches]
        scores_b = [rb.composite_score for rb in report_b.ranked_branches]
        assert scores_a == scores_b

    def test_no_context_report_has_no_context_fields(self, play_state, config):
        """Without context, match_context and context_signals are None."""
        report = run_pipeline(play_state, config)
        assert report.match_context is None
        assert report.context_signals is None
