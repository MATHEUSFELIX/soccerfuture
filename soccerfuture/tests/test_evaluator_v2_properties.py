"""Property-based tests for the simulation evaluator v2 orchestrator.

Feature: simulation-evaluator
Properties 1, 2, 14, 15: Gating failure zeroes downstream, low validity
skips opportunity, all scores in [0,1], aggregate report completeness.
"""

from __future__ import annotations

import dataclasses
import json
import math

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.models.config import EvaluatorConfig
from src.models.evaluation_report import EvaluationReport, SubMetrics
from src.scoring.aggregate import AggregateInput, compute_aggregate
from src.scoring.alignment import AlignmentResult
from src.scoring.decision_value import DecisionValueResult
from src.scoring.gating import GatingResult
from src.scoring.physical_plausibility import PhysicalPlausibilityResult
from src.scoring.predictive_fidelity import PredictiveFidelityResult
from src.scoring.tactical_consistency import TacticalConsistencyResult
from src.simulation_evaluator_v2 import evaluate_branch
from src.utils.constants import (
    FIELD_LENGTH,
    FIELD_WIDTH,
    MAX_HUMAN_SPRINT_SPEED,
    MAX_TIMESTAMP_GAP,
)
from tests.strategies import (
    out_of_bounds_branch_strategy,
    excessive_speed_branch_strategy,
    valid_positions_strategy,
    sub_metrics_strategy,
)


# ---------------------------------------------------------------------------
# Helpers — build a full branch dict from a positions-only dict
# ---------------------------------------------------------------------------

def _complete_branch(partial: dict) -> dict:
    """Add required fields to a partial branch dict so it passes validation."""
    branch = dict(partial)
    branch.setdefault("branch_id", "prop-test-branch")
    branch.setdefault("decision_point_timestamp", 1.0)
    branch.setdefault("events", [])
    branch.setdefault("player_roles", {})
    branch.setdefault("metadata", {})
    return branch


def _dummy_continuation_window(decision_ts: float = 1.0) -> dict:
    """Build a minimal continuation window for testing."""
    return {
        "window_id": "cw-test",
        "decision_point_timestamp": decision_ts,
        "outcomes": [],
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# Strategy: valid branch that passes gating (in-bounds, slow, ordered)
# ---------------------------------------------------------------------------

@st.composite
def _valid_branch_strategy(draw: st.DrawFn) -> dict:
    """Generate a complete branch that passes validation and gating."""
    positions = draw(valid_positions_strategy(min_positions=2, max_positions=6))
    branch = {
        "branch_id": "valid-branch",
        "decision_point_timestamp": positions[0]["timestamp"],
        "positions": positions,
        "events": [],
        "player_roles": {},
        "metadata": {},
    }
    return branch


# ---------------------------------------------------------------------------
# Strategy: aggregate input with random valid scores
# ---------------------------------------------------------------------------

_unit_float = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_pos_float = st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False)


