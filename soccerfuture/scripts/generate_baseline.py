"""Generate the benchmark manifest from current pipeline output.

Runs the pipeline on all 3 demo scenarios with default configuration
(N=20, K=5, seed=42) and writes data/benchmark_manifest.json.

Usage:
    python -m scripts.generate_baseline

Exit codes:
    0: Success
    1: Any scenario failed to produce a valid PipelineReport
"""

import json
import os
import sys

from src.models.pipeline_report import PipelineReport
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig, run_pipeline
from src.utils.manifest import save_manifest

SCENARIO_FILES: list[str] = [
    "data/play_states/first_and_ten_midfield.json",
    "data/play_states/third_and_short_goal_line.json",
    "data/play_states/second_and_long_after_sack.json",
]

MANIFEST_PATH: str = "data/benchmark_manifest.json"

DEFAULT_CONFIG = PipelineConfig(n=20, k=5, seed=42)


def generate_scenario_entry(
    scenario_file: str, report: PipelineReport
) -> dict:
    """Extract baseline expectations from a PipelineReport.

    Args:
        scenario_file: The scenario file name (basename).
        report: The PipelineReport from running the pipeline.

    Returns:
        Dict with: scenario_file, gating_pass_count,
        top_branch_min_score, bottom_branch_max_score,
        strategy_counts, expected_top_k.
    """
    ranked = report.ranked_branches
    top_branch_min_score = ranked[0].composite_score if ranked else 0.0
    bottom_branch_max_score = ranked[-1].composite_score if ranked else 0.0

    expected_top_k = [
        {
            "branch_id": rb.branch_id,
            "composite_score": rb.composite_score,
        }
        for rb in ranked
    ]

    return {
        "scenario_file": scenario_file,
        "gating_pass_count": report.metadata.get("gating_pass_count", 0),
        "top_branch_min_score": top_branch_min_score,
        "bottom_branch_max_score": bottom_branch_max_score,
        "strategy_counts": report.metadata.get("strategy_counts", {}),
        "expected_top_k": expected_top_k,
    }


def print_summary(scenarios: list[dict]) -> None:
    """Print a human-readable summary of the generated baseline.

    Args:
        scenarios: List of scenario entry dicts from the manifest.
    """
    for entry in scenarios:
        name = entry["scenario_file"]
        gating = entry["gating_pass_count"]
        top_k = entry["expected_top_k"]
        strategy_counts = entry["strategy_counts"]

        print(f"\n=== {name} ===")
        print(f"  Gating pass count: {gating}")

        if top_k:
            top = top_k[0]
            print(
                f"  Top branch: {top['branch_id']} "
                f"(score={top['composite_score']:.4f})"
            )
        else:
            print("  Top branch: (none)")

        print("  Strategy distribution:")
        for strategy, count in sorted(strategy_counts.items()):
            print(f"    {strategy}: {count}")


def main() -> None:
    """Run pipeline on all demo scenarios and write manifest."""
    scenarios: list[dict] = []

    for scenario_path in SCENARIO_FILES:
        scenario_name = os.path.basename(scenario_path)
        print(f"Running pipeline on {scenario_name}...")

        try:
            with open(scenario_path, encoding="utf-8") as f:
                ps = dict_to_play_state(json.load(f))
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
            print(f"ERROR: Failed to load {scenario_path}: {exc}", file=sys.stderr)
            sys.exit(1)

        report = run_pipeline(ps, DEFAULT_CONFIG)

        if report.errors and not report.ranked_branches:
            print(
                f"ERROR: Pipeline failed for {scenario_name}: "
                f"{report.errors}",
                file=sys.stderr,
            )
            sys.exit(1)

        entry = generate_scenario_entry(scenario_name, report)
        scenarios.append(entry)

    manifest = {
        "version": "v1.0-baseline",
        "pipeline_config": {
            "n": DEFAULT_CONFIG.n,
            "k": DEFAULT_CONFIG.k,
            "seed": DEFAULT_CONFIG.seed,
            "validity_weight": DEFAULT_CONFIG.validity_weight,
            "opportunity_weight": DEFAULT_CONFIG.opportunity_weight,
        },
        "scenarios": scenarios,
    }

    try:
        save_manifest(manifest, MANIFEST_PATH)
    except OSError as exc:
        print(f"ERROR: Failed to write manifest: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\nManifest written to {MANIFEST_PATH}")
    print_summary(scenarios)
    sys.exit(0)


if __name__ == "__main__":
    main()
