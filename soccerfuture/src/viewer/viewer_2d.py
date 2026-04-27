"""2D viewer rendering functions for the soccer play simulation pipeline.

Pure rendering functions that consume PipelineReport data and produce
matplotlib figures. No I/O or pipeline logic — just visualization.
"""

import matplotlib.axes
import matplotlib.figure
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Rectangle

from src.viewer.constants import (
    ARROW_HEAD_WIDTH,
    BALL_MARKER_COLOR,
    BALL_MARKER_SIZE,
    BRANCH_COLORS,
    CENTER_CIRCLE_COLOR,
    CONTEXT_PANEL_AXES_RECT,
    DEFAULT_ROLE_COLOR,
    EXPLANATION_AXES_RECT,
    FIELD_AXES_RECT,
    FIELD_COLOR,
    FIELD_LENGTH_M,
    FIELD_WIDTH_M,
    FIGURE_HEIGHT,
    FIGURE_WIDTH,
    GOAL_AREA_COLOR,
    LINE_COLOR,
    MIDFIELD_LINE_WIDTH,
    PANEL_TEXT_FONTSIZE,
    PANEL_TITLE_FONTSIZE,
    PENALTY_AREA_COLOR,
    PLAYER_LABEL_FONTSIZE,
    PLAYER_MARKER_SIZE,
    PLAYER_MARKER_SINGLE,
    ROLE_COLORS,
    TELEMETRY_AXES_RECT,
    TELEMETRY_AXES_RECT_SHIFTED,
    TITLE_FONTSIZE,
    TRAJECTORY_LINE_WIDTH,
    TRAJECTORY_LINE_WIDTH_SINGLE,
)
from src.utils.constants import (
    CENTER_CIRCLE_RADIUS,
    CORNER_ARC_RADIUS,
    GOAL_AREA_LENGTH,
    GOAL_AREA_WIDTH,
    PENALTY_AREA_LENGTH,
    PENALTY_AREA_WIDTH,
)


# Goal dimensions (meters) — standard FIFA goal width 7.32m
_GOAL_WIDTH: float = 7.32
_GOAL_DEPTH: float = 2.0


