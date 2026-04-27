"""Unit tests for the explainability module.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2
"""

import pytest

from src.explainability import build_filter_reason, build_ranking_explanation
from src.utils.constants import DEFAULT_VALIDITY_THRESHOLD


# ---------------------------------------------------------------------------
# Helpers — build evaluation report dicts with controlled sub_metrics
# ---------------------------------------------------------------------------

def _make_report(
    sub_metrics: dict[str, float] | None = None,
    validity_score: float | None = None,
    opportunity_score: float | None = None,
    explanations: list[str] | None = None,
) -> dict:
    """Build a minimal evaluation report dict for testing."""
    report: dict = {}
    if sub_metrics is not None:
        report["sub_metrics"] = sub_metrics
    if validity_score is not None:
        report["validity_score"] = validity_score
    if opportunity_score is not None:
        report["opportunity_score"] = opportunity_score
    if explanations is not None:
        report["explanations"] = explanations
    return report


def _high_sub_metrics() -> dict[str, float]:
    """Sub-metrics all above the promotion threshold (0.6)."""
    return {
        "speed_score": 0.8,
        "acceleration_score": 0.75,
        "plausibility_score": 0.9,
        "fidelity_score": 0.85,
        "tactical_consistency_score": 0.7,
        "decision_value_score": 0.65,
    }


def _low_sub_metrics() -> dict[str, float]:
    """Sub-metrics all below the penalty threshold (0.4)."""
    return {
        "speed_score": 0.2,
        "acceleration_score": 0.15,
        "plausibility_score": 0.1,
        "fidelity_score": 0.3,
        "tactical_consistency_score": 0.25,
        "decision_value_score": 0.35,
    }


# ---------------------------------------------------------------------------
# build_ranking_explanation — structure and required keys
# ---------------------------------------------------------------------------

class TestBuildRankingExplanationStructure:
    """Tests for the output structure of build_ranking_explanation."""

    def test_produces_all_required_keys(self) -> None:
        """Result contains promoted_factors, penalized_factors,
        top_scoring_block, and bottom_scoring_block."""
        report = _make_report(sub_metrics=_high_sub_metrics(), validity_score=0.6)
        result = build_ranking_explanation(report)

        assert "promoted_factors" in result
        assert "penalized_factors" in result
        assert "top_scoring_block" in result
        assert "bottom_scoring_block" in result
        assert isinstance(result["promoted_factors"], list)
        assert isinstance(result["penalized_factors"], list)
        assert isinstance(result["top_scoring_block"], str)
        assert isinstance(result["bottom_scoring_block"], str)

    def test_promoted_factors_populated_when_above_threshold(self) -> None:
        """Sub-metrics >= 0.6 appear as promoted factors."""
        report = _make_report(sub_metrics=_high_sub_metrics(), validity_score=0.6)
        result = build_ranking_explanation(report)

        assert len(result["promoted_factors"]) > 0
        # All our helper values are >= 0.65, so all should be promoted
        assert "Physical Speed" in result["promoted_factors"]
        assert "Acceleration" in result["promoted_factors"]

    def test_penalized_factors_populated_when_below_threshold(self) -> None:
        """Sub-metrics <= 0.4 appear as penalized factors."""
        report = _make_report(sub_metrics=_low_sub_metrics(), validity_score=0.5)
        result = build_ranking_explanation(report)

        assert len(result["penalized_factors"]) > 0
        assert "Physical Speed" in result["penalized_factors"]
        assert "Acceleration" in result["penalized_factors"]


# ---------------------------------------------------------------------------
# build_ranking_explanation — near-threshold warning (Req 8.5)
# ---------------------------------------------------------------------------

class TestNearThresholdWarning:
    """Tests for near_threshold_warning when validity is close to threshold."""

    def test_warning_present_when_validity_near_threshold(self) -> None:
        """near_threshold_warning appears when validity_score is within 0.1
        of DEFAULT_VALIDITY_THRESHOLD (0.35)."""
        # 0.40 is within 0.1 of 0.35
        report = _make_report(
            sub_metrics={"speed_score": 0.5},
            validity_score=0.40,
        )
        result = build_ranking_explanation(report)

        assert "near_threshold_warning" in result
        assert len(result["near_threshold_warning"]) > 0

    def test_warning_absent_when_validity_far_from_threshold(self) -> None:
        """near_threshold_warning absent when validity_score is far from threshold."""
        report = _make_report(
            sub_metrics={"speed_score": 0.5},
            validity_score=0.8,
        )
        result = build_ranking_explanation(report)

        assert "near_threshold_warning" not in result

    def test_warning_present_at_exact_threshold(self) -> None:
        """near_threshold_warning present when validity_score equals threshold."""
        report = _make_report(
            sub_metrics={"speed_score": 0.5},
            validity_score=DEFAULT_VALIDITY_THRESHOLD,
        )
        result = build_ranking_explanation(report)

        assert "near_threshold_warning" in result


# ---------------------------------------------------------------------------
# build_ranking_explanation — high-validity branch (Req 8.3)
# ---------------------------------------------------------------------------

