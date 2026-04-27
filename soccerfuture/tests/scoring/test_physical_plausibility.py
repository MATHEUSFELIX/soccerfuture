"""Unit tests for the physical plausibility scoring module.

Tests cover:
  - Stationary players score 1.0 on all dimensions
  - Moderate movement scores between 0 and 1
  - Teleportation-like movement scores 0.0
  - Empty positions return perfect score
  - Multiple players are averaged

Requirements: 5.1, 5.3, 5.4
"""

from __future__ import annotations

import pytest

from src.scoring.physical_plausibility import (
    PhysicalPlausibilityResult,
    score_physical_plausibility,
)
from src.utils.constants import MAX_HUMAN_SPRINT_SPEED


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_aligned_branch(positions: list[dict]) -> dict:
    """Build a minimal aligned branch dict with the given positions."""
    return {"positions": positions}


def _stationary_positions(
    player_id: str = "P1",
    x: float = 10.0,
    y: float = 20.0,
    start_ts: float = 0.0,
    frames: int = 5,
    dt: float = 0.1,
) -> list[dict]:
    """Generate positions for a player that does not move."""
    return [
        {"player_id": player_id, "x": x, "y": y, "timestamp": start_ts + i * dt}
        for i in range(frames)
    ]


def _linear_movement_positions(
    player_id: str = "P1",
    speed: float = 5.0,
    start_ts: float = 0.0,
    frames: int = 5,
    dt: float = 0.1,
) -> list[dict]:
    """Generate positions for a player moving at constant speed along x-axis."""
    return [
        {
            "player_id": player_id,
            "x": speed * i * dt,
            "y": 20.0,
            "timestamp": start_ts + i * dt,
        }
        for i in range(frames)
    ]


# ---------------------------------------------------------------------------
# Tests — Stationary players (Requirement 5.1, 5.3)
# ---------------------------------------------------------------------------


class TestStationaryPlayers:
    """Stationary players should score 1.0 on all dimensions."""

    def test_single_stationary_player(self) -> None:
        branch = _make_aligned_branch(_stationary_positions())
        result = score_physical_plausibility(branch)

        assert isinstance(result, PhysicalPlausibilityResult)
        assert result.plausibility_score == pytest.approx(1.0)
        assert result.speed_score == pytest.approx(1.0)
        assert result.acceleration_score == pytest.approx(1.0)
        assert result.deceleration_score == pytest.approx(1.0)

    def test_multiple_stationary_players(self) -> None:
        positions = (
            _stationary_positions("P1", x=5.0, y=10.0)
            + _stationary_positions("P2", x=20.0, y=30.0)
        )
        branch = _make_aligned_branch(positions)
        result = score_physical_plausibility(branch)

        assert result.plausibility_score == pytest.approx(1.0)
        assert result.speed_score == pytest.approx(1.0)

    def test_single_frame_player(self) -> None:
        """A player with only one position frame is effectively stationary."""
        positions = [{"player_id": "P1", "x": 10.0, "y": 20.0, "timestamp": 0.0}]
        branch = _make_aligned_branch(positions)
        result = score_physical_plausibility(branch)

        assert result.plausibility_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Tests — Moderate movement (Requirement 5.1, 5.3)
# ---------------------------------------------------------------------------


class TestModerateMovement:
    """Moderate, physically plausible movement should score between 0 and 1."""

    def test_slow_walk(self) -> None:
        """Walking speed (~2 m/s) should score high but below 1.0."""
        positions = _linear_movement_positions(speed=2.0, frames=5, dt=0.5)
        branch = _make_aligned_branch(positions)
        result = score_physical_plausibility(branch)

        assert 0.0 < result.plausibility_score < 1.0
        assert 0.0 < result.speed_score < 1.0
        # Constant speed → no acceleration/deceleration
        assert result.acceleration_score == pytest.approx(1.0)
        assert result.deceleration_score == pytest.approx(1.0)

    def test_moderate_jog(self) -> None:
        """Jogging speed (~6 m/s) should score in the middle range."""
        positions = _linear_movement_positions(speed=6.0, frames=5, dt=0.5)
        branch = _make_aligned_branch(positions)
        result = score_physical_plausibility(branch)

        assert 0.0 < result.plausibility_score < 1.0
        assert 0.0 < result.speed_score < 1.0
        # Quadratic curve: (1 - 6/10)^0.6 ≈ 0.55
        assert 0.4 < result.speed_score < 0.7

    def test_near_sprint(self) -> None:
        """Near-max sprint (~9.5 m/s) should score low but above 0."""
        positions = _linear_movement_positions(speed=9.5, frames=5, dt=0.5)
        branch = _make_aligned_branch(positions)
        result = score_physical_plausibility(branch)

        # (1 - 9.5/10)^0.6 ≈ 0.13 — low but non-zero
        assert 0.0 < result.speed_score < 0.3
        assert result.plausibility_score > 0.0