def draw_field(ax: matplotlib.axes.Axes) -> None:
    """Draw a regulation FIFA soccer field on the given axes.

    Renders the main pitch (105 × 68 meters), penalty areas, goal areas,
    center circle, midfield line, corner arcs, and goals.

    Args:
        ax: Matplotlib axes to draw the field on.
    """
    # Main pitch rectangle
    ax.add_patch(Rectangle(
        (0, 0), FIELD_WIDTH_M, FIELD_LENGTH_M,
        facecolor=FIELD_COLOR, edgecolor=LINE_COLOR, linewidth=1,
    ))

    # Midfield line
    ax.axhline(
        y=FIELD_LENGTH_M / 2,
        xmin=0, xmax=1,
        color=LINE_COLOR, linewidth=MIDFIELD_LINE_WIDTH,
    )

    # Center circle
    center_x = FIELD_WIDTH_M / 2
    center_y = FIELD_LENGTH_M / 2
    center_circle = Circle(
        (center_x, center_y), CENTER_CIRCLE_RADIUS,
        fill=False, edgecolor=CENTER_CIRCLE_COLOR, linewidth=1.5,
    )
    ax.add_patch(center_circle)

    # Center spot
    ax.plot(center_x, center_y, "o", color=LINE_COLOR, markersize=3)

    # --- Bottom half (y=0 end) ---
    pa_x_offset = (FIELD_WIDTH_M - PENALTY_AREA_WIDTH) / 2
    ga_x_offset = (FIELD_WIDTH_M - GOAL_AREA_WIDTH) / 2

    # Bottom penalty area
    ax.add_patch(Rectangle(
        (pa_x_offset, 0), PENALTY_AREA_WIDTH, PENALTY_AREA_LENGTH,
        facecolor=PENALTY_AREA_COLOR, edgecolor=LINE_COLOR, linewidth=1,
    ))

    # Bottom goal area
    ax.add_patch(Rectangle(
        (ga_x_offset, 0), GOAL_AREA_WIDTH, GOAL_AREA_LENGTH,
        facecolor=GOAL_AREA_COLOR, edgecolor=LINE_COLOR, linewidth=1,
    ))

    # Bottom penalty spot
    ax.plot(center_x, 11.0, "o", color=LINE_COLOR, markersize=3)

    # Bottom penalty arc (portion outside penalty area)
    bottom_arc = Arc(
        (center_x, 11.0), 2 * CENTER_CIRCLE_RADIUS, 2 * CENTER_CIRCLE_RADIUS,
        angle=0, theta1=37, theta2=143,
        edgecolor=LINE_COLOR, linewidth=1,
    )
    ax.add_patch(bottom_arc)

    # Bottom goal
    goal_x_offset = (FIELD_WIDTH_M - _GOAL_WIDTH) / 2
    ax.add_patch(Rectangle(
        (goal_x_offset, -_GOAL_DEPTH), _GOAL_WIDTH, _GOAL_DEPTH,
        facecolor="none", edgecolor=LINE_COLOR, linewidth=1.5,
    ))

    # --- Top half (y=FIELD_LENGTH_M end) ---

    # Top penalty area
    ax.add_patch(Rectangle(
        (pa_x_offset, FIELD_LENGTH_M - PENALTY_AREA_LENGTH),
        PENALTY_AREA_WIDTH, PENALTY_AREA_LENGTH,
        facecolor=PENALTY_AREA_COLOR, edgecolor=LINE_COLOR, linewidth=1,
    ))

    # Top goal area
    ax.add_patch(Rectangle(
        (ga_x_offset, FIELD_LENGTH_M - GOAL_AREA_LENGTH),
        GOAL_AREA_WIDTH, GOAL_AREA_LENGTH,
        facecolor=GOAL_AREA_COLOR, edgecolor=LINE_COLOR, linewidth=1,
    ))

    # Top penalty spot
    ax.plot(center_x, FIELD_LENGTH_M - 11.0, "o", color=LINE_COLOR, markersize=3)

    # Top penalty arc (portion outside penalty area)
    top_arc = Arc(
        (center_x, FIELD_LENGTH_M - 11.0),
        2 * CENTER_CIRCLE_RADIUS, 2 * CENTER_CIRCLE_RADIUS,
        angle=0, theta1=217, theta2=323,
        edgecolor=LINE_COLOR, linewidth=1,
    )
    ax.add_patch(top_arc)

    # Top goal
    ax.add_patch(Rectangle(
        (goal_x_offset, FIELD_LENGTH_M), _GOAL_WIDTH, _GOAL_DEPTH,
        facecolor="none", edgecolor=LINE_COLOR, linewidth=1.5,
    ))

    # Corner arcs
    for cx, cy, start, end in [
        (0, 0, 0, 90),
        (FIELD_WIDTH_M, 0, 90, 180),
        (0, FIELD_LENGTH_M, 270, 360),
        (FIELD_WIDTH_M, FIELD_LENGTH_M, 180, 270),
    ]:
        corner = Arc(
            (cx, cy), 2 * CORNER_ARC_RADIUS, 2 * CORNER_ARC_RADIUS,
            angle=0, theta1=start, theta2=end,
            edgecolor=LINE_COLOR, linewidth=1,
        )
        ax.add_patch(corner)

    # Axis configuration
    ax.set_xlim(-_GOAL_DEPTH, FIELD_WIDTH_M + _GOAL_DEPTH)
    ax.set_ylim(-_GOAL_DEPTH, FIELD_LENGTH_M + _GOAL_DEPTH)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def draw_ball_position(
    ax: matplotlib.axes.Axes,
    ball_position: dict,
) -> None:
    """Mark the ball position on the field.

    Args:
        ax: Matplotlib axes with the field already drawn.
        ball_position: Dict with keys 'x' and 'y' in meters.
    """
    bx = ball_position.get("x", FIELD_WIDTH_M / 2)
    by = ball_position.get("y", FIELD_LENGTH_M / 2)
    ax.scatter(
        bx, by,
        c=BALL_MARKER_COLOR,
        s=BALL_MARKER_SIZE,
        marker="o",
        zorder=10,
        edgecolors="black",
        linewidths=1.0,
        label="Ball",
    )


