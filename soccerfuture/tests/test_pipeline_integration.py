"""Integration tests for pipeline telemetry and explainability.

Runs the pipeline once on the counter_attack_midfield play state and
verifies that telemetry, ranking explanations, and filter reasons are
correctly wired end-to-end.

Requirements: 5.1, 5.2, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 9.1, 9.2, 9.3
"""

import json

import pytest
from hypothesis import given, settings

from src.models.play_state import dict_to_play_state
from src.models.pipeline_report import PipelineReport
from src.pipeline import PipelineConfig, run_pipeline
from src.utils.constants import DEFAULT_VALIDITY_THRESHOLD
from tests.strategies import play_state_strategy


@pytest.fixture(scope="module")
def pipeline_report() -> PipelineReport:
    """Run the pipeline once on counter_attack_midfield and reuse across tests."""
    with open("data/play_states/counter_attack_midfield.json") as f:
        ps = dict_to_play_state(json.load(f))
    return run_pipeline(ps, PipelineConfig(n=20, k=5, seed=42))


# ---------------------------------------------------------------------------
# 1. Telemetry presence and required keys (Req 7.1, 7.4)
# ---------------------------------------------------------------------------


class TestTelemetryPresence:
    """metadata['telemetry'] exists with all required keys."""

    def test_telemetry_key_exists(self, pipeline_report: PipelineReport):
        assert "telemetry" in pipeline_report.metadata

    def test_telemetry_has_required_keys(self, pipeline_report: PipelineReport):
        telemetry = pipeline_report.metadata["telemetry"]
        required = {
            "branches_generated",
            "hard_fail_count",
            "score_filtered_count",
            "avg_score_by_strategy",
            "avg_score_by_scenario",
            "time_per_stage",
        }
        assert required.issubset(telemetry.keys()), (
            f"Missing telemetry keys: {required - telemetry.keys()}"
        )

    def test_telemetry_is_json_serializable(self, pipeline_report: PipelineReport):
        telemetry = pipeline_report.metadata["telemetry"]
        # Should not raise
        json.dumps(telemetry)


# ---------------------------------------------------------------------------
# 2. time_per_stage contains generation, evaluation, ranking (Req 7.2)
# ---------------------------------------------------------------------------


class TestTimePerStage:
    """time_per_stage has the three required pipeline stages."""

    def test_time_per_stage_has_generation(self, pipeline_report: PipelineReport):
        tps = pipeline_report.metadata["telemetry"]["time_per_stage"]
        assert "generation" in tps

    def test_time_per_stage_has_evaluation(self, pipeline_report: PipelineReport):
        tps = pipeline_report.metadata["telemetry"]["time_per_stage"]
        assert "evaluation" in tps

    def test_time_per_stage_has_ranking(self, pipeline_report: PipelineReport):
        tps = pipeline_report.metadata["telemetry"]["time_per_stage"]
        assert "ranking" in tps

    def test_time_per_stage_values_are_non_negative(self, pipeline_report: PipelineReport):
        tps = pipeline_report.metadata["telemetry"]["time_per_stage"]
        for stage, elapsed in tps.items():
            assert elapsed >= 0.0, f"Stage '{stage}' has negative time: {elapsed}"


# ---------------------------------------------------------------------------
# 3. Ranked branches have ranking_explanation (Req 8.1, 8.2)
# ---------------------------------------------------------------------------


class TestRankingExplanation:
    """Each ranked branch carries a ranking_explanation with correct structure."""

    def test_all_ranked_branches_have_explanation(self, pipeline_report: PipelineReport):
        for rb in pipeline_report.ranked_branches:
            assert "ranking_explanation" in rb.evaluation_report, (
                f"Branch {rb.branch_id} missing ranking_explanation"
            )

    def test_explanation_has_promoted_factors(self, pipeline_report: PipelineReport):
        for rb in pipeline_report.ranked_branches:
            expl = rb.evaluation_report["ranking_explanation"]
            assert "promoted_factors" in expl
            assert isinstance(expl["promoted_factors"], list)

    def test_explanation_has_penalized_factors(self, pipeline_report: PipelineReport):
        for rb in pipeline_report.ranked_branches:
            expl = rb.evaluation_report["ranking_explanation"]
            assert "penalized_factors" in expl
            assert isinstance(expl["penalized_factors"], list)

    def test_explanation_has_top_scoring_block(self, pipeline_report: PipelineReport):
        for rb in pipeline_report.ranked_branches:
            expl = rb.evaluation_report["ranking_explanation"]
            assert "top_scoring_block" in expl
            assert isinstance(expl["top_scoring_block"], str)

    def test_explanation_has_bottom_scoring_block(self, pipeline_report: PipelineReport):
        for rb in pipeline_report.ranked_branches:
            expl = rb.evaluation_report["ranking_explanation"]
            assert "bottom_scoring_block" in expl
            assert isinstance(expl["bottom_scoring_block"], str)


# ---------------------------------------------------------------------------
# 4. Filtered branches have filter_reason with correct prefix (Req 9.1, 9.2)
# ---------------------------------------------------------------------------


