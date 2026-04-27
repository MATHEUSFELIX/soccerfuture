"""Unit tests for the tactical consistency scoring module.

Tests cover role-consistent branches scoring high, role-violating
branches scoring lower, formation coherence edge cases, and
defensive density with soccer events and roles.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 11.5
"""

from src.scoring.tactical_consistency import (
    TacticalConsistencyResult,
    score_tactical_consistency,
    _HALF_WIDTH,
    _EDGE_THRESHOLD,
)
from src.utils.constants import FIELD_WIDTH


class TestRoleConsistentBranch:
    """Test that role-consistent branches score high."""

    def test_gk_near_own_goal_scores_high(self) -> None:
        """GK positioned near own goal (x 24-44, y 0-10) should not violate."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 34.0, "y": 5.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 35.0, "y": 6.0, "timestamp": 0.5},
            ],
            "player_roles": {"p1": "GK"},
        }
        result = score_tactical_consistency(branch)
        assert isinstance(result, TacticalConsistencyResult)
        assert result.role_consistency_score == 1.0
        assert result.consistency_score >= 0.5

    def test_lw_on_left_flank_scores_high(self) -> None:
        """LW positioned on the left offensive flank (x 0-25, y 50-105) should not violate."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 10.0, "y": 70.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 12.0, "y": 72.0, "timestamp": 0.5},
            ],
            "player_roles": {"p1": "LW"},
        }
        result = score_tactical_consistency(branch)
        assert result.role_consistency_score == 1.0

    def test_full_role_consistent_team(self) -> None:
        """A team with all players in role-consistent positions scores high."""
        branch = {
            "positions": [
                {"player_id": "gk", "x": 34.0, "y": 5.0, "timestamp": 0.0},
                {"player_id": "cb1", "x": 24.0, "y": 20.0, "timestamp": 0.0},
                {"player_id": "cb2", "x": 44.0, "y": 20.0, "timestamp": 0.0},
                {"player_id": "lb", "x": 5.0, "y": 30.0, "timestamp": 0.0},
                {"player_id": "rb", "x": 60.0, "y": 30.0, "timestamp": 0.0},
            ],
            "player_roles": {
                "gk": "GK", "cb1": "CB", "cb2": "CB",
                "lb": "LB", "rb": "RB",
            },
        }
        result = score_tactical_consistency(branch)
        assert result.role_consistency_score == 1.0
        assert result.consistency_score >= 0.5


class TestRoleViolatingBranch:
    """Test that role-violating branches score lower."""

    def test_gk_far_from_goal_violates(self) -> None:
        """GK positioned far upfield (y > 10) should violate role expectations."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 34.0, "y": 50.0, "timestamp": 0.0},
            ],
            "player_roles": {"p1": "GK"},
        }
        result = score_tactical_consistency(branch)
        assert result.role_consistency_score < 1.0

    def test_st_in_own_half_violates(self) -> None:
        """ST positioned in own defensive zone (y < 65) should violate role expectations."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 34.0, "y": 10.0, "timestamp": 0.0},
            ],
            "player_roles": {"p1": "ST"},
        }
        result = score_tactical_consistency(branch)
        assert result.role_consistency_score < 1.0

    def test_more_violations_lower_score(self) -> None:
        """More role violations should produce a lower score."""
        # One violation out of two checks (first in zone, second out)
        branch_one = {
            "positions": [
                {"player_id": "p1", "x": 34.0, "y": 5.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 34.0, "y": 50.0, "timestamp": 0.5},
            ],
            "player_roles": {"p1": "GK"},
        }
        # Two violations out of two checks (both out of zone)
        branch_two = {
            "positions": [
                {"player_id": "p1", "x": 34.0, "y": 50.0, "timestamp": 0.0},
                {"player_id": "p1", "x": 34.0, "y": 60.0, "timestamp": 0.5},
            ],
            "player_roles": {"p1": "GK"},
        }
        result_one = score_tactical_consistency(branch_one)
        result_two = score_tactical_consistency(branch_two)
        assert result_two.role_consistency_score < result_one.role_consistency_score


class TestFormationCoherence:
    """Test formation coherence scoring."""

    def test_well_spaced_formation(self) -> None:
        """Players with reasonable spacing should score high."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 10.0, "y": 25.0, "timestamp": 0.0},
                {"player_id": "p2", "x": 20.0, "y": 25.0, "timestamp": 0.0},
                {"player_id": "p3", "x": 30.0, "y": 25.0, "timestamp": 0.0},
            ],
            "player_roles": {},
        }
        result = score_tactical_consistency(branch)
        assert result.formation_coherence_score == 1.0

    def test_clustered_players_score_lower(self) -> None:
        """Players clustered at the same spot should score lower."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 10.0, "y": 25.0, "timestamp": 0.0},
                {"player_id": "p2", "x": 10.01, "y": 25.0, "timestamp": 0.0},
                {"player_id": "p3", "x": 10.02, "y": 25.0, "timestamp": 0.0},
            ],
            "player_roles": {},
        }
        result = score_tactical_consistency(branch)
        assert result.formation_coherence_score < 1.0


