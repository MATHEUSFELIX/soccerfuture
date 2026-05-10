"""Unit tests for src/evaluation/ingestion_robustness_report.py."""

from src.evaluation.ingestion_robustness_report import (
    IngestionRobustnessReport,
    compute_ingestion_robustness,
    render_robustness_report_markdown,
)
from src.services.extraction_diagnostics import ExtractionDiagnostics


def _make_diag(grade="good", rejected=False, player_count=11, confidence=0.9, **kwargs):
    defaults = dict(
        scenario_id="s1",
        schema_version="v1",
        schema_compatible=True,
        normalization_applied=True,
        quality_grade=grade,
        rejected=rejected,
        player_count=player_count,
        avg_confidence=confidence,
    )
    defaults.update(kwargs)
    return ExtractionDiagnostics(**defaults)


class TestComputeIngestionRobustness:
    def test_empty_list(self):
        report = compute_ingestion_robustness([])
        assert report.total_payloads == 0
        assert report.accepted_count == 0

    def test_all_good(self):
        diags = [_make_diag(grade="good") for _ in range(3)]
        report = compute_ingestion_robustness(diags)
        assert report.total_payloads == 3
        assert report.accepted_count == 3
        assert report.good_count == 3
        assert report.rejected_count == 0

    def test_mixed_grades(self):
        diags = [
            _make_diag(grade="good"),
            _make_diag(grade="acceptable", player_count=7, confidence=0.6),
            _make_diag(grade="rejected", rejected=True, player_count=1, confidence=0.2),
        ]
        report = compute_ingestion_robustness(diags)
        assert report.total_payloads == 3
        assert report.accepted_count == 2
        assert report.rejected_count == 1
        assert report.good_count == 1
        assert report.acceptable_count == 1

    def test_avg_player_count(self):
        diags = [
            _make_diag(player_count=11),
            _make_diag(player_count=7),
        ]
        report = compute_ingestion_robustness(diags)
        assert report.avg_player_count == 9.0

    def test_common_warnings(self):
        diags = [
            _make_diag(warnings=["low conf", "missing field"]),
            _make_diag(warnings=["low conf"]),
        ]
        report = compute_ingestion_robustness(diags)
        assert "low conf" in report.common_warnings


class TestRenderRobustnessReportMarkdown:
    def test_contains_header(self):
        report = IngestionRobustnessReport(
            total_payloads=2, accepted_count=1, rejected_count=1,
            good_count=1, acceptable_count=0, poor_count=0,
            avg_player_count=11.0, avg_confidence=0.9,
        )
        md = render_robustness_report_markdown(report)
        assert "# Ingestion Robustness Report" in md
        assert "Total payloads tested:** 2" in md

    def test_contains_warnings_section(self):
        report = IngestionRobustnessReport(
            total_payloads=1, accepted_count=1, rejected_count=0,
            good_count=1, acceptable_count=0, poor_count=0,
            avg_player_count=11.0, avg_confidence=0.9,
            common_warnings=["low conf"],
        )
        md = render_robustness_report_markdown(report)
        assert "Common Warnings" in md
        assert "low conf" in md
