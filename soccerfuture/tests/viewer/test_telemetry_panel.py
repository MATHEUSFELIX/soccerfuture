"""Unit tests for draw_telemetry_panel."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.viewer.viewer_2d import draw_telemetry_panel


def _make_metadata_with_telemetry() -> dict:
    """Return sample metadata containing telemetry data."""
    return {
        "telemetry": {
            "branches_generated": 20,
            "hard_fail_count": 3,
            "score_filtered_count": 2,
            "avg_score_by_strategy": {"route_variation": 0.45},
            "time_per_stage": {
                "generation": 0.12,
                "evaluation": 1.85,
                "ranking": 0.01,
            },
        }
    }


def _get_all_text(ax) -> str:
    """Collect all text content from an axes."""
    return " ".join(t.get_text() for t in ax.texts)


class TestDrawTelemetryPanelWithData:
    """Tests when telemetry data is present."""

    def test_axis_is_off(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, _make_metadata_with_telemetry())
        assert not ax.axison
        plt.close(fig)

    def test_title_rendered(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, _make_metadata_with_telemetry())
        text = _get_all_text(ax)
        assert "Pipeline Telemetry" in text
        plt.close(fig)

    def test_branches_generated_displayed(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, _make_metadata_with_telemetry())
        text = _get_all_text(ax)
        assert "20" in text
        plt.close(fig)

    def test_hard_fail_count_displayed(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, _make_metadata_with_telemetry())
        text = _get_all_text(ax)
        assert "Hard fails: 3" in text
        plt.close(fig)

    def test_score_filtered_count_displayed(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, _make_metadata_with_telemetry())
        text = _get_all_text(ax)
        assert "Score filtered: 2" in text
        plt.close(fig)

    def test_avg_score_by_strategy_displayed(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, _make_metadata_with_telemetry())
        text = _get_all_text(ax)
        assert "route_variation" in text
        assert "0.45" in text
        plt.close(fig)

    def test_time_per_stage_displayed(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, _make_metadata_with_telemetry())
        text = _get_all_text(ax)
        assert "generation" in text
        assert "evaluation" in text
        assert "ranking" in text
        plt.close(fig)


class TestDrawTelemetryPanelMissing:
    """Tests when telemetry data is absent."""

    def test_fallback_message_when_no_telemetry(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, {})
        text = _get_all_text(ax)
        assert "Telemetry data not available" in text
        plt.close(fig)

    def test_fallback_message_when_none_metadata(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, None)
        text = _get_all_text(ax)
        assert "Telemetry data not available" in text
        plt.close(fig)

    def test_axis_is_off_when_missing(self):
        fig, ax = plt.subplots()
        draw_telemetry_panel(ax, {})
        assert not ax.axison
        plt.close(fig)
