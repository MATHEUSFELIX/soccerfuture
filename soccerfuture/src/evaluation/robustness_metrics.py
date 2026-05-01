"""Robustness classification and aggregate metrics.

Classifies individual robustness results as robust, sensitive, or fragile,
and computes aggregate summaries across multiple results. Includes JSON
persistence for saving and loading robustness analysis outputs.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field

from src.evaluation.robustness_suite import RobustnessResult

# ---------------------------------------------------------------------------
# Classification constants
# ---------------------------------------------------------------------------

ROBUST_VALIDITY_EPSILON: float = 0.03
ROBUST_OPPORTUNITY_EPSILON: float = 0.03
FRAGILE_VALIDITY_THRESHOLD: float = -0.10
FRAGILE_OPPORTUNITY_THRESHOLD: float = -0.10

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_robustness(result: RobustnessResult) -> str:
    """Classify a robustness result as robust, sensitive, or fragile.

    Classification rules (evaluated in order):
      - **fragile**: avg_validity_delta < FRAGILE_VALIDITY_THRESHOLD
            OR avg_opportunity_delta < FRAGILE_OPPORTUNITY_THRESHOLD
      - **robust**: abs(avg_validity_delta) < ROBUST_VALIDITY_EPSILON
            AND abs(avg_opportunity_delta) < ROBUST_OPPORTUNITY_EPSILON
            AND NOT top_1_changed
      - **sensitive**: everything else

    Args:
        result: A single robustness comparison result.

    Returns:
        One of ``"robust"``, ``"sensitive"``, or ``"fragile"``.
    """
    if (
        result.avg_validity_delta < FRAGILE_VALIDITY_THRESHOLD
        or result.avg_opportunity_delta < FRAGILE_OPPORTUNITY_THRESHOLD
    ):
        return "fragile"
    if (
        abs(result.avg_validity_delta) < ROBUST_VALIDITY_EPSILON
        and abs(result.avg_opportunity_delta) < ROBUST_OPPORTUNITY_EPSILON
        and not result.top_1_changed
    ):
        return "robust"
    return "sensitive"


# ---------------------------------------------------------------------------
# Aggregate summary
# ---------------------------------------------------------------------------


@dataclass
class RobustnessSummary:
    """Aggregate metrics across multiple robustness results.

    Attributes:
        scenario_count: Number of distinct scenarios evaluated.
        strategy_count: Number of distinct strategies applied.
        total_runs: Total number of (scenario, strategy) pairs.
        robust_count: Number of results classified as robust.
        sensitive_count: Number of results classified as sensitive.
        fragile_count: Number of results classified as fragile.
        avg_validity_delta: Mean validity delta across all results.
        avg_opportunity_delta: Mean opportunity delta across all results.
        avg_gating_pass_delta: Mean gating pass delta across all results.
        per_strategy_summary: Per-strategy breakdown of classification counts.
        notes: Human-readable observations about the aggregate.
    """

    scenario_count: int
    strategy_count: int
    total_runs: int
    robust_count: int
    sensitive_count: int
    fragile_count: int
    avg_validity_delta: float
    avg_opportunity_delta: float
    avg_gating_pass_delta: float
    per_strategy_summary: dict[str, dict] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def compute_robustness_summary(
    results: list[RobustnessResult],
) -> RobustnessSummary:
    """Compute aggregate robustness metrics from a list of results.

    Args:
        results: List of per-(scenario, strategy) robustness results.

    Returns:
        A RobustnessSummary with counts, averages, and per-strategy breakdown.
    """
    if not results:
        return RobustnessSummary(
            scenario_count=0,
            strategy_count=0,
            total_runs=0,
            robust_count=0,
            sensitive_count=0,
            fragile_count=0,
            avg_validity_delta=0.0,
            avg_opportunity_delta=0.0,
            avg_gating_pass_delta=0.0,
            per_strategy_summary={},
            notes=["No results to aggregate."],
        )

    # Classify each result
    classifications: list[str] = [classify_robustness(r) for r in results]

    robust_count = classifications.count("robust")
    sensitive_count = classifications.count("sensitive")
    fragile_count = classifications.count("fragile")

    # Distinct scenarios and strategies
    scenario_ids = {r.scenario_id for r in results}
    strategy_names = {r.strategy for r in results}

    # Averages
    total = len(results)
    avg_validity_delta = round(
        sum(r.avg_validity_delta for r in results) / total, 6
    )
    avg_opportunity_delta = round(
        sum(r.avg_opportunity_delta for r in results) / total, 6
    )
    avg_gating_pass_delta = round(
        sum(r.gating_pass_delta for r in results) / total, 6
    )

    # Per-strategy breakdown
    per_strategy: dict[str, dict] = {}
    for strategy in sorted(strategy_names):
        strategy_results = [r for r in results if r.strategy == strategy]
        strategy_classes = [classify_robustness(r) for r in strategy_results]
        per_strategy[strategy] = {
            "robust": strategy_classes.count("robust"),
            "sensitive": strategy_classes.count("sensitive"),
            "fragile": strategy_classes.count("fragile"),
        }

    # Notes
    notes: list[str] = [
        f"Aggregated {total} result(s) across {len(scenario_ids)} scenario(s) "
        f"and {len(strategy_names)} strategy(ies).",
    ]
    if fragile_count > 0:
        notes.append(f"{fragile_count} result(s) classified as fragile.")
    if robust_count == total:
        notes.append("All results are robust.")

    return RobustnessSummary(
        scenario_count=len(scenario_ids),
        strategy_count=len(strategy_names),
        total_runs=total,
        robust_count=robust_count,
        sensitive_count=sensitive_count,
        fragile_count=fragile_count,
        avg_validity_delta=avg_validity_delta,
        avg_opportunity_delta=avg_opportunity_delta,
        avg_gating_pass_delta=avg_gating_pass_delta,
        per_strategy_summary=per_strategy,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------


def save_robustness_json(
    results: list[RobustnessResult],
    summary: RobustnessSummary,
    output_path: str,
) -> None:
    """Write robustness results and summary to a JSON file.

    The output contains per-result data with classification labels,
    aggregate summary, and execution metadata.

    Args:
        results: List of per-(scenario, strategy) robustness results.
        summary: Aggregate summary across all results.
        output_path: File path to write the JSON output.
    """
    classified_results = []
    for r in results:
        entry = asdict(r)
        entry["classification"] = classify_robustness(r)
        classified_results.append(entry)

    payload = {
        "results": classified_results,
        "summary": asdict(summary),
        "metadata": {
            "generated_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "result_count": len(results),
        },
    }
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def load_robustness_json(path: str) -> dict:
    """Load a previously saved robustness JSON file.

    Args:
        path: File path to the JSON output.

    Returns:
        The parsed dict containing results, summary, and metadata.
    """
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
