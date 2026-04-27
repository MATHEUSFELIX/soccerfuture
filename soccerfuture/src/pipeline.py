"""Pipeline orchestrator for branch generation and evaluation.

Coordinates the full pipeline: generate branches from a PlayState,
evaluate each via the v3 simulation evaluator, compute composite scores,
rank, filter to top K, and assemble a PipelineReport.

This is the sole composition point that wires generation to evaluation.
"""

from __future__ import annotations

import dataclasses
import logging
import time
from dataclasses import dataclass

from src.explainability import build_filter_reason, build_ranking_explanation
from src.generation.branch_generator import generate_branches
from src.models.evaluation_report import EvaluationReport
from src.models.pipeline_report import PipelineReport, RankedBranch
from src.models.play_state import PlayState, play_state_to_dict
from src.simulation_evaluator_v2 import evaluate_branch
from src.telemetry import TelemetryCollector
from src.utils.constants import (
    DEFAULT_K,
    DEFAULT_N,
    DEFAULT_OPPORTUNITY_WEIGHT,
    DEFAULT_SEED,
    DEFAULT_VALIDITY_WEIGHT,
)

from src.domain.match_context import (
    ContextSignals,
    MatchContext,
    context_signals_to_dict,
    match_context_to_dict,
)
from src.services.context_enricher import enrich_context

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the pipeline orchestrator.

    Attributes:
        n: Number of branches to generate (10–30). Default 20.
        k: Number of top branches to keep. Default 5.
        seed: RNG seed for deterministic generation. Default 42.
        validity_weight: Weight for validity_score in composite. Default 0.5.
        opportunity_weight: Weight for opportunity_score in composite. Default 0.5.
    """

    n: int = DEFAULT_N
    k: int = DEFAULT_K
    seed: int = DEFAULT_SEED
    validity_weight: float = DEFAULT_VALIDITY_WEIGHT
    opportunity_weight: float = DEFAULT_OPPORTUNITY_WEIGHT


def compute_composite_score(
    report: EvaluationReport,
    validity_weight: float,
    opportunity_weight: float,
) -> float:
    """Compute weighted composite score for a branch.

    Args:
        report: Evaluation report for a branch.
        validity_weight: Weight for the validity component.
        opportunity_weight: Weight for the opportunity component.

    Returns:
        Composite score as a float.
    """
    return (
        validity_weight * report.validity_score
        + opportunity_weight * report.opportunity_score
    )


def _rank_and_filter(
    scored_branches: list[tuple[dict, EvaluationReport, float]],
    k: int,
) -> list[RankedBranch]:
    """Rank branches by composite score and filter to top K gating-passed.

    Sorting: descending by composite score, then ascending by branch_id
    for tiebreaking. Only branches that passed gating are included.

    Args:
        scored_branches: List of (branch_dict, eval_report, composite_score).
        k: Maximum number of branches to return.

    Returns:
        Top K RankedBranch objects that passed gating.
    """
    passed = [
        (branch, report, score)
        for branch, report, score in scored_branches
        if report.passed_gating
    ]

    passed.sort(key=lambda x: (-x[2], x[1].branch_id))

    ranked: list[RankedBranch] = []
    for branch, report, score in passed[:k]:
        ranked.append(
            RankedBranch(
                branch_id=report.branch_id,
                composite_score=score,
                evaluation_report=dataclasses.asdict(report),
                branch=branch,
            )
        )
    return ranked


def run_pipeline(
    play_state: PlayState,
    config: PipelineConfig | None = None,
    match_context: MatchContext | None = None,
) -> PipelineReport:
    """Execute the full branch generation and evaluation pipeline.

    Steps:
      1. Generate N branches + ContinuationWindow from PlayState.
      2. Evaluate each branch via evaluate_branch(branch, window).
      3. Compute composite score for each evaluated branch.
      4. Rank by composite score descending (branch_id tiebreaker).
      5. Filter to top K branches that passed gating.
      6. Assemble and return PipelineReport.

    Error handling:
      - If a single branch evaluation raises, skip it and log the error.
      - If all branches fail, return report with empty ranked list.
      - If the generator itself raises, return error report.
      - Never raises an unhandled exception.

    Args:
        play_state: The game situation to analyze.
        config: Optional pipeline configuration overrides.
        match_context: Optional pre-match context for context-aware
            enrichment. When provided, ContextSignals are derived and
            stored in the report. When absent, pipeline behavior is
            unchanged.

    Returns:
        PipelineReport with all results.
    """
    cfg = config or PipelineConfig()
    start = time.monotonic()
    errors: list[str] = []
    telemetry = TelemetryCollector()

    # --- Context enrichment (optional) ---
    context_signals: ContextSignals | None = None
    mc_dict: dict | None = None
    cs_dict: dict | None = None
    if match_context is not None:
        context_signals = enrich_context(match_context)
        mc_dict = match_context_to_dict(match_context)
        cs_dict = context_signals_to_dict(context_signals)

    try:
        ps_dict = play_state_to_dict(play_state)
    except Exception as exc:
        return PipelineReport(
            play_state={},
            evaluated_branches=[],
            ranked_branches=[],
            metadata={"error": f"Failed to serialize PlayState: {exc}"},
            errors=[f"PlayState serialization error: {exc}"],
        )

    # --- Step 1: Generate branches ---
    telemetry.start_stage("generation")
    try:
        gen_result = generate_branches(
            play_state, n=cfg.n, seed=cfg.seed
        )
    except Exception as exc:
        telemetry.end_stage("generation")
        elapsed = time.monotonic() - start
        msg = f"Branch generation failed: {exc}"
        logger.error(msg)
        return PipelineReport(
            play_state=ps_dict,
            evaluated_branches=[],
            ranked_branches=[],
            metadata={
                "seed": cfg.seed,
                "n_generated": 0,
                "k_requested": cfg.k,
                "gating_pass_count": 0,
                "execution_time_seconds": round(elapsed, 4),
                "error": msg,
                "telemetry": telemetry.to_dict(),
            },
            errors=[msg],
        )
    telemetry.end_stage("generation")

    branches = gen_result.branches
    window = gen_result.continuation_window

    # --- Step 2: Evaluate each branch ---
    telemetry.start_stage("evaluation")
    evaluated_branches: list[dict] = []
    scored: list[tuple[dict, EvaluationReport, float]] = []

    for branch in branches:
        branch_id = branch.get("branch_id", "unknown")
        try:
            report = evaluate_branch(branch, window)
        except Exception as exc:
            msg = f"Evaluation failed for branch {branch_id}: {exc}"
            logger.warning(msg)
            errors.append(msg)
            continue

        composite = compute_composite_score(
            report, cfg.validity_weight, cfg.opportunity_weight
        )
        strategy = branch.get("strategy", "unknown")
        telemetry.record_branch_result(
            strategy, composite, report.passed_gating, report.passed_validity
        )
        evaluated_branches.append(
            {"branch": branch, "evaluation_report": dataclasses.asdict(report)}
        )
        scored.append((branch, report, composite))
    telemetry.end_stage("evaluation")

    # --- Step 3: Rank and filter ---
    telemetry.start_stage("ranking")
    ranked = _rank_and_filter(scored, cfg.k)
    gating_pass_count = sum(
        1 for _, r, _ in scored if r.passed_gating
    )

    # --- Step 4: Attach ranking explanations to top-K branches ---
    for rb in ranked:
        explanation = build_ranking_explanation(
            rb.evaluation_report, cfg.validity_weight
        )
        rb.evaluation_report["ranking_explanation"] = explanation

    # --- Step 5: Attach filter reasons to non-top-K branches ---
    top_k_ids = {rb.branch_id for rb in ranked}
    for eb in evaluated_branches:
        report_dict = eb["evaluation_report"]
        branch_id = report_dict.get("branch_id", "")
        if branch_id not in top_k_ids:
            reason = build_filter_reason(
                report_dict,
                report_dict.get("passed_gating", False),
            )
            eb["filter_reason"] = reason

    telemetry.end_stage("ranking")

    elapsed = time.monotonic() - start

    metadata: dict = {
        "seed": cfg.seed,
        "n_generated": len(branches),
        "k_requested": cfg.k,
        "gating_pass_count": gating_pass_count,
        "execution_time_seconds": round(elapsed, 4),
        "strategy_counts": gen_result.strategy_counts,
        "telemetry": telemetry.to_dict(),
        "context_requested": match_context is not None,
        "context_applied": context_signals is not None,
        "context_cache_status": match_context.cache_status if match_context is not None else None,
        "context_source": match_context.source if match_context is not None else None,
    }

    # Handle all-branches-fail case
    if not evaluated_branches:
        metadata["error"] = "All branches failed evaluation"
        if not errors:
            errors.append("All branches failed evaluation")

    return PipelineReport(
        play_state=ps_dict,
        evaluated_branches=evaluated_branches,
        ranked_branches=ranked,
        metadata=metadata,
        errors=errors,
        match_context=mc_dict,
        context_signals=cs_dict,
    )
