"""Single-scenario analyst workflow runner.

Orchestrates the full end-to-end flow: input load, optional extraction,
pipeline execution, report generation, viewer artifact generation,
analyst summary generation, and bundle write.
"""

from __future__ import annotations

import datetime
import json
import logging
import time

from src.models.play_state import PlayState, play_state_to_dict, dict_to_play_state
from src.models.pipeline_report import PipelineReport
from src.pipeline import PipelineConfig, run_pipeline
from src.workflows.analyst_summary import render_analyst_summary
from src.workflows.scenario_bundle import (
    BundleManifest,
    StepStatus,
    bundle_manifest_to_dict,
    compute_overall_status,
    ensure_bundle_dir,
    make_step_status,
    write_json_artifact,
    write_text_artifact,
)

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run_analyst_workflow(
    scenario_id: str,
    play_state: PlayState | None = None,
    play_state_dict: dict | None = None,
    source_type: str = "structured",
    output_root: str = "output/runs",
    pipeline_config: PipelineConfig | None = None,
    extraction_notes: list[str] | None = None,
    confidence_notes: list[str] | None = None,
    match_context=None,
    match_priors=None,
    skip_viewer: bool = False,
) -> BundleManifest:
    """Execute the full analyst workflow for a single scenario.

    Steps:
      1. Load — resolve PlayState from input
      2. Extract — (optional) state extraction notes
      3. Pipeline — run branch generation and evaluation
      4. Report — write pipeline report JSON
      5. Viewer — write viewer artifact reference
      6. Summary — generate analyst-facing Markdown
      7. Bundle write — write run_status.json

    Args:
        scenario_id: Unique scenario identifier.
        play_state: A PlayState instance, or None if play_state_dict is provided.
        play_state_dict: A PlayState dict, or None if play_state is provided.
        source_type: Input source type ("structured", "video", "commentator").
        output_root: Root directory for bundle output.
        pipeline_config: Optional pipeline configuration.
        extraction_notes: Notes from state extraction.
        confidence_notes: Notes about confidence or completeness.
        match_context: Optional MatchContext for context-aware runs.
        match_priors: Optional MatchPriors for priors-aware runs.
        skip_viewer: If True, skip viewer artifact generation.

    Returns:
        BundleManifest describing the completed workflow run.
    """
    run_timestamp = _now_iso()
    step_statuses: list[StepStatus] = []
    artifact_refs: dict[str, str] = {}

    # --- Create bundle directory ---
    bundle_path = ensure_bundle_dir(output_root, scenario_id)

    # --- Step 1: Load ---
    resolved_play_state: PlayState | None = None
    try:
        if play_state is not None:
            resolved_play_state = play_state
        elif play_state_dict is not None:
            resolved_play_state = dict_to_play_state(play_state_dict)
        else:
            raise ValueError("Either play_state or play_state_dict must be provided")

        # Write input reference
        ps_dict = play_state_to_dict(resolved_play_state)
        path = write_json_artifact(bundle_path, "input_reference.json", {
            "scenario_id": scenario_id,
            "source_type": source_type,
        })
        artifact_refs["input_reference"] = "input_reference.json"

        step_statuses.append(make_step_status("load", "success"))
    except Exception as exc:
        step_statuses.append(make_step_status("load", "failed", notes=str(exc)))
        # Cannot continue without input
        for remaining in ("extract", "pipeline", "report", "viewer", "summary"):
            step_statuses.append(make_step_status(remaining, "skipped", notes="Load failed"))
        manifest = BundleManifest(
            scenario_id=scenario_id,
            source_type=source_type,
            run_timestamp=run_timestamp,
            step_statuses=step_statuses,
            artifact_references=artifact_refs,
            overall_status=compute_overall_status(step_statuses),
        )
        write_json_artifact(bundle_path, "run_status.json", bundle_manifest_to_dict(manifest))
        artifact_refs["run_status"] = "run_status.json"
        return manifest

    # --- Step 2: Extract ---
    # For structured inputs, extraction is a no-op. For video/commentator,
    # the caller should have already extracted and passed the PlayState.
    if source_type == "structured":
        step_statuses.append(make_step_status("extract", "skipped", notes="Structured input, no extraction needed"))
    else:
        notes = "; ".join(extraction_notes) if extraction_notes else "Extraction completed externally"
        step_statuses.append(make_step_status("extract", "success", notes=notes))

    # Write extracted play state
    ps_path = write_json_artifact(bundle_path, "extracted_play_state.json", ps_dict)
    artifact_refs["extracted_play_state"] = "extracted_play_state.json"

    # --- Step 3: Pipeline ---
    report: PipelineReport | None = None
    try:
        report = run_pipeline(
            resolved_play_state,
            config=pipeline_config,
            match_context=match_context,
            match_priors=match_priors,
        )
        step_statuses.append(make_step_status("pipeline", "success"))
    except Exception as exc:
        step_statuses.append(make_step_status("pipeline", "failed", notes=str(exc)))
        # Mark downstream as skipped
        for remaining in ("report", "viewer", "summary"):
            step_statuses.append(make_step_status(remaining, "skipped", notes="Pipeline failed"))
        manifest = BundleManifest(
            scenario_id=scenario_id,
            source_type=source_type,
            run_timestamp=run_timestamp,
            step_statuses=step_statuses,
            artifact_references=artifact_refs,
            overall_status=compute_overall_status(step_statuses),
        )
        write_json_artifact(bundle_path, "run_status.json", bundle_manifest_to_dict(manifest))
        artifact_refs["run_status"] = "run_status.json"
        return manifest

    # --- Step 4: Report ---
    report_dict = report.to_dict()
    try:
        write_json_artifact(bundle_path, "pipeline_report.json", report_dict)
        artifact_refs["pipeline_report"] = "pipeline_report.json"
        step_statuses.append(make_step_status("report", "success"))
    except Exception as exc:
        step_statuses.append(make_step_status("report", "failed", notes=str(exc)))

    # --- Step 5: Viewer ---
    if skip_viewer:
        step_statuses.append(make_step_status("viewer", "skipped", notes="Viewer generation skipped"))
    else:
        try:
            # Write a viewer artifact reference (actual rendering is optional)
            viewer_ref = {
                "scenario_id": scenario_id,
                "report_path": "pipeline_report.json",
                "note": "Viewer can be rendered from pipeline_report.json using render_pipeline_report()",
            }
            write_json_artifact(bundle_path, "viewer_artifact.json", viewer_ref)
            artifact_refs["viewer_artifact"] = "viewer_artifact.json"
            step_statuses.append(make_step_status("viewer", "success"))
        except Exception as exc:
            step_statuses.append(make_step_status("viewer", "partial", notes=str(exc)))

    # --- Step 6: Summary ---
    try:
        metadata = report_dict.get("metadata", {})
        context_applied = bool(metadata.get("context_applied", False))
        priors_applied = bool(metadata.get("priors_applied", False))

        summary_md = render_analyst_summary(
            scenario_id=scenario_id,
            source_type=source_type,
            pipeline_report=report_dict,
            extraction_notes=extraction_notes,
            context_applied=context_applied,
            priors_applied=priors_applied,
            confidence_notes=confidence_notes,
            artifact_references=artifact_refs,
        )
        write_text_artifact(bundle_path, "analyst_summary.md", summary_md)
        artifact_refs["analyst_summary"] = "analyst_summary.md"
        step_statuses.append(make_step_status("summary", "success"))
    except Exception as exc:
        step_statuses.append(make_step_status("summary", "failed", notes=str(exc)))

    # --- Step 7: Bundle write (run_status.json) ---
    manifest = BundleManifest(
        scenario_id=scenario_id,
        source_type=source_type,
        run_timestamp=run_timestamp,
        step_statuses=step_statuses,
        artifact_references=artifact_refs,
        overall_status=compute_overall_status(step_statuses),
    )
    write_json_artifact(bundle_path, "run_status.json", bundle_manifest_to_dict(manifest))
    artifact_refs["run_status"] = "run_status.json"

    return manifest
