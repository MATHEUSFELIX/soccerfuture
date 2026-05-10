"""Unit tests for tactical animation modules."""

import json
import os

import pytest

from src.animation.branch_timeline import (
    BranchTimeline,
    TimelineFrame,
    extract_timeline_from_branch,
    timeline_to_dict,
)
from src.animation.tactical_animator import (
    render_timeline_frames,
    render_timeline_html,
)
from src.animation.animation_exporter import (
    export_animation_html,
    export_svg_frames,
    export_timeline_json,
)
from src.evaluation.animation_quality_checks import (
    AnimationQualityResult,
    check_animation_quality,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_branch(n_timestamps=3) -> dict:
    """Create a ranked branch dict with positions at multiple timestamps."""
    positions = []
    for t in range(n_timestamps):
        positions.append({
            "player_id": "p1", "x": 10.0 + t, "y": 20.0 + t, "timestamp": float(t),
        })
        positions.append({
            "player_id": "p2", "x": 30.0 + t, "y": 40.0 + t, "timestamp": float(t),
        })
    return {
        "branch_id": "branch_001",
        "composite_score": 0.85,
        "branch": {"positions": positions},
        "evaluation_report": {},
    }


# ---------------------------------------------------------------------------
# BranchTimeline
# ---------------------------------------------------------------------------


class TestBranchTimeline:
    def test_extract_from_branch(self):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        assert isinstance(timeline, BranchTimeline)
        assert timeline.branch_id == "branch_001"
        assert len(timeline.frames) == 3

    def test_empty_positions(self):
        branch = {"branch_id": "empty", "composite_score": 0.0, "branch": {"positions": []}}
        timeline = extract_timeline_from_branch(branch)
        assert timeline.frames == []
        assert timeline.duration_seconds == 0.0

    def test_frames_ordered_by_timestamp(self):
        branch = _make_branch(5)
        timeline = extract_timeline_from_branch(branch)
        timestamps = [f.timestamp for f in timeline.frames]
        assert timestamps == sorted(timestamps)

    def test_player_positions_in_frames(self):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        assert len(timeline.frames[0].player_positions) == 2

    def test_timeline_to_dict(self):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        d = timeline_to_dict(timeline)
        assert isinstance(d, dict)
        assert d["branch_id"] == "branch_001"
        assert len(d["frames"]) == 3

    def test_deterministic(self):
        branch = _make_branch()
        t1 = extract_timeline_from_branch(branch)
        t2 = extract_timeline_from_branch(branch)
        assert timeline_to_dict(t1) == timeline_to_dict(t2)


# ---------------------------------------------------------------------------
# TacticalAnimator
# ---------------------------------------------------------------------------


class TestTacticalAnimator:
    def test_render_frames_returns_svg_list(self):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        frames = render_timeline_frames(timeline)
        assert len(frames) == 3
        assert all("<svg" in f for f in frames)

    def test_render_html_contains_branch_id(self):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        html = render_timeline_html(timeline)
        assert "branch_001" in html
        assert "<!DOCTYPE html>" in html

    def test_render_empty_timeline(self):
        timeline = BranchTimeline(branch_id="empty", composite_score=0.0)
        html = render_timeline_html(timeline)
        assert "No frames" in html


# ---------------------------------------------------------------------------
# AnimationExporter
# ---------------------------------------------------------------------------


class TestAnimationExporter:
    def test_export_timeline_json(self, tmp_path):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        path = export_timeline_json(timeline, str(tmp_path / "timeline.json"))
        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert data["branch_id"] == "branch_001"

    def test_export_animation_html(self, tmp_path):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        path = export_animation_html(timeline, str(tmp_path / "anim.html"))
        assert os.path.isfile(path)
        with open(path) as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content

    def test_export_svg_frames(self, tmp_path):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        out_dir = str(tmp_path / "frames")
        paths = export_svg_frames(timeline, out_dir)
        assert len(paths) == 3
        assert all(os.path.isfile(p) for p in paths)
        assert all(p.endswith(".svg") for p in paths)


# ---------------------------------------------------------------------------
# AnimationQualityChecks
# ---------------------------------------------------------------------------


class TestAnimationQualityChecks:
    def test_valid_timeline_passes(self):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        result = check_animation_quality(timeline)
        assert result.passed is True
        assert result.frame_count == 3

    def test_too_few_frames_fails(self):
        timeline = BranchTimeline(
            branch_id="short", composite_score=0.5,
            frames=[TimelineFrame(frame_index=0, timestamp=0.0)],
        )
        result = check_animation_quality(timeline)
        assert result.passed is False
        assert any("Too few frames" in i for i in result.issues)

    def test_out_of_bounds_detected(self):
        timeline = BranchTimeline(
            branch_id="oob", composite_score=0.5,
            frames=[
                TimelineFrame(frame_index=0, timestamp=0.0,
                              player_positions=[{"player_id": "p1", "x": -5.0, "y": 50.0}],
                              ball_position={"x": 34.0, "y": 52.0}),
                TimelineFrame(frame_index=1, timestamp=1.0,
                              player_positions=[{"player_id": "p1", "x": 10.0, "y": 50.0}],
                              ball_position={"x": 34.0, "y": 52.0}),
            ],
        )
        result = check_animation_quality(timeline)
        assert result.passed is False
        assert any("out of bounds" in i for i in result.issues)

    def test_teleportation_detected(self):
        # Player moves 100m in 0.1 seconds = 1000 m/s
        timeline = BranchTimeline(
            branch_id="teleport", composite_score=0.5,
            frames=[
                TimelineFrame(frame_index=0, timestamp=0.0,
                              player_positions=[{"player_id": "p1", "x": 10.0, "y": 10.0}],
                              ball_position={"x": 34.0, "y": 52.0}),
                TimelineFrame(frame_index=1, timestamp=0.1,
                              player_positions=[{"player_id": "p1", "x": 60.0, "y": 90.0}],
                              ball_position={"x": 34.0, "y": 52.0}),
            ],
        )
        result = check_animation_quality(timeline)
        assert result.passed is False
        assert any("speed" in i for i in result.issues)

    def test_result_has_branch_id(self):
        branch = _make_branch()
        timeline = extract_timeline_from_branch(branch)
        result = check_animation_quality(timeline)
        assert result.branch_id == "branch_001"
