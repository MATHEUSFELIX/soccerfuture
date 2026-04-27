"""Property-based tests for the predictive fidelity scoring module.

Properties tested:
  - Property 11: Significant divergence yields low fidelity
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from src.scoring.predictive_fidelity import score_predictive_fidelity
from src.utils.constants import SIGNIFICANT_DIVERGENCE_THRESHOLD


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Branch positions clustered near origin (0-5, 0-5)
_branch_coord = st.floats(
    min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False
)

# Window positions far away (80-100, 80-100)
_window_coord = st.floats(
    min_value=80.0, max_value=100.0, allow_nan=False, allow_infinity=False
)


@st.composite
def _divergent_branch_and_window(draw: st.DrawFn) -> tuple[dict, dict]:
    """Generate a branch and window with completely unrelated positions.

    Branch positions are in the (0-5, 0-5) region.
    Window positions are in the (80-100, 80-100) region.
    Events use different types so event timing also mismatches.
    """
    n_players = draw(st.integers(min_value=2, max_value=5))
    ts = draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))

    branch_positions = []
    window_positions = []
    for i in range(n_players):
        pid = f"P{i}"
        bx = draw(_branch_coord)
        by = draw(_branch_coord)
        branch_positions.append(
            {"player_id": pid, "x": bx, "y": by, "timestamp": ts}
        )
        wx = draw(_window_coord)
        wy = draw(_window_coord)
        window_positions.append(
            {"player_id": pid, "x": wx, "y": wy, "timestamp": ts}
        )

    # Use completely different event types
    branch_events = [
        {"event_type": "pass", "timestamp": ts, "player_id": "P0", "metadata": {}},
    ]
    window_events = [
        {"event_type": "tackle", "timestamp": ts + 10.0, "player_id": "P0", "metadata": {}},
    ]

    aligned_branch = {"positions": branch_positions, "events": branch_events}
    aligned_window = {
        "outcomes": [{"positions": window_positions, "events": window_events}],
    }
    return aligned_branch, aligned_window


# ---------------------------------------------------------------------------
# Property 11: Significant divergence yields low fidelity
# ---------------------------------------------------------------------------


class TestSignificantDivergenceLowFidelity:
    """Feature: simulation-evaluator, Property 11: Significant divergence yields low fidelity

    **Validates: Requirements 6.3**
    """

    @settings(max_examples=100)
    @given(data=_divergent_branch_and_window())
    def test_unrelated_branch_scores_below_threshold(
        self,
        data: tuple[dict, dict],
    ) -> None:
        """Branches with positions far from the window (80+ meters apart)
        should receive fidelity_score < SIGNIFICANT_DIVERGENCE_THRESHOLD (0.3)."""
        aligned_branch, aligned_window = data

        result = score_predictive_fidelity(aligned_branch, aligned_window)

        assert result.fidelity_score < SIGNIFICANT_DIVERGENCE_THRESHOLD
