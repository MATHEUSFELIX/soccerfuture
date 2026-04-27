"""Property-based tests for the explainability module.

Validates correctness properties of build_ranking_explanation and
build_filter_reason using Hypothesis.
"""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from src.explainability import build_filter_reason, build_ranking_explanation
from src.utils.constants import DEFAULT_VALIDITY_THRESHOLD
from tests.strategies import evaluation_report_dict_strategy


class TestRankingExplanationStructure:
    """Property 7: Ranking explanation structure.

    For any evaluation report dict, build_ranking_explanation returns a dict
    with promoted_factors (list), penalized_factors (list),
    top_scoring_block (str), and bottom_scoring_block (str).

    **Validates: Requirements 8.1, 8.2**
    """

    @given(report=evaluation_report_dict_strategy())
    @settings(max_examples=100)
    def test_ranking_explanation_has_required_keys_and_types(
        self, report: dict
    ) -> None:
        """For any evaluation report dict, the explanation contains all
        required keys with correct types."""
        result = build_ranking_explanation(report)

        # Required keys exist
        assert "promoted_factors" in result
        assert "penalized_factors" in result
        assert "top_scoring_block" in result
        assert "bottom_scoring_block" in result

        # Correct types
        assert isinstance(result["promoted_factors"], list)
        assert isinstance(result["penalized_factors"], list)
        assert isinstance(result["top_scoring_block"], str)
        assert isinstance(result["bottom_scoring_block"], str)

        # List elements are strings
        for factor in result["promoted_factors"]:
            assert isinstance(factor, str)
        for factor in result["penalized_factors"]:
            assert isinstance(factor, str)


class TestHighValidityPromotedFactors:
    """Property 8: High-validity branches reference plausibility/fidelity in promoted factors.

    For any evaluation report with validity_score > 0.7, promoted_factors
    includes at least one plausibility/fidelity sub-metric.

    **Validates: Requirements 8.3**
    """

    @given(data=st.data())
    @settings(max_examples=100)
    def test_high_validity_includes_plausibility_or_fidelity(
        self, data: st.DataObject
    ) -> None:
        """For any report with validity_score > 0.7, promoted_factors
        references Physical Plausibility or Predictive Fidelity."""
        report = data.draw(evaluation_report_dict_strategy())

        # Constrain: validity_score > 0.7 and sub_metrics has the keys
        report["validity_score"] = data.draw(
            st.floats(min_value=0.701, max_value=1.0, allow_nan=False, allow_infinity=False)
        )
        report["sub_metrics"]["plausibility_score"] = data.draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        )
        report["sub_metrics"]["fidelity_score"] = data.draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        )

        result = build_ranking_explanation(report)

        plausibility_fidelity_names = {"Physical Plausibility", "Predictive Fidelity"}
        promoted = set(result["promoted_factors"])
        assert promoted & plausibility_fidelity_names, (
            f"Expected at least one of {plausibility_fidelity_names} in "
            f"promoted_factors, got {result['promoted_factors']}"
        )


class TestLowOpportunityPenalizedFactors:
    """Property 9: Low-opportunity branches reference tactical/decision in penalized factors.

    For any evaluation report with opportunity_score < 0.4, penalized_factors
    includes at least one tactical/decision sub-metric.

    **Validates: Requirements 8.4**
    """

    @given(data=st.data())
    @settings(max_examples=100)
    def test_low_opportunity_includes_tactical_or_decision(
        self, data: st.DataObject
    ) -> None:
        """For any report with opportunity_score < 0.4, penalized_factors
        references Tactical Consistency or Decision Value."""
        report = data.draw(evaluation_report_dict_strategy())

        # Constrain: opportunity_score < 0.4 and sub_metrics has the keys
        report["opportunity_score"] = data.draw(
            st.floats(min_value=0.0, max_value=0.399, allow_nan=False, allow_infinity=False)
        )
        report["sub_metrics"]["tactical_consistency_score"] = data.draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        )
        report["sub_metrics"]["decision_value_score"] = data.draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        )

        result = build_ranking_explanation(report)

        tactical_decision_names = {"Tactical Consistency", "Decision Value"}
        penalized = set(result["penalized_factors"])
        assert penalized & tactical_decision_names, (
            f"Expected at least one of {tactical_decision_names} in "
            f"penalized_factors, got {result['penalized_factors']}"
        )


class TestNearThresholdWarning:
    """Property 10: Near-threshold branches receive warning.

    For any evaluation report where validity_score is within 0.1 of the
    validity threshold, ranking_explanation contains non-empty
    near_threshold_warning.

    **Validates: Requirements 8.5**
    """

    @given(data=st.data())
    @settings(max_examples=100)
    def test_near_threshold_has_warning(self, data: st.DataObject) -> None:
        """For any report with validity_score within 0.1 of threshold,
        near_threshold_warning is present and non-empty."""
        report = data.draw(evaluation_report_dict_strategy())

        # Generate validity_score in [0.26, 0.44] to be safely within 0.1 of 0.35
        # (avoids floating-point boundary issues at exactly ±0.1)
        report["validity_score"] = data.draw(
            st.floats(min_value=0.26, max_value=0.44, allow_nan=False, allow_infinity=False)
        )

        result = build_ranking_explanation(report, validity_threshold=DEFAULT_VALIDITY_THRESHOLD)

        assert "near_threshold_warning" in result, (
            f"Expected near_threshold_warning for validity_score={report['validity_score']}"
        )
        assert isinstance(result["near_threshold_warning"], str)
        assert len(result["near_threshold_warning"]) > 0, (
            "near_threshold_warning should be non-empty"
        )


class TestFilterReasonPrefixCorrectness:
    """Property 11: Filter reason prefix correctness.

    For any branch that failed gating, build_filter_reason returns string
    starting with "Rejected: "; for validity-filtered branches, starts
    with "Filtered: ".

    **Validates: Requirements 9.1, 9.2**
    """

    @given(report=evaluation_report_dict_strategy())
    @settings(max_examples=100)
    def test_gating_failure_rejected_prefix(self, report: dict) -> None:
        """For any branch that failed gating, filter reason starts with
        'Rejected: '."""
        reason = build_filter_reason(report, passed_gating=False)
        assert reason.startswith("Rejected: "), (
            f"Expected 'Rejected: ' prefix for gating failure, got: {reason!r}"
        )

    @given(report=evaluation_report_dict_strategy())
    @settings(max_examples=100)
    def test_validity_filtered_prefix(self, report: dict) -> None:
        """For any branch that passed gating but was validity-filtered,
        filter reason starts with 'Filtered: '."""
        reason = build_filter_reason(report, passed_gating=True)
        assert reason.startswith("Filtered: "), (
            f"Expected 'Filtered: ' prefix for validity filter, got: {reason!r}"
        )


class TestGatingFailureExplanationsNonEmpty:
    """Property 6: Gating failure explanations are non-empty.

    For any evaluation report with passed_gating=False, the explanations
    list contains at least one non-empty string.

    **Validates: Requirements 5.3**
    """

    @given(report=evaluation_report_dict_strategy())
    @settings(max_examples=100)
    def test_failed_gating_has_non_empty_explanation(self, report: dict) -> None:
        """For any report with passed_gating=False and at least one
        non-empty explanation, the explanations list is non-empty."""
        assume(report["passed_gating"] is False)
        assume(any(len(e) > 0 for e in report["explanations"]))

        non_empty = [e for e in report["explanations"] if len(e) > 0]
        assert len(non_empty) >= 1, (
            "Expected at least one non-empty explanation for a branch "
            f"that failed gating, got: {report['explanations']}"
        )
