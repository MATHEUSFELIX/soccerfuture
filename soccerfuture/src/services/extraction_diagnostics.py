"""Machine-readable extraction diagnostics.

Generates structured diagnostics combining schema detection,
normalization, and quality assessment results into a single
inspectable record.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.integrations.commentator_payload_normalizer import NormalizationResult
from src.integrations.commentator_schema_registry import SchemaDetectionResult
from src.services.input_quality_assessor import QualityAssessment


@dataclass
class ExtractionDiagnostics:
    """Complete diagnostics for a single payload ingestion attempt.

    Attributes:
        scenario_id: Identifier for the scenario being ingested.
        schema_version: Detected schema version.
        schema_compatible: Whether the schema was compatible.
        normalization_applied: Whether normalization was applied.
        normalization_fixes: List of normalization actions taken.
        quality_grade: Quality grade ("good", "acceptable", "poor", "rejected").
        rejected: Whether the payload was rejected.
        rejection_reason: Reason for rejection, if applicable.
        warnings: All warnings from schema, normalization, and quality.
        errors: All errors from schema detection.
        player_count: Number of unique players detected.
        avg_confidence: Average player confidence.
    """

    scenario_id: str
    schema_version: str = "unknown"
    schema_compatible: bool = False
    normalization_applied: bool = False
    normalization_fixes: list[str] = field(default_factory=list)
    quality_grade: str = "rejected"
    rejected: bool = True
    rejection_reason: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    player_count: int = 0
    avg_confidence: float = 0.0


def build_diagnostics(
    scenario_id: str,
    schema_result: SchemaDetectionResult,
    normalization_result: NormalizationResult | None = None,
    quality_result: QualityAssessment | None = None,
) -> ExtractionDiagnostics:
    """Build complete diagnostics from component results.

    Args:
        scenario_id: Identifier for the scenario.
        schema_result: Result of schema detection.
        normalization_result: Result of normalization, or None if skipped.
        quality_result: Result of quality assessment, or None if skipped.

    Returns:
        An ExtractionDiagnostics instance.
    """
    all_warnings = list(schema_result.warnings)
    all_errors = list(schema_result.errors)

    normalization_applied = False
    normalization_fixes: list[str] = []
    rejected = not schema_result.compatible
    rejection_reason = ""

    if not schema_result.compatible:
        rejection_reason = "; ".join(schema_result.errors) if schema_result.errors else "Schema incompatible"

    if normalization_result is not None:
        normalization_applied = True
        normalization_fixes = list(normalization_result.applied_fixes)
        all_warnings.extend(normalization_result.warnings)
        if normalization_result.rejected:
            rejected = True
            rejection_reason = normalization_result.rejection_reason

    quality_grade = "rejected"
    player_count = 0
    avg_confidence = 0.0

    if quality_result is not None:
        quality_grade = quality_result.grade
        player_count = quality_result.player_count
        avg_confidence = quality_result.avg_player_confidence
        all_warnings.extend(quality_result.issues)
        if quality_result.grade == "rejected":
            rejected = True
            if not rejection_reason:
                rejection_reason = "; ".join(quality_result.issues)

    return ExtractionDiagnostics(
        scenario_id=scenario_id,
        schema_version=schema_result.version,
        schema_compatible=schema_result.compatible,
        normalization_applied=normalization_applied,
        normalization_fixes=normalization_fixes,
        quality_grade=quality_grade,
        rejected=rejected,
        rejection_reason=rejection_reason,
        warnings=all_warnings,
        errors=all_errors,
        player_count=player_count,
        avg_confidence=avg_confidence,
    )


def diagnostics_to_dict(diag: ExtractionDiagnostics) -> dict:
    """Convert ExtractionDiagnostics to a JSON-serializable dict."""
    return asdict(diag)