def draw_player_positions(
    ax: matplotlib.axes.Axes,
    player_positions: list[dict],
    player_roles: dict[str, str],
) -> None:
    """Render initial player positions on the field.

    Each player is drawn as a colored marker based on their role,
    with the player_id as a text label. A legend maps colors to roles.

    Args:
        ax: Matplotlib axes with the field already drawn.
        player_positions: List of dicts with keys player_id, x, y.
        player_roles: Mapping of player_id to role string (e.g. "GK").
    """
    # Track which roles we've already added to the legend.
    legend_roles: dict[str, object] = {}

    for player in player_positions:
        pid = player["player_id"]
        role = player_roles.get(pid, "")
        color = ROLE_COLORS.get(role, DEFAULT_ROLE_COLOR)

        scatter = ax.scatter(
            player["x"],
            player["y"],
            c=color,
            s=PLAYER_MARKER_SIZE,
            zorder=5,
            edgecolors="white",
            linewidths=0.5,
        )

        # Only add the first scatter per role to the legend.
        label = role or "Unknown"
        if label not in legend_roles:
            legend_roles[label] = scatter

        ax.text(
            player["x"],
            player["y"] + 1,
            pid,
            fontsize=PLAYER_LABEL_FONTSIZE,
            ha="center",
            va="bottom",
            color="white",
            zorder=6,
        )

    # Build legend from unique roles.
    if legend_roles:
        ax.legend(
            legend_roles.values(),
            legend_roles.keys(),
            loc="upper right",
            fontsize=PLAYER_LABEL_FONTSIZE,
            framealpha=0.7,
        )


def _group_positions_by_player(
    positions: list[dict],
) -> dict[str, list[dict]]:
    """Group branch positions by player_id, sorted by timestamp.

    Args:
        positions: List of position dicts with player_id, x, y, timestamp.

    Returns:
        Mapping of player_id to list of positions sorted by timestamp.
    """
    groups: dict[str, list[dict]] = {}
    for pos in positions:
        groups.setdefault(pos["player_id"], []).append(pos)
    for pts in groups.values():
        pts.sort(key=lambda p: p["timestamp"])
    return groups


def draw_branches(
    ax: matplotlib.axes.Axes,
    ranked_branches: list[dict],
) -> None:
    """Render top-K branch trajectories overlaid on the field.

    Each branch gets a distinct color (cycling through BRANCH_COLORS).
    For each player in each branch, draws line segments connecting
    positions sorted by timestamp, with directional arrows on the
    last segment. Adds a legend with branch_id and composite_score.

    Args:
        ax: Matplotlib axes with the field and players already drawn.
        ranked_branches: List of RankedBranch dicts (via to_dict()).
    """
    legend_handles = []
    legend_labels = []

    for idx, rb in enumerate(ranked_branches):
        color = BRANCH_COLORS[idx % len(BRANCH_COLORS)]
        branch = rb.get("branch", {})
        positions = branch.get("positions", [])
        player_groups = _group_positions_by_player(positions)

        for pts in player_groups.values():
            if len(pts) < 2:
                continue

            xs = [p["x"] for p in pts]
            ys = [p["y"] for p in pts]
            ax.plot(
                xs, ys,
                color=color,
                linewidth=TRAJECTORY_LINE_WIDTH,
                zorder=3,
            )

            # Directional arrow on the last segment.
            ax.annotate(
                "",
                xy=(xs[-1], ys[-1]),
                xytext=(xs[-2], ys[-2]),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=color,
                    lw=TRAJECTORY_LINE_WIDTH,
                    mutation_scale=ARROW_HEAD_WIDTH * 15,
                ),
                zorder=4,
            )

        branch_id = rb.get("branch_id", f"branch-{idx}")
        score = rb.get("composite_score", 0.0)
        handle = ax.plot([], [], color=color, linewidth=TRAJECTORY_LINE_WIDTH)[0]
        legend_handles.append(handle)
        legend_labels.append(f"{branch_id} ({score:.2f})")

    if legend_handles:
        ax.legend(
            legend_handles,
            legend_labels,
            loc="lower right",
            fontsize=PLAYER_LABEL_FONTSIZE,
            framealpha=0.7,
            title="Branches",
        )


