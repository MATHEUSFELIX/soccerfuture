"""Batch demo runner for executing multiple analyst workflows.

Runs the single-scenario workflow repeatedly over a scenario set,
collects aggregate metrics, and generates the demo index.
"""

from __future__ import annotations

import json
import logging
import os

from src.models.play_state import PlayState
from src.pipeline import PipelineConfig
from src.workflows.analyst_workflow_runner import run_analyst_workflow
from src.workflows.demo_index import (
    DemoIndexEntry,
    build_index_entry,
    save_demo_index,
)
from src.workflows.scenario_bundle import BundleManifest

logger = logging.getLogger(__name__)


def run_batch_demo(
    scenarios: list[dict],
    output_root: str = "output/runs",
    pipeline_config: PipelineConfig | None = None,
    skip_viewer: bool = False,
) -> tuple[list[BundleManifest], list[DemoIndexEntry]]:
    """Execute the analyst workflow for each scenario in the batch.

    Each scenario dict must contain:
      - ``scenario_id``: Unique identifier.
      - ``play_state``: A PlayState instance.

    Optional keys:
      - ``source_type``: Input source type (default "structured").
      - ``extraction_notes``: List of extraction notes.
      - ``confidence_notes``: List of confidence notes.
      - ``match_context``: Optional MatchContext.
      - ``match_priors``: Optional MatchPriors.

    Args:
        scenarios: List of scenario dicts.
        output_root: Root directory for all bundle output.
        pipeline_config: Optional pipeline configuration.
        skip_viewer: If True, skip viewer generation for all scenarios.

    Returns:
        Tuple of (list of BundleManifests, list of DemoIndexEntries).
    """
    manifests: list[BundleManifest] = []
    index_entries: list[DemoIndexEntry] = []

    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        play_state: PlayState = scenario["play_state"]
        source_type = scenario.get("source_type", "structured")
        extraction_notes = scenario.get("extraction_notes")
        confidence_notes = scenario.get("confidence_notes")
        match_context = scenario.get("match_context")
        match_priors = scenario.get("match_priors")

        logger.info("Running workflow for scenario: %s", scenario_id)

        manifest = run_analyst_workflow(
            scenario_id=scenario_id,
            play_state=play_state,
            source_type=source_type,
            output_root=output_root,
            pipeline_config=pipeline_config,
            extraction_notes=extraction_notes,
            confidence_notes=confidence_notes,
            match_context=match_context,
            match_priors=match_priors,
            skip_viewer=skip_viewer,
        )
        manifests.append(manifest)

        # Determine flags for index entry
        context_flag = match_context is not None
        priors_flag = match_priors is not None
        confidence_flag = bool(confidence_notes)

        # Extract top-1 branch from the pipeline report if available
        top_1_branch: str | None = None
        report_path = os.path.join(output_root, scenario_id, "pipeline_report.json")
        if os.path.isfile(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as fh:
                    report_data = json.load(fh)
                ranked = report_data.get("ranked_branches", [])
                if ranked:
                    top_1_branch = ranked[0].get("branch_id")
            except (json.JSONDecodeError, OSError):
                pass

        entry = build_index_entry(
            manifest=manifest,
            top_1_branch=top_1_branch,
            confidence_flag=confidence_flag,
            context_flag=context_flag,
            priors_flag=priors_flag,
        )
        index_entries.append(entry)

    # Generate aggregate index
    save_demo_index(index_entries, output_root)

    return manifests, index_entries
