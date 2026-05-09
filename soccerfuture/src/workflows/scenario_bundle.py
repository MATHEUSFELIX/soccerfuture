"""Scenario bundle structure and artifact reference utilities.

Defines the StepStatus, BundleManifest, and helper functions for
creating deterministic bundle directories and writing artifacts.
"""

from __future__ import annotations

import datetime
import json
import os
from dataclasses import asdict, dataclass, field


# ---------------------------------------------------------------------------
# Step status model
# ---------------------------------------------------------------------------

VALID_STEP_STATUSES = {"success", "partial", "failed", "skipped"}

WORKFLOW_STEPS = ("load", "extract", "pipeline", "report", "viewer", "summary", "bundle_write")


@dataclass
class StepStatus:
    """Status of a single workflow step.

    Attributes:
        step_name: Name of the workflow step.
        status: One of "success", "partial", "failed", "skipped".
        started_at: ISO-8601 timestamp when the step started.
        finished_at: ISO-8601 timestamp when the step finished.
        notes: Free-text notes about the step execution.
        artifact_path: Path to the artifact produced by this step, if any.
    """

    step_name: str
    status: str
    started_at: str = ""
    finished_at: str = ""
    notes: str = ""
    artifact_path: str | None = None

    def __post_init__(self) -> None:
        """Validate status value."""
        if self.status not in VALID_STEP_STATUSES:
            raise ValueError(
                f"Invalid step status '{self.status}'. "
                f"Must be one of {sorted(VALID_STEP_STATUSES)}"
            )


def make_step_status(
    step_name: str,
    status: str,
    notes: str = "",
    artifact_path: str | None = None,
) -> StepStatus:
    """Create a StepStatus with current timestamps.

    Args:
        step_name: Name of the workflow step.
        status: One of "success", "partial", "failed", "skipped".
        notes: Free-text notes.
        artifact_path: Path to the produced artifact.

    Returns:
        A StepStatus instance with timestamps filled.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return StepStatus(
        step_name=step_name,
        status=status,
        started_at=now,
        finished_at=now,
        notes=notes,
        artifact_path=artifact_path,
    )


# ---------------------------------------------------------------------------
# Bundle manifest
# ---------------------------------------------------------------------------


@dataclass
class BundleManifest:
    """Manifest describing a scenario bundle.

    Attributes:
        scenario_id: Unique identifier for the scenario.
        source_type: Type of input source ("structured", "video", "commentator").
        run_timestamp: ISO-8601 timestamp of the workflow run.
        step_statuses: List of per-step status records.
        artifact_references: Mapping of artifact name to relative path.
        notes: Free-text notes about the run.
        overall_status: Aggregate status ("success", "partial", "failed").
    """

    scenario_id: str
    source_type: str
    run_timestamp: str
    step_statuses: list[StepStatus] = field(default_factory=list)
    artifact_references: dict[str, str] = field(default_factory=dict)
    notes: str = ""
    overall_status: str = "success"


def compute_overall_status(step_statuses: list[StepStatus]) -> str:
    """Compute the aggregate status from step statuses.

    Rules:
      - If any step is "failed", overall is "failed".
      - If any step is "partial" or "skipped", overall is "partial".
      - Otherwise, overall is "success".

    Args:
        step_statuses: List of step status records.

    Returns:
        One of "success", "partial", "failed".
    """
    statuses = {s.status for s in step_statuses}
    if "failed" in statuses:
        return "failed"
    if "partial" in statuses or "skipped" in statuses:
        return "partial"
    return "success"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def step_status_to_dict(s: StepStatus) -> dict:
    """Convert a StepStatus to a JSON-serializable dict."""
    return asdict(s)


def bundle_manifest_to_dict(m: BundleManifest) -> dict:
    """Convert a BundleManifest to a JSON-serializable dict."""
    return {
        "scenario_id": m.scenario_id,
        "source_type": m.source_type,
        "run_timestamp": m.run_timestamp,
        "step_statuses": [step_status_to_dict(s) for s in m.step_statuses],
        "artifact_references": m.artifact_references,
        "notes": m.notes,
        "overall_status": m.overall_status,
    }


def dict_to_bundle_manifest(data: dict) -> BundleManifest:
    """Reconstruct a BundleManifest from a dict.

    Args:
        data: Dict previously produced by bundle_manifest_to_dict.

    Returns:
        Reconstructed BundleManifest.
    """
    step_statuses = [
        StepStatus(**s) for s in data.get("step_statuses", [])
    ]
    return BundleManifest(
        scenario_id=data["scenario_id"],
        source_type=data["source_type"],
        run_timestamp=data["run_timestamp"],
        step_statuses=step_statuses,
        artifact_references=data.get("artifact_references", {}),
        notes=data.get("notes", ""),
        overall_status=data.get("overall_status", "success"),
    )


# ---------------------------------------------------------------------------
# Bundle directory utilities
# ---------------------------------------------------------------------------


def bundle_dir_path(output_root: str, scenario_id: str) -> str:
    """Compute the deterministic bundle directory path.

    Args:
        output_root: Root directory for all bundles.
        scenario_id: Unique scenario identifier.

    Returns:
        Absolute path to the scenario bundle directory.
    """
    return os.path.join(output_root, scenario_id)


def ensure_bundle_dir(output_root: str, scenario_id: str) -> str:
    """Create the bundle directory if it does not exist.

    Args:
        output_root: Root directory for all bundles.
        scenario_id: Unique scenario identifier.

    Returns:
        Path to the created/existing bundle directory.
    """
    path = bundle_dir_path(output_root, scenario_id)
    os.makedirs(path, exist_ok=True)
    return path


def write_json_artifact(bundle_path: str, filename: str, data: dict) -> str:
    """Write a JSON artifact to the bundle directory.

    Args:
        bundle_path: Path to the bundle directory.
        filename: Name of the JSON file to write.
        data: Dict to serialize as JSON.

    Returns:
        Full path to the written file.
    """
    filepath = os.path.join(bundle_path, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return filepath


def write_text_artifact(bundle_path: str, filename: str, content: str) -> str:
    """Write a text artifact to the bundle directory.

    Args:
        bundle_path: Path to the bundle directory.
        filename: Name of the file to write.
        content: Text content to write.

    Returns:
        Full path to the written file.
    """
    filepath = os.path.join(bundle_path, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)
    return filepath
