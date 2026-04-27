"""Property-based tests for the alignment module.

Properties tested:
  - Property 8: Alignment anchors on decision-point timestamp
  - Property 9: Large alignment residual appears in output
"""

from __future__ import annotations

import math

from hypothesis import given, settings, strategies as st

from src.scoring.alignment import align
from src.utils.constants import ALIGNMENT_RESIDUAL_TOLERANCE


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_finite_float = st.floats(
    min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False
)

_positive_ts = st.floats(
    min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
)

_coord = st.floats(
    min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False
)


def _make_branch(decision_ts: float, positions: list[dict]) -> dict:
    return {
        "branch_id": "b1",
        "decision_point_timestamp": decision_ts,
        "positions": positions,
        "events": [],
        "player_roles": {},
        "metadata": {},
    }


def _make_window(decision_ts: float, outcome_positions: list[list[dict]]) -> dict:
    outcomes = [{"positions": p} for p in outcome_positions]
    return {
        "window_id": "w1",
        "decision_point_timestamp": decision_ts,
        "outcomes": outcomes,
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# Property 8: Alignment anchors on decision-point timestamp
# ---------------------------------------------------------------------------


class TestAlignmentAnchorProperty:
    """Feature: simulation-evaluator, Property 8: Alignment anchors on decision-point timestamp

    **Validates: Requirements 4.3, 4.4**
    """

    @settings(max_examples=100)
    @given(
        branch_ts=st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False),
        window_ts=st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False),
        px=_coord,
        py=_coord,
        extra_dt=st.floats(min_value=0.01, max_value=5.0, allow_nan=False, allow_infinity=False),
    )
    def test_aligned_timestamps_shifted_by_temporal_offset(
        self,
        branch_ts: float,
        window_ts: float,
        px: float,
        py: float,
        extra_dt: float,
    ) -> None:
        """After alignment, branch timestamps are shifted by -temporal_offset
        where temporal_offset = branch_ts - window_ts."""
        # Build branch with two positions at the decision point and one later
        positions = [
            {"player_id": "P1", "x": px, "y": py, "timestamp": branch_ts},
            {"player_id": "P1", "x": px, "y": py, "timestamp": branch_ts + extra_dt},
        ]
        # Window has the same player at the same coords so spatial offset is 0
        window_positions = [
            {"player_id": "P1", "x": px, "y": py, "timestamp": window_ts},
        ]

        branch = _make_branch(branch_ts, positions)
        window = _make_window(window_ts, [window_positions])

        result = align(branch, window)

        expected_offset = branch_ts - window_ts

        # The aligned branch timestamps should be shifted by -temporal_offset
        aligned_positions = result.aligned_branch["positions"]
        assert len(aligned_positions) == 2

        # First position: branch_ts - (branch_ts - window_ts) = window_ts
        assert abs(aligned_positions[0]["timestamp"] - window_ts) < 1e-9
        # Second position: (branch_ts + extra_dt) - (branch_ts - window_ts) = window_ts + extra_dt
        assert abs(aligned_positions[1]["timestamp"] - (window_ts + extra_dt)) < 1e-9

        # Temporal offset should match
        assert abs(result.temporal_offset - expected_offset) < 1e-9


# ---------------------------------------------------------------------------
# Property 9: Large alignment residual appears in output
# ---------------------------------------------------------------------------


class TestLargeAlignmentResidualProperty:
    """Feature: simulation-evaluator, Property 9: Large alignment residual appears in output

    **Validates: Requirements 4.5**
    """

    @settings(max_examples=100)
    @given(
        branch_ts=st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        window_ts=st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False),
        px=_coord,
        py=_coord,
    )
    def test_large_residual_is_nonzero(
        self,
        branch_ts: float,
        window_ts: float,
        px: float,
        py: float,
    ) -> None:
        """When decision-point timestamps are far apart (>= 2.0s difference),
        the residual magnitude exceeds ALIGNMENT_RESIDUAL_TOLERANCE and is non-zero."""
        # Ensure the temporal difference is large enough
        # branch_ts >= 5.0, window_ts <= 3.0, so diff >= 2.0
        positions = [
            {"player_id": "P1", "x": px, "y": py, "timestamp": branch_ts},
        ]
        window_positions = [
            {"player_id": "P1", "x": px, "y": py, "timestamp": window_ts},
        ]

        branch = _make_branch(branch_ts, positions)
        window = _make_window(window_ts, [window_positions])

        result = align(branch, window)

        # temporal_offset = branch_ts - window_ts >= 2.0
        # spatial_offset = 0 (same coords)
        # residual = sqrt(temporal^2 + spatial^2) = |temporal_offset| >= 2.0
        # ALIGNMENT_RESIDUAL_TOLERANCE = 1.0, so residual > tolerance
        assert result.residual_magnitude > 0.0
        assert result.residual_magnitude > ALIGNMENT_RESIDUAL_TOLERANCE
