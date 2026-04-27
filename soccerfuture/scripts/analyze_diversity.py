"""Analyze generator diversity across demo scenarios.

Runs the pipeline on all 3 demo scenarios and produces a human-readable
report covering strategy distribution, entropy, dominance, and discard rates.

Usage:
    python -m scripts.analyze_diversity

Exit codes:
    0: Success
    1: Any scenario failed to produce a valid PipelineReport
"""

import json
import math
import os
import sys

from src.models.pipeline_report import PipelineReport
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig, run_pipeline

SCENARIO_FILES: list[str] = [
    "data/play_states/first_and_ten_midfield.json",
    "data/play_states/third_and_short_goal_line.json",
    "data/play_states/second_and_long_after_sack.json",
]

DEFAULT_CONFIG = PipelineConfig(n=20, k=5, seed=42)


DOMINANCE_WARNING_THRESHOLD: float = 80.0


def compute_entropy(counts: dict[str, int]) -> float:
    """Compute Shannon entropy over a distribution of counts.

    Args:
        counts: Mapping of category to count.

    Returns:
        Entropy in bits. Returns 0.0 for empty or single-category
        distributions.
    """
    total = sum(counts.values())
    if total <= 0:
        return 0.0

    non_zero = [c for c in counts.values() if c > 0]
    if len(non_zero) <= 1:
        return 0.0

    entropy = 0.0
    for count in non_zero:
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def compute_strategy_dominance(counts: dict[str, int]) -> float:
    """Compute the percentage of the most dominant strategy.

    Args:
        counts: Mapping of strategy to count in top-K.

    Returns:
        Dominance percentage (0-100). Returns 0.0 for empty distributions.
    """
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    max_count = max(counts.values())
    return (max_count / total) * 100


def analyze_scenario(scenario_file: str, report: PipelineReport) -> dict:
    """Compute diversity metrics for a single scenario.

    Args:
        scenario_file: Basename of the scenario file.
        report: PipelineReport from running the pipeline.

    Returns:
        Dict with keys: scenario_file, unique_passing_count,
        strategy_distribution, discard_rate, entropy,
        strategy_dominance, dominant_strategy, avg_score_by_strategy,
        top_k_branches.
    """
    ranked = report.ranked_branches
    n_generated = report.metadata.get("n_generated", 0)

    # Count strategies in top-K
    strategy_counts: dict[str, int] = {}
    for rb in ranked:
        strategy = rb.branch.get("strategy", "unknown")
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

    entropy = compute_entropy(strategy_counts)
    dominance = compute_strategy_dominance(strategy_counts)

    # Identify dominant strategy
    dominant_strategy = ""
    if strategy_counts:
        dominant_strategy = max(strategy_counts, key=lambda s: strategy_counts[s])

    # Discard rate: branches not in ranked_branches out of total generated
    n_ranked = len(report.ranked_branches)
    discard_rate = 0.0
    if n_generated > 0:
        discard_rate = ((n_generated - n_ranked) / n_generated) * 100

    # Unique passing count (gating)
    unique_passing_count = report.metadata.get("gating_pass_count", 0)

    # Avg score by strategy from telemetry (across ALL evaluated branches)
    telemetry = report.metadata.get("telemetry", {})
    avg_score_by_strategy = telemetry.get("avg_score_by_strategy", {})

    # Build top-K branch info for display
    top_k_branches = []
    for rb in ranked:
        top_k_branches.append({
            "branch_id": rb.branch_id,
            "composite_score": rb.composite_score,
            "strategy": rb.branch.get("strategy", "unknown"),
            "validity_score": rb.evaluation_report.get("validity_score", 0.0),
        })

    return {
        "scenario_file": scenario_file,
        "unique_passing_count": unique_passing_count,
        "strategy_distribution": strategy_counts,
        "discard_rate": discard_rate,
        "entropy": entropy,
        "strategy_dominance": dominance,
        "dominant_strategy": dominant_strategy,
        "avg_score_by_strategy": avg_score_by_strategy,
        "top_k_branches": top_k_branches,
    }


def print_report(analyses: list[dict]) -> None:
    """Print the consolidated diversity report to stdout.

    Prints per-scenario tables showing top-K branches, strategy
    distribution, and metrics, followed by a cross-scenario summary.

    Args:
        analyses: List of analysis dicts from analyze_scenario.
    """
    dominance_warnings: list[str] = []

    for analysis in analyses:
        name = analysis["scenario_file"]
        print(f"\n=== Scenario: {name} ===")

        # Top-K Branches table
        print("\nTop-K Branches:")
        print(f"  {'Branch ID':<14}{'Score':<10}{'Strategy':<24}{'Validity'}")
        for branch in analysis["top_k_branches"]:
            print(
                f"  {branch['branch_id']:<14}"
                f"{branch['composite_score']:<10.4f}"
                f"{branch['strategy']:<24}"
                f"{branch['validity_score']:.4f}"
            )

        # Strategy Distribution table
        print("\nStrategy Distribution:")
        print(f"  {'Strategy':<24}{'Count':<10}{'Avg Score'}")
        avg_scores = analysis["avg_score_by_strategy"]
        for strategy, count in sorted(analysis["strategy_distribution"].items()):
            avg = avg_scores.get(strategy, 0.0)
            print(f"  {strategy:<24}{count:<10}{avg:.4f}")

        # Metrics
        print("\nMetrics:")
        print(f"  Unique Passing Count: {analysis['unique_passing_count']}")
        print(f"  Discard Rate: {analysis['discard_rate']:.1f}%")
        print(f"  Top-K Entropy: {analysis['entropy']:.2f} bits")
        dom = analysis["strategy_dominance"]
        dom_strat = analysis["dominant_strategy"]
        print(f"  Strategy Dominance: {dom:.1f}% ({dom_strat})")

        if dom > DOMINANCE_WARNING_THRESHOLD:
            warning = (
                f"{name}: Strategy dominance {dom:.1f}% "
                f"({dom_strat}) exceeds {DOMINANCE_WARNING_THRESHOLD:.0f}%"
            )
            dominance_warnings.append(warning)
            print(f"  ⚠ WARNING: {warning}")

    # Cross-scenario summary
    print("\n=== Cross-Scenario Summary ===")
    if analyses:
        total_discard = sum(a["discard_rate"] for a in analyses) / len(analyses)
        print(f"  Overall Discard Rate: {total_discard:.1f}%")
    else:
        print("  Overall Discard Rate: N/A")

    if dominance_warnings:
        print("  Dominance Warnings:")
        for w in dominance_warnings:
            print(f"    ⚠ {w}")
    else:
        print("  Dominance Warnings: None")


def main() -> None:
    """Run pipeline on all demo scenarios and print diversity report."""
    analyses: list[dict] = []

    for scenario_path in SCENARIO_FILES:
        scenario_name = os.path.basename(scenario_path)
        print(f"Running pipeline on {scenario_name}...")

        try:
            with open(scenario_path, encoding="utf-8") as f:
                ps = dict_to_play_state(json.load(f))
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
            print(
                f"ERROR: Failed to load {scenario_path}: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

        report = run_pipeline(ps, DEFAULT_CONFIG)

        if report.errors and not report.ranked_branches:
            print(
                f"ERROR: Pipeline failed for {scenario_name}: "
                f"{report.errors}",
                file=sys.stderr,
            )
            sys.exit(1)

        analysis = analyze_scenario(scenario_name, report)
        analyses.append(analysis)

    print_report(analyses)
    sys.exit(0)


if __name__ == "__main__":
    main()
