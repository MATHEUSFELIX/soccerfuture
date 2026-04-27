"""Unit tests for the alignment module.

Tests cover:
  - Known temporal/spatial offset produces expected aligned positions
  - Zero-offset case is identity
  - Large residual is flagged in output
  - Originals are not mutated
"""

from __future__ import annotations

import math

import pytest

from src.scoring.alignment import AlignmentResult, align
from src.utils.constants import ALIGNMENT_RESIDUAL_TOLERANCE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_branch(
    decision_ts: float, positions: list[dict]
) -> dict:
    """Build a minimal branch dict."""
    return {
        "branch_id": "b1",
        "decision_point_timestamp": decision_ts,
        "positions": positions,
        "events": [],
        "player_roles": {},
        "metadata": {},
    }


def _make_window(
    decision_ts: float, outcome_positions: list[list[dict]]
) -> dict:
    """Build a minimal continuation-window dict."""
    outcomes = [{"positions": p} for p in outcome_positions]
    return {
        "window_id": "w1",
        "decision_point_timestamp": decision_ts,
        "outcomes": outcomes,
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAlignZeroOffset:
    """When branch and window share the same decision-point timestamp
    and the same average position, offsets should be zero and positions
    unchanged."""

    def test_zero_offset_identity(self) -> None:
        positions = [
            {"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 1.0},
            {"player_id": "P1", "x": 10.5, "y": 20.5, "timestamp": 1.1},
        ]
        branch = _make_branch(1.0, positions)
        window = _make_window(1.0, [positions])

        result = align(branch, window)

        assert isinstance(result, AlignmentResult)
        assert result.temporal_offset == pytest.approx(0.0)
        assert result.spatial_offset == pytest.approx(0.0)
        assert result.residual_magnitude == pytest.approx(0.0)

        # Positions should be unchanged
        for orig, aligned in zip(
            branch["positions"], result.aligned_branch["positions"]
        ):
            assert aligned["x"] == pytest.approx(orig["x"])
            assert aligned["y"] == pytest.approx(orig["y"])
            assert aligned["timestamp"] == pytest.approx(orig["timestamp"])


class TestAlignKnownOffset:
    """When branch and window have a known temporal and spatial offset,
    the aligned branch should be shifted accordingly."""

    def test_temporal_shift(self) -> None:
        branch = _make_branch(
            decision_ts=2.0,
            positions=[
                {"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 2.0},
                {"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 2.5},
            ],
        )
        window = _make_window(
            decision_ts=1.0,
            outcome_positions=[
                [{"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 1.0}]
            ],
        )

        result = align(branch, window)

        # temporal_offset = 2.0 - 1.0 = 1.0
        assert result.temporal_offset == pytest.approx(1.0)
        # Branch timestamps shifted by -1.0
        assert result.aligned_branch["positions"][0]["timestamp"] == pytest.approx(1.0)
        assert result.aligned_branch["positions"][1]["timestamp"] == pytest.approx(1.5)

    def test_spatial_shift(self) -> None:
        # Branch player at (10, 20), window player at (5, 10)
        branch = _make_branch(
            decision_ts=1.0,
            positions=[
                {"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 1.0},
            ],
        )
        window = _make_window(
            decision_ts=1.0,
            outcome_positions=[
                [{"player_id": "P1", "x": 5.0, "y": 10.0, "timestamp": 1.0}]
            ],
        )

        result = align(branch, window)

        # spatial_offset = sqrt((10-5)^2 + (20-10)^2) = sqrt(125)
        expected_spatial = math.sqrt(125.0)
        assert result.spatial_offset == pytest.approx(expected_spatial)
        # Branch position shifted by dx=-5, dy=-10
        assert result.aligned_branch["positions"][0]["x"] == pytest.approx(5.0)
        assert result.aligned_branch["positions"][0]["y"] == pytest.approx(10.0)

    def test_combined_offset(self) -> None:
        branch = _make_branch(
            decision_ts=3.0,
            positions=[
                {"player_id": "P1", "x": 15.0, "y": 30.0, "timestamp": 3.0},
            ],
        )
        window = _make_window(
            decision_ts=1.0,
            outcome_positions=[
                [{"player_id": "P1", "x": 10.0, "y": 25.0, "timestamp": 1.0}]
            ],
        )

        result = align(branch, window)

        assert result.temporal_offset == pytest.approx(2.0)
        spatial = math.sqrt(5.0**2 + 5.0**2)
        assert result.spatial_offset == pytest.approx(spatial)
        residual = math.sqrt(2.0**2 + spatial**2)
        assert result.residual_magnitude == pytest.approx(residual)


class TestAlignResidual:
    """Residual magnitude should reflect combined temporal + spatial offset."""

    def test_large_residual_exceeds_tolerance(self) -> None:
        # Create a large offset that exceeds ALIGNMENT_RESIDUAL_TOLERANCE
        branch = _make_branch(
            decision_ts=5.0,
            positions=[
                {"player_id": "P1", "x": 30.0, "y": 50.0, "timestamp": 5.0},
            ],
        )
        window = _make_window(
            decision_ts=1.0,
            outcome_positions=[
                [{"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 1.0}]
            ],
        )

        result = align(branch, window)

        assert result.residual_magnitude > ALIGNMENT_RESIDUAL_TOLERANCE
        assert result.residual_magnitude > 0.0

    def test_small_residual_within_tolerance(self) -> None:
        # Tiny offset that stays within tolerance
        branch = _make_branch(
            decision_ts=1.001,
            positions=[
                {"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 1.001},
            ],
        )
        window = _make_window(
            decision_ts=1.0,
            outcome_positions=[
                [{"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 1.0}]
            ],
        )

        result = align(branch, window)

        assert result.residual_magnitude < ALIGNMENT_RESIDUAL_TOLERANCE


class TestAlignNoMutation:
    """Alignment must not mutate the original branch or window."""

    def test_originals_unchanged(self) -> None:
        branch = _make_branch(
            decision_ts=2.0,
            positions=[
                {"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 2.0},
            ],
        )
        window = _make_window(
            decision_ts=1.0,
            outcome_positions=[
                [{"player_id": "P1", "x": 5.0, "y": 15.0, "timestamp": 1.0}]
            ],
        )

        # Snapshot originals
        orig_branch_ts = branch["positions"][0]["timestamp"]
        orig_branch_x = branch["positions"][0]["x"]
        orig_branch_y = branch["positions"][0]["y"]

        align(branch, window)

        assert branch["positions"][0]["timestamp"] == orig_branch_ts
        assert branch["positions"][0]["x"] == orig_branch_x
        assert branch["positions"][0]["y"] == orig_branch_y


class TestAlignEdgeCases:
    """Edge cases: empty positions, multiple players."""

    def test_empty_positions(self) -> None:
        branch = _make_branch(decision_ts=1.0, positions=[])
        window = _make_window(decision_ts=1.0, outcome_positions=[[]])

        result = align(branch, window)

        assert result.temporal_offset == pytest.approx(0.0)
        assert result.spatial_offset == pytest.approx(0.0)
        assert result.residual_magnitude == pytest.approx(0.0)
        assert result.aligned_branch["positions"] == []

    def test_multiple_players_averaged(self) -> None:
        # Two branch players at (10, 20) and (20, 30) → avg (15, 25)
        # Two window players at (5, 10) and (15, 20) → avg (10, 15)
        branch = _make_branch(
            decision_ts=1.0,
            positions=[
                {"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 1.0},
                {"player_id": "P2", "x": 20.0, "y": 30.0, "timestamp": 1.0},
            ],
        )
        window = _make_window(
            decision_ts=1.0,
            outcome_positions=[
                [
                    {"player_id": "P1", "x": 5.0, "y": 10.0, "timestamp": 1.0},
                    {"player_id": "P2", "x": 15.0, "y": 20.0, "timestamp": 1.0},
                ]
            ],
        )

        result = align(branch, window)

        # dx = 15 - 10 = 5, dy = 25 - 15 = 10
        expected_spatial = math.sqrt(5.0**2 + 10.0**2)
        assert result.spatial_offset == pytest.approx(expected_spatial)
        # P1 shifted: (10-5, 20-10) = (5, 10)
        assert result.aligned_branch["positions"][0]["x"] == pytest.approx(5.0)
        assert result.aligned_branch["positions"][0]["y"] == pytest.approx(10.0)
        # P2 shifted: (20-5, 30-10) = (15, 20)
        assert result.aligned_branch["positions"][1]["x"] == pytest.approx(15.0)
        assert result.aligned_branch["positions"][1]["y"] == pytest.approx(20.0)
