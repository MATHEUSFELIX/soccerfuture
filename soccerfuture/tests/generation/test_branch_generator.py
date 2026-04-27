"""Unit tests for Branch Generator.

Tests core generation behavior: count, determinism, sequential IDs,
required fields, timestamp ordering, speed limits, ContinuationWindow
structure, and input validation.

Soccer events generated: pass, dribble, shot, kick_off.
Field bounds: x ∈ [0, 68], y ∈ [0, 105] (no end zones).

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.5
"""

import math
from collections import defaultdict

import pytest

from src.generation.branch_generator import generate_branches
from src.models.branch import PlayerPosition
from src.models.play_state import PlayState
from src.utils.constants import MAX_HUMAN_SPRINT_SPEED


def _make_play_state() -> PlayState:
    """Build a test PlayState with 5 players and assigned soccer roles."""
    positions = [
        PlayerPosition(player_id="P1", x=34.0, y=50.0, timestamp=1.0),
        PlayerPosition(player_id="P2", x=20.0, y=52.0, timestamp=1.0),
        PlayerPosition(player_id="P3", x=40.0, y=48.0, timestamp=1.0),
        PlayerPosition(player_id="P4", x=15.0, y=45.0, timestamp=1.0),
        PlayerPosition(player_id="P5", x=10.0, y=80.0, timestamp=1.0),
    ]
    return PlayState(
        match_time=45.0,
        possession_team="home",
        ball_position={"x": 34.0, "y": 50.0},
        game_phase="open_play",
        score_differential=0,
        game_clock=2700.0,
        player_positions=positions,
        decision_point_timestamp=1.0,
        player_roles={
            "P1": "CM",
            "P2": "ST",
            "P3": "CB",
            "P4": "GK",
            "P5": "LW",
        },
        metadata={"formation": "4-3-3"},
    )


# ---- 1. Exactly N branches generated ----


class TestExactlyNBranches:
    """Verify generate_branches returns exactly N branches."""

    @pytest.mark.parametrize("n", [10, 20, 30])
    def test_generates_exactly_n_branches(self, n: int) -> None:
        ps = _make_play_state()
        result = generate_branches(ps, n=n, seed=42)
        assert len(result.branches) == n


# ---- 2. Deterministic with same seed ----


class TestDeterminism:
    """Same PlayState + seed must produce identical branches."""

    def test_same_seed_produces_identical_branches(self) -> None:
        ps = _make_play_state()
        result_a = generate_branches(ps, n=15, seed=99)
        result_b = generate_branches(ps, n=15, seed=99)
        assert result_a.branches == result_b.branches
        assert result_a.continuation_window == result_b.continuation_window


# ---- 3. Different seeds produce different branches ----


class TestDifferentSeeds:
    """Different seeds must produce at least one differing branch."""

    def test_different_seeds_differ(self) -> None:
        ps = _make_play_state()
        result_a = generate_branches(ps, n=15, seed=1)
        result_b = generate_branches(ps, n=15, seed=2)
        assert result_a.branches != result_b.branches


# ---- 4. Sequential branch_ids ----


class TestSequentialBranchIds:
    """Branch IDs must follow 'gen-001', 'gen-002', ... pattern."""

    def test_branch_ids_are_sequential(self) -> None:
        ps = _make_play_state()
        result = generate_branches(ps, n=20, seed=42)
        for i, branch in enumerate(result.branches):
            expected_id = f"gen-{i + 1:03d}"
            assert branch["branch_id"] == expected_id


# ---- 5. Required fields present ----


class TestRequiredFields:
    """Every branch must have all required top-level keys."""

    _REQUIRED_KEYS = {
        "branch_id",
        "decision_point_timestamp",
        "positions",
        "events",
        "player_roles",
        "metadata",
    }

    def test_all_branches_have_required_fields(self) -> None:
        ps = _make_play_state()
        result = generate_branches(ps, n=10, seed=42)
        for branch in result.branches:
            assert self._REQUIRED_KEYS.issubset(branch.keys()), (
                f"Branch {branch.get('branch_id')} missing keys: "
                f"{self._REQUIRED_KEYS - set(branch.keys())}"
            )


