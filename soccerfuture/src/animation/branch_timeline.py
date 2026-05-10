"""Branch timeline model for animation generation.

Converts ranked branch data into ordered timeline frames suitable
for deterministic animation rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TimelineFrame:
    """A single frame in a branch animation timeline.

    Attributes:
        frame_index: Sequential frame number (0-based).
        timestamp: Time in seconds from branch start.
        player_positions: List of {player_id, x, y} dicts.
        ball_position: {x, y} dict for ball location.
    """

    frame_index: int
    timestamp: float
    player_positions: list[dict] = field(default_factory=list)
    ball_position: dict = field(default_factory=dict)


@dataclass
class BranchTimeline:
    """Complete timeline for animating a single branch.

    Attributes:
        branch_id: Identifier of the source branch.
        composite_score: Branch composite score.
        frames: Ordered list of timeline frames.
        duration_seconds: Total animation duration.
        fps: Frames per second for playback.
        metadata: Additional branch metadata.
    """

    branch_id: str
    composite_score: float
    frames: list[TimelineFrame] = field(default_factory=list)
    duration_seconds: float = 0.0
    fps: float = 10.0
    metadata: dict = field(default_factory=dict)


def extract_timeline_from_branch(
    ranked_branch: dict,
    fps: float = 10.0,
) -> BranchTimeline:
    """Extract a BranchTimeline from a ranked branch dict.

    Reads the branch positions sorted by timestamp and converts them
    into sequential frames at the specified fps.

    Args:
        ranked_branch: A ranked branch dict (from PipelineReport.to_dict()).
        fps: Target frames per second.

    Returns:
        A BranchTimeline with ordered frames.
    """
    branch_id = ranked_branch.get("branch_id", "unknown")
    composite_score = ranked_branch.get("composite_score", 0.0)
    branch = ranked_branch.get("branch", {})
    positions = branch.get("positions", [])

    if not positions:
        return BranchTimeline(
            branch_id=branch_id,
            composite_score=composite_score,
            frames=[],
            duration_seconds=0.0,
            fps=fps,
        )

    # Group positions by timestamp
    by_timestamp: dict[float, list[dict]] = {}
    for pos in positions:
        ts = pos.get("timestamp", 0.0)
        by_timestamp.setdefault(ts, []).append(pos)

    sorted_timestamps = sorted(by_timestamp.keys())
    duration = sorted_timestamps[-1] - sorted_timestamps[0] if len(sorted_timestamps) > 1 else 0.0

    frames: list[TimelineFrame] = []
    for i, ts in enumerate(sorted_timestamps):
        entries = by_timestamp[ts]
        player_positions = [
            {"player_id": p.get("player_id", f"p{j}"), "x": p.get("x", 0.0), "y": p.get("y", 0.0)}
            for j, p in enumerate(entries)
            if p.get("player_id") is not None
        ]
        # Use first entry as ball approximation if no explicit ball
        ball_position = {"x": entries[0].get("x", 0.0), "y": entries[0].get("y", 0.0)}

        frames.append(TimelineFrame(
            frame_index=i,
            timestamp=ts,
            player_positions=player_positions,
            ball_position=ball_position,
        ))

    return BranchTimeline(
        branch_id=branch_id,
        composite_score=composite_score,
        frames=frames,
        duration_seconds=duration,
        fps=fps,
        metadata={"source_positions_count": len(positions)},
    )


def timeline_to_dict(timeline: BranchTimeline) -> dict:
    """Convert a BranchTimeline to a JSON-serializable dict."""
    return {
        "branch_id": timeline.branch_id,
        "composite_score": timeline.composite_score,
        "frames": [
            {
                "frame_index": f.frame_index,
                "timestamp": f.timestamp,
                "player_positions": f.player_positions,
                "ball_position": f.ball_position,
            }
            for f in timeline.frames
        ],
        "duration_seconds": timeline.duration_seconds,
        "fps": timeline.fps,
        "metadata": timeline.metadata,
    }
