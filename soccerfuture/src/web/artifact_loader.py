"""Artifact loader for the web UI.

Loads run data, summaries, and reports from the filesystem for
rendering in web pages.
"""

from __future__ import annotations

import json
import os


def load_runs_list(runs_root: str = "output/runs") -> list[dict]:
    """Load summary data for all available runs.

    Args:
        runs_root: Root directory containing run bundles.

    Returns:
        Sorted list of run summary dicts.
    """
    if not os.path.isdir(runs_root):
        return []

    runs: list[dict] = []
    for entry in sorted(os.listdir(runs_root)):
        entry_path = os.path.join(runs_root, entry)
        if not os.path.isdir(entry_path):
            continue
        status_path = os.path.join(entry_path, "run_status.json")
        if not os.path.isfile(status_path):
            continue
        try:
            with open(status_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Get top branch from report if available
            top_branch = None
            report_path = os.path.join(entry_path, "pipeline_report.json")
            if os.path.isfile(report_path):
                with open(report_path, "r", encoding="utf-8") as fh:
                    report = json.load(fh)
                ranked = report.get("ranked_branches", [])
                if ranked:
                    top_branch = ranked[0].get("branch_id")

            runs.append({
                "scenario_id": data.get("scenario_id", entry),
                "status": data.get("overall_status", "unknown"),
                "source_type": data.get("source_type", "unknown"),
                "top_branch": top_branch,
                "bundle_path": entry_path,
            })
        except (json.JSONDecodeError, OSError):
            runs.append({
                "scenario_id": entry,
                "status": "error",
                "source_type": "?",
                "top_branch": None,
                "bundle_path": entry_path,
            })

    return runs


def load_run_detail(runs_root: str, scenario_id: str) -> dict:
    """Load full detail for a single run.

    Args:
        runs_root: Root directory containing run bundles.
        scenario_id: The scenario to load.

    Returns:
        Dict with all available run data.
    """
    bundle_path = os.path.join(runs_root, scenario_id)
    if not os.path.isdir(bundle_path):
        return {"error": f"Run not found: {scenario_id}"}

    detail: dict = {"scenario_id": scenario_id, "bundle_path": bundle_path}

    # Run status
    status_path = os.path.join(bundle_path, "run_status.json")
    if os.path.isfile(status_path):
        with open(status_path, "r", encoding="utf-8") as fh:
            detail["run_status"] = json.load(fh)

    # Pipeline report
    report_path = os.path.join(bundle_path, "pipeline_report.json")
    if os.path.isfile(report_path):
        with open(report_path, "r", encoding="utf-8") as fh:
            detail["pipeline_report"] = json.load(fh)

    # Analyst summary
    summary_path = os.path.join(bundle_path, "analyst_summary.md")
    if os.path.isfile(summary_path):
        with open(summary_path, "r", encoding="utf-8") as fh:
            detail["analyst_summary"] = fh.read()

    # Viewer artifact
    viewer_path = os.path.join(bundle_path, "viewer_artifact.json")
    if os.path.isfile(viewer_path):
        with open(viewer_path, "r", encoding="utf-8") as fh:
            detail["viewer_artifact"] = json.load(fh)

    return detail
