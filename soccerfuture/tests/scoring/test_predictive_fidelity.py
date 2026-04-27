"""Unit tests for the predictive fidelity scoring module.

Tests cover:
  - Identical branch and window score 1.0
  - Completely unrelated branch and window score < 0.3

Requirements: 6.1, 6.3
"""

from __future__ import annotations

import pytest

from src.scoring.predictive_fidelity import (
    PredictiveFidelityResult,
    score_predictive_fidelity,
)
from src.utils.constants import SIGNIFICANT_DIVERGENCE_THRESHOLD


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_positions(
    player_ids: list[str],
    coords: list[tuple[float, float]],
    timestamp: float = 1.0,
) -> list[dict]:
    """Build a list of position dicts from player IDs and (x, y) pairs."""
    return [
        {"player_id": pid, "x": x, "y": y, "timestamp": timestamp}
        for pid, (x, y) in zip(player_ids, coords)
    ]


def _make_events(
    event_types: list[str],
    timestamps: list[float],
    player_id: str = "P1",
) -> list[dict]:
    """Build a list of event dicts."""
    return [
        {
            "event_type": etype,
            "timestamp": ts,
            "player_id": player_id,
            "metadata": {},
        }
        for etype, ts in zip(event_types, timestamps)
    ]


# ---------------------------------------------------------------------------
# Tests — Identical branch and window (Requirement 6.1)
# ---------------------------------------------------------------------------


class TestIdenticalBranchAndWindow:
    """When branch and window contain the same data, fidelity should be 1.0."""

    def test_identical_positions_and_events(self) -> None:
        """Identical positions and events in branch and window yield score 1.0."""
        players = ["P1", "P2", "P3"]
        coords = [(10.0, 20.0), (15.0, 25.0), (20.0, 30.0)]
        positions = _make_positions(players, coords)
        events = _make_events(["pass", "dribble"], [1.0, 2.0])

        aligned_branch = {"positions": positions, "events": events}
        aligned_window = {
            "outcomes": [{"positions": positions, "events": events}],
        }

        result = score_predictive_fidelity(aligned_branch, aligned_window)

        assert isinstance(result, PredictiveFidelityResult)
        assert result.fidelity_score == pytest.approx(1.0)
        assert result.position_accuracy == pytest.approx(1.0)
        assert result.event_timing_accuracy == pytest.approx(1.0)
        assert result.formation_consistency == pytest.approx(1.0)

    def test_identical_positions_no_events(self) -> None:
        """Identical positions with no events still yield high fidelity."""
        players = ["P1", "P2"]
        coords = [(5.0, 10.0), (25.0, 40.0)]
        positions = _make_positions(players, coords)

        aligned_branch = {"positions": positions, "events": []}
        aligned_window = {
            "outcomes": [{"positions": positions, "events": []}],
        }

        result = score_predictive_fidelity(aligned_branch, aligned_window)

        # position_accuracy = 1.0, event_timing = 0.5 (neutral), formation = 1.0
        # fidelity = 0.5*1.0 + 0.3*0.5 + 0.2*1.0 = 0.85
        assert result.position_accuracy == pytest.approx(1.0)
        assert result.formation_consistency == pytest.approx(1.0)
        assert result.fidelity_score > 0.8


# ---------------------------------------------------------------------------
# Tests — Completely unrelated branch and window (Requirement 6.3)
# ---------------------------------------------------------------------------


class TestUnrelatedBranchAndWindow:
    """Completely unrelated branch and window should score below 0.3."""

    def test_far_apart_positions_different_events(self) -> None:
        """Branch at (0,0) vs window at (90,90) with different events."""
        branch_players = ["P1", "P2", "P3"]
        branch_coords = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
        branch_positions = _make_positions(branch_players, branch_coords)
        branch_events = _make_events(["pass"], [0.0])

        window_players = ["P1", "P2", "P3"]
        window_coords = [(90.0, 90.0), (91.0, 91.0), (92.0, 92.0)]
        window_positions = _make_positions(window_players, window_coords)
        window_events = _make_events(["tackle"], [10.0])

        aligned_branch = {
            "positions": branch_positions,
            "events": branch_events,
        }
        aligned_window = {
            "outcomes": [
                {"positions": window_positions, "events": window_events},
            ],
        }

        result = score_predictive_fidelity(aligned_branch, aligned_window)

        assert isinstance(result, PredictiveFidelityResult)
        assert result.fidelity_score < SIGNIFICANT_DIVERGENCE_THRESHOLD

    def test_far_apart_positions_no_matching_event_types(self) -> None:
        """Completely different positions and no matching event types."""
        branch_positions = _make_positions(
            ["P1", "P2"], [(0.0, 0.0), (1.0, 0.0)]
        )
        branch_events = _make_events(["pass", "dribble"], [0.0, 1.0])

        window_positions = _make_positions(
            ["P1", "P2"], [(90.0, 90.0), (91.0, 90.0)]
        )
        window_events = _make_events(["tackle", "foul"], [8.0, 9.0], player_id="P2")

        aligned_branch = {
            "positions": branch_positions,
            "events": branch_events,
        }
        aligned_window = {
            "outcomes": [
                {"positions": window_positions, "events": window_events},
            ],
        }

        result = score_predictive_fidelity(aligned_branch, aligned_window)

        assert result.fidelity_score < SIGNIFICANT_DIVERGENCE_THRESHOLD
        assert result.position_accuracy < 0.3


# ---------------------------------------------------------------------------
# Tests — All scores in valid range
# ---------------------------------------------------------------------------


class TestScoreRanges:
    """All returned scores must be in [0.0, 1.0]."""

    def test_all_scores_in_unit_range(self) -> None:
        branch_positions = _make_positions(["P1"], [(10.0, 20.0)])
        window_positions = _make_positions(["P1"], [(30.0, 40.0)])

        aligned_branch = {"positions": branch_positions, "events": []}
        aligned_window = {
            "outcomes": [{"positions": window_positions}],
        }

        result = score_predictive_fidelity(aligned_branch, aligned_window)

        for field in (
            result.fidelity_score,
            result.position_accuracy,
            result.event_timing_accuracy,
            result.formation_consistency,
        ):
            assert 0.0 <= field <= 1.0
