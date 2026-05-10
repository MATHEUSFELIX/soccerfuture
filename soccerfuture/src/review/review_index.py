"""Aggregate review index generation.

Produces JSON and Markdown review index artifacts from readiness results
and feedback status, enabling quick browsing of review state.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from src.review.demo_readiness import ReadinessResult


@dataclass
class ReviewIndexEntry:
    """A single entry in the review index.

    Attributes:
        scenario_id: Unique scenario identifier.
        status: Overall run status.
        readiness_label: Readiness classification.
        confidence_flag: Whether confidence concerns exist.
        feedback_received: Whether feedback has been received.
        key_blocker: Primary blocker summary, if any.
        bundle_path: Relative path to the bundle.
        summary_path: Relative path to the analyst summary.
    """

    scenario_id: str
    status: str
    readiness_label: str
    confidence_flag: bool = False
    feedback_received: bool = False
    key_blocker: str = ""
    bundle_path: str = ""
    summary_path: str = ""


def build_review_index_entry(
    readiness: ReadinessResult,
    status: str = "success",
    confidence_flag: bool = False,
    feedback_received: bool = False,
    key_blocker: str = "",
) -> ReviewIndexEntry:
    """Build a ReviewIndexEntry from a ReadinessResult.

    Args:
        readiness: The readiness evaluation result.
        status: Overall run status.
        confidence_flag: Whether confidence concerns exist.
        feedback_received: Whether feedback has been received.
        key_blocker: Primary blocker summary.

    Returns:
        A ReviewIndexEntry for the index.
    """
    return ReviewIndexEntry(
        scenario_id=readiness.scenario_id,
        status=status,
        readiness_label=readiness.label,
        confidence_flag=confidence_flag,
        feedback_received=feedback_received,
        key_blocker=key_blocker,
        bundle_path=readiness.scenario_id,
        summary_path=f"{readiness.scenario_id}/analyst_summary.md",
    )


def _entry_to_dict(entry: ReviewIndexEntry) -> dict:
    """Convert a ReviewIndexEntry to a JSON-serializable dict."""
    return {
        "scenario_id": entry.scenario_id,
        "status": entry.status,
        "readiness_label": entry.readiness_label,
        "confidence_flag": entry.confidence_flag,
        "feedback_received": entry.feedback_received,
        "key_blocker": entry.key_blocker,
        "bundle_path": entry.bundle_path,
        "summary_path": entry.summary_path,
    }


def generate_review_index_json(entries: list[ReviewIndexEntry]) -> dict:
    """Generate the review index as a JSON-serializable dict.

    Args:
        entries: List of review index entries.

    Returns:
        Dict with "scenarios" list and "summary" counts.
    """
    total = len(entries)
    ready_count = sum(1 for e in entries if e.readiness_label == "ready")
    partial_count = sum(1 for e in entries if e.readiness_label == "partially_ready")
    not_ready_count = sum(1 for e in entries if e.readiness_label == "not_ready")
    reviewed_count = sum(1 for e in entries if e.feedback_received)

    return {
        "scenarios": [_entry_to_dict(e) for e in entries],
        "summary": {
            "total": total,
            "ready": ready_count,
            "partially_ready": partial_count,
            "not_ready": not_ready_count,
            "reviewed": reviewed_count,
            "not_reviewed": total - reviewed_count,
        },
    }


def generate_review_index_markdown(entries: list[ReviewIndexEntry]) -> str:
    """Generate the review index as a Markdown string.

    Args:
        entries: List of review index entries.

    Returns:
        Markdown table with review overview.
    """
    lines: list[str] = []
    lines.append("# Review Index")
    lines.append("")

    total = len(entries)
    ready_count = sum(1 for e in entries if e.readiness_label == "ready")
    partial_count = sum(1 for e in entries if e.readiness_label == "partially_ready")
    not_ready_count = sum(1 for e in entries if e.readiness_label == "not_ready")

    lines.append(f"**Total:** {total} | Ready: {ready_count} | "
                 f"Partial: {partial_count} | Not Ready: {not_ready_count}")
    lines.append("")

    lines.append("| Scenario | Status | Readiness | Confidence | Feedback | Blocker |")
    lines.append("|---|---|---|---|---|---|")

    for entry in entries:
        conf = "⚠" if entry.confidence_flag else "✓"
        fb = "✓" if entry.feedback_received else "—"
        blocker = entry.key_blocker or "—"
        lines.append(
            f"| {entry.scenario_id} | {entry.status} | {entry.readiness_label} | "
            f"{conf} | {fb} | {blocker} |"
        )

    lines.append("")
    return "\n".join(lines)


def save_review_index(
    entries: list[ReviewIndexEntry],
    output_dir: str,
) -> tuple[str, str]:
    """Save review index as both JSON and Markdown files.

    Args:
        entries: List of review index entries.
        output_dir: Directory to write index files.

    Returns:
        Tuple of (json_path, markdown_path).
    """
    os.makedirs(output_dir, exist_ok=True)

    json_data = generate_review_index_json(entries)
    json_path = os.path.join(output_dir, "review_index.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(json_data, fh, indent=2)

    md_content = generate_review_index_markdown(entries)
    md_path = os.path.join(output_dir, "review_index.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md_content)

    return json_path, md_path