class TestFilterReason:
    """Non-top-K evaluated branches carry a filter_reason string."""

    def test_filtered_branches_have_filter_reason(self, pipeline_report: PipelineReport):
        top_k_ids = {rb.branch_id for rb in pipeline_report.ranked_branches}
        non_top_k = [
            eb for eb in pipeline_report.evaluated_branches
            if eb["evaluation_report"].get("branch_id") not in top_k_ids
        ]
        # There should be some non-top-K branches (n=20, k=5)
        assert len(non_top_k) > 0, "Expected some non-top-K branches"
        for eb in non_top_k:
            assert "filter_reason" in eb, (
                f"Branch {eb['evaluation_report'].get('branch_id')} "
                f"missing filter_reason"
            )

    def test_filter_reason_has_correct_prefix(self, pipeline_report: PipelineReport):
        top_k_ids = {rb.branch_id for rb in pipeline_report.ranked_branches}
        for eb in pipeline_report.evaluated_branches:
            bid = eb["evaluation_report"].get("branch_id", "")
            if bid not in top_k_ids:
                reason = eb["filter_reason"]
                assert reason.startswith("Rejected: ") or reason.startswith("Filtered: "), (
                    f"Branch {bid} filter_reason has wrong prefix: {reason!r}"
                )


# ---------------------------------------------------------------------------
# 5. Top-K branches do NOT have filter_reason (Req 9.3)
# ---------------------------------------------------------------------------


class TestFilterReasonAbsentOnTopK:
    """filter_reason must not appear on branches that made it into top-K."""

    def test_top_k_branches_lack_filter_reason(self, pipeline_report: PipelineReport):
        top_k_ids = {rb.branch_id for rb in pipeline_report.ranked_branches}
        for eb in pipeline_report.evaluated_branches:
            bid = eb["evaluation_report"].get("branch_id", "")
            if bid in top_k_ids:
                assert "filter_reason" not in eb, (
                    f"Top-K branch {bid} should not have filter_reason, "
                    f"but found: {eb.get('filter_reason')!r}"
                )


# ---------------------------------------------------------------------------
# 6. Branch accounting invariant (Req 7.3)
# ---------------------------------------------------------------------------


class TestBranchAccountingInvariant:
    """hard_fail_count + score_filtered_count + gating_pass_count == branches_generated."""

    def test_accounting_invariant(self, pipeline_report: PipelineReport):
        telemetry = pipeline_report.metadata["telemetry"]
        gating_pass_count = pipeline_report.metadata["gating_pass_count"]

        total = (
            telemetry["hard_fail_count"]
            + telemetry["score_filtered_count"]
            + gating_pass_count
        )
        assert total == telemetry["branches_generated"], (
            f"Branch accounting mismatch: "
            f"hard_fail({telemetry['hard_fail_count']}) + "
            f"score_filtered({telemetry['score_filtered_count']}) + "
            f"gating_pass({gating_pass_count}) = {total}, "
            f"but branches_generated = {telemetry['branches_generated']}"
        )


# ---------------------------------------------------------------------------
# 7. Property 5: Top-K branch quality invariant (Req 5.1, 5.2)
# ---------------------------------------------------------------------------


class TestTopKBranchQualityInvariant:
    """Every ranked branch has passed_gating=True and validity_score >= threshold.

    **Validates: Requirements 5.1, 5.2**
    """

    @given(play_state=play_state_strategy())
    @settings(max_examples=10)
    def test_top_k_quality_invariant(self, play_state):
        """For any pipeline execution, all ranked branches pass gating and validity."""
        report = run_pipeline(play_state, PipelineConfig())

        for rb in report.ranked_branches:
            er = rb.evaluation_report
            assert er["passed_gating"] is True, (
                f"Ranked branch {rb.branch_id} has passed_gating=False"
            )
            assert er["validity_score"] >= DEFAULT_VALIDITY_THRESHOLD, (
                f"Ranked branch {rb.branch_id} has validity_score "
                f"{er['validity_score']:.4f} < threshold {DEFAULT_VALIDITY_THRESHOLD}"
            )


# ---------------------------------------------------------------------------
# 8. Property 12: Filter reason exclusivity (Req 9.3)
# ---------------------------------------------------------------------------


class TestFilterReasonExclusivity:
    """filter_reason is present only on non-top-K evaluated branches.

    **Validates: Requirements 9.3**
    """

    @given(play_state=play_state_strategy())
    @settings(max_examples=10)
    def test_filter_reason_exclusivity(self, play_state):
        """For any pipeline execution, filter_reason appears only on non-top-K branches."""
        report = run_pipeline(play_state, PipelineConfig())

        top_k_ids = {rb.branch_id for rb in report.ranked_branches}

        for eb in report.evaluated_branches:
            branch_id = eb["evaluation_report"].get("branch_id", "")
            if branch_id in top_k_ids:
                assert "filter_reason" not in eb, (
                    f"Top-K branch {branch_id} should not have filter_reason, "
                    f"but found: {eb.get('filter_reason')!r}"
                )
            else:
                assert "filter_reason" in eb, (
                    f"Non-top-K branch {branch_id} is missing filter_reason"
                )