def draw_single_branch(
    ax: matplotlib.axes.Axes,
    ranked_branch: dict,
    color: str,
) -> None:
    """Render a single branch with enhanced visual emphasis.

    Uses larger markers and thicker lines than draw_branches for
    improved visibility when inspecting an individual branch.

    Args:
        ax: Matplotlib axes with the field already drawn.
        ranked_branch: Single RankedBranch dict (via to_dict()).
        color: Color string for the trajectories.
    """
    branch = ranked_branch.get("branch", {})
    positions = branch.get("positions", [])
    player_groups = _group_positions_by_player(positions)

    for pts in player_groups.values():
        if len(pts) < 2:
            continue

        xs = [p["x"] for p in pts]
        ys = [p["y"] for p in pts]

        # Enhanced marker at each position.
        ax.scatter(
            xs, ys,
            c=color,
            s=PLAYER_MARKER_SINGLE,
            zorder=5,
            edgecolors="white",
            linewidths=0.5,
        )

        # Thicker trajectory line.
        ax.plot(
            xs, ys,
            color=color,
            linewidth=TRAJECTORY_LINE_WIDTH_SINGLE,
            zorder=3,
        )

        # Directional arrow on the last segment.
        ax.annotate(
            "",
            xy=(xs[-1], ys[-1]),
            xytext=(xs[-2], ys[-2]),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                lw=TRAJECTORY_LINE_WIDTH_SINGLE,
                mutation_scale=ARROW_HEAD_WIDTH * 15,
            ),
            zorder=4,
        )


_GAME_PHASE_LABELS: dict[str, str] = {
    "open_play": "Open Play",
    "set_piece": "Set Piece",
    "transition": "Transition",
    "dead_ball": "Dead Ball",
}


def draw_scenario_info(
    fig: matplotlib.figure.Figure,
    play_state: dict,
) -> None:
    """Render contextual scenario information as the figure's suptitle.

    Displays match time, possession team, game phase, score differential,
    and optionally formation and description from play_state metadata.

    Args:
        fig: Matplotlib figure to set the title on.
        play_state: Dict of PlayState (via play_state_to_dict).
    """
    match_time = play_state.get("match_time", 0.0)
    possession_team = play_state.get("possession_team", "Unknown")
    game_phase = play_state.get("game_phase", "open_play")
    score_diff = play_state.get("score_differential", 0)
    metadata = play_state.get("metadata", {}) or {}

    phase_label = _GAME_PHASE_LABELS.get(game_phase, game_phase)
    title = f"{int(match_time)}' — {possession_team} possession  |  {phase_label}"

    # Score differential.
    title += f"  |  Score diff: {score_diff:+d}"

    # Optional formation.
    formation = metadata.get("formation")
    if formation:
        title += f"  |  {formation}"

    # Optional description.
    description = metadata.get("description")
    if description:
        title += f"\n{description}"

    fig.suptitle(title, fontsize=TITLE_FONTSIZE)


