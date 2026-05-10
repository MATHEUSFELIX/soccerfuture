"""Deterministic tactical animator.

Renders BranchTimeline frames into SVG frame sequences for
lightweight tactical animation without heavy video dependencies.
"""

from __future__ import annotations

from src.animation.branch_timeline import BranchTimeline, TimelineFrame
from src.utils.constants import FIELD_LENGTH, FIELD_WIDTH


def _render_svg_frame(
    frame: TimelineFrame,
    field_width: float = FIELD_WIDTH,
    field_length: float = FIELD_LENGTH,
    canvas_width: int = 680,
    canvas_height: int = 1050,
) -> str:
    """Render a single timeline frame as an SVG string.

    Args:
        frame: The frame to render.
        field_width: Field width in meters.
        field_length: Field length in meters.
        canvas_width: SVG canvas width in pixels.
        canvas_height: SVG canvas height in pixels.

    Returns:
        SVG string for this frame.
    """
    scale_x = canvas_width / field_width
    scale_y = canvas_height / field_length

    svg_parts: list[str] = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{canvas_width}" height="{canvas_height}" '
        f'viewBox="0 0 {canvas_width} {canvas_height}">'
    )

    # Field background
    svg_parts.append(
        f'<rect width="{canvas_width}" height="{canvas_height}" fill="#2d8a2d"/>'
    )

    # Players
    for player in frame.player_positions:
        px = player.get("x", 0.0) * scale_x
        py = player.get("y", 0.0) * scale_y
        pid = player.get("player_id", "")
        svg_parts.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="8" fill="#ffffff" stroke="#000" stroke-width="1"/>'
        )
        svg_parts.append(
            f'<text x="{px:.1f}" y="{py - 10:.1f}" text-anchor="middle" '
            f'font-size="8" fill="#fff">{pid}</text>'
        )

    # Ball
    bx = frame.ball_position.get("x", 0.0) * scale_x
    by = frame.ball_position.get("y", 0.0) * scale_y
    svg_parts.append(
        f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="5" fill="#ffff00" stroke="#000" stroke-width="1"/>'
    )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def render_timeline_frames(timeline: BranchTimeline) -> list[str]:
    """Render all frames of a BranchTimeline as SVG strings.

    Args:
        timeline: The branch timeline to render.

    Returns:
        List of SVG strings, one per frame.
    """
    return [_render_svg_frame(frame) for frame in timeline.frames]


def render_timeline_html(timeline: BranchTimeline) -> str:
    """Render a BranchTimeline as a self-contained HTML animation page.

    Uses JavaScript to cycle through SVG frames at the timeline's fps.

    Args:
        timeline: The branch timeline to render.

    Returns:
        Complete HTML string with embedded animation.
    """
    frames_svg = render_timeline_frames(timeline)

    if not frames_svg:
        return (
            "<!DOCTYPE html><html><body>"
            "<p>No frames to animate.</p>"
            "</body></html>"
        )

    # Escape SVG for embedding in JS
    import json
    frames_json = json.dumps(frames_svg)
    interval_ms = int(1000 / timeline.fps) if timeline.fps > 0 else 100

    html = f"""<!DOCTYPE html>
<html>
<head>
<title>Branch Animation: {timeline.branch_id}</title>
<style>
body {{ margin: 0; display: flex; flex-direction: column; align-items: center; background: #1a1a1a; color: #fff; font-family: sans-serif; }}
#info {{ padding: 1rem; }}
#canvas {{ border: 2px solid #444; }}
</style>
</head>
<body>
<div id="info">
<h2>Branch: {timeline.branch_id} (score: {timeline.composite_score:.3f})</h2>
<p>Frames: {len(frames_svg)} | FPS: {timeline.fps} | Duration: {timeline.duration_seconds:.2f}s</p>
</div>
<div id="canvas"></div>
<script>
const frames = {frames_json};
let idx = 0;
const canvas = document.getElementById('canvas');
function tick() {{
    canvas.innerHTML = frames[idx];
    idx = (idx + 1) % frames.length;
}}
tick();
setInterval(tick, {interval_ms});
</script>
</body>
</html>"""
    return html
