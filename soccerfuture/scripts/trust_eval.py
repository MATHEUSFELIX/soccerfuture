"""CLI entry points for human evaluation, robustness analysis, and trust reporting.

Subcommands:
  human-pack   — Generate a human evaluation pack from play state scenarios.
  robustness   — Run robustness analysis across all degradation strategies.
  trust-report — Generate a consolidated Markdown trust report from evaluation JSONs.

Usage:
    python scripts/trust_eval.py human-pack --output output/human_eval_pack.json
    python scripts/trust_eval.py robustness --output output/robustness.json
    python scripts/trust_eval.py trust-report --human-eval output/human_eval.json \
        --robustness output/robustness.json --context-impact output/context_impact.json \
        --output output/trust_report.md
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.human_eval_pack import generate_eval_pack, save_eval_pack
from src.evaluation.robustness_metrics import (
    compute_robustness_summary,
    save_robustness_json,
)
from src.evaluation.robustness_suite import (
    DEGRADATION_STRATEGIES,
    run_robustness_batch,
)
from src.evaluation.trust_report import save_trust_report
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig

PLAY_STATES_DIR = os.path.join("data", "play_states")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_play_states() -> list[dict]:
    """Load all play state scenarios from data/play_states/.

    Returns:
        List of scenario dicts with scenario_id, play_state_file,
        and play_state keys.

    Raises:
        FileNotFoundError: If the play_states directory does not exist.
    """
    if not os.path.isdir(PLAY_STATES_DIR):
        raise FileNotFoundError(
            f"Play states directory not found: {PLAY_STATES_DIR}"
        )

    scenarios: list[dict] = []
    for filename in sorted(os.listdir(PLAY_STATES_DIR)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(PLAY_STATES_DIR, filename)
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        play_state = dict_to_play_state(raw)
        scenario_id = filename.replace(".json", "")
        scenarios.append({
            "scenario_id": scenario_id,
            "play_state_file": filename,
            "play_state": play_state,
        })
    return scenarios


def _ensure_output_dir(output_path: str) -> None:
    """Create parent directories for an output path if needed.

    Args:
        output_path: File path whose parent directory should exist.
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _load_json_optional(path: str | None) -> dict | None:
    """Load a JSON file if the path is provided and the file exists.

    Args:
        path: File path or None.

    Returns:
        Parsed dict, or None if path is None or file does not exist.
    """
    if path is None or not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_human_pack(args: argparse.Namespace) -> None:
    """Execute the 'human-pack' subcommand.

    Loads all play states, generates an evaluation pack, and saves JSON.

    Args:
        args: Parsed CLI arguments with ``output`` path.
    """
    print("Loading play state scenarios from data/play_states/ ...")
    try:
        scenarios = _load_play_states()
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not scenarios:
        print("Error: No play state scenarios found.", file=sys.stderr)
        sys.exit(1)

    config = PipelineConfig(n=15, k=3, seed=42)
    print(
        f"Found {len(scenarios)} scenario(s). "
        f"Generating eval pack (n={config.n}, k={config.k}, seed={config.seed}) ..."
    )

    try:
        protocol = generate_eval_pack(scenarios, config=config)
    except Exception as exc:
        print(f"Error generating eval pack: {exc}", file=sys.stderr)
        sys.exit(1)

    _ensure_output_dir(args.output)
    save_eval_pack(protocol, args.output)

    print(f"Eval pack saved to {args.output}")
    print(f"  Protocol ID: {protocol.protocol_id}")
    print(f"  Scenarios: {len(protocol.scenarios)}")
    print(
        f"  Questions per scenario: "
        f"{len(protocol.scenarios[0].questions) if protocol.scenarios else 0}"
    )