def draw_explanation_panel(
    ax: matplotlib.axes.Axes,
    ranked_branches: list[dict],
) -> None:
    """Render the ranking explanation panel for the top-K branches.

    For each branch, displays branch_id, validity_score, opportunity_score,
    composite_score, promoted/penalized factors, top/bottom scoring blocks,
    and near_threshold_warning when present.

    Args:
        ax: Matplotlib axes dedicated to the explanation panel.
        ranked_branches: List of RankedBranch dicts (via to_dict()).
    """
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.0, 0.97, "Ranking Explanation", fontsize=PANEL_TITLE_FONTSIZE,
            fontweight="bold", va="top", transform=ax.transAxes)

    y = 0.90
    line_step = 0.055

    for rb in ranked_branches:
        if y < 0.0:
            break

        branch_id = rb.get("branch_id", "?")
        composite = rb.get("composite_score", 0.0)
        report = rb.get("evaluation_report", {}) or {}
        validity = report.get("validity_score", 0.0)
        opportunity = report.get("opportunity_score", 0.0)
        explanation = report.get("ranking_explanation", {}) or {}

        # Branch header
        ax.text(0.0, y, f"{branch_id}  composite={composite:.2f}",
                fontsize=PANEL_TEXT_FONTSIZE, fontweight="bold",
                va="top", transform=ax.transAxes)
        y -= line_step

        # Scores
        ax.text(0.02, y,
                f"validity={validity:.2f}  opportunity={opportunity:.2f}",
                fontsize=PANEL_TEXT_FONTSIZE, va="top",
                transform=ax.transAxes)
        y -= line_step

        # Promoted / penalized factors
        promoted = explanation.get("promoted_factors", [])
        penalized = explanation.get("penalized_factors", [])
        if promoted:
            ax.text(0.02, y, f"+ {', '.join(promoted)}",
                    fontsize=PANEL_TEXT_FONTSIZE, color="green",
                    va="top", transform=ax.transAxes)
            y -= line_step
        if penalized:
            ax.text(0.02, y, f"- {', '.join(penalized)}",
                    fontsize=PANEL_TEXT_FONTSIZE, color="red",
                    va="top", transform=ax.transAxes)
            y -= line_step

        # Top / bottom scoring blocks
        top_block = explanation.get("top_scoring_block", "")
        bottom_block = explanation.get("bottom_scoring_block", "")
        if top_block or bottom_block:
            ax.text(0.02, y,
                    f"top: {top_block}  |  bottom: {bottom_block}",
                    fontsize=PANEL_TEXT_FONTSIZE, va="top",
                    transform=ax.transAxes)
            y -= line_step

        # Near-threshold warning (visually emphasised)
        warning = explanation.get("near_threshold_warning")
        if warning:
            ax.text(0.02, y, f"\u26a0 {warning}",
                    fontsize=PANEL_TEXT_FONTSIZE, fontweight="bold",
                    color="#FF8C00", va="top", transform=ax.transAxes)
            y -= line_step

        # Spacer between branches
        y -= line_step * 0.5


def draw_telemetry_panel(
    ax: matplotlib.axes.Axes,
    metadata: dict,
) -> None:
    """Render the pipeline telemetry panel.

    Displays branches_generated, hard_fail_count, score_filtered_count,
    avg_score_by_strategy, and time_per_stage. Shows a fallback message
    when telemetry data is not present in metadata.

    Args:
        ax: Matplotlib axes dedicated to the telemetry panel.
        metadata: Dict of metadata from PipelineReport.
    """
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.0, 0.97, "Pipeline Telemetry", fontsize=PANEL_TITLE_FONTSIZE,
            fontweight="bold", va="top", transform=ax.transAxes)

    telemetry = (metadata or {}).get("telemetry")
    if not telemetry:
        ax.text(0.0, 0.82, "Telemetry data not available",
                fontsize=PANEL_TEXT_FONTSIZE, va="top",
                transform=ax.transAxes)
        return

    y = 0.85
    step = 0.065

    # Scalar counters
    ax.text(0.0, y,
            f"Branches generated: {telemetry.get('branches_generated', 'N/A')}",
            fontsize=PANEL_TEXT_FONTSIZE, va="top", transform=ax.transAxes)
    y -= step
    ax.text(0.0, y,
            f"Hard fails: {telemetry.get('hard_fail_count', 'N/A')}",
            fontsize=PANEL_TEXT_FONTSIZE, va="top", transform=ax.transAxes)
    y -= step
    ax.text(0.0, y,
            f"Score filtered: {telemetry.get('score_filtered_count', 'N/A')}",
            fontsize=PANEL_TEXT_FONTSIZE, va="top", transform=ax.transAxes)
    y -= step

    # Avg score by strategy
    avg_scores = telemetry.get("avg_score_by_strategy", {})
    if avg_scores:
        ax.text(0.0, y, "Avg score by strategy:",
                fontsize=PANEL_TEXT_FONTSIZE, fontweight="bold",
                va="top", transform=ax.transAxes)
        y -= step
        for strategy, score in avg_scores.items():
            ax.text(0.02, y, f"{strategy}: {score:.2f}",
                    fontsize=PANEL_TEXT_FONTSIZE, va="top",
                    transform=ax.transAxes)
            y -= step

    # Time per stage
    time_stages = telemetry.get("time_per_stage", {})
    if time_stages:
        ax.text(0.0, y, "Time per stage:",
                fontsize=PANEL_TEXT_FONTSIZE, fontweight="bold",
                va="top", transform=ax.transAxes)
        y -= step
        for stage, secs in time_stages.items():
            ax.text(0.02, y, f"{stage}: {secs:.2f}s",
                    fontsize=PANEL_TEXT_FONTSIZE, va="top",
                    transform=ax.transAxes)
            y -= step


