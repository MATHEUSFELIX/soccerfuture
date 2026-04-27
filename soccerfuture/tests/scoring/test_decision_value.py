"""Unit tests for the decision value scoring module.

Tests cover branches better than reality scoring > 0.5, branches worse
than reality scoring < 0.5, and edge cases.  All positions use the
FIFA soccer field coordinate system (105 m × 68 m).

Requirements: 8.1, 8.3
"""

from src.scoring.decision_value import (
    DecisionValueResult,
    score_decision_value,
)
from src.utils.constants import FIELD_LENGTH


class TestBranchBetterThanReality:
    """Test that branches better than reality score > 0.5."""

    def test_higher_ball_progression_scores_above_half(self) -> None:
        """Branch with more forward progress than window should score > 0.5."""
        # Branch: players move forward significantly
        branch = {
            "positions": [
                {"player_id": "p1", "x": 26.0, "y": 20.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 26.0, "y": 50.0, "timestamp": 1.0},
            ],
            "events": [],
        }
        # Window: modest forward progress (meters)
        window = {
            "outcomes": [
                {"yard_gain": 3.0, "turnover": False, "scoring_play": False},
                {"yard_gain": 2.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert isinstance(result, DecisionValueResult)
        assert result.opportunity_score > 0.5

    def test_scoring_play_branch_scores_high(self) -> None:
        """Branch with a goal event should score high."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 26.0, "y": 90.0, "timestamp": 0.0},
            ],
            "events": [
                {"event_type": "goal", "timestamp": 1.0,
                 "player_id": "p1", "metadata": {}},
            ],
        }
        window = {
            "outcomes": [
                {"yard_gain": 5.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert result.opportunity_score > 0.5
        assert result.scoring_probability_delta > 0.5

    def test_no_turnover_vs_high_turnover_window(self) -> None:
        """Branch with no turnovers vs window with high turnover rate."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 26.0, "y": 30.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 26.0, "y": 35.0, "timestamp": 1.0},
            ],
            "events": [
                {"event_type": "pass", "timestamp": 0.5,
                 "player_id": "p1", "metadata": {}},
            ],
        }
        window = {
            "outcomes": [
                {"yard_gain": 5.0, "turnover": True, "scoring_play": False},
                {"yard_gain": 3.0, "turnover": True, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert result.turnover_risk_delta > 0.5


class TestBranchWorseThanReality:
    """Test that branches worse than reality score < 0.5."""

    def test_negative_ball_progression_scores_below_half(self) -> None:
        """Branch with backward movement vs positive window should score < 0.5."""
        # Branch: players move backward
        branch = {
            "positions": [
                {"player_id": "p1", "x": 26.0, "y": 30.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 26.0, "y": 10.0, "timestamp": 1.0},
            ],
            "events": [],
        }
        # Window: good forward progress (meters)
        window = {
            "outcomes": [
                {"yard_gain": 15.0, "turnover": False, "scoring_play": False},
                {"yard_gain": 20.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert result.opportunity_score < 0.5

    def test_turnover_branch_vs_clean_window(self) -> None:
        """Branch with turnovers vs clean window should score lower."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 26.0, "y": 30.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 26.0, "y": 25.0, "timestamp": 1.0},
            ],
            "events": [
                {"event_type": "dispossession", "timestamp": 0.5,
                 "player_id": "p1", "metadata": {}},
            ],
        }
        window = {
            "outcomes": [
                {"yard_gain": 10.0, "turnover": False, "scoring_play": False},
                {"yard_gain": 8.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert result.turnover_risk_delta < 0.5

    def test_all_worse_dimensions_below_half(self) -> None:
        """Branch worse on all dimensions should have opportunity < 0.5."""
        # Branch: backward movement, dispossession, no scoring, far from goal
        branch = {
            "positions": [
                {"player_id": "p1", "x": 26.0, "y": 30.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 26.0, "y": 10.0, "timestamp": 1.0},
            ],
            "events": [
                {"event_type": "dispossession", "timestamp": 0.5,
                 "player_id": "p1", "metadata": {}},
            ],
        }
        # Window: great outcomes
        window = {
            "outcomes": [
                {"yard_gain": 30.0, "turnover": False, "scoring_play": True},
                {"yard_gain": 25.0, "turnover": False, "scoring_play": True},
            ],
        }
        result = score_decision_value(branch, window)
        assert result.opportunity_score < 0.5


class TestEdgeCases:
    """Test edge cases for decision value scoring."""

    def test_empty_branch_and_window(self) -> None:
        """Empty branch and window should return neutral scores."""
        result = score_decision_value(
            {"positions": [], "events": []},
            {"outcomes": []},
        )
        assert 0.0 <= result.opportunity_score <= 1.0
        assert result.ball_progression == 0.5  # no difference

    def test_window_with_no_outcome_fields(self) -> None:
        """Window outcomes without progression/turnover/scoring_play fields."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 26.0, "y": 30.0, "timestamp": 0.0},
            ],
            "events": [],
        }
        window = {
            "outcomes": [{"some_other_field": 42}],
        }
        result = score_decision_value(branch, window)
        assert 0.0 <= result.opportunity_score <= 1.0

    def test_all_scores_in_range(self) -> None:
        """All scores should be in [0, 1]."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 26.0, "y": 50.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 26.0, "y": 80.0, "timestamp": 1.0},
            ],
            "events": [
                {"event_type": "pass", "timestamp": 0.5,
                 "player_id": "p1", "metadata": {}},
            ],
        }
        window = {
            "outcomes": [
                {"yard_gain": 10.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        assert 0.0 <= result.opportunity_score <= 1.0
        assert 0.0 <= result.ball_progression <= 1.0
        assert 0.0 <= result.turnover_risk_delta <= 1.0
        assert 0.0 <= result.scoring_probability_delta <= 1.0

    def test_identical_branch_and_window_near_half(self) -> None:
        """Branch matching window exactly should score near 0.5."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 26.0, "y": 30.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 26.0, "y": 35.0, "timestamp": 1.0},
            ],
            "events": [],
        }
        window = {
            "outcomes": [
                {"yard_gain": 5.0, "turnover": False, "scoring_play": False},
            ],
        }
        result = score_decision_value(branch, window)
        # Should be close to 0.5 since branch ≈ reality
        assert 0.3 <= result.opportunity_score <= 0.7
