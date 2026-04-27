"""Unit tests for data models.

Tests dataclass instantiation and field access for all models:
PlayerPosition, EventMarker, Branch, ContinuationWindow,
SubMetrics, EvaluationReport, EvaluatorConfig.

Requirements: 9.4, 9.5
"""

import json
from dataclasses import asdict

import pytest

from src.models.branch import Branch, EventMarker, PlayerPosition
from src.models.config import EvaluatorConfig
from src.models.continuation_window import ContinuationWindow
from src.models.evaluation_report import EvaluationReport, SubMetrics


class TestPlayerPosition:
    """Tests for PlayerPosition dataclass."""

    def test_instantiation_and_field_access(self) -> None:
        pos = PlayerPosition(player_id="P1", x=10.0, y=25.0, timestamp=1.5)
        assert pos.player_id == "P1"
        assert pos.x == 10.0
        assert pos.y == 25.0
        assert pos.timestamp == 1.5

    def test_json_serializable(self) -> None:
        pos = PlayerPosition(player_id="P1", x=10.0, y=25.0, timestamp=1.5)
        result = json.dumps(asdict(pos))
        assert isinstance(result, str)


class TestEventMarker:
    """Tests for EventMarker dataclass."""

    def test_instantiation_and_field_access(self) -> None:
        event = EventMarker(
            event_type="pass", timestamp=0.0, player_id="P1", metadata={"zone": "midfield"}
        )
        assert event.event_type == "pass"
        assert event.timestamp == 0.0
        assert event.player_id == "P1"
        assert event.metadata == {"zone": "midfield"}

    def test_default_metadata(self) -> None:
        event = EventMarker(event_type="dribble", timestamp=2.0, player_id="P2")
        assert event.metadata == {}

    def test_json_serializable(self) -> None:
        event = EventMarker(event_type="shot", timestamp=1.0, player_id="P1")
        result = json.dumps(asdict(event))
        assert isinstance(result, str)


class TestBranch:
    """Tests for Branch dataclass."""

    def test_instantiation_and_field_access(self) -> None:
        pos = PlayerPosition(player_id="P1", x=10.0, y=25.0, timestamp=0.0)
        event = EventMarker(event_type="pass", timestamp=0.0, player_id="P1")
        branch = Branch(
            branch_id="B1",
            decision_point_timestamp=1.0,
            positions=[pos],
            events=[event],
            player_roles={"P1": "ST"},
            metadata={"play_type": "build_up"},
        )
        assert branch.branch_id == "B1"
        assert branch.decision_point_timestamp == 1.0
        assert len(branch.positions) == 1
        assert branch.positions[0].player_id == "P1"
        assert len(branch.events) == 1
        assert branch.player_roles == {"P1": "ST"}
        assert branch.metadata == {"play_type": "build_up"}

    def test_defaults(self) -> None:
        branch = Branch(branch_id="B2", decision_point_timestamp=0.5)
        assert branch.positions == []
        assert branch.events == []
        assert branch.player_roles == {}
        assert branch.metadata == {}

    def test_json_serializable(self) -> None:
        branch = Branch(branch_id="B1", decision_point_timestamp=1.0)
        result = json.dumps(asdict(branch))
        assert isinstance(result, str)


class TestContinuationWindow:
    """Tests for ContinuationWindow dataclass."""

    def test_instantiation_and_field_access(self) -> None:
        cw = ContinuationWindow(
            window_id="W1",
            decision_point_timestamp=1.0,
            outcomes=[{"ball_progression": 5}],
            metadata={"source": "real"},
        )
        assert cw.window_id == "W1"
        assert cw.decision_point_timestamp == 1.0
        assert cw.outcomes == [{"ball_progression": 5}]
        assert cw.metadata == {"source": "real"}

    def test_defaults(self) -> None:
        cw = ContinuationWindow(window_id="W2", decision_point_timestamp=0.0)
        assert cw.outcomes == []
        assert cw.metadata == {}

    def test_json_serializable(self) -> None:
        cw = ContinuationWindow(window_id="W1", decision_point_timestamp=1.0)
        result = json.dumps(asdict(cw))
        assert isinstance(result, str)