def draw_match_context_panel(
    ax: matplotlib.axes.Axes,
    match_context: dict | None,
    context_signals: dict | None,
) -> None:
    """Render the optional match context panel.

    Displays pre-match context information including teams, competition,
    lookback window, comparative edges, cache status, and derived notes.
    Shows a fallback message when no context is available.

    Args:
        ax: Matplotlib axes dedicated to the context panel.
        match_context: Serialized MatchContext dict, or None.
        context_signals: Serialized ContextSignals dict, or None.
    """
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.0, 0.97, "Match Context", fontsize=PANEL_TITLE_FONTSIZE,
            fontweight="bold", va="top", transform=ax.transAxes)

    if match_context is None:
        ax.text(0.0, 0.82, "No match context available",
                fontsize=PANEL_TEXT_FONTSIZE, va="top",
                transform=ax.transAxes)
        return

    y = 0.85
    step = 0.065

    # Teams
    home = match_context.get("home_team", "?")
    away = match_context.get("away_team", "?")
    ax.text(0.0, y, f"{home} vs {away}",
            fontsize=PANEL_TEXT_FONTSIZE, fontweight="bold",
            va="top", transform=ax.transAxes)
    y -= step

    # Competition / season
    comp = match_context.get("competition")
    season = match_context.get("season")
    if comp or season:
        parts = [p for p in [comp, season] if p]
        ax.text(0.0, y, " | ".join(parts),
                fontsize=PANEL_TEXT_FONTSIZE, va="top",
                transform=ax.transAxes)
        y -= step

    # Lookback
    lookback = match_context.get("lookback_matches", 0)
    ax.text(0.0, y, f"Lookback: {lookback} matches",
            fontsize=PANEL_TEXT_FONTSIZE, va="top",
            transform=ax.transAxes)
    y -= step

    # Comparative edges
    comp_signals = match_context.get("comparative_signals", {})
    if comp_signals:
        edges = []
        for key in ("stronger_team", "form_edge", "attack_edge", "defense_edge"):
            val = comp_signals.get(key)
            if val:
                label = key.replace("_", " ").title()
                edges.append(f"{label}: {val}")
        if edges:
            ax.text(0.0, y, "Edges: " + "; ".join(edges),
                    fontsize=PANEL_TEXT_FONTSIZE, va="top",
                    transform=ax.transAxes)
            y -= step

    # Cache status
    cache = match_context.get("cache_status", "unknown")
    source = match_context.get("source", "unknown")
    ax.text(0.0, y, f"Source: {source}  |  Cache: {cache}",
            fontsize=PANEL_TEXT_FONTSIZE, va="top",
            transform=ax.transAxes)
    y -= step

    # Context signal notes (show up to 3)
    if context_signals:
        signal_notes = context_signals.get("notes", [])
        for note in signal_notes[:3]:
            if y < 0.0:
                break
            ax.text(0.02, y, f"\u2022 {note}",
                    fontsize=PANEL_TEXT_FONTSIZE, va="top",
                    color="#555555", transform=ax.transAxes)
            y -= step


