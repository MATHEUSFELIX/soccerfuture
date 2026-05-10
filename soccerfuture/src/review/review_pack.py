"""Review pack generation from scenario bundles.

Produces concise stakeholder-facing review packs that summarize a
scenario bundle without exposing unnecessary engineering details.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field


@dataclass
class ReviewPack:
    """A concise stakeholder-facing review pack for one scenario.

    Attributes:
        scenario_id: Unique scenario identifier.
        source_type: Input source type.
        top_branches: List of top branch summaries (id + score).
        summary_text: Analyst summary text (or excerpt).
        confidence_notes: Confidence/completeness notes.
        context_notes: Context/prior influence notes.
        run_status: Overall run status.
        viewer_artifact_ref: Path to viewer artifact, if available.
        readiness_label: Readiness classification, if evaluated.
    """

    scenario_id: str
    source_type: str = "structured"
    top_branches: list[dict] = field(default_factory=list)
    summary_text: str = ""
    confidence_notes: list[str] = field(default_factory=list)
    context_notes: list[str] = field(default_factory=list)
    run_status: str = "success"
    viewer_artifact_ref: str | None = None
    readiness_label: str | None = None


def generate_review_pack(
    bundle_path: str,
    scenario_id: str | None = None,
) -> ReviewPack:
    """Generate a review pack from a scenario bundle directory.

    Reads the bundle's run_status.json, pipeline_report.json, and
    analyst_summary.md to assemble a concise review pack.

    Args:
        bundle_path: Path to the scenario bundle directory.
        scenario_id: Override scenario_id (auto-detected from run_status if None).

    Returns:
        A ReviewPack instance.

    Raises:
        FileNotFoundError: If the bundle directory or run_status.json is missing.
    """
    # Load run status
    status_path = os.path.join(bundle_path, "run_status.json")
    if not os.path.isfile(status_path):
        raise FileNotFoundError(f"run_status.json not found in {bundle_path}")

    with open(status_path, "r", encoding="utf-8") as fh:
        run_status = json.load(fh)

    sid = scenario_id or run_status.get("scenario_id", os.path.basename(bundle_path))
    source_type = run_status.get("source_type", "structured")
    overall_status = run_status.get("overall_status", "unknown")

    # Load pipeline report (optional)
    top_branches: list[dict] = []
    context_notes: list[str] = []
    report_path = os.path.join(bundle_path, "pipeline_report.json")
    if os.path.isfile(report_path):
        with open(report_path, "r", encoding="utf-8") as fh:
            report = json.load(fh)
        ranked = report.get("ranked_branches", [])
        for rb in ranked[:5]:
            top_branches.append({
                "branch_id": rb.get("branch_id", "unknown"),
                "composite_score": rb.get("composite_score", 0.0),
            })
        metadata = report.get("metadata", {})
        if metadata.get("context_applied"):
            context_notes.append("Match context was applied.")
        if metadata.get("priors_applied"):
            influence = metadata.get("priors_influence_level", "unknown")
            context_notes.append(f"Match priors applied (influence: {influence}).")

    # Load analyst summary (optional)
    summary_text = ""
    summary_path = os.path.join(bundle_path, "analyst_summary.md")
    if os.path.isfile(summary_path):
        with open(summary_path, "r", encoding="utf-8") as fh:
            summary_text = fh.read()

    # Viewer artifact reference
    viewer_ref: str | None = None
    viewer_path = os.path.join(bundle_path, "viewer_artifact.json")
    if os.path.isfile(viewer_path):
        viewer_ref = "viewer_artifact.json"

    # Confidence notes from run status
    confidence_notes: list[str] = []
    for step in run_status.get("step_statuses", []):
        if step.get("status") == "partial":
            confidence_notes.append(f"Step '{step.get('step_name')}' was partial: {step.get('notes', '')}")
        elif step.get("status") == "failed":
            confidence_notes.append(f"Step '{step.get('step_name')}' failed: {step.get('notes', '')}")

    return ReviewPack(
        scenario_id=sid,
        source_type=source_type,
        top_branches=top_branches,
        summary_text=summary_text,
        confidence_notes=confidence_notes,
        context_notes=context_notes,
        run_status=overall_status,
        viewer_artifact_ref=viewer_ref,
    )


def review_pack_to_dict(pack: ReviewPack) -> dict:
    """Convert a ReviewPack to a JSON-serializable dict."""
    return asdict(pack)