@st.composite
def _aggregate_input_strategy(draw: st.DrawFn) -> AggregateInput:
    """Generate a random AggregateInput with all scores in [0, 1]."""
    return AggregateInput(
        plausibility=PhysicalPlausibilityResult(
            plausibility_score=draw(_unit_float),
            speed_score=draw(_unit_float),
            acceleration_score=draw(_unit_float),
            deceleration_score=draw(_unit_float),
        ),
        fidelity=PredictiveFidelityResult(
            fidelity_score=draw(_unit_float),
            position_accuracy=draw(_unit_float),
            event_timing_accuracy=draw(_unit_float),
            formation_consistency=draw(_unit_float),
        ),
        alignment=AlignmentResult(
            aligned_branch={"branch_id": "agg-test"},
            aligned_window={},
            temporal_offset=draw(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
            spatial_offset=draw(_pos_float),
            residual_magnitude=draw(_pos_float),
        ),
        tactical=TacticalConsistencyResult(
            consistency_score=draw(_unit_float),
            role_consistency_score=draw(_unit_float),
            formation_coherence_score=draw(_unit_float),
            compactness_score=draw(_unit_float),
            defensive_density_score=draw(_unit_float),
            formation_shape_score=draw(_unit_float),
        ),
        decision=DecisionValueResult(
            opportunity_score=draw(_unit_float),
            ball_progression=draw(_unit_float),
            turnover_risk_delta=draw(_unit_float),
            scoring_probability_delta=draw(_unit_float),
        ),
        gating=GatingResult(
            passed=True,
            flags={"field_bounds": True, "max_speed": True, "temporal_continuity": True},
            explanations=[],
        ),
        continuation_window={},
    )


# ── Property 1: Gating failure zeroes downstream scores ─────────────────


@given(branch=st.one_of(out_of_bounds_branch_strategy(), excessive_speed_branch_strategy()))
@settings(max_examples=100)
def test_gating_failure_zeroes_downstream_scores(branch: dict) -> None:
    """Property 1: Gating failure zeroes downstream scores.

    **Validates: Requirements 2.1, 2.2, 2.4**

    For any branch that fails any gating check, the Evaluator shall
    return validity_score=0.0 and opportunity_score=0.0.
    """
    full_branch = _complete_branch(branch)
    window = _dummy_continuation_window(
        decision_ts=full_branch["decision_point_timestamp"]
    )

    report = evaluate_branch(full_branch, window)

    assert report.validity_score == 0.0, (
        f"Expected validity_score=0.0 for gating failure, got {report.validity_score}"
    )
    assert report.opportunity_score == 0.0, (
        f"Expected opportunity_score=0.0 for gating failure, got {report.opportunity_score}"
    )


# ── Property 2: Low validity skips opportunity scoring ───────────────────


@given(branch=_valid_branch_strategy())
@settings(max_examples=100)
def test_low_validity_skips_opportunity_scoring(branch: dict) -> None:
    """Property 2: Low validity skips opportunity scoring.

    **Validates: Requirements 2.3**

    For any branch that passes gating but receives validity below the
    configured threshold, the Evaluator shall return opportunity_score=0.0.
    """
    window = _dummy_continuation_window(
        decision_ts=branch["decision_point_timestamp"]
    )

    # Use a very high validity threshold so most branches fail it
    config = EvaluatorConfig(validity_threshold=0.99)
    report = evaluate_branch(branch, window, config=config)

    # If gating failed, validity=0 and opportunity=0 (still satisfies property)
    if not report.passed_gating:
        assert report.opportunity_score == 0.0
        return

    # If validity is below threshold, opportunity must be 0
    if report.validity_score < 0.99:
        assert report.opportunity_score == 0.0, (
            f"Expected opportunity_score=0.0 when validity={report.validity_score} "
            f"< threshold=0.99, got {report.opportunity_score}"
        )


# ── Property 14: All scores and sub-metrics are in [0, 1] ───────────────


@given(branch=_valid_branch_strategy())
@settings(max_examples=100)
def test_all_scores_and_sub_metrics_in_unit_range(branch: dict) -> None:
    """Property 14: All scores and sub-metrics are in [0, 1].

    **Validates: Requirements 5.1, 5.3, 6.1, 6.2, 7.1, 7.3, 8.1, 8.2, 10.5**

    For any valid branch processed by the evaluator, every score field
    and every sub-metric field in the EvaluationReport shall be a float
    in [0.0, 1.0].
    """
    window = _dummy_continuation_window(
        decision_ts=branch["decision_point_timestamp"]
    )

    report = evaluate_branch(branch, window)

    # Top-level scores
    assert 0.0 <= report.validity_score <= 1.0, (
        f"validity_score={report.validity_score} not in [0, 1]"
    )
    assert 0.0 <= report.opportunity_score <= 1.0, (
        f"opportunity_score={report.opportunity_score} not in [0, 1]"
    )

    # All sub-metric fields
    for field_info in dataclasses.fields(report.sub_metrics):
        value = getattr(report.sub_metrics, field_info.name)
        assert isinstance(value, (int, float)), (
            f"sub_metrics.{field_info.name} is not numeric: {type(value)}"
        )
        assert 0.0 <= value <= 1.0, (
            f"sub_metrics.{field_info.name}={value} not in [0, 1]"
        )



# ── Property 15: Aggregate report completeness and JSON-serializability ──


@given(inputs=_aggregate_input_strategy())
@settings(max_examples=100)
def test_aggregate_report_completeness_and_json_serializable(
    inputs: AggregateInput,
) -> None:
    """Property 15: Aggregate report completeness and JSON-serializability.

    **Validates: Requirements 9.1, 9.2, 9.4**

    For any set of valid scoring results, the Aggregate Module shall
    produce an EvaluationReport containing all required fields, and
    calling json.dumps on the report's dict representation shall succeed.
    """
    report = compute_aggregate(inputs)

    # Required top-level fields
    assert isinstance(report, EvaluationReport)
    assert isinstance(report.branch_id, str)
    assert isinstance(report.validity_score, float)
    assert isinstance(report.opportunity_score, float)
    assert isinstance(report.gating_flags, dict)
    assert isinstance(report.explanations, list)
    assert isinstance(report.sub_metrics, SubMetrics)
    assert isinstance(report.passed_gating, bool)
    assert isinstance(report.passed_validity, bool)

    # All 20 sub-metric fields present (16 original + 4 v3 fields)
    sm_fields = dataclasses.fields(report.sub_metrics)
    assert len(sm_fields) == 20, f"Expected 20 sub-metric fields, got {len(sm_fields)}"

    for field_info in sm_fields:
        value = getattr(report.sub_metrics, field_info.name)
        assert isinstance(value, float), (
            f"sub_metrics.{field_info.name} should be float, got {type(value)}"
        )

    # JSON-serializability
    report_dict = dataclasses.asdict(report)
    json_str = json.dumps(report_dict)
    assert isinstance(json_str, str)
    assert len(json_str) > 0

    # Round-trip: deserialize and check structure
    parsed = json.loads(json_str)
    assert "validity_score" in parsed
    assert "opportunity_score" in parsed
    assert "gating_flags" in parsed
    assert "explanations" in parsed
    assert "sub_metrics" in parsed