class TestSubMetrics:
    """Tests for SubMetrics dataclass."""

    def test_default_values(self) -> None:
        sm = SubMetrics()
        assert sm.speed_score == 0.0
        assert sm.acceleration_score == 0.0
        assert sm.deceleration_score == 0.0
        assert sm.position_accuracy == 0.0
        assert sm.event_timing_accuracy == 0.0
        assert sm.formation_consistency == 0.0
        assert sm.role_consistency_score == 0.0
        assert sm.formation_coherence_score == 0.0
        assert sm.ball_progression == 0.0
        assert sm.turnover_risk_delta == 0.0
        assert sm.scoring_probability_delta == 0.0
        assert sm.alignment_residual == 0.0
        assert sm.plausibility_score == 0.0
        assert sm.fidelity_score == 0.0
        assert sm.tactical_consistency_score == 0.0
        assert sm.decision_value_score == 0.0
        # v3 fields
        assert sm.compactness_score == 0.0
        assert sm.defensive_density_score == 0.0
        assert sm.formation_shape_score == 0.0
        assert sm.branch_window_similarity == 0.0

    def test_custom_values(self) -> None:
        sm = SubMetrics(speed_score=0.9, plausibility_score=0.85)
        assert sm.speed_score == 0.9
        assert sm.plausibility_score == 0.85
        assert sm.acceleration_score == 0.0  # still default

    def test_v3_custom_values(self) -> None:
        sm = SubMetrics(
            compactness_score=0.8,
            defensive_density_score=0.7,
            formation_shape_score=0.6,
            branch_window_similarity=0.95,
        )
        assert sm.compactness_score == 0.8
        assert sm.defensive_density_score == 0.7
        assert sm.formation_shape_score == 0.6
        assert sm.branch_window_similarity == 0.95
        # existing fields still default
        assert sm.speed_score == 0.0

    def test_json_serializable(self) -> None:
        sm = SubMetrics(speed_score=0.5)
        result = json.dumps(asdict(sm))
        assert isinstance(result, str)

    def test_v3_fields_json_serializable(self) -> None:
        sm = SubMetrics(
            compactness_score=0.8,
            defensive_density_score=0.7,
            formation_shape_score=0.6,
            branch_window_similarity=0.95,
        )
        d = asdict(sm)
        result = json.dumps(d)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["compactness_score"] == 0.8
        assert parsed["defensive_density_score"] == 0.7
        assert parsed["formation_shape_score"] == 0.6
        assert parsed["branch_window_similarity"] == 0.95


class TestEvaluationReport:
    """Tests for EvaluationReport dataclass."""

    def test_instantiation_and_field_access(self) -> None:
        sm = SubMetrics(speed_score=0.8, plausibility_score=0.7)
        report = EvaluationReport(
            branch_id="B1",
            validity_score=0.75,
            opportunity_score=0.6,
            gating_flags={"field_bounds": True, "max_speed": True},
            explanations=[],
            sub_metrics=sm,
            passed_gating=True,
            passed_validity=True,
        )
        assert report.branch_id == "B1"
        assert report.validity_score == 0.75
        assert report.opportunity_score == 0.6
        assert report.gating_flags == {"field_bounds": True, "max_speed": True}
        assert report.explanations == []
        assert report.sub_metrics.speed_score == 0.8
        assert report.passed_gating is True
        assert report.passed_validity is True

    def test_defaults(self) -> None:
        report = EvaluationReport(
            branch_id="B2", validity_score=0.0, opportunity_score=0.0
        )
        assert report.gating_flags == {}
        assert report.explanations == []
        assert isinstance(report.sub_metrics, SubMetrics)
        assert report.passed_gating is False
        assert report.passed_validity is False

    def test_json_serializable(self) -> None:
        report = EvaluationReport(
            branch_id="B1", validity_score=0.5, opportunity_score=0.3
        )
        result = json.dumps(asdict(report))
        assert isinstance(result, str)


class TestEvaluatorConfig:
    """Tests for EvaluatorConfig dataclass."""

    def test_default_values(self) -> None:
        config = EvaluatorConfig()
        assert config.validity_threshold == 0.35
        assert config.max_speed_override is None
        assert config.temporal_tolerance_override is None

    def test_custom_values(self) -> None:
        config = EvaluatorConfig(
            validity_threshold=0.7,
            max_speed_override=15.0,
            temporal_tolerance_override=0.1,
        )
        assert config.validity_threshold == 0.7
        assert config.max_speed_override == 15.0
        assert config.temporal_tolerance_override == 0.1

    def test_json_serializable(self) -> None:
        config = EvaluatorConfig()
        result = json.dumps(asdict(config))
        assert isinstance(result, str)
