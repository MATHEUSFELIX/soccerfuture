"""Property-based tests for the tactical consistency scoring module.

Properties tested:
  - Property 12: Role violations reduce tactical consistency
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from src.scoring.tactical_consistency import (
    score_tactical_consistency,
    _ROLE_ZONES,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# ST zone: x ∈ [14, 54], y ∈ [65, 105]
# X coordinate comfortably inside the ST zone
_st_centre_x = st.floats(
    min_value=20.0,
    max_value=48.0,
    allow_nan=False,
    allow_infinity=False,
)

# Y coordinate inside the ST zone (attacking third)
_st_valid_y = st.floats(
    min_value=70.0,
    max_value=100.0,
    allow_nan=False,
    allow_infinity=False,
)

# X coordinate that violates the ST zone — outside [14, 54]
_st_violation_x = st.one_of(
    st.floats(min_value=0.0, max_value=13.99,
              allow_nan=False, allow_infinity=False),
    st.floats(min_value=54.01, max_value=68.0,
              allow_nan=False, allow_infinity=False),
)

# Ordered timestamps
_ts_start = st.floats(
    min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False
)


# ---------------------------------------------------------------------------
# Property 12: Role violations reduce tactical consistency
# ---------------------------------------------------------------------------


class TestRoleViolationsReduceConsistency:
    """Feature: soccer-domain-migration, Property 12: Role violations reduce tactical consistency

    **Validates: Requirements 6.1**
    """

    @settings(max_examples=100)
    @given(
        centre_x=_st_centre_x,
        violation_x=_st_violation_x,
        y=_st_valid_y,
        t0=_ts_start,
    )
    def test_st_zone_violation_lowers_role_consistency(
        self,
        centre_x: float,
        violation_x: float,
        y: float,
        t0: float,
    ) -> None:
        """Injecting a ST (striker) position outside the ST zone
        should produce a lower role_consistency_score than keeping the
        ST in the attacking third of the field."""
        pid = "ST1"
        t1 = t0 + 0.5

        # Baseline: ST stays in the attacking zone for both frames
        baseline_branch = {
            "positions": [
                {"player_id": pid, "x": centre_x, "y": y, "timestamp": t0},
                {"player_id": pid, "x": centre_x, "y": y, "timestamp": t1},
            ],
            "player_roles": {pid: "ST"},
        }

        # Violated: second frame moves ST outside the zone
        violated_branch = {
            "positions": [
                {"player_id": pid, "x": centre_x, "y": y, "timestamp": t0},
                {"player_id": pid, "x": violation_x, "y": y, "timestamp": t1},
            ],
            "player_roles": {pid: "ST"},
        }

        baseline_result = score_tactical_consistency(baseline_branch)
        violated_result = score_tactical_consistency(violated_branch)

        # The baseline has 0 violations → role_consistency_score == 1.0
        assert baseline_result.role_consistency_score == 1.0
        # The violated branch has at least 1 violation → score must be lower
        assert violated_result.role_consistency_score < baseline_result.role_consistency_score
