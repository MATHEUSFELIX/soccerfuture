"""Unit tests for the gating module.

Tests cover requirements 1.4, 5.5, 11.5: binary pass/fail gating checks for
soccer field bounds (x: 0–68, y: 0–105), max speed in m/s, and temporal
continuity.
"""

import pytest

from src.scoring.gating import run_gates


def _make_branch(positions: list[dict], events: list[dict] | None = None) -> dict:
    """Helper to build a minimal branch dict with the given positions and optional events."""
    branch: dict = {"positions": positions}
    if events is not None:
        branch["events"] = events
    return branch


# ── Realistic branch passes all gates ────────────────────────────────────


class TestRealisticBranchPassesAllGates:
    """Requirement 1.4, 5.5: a physically plausible soccer branch passes."""

    def test_realistic_branch_passes(self):
        positions = [
            {"player_id": "CM1", "x": 34.0, "y": 52.0, "timestamp": 1.0},
            {"player_id": "CM1", "x": 34.0, "y": 52.8, "timestamp": 1.1},
            {"player_id": "CM1", "x": 33.9, "y": 53.5, "timestamp": 1.2},
            {"player_id": "LW1", "x": 10.0, "y": 70.0, "timestamp": 1.0},
            {"player_id": "LW1", "x": 10.2, "y": 70.9, "timestamp": 1.1},
            {"player_id": "LW1", "x": 10.5, "y": 71.8, "timestamp": 1.2},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is True
        assert result.flags["field_bounds"] is True
        assert result.flags["max_speed"] is True
        assert result.flags["temporal_continuity"] is True
        assert result.explanations == []


# ── Out-of-bounds branch fails field_bounds gate ─────────────────────────


class TestOutOfBoundsFailsFieldBounds:
    """Requirement 1.4: positions outside soccer field boundaries are rejected.

    Soccer field bounds: x ∈ [0, 68], y ∈ [0, 105]. No end zones.
    """

    def test_x_below_zero(self):
        positions = [
            {"player_id": "P1", "x": -1.0, "y": 50.0, "timestamp": 1.0},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["field_bounds"] is False
        assert any("x=-1.0" in e for e in result.explanations)

    def test_x_above_field_width(self):
        # FIELD_WIDTH = 68.0m; x=69.0 is out of bounds
        positions = [
            {"player_id": "P1", "x": 69.0, "y": 50.0, "timestamp": 1.0},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["field_bounds"] is False
        assert any("x=69.0" in e for e in result.explanations)

    def test_y_below_zero(self):
        # No end zones — y < 0 is out of bounds
        positions = [
            {"player_id": "P1", "x": 34.0, "y": -1.0, "timestamp": 1.0},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["field_bounds"] is False
        assert any("y=-1.0" in e for e in result.explanations)

    def test_y_above_field_length(self):
        # FIELD_LENGTH = 105.0m; y=106.0 is out of bounds
        positions = [
            {"player_id": "P1", "x": 34.0, "y": 106.0, "timestamp": 1.0},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["field_bounds"] is False
        assert any("y=106.0" in e for e in result.explanations)


# ── Teleport branch fails max_speed gate ─────────────────────────────────


class TestTeleportFailsMaxSpeed:
    """Requirement 5.5: speed exceeding MAX_HUMAN_SPRINT_SPEED (10.0 m/s) is rejected."""

    def test_teleport_detected(self):
        # LW1 moves ~63m in 0.1s → 630 m/s, far above 10 m/s
        positions = [
            {"player_id": "LW1", "x": 10.0, "y": 36.0, "timestamp": 1.0},
            {"player_id": "LW1", "x": 45.0, "y": 90.0, "timestamp": 1.1},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["max_speed"] is False
        assert any("speed" in e.lower() and "LW1" in e for e in result.explanations)

    def test_speed_just_above_threshold(self):
        # Player moves 1.1m in 0.1s → 11 m/s, just above 10 m/s
        positions = [
            {"player_id": "P1", "x": 34.0, "y": 50.0, "timestamp": 1.0},
            {"player_id": "P1", "x": 34.0, "y": 51.1, "timestamp": 1.1},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["max_speed"] is False


# ── Contact events allow elevated speed threshold ────────────────────────


class TestContactSpeedThreshold:
    """Requirement 5.5: contact events (tackle, foul, dispossession) allow
    speeds up to CONTACT_SPEED_THRESHOLD (15.0 m/s).
    """

    def test_speed_above_base_but_below_contact_threshold_passes_with_contact(self):
        # Player moves 1.2m in 0.1s → 12 m/s, above 10 m/s base but below 15 m/s contact
        positions = [
            {"player_id": "ST1", "x": 34.0, "y": 80.0, "timestamp": 1.0},
            {"player_id": "ST1", "x": 34.0, "y": 81.2, "timestamp": 1.1},
        ]
        # Tackle event near the midpoint timestamp (1.05)
        events = [
            {"event_type": "tackle", "timestamp": 1.05},
        ]
        result = run_gates(_make_branch(positions, events))

        assert result.flags["max_speed"] is True

    def test_speed_above_contact_threshold_fails_even_with_contact(self):
        # Player moves 1.6m in 0.1s → 16 m/s, above 15 m/s contact threshold
        positions = [
            {"player_id": "ST1", "x": 34.0, "y": 80.0, "timestamp": 1.0},
            {"player_id": "ST1", "x": 34.0, "y": 81.6, "timestamp": 1.1},
        ]
        events = [
            {"event_type": "foul", "timestamp": 1.05},
        ]
        result = run_gates(_make_branch(positions, events))

        assert result.passed is False
        assert result.flags["max_speed"] is False
        assert any("contact context" in e for e in result.explanations)

    def test_speed_above_base_fails_without_contact(self):
        # Player moves 1.2m in 0.1s → 12 m/s, above 10 m/s base, no contact events
        positions = [
            {"player_id": "ST1", "x": 34.0, "y": 80.0, "timestamp": 1.0},
            {"player_id": "ST1", "x": 34.0, "y": 81.2, "timestamp": 1.1},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["max_speed"] is False
        assert any("no contact context" in e for e in result.explanations)

    def test_dispossession_is_valid_contact_event(self):
        # Verify dispossession is recognized as a contact event type
        positions = [
            {"player_id": "CB1", "x": 34.0, "y": 30.0, "timestamp": 1.0},
            {"player_id": "CB1", "x": 34.0, "y": 31.2, "timestamp": 1.1},
        ]
        events = [
            {"event_type": "dispossession", "timestamp": 1.05},
        ]
        result = run_gates(_make_branch(positions, events))

        # 12 m/s is above base (10) but below contact (15), should pass
        assert result.flags["max_speed"] is True


# ── Disordered timestamps fail temporal_continuity gate ──────────────────


class TestDisorderedTimestampsFailTemporal:
    """Requirement 1.4: out-of-order or gapped timestamps are rejected."""

    def test_large_timestamp_gap(self):
        # Gap of 1.0s exceeds MAX_TIMESTAMP_GAP (0.5s)
        positions = [
            {"player_id": "P1", "x": 34.0, "y": 50.0, "timestamp": 1.0},
            {"player_id": "P1", "x": 34.0, "y": 50.5, "timestamp": 2.0},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["temporal_continuity"] is False
        assert any("gap" in e.lower() for e in result.explanations)

    def test_out_of_order_timestamps(self):
        positions = [
            {"player_id": "P1", "x": 34.0, "y": 50.0, "timestamp": 2.0},
            {"player_id": "P1", "x": 34.0, "y": 50.1, "timestamp": 1.0},
            {"player_id": "P1", "x": 34.0, "y": 50.2, "timestamp": 3.0},
        ]
        result = run_gates(_make_branch(positions))

        # After sorting, the gap from 1.0 → 3.0 is 2.0s which exceeds 0.5s
        assert result.passed is False
        assert result.flags["temporal_continuity"] is False


# ── Multiple gate failures are all reported ──────────────────────────────


class TestMultipleGateFailures:
    """Requirement 1.4, 5.5: all failing gates are reported, not just the first."""

    def test_bounds_and_speed_both_fail(self):
        positions = [
            # Out of bounds (x = -5) AND teleport speed
            {"player_id": "P1", "x": -5.0, "y": 50.0, "timestamp": 1.0},
            {"player_id": "P1", "x": 34.0, "y": 50.0, "timestamp": 1.1},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["field_bounds"] is False
        assert result.flags["max_speed"] is False
        assert len(result.explanations) >= 2

    def test_all_three_gates_fail(self):
        positions = [
            # Out of bounds (x = -5)
            {"player_id": "P1", "x": -5.0, "y": 50.0, "timestamp": 1.0},
            # Teleport + large gap (1.0s gap, huge distance)
            {"player_id": "P1", "x": 50.0, "y": 100.0, "timestamp": 2.0},
        ]
        result = run_gates(_make_branch(positions))

        assert result.passed is False
        assert result.flags["field_bounds"] is False
        assert result.flags["max_speed"] is False
        assert result.flags["temporal_continuity"] is False
        assert len(result.explanations) >= 3
