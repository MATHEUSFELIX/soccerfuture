"""Unit tests for src/services/extraction_diagnostics.py."""

from src.integrations.commentator_payload_normalizer import NormalizationResult
from src.integrations.commentator_schema_registry import SchemaDetectionResult
from src.services.extraction_diagnostics import (
    ExtractionDiagnostics,
    build_diagnostics,
    diagnostics_to_dict,
)
from src.services.input_quality_assessor import QualityAssessment


class TestBuildDiagnostics:
    def test_compatible_schema_not_rejected(self):
        schema = SchemaDetectionResult(version="v1", compatible=True)
        norm = NormalizationResult(payload={"players": []}, applied_fixes=["fix1"])
        quality = QualityAssessment(
            grade="good", player_count=11, ball_entry_count=2,
            avg_player_confidence=0.9, avg_ball_confidence=0.9,
        )
        diag = build_diagnostics("s1", schema, norm, quality)
        assert diag.rejected is False
        assert diag.quality_grade == "good"
        assert diag.schema_version == "v1"

    def test_incompatible_schema_rejected(self):
        schema = SchemaDetectionResult(
            version="unknown", compatible=False, errors=["Missing players"],
        )
        diag = build_diagnostics("s1", schema)
        assert diag.rejected is True
        assert "Missing players" in diag.rejection_reason

    def test_normalization_rejected(self):
        schema = SchemaDetectionResult(version="v1", compatible=True)
        norm = NormalizationResult(
            payload={}, rejected=True, rejection_reason="No players",
        )
        diag = build_diagnostics("s1", schema, norm)
        assert diag.rejected is True
        assert "No players" in diag.rejection_reason

    def test_quality_rejected(self):
        schema = SchemaDetectionResult(version="v1", compatible=True)
        norm = NormalizationResult(payload={})
        quality = QualityAssessment(
            grade="rejected", player_count=1, ball_entry_count=0,
            avg_player_confidence=0.0, avg_ball_confidence=0.0,
            issues=["Too few players"],
        )
        diag = build_diagnostics("s1", schema, norm, quality)
        assert diag.rejected is True
        assert diag.quality_grade == "rejected"

    def test_diagnostics_to_dict(self):
        schema = SchemaDetectionResult(version="v1", compatible=True)
        diag = build_diagnostics("s1", schema)
        d = diagnostics_to_dict(diag)
        assert isinstance(d, dict)
        assert d["scenario_id"] == "s1"

    def test_warnings_aggregated(self):
        schema = SchemaDetectionResult(version="v1", compatible=True, warnings=["w1"])
        norm = NormalizationResult(payload={}, warnings=["w2"])
        quality = QualityAssessment(
            grade="acceptable", player_count=7, ball_entry_count=2,
            avg_player_confidence=0.6, avg_ball_confidence=0.6,
            issues=["low conf"],
        )
        diag = build_diagnostics("s1", schema, norm, quality)
        assert "w1" in diag.warnings
        assert "w2" in diag.warnings
        assert "low conf" in diag.warnings
