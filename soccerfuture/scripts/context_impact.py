"""CLI entry point for context impact analysis.

Subcommands:
  analyze  — Run paired pipeline analysis on fixture scenarios and save JSON.
  report   — Generate a Markdown report from a JSON analysis file.

Usage:
    python scripts/context_impact.py analyze --output output/context_impact.json
    python scripts/context_impact.py report --input output/context_impact.json --output output/context_impact_report.md
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.context_impact_analysis import (
    run_batch_analysis,
    save_analysis_json,
    load_analysis_json,
)
from src.evaluation.context_impact_report import (
    generate_markdown_report,
    save_markdown_report,
)
from src.integrations.soccerdata_adapter import get_match_context
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig

PLAY_STATES_DIR = os.path.join("data", "play_states")


def _load_scenarios() -> list[dict]:
    """Load all play state scenarios from data/play_states/.

    Returns:
        List of scenario dicts with scenario_id, play_state, and match_context.

    Raises:
        FileNotFoundError: If the play_states directory does not exist.
    """
    if not os.path.isdir(PLAY_STATES_DIR):
        raise FileNotFoundError(f"Play states directory not found: {PLAY_STATES_DIR}")

    scenarios: list[dict] = []
    for filename in sorted(os.listdir(PLAY_STATES_DIR)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(PLAY_STATES_DIR, filename)
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        play_state = dict_to_play_state(raw)
        match_context = get_match_context("TeamA", "TeamB", use_cache=False)
        scenario_id = filename.replace(".json", "")
        scenarios.append({
            "scenario_id": scenario_id,
            "play_state": play_state,
            "match_context": match_context,
        })
    return scenarios


def cmd_analyze(args: argparse.Namespace) -> None:
    """Execute the 'analyze' subcommand.

    Args:
        args: Parsed CLI arguments with ``output`` path.
    """
    print("Loading play state scenarios from data/play_states/ ...")
    try:
        scenarios = _load_scenarios()
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not scenarios:
        print("Error: No play state scenarios found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(scenarios)} scenario(s). Running batch analysis ...")
    config = PipelineConfig(n=15, k=3, seed=42)

    try:
        results, summary = run_batch_analysis(scenarios, config=config)
    except Exception as exc:
        print(f"Error during analysis: {exc}", file=sys.stderr)
        sys.exit(1)

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    save_analysis_json(results, summary, args.output)
    print(f"Analysis saved to {args.output}")
    print(f"  Scenarios: {summary.scenario_count}")
    print(f"  Helped: {len(summary.scenarios_helped)}")
    print(f"  Neutral: {len(summary.scenarios_neutral)}")
    print(f"  Degraded: {len(summary.scenarios_degraded)}")


def cmd_report(args: argparse.Namespace) -> None:
    """Execute the 'report' subcommand.

    Args:
        args: Parsed CLI arguments with ``input`` and ``output`` paths.
    """
    if not os.path.isfile(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        analysis_data = load_analysis_json(args.input)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error loading analysis JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    save_markdown_report(analysis_data, args.output)
    print(f"Markdown report saved to {args.output}")


def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        description="Context impact analysis CLI for paired pipeline evaluation.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # --- analyze ---
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run paired analysis on fixture scenarios and save JSON output.",
    )
    analyze_parser.add_argument(
        "--output",
        required=True,
        help="Path to write the JSON analysis output.",
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    # --- report ---
    report_parser = subparsers.add_parser(
        "report",
        help="Generate a Markdown report from a JSON analysis file.",
    )
    report_parser.add_argument(
        "--input",
        required=True,
        help="Path to the JSON analysis input file.",
    )
    report_parser.add_argument(
        "--output",
        required=True,
        help="Path to write the Markdown report.",
    )
    report_parser.set_defaults(func=cmd_report)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
