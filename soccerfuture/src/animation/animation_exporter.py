"""Animation exporter for saving timeline artifacts.

Exports BranchTimeline animations as HTML files, SVG frame sequences,
or JSON timeline data.
"""

from __future__ import annotations

import json
import os

from src.animation.branch_timeline import BranchTimeline, timeline_to_dict
from src.animation.tactical_animator import render_timeline_frames, render_timeline_html


def export_timeline_json(timeline: BranchTimeline, output_path: str) -> str:
    """Export a BranchTimeline as a JSON file.

    Args:
        timeline: The timeline to export.
        output_path: Path to write the JSON file.

    Returns:
        Path to the written file.
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(timeline_to_dict(timeline), fh, indent=2)
    return output_path


def export_animation_html(timeline: BranchTimeline, output_path: str) -> str:
    """Export a BranchTimeline as a self-contained HTML animation.

    Args:
        timeline: The timeline to export.
        output_path: Path to write the HTML file.

    Returns:
        Path to the written file.
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    html = render_timeline_html(timeline)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return output_path


def export_svg_frames(timeline: BranchTimeline, output_dir: str) -> list[str]:
    """Export individual SVG frames to a directory.

    Args:
        timeline: The timeline to export.
        output_dir: Directory to write SVG files.

    Returns:
        List of paths to written SVG files.
    """
    os.makedirs(output_dir, exist_ok=True)
    frames = render_timeline_frames(timeline)
    paths: list[str] = []
    for i, svg in enumerate(frames):
        path = os.path.join(output_dir, f"frame_{i:04d}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        paths.append(path)
    return paths
