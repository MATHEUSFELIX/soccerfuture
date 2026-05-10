"""Reusable command implementations for the CLI.

Each function performs a workflow action and returns structured results
suitable for rendering. These are called by both the interactive menu
and the direct typer commands.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from src.cli_app.healthcheck import HealthCheckResult, run_healthcheck


@dataclass
class CommandResult:
    """Result of a CLI command execution.

    Attributes:
        success: Whether the command succeeded.
        scenario_id: Scenario processed, if applicable.
        status: Overall status string.
        steps: List of step status dicts.
        artifacts: Mapping of artifact name to path.
        error_message: Error message if failed.
        suggestion: Suggested fix for the error.
    """

    success: bool
    scenario_id: str = ""
    status: str = ""
    steps: list[dict] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    error_message: str = ""
    suggestion: str = ""


def cmd_run_demo(output_root: str = "output/runs") -> CommandResult:
    """Run the official demo scenario.

    Uses the first available play state as the demo input.

    Args:
        output_root: Root directory for output bundles.

    Returns:
        CommandResult with execution details.
    """
    from src.models.play_state import dict_to_play_state
    from src.pipeline import PipelineConfig
    from src.workflows.analyst_workflow_runner import run_analyst_workflow

    ps_dir = "data/play_states"
    if not os.path.isdir(ps_dir):
        return CommandResult(
            success=False,
            error_message="Play states directory not found",
            suggestion="Ensure data/play_states/ exists with JSON files",
        )

    files = sorted(f for f in os.listdir(ps_dir) if f.endswith(".json"))
    if not files:
        return CommandResult(
            success=False,
            error_message="No play state files found",
            suggestion="Add JSON play state files to data/play_states/",
        )

    # Use first file as demo
    demo_file = os.path.join(ps_dir, files[0])
    try:
        with open(demo_file, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        play_state = dict_to_play_state(raw)
    except Exception as exc:
        return CommandResult(
            success=False,
            error_message=f"Failed to load demo input: {exc}",
            suggestion=f"Check file: {demo_file}",
        )

    scenario_id = files[0].replace(".json", "")
    config = PipelineConfig(n=15, k=3, seed=42)

    try:
        manifest = run_analyst_workflow(
            scenario_id=scenario_id,
            play_state=play_state,
            output_root=output_root,
            pipeline_config=config,
        )
    except Exception as exc:
        return CommandResult(
            success=False,
            scenario_id=scenario_id,
            error_message=f"Workflow failed: {exc}",
        )

    steps = [
        {"name": s.step_name, "status": s.status}
        for s in manifest.step_statuses
    ]
    bundle_path = os.path.join(output_root, scenario_id)
    artifacts = {k: os.path.join(bundle_path, v) for k, v in manifest.artifact_references.items()}

    return CommandResult(
        success=manifest.overall_status != "failed",
        scenario_id=scenario_id,
        status=manifest.overall_status,
        steps=steps,
        artifacts=artifacts,
    )


def cmd_run_scenario(
    input_path: str,
    output_root: str = "output/runs",
    scenario_id: str | None = None,
) -> CommandResult:
    """Run a single scenario from a play state JSON file.

    Args:
        input_path: Path to the play state JSON file.
        output_root: Root directory for output bundles.
        scenario_id: Optional override for scenario ID.

    Returns:
        CommandResult with execution details.
    """
    from src.models.play_state import dict_to_play_state
    from src.pipeline import PipelineConfig
    from src.workflows.analyst_workflow_runner import run_analyst_workflow

    if not os.path.isfile(input_path):
        return CommandResult(
            success=False,
            error_message=f"Input file not found: {input_path}",
            suggestion="Provide a valid path to a PlayState JSON file",
        )

    try:
        with open(input_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        play_state = dict_to_play_state(raw)
    except Exception as exc:
        return CommandResult(
            success=False,
            error_message=f"Failed to load input: {exc}",
            suggestion=f"Check file format: {input_path}",
        )

    sid = scenario_id or os.path.basename(input_path).replace(".json", "")
    config = PipelineConfig(n=15, k=3, seed=42)

    try:
        manifest = run_analyst_workflow(
            scenario_id=sid,
            play_state=play_state,
            output_root=output_root,
            pipeline_config=config,
        )
    except Exception as exc:
        return CommandResult(
            success=False,
            scenario_id=sid,
            error_message=f"Workflow failed: {exc}",
        )

    steps = [{"name": s.step_name, "status": s.status} for s in manifest.step_statuses]
    bundle_path = os.path.join(output_root, sid)
    artifacts = {k: os.path.join(bundle_path, v) for k, v in manifest.artifact_references.items()}

    return CommandResult(
        success=manifest.overall_status != "failed",
        scenario_id=sid,
        status=manifest.overall_status,
        steps=steps,
        artifacts=artifacts,
    )


def cmd_healthcheck() -> HealthCheckResult:
    """Run system health check."""
    return run_healthcheck()


def cmd_list_runs(output_root: str = "output/runs") -> list[dict]:
    """List available runs.

    Args:
        output_root: Root directory for bundles.

    Returns:
        List of run summary dicts.
    """
    if not os.path.isdir(output_root):
        return []

    runs: list[dict] = []
    for entry in sorted(os.listdir(output_root)):
        entry_path = os.path.join(output_root, entry)
        if not os.path.isdir(entry_path):
            continue
        status_path = os.path.join(entry_path, "run_status.json")
        if os.path.isfile(status_path):
            try:
                with open(status_path) as fh:
                    data = json.load(fh)
                runs.append({
                    "scenario_id": data.get("scenario_id", entry),
                    "status": data.get("overall_status", "unknown"),
                    "source_type": data.get("source_type", "unknown"),
                })
            except (json.JSONDecodeError, OSError):
                runs.append({"scenario_id": entry, "status": "error", "source_type": "?"})

    return runs


def cmd_generate_review_site(
    runs_root: str = "output/runs",
    output_dir: str = "output/review_site",
) -> CommandResult:
    """Generate the static review site.

    Args:
        runs_root: Root directory with scenario bundles.
        output_dir: Directory to write HTML files.

    Returns:
        CommandResult with generated file paths.
    """
    from src.ui.review_app import generate_review_site

    try:
        files = generate_review_site(runs_root, output_dir)
    except Exception as exc:
        return CommandResult(
            success=False,
            error_message=f"Review site generation failed: {exc}",
        )

    artifacts = {f"page_{i}": f for i, f in enumerate(files)}
    return CommandResult(
        success=True,
        status="success",
        artifacts=artifacts,
    )