# ---------------------------------------------------------------------------
# Tests — Teleportation (Requirement 5.4)
# ---------------------------------------------------------------------------


class TestTeleportation:
    """Teleportation-like movement should score 0.0."""

    def test_instant_teleport(self) -> None:
        """A player jumping 100 meters in 0.1s far exceeds max sprint speed."""
        positions = [
            {"player_id": "P1", "x": 0.0, "y": 0.0, "timestamp": 0.0},
            {"player_id": "P1", "x": 100.0, "y": 0.0, "timestamp": 0.1},
        ]
        branch = _make_aligned_branch(positions)
        result = score_physical_plausibility(branch)

        # Speed = 100 / 0.1 = 1000 m/s >> MAX_HUMAN_SPRINT_SPEED (10.0 m/s)
        assert result.speed_score == pytest.approx(0.0)
        # With only 2 frames, no acceleration data exists, so accel/decel = 1.0
        # plausibility = (0.0 + 1.0 + 1.0) / 3 ≈ 0.667
        assert result.plausibility_score < 1.0

    def test_teleport_among_normal_players(self) -> None:
        """One teleporting player among normal players drags the average down."""
        normal = _linear_movement_positions("P1", speed=3.0, frames=5, dt=0.5)
        teleport = [
            {"player_id": "P2", "x": 0.0, "y": 0.0, "timestamp": 0.0},
            {"player_id": "P2", "x": 200.0, "y": 0.0, "timestamp": 0.1},
        ]
        branch = _make_aligned_branch(normal + teleport)
        result = score_physical_plausibility(branch)

        # P2 teleports → speed_score for P2 = 0.0
        # P1 has speed 3.0 m/s → score = (1 - 3/10)^0.6 ≈ 0.78
        # Average speed_score = (P1_score + 0.0) / 2 ≈ 0.39
        assert result.speed_score < 1.0
        assert result.speed_score > 0.0
        assert result.speed_score < 0.5  # dragged down by teleporter

    def test_barely_exceeds_max_speed(self) -> None:
        """Speed just above MAX_HUMAN_SPRINT_SPEED triggers teleportation flag."""
        speed = MAX_HUMAN_SPRINT_SPEED + 0.1
        positions = _linear_movement_positions(speed=speed, frames=3, dt=1.0)
        branch = _make_aligned_branch(positions)
        result = score_physical_plausibility(branch)

        assert result.speed_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests — Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: empty positions, no positions key."""

    def test_empty_positions(self) -> None:
        branch = _make_aligned_branch([])
        result = score_physical_plausibility(branch)

        assert result.plausibility_score == pytest.approx(1.0)
        assert result.speed_score == pytest.approx(1.0)
        assert result.acceleration_score == pytest.approx(1.0)
        assert result.deceleration_score == pytest.approx(1.0)

    def test_no_positions_key(self) -> None:
        """Branch without a positions key should still return a valid result."""
        result = score_physical_plausibility({})

        assert result.plausibility_score == pytest.approx(1.0)

    def test_all_scores_in_unit_range(self) -> None:
        """All returned scores must be in [0.0, 1.0]."""
        positions = _linear_movement_positions(speed=8.0, frames=10, dt=0.2)
        branch = _make_aligned_branch(positions)
        result = score_physical_plausibility(branch)

        for field in (
            result.plausibility_score,
            result.speed_score,
            result.acceleration_score,
            result.deceleration_score,
        ):
            assert 0.0 <= field <= 1.0
