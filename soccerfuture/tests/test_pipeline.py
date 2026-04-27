"""Unit tests for the Pipeline Orchestrator (src/pipeline.py).

Tests cover end-to-end execution, default config, composite score
computation, ranking order, tiebreaking, and error handling scenarios.

Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4
"""

from unittest.mock import patch, MagicMock

import pytest

from src.models.branch import PlayerPosition
from src.models.evaluation_report import EvaluationReport, SubMetrics
from src.models.pipeline_report import PipelineReport, RankedBranch
from src.models.play_state import PlayState
from src.pipeline import (
    PipelineConfig,
    compute_composite_score,
    run_pipeline,
    _rank_and_filter,
)


def _make_play_state() -> PlayState:
    """Build a test PlayState with 5 players."""
    positions = [
        PlayerPosition(player_id="p1", x=26.0, y=50.0, timestamp=1.0),
        PlayerPosition(player_id="p2", x=20.0, y=48.0, timestamp=1.0),
        PlayerPosition(player_id="p3", x=30.0, y=52.0, timestamp=1.0),
        PlayerPosition(player_id="p4", x=15.0, y=45.0, timestamp=1.0),
        PlayerPosition(player_id="p5", x=35.0, y=55.0, timestamp=1.0),
    ]
    return PlayState(
        match_time=45.0,
        possession_team="home",
        ball_position={"x": 34.0, "y": 52.5},
        game_phase="open_play",
        score_differential=0,
        game_clock=2700.0,
        player_positions=positions,
        decision_point_timestamp=1.0,
        player_roles={
            "p1": "ST",
            "p2": "CM",
            "p3": "LW",
            "p4": "RW",
            "p5": "CDM",
        },
        metadata={"formation": "4-3-3"},
    )


def _make_eval_report(
    branch_id: str,
    validity: float = 0.8,
    opportunity: float = 0.6,
    passed_gating: bool = True,
) -> EvaluationReport:
    """Build a controllable EvaluationReport for mocking."""
    return EvaluationReport(
        branch_id=branch_id,
        validity_score=validity,
        opportunity_score=opportunity,
        gating_flags={"speed": True, "timestamp": True},
        explanations=[],
        sub_metrics=SubMetrics(),
        passed_gating=passed_gating,
        passed_validity=validity > 0.35,
    )


# -----------------------------------------------------------------------
# 1. End-to-end with a simple PlayState produces a valid PipelineReport
# -----------------------------------------------------------------------


class TestEndToEnd:
    """End-to-end pipeline execution with a simple PlayState."""

    def test_produces_valid_pipeline_report(self):
        ps = _make_play_state()
        report = run_pipeline(ps)

        assert isinstance(report, PipelineReport)
        assert report.play_state  # non-empty dict
        assert isinstance(report.evaluated_branches, list)
        assert isinstance(report.ranked_branches, list)
        assert isinstance(report.metadata, dict)
        assert isinstance(report.errors, list)
        assert "seed" in report.metadata
        assert "n_generated" in report.metadata
        assert "execution_time_seconds" in report.metadata

    def test_report_is_json_serializable(self):
        import json

        ps = _make_play_state()
        report = run_pipeline(ps)
        d = report.to_dict()
        # Should not raise
        json.dumps(d)


# -----------------------------------------------------------------------
# 2. Default config applied when no config provided
# -----------------------------------------------------------------------


class TestDefaultConfig:
    """Default PipelineConfig values are applied when config=None."""

    def test_default_n_generates_20_branches(self):
        ps = _make_play_state()
        report = run_pipeline(ps)
        assert report.metadata["n_generated"] == 20

    def test_default_k_requests_5(self):
        ps = _make_play_state()
        report = run_pipeline(ps)
        assert report.metadata["k_requested"] == 5

    def test_default_seed_is_42(self):
        ps = _make_play_state()
        report = run_pipeline(ps)
        assert report.metadata["seed"] == 42


# -----------------------------------------------------------------------
# 3. Composite score correctness
# -----------------------------------------------------------------------


class TestCompositeScore:
    """composite = validity_weight * validity + opportunity_weight * opportunity."""

    def test_equal_weights(self):
        report = _make_eval_report("b1", validity=0.8, opportunity=0.6)
        score = compute_composite_score(report, 0.5, 0.5)
        assert score == pytest.approx(0.5 * 0.8 + 0.5 * 0.6)

    def test_validity_only(self):
        report = _make_eval_report("b1", validity=0.9, opportunity=0.3)
        score = compute_composite_score(report, 1.0, 0.0)
        assert score == pytest.approx(0.9)

    def test_opportunity_only(self):
        report = _make_eval_report("b1", validity=0.9, opportunity=0.3)
        score = compute_composite_score(report, 0.0, 1.0)
        assert score == pytest.approx(0.3)

    def test_custom_weights(self):
        report = _make_eval_report("b1", validity=0.6, opportunity=0.4)
        score = compute_composite_score(report, 0.7, 0.3)
        assert score == pytest.approx(0.7 * 0.6 + 0.3 * 0.4)


# -----------------------------------------------------------------------
# 4. Ranking order (descending by composite score)
# -----------------------------------------------------------------------


