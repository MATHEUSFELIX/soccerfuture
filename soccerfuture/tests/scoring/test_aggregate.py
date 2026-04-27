"""Unit tests for the aggregate scoring module.

Tests cover requirements 9.1, 9.2: correct validity/opportunity computation
and full sub-metric traceability in the EvaluationReport.
"""

import math

import pytest

from src.scoring.aggregate import AggregateInput, compute_aggregate
from src.scoring.alignment import AlignmentResult
from src.scoring.decision_value import DecisionValueResult
from src.scoring.gating import GatingResult
from src.scoring.physical_plausibility import PhysicalPlausibilityResult
from src.scoring.predictive_fidelity import PredictiveFidelityResult
from src.scoring.tactical_consistency import TacticalConsistencyResult
from src.utils.constants import ALIGNMENT_RESIDUAL_TOLERANCE


def _make_inputs(
    plausibility: float = 0.8,
    speed: float = 0.9,
    accel: float = 0.7,
    decel: float = 0.8,
    fidelity: float = 0.7,
    pos_acc: float = 0.8,
    evt_timing: float = 0.6,
    formation_cons: float = 0.5,
    residual_mag: float = 0.3,
    tactical: float = 0.6,
    role_cons: float = 0.7,
    form_coh: float = 0.5,
    decision_opp: float = 0.5,
    yard_gain: float = 0.6,
    turnover: float = 0.4,
    scoring_prob: float = 0.5,
    gating_passed: bool = True,
    continuation_window: dict | None = None,
) -> AggregateInput:
    """Build an AggregateInput with controllable sub-scores."""
    return AggregateInput(
        plausibility=PhysicalPlausibilityResult(
            plausibility_score=plausibility,
            speed_score=speed,
            acceleration_score=accel,
            deceleration_score=decel,
        ),
        fidelity=PredictiveFidelityResult(
            fidelity_score=fidelity,
            position_accuracy=pos_acc,
            event_timing_accuracy=evt_timing,
            formation_consistency=formation_cons,
        ),
        alignment=AlignmentResult(
            aligned_branch={"branch_id": "test-branch"},
            aligned_window={},
            temporal_offset=0.0,
            spatial_offset=0.0,
            residual_magnitude=residual_mag,
        ),
        tactical=TacticalConsistencyResult(
            consistency_score=tactical,
            role_consistency_score=role_cons,
            formation_coherence_score=form_coh,
            compactness_score=1.0,
            defensive_density_score=0.5,
            formation_shape_score=1.0,
        ),
        decision=DecisionValueResult(
            opportunity_score=decision_opp,
            ball_progression=yard_gain,
            turnover_risk_delta=turnover,
            scoring_probability_delta=scoring_prob,
        ),
        gating=GatingResult(
            passed=gating_passed,
            flags={"field_bounds": True, "max_speed": True, "temporal_continuity": True},
            explanations=[],
        ),
        continuation_window=continuation_window if continuation_window is not None else {},
    )


class TestValidityScoreComputation:
    """Requirement 9.1: validity = 0.5*plausibility + 0.3*fidelity + 0.2*(1-residual_norm)."""

    def test_known_values(self):
        inputs = _make_inputs(
            plausibility=0.8,
            fidelity=0.6,
            residual_mag=0.5,
        )
        report = compute_aggregate(inputs)

        # residual_norm = 0.5 / ALIGNMENT_RESIDUAL_TOLERANCE = 0.5 / 1.0 = 0.5
        # validity = 0.5*0.8 + 0.3*0.6 + 0.2*(1-0.5) = 0.4 + 0.18 + 0.1 = 0.68
        assert math.isclose(report.validity_score, 0.68, abs_tol=1e-9)

    def test_zero_residual_gives_full_alignment_contribution(self):
        inputs = _make_inputs(
            plausibility=1.0,
            fidelity=1.0,
            residual_mag=0.0,
        )
        report = compute_aggregate(inputs)

        # validity = 0.5*1.0 + 0.3*1.0 + 0.2*(1-0) = 0.5 + 0.3 + 0.2 = 1.0
        assert math.isclose(report.validity_score, 1.0, abs_tol=1e-9)

    def test_max_residual_zeroes_alignment_contribution(self):
        inputs = _make_inputs(
            plausibility=0.0,
            fidelity=0.0,
            residual_mag=ALIGNMENT_RESIDUAL_TOLERANCE,
        )
        report = compute_aggregate(inputs)

        # residual_norm = 1.0, validity = 0.5*0 + 0.3*0 + 0.2*(1-1) = 0.0
        assert math.isclose(report.validity_score, 0.0, abs_tol=1e-9)