def cmd_robustness(args: argparse.Namespace) -> None:
    """Execute the 'robustness' subcommand.

    Loads all play states, runs robustness batch with all strategies,
    computes summary, and saves JSON.

    Args:
        args: Parsed CLI arguments with ``output`` path.
    """
    print("Loading play state scenarios from data/play_states/ ...")
    try:
        scenarios = _load_play_states()
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not scenarios:
        print("Error: No play state scenarios found.", file=sys.stderr)
        sys.exit(1)

    config = PipelineConfig(n=15, k=3, seed=42)
    strategies = list(DEGRADATION_STRATEGIES.keys())
    print(
        f"Found {len(scenarios)} scenario(s). "
        f"Running robustness batch with {len(strategies)} strategies "
        f"(n={config.n}, k={config.k}, seed={config.seed}) ..."
    )

    try:
        results = run_robustness_batch(
            scenarios, strategies=strategies, config=config,
        )
    except Exception as exc:
        print(f"Error during robustness batch: {exc}", file=sys.stderr)
        sys.exit(1)

    summary = compute_robustness_summary(results)

    _ensure_output_dir(args.output)
    save_robustness_json(results, summary, args.output)

    print(f"Robustness analysis saved to {args.output}")
    print(f"  Total runs: {summary.total_runs}")
    print(f"  Robust: {summary.robust_count}")
    print(f"  Sensitive: {summary.sensitive_count}")
    print(f"  Fragile: {summary.fragile_count}")
    print(f"  Avg validity delta: {summary.avg_validity_delta}")
    print(f"  Avg opportunity delta: {summary.avg_opportunity_delta}")


def cmd_trust_report(args: argparse.Namespace) -> None:
    """Execute the 'trust-report' subcommand.

    Loads each input JSON (all optional), generates a consolidated
    Markdown trust report, and saves it.

    Args:
        args: Parsed CLI arguments with optional input paths and ``output``.
    """
    human_eval_data = _load_json_optional(args.human_eval)
    robustness_data = _load_json_optional(args.robustness)
    context_impact_data = _load_json_optional(args.context_impact)

    loaded: list[str] = []
    skipped: list[str] = []
    for name, data in [
        ("human-eval", human_eval_data),
        ("robustness", robustness_data),
        ("context-impact", context_impact_data),
    ]:
        if data is not None:
            loaded.append(name)
        else:
            skipped.append(name)

    if loaded:
        print(f"Loaded streams: {', '.join(loaded)}")
    if skipped:
        print(f"Skipped (not provided or missing): {', '.join(skipped)}")

    _ensure_output_dir(args.output)
    save_trust_report(
        human_eval_data=human_eval_data,
        robustness_data=robustness_data,
        context_impact_data=context_impact_data,
        output_path=args.output,
    )

    print(f"Trust report saved to {args.output}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            "Trust evaluation CLI for human eval pack generation, "
            "robustness analysis, and consolidated trust reporting."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # --- human-pack ---
    hp_parser = subparsers.add_parser(
        "human-pack",
        help="Generate a human evaluation pack from play state scenarios.",
    )
    hp_parser.add_argument(
        "--output",
        required=True,
        help="Path to write the JSON evaluation pack.",
    )
    hp_parser.set_defaults(func=cmd_human_pack)

    # --- robustness ---
    rob_parser = subparsers.add_parser(
        "robustness",
        help="Run robustness analysis across all degradation strategies.",
    )
    rob_parser.add_argument(
        "--output",
        required=True,
        help="Path to write the JSON robustness analysis.",
    )
    rob_parser.set_defaults(func=cmd_robustness)

    # --- trust-report ---
    tr_parser = subparsers.add_parser(
        "trust-report",
        help="Generate a consolidated Markdown trust report.",
    )
    tr_parser.add_argument(
        "--human-eval",
        default=None,
        help="Path to human evaluation summary JSON (optional).",
    )
    tr_parser.add_argument(
        "--robustness",
        default=None,
        help="Path to robustness analysis JSON (optional).",
    )
    tr_parser.add_argument(
        "--context-impact",
        default=None,
        help="Path to context impact analysis JSON (optional).",
    )
    tr_parser.add_argument(
        "--output",
        required=True,
        help="Path to write the Markdown trust report.",
    )
    tr_parser.set_defaults(func=cmd_trust_report)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
