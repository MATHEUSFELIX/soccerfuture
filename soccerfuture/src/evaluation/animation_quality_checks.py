"""Physical plausibility checks for animation timelines.

Validates that branch timelines are physically reasonable before
export — checking for teleportation, out-of-bounds positions, and
minimum frame counts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from src.animation.branch_timeline import BranchTimeline, TimelineFrame
from src.utils.constants import FIELD_LENGTH, FIELD_WIDTH

# Maximum plausible player speed in m/s (sprint ~10 m/s)
MAX_PLAYER_SPEED_MS: float = 12.0

# Minimum frames for a meaningful animation
MIN_FRAMES_FOR_ANIMATION: int = 2


@dataclass
class AnimationQualityResult:
    """Result of animation quality checks.

    Attributes:
        branch_id: Branch identifier.
        passed: Whether all checks passed.
        frame_count: Number of frames in the timeline.
        issues: List of quality issues found.
        notes: Additional notes.
    """

    branch_id: str
    passed: bool
    frame_count: int
    issues: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _check_bounds(frame: TimelineFrame) -> list[str]:
    """Check that all positions are within field bounds."""
    issues: list[str] = []
    for p in frame.player_positions:
        x = p.get("x", 0.0)
        y = p.get("y", 0.0)
        if x < 0 or x > FIELD_WIDTH or y < 0 or y > FIELD_LENGTH:
            issues.append(
                f"Frame {frame.frame_index}: player {p.get('player_id', '?')} "
                f"out of bounds ({x:.1f}, {y:.1f})"
            )
    bx = frame.ball_position.get("x", 0.0)
    by = frame.ball_position.get("y", 0.0)
    if bx < 0 or bx > FIELD_WIDTH or by < 0 or by > FIELD_LENGTH:
        issues.append(
            f"Frame {frame.frame_index}: ball out of bounds ({bx:.1f}, {by:.1f})"
        )
    return issues


def _check_speed(
    frame_a: TimelineFrame,
    frame_b: TimelineFrame,
) -> list[str]:
    """Check that player movement between frames is physically plausible."""
    issues: list[str] = []
    dt = frame_b.timestamp - frame_a.timestamp
    if dt <= 0:
        return issues

    # Build position lookup for frame_a
    pos_a: dict[str, tuple[float, float]] = {}
    for p in frame_a.player_positions:
        pid = p.get("player_id", "")
        pos_a[pid] = (p.get("x", 0.0), p.get("y", 0.0))

    for p in frame_b.player_positions:
        pid = p.get("player_id", "")
        if pid not in pos_a:
            continue
        ax, ay = pos_a[pid]
        bx, by = p.get("x", 0.0), p.get("y", 0.0)
        dist = math.sqrt((bx - ax) ** 2 + (by - ay) ** 2)
        speed = dist / dt
        if speed > MAX_PLAYER_SPEED_MS:
            issues.append(
                f"Frames {frame_a.frame_index}->{frame_b.frame_index}: "
                f"player {pid} speed {speed:.1f} m/s exceeds max {MAX_PLAYER_SPEED_MS}"
            )

    return issues


def check_animation_quality(timeline: BranchTimeline) -> AnimationQualityResult:
    """Run physical plausibility checks on a branch timeline.

    Checks:
      - Minimum frame count
      - All positions within field bounds
      - Player speeds between frames are physically plausible

    Args:
        timeline: The branch timeline to check.

    Returns:
        An AnimationQualityResult with pass/fail and issues.
    """
    issues: list[str] = []
    notes: list[str] = []

    frame_count = len(timeline.frames)

    if frame_count < MIN_FRAMES_FOR_ANIMATION:
        issues.append(
            f"Too few frames ({frame_count} < {MIN_FRAMES_FOR_ANIMATION})"
        )

    # Bounds checks
    for frame in timeline.frames:
        issues.extend(_check_bounds(frame))

    # Speed checks between consecutive frames
    for i in range(len(timeline.frames) - 1):
        issues.extend(_check_speed(timeline.frames[i], timeline.frames[i + 1]))

    passed = len(issues) == 0
    if passed:
        notes.append("All physical plausibility checks passed.")
    else:
        notes.append(f"{len(issues)} issue(s) found.")

    return AnimationQualityResult(
        branch_id=timeline.branch_id,
        passed=passed,
        frame_count=frame_count,
        issues=issues,
        notes=notes,
    )
