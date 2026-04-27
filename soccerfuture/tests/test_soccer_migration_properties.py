"""Property-based tests for soccer domain migration.

Feature: soccer-domain-migration
Properties 3–9: Gating field bounds, speed thresholds, generated events,
generated positions, tactical zones, ball progression, turnover detection.

Validates: Requirements 1.4, 4.4, 5.4, 5.5, 6.1, 7.1, 7.2, 7.4, 10.2,
10.3, 10.4
"""

from __future__ import annotations

import math

from hypothesis import given, settings, strategies as st

from src.generation.branch_generator import generate_branches
from src.scoring.decision_value import score_decision_value
from src.scoring.gating import run_gates
from src.scoring.physical_plausibility import score_physical_plausibility
from src.scoring.tactical_consistency import _ROLE_ZONES, _check_role_violation
from src.utils.constants import (
    FIELD_LENGTH,
    FIELD_WIDTH,
    MAX_HUMAN_SPRINT_SPEED,
    SPEED_SAFETY_FACTOR,
)
from tests.strategies import (
    out_of_bounds_branch_strategy,
    play_state_strategy,
    valid_positions_strategy,
)


# ---------------------------------------------------------------------------
# Property 3: Gating validates soccer field bounds without end zones
# ---------------------------------------------------------------------------


class TestGatingSoccerFieldBounds:
    """Feature: soccer-domain-migration, Property 3: Gating validates soccer field bounds without end zones

    **Validates: Requirements 1.4, 5.5**
    """

    @given(positions=valid_positions_strategy())
    @settings(max_examples=100)
    def test_valid_positions_pass_field_bounds_gate(
        self, positions: list[dict]
    ) -> None:
        """For any branch where all positions have x in [0, 68] and y in [0, 105],
        the field bounds gate shall pass."""
        branch = {"positions": positions}
        result = run_gates(branch)
        assert result.flags["field_bounds"] is True, (
            f"Valid positions should pass field_bounds gate, got explanations: "
            f"{result.explanations}"
        )

    @given(branch=out_of_bounds_branch_strategy())
    @settings(max_examples=100)
    def test_out_of_bounds_positions_fail_field_bounds_gate(
        self, branch: dict
    ) -> None:
        """For any branch with at least one position outside x in [0, 68] or
        y in [0, 105], the field bounds gate shall fail. No end zones."""
        result = run_gates(branch)
        assert result.flags["field_bounds"] is False, (
            "Out-of-bounds positions should fail field_bounds gate"
        )
        assert len(result.explanations) > 0, (
            "Explanations should be non-empty for field bounds failure"
        )


# ---------------------------------------------------------------------------
# Property 4: Gating and plausibility use meters-per-second speed thresholds
# ---------------------------------------------------------------------------

# Strategy: two consecutive positions for the same player with speed > 10 m/s
_valid_x = st.floats(
    min_value=5.0, max_value=FIELD_WIDTH - 5.0,
    allow_nan=False, allow_infinity=False,
)
_valid_y = st.floats(
    min_value=5.0, max_value=FIELD_LENGTH - 5.0,
    allow_nan=False, allow_infinity=False,
)


