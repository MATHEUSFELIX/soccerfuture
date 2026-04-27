"""Tests for src/viewer/constants.py — visual configuration constants.

Validates: Requirements 8.3, 8.4, 11.6
"""

from src.viewer.constants import (
    FIELD_LENGTH_M,
    FIELD_WIDTH_M,
    ROLE_COLORS,
    DEFAULT_ROLE_COLOR,
    BRANCH_COLORS,
    PLAYER_MARKER_SIZE,
    PLAYER_MARKER_SINGLE,
    PLAYER_LABEL_FONTSIZE,
    TRAJECTORY_LINE_WIDTH,
    TRAJECTORY_LINE_WIDTH_SINGLE,
    ARROW_HEAD_WIDTH,
    ARROW_HEAD_LENGTH,
    FIELD_COLOR,
    LINE_COLOR,
    PENALTY_AREA_COLOR,
    GOAL_AREA_COLOR,
    CENTER_CIRCLE_COLOR,
    MIDFIELD_LINE_WIDTH,
    BALL_MARKER_SIZE,
    BALL_MARKER_COLOR,
    FIGURE_WIDTH,
    FIGURE_HEIGHT,
    FIELD_AXES_RECT,
    EXPLANATION_AXES_RECT,
    TELEMETRY_AXES_RECT,
    TITLE_FONTSIZE,
    PANEL_TITLE_FONTSIZE,
    PANEL_TEXT_FONTSIZE,
)


class TestRoleColors:
    """Validates Requirement 8.3 — role color mapping for soccer positions."""

    def test_contains_all_required_roles(self) -> None:
        for role in ("GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"):
            assert role in ROLE_COLORS

    def test_values_are_strings(self) -> None:
        for role, color in ROLE_COLORS.items():
            assert isinstance(color, str), f"{role} color is not a string"

    def test_default_role_color_is_string(self) -> None:
        assert isinstance(DEFAULT_ROLE_COLOR, str)


class TestBranchColors:
    """Validates Requirement 8.3 — branch color list."""

    def test_has_at_least_five_entries(self) -> None:
        assert len(BRANCH_COLORS) >= 5

    def test_values_are_strings(self) -> None:
        for color in BRANCH_COLORS:
            assert isinstance(color, str)


class TestFieldDimensions:
    """Validates Requirement 8.3 — soccer field dimension constants."""

    def test_field_length_is_105(self) -> None:
        assert isinstance(FIELD_LENGTH_M, float)
        assert FIELD_LENGTH_M == 105.0

    def test_field_width_is_68(self) -> None:
        assert isinstance(FIELD_WIDTH_M, float)
        assert FIELD_WIDTH_M == 68.0


class TestSoccerFieldColors:
    """Validates Requirement 8.3, 8.4 — soccer-specific viewer constants."""

    def test_penalty_area_color_is_string(self) -> None:
        assert isinstance(PENALTY_AREA_COLOR, str)

    def test_goal_area_color_is_string(self) -> None:
        assert isinstance(GOAL_AREA_COLOR, str)

    def test_center_circle_color_is_string(self) -> None:
        assert isinstance(CENTER_CIRCLE_COLOR, str)

    def test_midfield_line_width_positive(self) -> None:
        assert isinstance(MIDFIELD_LINE_WIDTH, float)
        assert MIDFIELD_LINE_WIDTH > 0

    def test_ball_marker_size_positive(self) -> None:
        assert isinstance(BALL_MARKER_SIZE, float)
        assert BALL_MARKER_SIZE > 0

    def test_ball_marker_color_is_string(self) -> None:
        assert isinstance(BALL_MARKER_COLOR, str)


class TestLayoutRects:
    """Validates Requirement 8.3 — figure layout rectangles."""

    def test_field_axes_rect(self) -> None:
        assert isinstance(FIELD_AXES_RECT, list)
        assert len(FIELD_AXES_RECT) == 4
        assert all(isinstance(v, float) for v in FIELD_AXES_RECT)

    def test_explanation_axes_rect(self) -> None:
        assert isinstance(EXPLANATION_AXES_RECT, list)
        assert len(EXPLANATION_AXES_RECT) == 4
        assert all(isinstance(v, float) for v in EXPLANATION_AXES_RECT)

    def test_telemetry_axes_rect(self) -> None:
        assert isinstance(TELEMETRY_AXES_RECT, list)
        assert len(TELEMETRY_AXES_RECT) == 4
        assert all(isinstance(v, float) for v in TELEMETRY_AXES_RECT)


class TestFontSizes:
    """Validates Requirement 8.3 — font sizes are positive integers."""

    def test_title_fontsize(self) -> None:
        assert isinstance(TITLE_FONTSIZE, int) and TITLE_FONTSIZE > 0

    def test_panel_title_fontsize(self) -> None:
        assert isinstance(PANEL_TITLE_FONTSIZE, int) and PANEL_TITLE_FONTSIZE > 0

    def test_panel_text_fontsize(self) -> None:
        assert isinstance(PANEL_TEXT_FONTSIZE, int) and PANEL_TEXT_FONTSIZE > 0

    def test_player_label_fontsize(self) -> None:
        assert isinstance(PLAYER_LABEL_FONTSIZE, int) and PLAYER_LABEL_FONTSIZE > 0


class TestMarkerSizes:
    """Validates Requirement 8.3 — marker and line sizes are positive floats."""

    def test_player_marker_size(self) -> None:
        assert isinstance(PLAYER_MARKER_SIZE, float) and PLAYER_MARKER_SIZE > 0

    def test_player_marker_single(self) -> None:
        assert isinstance(PLAYER_MARKER_SINGLE, float) and PLAYER_MARKER_SINGLE > 0

    def test_trajectory_line_width(self) -> None:
        assert isinstance(TRAJECTORY_LINE_WIDTH, float) and TRAJECTORY_LINE_WIDTH > 0

    def test_trajectory_line_width_single(self) -> None:
        assert isinstance(TRAJECTORY_LINE_WIDTH_SINGLE, float) and TRAJECTORY_LINE_WIDTH_SINGLE > 0

    def test_arrow_head_width(self) -> None:
        assert isinstance(ARROW_HEAD_WIDTH, float) and ARROW_HEAD_WIDTH > 0

    def test_arrow_head_length(self) -> None:
        assert isinstance(ARROW_HEAD_LENGTH, float) and ARROW_HEAD_LENGTH > 0
