"""Tests for field rendering functions in src/viewer/viewer_2d.py.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 11.6
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.figure
import matplotlib.pyplot as plt
import pytest
from matplotlib.patches import Arc, Circle, Rectangle

from src.viewer.constants import (
    FIELD_LENGTH_M,
    FIELD_WIDTH_M,
    PLAYER_MARKER_SINGLE,
    TRAJECTORY_LINE_WIDTH,
    TRAJECTORY_LINE_WIDTH_SINGLE,
)
from src.viewer.viewer_2d import (
    draw_ball_position,
    draw_branches,
    draw_explanation_panel,
    draw_field,
    draw_match_context_panel,
    draw_player_positions,
    draw_scenario_info,
    draw_single_branch,
    draw_telemetry_panel,
    render_pipeline_report,
    render_single_branch,
)


class TestDrawField:
    """Validates Requirements 8.1, 8.2 — FIFA soccer field rendering."""

    def test_axis_limits_cover_field(self) -> None:
        """Requirement 8.1: field axes encompass the full pitch."""
        fig, ax = plt.subplots()
        draw_field(ax)

        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        # Must include the full pitch (0..68 x, 0..105 y)
        assert xlim[0] <= 0 and xlim[1] >= FIELD_WIDTH_M
        assert ylim[0] <= 0 and ylim[1] >= FIELD_LENGTH_M
        plt.close(fig)

    def test_main_pitch_rectangle(self) -> None:
        """Requirement 8.1: main pitch rectangle is 68 × 105 meters."""
        fig, ax = plt.subplots()
        draw_field(ax)

        rects = [p for p in ax.patches if isinstance(p, Rectangle)]
        main = [
            r for r in rects
            if r.get_xy() == (0, 0)
            and r.get_width() == FIELD_WIDTH_M
            and r.get_height() == FIELD_LENGTH_M
        ]
        assert len(main) == 1, "Expected exactly one main pitch rectangle at (0,0)"
        plt.close(fig)

    def test_penalty_areas_present(self) -> None:
        """Requirement 8.1: two penalty areas rendered."""
        fig, ax = plt.subplots()
        draw_field(ax)

        rects = [p for p in ax.patches if isinstance(p, Rectangle)]
        # Penalty areas have height 16.5
        penalty_rects = [r for r in rects if abs(r.get_height() - 16.5) < 0.01]
        assert len(penalty_rects) == 2, f"Expected 2 penalty area rects, got {len(penalty_rects)}"
        plt.close(fig)

    def test_goal_areas_present(self) -> None:
        """Requirement 8.1: two goal areas rendered."""
        fig, ax = plt.subplots()
        draw_field(ax)

        rects = [p for p in ax.patches if isinstance(p, Rectangle)]
        # Goal areas have height 5.5
        goal_rects = [r for r in rects if abs(r.get_height() - 5.5) < 0.01]
        assert len(goal_rects) == 2, f"Expected 2 goal area rects, got {len(goal_rects)}"
        plt.close(fig)

    def test_center_circle_present(self) -> None:
        """Requirement 8.1: center circle rendered."""
        fig, ax = plt.subplots()
        draw_field(ax)

        circles = [p for p in ax.patches if isinstance(p, Circle)]
        assert len(circles) >= 1, "Expected at least one center circle"
        plt.close(fig)

    def test_midfield_line_present(self) -> None:
        """Requirement 8.1: midfield line at y = 52.5."""
        fig, ax = plt.subplots()
        draw_field(ax)

        midfield_y = FIELD_LENGTH_M / 2
        found = False
        for line in ax.lines:
            ydata = line.get_ydata()
            if len(set(ydata)) == 1 and abs(float(ydata[0]) - midfield_y) < 0.01:
                found = True
                break
        assert found, f"Missing midfield line at y={midfield_y}"
        plt.close(fig)

    def test_corner_arcs_present(self) -> None:
        """Requirement 8.1: corner arcs rendered."""
        fig, ax = plt.subplots()
        draw_field(ax)

        arcs = [p for p in ax.patches if isinstance(p, Arc)]
        # At least 4 corner arcs + 2 penalty arcs
        assert len(arcs) >= 4, f"Expected at least 4 arcs, got {len(arcs)}"
        plt.close(fig)

    def test_no_end_zones(self) -> None:
        """Requirement 8.2: no end zone rectangles."""
        fig, ax = plt.subplots()
        draw_field(ax)

        rects = [p for p in ax.patches if isinstance(p, Rectangle)]
        # No rectangle should have the old end zone depth of 10 meters
        end_zone_rects = [r for r in rects if abs(r.get_height() - 10.0) < 0.01]
        assert len(end_zone_rects) == 0, "Should not have end zone rectangles"
        plt.close(fig)

    def test_aspect_ratio_equal(self) -> None:
        """Requirement 8.1: aspect ratio is set to equal."""
        fig, ax = plt.subplots()
        draw_field(ax)

        aspect = ax.get_aspect()
        assert aspect == 1.0 or aspect == "equal"
        plt.close(fig)


class TestDrawBallPosition:
    """Validates Requirement 8.6 — draw_ball_position marks ball on field."""

    def test_adds_scatter_collection(self) -> None:
        fig, ax = plt.subplots()
        collections_before = len(ax.collections)
        draw_ball_position(ax, {"x": 34.0, "y": 52.5})
        assert len(ax.collections) - collections_before == 1
        plt.close(fig)

    def test_defaults_to_center_when_keys_missing(self) -> None:
        fig, ax = plt.subplots()
        draw_ball_position(ax, {})
        assert len(ax.collections) >= 1
        plt.close(fig)


# --- Sample data for player/branch tests ---

SAMPLE_PLAYER_POSITIONS = [
    {"player_id": "GK1", "x": 34.0, "y": 5.0},
    {"player_id": "ST1", "x": 34.0, "y": 80.0},
]

SAMPLE_PLAYER_ROLES = {"GK1": "GK", "ST1": "ST"}

SAMPLE_RANKED_BRANCHES = [
    {
        "branch_id": "gen-001",
        "composite_score": 0.62,
        "branch": {
            "positions": [
                {"player_id": "ST1", "x": 34.0, "y": 82.0, "timestamp": 2.0},
                {"player_id": "ST1", "x": 35.0, "y": 88.0, "timestamp": 2.5},
            ]
        },
    }
]


class TestDrawPlayerPositions:
    """Validates Requirements 8.1 — player markers, role colors, labels."""

    def test_scatter_artists_created(self) -> None:
        fig, ax = plt.subplots()
        draw_field(ax)
        draw_player_positions(ax, SAMPLE_PLAYER_POSITIONS, SAMPLE_PLAYER_ROLES)

        assert len(ax.collections) >= len(SAMPLE_PLAYER_POSITIONS)
        plt.close(fig)

    def test_scatter_count_matches_players(self) -> None:
        fig, ax = plt.subplots()
        collections_before = len(ax.collections)
        draw_player_positions(ax, SAMPLE_PLAYER_POSITIONS, SAMPLE_PLAYER_ROLES)

        added = len(ax.collections) - collections_before
        assert added == len(SAMPLE_PLAYER_POSITIONS)
        plt.close(fig)

    def test_player_labels_present(self) -> None:
        fig, ax = plt.subplots()
        draw_player_positions(ax, SAMPLE_PLAYER_POSITIONS, SAMPLE_PLAYER_ROLES)

        text_contents = [t.get_text() for t in ax.texts]
        for player in SAMPLE_PLAYER_POSITIONS:
            assert player["player_id"] in text_contents, (
                f"Missing label for {player['player_id']}"
            )
        plt.close(fig)

    def test_role_differentiation(self) -> None:
        fig, ax = plt.subplots()
        draw_player_positions(ax, SAMPLE_PLAYER_POSITIONS, SAMPLE_PLAYER_ROLES)

        colors = []
        for coll in ax.collections:
            fc = coll.get_facecolor()
            if len(fc) > 0:
                colors.append(tuple(fc[0]))

        assert len(set(colors)) >= 2, "Expected distinct colors for different roles"
        plt.close(fig)


class TestDrawBranches:
    """Validates Requirements 8.1 — branch trajectories and legend."""

    def test_line_artists_created(self) -> None:
        fig, ax = plt.subplots()
        lines_before = len(ax.lines)
        draw_branches(ax, SAMPLE_RANKED_BRANCHES)

        lines_added = len(ax.lines) - lines_before
        assert lines_added >= 1, f"Expected line artists, got {lines_added} new lines"
        plt.close(fig)

    def test_trajectory_line_width(self) -> None:
        fig, ax = plt.subplots()
        draw_branches(ax, SAMPLE_RANKED_BRANCHES)

        trajectory_lines = [
            line for line in ax.lines
            if len(line.get_xdata()) > 1
        ]
        assert len(trajectory_lines) >= 1
        for line in trajectory_lines:
            assert line.get_linewidth() == TRAJECTORY_LINE_WIDTH
        plt.close(fig)

    def test_legend_contains_branch_info(self) -> None:
        fig, ax = plt.subplots()
        draw_branches(ax, SAMPLE_RANKED_BRANCHES)

        legend = ax.get_legend()
        assert legend is not None, "Expected a legend for branches"
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert any("gen-001" in t for t in legend_texts)
        assert any("0.62" in t for t in legend_texts)
        plt.close(fig)

    def test_multiple_branches_distinct_colors(self) -> None:
        second_branch = {
            "branch_id": "gen-002",
            "composite_score": 0.45,
            "branch": {
                "positions": [
                    {"player_id": "GK1", "x": 34.0, "y": 8.0, "timestamp": 2.0},
                    {"player_id": "GK1", "x": 34.0, "y": 10.0, "timestamp": 2.5},
                ]
            },
        }
        branches = SAMPLE_RANKED_BRANCHES + [second_branch]

        fig, ax = plt.subplots()
        draw_branches(ax, branches)

        trajectory_lines = [
            line for line in ax.lines
            if len(line.get_xdata()) > 1
        ]
        colors = [line.get_color() for line in trajectory_lines]
        assert len(set(colors)) >= 2, "Expected distinct colors for different branches"
        plt.close(fig)


class TestDrawSingleBranch:
    """Validates Requirements 8.1, 8.2 — single branch with enhanced visibility."""

    def test_scatter_uses_enhanced_marker_size(self) -> None:
        fig, ax = plt.subplots()
        draw_single_branch(ax, SAMPLE_RANKED_BRANCHES[0], "#1F77B4")

        assert len(ax.collections) >= 1, "Expected scatter collections"
        for coll in ax.collections:
            sizes = coll.get_sizes()
            if len(sizes) > 0:
                for s in sizes:
                    assert s == PLAYER_MARKER_SINGLE
        plt.close(fig)

    def test_line_uses_enhanced_width(self) -> None:
        fig, ax = plt.subplots()
        draw_single_branch(ax, SAMPLE_RANKED_BRANCHES[0], "#1F77B4")

        trajectory_lines = [
            line for line in ax.lines
            if len(line.get_xdata()) > 1
        ]
        assert len(trajectory_lines) >= 1
        for line in trajectory_lines:
            assert line.get_linewidth() == TRAJECTORY_LINE_WIDTH_SINGLE
        plt.close(fig)

    def test_creates_both_scatter_and_line_artists(self) -> None:
        fig, ax = plt.subplots()
        draw_single_branch(ax, SAMPLE_RANKED_BRANCHES[0], "#FF7F0E")

        assert len(ax.collections) >= 1
        trajectory_lines = [
            line for line in ax.lines
            if len(line.get_xdata()) > 1
        ]
        assert len(trajectory_lines) >= 1
        plt.close(fig)


# --- Sample data for panel tests ---

SAMPLE_PLAY_STATE = {
    "match_time": 45.0,
    "possession_team": "home",
    "game_phase": "open_play",
    "ball_position": {"x": 34.0, "y": 52.5},
    "score_differential": 1,
    "metadata": {"formation": "4-3-3", "description": "Counter attack from midfield"},
}

SAMPLE_EXPLANATION_BRANCHES = [
    {
        "branch_id": "gen-001",
        "composite_score": 0.62,
        "evaluation_report": {
            "validity_score": 0.78,
            "opportunity_score": 0.46,
            "ranking_explanation": {
                "promoted_factors": ["Physical Speed"],
                "penalized_factors": ["Turnover Risk"],
                "top_scoring_block": "Physical Speed",
                "bottom_scoring_block": "Turnover Risk",
                "near_threshold_warning": None,
            },
        },
    }
]


def _collect_ax_text(ax) -> str:
    """Join all text artists on an axes into a single string."""
    return " ".join(t.get_text() for t in ax.texts)


class TestDrawScenarioInfo:
    """Validates Requirement 8.5 — scenario context in suptitle with soccer fields."""

    def test_suptitle_contains_match_time(self) -> None:
        """Requirement 8.5: suptitle includes match_time."""
        fig, _ = plt.subplots()
        draw_scenario_info(fig, SAMPLE_PLAY_STATE)

        title = fig._suptitle.get_text()
        assert "45" in title
        plt.close(fig)

    def test_suptitle_contains_possession_team(self) -> None:
        """Requirement 8.5: suptitle includes possession_team."""
        fig, _ = plt.subplots()
        draw_scenario_info(fig, SAMPLE_PLAY_STATE)

        title = fig._suptitle.get_text()
        assert "home" in title
        plt.close(fig)

    def test_suptitle_contains_game_phase(self) -> None:
        """Requirement 8.5: suptitle includes game_phase label."""
        fig, _ = plt.subplots()
        draw_scenario_info(fig, SAMPLE_PLAY_STATE)

        title = fig._suptitle.get_text()
        assert "Open Play" in title
        plt.close(fig)

    def test_suptitle_contains_score_differential(self) -> None:
        """Requirement 8.5: suptitle includes score differential."""
        fig, _ = plt.subplots()
        draw_scenario_info(fig, SAMPLE_PLAY_STATE)

        title = fig._suptitle.get_text()
        assert "+1" in title
        plt.close(fig)

    def test_suptitle_contains_formation(self) -> None:
        """Requirement 8.5: suptitle includes formation when present."""
        fig, _ = plt.subplots()
        draw_scenario_info(fig, SAMPLE_PLAY_STATE)

        title = fig._suptitle.get_text()
        assert "4-3-3" in title
        plt.close(fig)

    def test_suptitle_contains_description(self) -> None:
        """Requirement 8.5: suptitle includes description when present."""
        fig, _ = plt.subplots()
        draw_scenario_info(fig, SAMPLE_PLAY_STATE)

        title = fig._suptitle.get_text()
        assert "Counter attack from midfield" in title
        plt.close(fig)


class TestDrawExplanationPanel:
    """Validates Requirements 8.1 — explanation panel text content."""

    def test_axis_is_off(self) -> None:
        fig, ax = plt.subplots()
        draw_explanation_panel(ax, SAMPLE_EXPLANATION_BRANCHES)

        assert not ax.axison
        plt.close(fig)

    def test_branch_id_displayed(self) -> None:
        fig, ax = plt.subplots()
        draw_explanation_panel(ax, SAMPLE_EXPLANATION_BRANCHES)

        text = _collect_ax_text(ax)
        assert "gen-001" in text
        plt.close(fig)

    def test_composite_score_displayed(self) -> None:
        fig, ax = plt.subplots()
        draw_explanation_panel(ax, SAMPLE_EXPLANATION_BRANCHES)

        text = _collect_ax_text(ax)
        assert "0.62" in text
        plt.close(fig)

    def test_validity_score_displayed(self) -> None:
        fig, ax = plt.subplots()
        draw_explanation_panel(ax, SAMPLE_EXPLANATION_BRANCHES)

        text = _collect_ax_text(ax)
        assert "0.78" in text
        plt.close(fig)

    def test_opportunity_score_displayed(self) -> None:
        fig, ax = plt.subplots()
        draw_explanation_panel(ax, SAMPLE_EXPLANATION_BRANCHES)

        text = _collect_ax_text(ax)
        assert "0.46" in text
        plt.close(fig)

    def test_promoted_factors_displayed(self) -> None:
        fig, ax = plt.subplots()
        draw_explanation_panel(ax, SAMPLE_EXPLANATION_BRANCHES)

        text = _collect_ax_text(ax)
        assert "Physical Speed" in text
        plt.close(fig)

    def test_penalized_factors_displayed(self) -> None:
        fig, ax = plt.subplots()
        draw_explanation_panel(ax, SAMPLE_EXPLANATION_BRANCHES)

        text = _collect_ax_text(ax)
        assert "Turnover Risk" in text
        plt.close(fig)


class TestDrawTelemetryPanelInViewer:
    """Validates Requirements 8.1 — minimal telemetry panel tests."""

    def test_telemetry_data_rendered(self) -> None:
        fig, ax = plt.subplots()
        metadata = {
            "telemetry": {
                "branches_generated": 20,
                "hard_fail_count": 3,
                "score_filtered_count": 2,
                "avg_score_by_strategy": {"route_variation": 0.45},
                "time_per_stage": {"generation": 0.12},
            }
        }
        draw_telemetry_panel(ax, metadata)

        text = _collect_ax_text(ax)
        assert "20" in text
        assert "route_variation" in text
        plt.close(fig)

    def test_fallback_when_telemetry_missing(self) -> None:
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, {})

        text = _collect_ax_text(ax)
        assert "Telemetry data not available" in text
        plt.close(fig)


# --- Sample data for composition function tests ---

SAMPLE_REPORT_DICT = {
    "play_state": {
        "match_time": 45.0,
        "possession_team": "home",
        "game_phase": "open_play",
        "ball_position": {"x": 34.0, "y": 52.5},
        "score_differential": 0,
        "player_positions": [
            {"player_id": "GK1", "x": 34.0, "y": 5.0},
        ],
        "player_roles": {"GK1": "GK"},
        "metadata": {},
    },
    "ranked_branches": [
        {
            "branch_id": "gen-001",
            "composite_score": 0.62,
            "evaluation_report": {
                "validity_score": 0.78,
                "opportunity_score": 0.46,
                "ranking_explanation": {
                    "promoted_factors": ["Physical Speed"],
                    "penalized_factors": [],
                    "top_scoring_block": "Physical Speed",
                    "bottom_scoring_block": "Turnover Risk",
                    "near_threshold_warning": None,
                },
            },
            "branch": {
                "positions": [
                    {"player_id": "GK1", "x": 34.0, "y": 7.0, "timestamp": 2.0},
                    {"player_id": "GK1", "x": 34.0, "y": 9.0, "timestamp": 2.5},
                ]
            },
        }
    ],
    "metadata": {
        "telemetry": {
            "branches_generated": 20,
            "hard_fail_count": 0,
            "score_filtered_count": 0,
            "avg_score_by_strategy": {},
            "time_per_stage": {},
        }
    },
}


class TestDrawMatchContextPanel:
    """Validates match context panel rendering."""

    def test_no_context_shows_fallback(self) -> None:
        """When match_context is None, panel shows fallback message."""
        fig, ax = plt.subplots()
        draw_match_context_panel(ax, None, None)

        text = _collect_ax_text(ax)
        assert "No match context available" in text
        plt.close(fig)

    def test_with_context_shows_teams(self) -> None:
        """When match_context is provided, panel shows team names."""
        fig, ax = plt.subplots()
        mc = {
            "home_team": "FC Porto",
            "away_team": "SL Benfica",
            "lookback_matches": 10,
            "source": "soccerdata",
            "cache_status": "hit",
            "comparative_signals": {"stronger_team": "FC Porto"},
        }
        draw_match_context_panel(ax, mc, None)

        text = _collect_ax_text(ax)
        assert "FC Porto" in text
        assert "SL Benfica" in text
        plt.close(fig)

    def test_with_context_shows_cache_status(self) -> None:
        """Cache status appears in the panel text."""
        fig, ax = plt.subplots()
        mc = {
            "home_team": "TeamA",
            "away_team": "TeamB",
            "lookback_matches": 5,
            "source": "soccerdata",
            "cache_status": "miss",
            "comparative_signals": {},
        }
        draw_match_context_panel(ax, mc, None)

        text = _collect_ax_text(ax)
        assert "miss" in text
        plt.close(fig)

    def test_with_context_shows_notes(self) -> None:
        """Context signal notes appear in the panel text."""
        fig, ax = plt.subplots()
        mc = {
            "home_team": "TeamA",
            "away_team": "TeamB",
            "lookback_matches": 5,
            "source": "soccerdata",
            "cache_status": "hit",
            "comparative_signals": {},
        }
        cs = {"notes": ["Home team has attacking edge"], "aggression_bias": 0.1}
        draw_match_context_panel(ax, mc, cs)

        text = _collect_ax_text(ax)
        assert "Home team has attacking edge" in text
        plt.close(fig)


class TestRenderPipelineReportWithContext:
    """Validates layout changes when match_context is present or absent."""

    def test_figure_has_four_axes_with_context(self) -> None:
        """render_pipeline_report with match_context produces 4 axes."""
        report_with_ctx = {
            **SAMPLE_REPORT_DICT,
            "match_context": {
                "home_team": "TeamA",
                "away_team": "TeamB",
                "lookback_matches": 10,
                "source": "soccerdata",
                "cache_status": "hit",
                "comparative_signals": {},
            },
            "context_signals": {"notes": [], "aggression_bias": 0.0},
        }
        fig = render_pipeline_report(report_with_ctx)
        axes = fig.get_axes()
        assert len(axes) == 4, f"Expected 4 axes with context, got {len(axes)}"
        plt.close(fig)

    def test_figure_has_three_axes_without_context(self) -> None:
        """render_pipeline_report without match_context produces 3 axes."""
        fig = render_pipeline_report(SAMPLE_REPORT_DICT)
        axes = fig.get_axes()
        assert len(axes) == 3, f"Expected 3 axes without context, got {len(axes)}"
        plt.close(fig)


class TestRenderPipelineReport:
    """Validates Requirements 8.1 — composition returns a Figure with expected axes."""

    def test_returns_figure(self) -> None:
        fig = render_pipeline_report(SAMPLE_REPORT_DICT)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_figure_has_three_axes(self) -> None:
        fig = render_pipeline_report(SAMPLE_REPORT_DICT)
        axes = fig.get_axes()
        assert len(axes) == 3, f"Expected 3 axes, got {len(axes)}"
        plt.close(fig)


class TestRenderSingleBranch:
    """Validates Requirements 8.1, 8.3 — single branch rendering and error handling."""

    def test_returns_figure_for_valid_index(self) -> None:
        fig = render_single_branch(SAMPLE_REPORT_DICT, branch_index=0)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_raises_index_error_for_out_of_range(self) -> None:
        with pytest.raises(IndexError):
            render_single_branch(SAMPLE_REPORT_DICT, branch_index=5)

    def test_raises_value_error_for_empty_branches(self) -> None:
        empty_report = {
            **SAMPLE_REPORT_DICT,
            "ranked_branches": [],
        }
        with pytest.raises(ValueError):
            render_single_branch(empty_report, branch_index=0)
