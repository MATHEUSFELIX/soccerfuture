"""Runtime artifact store for persisting ingested payloads with traceability.

Stores raw payloads, diagnostics, and quality assessments in a
structured directory layout for audit and replay.
"""

from __future__ import annotations

import datetime
import json
import os
from dataclasses import dataclass, field


@dataclass
class StoredArtifact:
    """Record of a stored runtime artifact.

    Attributes:
        artifact_id: Unique identifier for this artifact.
        source_path: Original source path of the payload.
        store_path: Path where the artifact was persisted.
        stored_at: ISO-8601 timestamp of storage.
        quality_grade: Quality grade from assessment.
        rejected: Whether the payload was rejected.
        notes: Storage notes.
    """

    artifact_id: str
    source_path: str
    store_path: str
    stored_at: str
    quality_grade: str = "unknown"
    rejected: bool = False
    notes: list[str] = field(default_factory=list)


def _generate_artifact_id(source_path: str, index: int) -> str:
    """Generate a deterministic artifact ID from source path and index.

    Args:
        source_path: Original source path.
        index: Sequential index for this ingestion run.

    Returns:
        A deterministic artifact ID string.
    """
    basename = os.path.basename(source_path).replace(".json", "")
    return f"{basename}_{index:04d}"


def store_artifact(
    store_root: str,
    payload: dict,
    source_path: str,
    index: int,
    quality_grade: str = "unknown",
    rejected: bool = False,
    diagnostics: dict | None = None,
) -> StoredArtifact:
    """Persist a runtime payload and its diagnostics.

    Creates a subdirectory per artifact containing:
      - payload.json — the raw payload
      - diagnostics.json — quality/schema diagnostics (if provided)
      - metadata.json — provenance metadata

    Args:
        store_root: Root directory for the artifact store.
        payload: The raw payload dict to store.
        source_path: Original source path.
        index: Sequential index.
        quality_grade: Quality grade from assessment.
        rejected: Whether the payload was rejected.
        diagnostics: Optional diagnostics dict.

    Returns:
        A StoredArtifact record.
    """
    artifact_id = _generate_artifact_id(source_path, index)
    artifact_dir = os.path.join(store_root, artifact_id)
    os.makedirs(artifact_dir, exist_ok=True)

    stored_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Write payload
    payload_path = os.path.join(artifact_dir, "payload.json")
    with open(payload_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    # Write diagnostics if provided
    if diagnostics is not None:
        diag_path = os.path.join(artifact_dir, "diagnostics.json")
        with open(diag_path, "w", encoding="utf-8") as fh:
            json.dump(diagnostics, fh, indent=2)

    # Write metadata
    metadata = {
        "artifact_id": artifact_id,
        "source_path": source_path,
        "stored_at": stored_at,
        "quality_grade": quality_grade,
        "rejected": rejected,
    }
    metadata_path = os.path.join(artifact_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    return StoredArtifact(
        artifact_id=artifact_id,
        source_path=source_path,
        store_path=artifact_dir,
        stored_at=stored_at,
        quality_grade=quality_grade,
        rejected=rejected,
        notes=[f"Stored at {artifact_dir}"],
    )
