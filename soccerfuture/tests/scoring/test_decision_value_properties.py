"""Property-based tests for the decision value scoring module.

Properties tested:
  - Property 13: Worse-than-reality yields low opportunity
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from src.scoring.decision_value import score_decision_value


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Positive ball progression for the window outcomes (meters)
_positive_yard_gain = st.floats(
    min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False
)

# Negative y-displacement for the branch (players move backward)
_negative_dy = st.floats(
    min_value=-40.0, max_value=-1.0, allow_nan=False, allow_infinity=False
)

# Number of turnover events in the branch
_turnover_count = st.integers(min_value=1, max_value=3)

# Soccer turnover event types
_turnover_event_type = st.sampled_from(["interception", "dispossession"])


# ---------------------------------------------------------------------------
# Property 13: Worse-than-reality yields low opportunity
# ---------------------------------------------------------------------------


class TestWorseThanRealityLowOpportunity:
    """Feature: soccer-domain-migration, Property 13: Worse-than-reality yields low opportunity

    **Validates: Requirements 7.2, 7.4**
    """

    @settings(max_examples=100)
    @given(
        negative_dy=_negative_dy,
        window_yard_gain=_positive_yard_gain,
        n_turnovers=_turnover_count,
        event_type=_turnover_event_type,
    )
    def test_worse_branch_scores_below_half(
        self,
        negative_dy: float,
        window_yard_gain: float,
        n_turnovers: int,
        event_type: str,
    ) -> None:
        """A branch with negative ball progression, turnover events
        (interception/dispossession), and no scoring plays — compared
        against a window with positive ball progression, no turnovers,
        and scoring plays — should receive an opportunity_score below 0.5."""
        # Branch: player moves backward, has turnovers, no scoring
        branch_positions = [
            {"player_id": "P1", "x": 34.0, "y": 52.0, "timestamp": 0.0},
            {"player_id": "P1", "x": 34.0, "y": 52.0 + negative_dy, "timestamp": 1.0},
        ]
        branch_events = [
            {
                "event_type": event_type,
                "timestamp": 0.5 + i * 0.1,
                "player_id": "P1",
                "metadata": {},
            }
            for i in range(n_turnovers)
        ]

        aligned_branch = {
            "positions": branch_positions,
            "events": branch_events,
        }

        # Window: positive ball progression, no turnovers, scoring plays
        aligned_window = {
            "outcomes": [
                {
                    "yard_gain": window_yard_gain,
                    "turnover": False,
                    "scoring_play": True,
                },
            ],
        }

        result = score_decision_value(aligned_branch, aligned_window)

        assert result.opportunity_score < 0.5
