"""Runtime ingestion runner.

Orchestrates the full runtime ingestion flow: load → schema check →
normalize → quality assess → diagnostics → store. Rejected payloads
are stored but never passed to the pipeline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from src.integrations.commentator_payload_normalizer import normalize_payload
from src.integrations.commentator_schema_registry import detect_schema_version
from src.runtime.commentator_runtime_client import RuntimePayload, load_payloads
from src.runtime.commentator_runtime_config import RuntimeConfig
from src.runtime.runtime_artifact_store import StoredArtifact, store_artifact
from src.services.extraction_diagnostics import (
    ExtractionDiagnostics,
    build_diagnostics,
    diagnostics_to_dict,
)
from src.services.input_quality_assessor import assess_quality


@dataclass
class IngestionResult:
    """Result of processing a single runtime payload.

    Attributes:
        source_path: Original source path.
        accepted: Whether the payload was accepted for pipeline use.
        quality_grade: Quality grade.
        diagnostics: Full extraction diagnostics.
        stored_artifact: Reference to the stored artifact.
        normalized_payload: The normalized payload (None if rejected).
        notes: Processing notes.
    """

    source_path: str
    accepted: bool
    quality_grade: str
    diagnostics: ExtractionDiagnostics
    stored_artifact: StoredArtifact | None = None
    normalized_payload: dict | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class IngestionBatchResult:
    """Aggregate result of a batch ingestion run.

    Attributes:
        total: Total payloads processed.
        accepted_count: Number accepted.
        rejected_count: Number rejected.
        results: Per-payload results.
        notes: Batch-level notes.
    """

    total: int
    accepted_count: int
    rejected_count: int
    results: list[IngestionResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def run_ingestion(
    config: RuntimeConfig,
    provider_fetcher: Callable | None = None,
) -> IngestionBatchResult:
    """Execute the full runtime ingestion flow.

    Steps per payload:
      1. Load from configured source
      2. Detect schema version
      3. Normalize payload
      4. Assess quality
      5. Build diagnostics
      6. Store artifact (accepted or rejected)
      7. Return result (rejected payloads have normalized_payload=None)

    Args:
        config: Runtime configuration.
        provider_fetcher: Optional provider fetcher callable.

    Returns:
        An IngestionBatchResult with per-payload results.
    """
    # Load payloads
    raw_payloads = load_payloads(config, provider_fetcher)

    results: list[IngestionResult] = []
    accepted_count = 0
    rejected_count = 0

    for i, runtime_payload in enumerate(raw_payloads):
        source_path = runtime_payload.source_path
        payload = runtime_payload.payload

        # Schema detection
        schema_result = detect_schema_version(payload)

        # Normalization
        norm_result = normalize_payload(payload)

        # Quality assessment (on normalized payload if not rejected)
        quality_result = None
        if not norm_result.rejected:
            quality_result = assess_quality(norm_result.payload)

        # Build diagnostics
        scenario_id = f"runtime_{i:04d}"
        diag = build_diagnostics(scenario_id, schema_result, norm_result, quality_result)

        # Determine acceptance
        accepted = not diag.rejected
        if accepted and config.auto_reject and quality_result and quality_result.grade == "rejected":
            accepted = False
            diag.rejected = True
            diag.rejection_reason = "Auto-rejected due to quality grade"

        # Store artifact
        stored = store_artifact(
            store_root=config.artifact_store_path,
            payload=payload,
            source_path=source_path,
            index=i,
            quality_grade=diag.quality_grade,
            rejected=not accepted,
            diagnostics=diagnostics_to_dict(diag),
        )

        # Build result
        normalized = norm_result.payload if accepted else None
        result = IngestionResult(
            source_path=source_path,
            accepted=accepted,
            quality_grade=diag.quality_grade,
            diagnostics=diag,
            stored_artifact=stored,
            normalized_payload=normalized,
            notes=runtime_payload.load_notes,
        )
        results.append(result)

        if accepted:
            accepted_count += 1
        else:
            rejected_count += 1

    return IngestionBatchResult(
        total=len(results),
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        results=results,
        notes=[f"Processed {len(results)} payload(s) from {config.source_type}"],
    )
