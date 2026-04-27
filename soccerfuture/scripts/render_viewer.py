"""Generate 2D visualizations for the demo pipeline scenarios.

Runs the pipeline on the 3 demo play states and saves PNG images to
output/viewer/. Supports loading a pre-saved PipelineReport JSON via
``--from-json`` and persisting generated reports via ``--save-json``.

Usage:
    python -m scripts.render_viewer
    python -m scripts.render_viewer --from-json output/report.json
    python -m scripts.render_viewer --save-json output/report.json

Exit codes:
    0: All visualizations generated successfully.
    1: Any scenario failed.
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from src.models.play_state import dict_to_play_state
from src.pipeline import run_pipeline
from src.viewer.viewer_2d import render_pipeline_report

DEMO_SCENARIOS: list[str] = [
    "data/play_states/counter_attack_midfield.json",
    "data/play_states/build_up_from_defense.json",
    "data/play_states/set_piece_penalty_area.json",
]

OUTPUT_DIR: str = "output/viewer"


def load_report_from_json(path: str) -> dict:
    """Load a PipelineReport dict from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Dict of the PipelineReport.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the JSON is invalid.
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_report_to_json(report_dict: dict, path: str) -> None:
    """Save a PipelineReport dict as JSON with 2-space indent.

    Args:
        report_dict: Dict of the PipelineReport (via to_dict()).
        path: Output file path.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)


def run_scenario(scenario_file: str) -> dict:
    """Run the pipeline for a scenario and return the report dict.

    Args:
        scenario_file: Path to the PlayState JSON file.

    Returns:
        Dict of the PipelineReport (via to_dict()).
    """
    with open(scenario_file, encoding="utf-8") as f:
        ps_data = json.load(f)
    play_state = dict_to_play_state(ps_data)
    report = run_pipeline(play_state)
    return report.to_dict()


def main() -> None:
    """Entry point: parse arguments, generate visualizations, print summary."""
    parser = argparse.ArgumentParser(
        description="Generate 2D viewer PNGs for demo pipeline scenarios.",
    )
    parser.add_argument(
        "--from-json",
        type=str,
        default=None,
        help="Load a pre-saved PipelineReport JSON instead of running the pipeline.",
    )
    parser.add_argument(
        "--save-json",
        type=str,
        default=None,
        help="Save generated PipelineReport(s) as JSON before rendering.",
    )
    args = parser.parse_args()

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, str]] = []  # (scenario_name, png_path)

    try:
        if args.from_json:
            # Single report mode: load JSON, render, save PNG.
            report_dict = load_report_from_json(args.from_json)
            fig = render_pipeline_report(report_dict)
            png_name = Path(args.from_json).stem + ".png"
            png_path = output_dir / png_name
            fig.savefig(str(png_path), dpi=150, bbox_inches="tight")
            plt.close(fig)
            results.append((Path(args.from_json).name, str(png_path)))
        else:
            # Demo mode: run each scenario through the pipeline.
            for scenario_file in DEMO_SCENARIOS:
                scenario_name = Path(scenario_file).stem
                print(f"Running pipeline on {scenario_name}...")

                report_dict = run_scenario(scenario_file)

                if args.save_json:
                    json_path = Path(args.save_json).parent / f"{scenario_name}.json"
                    save_report_to_json(report_dict, str(json_path))
                    print(f"  Saved JSON: {json_path}")

                fig = render_pipeline_report(report_dict)
                png_path = output_dir / f"{scenario_name}.png"
                fig.savefig(str(png_path), dpi=150, bbox_inches="tight")
                plt.close(fig)
                results.append((scenario_name, str(png_path)))

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Print summary.
    print(f"\n{'='*50}")
    print(f"Viewer output — {len(results)} visualization(s) generated:")
    for name, path in results:
        print(f"  {name} -> {path}")
    print(f"{'='*50}")
    sys.exit(0)


if __name__ == "__main__":
    main()
