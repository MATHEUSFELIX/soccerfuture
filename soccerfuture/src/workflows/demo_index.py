"""Aggregate demo index generation.

Produces JSON and Markdown index artifacts from a collection of
BundleManifest results, enabling quick browsing of scenario outputs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from src.workflows.scenario_bundle import BundleManifest


@dataclass
class DemoIndexEntry:
    """A single entry in the demo index.

    Attributes:
        scenario_id: Unique scenario identifier.
        source_type: Input source type.
        top_1_branch: Branch ID of the top-ranked branch, or None.
        status: Overall workflow status.
        confidence_flag: Whether confidence concerns were noted.
        context_flag: Whether match context was applied.
        priors_flag: Whether match priors were applied.
        bundle_path: Relative path to the scenario bundle directory.
        summary_path: Relative path to the analyst summary, or None.
    """

    scenario_id: str
    source_type: str
    top_1_branch: str | None
    status: str
    confidence_flag: bool
    context_flag: bool
    priors_flag: bool
    bundle_path: str
    summary_path: str | None


def build_index_entry(
    manifest: BundleManifest,
    top_1_branch: str | None = None,
    confidence_flag: bool = False,
    context_flag: bool = False,
    priors_flag: bool = False,
) -> DemoIndexEntry:
    """Build a DemoIndexEntry from a BundleManifest.

    Args:
        manifest: The completed bundle manifest.
        top_1_branch: Branch ID of the top-ranked branch.
        confidence_flag: Whether confidence concerns exist.
        context_flag: Whether context was applied.
        priors_flag: Whether priors were applied.

    Returns:
        A DemoIndexEntry for the index.
    """
    summary_path = manifest.artifact_references.get("analyst_summary")
    bundle_path = manifest.scenario_id

    return DemoIndexEntry(
        scenario_id=manifest.scenario_id,
        source_type=manifest.source_type,
        top_1_branch=top_1_branch,
        status=manifest.overall_status,
        confidence_flag=confidence_flag,
        context_flag=context_flag,
        priors_flag=priors_flag,
        bundle_path=bundle_path,
        summary_path=f"{bundle_path}/{summary_path}" if summary_path else None,
    )


def _entry_to_dict(entry: DemoIndexEntry) -> dict:
    """Convert a DemoIndexEntry to a JSON-serializable dict."""
    return {
        "scenario_id": entry.scenario_id,
        "source_type": entry.source_type,
        "top_1_branch": entry.top_1_branch,
        "status": entry.status,
        "confidence_flag": entry.confidence_flag,
        "context_flag": entry.context_flag,
        "priors_flag": entry.priors_flag,
        "bundle_path": entry.bundle_path,
        "summary_path": entry.summary_path,
    }


def generate_demo_index_json(entries: list[DemoIndexEntry]) -> dict:
    """Generate the demo index as a JSON-serializable dict.

    Args:
        entries: List of index entries.

    Returns:
        Dict with "scenarios" list and "summary" counts.
    """
    total = len(entries)
    success_count = sum(1 for e in entries if e.status == "success")
    partial_count = sum(1 for e in entries if e.status == "partial")
    failed_count = sum(1 for e in entries if e.status == "failed")

    return {
        "scenarios": [_entry_to_dict(e) for e in entries],
        "summary": {
            "total": total,
            "success": success_count,
            "partial": partial_count,
            "failed": failed_count,
        },
    }


def generate_demo_index_markdown(entries: list[DemoIndexEntry]) -> str:
    """Generate the demo index as a Markdown string.

    Args:
        entries: List of index entries.

    Returns:
        Markdown table with scenario overview.
    """
    lines: list[str] = []
    lines.append("# Demo Index")
    lines.append("")

    total = len(entries)
    success_count = sum(1 for e in entries if e.status == "success")
    partial_count = sum(1 for e in entries if e.status == "partial")
    failed_count = sum(1 for e in entries if e.status == "failed")

    lines.append(f"**Total scenarios:** {total} | "
                 f"Success: {success_count} | "
                 f"Partial: {partial_count} | "
                 f"Failed: {failed_count}")
    lines.append("")

    # Table header
    lines.append("| Scenario | Source | Top-1 Branch | Status | Context | Priors | Confidence |")
    lines.append("|---|---|---|---|---|---|---|")

    for entry in entries:
        top_1 = entry.top_1_branch or "—"
        ctx = "✓" if entry.context_flag else "—"
        pri = "✓" if entry.priors_flag else "—"
        conf = "⚠" if entry.confidence_flag else "✓"
        lines.append(
            f"| {entry.scenario_id} | {entry.source_type} | {top_1} | "
            f"{entry.status} | {ctx} | {pri} | {conf} |"
        )

    lines.append("")
    return "\n".join(lines)


def save_demo_index(
    entries: list[DemoIndexEntry],
    output_dir: str,
) -> tuple[str, str]:
    """Save demo index as both JSON and Markdown files.

    Args:
        entries: List of index entries.
        output_dir: Directory to write index files.

    Returns:
        Tuple of (json_path, markdown_path).
    """
    os.makedirs(output_dir, exist_ok=True)

    json_data = generate_demo_index_json(entries)
    json_path = os.path.join(output_dir, "demo_index.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(json_data, fh, indent=2)

    md_content = generate_demo_index_markdown(entries)
    md_path = os.path.join(output_dir, "demo_index.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md_content)

    return json_path, md_path
