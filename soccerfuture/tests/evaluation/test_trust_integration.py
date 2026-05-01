"""Integration tests for end-to-end human eval, robustness, and trust report."""

from __future__ import annotations

import json
import os

import pytest

from src.evaluation.human_eval_pack import generate_eval_pack, save_eval_pack
from src.evaluation.human_eval_protocol import HumanEvalProtocol
from src.evaluation.human_eval_results import (
    HumanEvalResponse,
    ingest_responses,
)
from src.evaluation.robustness_metrics import compute_robustness_summary
from src.evaluation.robustness_suite import run_robustness_batch
from src.evaluation.trust_report import generate_trust_report, save_trust_report
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig


@pytest.fixture(scope="module")
def play_state():
    with open("data/play_states/counter_attack_midfield.json") as f:
        return dict_to_play_state(json.load(f))


@pytest.fixture(scope="module")
def config():
    return PipelineConfig(n=10, k=3, seed=42)


# ---------------------------------------------------------------------------
# TestEndToEndHumanEvalPack
# ---------------------------------------------------------------------------


class TestEndToEndHumanEvalPack:
    """End-to-end: generate pack, create mock responses, ingest, verify."""

    def test_pack_generation_and_results_ingestion(self, play_state, config):
        scenarios = [
            {
                "scenario_id": "integ_s1",
                "play_state_file": "counter_attack_midfield.json",
                "play_state": play_state,
            }
        ]
        pack = generate_eval_pack(scenarios, config=config)
        assert isinstance(pack, HumanEvalProtocol)
        assert len(pack.scenarios) == 1

        # Create mock evaluator responses using the pack's questions
        question_ids = [q.question_id for q in pack.scenarios[0].questions]
        responses = [
            HumanEvalResponse(
                scenario_id="integ_s1",
                evaluator_id="evaluator_A",
                ratings={qid: 4 for qid in question_ids},
                notes="Looks reasonable.",
            ),
            HumanEvalResponse(
                scenario_id="integ_s1",
                evaluator_id="evaluator_B",
                ratings={qid: 3 for qid in question_ids},
            ),
        ]

        summary = ingest_responses(responses, pack)
        assert summary.scenario_count == 1
        assert summary.evaluator_count == 2
        assert summary.overall_avg > 0.0
        assert len(summary.scenario_summaries) == 1
        assert summary.scenario_summaries[0].response_count == 2


# ---------------------------------------------------------------------------
# TestEndToEndRobustness
# ---------------------------------------------------------------------------


class TestEndToEndRobustness:
    """End-to-end robustness batch execution and summary."""

    def test_robustness_batch_execution(self, play_state, config):
        """run_robustness_batch with 1 scenario and 2 strategies → correct result count."""
        scenarios = [
            {"scenario_id": "rob_s1", "play_state": play_state},
        ]
        strategies = ["noise", "time_shift"]
        results = run_robustness_batch(scenarios, strategies=strategies, config=config)
        assert len(results) == 2  # 1 scenario × 2 strategies
        for r in results:
            assert r.scenario_id == "rob_s1"
            assert r.strategy in strategies

    def test_robustness_summary_from_batch(self, play_state, config):
        """compute_robustness_summary from batch results → valid summary."""
        scenarios = [
            {"scenario_id": "rob_s2", "play_state": play_state},
        ]
        strategies = ["noise", "time_shift"]
        results = run_robustness_batch(scenarios, strategies=strategies, config=config)
        summary = compute_robustness_summary(results)

        assert summary.total_runs == 2
        assert summary.scenario_count == 1
        assert summary.strategy_count == 2
        assert (
            summary.robust_count + summary.sensitive_count + summary.fragile_count
            == summary.total_runs
        )


# ---------------------------------------------------------------------------
# TestEndToEndTrustReport
# ---------------------------------------------------------------------------


class TestEndToEndTrustReport:
    """End-to-end trust report generation with all streams."""

    def test_trust_report_with_all_streams(self, play_state, config):
        """Generate trust report with all three data streams → contains all sections."""
        human_eval_data = {
            "overall_avg": 3.8,
            "scenario_count": 1,
            "evaluator_count": 2,
            "category_averages": {"ranking_quality": 4.0, "general": 3.5},
        }
        robustness_data = {
            "summary": {
                "robust_count": 1,
                "sensitive_count": 1,
                "fragile_count": 0,
                "avg_validity_delta": -0.02,
                "avg_opportunity_delta": -0.01,
            }
        }
        context_impact_data = {
            "summary": {
                "scenarios_helped": ["s1"],
                "scenarios_neutral": [],
                "scenarios_degraded": [],
                "avg_validity_delta": 0.03,
                "avg_opportunity_delta": 0.02,
            }
        }

        report = generate_trust_report(
            human_eval_data=human_eval_data,
            robustness_data=robustness_data,
            context_impact_data=context_impact_data,
        )

        assert "## Human Evaluation Summary" in report
        assert "## Robustness Summary" in report
        assert "## Context Impact Summary" in report
        assert "## Trust Assessment" in report
        assert "## Recommendations" in report
        assert "High trust" in report

    def test_trust_report_save_creates_file(self, tmp_path):
        """save_trust_report creates file."""
        output_path = str(tmp_path / "trust_report.md")
        save_trust_report(output_path=output_path)
        assert os.path.isfile(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "# Consolidated Trust Report" in content