def render_pipeline_report(
    report_dict: dict,
) -> matplotlib.figure.Figure:
    """Render a complete visualization of a PipelineReport.

    Composes the field with initial player positions, ball position,
    top-K branch trajectories, ranking explanation panel, telemetry
    panel, and scenario info into a single matplotlib figure.

    Args:
        report_dict: Dict of PipelineReport (via to_dict()).

    Returns:
        Matplotlib figure with the complete visualization.
    """
    play_state = report_dict.get("play_state", {})
    ranked_branches = report_dict.get("ranked_branches", [])
    metadata = report_dict.get("metadata", {})
    mc = report_dict.get("match_context")
    cs = report_dict.get("context_signals")
    has_context = mc is not None

    fig = plt.figure(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # Field panel
    field_ax = fig.add_axes(FIELD_AXES_RECT)
    draw_field(field_ax)
    draw_ball_position(
        field_ax,
        play_state.get("ball_position", {"x": FIELD_WIDTH_M / 2, "y": FIELD_LENGTH_M / 2}),
    )
    draw_player_positions(
        field_ax,
        play_state.get("player_positions", []),
        play_state.get("player_roles", {}),
    )
    draw_branches(field_ax, ranked_branches)

    # Explanation panel
    explanation_ax = fig.add_axes(EXPLANATION_AXES_RECT)
    draw_explanation_panel(explanation_ax, ranked_branches)

    # Telemetry panel — shift up if context panel is shown
    telemetry_rect = TELEMETRY_AXES_RECT_SHIFTED if has_context else TELEMETRY_AXES_RECT
    telemetry_ax = fig.add_axes(telemetry_rect)
    draw_telemetry_panel(telemetry_ax, metadata)

    # Context panel (only when match_context is present)
    if has_context:
        context_ax = fig.add_axes(CONTEXT_PANEL_AXES_RECT)
        draw_match_context_panel(context_ax, mc, cs)

    # Scenario info as figure title
    draw_scenario_info(fig, play_state)

    return fig


def render_single_branch(
    report_dict: dict,
    branch_index: int,
) -> matplotlib.figure.Figure:
    """Render a focused visualization of a single ranked branch.

    Displays the field with the selected branch's trajectories drawn
    with enhanced visibility, and the full ranking explanation for
    that branch in the side panel.

    Args:
        report_dict: Dict of PipelineReport (via to_dict()).
        branch_index: Zero-based index into ranked_branches.

    Returns:
        Matplotlib figure with the single-branch visualization.

    Raises:
        ValueError: If ranked_branches is empty.
        IndexError: If branch_index is out of range.
    """
    ranked_branches = report_dict.get("ranked_branches", [])

    if not ranked_branches:
        raise ValueError("ranked_branches is empty")
    if branch_index < 0 or branch_index >= len(ranked_branches):
        raise IndexError(
            f"branch_index {branch_index} out of range for "
            f"{len(ranked_branches)} branches"
        )

    play_state = report_dict.get("play_state", {})
    metadata = report_dict.get("metadata", {})
    mc = report_dict.get("match_context")
    cs = report_dict.get("context_signals")
    has_context = mc is not None
    selected = ranked_branches[branch_index]
    color = BRANCH_COLORS[branch_index % len(BRANCH_COLORS)]

    fig = plt.figure(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # Field panel
    field_ax = fig.add_axes(FIELD_AXES_RECT)
    draw_field(field_ax)
    draw_ball_position(
        field_ax,
        play_state.get("ball_position", {"x": FIELD_WIDTH_M / 2, "y": FIELD_LENGTH_M / 2}),
    )
    draw_player_positions(
        field_ax,
        play_state.get("player_positions", []),
        play_state.get("player_roles", {}),
    )
    draw_single_branch(field_ax, selected, color)

    # Explanation panel — show only the selected branch
    explanation_ax = fig.add_axes(EXPLANATION_AXES_RECT)
    draw_explanation_panel(explanation_ax, [selected])

    # Telemetry panel — shift up if context panel is shown
    telemetry_rect = TELEMETRY_AXES_RECT_SHIFTED if has_context else TELEMETRY_AXES_RECT
    telemetry_ax = fig.add_axes(telemetry_rect)
    draw_telemetry_panel(telemetry_ax, metadata)

    # Context panel (only when match_context is present)
    if has_context:
        context_ax = fig.add_axes(CONTEXT_PANEL_AXES_RECT)
        draw_match_context_panel(context_ax, mc, cs)

    # Scenario info as figure title
    draw_scenario_info(fig, play_state)

    return fig
