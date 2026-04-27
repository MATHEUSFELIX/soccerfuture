"""Property-based tests for Pipeline Orchestrator (src/pipeline.py).

Feature: branch-generation-pipeline
- Property 12: Composite score equals weighted sum
- Property 13: Ranking is descending by composite score with branch_id tiebreaker
- Property 14: Pipeline never raises unhandled exceptions

Validates: Requirements 6.1, 6.2, 6.3, 7.4
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.evaluation_report import EvaluationReport
from src.models.pipeline_report import PipelineReport
from src.pipeline import compute_composite_score, _rank_and_filter, run_pipeline
from tests.strategies import evaluation_report_strategy, play_state_strategy


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Non-negative weights for composite score computation
_non_negative_weight = st.floats(
    min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
)


class TestProperty12CompositeScoreEqualsWeightedSum:
    """Property 12: Composite score equals weighted sum.

    For any EvaluationReport with validity_score v and opportunity_score o,
    and any non-negative weights wv and wo, the composite score SHALL equal
    wv * v + wo * o.
    """

    @given(
        report=evaluation_report_strategy(),
        wv=_non_negative_weight,
        wo=_non_negative_weight,
    )
    @settings(max_examples=100)
    def test_composite_score_equals_weighted_sum(
        self, report: EvaluationReport, wv: float, wo: float
    ) -> None:
        """**Validates: Requirements 6.1**"""
        result = compute_composite_score(report, wv, wo)
        expected = wv * report.validity_score + wo * report.opportunity_score
        assert result == expected


class TestProperty13RankingDescendingByCompositeScoreWithTiebreaker:
    """Property 13: Ranking is descending by composite score with branch_id tiebreaker.

    For any list of evaluated branches with composite scores, the ranked
    output SHALL be sorted in descending order by composite score, and for
    branches with equal composite scores, sorted in ascending lexicographic
    order by branch_id.
    """

    @given(
        data=st.lists(
            st.tuples(
                # branch dict with a branch_id
                st.text(min_size=1, max_size=20).map(lambda bid: {"branch_id": bid}),
                # EvaluationReport (always passed_gating=True so they appear in output)
                evaluation_report_strategy().map(
                    lambda r: EvaluationReport(
                        branch_id=r.branch_id,
                        validity_score=r.validity_score,
                        opportunity_score=r.opportunity_score,
                        gating_flags=r.gating_flags,
                        explanations=r.explanations,
                        sub_metrics=r.sub_metrics,
                        passed_gating=True,
                        passed_validity=r.passed_validity,
                    )
                ),
                # composite score
                st.floats(
                    min_value=0.0, max_value=1.0,
                    allow_nan=False, allow_infinity=False,
                ),
            ),
            min_size=0,
            max_size=15,
        ),
    )
    @settings(max_examples=100)
    def test_ranking_is_descending_with_tiebreaker(
        self, data: list[tuple[dict, EvaluationReport, float]]
    ) -> None:
        """**Validates: Requirements 6.2, 6.3**"""
        # Sync branch_id between the branch dict and the report
        scored = []
        for branch, report, score in data:
            synced_report = EvaluationReport(
                branch_id=branch["branch_id"],
                validity_score=report.validity_score,
                opportunity_score=report.opportunity_score,
                gating_flags=report.gating_flags,
                explanations=report.explanations,
                sub_metrics=report.sub_metrics,
                passed_gating=True,
                passed_validity=report.passed_validity,
            )
            scored.append((branch, synced_report, score))

        k = len(scored) + 1  # request more than available to get all
        ranked = _rank_and_filter(scored, k=k)

        # Verify descending by composite score
        for i in range(len(ranked) - 1):
            assert ranked[i].composite_score >= ranked[i + 1].composite_score, (
                f"ranked[{i}].composite_score={ranked[i].composite_score} < "
                f"ranked[{i + 1}].composite_score={ranked[i + 1].composite_score}"
            )

        # Verify tiebreaker: equal scores → ascending branch_id
        for i in range(len(ranked) - 1):
            if ranked[i].composite_score == ranked[i + 1].composite_score:
                assert ranked[i].branch_id <= ranked[i + 1].branch_id, (
                    f"Tiebreaker violated: {ranked[i].branch_id!r} > "
                    f"{ranked[i + 1].branch_id!r} at equal score "
                    f"{ranked[i].composite_score}"
                )


class TestProperty14PipelineNeverRaisesUnhandledExceptions:
    """Property 14: Pipeline never raises unhandled exceptions.

    For any input (valid PlayState, invalid PlayState, or None), calling
    run_pipeline SHALL return a PipelineReport and SHALL NOT raise.
    """

    @given(ps=play_state_strategy())
    @settings(max_examples=100)
    def test_valid_play_state_never_raises(self, ps) -> None:
        """**Validates: Requirements 7.4** — valid PlayState inputs."""
        result = run_pipeline(ps)
        assert isinstance(result, PipelineReport)

    @given(
        bad_input=st.one_of(
            st.none(),
            st.dictionaries(
                st.text(min_size=0, max_size=10),
                st.one_of(
                    st.text(min_size=0, max_size=20),
                    st.integers(min_value=-100, max_value=100),
                    st.floats(allow_nan=True, allow_infinity=True),
                    st.booleans(),
                    st.none(),
                ),
                min_size=0,
                max_size=5,
            ),
            st.integers(min_value=-1000, max_value=1000),
            st.text(min_size=0, max_size=50),
        ),
    )
    @settings(max_examples=100)
    def test_arbitrary_input_never_raises(self, bad_input) -> None:
        """**Validates: Requirements 7.4** — arbitrary/invalid inputs."""
        try:
            result = run_pipeline(bad_input)
            assert isinstance(result, PipelineReport)
        except Exception:
            # If it does raise, that's a property violation
            raise AssertionError(
                f"run_pipeline raised an exception for input: {bad_input!r}"
            )