class TestDefensiveDensity:
    """Test defensive density scoring with soccer events and roles."""

    def test_defenders_near_ball_carrier(self) -> None:
        """Defensive players near the ball carrier should produce high density."""
        branch = {
            "positions": [
                {"player_id": "st1", "x": 34.0, "y": 80.0, "timestamp": 0.0},
                {"player_id": "cb1", "x": 33.0, "y": 78.0, "timestamp": 0.0},
                {"player_id": "cb2", "x": 35.0, "y": 79.0, "timestamp": 0.0},
                {"player_id": "lb1", "x": 32.0, "y": 77.0, "timestamp": 0.0},
            ],
            "player_roles": {
                "st1": "ST", "cb1": "CB", "cb2": "CB", "lb1": "LB",
            },
            "events": [
                {"event_type": "dribble", "player_id": "st1", "timestamp": 0.0},
            ],
        }
        result = score_tactical_consistency(branch)
        assert result.defensive_density_score > 0.5

    def test_ball_carrier_from_pass_received(self) -> None:
        """Ball carrier identified via pass_received event."""
        branch = {
            "positions": [
                {"player_id": "cam1", "x": 34.0, "y": 60.0, "timestamp": 0.0},
                {"player_id": "cdm1", "x": 33.0, "y": 58.0, "timestamp": 0.0},
            ],
            "player_roles": {
                "cam1": "CAM", "cdm1": "CDM",
            },
            "events": [
                {"event_type": "pass_received", "player_id": "cam1", "timestamp": 0.0},
            ],
        }
        result = score_tactical_consistency(branch)
        # CDM is a defensive role and is near the ball carrier
        assert result.defensive_density_score > 0.0

    def test_fallback_to_st_when_no_events(self) -> None:
        """Without ball carrier events, should fall back to ST."""
        branch = {
            "positions": [
                {"player_id": "st1", "x": 34.0, "y": 80.0, "timestamp": 0.0},
                {"player_id": "rb1", "x": 55.0, "y": 30.0, "timestamp": 0.0},
            ],
            "player_roles": {
                "st1": "ST", "rb1": "RB",
            },
            "events": [],
        }
        result = score_tactical_consistency(branch)
        # RB is far from ST, so density should be low
        assert result.defensive_density_score < 1.0


class TestFormationShape:
    """Test formation_shape_score (replaces line_integrity_score)."""

    def test_evenly_spaced_defensive_line(self) -> None:
        """Evenly spaced defensive line should score high on formation shape."""
        branch = {
            "positions": [
                {"player_id": "lb", "x": 10.0, "y": 25.0, "timestamp": 0.0},
                {"player_id": "cb1", "x": 25.0, "y": 25.0, "timestamp": 0.0},
                {"player_id": "cb2", "x": 40.0, "y": 25.0, "timestamp": 0.0},
                {"player_id": "rb", "x": 55.0, "y": 25.0, "timestamp": 0.0},
            ],
            "player_roles": {
                "lb": "LB", "cb1": "CB", "cb2": "CB", "rb": "RB",
            },
        }
        result = score_tactical_consistency(branch)
        assert result.formation_shape_score >= 0.9

    def test_uneven_defensive_line_scores_lower(self) -> None:
        """Unevenly spaced defensive line should score lower on formation shape."""
        branch = {
            "positions": [
                {"player_id": "lb", "x": 5.0, "y": 25.0, "timestamp": 0.0},
                {"player_id": "cb1", "x": 6.0, "y": 25.0, "timestamp": 0.0},
                {"player_id": "cb2", "x": 7.0, "y": 25.0, "timestamp": 0.0},
                {"player_id": "rb", "x": 60.0, "y": 25.0, "timestamp": 0.0},
            ],
            "player_roles": {
                "lb": "LB", "cb1": "CB", "cb2": "CB", "rb": "RB",
            },
        }
        result = score_tactical_consistency(branch)
        assert result.formation_shape_score < 0.9


class TestEdgeCases:
    """Test edge cases for tactical consistency."""

    def test_empty_positions(self) -> None:
        """Empty positions should return high scores.

        With no positions: role=1.0, formation=1.0, compactness=1.0,
        density=0.5 (no defenders), formation_shape=1.0.
        consistency = 0.25*1 + 0.20*1 + 0.20*1 + 0.20*0.5 + 0.15*1 = 0.90
        """
        result = score_tactical_consistency({"positions": [], "player_roles": {}})
        assert result.role_consistency_score == 1.0
        assert result.formation_coherence_score == 1.0
        assert result.compactness_score == 1.0
        assert result.defensive_density_score == 0.5
        assert result.formation_shape_score == 1.0
        assert abs(result.consistency_score - 0.90) < 1e-9

    def test_no_player_roles(self) -> None:
        """Branch with positions but no roles should score 1.0 on role consistency."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 10.0, "y": 25.0, "timestamp": 0.0},
            ],
            "player_roles": {},
        }
        result = score_tactical_consistency(branch)
        assert result.role_consistency_score == 1.0

    def test_unknown_role(self) -> None:
        """Unknown role should not cause violations."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 10.0, "y": 25.0, "timestamp": 0.0},
            ],
            "player_roles": {"p1": "UNKNOWN_ROLE"},
        }
        result = score_tactical_consistency(branch)
        assert result.role_consistency_score == 1.0

    def test_scores_in_range(self) -> None:
        """All scores should be in [0, 1]."""
        branch = {
            "positions": [
                {"player_id": "p1", "x": 34.0, "y": 50.0, "timestamp": 0.0},
                {"player_id": "p2", "x": 10.0, "y": 70.0, "timestamp": 0.0},
            ],
            "player_roles": {"p1": "GK", "p2": "LW"},
        }
        result = score_tactical_consistency(branch)
        assert 0.0 <= result.consistency_score <= 1.0
        assert 0.0 <= result.role_consistency_score <= 1.0
        assert 0.0 <= result.formation_coherence_score <= 1.0
        assert 0.0 <= result.compactness_score <= 1.0
        assert 0.0 <= result.defensive_density_score <= 1.0
        assert 0.0 <= result.formation_shape_score <= 1.0
