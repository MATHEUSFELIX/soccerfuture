"""Unit tests for JSON serialization helpers.

Tests report_to_dict round-trip on a known report and
dict_to_report error handling on malformed dicts.

Requirements: 9.4, 9.5
"""

import json

import pytest

from src.models.evaluation_report import EvaluationReport, SubMetrics
from src.utils.serialization import dict_to_report, report_to_dict


def _make_known_report() -> EvaluationReport:
    """Build a fully-populated EvaluationReport for round-trip testing."""
    return EvaluationReport(
        branch_id="B-round-trip",
        validity_score=0.82,
        opportunity_score=0.65,
        gating_flags={
            "field_bounds": True,
            "max_speed": True,
            "temporal_continuity": True,
        },
        explanations=["Minor alignment residual noted"],
        sub_metrics=SubMetrics(
            speed_score=0.9,
            acceleration_score=0.85,
            deceleration_score=0.88,
            position_accuracy=0.75,
            event_timing_accuracy=0.8,
            formation_consistency=0.7,
            role_consistency_score=0.92,
            formation_coherence_score=0.78,
            ball_progression=0.6,
            turnover_risk_delta=0.55,
            scoring_probability_delta=0.5,
            alignment_residual=0.3,
            plausibility_score=0.87,
            fidelity_score=0.76,
            tactical_consistency_score=0.85,
            decision_value_score=0.62,
        ),
        passed_gating=True,
        passed_validity=True,
    )


class TestReportToDict:
    """Tests for report_to_dict."""

    def test_returns_plain_dict(self) -> None:
        report = _make_known_report()
        result = report_to_dict(report)
        assert isinstance(result, dict)

    def test_json_serializable(self) -> None:
        report = _make_known_report()
        d = report_to_dict(report)
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

    def test_preserves_top_level_fields(self) -> None:
        report = _make_known_report()
        d = report_to_dict(report)
        assert d["branch_id"] == "B-round-trip"
        assert d["validity_score"] == 0.82
        assert d["opportunity_score"] == 0.65
        assert d["passed_gating"] is True
        assert d["passed_validity"] is True

    def test_preserves_sub_metrics(self) -> None:
        report = _make_known_report()
        d = report_to_dict(report)
        sm = d["sub_metrics"]
        assert sm["speed_score"] == 0.9
        assert sm["plausibility_score"] == 0.87


class TestDictToReport:
    """Tests for dict_to_report."""

    def test_round_trip_equivalence(self) -> None:
        """Serialize then deserialize — result must equal the original."""
        original = _make_known_report()
        d = report_to_dict(original)
        restored = dict_to_report(d)

        assert restored.branch_id == original.branch_id
        assert restored.validity_score == original.validity_score
        assert restored.opportunity_score == original.opportunity_score
        assert restored.gating_flags == original.gating_flags
        assert restored.explanations == original.explanations
        assert restored.passed_gating == original.passed_gating
        assert restored.passed_validity == original.passed_validity
        # Sub-metrics
        assert restored.sub_metrics.speed_score == original.sub_metrics.speed_score
        assert restored.sub_metrics.plausibility_score == original.sub_metrics.plausibility_score
        assert restored.sub_metrics.alignment_residual == original.sub_metrics.alignment_residual

    def test_json_round_trip(self) -> None:
        """Full JSON string round-trip: dict → JSON string → dict → report."""
        original = _make_known_report()
        json_str = json.dumps(report_to_dict(original))
        restored = dict_to_report(json.loads(json_str))
        assert restored == original

    def test_raises_on_missing_branch_id(self) -> None:
        d = report_to_dict(_make_known_report())
        del d["branch_id"]
        with pytest.raises(KeyError):
            dict_to_report(d)

    def test_raises_on_missing_sub_metrics(self) -> None:
        d = report_to_dict(_make_known_report())
        del d["sub_metrics"]
        with pytest.raises(KeyError):
            dict_to_report(d)

    def test_raises_on_missing_validity_score(self) -> None:
        d = report_to_dict(_make_known_report())
        del d["validity_score"]
        with pytest.raises(KeyError):
            dict_to_report(d)

    def test_raises_on_missing_gating_flags(self) -> None:
        d = report_to_dict(_make_known_report())
        del d["gating_flags"]
        with pytest.raises(KeyError):
            dict_to_report(d)

    def test_raises_on_empty_dict(self) -> None:
        with pytest.raises(KeyError):
            dict_to_report({})
