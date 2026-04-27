"""Context impact analysis for comparing pipeline runs with and without context.

Provides paired execution, per-scenario diff logic, aggregate metrics,
impact classification, and JSON persistence. This module ONLY observes
and compares outputs — it never modifies pipeline behavior.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field

from src.domain.match_context import MatchContext
from src.models.pipeline_report import PipelineReport
from src.models.play_state import PlayState
from src.pipeline import PipelineConfig, run_pipeline

# ---------------------------------------------------------------------------
# Classification thresholds
# ---------------------------------------------------------------------------

NEUTRAL_OPPORTUNITY_EPSILON: float = 0.02
NEUTRAL_VALIDITY_EPSILON: float = 0.02
DEGRADED_OPPORTUNITY_THRESHOLD: float = -0.05
DEGRADED_VALIDITY_THRESHOLD: float = -0.05

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ContextImpactResult:
    """Per-scenario comparison between no-context and with-context runs."""

    scenario_id: str
    no_context_top_1: str | None
    with_context_top_1: str | None
    top_1_changed: bool
    no_context_top_3: list[str]
    with_context_top_3: list[str]
    top_3_changed: bool
    avg_validity_delta: float
    avg_opportunity_delta: float
    context_applied: bool
    context_partial: bool
    cache_status: str | None
    fallback_used: bool
    notes: list[str]
    explanation_delta_summary: list[str] = field(default_factory=list)
    viewer_artifacts: dict[str, str] | None = None


@dataclass
class ContextImpactSummary:
    """Aggregate across multiple scenarios."""

    scenario_count: int
    top_1_changed_count: int
    top_3_changed_count: int
    neutral_context_count: int
    partial_context_count: int
    fallback_count: int
    cache_hit_count: int
    cache_miss_count: int
    avg_validity_delta: float
    avg_opportunity_delta: float
    scenarios_helped: list[str]
    scenarios_neutral: list[str]
    scenarios_degraded: list[str]
    notes: list[str]


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_impact(result: ContextImpactResult) -> str:
    """Classify a scenario's context impact as helpful, neutral, or degrading.

    Classification rules:
      - helpful: top_1_changed AND avg_opportunity_delta > NEUTRAL_OPPORTUNITY_EPSILON
      - degrading: avg_opportunity_delta < DEGRADED_OPPORTUNITY_THRESHOLD
            OR avg_validity_delta < DEGRADED_VALIDITY_THRESHOLD
      - neutral: everything else

    Args:
        result: A single scenario's impact result.

    Returns:
        One of ``"helpful"``, ``"neutral"``, or ``"degrading"``.
    """
    if (
        result.avg_opportunity_delta < DEGRADED_OPPORTUNITY_THRESHOLD
        or result.avg_validity_delta < DEGRADED_VALIDITY_THRESHOLD
    ):
        return "degrading"
    if (
        result.top_1_changed
        and result.avg_opportunity_delta > NEUTRAL_OPPORTUNITY_EPSILON
    ):
        return "helpful"
    return "neutral"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_top_n_ids(report: PipelineReport, n: int) -> list[str]:
    """Extract the top-N branch IDs from a pipeline report.

    Args:
        report: A completed pipeline report.
        n: Number of top branch IDs to return.

    Returns:
        List of branch_id strings, up to *n* entries.
    """
    return [rb.branch_id for rb in report.ranked_branches[:n]]


def _avg_score(report: PipelineReport, key: str) -> float:
    """Compute the average of a score field across ranked branches.

    Args:
        report: A completed pipeline report.
        key: The evaluation report key to average (e.g. ``"validity_score"``).

    Returns:
        The mean value, or ``0.0`` if no ranked branches exist.
    """
    scores = [
        rb.evaluation_report.get(key, 0.0)
        for rb in report.ranked_branches
    ]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def compare_pipeline_runs(
    no_context_report: PipelineReport,
    with_context_report: PipelineReport,
    scenario_id: str,
) -> ContextImpactResult:
    """Compare two pipeline reports (no-context vs with-context) for one scenario.

    Extracts top-1, top-3, computes avg validity/opportunity deltas across
    ranked branches, extracts cache_status and context_applied from metadata,
    and generates notes.

    Args:
        no_context_report: Pipeline report from a run without match context.
        with_context_report: Pipeline report from a run with match context.
        scenario_id: Identifier for this scenario.

    Returns:
        A ContextImpactResult capturing the diff.
    """
    no_top_1 = _extract_top_n_ids(no_context_report, 1)
    wc_top_1 = _extract_top_n_ids(with_context_report, 1)
    no_top_3 = _extract_top_n_ids(no_context_report, 3)
    wc_top_3 = _extract_top_n_ids(with_context_report, 3)

    no_top_1_id = no_top_1[0] if no_top_1 else None
    wc_top_1_id = wc_top_1[0] if wc_top_1 else None

    top_1_changed = no_top_1_id != wc_top_1_id
    top_3_changed = no_top_3 != wc_top_3

    no_avg_validity = _avg_score(no_context_report, "validity_score")
    wc_avg_validity = _avg_score(with_context_report, "validity_score")
    no_avg_opportunity = _avg_score(no_context_report, "opportunity_score")
    wc_avg_opportunity = _avg_score(with_context_report, "opportunity_score")

    avg_validity_delta = round(wc_avg_validity - no_avg_validity, 6)
    avg_opportunity_delta = round(wc_avg_opportunity - no_avg_opportunity, 6)

    wc_meta = with_context_report.metadata
    context_applied = bool(wc_meta.get("context_applied", False))
    context_partial = not context_applied and wc_meta.get("context_requested", False)
    cache_status = wc_meta.get("context_cache_status")
    fallback_used = bool(with_context_report.errors) and context_partial

    notes: list[str] = []
    if top_1_changed:
        notes.append(
            f"Top-1 changed from {no_top_1_id} to {wc_top_1_id}."
        )
    if top_3_changed:
        notes.append("Top-3 ranking order changed with context.")
    if context_partial:
        notes.append("Context was requested but only partially applied.")
    if fallback_used:
        notes.append("Fallback was used due to errors in context run.")
    if avg_opportunity_delta > NEUTRAL_OPPORTUNITY_EPSILON:
        notes.append(
            f"Opportunity improved by {avg_opportunity_delta:.4f}."
        )
    elif avg_opportunity_delta < DEGRADED_OPPORTUNITY_THRESHOLD:
        notes.append(
            f"Opportunity degraded by {abs(avg_opportunity_delta):.4f}."
        )

    return ContextImpactResult(
        scenario_id=scenario_id,
        no_context_top_1=no_top_1_id,
        with_context_top_1=wc_top_1_id,
        top_1_changed=top_1_changed,
        no_context_top_3=no_top_3,
        with_context_top_3=wc_top_3,
        top_3_changed=top_3_changed,
        avg_validity_delta=avg_validity_delta,
        avg_opportunity_delta=avg_opportunity_delta,
        context_applied=context_applied,
        context_partial=context_partial,
        cache_status=cache_status,
        fallback_used=fallback_used,
        notes=notes,
    )


def run_paired_analysis(
    play_state: PlayState,
    match_context: MatchContext,
    scenario_id: str,
    config: PipelineConfig | None = None,
) -> ContextImpactResult:
    """Run the pipeline twice (without and with context) and compare.

    Args:
        play_state: The game situation to analyze.
        match_context: Pre-match context to use for the with-context run.
        scenario_id: Identifier for this scenario.
        config: Optional pipeline configuration overrides.

    Returns:
        A ContextImpactResult capturing the diff between the two runs.
    """
    no_context_report = run_pipeline(play_state, config=config, match_context=None)
    with_context_report = run_pipeline(
        play_state, config=config, match_context=match_context
    )
    return compare_pipeline_runs(no_context_report, with_context_report, scenario_id)


def compute_aggregate_summary(
    results: list[ContextImpactResult],
) -> ContextImpactSummary:
    """Aggregate multiple per-scenario results into a summary.

    Args:
        results: List of per-scenario impact results.

    Returns:
        A ContextImpactSummary with counts, averages, and classification lists.
    """
    if not results:
        return ContextImpactSummary(
            scenario_count=0,
            top_1_changed_count=0,
            top_3_changed_count=0,
            neutral_context_count=0,
            partial_context_count=0,
            fallback_count=0,
            cache_hit_count=0,
            cache_miss_count=0,
            avg_validity_delta=0.0,
            avg_opportunity_delta=0.0,
            scenarios_helped=[],
            scenarios_neutral=[],
            scenarios_degraded=[],
            notes=["No scenarios to aggregate."],
        )

    top_1_changed_count = sum(1 for r in results if r.top_1_changed)
    top_3_changed_count = sum(1 for r in results if r.top_3_changed)
    neutral_context_count = sum(
        1 for r in results if not r.context_applied and not r.context_partial
    )
    partial_context_count = sum(1 for r in results if r.context_partial)
    fallback_count = sum(1 for r in results if r.fallback_used)
    cache_hit_count = sum(1 for r in results if r.cache_status == "hit")
    cache_miss_count = sum(1 for r in results if r.cache_status == "miss")

    avg_validity_delta = round(
        sum(r.avg_validity_delta for r in results) / len(results), 6
    )
    avg_opportunity_delta = round(
        sum(r.avg_opportunity_delta for r in results) / len(results), 6
    )

    helped: list[str] = []
    neutral: list[str] = []
    degraded: list[str] = []
    for r in results:
        label = classify_impact(r)
        if label == "helpful":
            helped.append(r.scenario_id)
        elif label == "degrading":
            degraded.append(r.scenario_id)
        else:
            neutral.append(r.scenario_id)

    notes: list[str] = []
    notes.append(f"Aggregated {len(results)} scenario(s).")
    if helped:
        notes.append(f"{len(helped)} scenario(s) helped by context.")
    if degraded:
        notes.append(f"{len(degraded)} scenario(s) degraded by context.")

    return ContextImpactSummary(
        scenario_count=len(results),
        top_1_changed_count=top_1_changed_count,
        top_3_changed_count=top_3_changed_count,
        neutral_context_count=neutral_context_count,
        partial_context_count=partial_context_count,
        fallback_count=fallback_count,
        cache_hit_count=cache_hit_count,
        cache_miss_count=cache_miss_count,
        avg_validity_delta=avg_validity_delta,
        avg_opportunity_delta=avg_opportunity_delta,
        scenarios_helped=helped,
        scenarios_neutral=neutral,
        scenarios_degraded=degraded,
        notes=notes,
    )


def run_batch_analysis(
    scenarios: list[dict],
    config: PipelineConfig | None = None,
) -> tuple[list[ContextImpactResult], ContextImpactSummary]:
    """Run paired analysis for each scenario and compute aggregate summary.

    Each scenario dict must contain ``"scenario_id"``, ``"play_state"``,
    and ``"match_context"`` keys.

    Args:
        scenarios: List of scenario dicts.
        config: Optional pipeline configuration overrides.

    Returns:
        Tuple of (per-scenario results, aggregate summary).
    """
    results: list[ContextImpactResult] = []
    for scenario in scenarios:
        result = run_paired_analysis(
            play_state=scenario["play_state"],
            match_context=scenario["match_context"],
            scenario_id=scenario["scenario_id"],
            config=config,
        )
        results.append(result)

    summary = compute_aggregate_summary(results)
    return results, summary


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------


def save_analysis_json(
    results: list[ContextImpactResult],
    summary: ContextImpactSummary,
    output_path: str,
) -> None:
    """Write analysis results and summary to a JSON file.

    The output contains per-scenario results, aggregate summary, and
    execution metadata.

    Args:
        results: List of per-scenario impact results.
        summary: Aggregate summary across all scenarios.
        output_path: File path to write the JSON output.
    """
    payload = {
        "results": [asdict(r) for r in results],
        "summary": asdict(summary),
        "metadata": {
            "generated_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "scenario_count": len(results),
        },
    }
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def load_analysis_json(path: str) -> dict:
    """Load a previously saved analysis JSON file.

    Args:
        path: File path to the JSON output.

    Returns:
        The parsed dict containing results, summary, and metadata.
    """
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
