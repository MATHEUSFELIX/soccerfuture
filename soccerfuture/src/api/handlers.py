"""API handler functions.

Pure functions that process API requests and return responses.
Can be wired to any web framework (Flask, FastAPI, etc.) or
called directly in tests.
"""

from __future__ import annotations

import json
import os

from src.api.schemas import (
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
    RunStatusResponse,
    WorkflowSubmitRequest,
    WorkflowSubmitResponse,
)
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig
from src.workflows.analyst_workflow_runner import run_analyst_workflow


DEFAULT_OUTPUT_ROOT = "output/runs"


def handle_workflow_submit(
    request: WorkflowSubmitRequest,
    output_root: str = DEFAULT_OUTPUT_ROOT,
) -> WorkflowSubmitResponse:
    """Handle a workflow submission request.

    Runs the full analyst workflow for the given scenario.

    Args:
        request: The workflow submission request.
        output_root: Root directory for bundle output.

    Returns:
        A WorkflowSubmitResponse with execution results.
    """
    try:
        play_state = dict_to_play_state(request.play_state)
    except (KeyError, TypeError, ValueError) as exc:
        return WorkflowSubmitResponse(
            scenario_id=request.scenario_id,
            status="failed",
            errors=[f"Invalid play_state: {exc}"],
        )

    config = None
    if request.pipeline_config:
        config = PipelineConfig(
            n=request.pipeline_config.get("n", 20),
            k=request.pipeline_config.get("k", 5),
            seed=request.pipeline_config.get("seed", 42),
        )

    try:
        manifest = run_analyst_workflow(
            scenario_id=request.scenario_id,
            play_state=play_state,
            source_type=request.source_type,
            output_root=output_root,
            pipeline_config=config,
        )
    except Exception as exc:
        return WorkflowSubmitResponse(
            scenario_id=request.scenario_id,
            status="failed",
            errors=[str(exc)],
        )

    bundle_path = os.path.join(output_root, request.scenario_id)
    return WorkflowSubmitResponse(
        scenario_id=request.scenario_id,
        status=manifest.overall_status,
        bundle_path=bundle_path,
        errors=[],
    )


def handle_run_status(
    scenario_id: str,
    output_root: str = DEFAULT_OUTPUT_ROOT,
) -> RunStatusResponse:
    """Handle a run status query.

    Reads the run_status.json from the scenario bundle.

    Args:
        scenario_id: The scenario to query.
        output_root: Root directory for bundles.

    Returns:
        A RunStatusResponse with status and artifact references.
    """
    status_path = os.path.join(output_root, scenario_id, "run_status.json")
    if not os.path.isfile(status_path):
        return RunStatusResponse(
            scenario_id=scenario_id,
            overall_status="not_found",
        )

    try:
        with open(status_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return RunStatusResponse(
            scenario_id=scenario_id,
            overall_status="error",
        )

    return RunStatusResponse(
        scenario_id=scenario_id,
        overall_status=data.get("overall_status", "unknown"),
        step_statuses=data.get("step_statuses", []),
        artifact_references=data.get("artifact_references", {}),
    )


def handle_feedback_submit(
    request: FeedbackSubmitRequest,
    feedback_dir: str = "output/feedback",
) -> FeedbackSubmitResponse:
    """Handle a feedback submission request.

    Persists the feedback record as a JSON file.

    Args:
        request: The feedback submission request.
        feedback_dir: Directory to store feedback files.

    Returns:
        A FeedbackSubmitResponse indicating acceptance.
    """
    os.makedirs(feedback_dir, exist_ok=True)

    filename = f"{request.scenario_id}_{request.reviewer_id}.json"
    filepath = os.path.join(feedback_dir, filename)

    record = {
        "scenario_id": request.scenario_id,
        "reviewer_id": request.reviewer_id,
        **request.feedback,
    }

    try:
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
    except OSError as exc:
        return FeedbackSubmitResponse(
            scenario_id=request.scenario_id,
            accepted=False,
            errors=[str(exc)],
        )

    return FeedbackSubmitResponse(
        scenario_id=request.scenario_id,
        accepted=True,
    )