class TestRankingOrder:
    """Ranked branches are sorted descending by composite score."""

    def test_descending_order(self):
        scored = [
            ({"branch_id": "gen-001"}, _make_eval_report("gen-001", 0.5, 0.5), 0.5),
            ({"branch_id": "gen-002"}, _make_eval_report("gen-002", 0.9, 0.9), 0.9),
            ({"branch_id": "gen-003"}, _make_eval_report("gen-003", 0.7, 0.7), 0.7),
        ]
        ranked = _rank_and_filter(scored, k=3)
        scores = [rb.composite_score for rb in ranked]
        assert scores == sorted(scores, reverse=True)
        assert ranked[0].branch_id == "gen-002"
        assert ranked[1].branch_id == "gen-003"
        assert ranked[2].branch_id == "gen-001"

    def test_top_k_filtering(self):
        scored = [
            ({"branch_id": f"gen-{i:03d}"}, _make_eval_report(f"gen-{i:03d}", 0.1 * i, 0.1 * i), 0.1 * i)
            for i in range(1, 6)
        ]
        ranked = _rank_and_filter(scored, k=2)
        assert len(ranked) == 2
        assert ranked[0].composite_score >= ranked[1].composite_score


# -----------------------------------------------------------------------
# 5. Tiebreaker (branch_id lexicographic ascending when scores equal)
# -----------------------------------------------------------------------


class TestTiebreaker:
    """When composite scores are equal, branch_id ascending is the tiebreaker."""

    def test_equal_scores_sorted_by_branch_id(self):
        scored = [
            ({"branch_id": "gen-003"}, _make_eval_report("gen-003", 0.5, 0.5), 0.5),
            ({"branch_id": "gen-001"}, _make_eval_report("gen-001", 0.5, 0.5), 0.5),
            ({"branch_id": "gen-002"}, _make_eval_report("gen-002", 0.5, 0.5), 0.5),
        ]
        ranked = _rank_and_filter(scored, k=3)
        ids = [rb.branch_id for rb in ranked]
        assert ids == ["gen-001", "gen-002", "gen-003"]


# -----------------------------------------------------------------------
# 6. Single branch failure handling
# -----------------------------------------------------------------------


class TestSingleBranchFailure:
    """A single branch evaluation failure is skipped; others continue."""

    @patch("src.pipeline.evaluate_branch")
    @patch("src.pipeline.generate_branches")
    def test_single_failure_skipped(self, mock_gen, mock_eval):
        from src.generation.branch_generator import GenerationResult

        ps = _make_play_state()
        branches = [
            {"branch_id": "gen-001"},
            {"branch_id": "gen-002"},
            {"branch_id": "gen-003"},
        ]
        mock_gen.return_value = GenerationResult(
            branches=branches,
            continuation_window={"window_id": "cw-001"},
            strategy_counts={"route_variation": 1, "speed_variation": 1, "decision_variation": 1},
        )

        def side_effect(branch, window):
            if branch["branch_id"] == "gen-002":
                raise RuntimeError("Evaluation exploded")
            return _make_eval_report(branch["branch_id"])

        mock_eval.side_effect = side_effect

        report = run_pipeline(ps)

        assert isinstance(report, PipelineReport)
        # gen-002 was skipped
        assert len(report.evaluated_branches) == 2
        assert any("gen-002" in e for e in report.errors)


# -----------------------------------------------------------------------
# 7. All branches fail (empty ranked list, explanatory metadata)
# -----------------------------------------------------------------------


class TestAllBranchesFail:
    """When every branch evaluation raises, report has empty ranked list."""

    @patch("src.pipeline.evaluate_branch")
    @patch("src.pipeline.generate_branches")
    def test_all_fail_empty_ranked(self, mock_gen, mock_eval):
        from src.generation.branch_generator import GenerationResult

        ps = _make_play_state()
        branches = [{"branch_id": f"gen-{i:03d}"} for i in range(1, 4)]
        mock_gen.return_value = GenerationResult(
            branches=branches,
            continuation_window={"window_id": "cw-001"},
            strategy_counts={"route_variation": 1, "speed_variation": 1, "decision_variation": 1},
        )
        mock_eval.side_effect = RuntimeError("boom")

        report = run_pipeline(ps)

        assert isinstance(report, PipelineReport)
        assert report.ranked_branches == []
        assert report.evaluated_branches == []
        assert len(report.errors) == 3
        assert "error" in report.metadata


# -----------------------------------------------------------------------
# 8. Generator failure (error PipelineReport with message)
# -----------------------------------------------------------------------


class TestGeneratorFailure:
    """When the generator itself raises, an error PipelineReport is returned."""

    @patch("src.pipeline.generate_branches")
    def test_generator_exception(self, mock_gen):
        mock_gen.side_effect = ValueError("n must be between 10 and 30")

        ps = _make_play_state()
        report = run_pipeline(ps)

        assert isinstance(report, PipelineReport)
        assert report.ranked_branches == []
        assert report.evaluated_branches == []
        assert len(report.errors) >= 1
        assert any("generation" in e.lower() or "branch" in e.lower() for e in report.errors)


# -----------------------------------------------------------------------
# 9. Pipeline never raises (even with bad input)
# -----------------------------------------------------------------------


class TestNeverRaises:
    """run_pipeline must never raise an unhandled exception."""

    def test_with_valid_play_state(self):
        ps = _make_play_state()
        report = run_pipeline(ps)
        assert isinstance(report, PipelineReport)

    @patch("src.pipeline.generate_branches")
    def test_with_generator_raising(self, mock_gen):
        mock_gen.side_effect = Exception("unexpected")
        ps = _make_play_state()
        report = run_pipeline(ps)
        assert isinstance(report, PipelineReport)

    @patch("src.pipeline.play_state_to_dict")
    def test_with_serialization_failure(self, mock_ser):
        mock_ser.side_effect = TypeError("not serializable")
        ps = _make_play_state()
        report = run_pipeline(ps)
        assert isinstance(report, PipelineReport)
        assert len(report.errors) >= 1
