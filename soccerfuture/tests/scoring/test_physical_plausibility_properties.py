"""Property-based tests for the physical plausibility scoring module.

Properties tested:
  - Property 10: Teleportation yields zero plausibility for that segment
"""

from __future__ import annotations

import math

from hypothesis import given, settings, strategies as st

from src.scoring.physical_plausibility import score_physical_plausibility
from src.utils.constants import MAX_HUMAN_SPRINT_SPEED


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Coordinates within soccer field bounds (meters)
_coord = st.floats(
    min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False
)

_positive_ts = st.floats(
    min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False
)


# ---------------------------------------------------------------------------
# Property 10: Teleportation yields zero plausibility for that segment
# ---------------------------------------------------------------------------


class TestTeleportationZeroPlausibility:
    """Feature: simulation-evaluator, Property 10: Teleportation yields zero plausibility for that segment

    **Validates: Requirements 5.4**
    """

    @settings(max_examples=100)
    @given(
        x1=_coord,
        y1=_coord,
        t1=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        dt=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
        speed_multiplier=st.floats(min_value=1.5, max_value=20.0, allow_nan=False, allow_infinity=False),
        angle=st.floats(min_value=0.0, max_value=2 * math.pi, allow_nan=False, allow_infinity=False),
    )
    def test_teleportation_gives_zero_speed_score(
        self,
        x1: float,
        y1: float,
        t1: float,
        dt: float,
        speed_multiplier: float,
        angle: float,
    ) -> None:
        """When a player moves faster than MAX_HUMAN_SPRINT_SPEED (10.0 m/s)
        * dt in one frame, the speed_score for that player should be 0.0."""
        # Compute displacement that exceeds the physical limit
        distance = MAX_HUMAN_SPRINT_SPEED * dt * speed_multiplier
        x2 = x1 + distance * math.cos(angle)
        y2 = y1 + distance * math.sin(angle)
        t2 = t1 + dt

        positions = [
            {"player_id": "P1", "x": x1, "y": y1, "timestamp": t1},
            {"player_id": "P1", "x": x2, "y": y2, "timestamp": t2},
        ]
        aligned_branch = {"positions": positions}

        result = score_physical_plausibility(aligned_branch)

        # With only one player who teleports, speed_score must be 0.0
        assert result.speed_score == 0.0