# ---- 6. Timestamps ordered per player ----


class TestTimestampOrdering:
    """For each player within a branch, timestamps must be strictly increasing."""

    def test_timestamps_ordered_per_player(self) -> None:
        ps = _make_play_state()
        result = generate_branches(ps, n=10, seed=42)
        for branch in result.branches:
            by_player: dict[str, list[float]] = defaultdict(list)
            for pos in branch["positions"]:
                by_player[pos["player_id"]].append(pos["timestamp"])
            for pid, timestamps in by_player.items():
                for a, b in zip(timestamps, timestamps[1:]):
                    assert a < b, (
                        f"Branch {branch['branch_id']}, player {pid}: "
                        f"timestamp {a} not < {b}"
                    )


# ---- 7. Speeds within limits for majority (≥70%) ----


def _compute_branch_speeds(branch: dict) -> list[float]:
    """Compute speeds between consecutive positions for each player."""
    by_player: dict[str, list[dict]] = defaultdict(list)
    for pos in branch["positions"]:
        by_player[pos["player_id"]].append(pos)

    speeds: list[float] = []
    for pid, positions in by_player.items():
        positions.sort(key=lambda p: p["timestamp"])
        for a, b in zip(positions, positions[1:]):
            dt = b["timestamp"] - a["timestamp"]
            if dt > 0:
                dist = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
                speeds.append(dist / dt)
    return speeds


class TestSpeedLimits:
    """At least 70% of branches must have all speeds ≤ MAX_HUMAN_SPRINT_SPEED."""

    def test_majority_branches_within_speed_limits(self) -> None:
        ps = _make_play_state()
        result = generate_branches(ps, n=20, seed=42)
        compliant = 0
        for branch in result.branches:
            speeds = _compute_branch_speeds(branch)
            if speeds and all(s <= MAX_HUMAN_SPRINT_SPEED for s in speeds):
                compliant += 1
        ratio = compliant / len(result.branches)
        assert ratio >= 0.70, (
            f"Only {compliant}/{len(result.branches)} branches "
            f"({ratio:.0%}) have compliant speeds"
        )


# ---- 8. ContinuationWindow well-formed ----


class TestContinuationWindow:
    """Synthesized ContinuationWindow must have required structure."""

    def test_has_window_id(self) -> None:
        ps = _make_play_state()
        result = generate_branches(ps, n=10, seed=42)
        cw = result.continuation_window
        assert "window_id" in cw
        assert isinstance(cw["window_id"], str)

    def test_has_decision_point_timestamp(self) -> None:
        ps = _make_play_state()
        result = generate_branches(ps, n=10, seed=42)
        cw = result.continuation_window
        assert cw["decision_point_timestamp"] == ps.decision_point_timestamp

    def test_outcomes_well_formed(self) -> None:
        ps = _make_play_state()
        result = generate_branches(ps, n=10, seed=42)
        cw = result.continuation_window
        assert "outcomes" in cw
        assert len(cw["outcomes"]) >= 1
        outcome = cw["outcomes"][0]
        assert "positions" in outcome
        assert "meter_gain" in outcome
        assert "turnover" in outcome
        assert "scoring_play" in outcome


# ---- 9. ValueError for N outside [10, 30] ----


class TestInputValidation:
    """generate_branches must reject N outside [10, 30]."""

    def test_raises_for_n_too_low(self) -> None:
        ps = _make_play_state()
        with pytest.raises(ValueError, match="10 and 30"):
            generate_branches(ps, n=5, seed=42)

    def test_raises_for_n_too_high(self) -> None:
        ps = _make_play_state()
        with pytest.raises(ValueError, match="10 and 30"):
            generate_branches(ps, n=35, seed=42)