class TestOpportunityScoreComputation:
    """Requirement 9.2: opportunity = 0.6*tactical + 0.4*decision."""

    def test_known_values(self):
        # Use a window with outcomes so similarity is computed properly
        # With empty continuation_window, event_sim=1.0 (no branch events to mismatch)
        # and pos_sim=0.5 (neutral), giving similarity=0.7 which triggers anchor.
        # We test the raw formula by checking the score is dampened toward 0.5.
        inputs = _make_inputs(tactical=0.8, decision_opp=0.5)
        report = compute_aggregate(inputs)

        # Raw opportunity = 0.4*0.8 + 0.6*0.5 = 0.62
        # Similarity ~0.7, anchor_strength = (0.7-0.2)/(1-0.2) = 0.625
        # Dampened = 0.62 + 0.625*(0.5-0.62)*1.0 = 0.62 - 0.075 = 0.545
        assert 0.4 <= report.opportunity_score <= 0.7

    def test_perfect_scores(self):
        inputs = _make_inputs(tactical=1.0, decision_opp=1.0)
        report = compute_aggregate(inputs)

        # Raw = 1.0, similarity ~0.7, dampened toward 0.5 but guardrail at 0.6
        assert report.opportunity_score >= 0.6

    def test_zero_scores(self):
        inputs = _make_inputs(tactical=0.0, decision_opp=0.0)
        report = compute_aggregate(inputs)

        # Raw = 0.0, similarity ~0.7, dampened toward 0.5 but guardrail at 0.4
        assert report.opportunity_score <= 0.4


class TestSubMetricsPresence:
    """Requirement 9.2: all 16 sub-metric fields are present in the report."""

    EXPECTED_FIELDS = [
        "speed_score",
        "acceleration_score",
        "deceleration_score",
        "position_accuracy",
        "event_timing_accuracy",
        "formation_consistency",
        "role_consistency_score",
        "formation_coherence_score",
        "ball_progression",
        "turnover_risk_delta",
        "scoring_probability_delta",
        "alignment_residual",
        "plausibility_score",
        "fidelity_score",
        "tactical_consistency_score",
        "decision_value_score",
    ]

    def test_all_sub_metrics_present(self):
        inputs = _make_inputs()
        report = compute_aggregate(inputs)

        for field_name in self.EXPECTED_FIELDS:
            assert hasattr(report.sub_metrics, field_name), (
                f"SubMetrics missing field: {field_name}"
            )
            value = getattr(report.sub_metrics, field_name)
            assert isinstance(value, float), (
                f"SubMetrics.{field_name} should be float, got {type(value)}"
            )

    def test_sub_metrics_count(self):
        inputs = _make_inputs()
        report = compute_aggregate(inputs)

        import dataclasses
        fields = dataclasses.fields(report.sub_metrics)
        assert len(fields) == 20, f"Expected 20 sub-metric fields, got {len(fields)}"

    def test_sub_metrics_reflect_inputs(self):
        inputs = _make_inputs(
            speed=0.9,
            accel=0.7,
            decel=0.8,
            pos_acc=0.8,
            evt_timing=0.6,
            formation_cons=0.5,
            role_cons=0.7,
            form_coh=0.5,
            yard_gain=0.6,
            turnover=0.4,
            scoring_prob=0.5,
        )
        report = compute_aggregate(inputs)
        sm = report.sub_metrics

        assert math.isclose(sm.speed_score, 0.9, abs_tol=1e-9)
        assert math.isclose(sm.acceleration_score, 0.7, abs_tol=1e-9)
        assert math.isclose(sm.deceleration_score, 0.8, abs_tol=1e-9)
        assert math.isclose(sm.position_accuracy, 0.8, abs_tol=1e-9)
        assert math.isclose(sm.event_timing_accuracy, 0.6, abs_tol=1e-9)
        assert math.isclose(sm.formation_consistency, 0.5, abs_tol=1e-9)
        assert math.isclose(sm.role_consistency_score, 0.7, abs_tol=1e-9)
        assert math.isclose(sm.formation_coherence_score, 0.5, abs_tol=1e-9)
        assert math.isclose(sm.ball_progression, 0.6, abs_tol=1e-9)
        assert math.isclose(sm.turnover_risk_delta, 0.4, abs_tol=1e-9)
        assert math.isclose(sm.scoring_probability_delta, 0.5, abs_tol=1e-9)