class TestHighValidityPromotedFactors:
    """Tests for Req 8.3: high-validity branches reference plausibility/fidelity."""

    def test_high_validity_includes_plausibility_or_fidelity(self) -> None:
        """When validity_score > 0.7, promoted_factors includes a
        plausibility or fidelity sub-metric."""
        report = _make_report(
            sub_metrics={
                "plausibility_score": 0.5,  # below promotion threshold
                "fidelity_score": 0.45,     # below promotion threshold
                "speed_score": 0.3,
            },
            validity_score=0.75,
        )
        result = build_ranking_explanation(report)

        plausibility_fidelity_names = {"Physical Plausibility", "Predictive Fidelity"}
        promoted = set(result["promoted_factors"])
        assert promoted & plausibility_fidelity_names, (
            "Expected at least one plausibility/fidelity factor in promoted_factors"
        )

    def test_high_validity_already_promoted_not_duplicated(self) -> None:
        """When plausibility/fidelity already promoted (>= 0.6), no duplicate."""
        report = _make_report(
            sub_metrics={
                "plausibility_score": 0.9,
                "fidelity_score": 0.85,
                "speed_score": 0.7,
            },
            validity_score=0.75,
        )
        result = build_ranking_explanation(report)

        # Count occurrences — should not be duplicated
        count = result["promoted_factors"].count("Physical Plausibility")
        assert count <= 1


# ---------------------------------------------------------------------------
# build_ranking_explanation — low-opportunity branch (Req 8.4)
# ---------------------------------------------------------------------------

class TestLowOpportunityPenalizedFactors:
    """Tests for Req 8.4: low-opportunity branches reference tactical/decision."""

    def test_low_opportunity_includes_tactical_or_decision(self) -> None:
        """When opportunity_score < 0.4, penalized_factors includes a
        tactical or decision sub-metric."""
        report = _make_report(
            sub_metrics={
                "tactical_consistency_score": 0.5,  # above penalty threshold
                "decision_value_score": 0.45,       # above penalty threshold
                "speed_score": 0.6,
            },
            validity_score=0.5,
            opportunity_score=0.3,
        )
        result = build_ranking_explanation(report)

        tactical_decision_names = {"Tactical Consistency", "Decision Value"}
        penalized = set(result["penalized_factors"])
        assert penalized & tactical_decision_names, (
            "Expected at least one tactical/decision factor in penalized_factors"
        )

    def test_low_opportunity_already_penalized_not_duplicated(self) -> None:
        """When tactical/decision already penalized (<= 0.4), no duplicate."""
        report = _make_report(
            sub_metrics={
                "tactical_consistency_score": 0.2,
                "decision_value_score": 0.15,
            },
            validity_score=0.5,
            opportunity_score=0.3,
        )
        result = build_ranking_explanation(report)

        count_tc = result["penalized_factors"].count("Tactical Consistency")
        count_dv = result["penalized_factors"].count("Decision Value")
        assert count_tc <= 1
        assert count_dv <= 1


# ---------------------------------------------------------------------------
# build_filter_reason — prefix correctness (Req 9.1, 9.2)
# ---------------------------------------------------------------------------

class TestBuildFilterReason:
    """Tests for build_filter_reason prefix and content."""

    def test_rejected_prefix_for_gating_failure(self) -> None:
        """Gating failure produces a reason starting with 'Rejected: '."""
        report = _make_report(
            explanations=["Player QB1 exceeded speed limit"],
        )
        reason = build_filter_reason(report, passed_gating=False)

        assert reason.startswith("Rejected: ")

    def test_rejected_includes_first_explanation(self) -> None:
        """Gating failure reason includes the first explanation string."""
        report = _make_report(
            explanations=["Player QB1 exceeded speed limit"],
        )
        reason = build_filter_reason(report, passed_gating=False)

        assert "Player QB1 exceeded speed limit" in reason

    def test_filtered_prefix_for_validity_failure(self) -> None:
        """Validity failure produces a reason starting with 'Filtered: '."""
        report = _make_report(
            sub_metrics={"speed_score": 0.1, "acceleration_score": 0.2},
            validity_score=0.2,
        )
        reason = build_filter_reason(report, passed_gating=True)

        assert reason.startswith("Filtered: ")

    def test_filtered_mentions_insufficient_sub_scores(self) -> None:
        """Validity failure reason mentions sub-scores below 0.3."""
        report = _make_report(
            sub_metrics={"speed_score": 0.1, "position_accuracy": 0.05},
            validity_score=0.2,
        )
        reason = build_filter_reason(report, passed_gating=True)

        assert reason.startswith("Filtered: ")
        assert "Physical Speed" in reason or "Position Accuracy" in reason


# ---------------------------------------------------------------------------
# Graceful degradation — missing sub_metrics and explanations
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """Tests for graceful handling of missing data."""

    def test_missing_sub_metrics_returns_empty_factors(self) -> None:
        """Missing sub_metrics → empty promoted/penalized factors."""
        report = _make_report(validity_score=0.5)
        result = build_ranking_explanation(report)

        assert result["promoted_factors"] == []
        assert result["penalized_factors"] == []

    def test_missing_sub_metrics_returns_unknown_blocks(self) -> None:
        """Missing sub_metrics → 'unknown' for top/bottom scoring blocks."""
        report = _make_report(validity_score=0.5)
        result = build_ranking_explanation(report)

        assert result["top_scoring_block"] == "unknown"
        assert result["bottom_scoring_block"] == "unknown"

    def test_missing_explanations_returns_generic_rejection(self) -> None:
        """Missing explanations → generic rejection reason."""
        report = _make_report()
        reason = build_filter_reason(report, passed_gating=False)

        assert reason.startswith("Rejected: ")

    def test_empty_explanations_list_returns_generic_rejection(self) -> None:
        """Empty explanations list → generic rejection reason."""
        report = _make_report(explanations=[])
        reason = build_filter_reason(report, passed_gating=False)

        assert reason.startswith("Rejected: ")

    def test_empty_report_ranking_explanation(self) -> None:
        """Completely empty report still produces valid structure."""
        result = build_ranking_explanation({})

        assert "promoted_factors" in result
        assert "penalized_factors" in result
        assert "top_scoring_block" in result
        assert "bottom_scoring_block" in result
