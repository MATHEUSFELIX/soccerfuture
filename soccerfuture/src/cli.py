"""CLI entry point for the branch generation pipeline.

Loads a PlayState JSON file, runs the pipeline, and writes the
PipelineReport as formatted JSON to stdout or an output file.

Usage::

    python -m src.cli <play_state.json> [options]
"""

from __future__ import annotations

import argparse
import json
import sys

from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig, run_pipeline
from src.utils.constants import (
    DEFAULT_K,
    DEFAULT_N,
    DEFAULT_OPPORTUNITY_WEIGHT,
    DEFAULT_SEED,
    DEFAULT_VALIDITY_WEIGHT,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Run the branch generation pipeline on a PlayState JSON file.",
    )
    parser.add_argument(
        "play_state_path",
        help="Path to a PlayState JSON file.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=DEFAULT_N,
        help=f"Number of branches to generate (default: {DEFAULT_N}).",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=DEFAULT_K,
        help=f"Number of top branches to keep (default: {DEFAULT_K}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"RNG seed (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--validity-weight",
        type=float,
        default=DEFAULT_VALIDITY_WEIGHT,
        help=f"Validity weight in composite score (default: {DEFAULT_VALIDITY_WEIGHT}).",
    )
    parser.add_argument(
        "--opportunity-weight",
        type=float,
        default=DEFAULT_OPPORTUNITY_WEIGHT,
        help=f"Opportunity weight in composite score (default: {DEFAULT_OPPORTUNITY_WEIGHT}).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write report to this file instead of stdout.",
    )
    return parser


def main() -> None:
    """CLI entry point for the branch generation pipeline."""
    parser = _build_parser()
    args = parser.parse_args()

    # Load JSON file
    try:
        with open(args.play_state_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        print(
            f"Error: File not found: {args.play_state_path}",
            file=sys.stderr,
        )
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(
            f"Error: Invalid JSON in {args.play_state_path}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse into PlayState
    try:
        play_state = dict_to_play_state(raw)
    except (KeyError, TypeError) as exc:
        print(
            f"Error: Invalid PlayState: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build config and run pipeline
    config = PipelineConfig(
        n=args.n,
        k=args.k,
        seed=args.seed,
        validity_weight=args.validity_weight,
        opportunity_weight=args.opportunity_weight,
    )
    report = run_pipeline(play_state, config)

    # Output
    output_json = json.dumps(report.to_dict(), indent=2)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
                f.write("\n")
        except OSError as exc:
            print(
                f"Error: Cannot write to {args.output}: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