class TestSpeedThresholdsMetersPerSecond:
    """Feature: soccer-domain-migration, Property 4: Gating and plausibility use meters-per-second speed thresholds

    **Validates: Requirements 5.4, 5.5**
    """

    @given(
        x=_valid_x,
        y=_valid_y,
        dt=st.floats(min_value=0.1, max_value=0.4, allow_nan=False, allow_infinity=False),
        speed_factor=st.floats(min_value=1.05, max_value=3.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_speed_exceeding_10_mps_fails_speed_gate_no_contact(
        self, x: float, y: float, dt: float, speed_factor: float,
    ) -> None:
        """Speeds > 10.0 m/s without contact context shall fail the speed gate."""
        speed = MAX_HUMAN_SPRINT_SPEED * speed_factor
        dy = speed * dt  # move purely in y direction
        y2 = y + dy
        # Ensure y2 stays in a reasonable range (may go out of field bounds,
        # but we're testing speed gate specifically)
        branch = {
            "positions": [
                {"player_id": "P1", "x": x, "y": y, "timestamp": 0.0},
                {"player_id": "P1", "x": x, "y": y2, "timestamp": dt},
            ],
        }
        result = run_gates(branch)
        assert result.flags["max_speed"] is False, (
            f"Speed {speed:.2f} m/s should fail max_speed gate (threshold={MAX_HUMAN_SPRINT_SPEED})"
        )

    @given(
        x=_valid_x,
        y=_valid_y,
        dt=st.floats(min_value=0.1, max_value=0.4, allow_nan=False, allow_infinity=False),
        speed_factor=st.floats(min_value=1.05, max_value=3.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_plausibility_assigns_zero_speed_score_above_10_mps(
        self, x: float, y: float, dt: float, speed_factor: float,
    ) -> None:
        """Plausibility shall assign speed_score 0.0 for players exceeding 10.0 m/s."""
        speed = MAX_HUMAN_SPRINT_SPEED * speed_factor
        dy = speed * dt
        branch = {
            "positions": [
                {"player_id": "P1", "x": x, "y": y, "timestamp": 0.0},
                {"player_id": "P1", "x": x, "y": y + dy, "timestamp": dt},
            ],
        }
        result = score_physical_plausibility(branch)
        assert result.speed_score == 0.0, (
            f"speed_score should be 0.0 for speed {speed:.2f} m/s > {MAX_HUMAN_SPRINT_SPEED} m/s, "
            f"got {result.speed_score}"
        )

    @given(
        x=_valid_x,
        y=_valid_y,
        dt=st.floats(min_value=0.1, max_value=0.4, allow_nan=False, allow_infinity=False),
        speed_factor=st.floats(min_value=1.05, max_value=2.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_speed_exceeding_15_mps_fails_even_with_contact(
        self, x: float, y: float, dt: float, speed_factor: float,
    ) -> None:
        """Speeds > 15.0 m/s with contact context shall still fail the speed gate."""
        from src.utils.constants import CONTACT_SPEED_THRESHOLD

        speed = CONTACT_SPEED_THRESHOLD * speed_factor
        dy = speed * dt
        t_mid = dt / 2.0
        branch = {
            "positions": [
                {"player_id": "P1", "x": x, "y": y, "timestamp": 0.0},
                {"player_id": "P1", "x": x, "y": y + dy, "timestamp": dt},
            ],
            "events": [
                {"event_type": "tackle", "timestamp": t_mid, "player_id": "P1", "metadata": {}},
            ],
        }
        result = run_gates(branch)
        assert result.flags["max_speed"] is False, (
            f"Speed {speed:.2f} m/s should fail max_speed gate even with contact "
            f"(contact threshold={CONTACT_SPEED_THRESHOLD})"
        )


# ---------------------------------------------------------------------------
# Property 5: Generated branches contain only soccer events
# ---------------------------------------------------------------------------

_SOCCER_EVENTS = frozenset({
    "pass", "shot", "tackle", "interception", "dribble", "cross", "header",
    "goal", "corner_kick", "free_kick", "throw_in", "goal_kick", "offside",
    "foul", "save", "clearance", "dispossession", "kick_off",
})


class TestGeneratedBranchesContainOnlySoccerEvents:
    """Feature: soccer-domain-migration, Property 5: Generated branches contain only soccer events

    **Validates: Requirements 4.4, 10.2**
    """

    @given(ps=play_state_strategy())
    @settings(max_examples=100)
    def test_all_events_are_soccer_events(self, ps) -> None:
        """For any PlayState with valid soccer roles, all events in branches
        produced by generate_branches shall have event_type from the soccer
        event set."""
        result = generate_branches(ps, n=10, seed=42)
        for branch in result.branches:
            for event in branch.get("events", []):
                etype = event.get("event_type", "")
                assert etype in _SOCCER_EVENTS, (
                    f"Event type '{etype}' is not in the soccer event set. "
                    f"Allowed: {sorted(_SOCCER_EVENTS)}"
                )


# ---------------------------------------------------------------------------
# Property 6: Generated branches respect soccer field bounds and speed limits
# ---------------------------------------------------------------------------

_MAX_GENERATED_SPEED = MAX_HUMAN_SPRINT_SPEED * SPEED_SAFETY_FACTOR  # 8.5 m/s


class TestGeneratedBranchesRespectBoundsAndSpeed:
    """Feature: soccer-domain-migration, Property 6: Generated branches respect soccer field bounds and speed limits

    **Validates: Requirements 10.3, 10.4**
    """

    @given(ps=play_state_strategy())
    @settings(max_examples=100)
    def test_all_positions_within_field_bounds(self, ps) -> None:
        """For any PlayState, all positions in generated branches shall have
        x in [0, 68] and y in [0, 105]."""
        result = generate_branches(ps, n=10, seed=42)
        for branch in result.branches:
            for pos in branch.get("positions", []):
                x = pos.get("x", 0.0)
                y = pos.get("y", 0.0)
                assert 0.0 <= x <= FIELD_WIDTH, (
                    f"Position x={x} outside [0, {FIELD_WIDTH}]"
                )
                assert 0.0 <= y <= FIELD_LENGTH, (
                    f"Position y={y} outside [0, {FIELD_LENGTH}]"
                )

    @given(ps=play_state_strategy())
    @settings(max_examples=100)
    def test_all_speeds_within_safety_limit(self, ps) -> None:
        """For any PlayState, no player shall exceed 8.5 m/s between
        consecutive snapshots in generated branches."""
        result = generate_branches(ps, n=10, seed=42)
        for branch in result.branches:
            positions = branch.get("positions", [])
            # Group by player_id
            by_player: dict[str, list[dict]] = {}
            for pos in positions:
                pid = pos.get("player_id", "")
                by_player.setdefault(pid, []).append(pos)

            for pid, plist in by_player.items():
                sorted_pos = sorted(plist, key=lambda p: p.get("timestamp", 0.0))
                for i in range(1, len(sorted_pos)):
                    prev = sorted_pos[i - 1]
                    curr = sorted_pos[i]
                    dt = curr["timestamp"] - prev["timestamp"]
                    if dt <= 0:
                        continue
                    dx = curr["x"] - prev["x"]
                    dy = curr["y"] - prev["y"]
                    speed = math.sqrt(dx * dx + dy * dy) / dt
                    assert speed <= _MAX_GENERATED_SPEED + 0.01, (
                        f"Player {pid} speed {speed:.2f} m/s exceeds "
                        f"safety limit {_MAX_GENERATED_SPEED} m/s"
                    )


# ---------------------------------------------------------------------------
# Property 7: Tactical zone checks are consistent for soccer positions
# ---------------------------------------------------------------------------

_SOCCER_ROLES = list(_ROLE_ZONES.keys())


class TestTacticalZoneConsistency:
    """Feature: soccer-domain-migration, Property 7: Tactical zone checks are consistent for soccer positions

    **Validates: Requirements 6.1**
    """

    @given(
        role=st.sampled_from(_SOCCER_ROLES),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_positions_within_zone_not_flagged(self, role: str, data) -> None:
        """For any soccer role, positions within the defined zone shall not
        be flagged as violations."""
        zone = _ROLE_ZONES[role]
        x = data.draw(st.floats(
            min_value=zone["x_min"], max_value=zone["x_max"],
            allow_nan=False, allow_infinity=False,
        ))
        y = data.draw(st.floats(
            min_value=zone["y_min"], max_value=zone["y_max"],
            allow_nan=False, allow_infinity=False,
        ))
        violation = _check_role_violation(role, x, y)
        assert violation is False, (
            f"Position ({x}, {y}) within zone {zone} for role {role} "
            f"should NOT be flagged as a violation"
        )

    @given(
        role=st.sampled_from(_SOCCER_ROLES),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_positions_outside_zone_flagged(self, role: str, data) -> None:
        """For any soccer role, positions outside the defined zone shall be
        flagged as violations."""
        zone = _ROLE_ZONES[role]
        # Pick one of four violation directions
        direction = data.draw(st.sampled_from(["x_low", "x_high", "y_low", "y_high"]))

        if direction == "x_low" and zone["x_min"] > 0:
            x = data.draw(st.floats(
                min_value=-10.0, max_value=zone["x_min"] - 0.01,
                allow_nan=False, allow_infinity=False,
            ))
            y = data.draw(st.floats(
                min_value=zone["y_min"], max_value=zone["y_max"],
                allow_nan=False, allow_infinity=False,
            ))
        elif direction == "x_high" and zone["x_max"] < FIELD_WIDTH:
            x = data.draw(st.floats(
                min_value=zone["x_max"] + 0.01, max_value=FIELD_WIDTH + 10.0,
                allow_nan=False, allow_infinity=False,
            ))
            y = data.draw(st.floats(
                min_value=zone["y_min"], max_value=zone["y_max"],
                allow_nan=False, allow_infinity=False,
            ))
        elif direction == "y_low" and zone["y_min"] > 0:
            x = data.draw(st.floats(
                min_value=zone["x_min"], max_value=zone["x_max"],
                allow_nan=False, allow_infinity=False,
            ))
            y = data.draw(st.floats(
                min_value=-10.0, max_value=zone["y_min"] - 0.01,
                allow_nan=False, allow_infinity=False,
            ))
        elif direction == "y_high" and zone["y_max"] < FIELD_LENGTH:
            x = data.draw(st.floats(
                min_value=zone["x_min"], max_value=zone["x_max"],
                allow_nan=False, allow_infinity=False,
            ))
            y = data.draw(st.floats(
                min_value=zone["y_max"] + 0.01, max_value=FIELD_LENGTH + 10.0,
                allow_nan=False, allow_infinity=False,
            ))
        else:
            # This direction doesn't have room for violation (e.g. x_min=0
            # for x_low, or y_max=105 for y_high). Skip via assume.
            from hypothesis import assume
            assume(False)
            return

        violation = _check_role_violation(role, x, y)
        assert violation is True, (
            f"Position ({x}, {y}) outside zone {zone} for role {role} "
            f"should be flagged as a violation"
        )


# ---------------------------------------------------------------------------
# Property 8: Ball progression measures forward progress in meters
# ---------------------------------------------------------------------------


class TestBallProgressionInMeters:
    """Feature: soccer-domain-migration, Property 8: Ball progression measures forward progress in meters

    **Validates: Requirements 7.1, 7.4**
    """

    @given(
        forward_dy=st.floats(
            min_value=10.0, max_value=50.0,
            allow_nan=False, allow_infinity=False,
        ),
    )
    @settings(max_examples=100)
    def test_forward_progress_yields_ball_progression_above_half(
        self, forward_dy: float,
    ) -> None:
        """A branch with greater forward progress (toward y=105) than the
        window shall have ball_progression > 0.5."""
        # Branch: player moves forward significantly
        branch = {
            "positions": [
                {"player_id": "P1", "x": 34.0, "y": 30.0, "timestamp": 0.0},
                {"player_id": "P1", "x": 34.0, "y": 30.0 + forward_dy, "timestamp": 1.0},
            ],
            "events": [],
        }
        # Window: no forward progress
        window = {
            "outcomes": [
                {"yard_gain": 0.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert result.ball_progression > 0.5, (
            f"Branch with {forward_dy:.1f}m forward progress should have "
            f"ball_progression > 0.5, got {result.ball_progression}"
        )

    @given(
        forward_dy=st.floats(
            min_value=1.0, max_value=50.0,
            allow_nan=False, allow_infinity=False,
        ),
    )
    @settings(max_examples=100)
    def test_ball_progression_normalized_by_field_length(
        self, forward_dy: float,
    ) -> None:
        """ball_progression shall be normalized by FIELD_LENGTH (105.0) and
        clamped to [0, 1]."""
        branch = {
            "positions": [
                {"player_id": "P1", "x": 34.0, "y": 20.0, "timestamp": 0.0},
                {"player_id": "P1", "x": 34.0, "y": 20.0 + forward_dy, "timestamp": 1.0},
            ],
            "events": [],
        }
        window = {
            "outcomes": [
                {"yard_gain": 0.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert 0.0 <= result.ball_progression <= 1.0, (
            f"ball_progression should be in [0, 1], got {result.ball_progression}"
        )


# ---------------------------------------------------------------------------
# Property 9: Turnover detection uses soccer events
# ---------------------------------------------------------------------------

_SOCCER_TURNOVER_EVENTS = ["interception", "dispossession"]


class TestTurnoverDetectionSoccerEvents:
    """Feature: soccer-domain-migration, Property 9: Turnover detection uses soccer events

    **Validates: Requirements 7.2**
    """

    @given(
        event_type=st.sampled_from(_SOCCER_TURNOVER_EVENTS),
        n_events=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100)
    def test_turnover_events_elevate_turnover_risk(
        self, event_type: str, n_events: int,
    ) -> None:
        """Branches with interception or dispossession events shall have
        elevated turnover risk (turnover_risk_delta < 0.5)."""
        branch = {
            "positions": [
                {"player_id": "P1", "x": 34.0, "y": 52.0, "timestamp": 0.0},
                {"player_id": "P1", "x": 34.0, "y": 53.0, "timestamp": 1.0},
            ],
            "events": [
                {
                    "event_type": event_type,
                    "timestamp": 0.3 + i * 0.1,
                    "player_id": "P1",
                    "metadata": {},
                }
                for i in range(n_events)
            ],
        }
        # Window with no turnovers
        window = {
            "outcomes": [
                {"yard_gain": 0.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert result.turnover_risk_delta < 0.5, (
            f"Branch with {n_events} '{event_type}' events should have "
            f"turnover_risk_delta < 0.5, got {result.turnover_risk_delta}"
        )

    @given(
        y_start=st.floats(
            min_value=10.0, max_value=90.0,
            allow_nan=False, allow_infinity=False,
        ),
    )
    @settings(max_examples=100)
    def test_no_turnover_events_yields_high_turnover_risk_delta(
        self, y_start: float,
    ) -> None:
        """Branches without turnover events shall have turnover_risk_delta >= 0.5."""
        branch = {
            "positions": [
                {"player_id": "P1", "x": 34.0, "y": y_start, "timestamp": 0.0},
                {"player_id": "P1", "x": 34.0, "y": y_start + 2.0, "timestamp": 1.0},
            ],
            "events": [
                {"event_type": "pass", "timestamp": 0.3, "player_id": "P1", "metadata": {}},
            ],
        }
        # Window with no turnovers
        window = {
            "outcomes": [
                {"yard_gain": 0.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert result.turnover_risk_delta >= 0.5, (
            f"Branch without turnover events should have "
            f"turnover_risk_delta >= 0.5, got {result.turnover_risk_delta}"
        )
