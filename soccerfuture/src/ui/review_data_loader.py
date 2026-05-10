"""Review data loader for the analyst review UI.

Loads bundle artifacts, review packs, readiness results, and feedback
from the filesystem for rendering in the review UI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class ScenarioViewData:
    """All data needed to render a single scenario in the review UI.

    Attributes:
        scenario_id: Unique scenario identifier.
        bundle_path: Path to the bundle directory.
        run_status: Parsed run_status.json dict, or None.
        pipeline_report: Parsed pipeline_report.json dict, or None.
        analyst_summary: Analyst summary markdown text, or None.
        viewer_artifact: Parsed viewer_artifact.json dict, or None.
        readiness_label: Readiness classification, or None.
        feedback_records: List of feedback dicts for this scenario.
        top_branches: List of top branch summaries.
        overall_status: Overall run status string.
        source_type: Input source type.
    """

    scenario_id: str
    bundle_path: str
    run_status: dict | None = None
    pipeline_report: dict | None = None
    analyst_summary: str | None = None
    viewer_artifact: dict | None = None
    readiness_label: str | None = None
    feedback_records: list[dict] = field(default_factory=list)
    top_branches: list[dict] = field(default_factory=list)
    overall_status: str = "unknown"
    source_type: str = "structured"


def _load_json_optional(path: str) -> dict | None:
    """Load a JSON file if it exists, return None otherwise."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def _load_text_optional(path: str) -> str | None:
    """Load a text file if it exists, return None otherwise."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def load_scenario_data(bundle_path: str) -> ScenarioViewData:
    """Load all review data for a single scenario bundle.

    Args:
        bundle_path: Path to the scenario bundle directory.

    Returns:
        A ScenarioViewData instance with all available data loaded.
    """
    scenario_id = os.path.basename(bundle_path)

    run_status = _load_json_optional(os.path.join(bundle_path, "run_status.json"))
    pipeline_report = _load_json_optional(os.path.join(bundle_path, "pipeline_report.json"))
    analyst_summary = _load_text_optional(os.path.join(bundle_path, "analyst_summary.md"))
    viewer_artifact = _load_json_optional(os.path.join(bundle_path, "viewer_artifact.json"))

    # Extract metadata from run_status
    overall_status = "unknown"
    source_type = "structured"
    if run_status:
        overall_status = run_status.get("overall_status", "unknown")
        source_type = run_status.get("source_type", "structured")

    # Extract top branches from pipeline report
    top_branches: list[dict] = []
    if pipeline_report:
        ranked = pipeline_report.get("ranked_branches", [])
        for rb in ranked[:5]:
            top_branches.append({
                "branch_id": rb.get("branch_id", "unknown"),
                "composite_score": rb.get("composite_score", 0.0),
            })

    return ScenarioViewData(
        scenario_id=scenario_id,
        bundle_path=bundle_path,
        run_status=run_status,
        pipeline_report=pipeline_report,
        analyst_summary=analyst_summary,
        viewer_artifact=viewer_artifact,
        top_branches=top_branches,
        overall_status=overall_status,
        source_type=source_type,
    )


def load_all_scenarios(runs_root: str) -> list[ScenarioViewData]:
    """Load all scenario bundles from a runs directory.

    Args:
        runs_root: Root directory containing scenario bundle subdirectories.

    Returns:
        Sorted list of ScenarioViewData instances.
    """
    if not os.path.isdir(runs_root):
        return []

    scenarios: list[ScenarioViewData] = []
    for entry in sorted(os.listdir(runs_root)):
        entry_path = os.path.join(runs_root, entry)
        if not os.path.isdir(entry_path):
            continue
        # Only load directories that have a run_status.json
        if os.path.isfile(os.path.join(entry_path, "run_status.json")):
            scenarios.append(load_scenario_data(entry_path))

    return scenarios


def load_feedback_for_scenario(
    feedback_dir: str,
    scenario_id: str,
) -> list[dict]:
    """Load feedback records for a specific scenario.

    Looks for JSON files in feedback_dir matching the scenario_id.

    Args:
        feedback_dir: Directory containing feedback JSON files.
        scenario_id: Scenario to filter feedback for.

    Returns:
        List of feedback dicts for the scenario.
    """
    if not os.path.isdir(feedback_dir):
        return []

    records: list[dict] = []
    for filename in sorted(os.listdir(feedback_dir)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(feedback_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and data.get("scenario_id") == scenario_id:
                records.append(data)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("scenario_id") == scenario_id:
                        records.append(item)
        except (json.JSONDecodeError, OSError):
            continue

    return records
