"""Provenance tracking for pipeline runs.

Records the lineage of inputs, transformations, and outputs across
the full execution chain for auditability.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field


@dataclass
class ProvenanceRecord:
    """Provenance record for a single pipeline execution.

    Attributes:
        run_id: Unique run identifier.
        scenario_id: Scenario being processed.
        input_source: Where the input came from.
        input_type: Type of input (structured, video, commentator).
        extraction_applied: Whether state extraction was performed.
        pipeline_version: Version/config of the pipeline used.
        context_applied: Whether match context was used.
        priors_applied: Whether match priors were used.
        artifacts_produced: List of artifact names produced.
        policy_decisions: List of policy check outcomes.
        timestamp: ISO-8601 timestamp of the run.
        notes: Additional provenance notes.
    """

    run_id: str
    scenario_id: str
    input_source: str = ""
    input_type: str = "structured"
    extraction_applied: bool = False
    pipeline_version: str = "v1"
    context_applied: bool = False
    priors_applied: bool = False
    artifacts_produced: list[str] = field(default_factory=list)
    policy_decisions: list[str] = field(default_factory=list)
    timestamp: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()


def provenance_to_dict(record: ProvenanceRecord) -> dict:
    """Convert a ProvenanceRecord to a JSON-serializable dict."""
    return asdict(record)


def dict_to_provenance(data: dict) -> ProvenanceRecord:
    """Reconstruct a ProvenanceRecord from a dict."""
    return ProvenanceRecord(
        run_id=data.get("run_id", ""),
        scenario_id=data.get("scenario_id", ""),
        input_source=data.get("input_source", ""),
        input_type=data.get("input_type", "structured"),
        extraction_applied=data.get("extraction_applied", False),
        pipeline_version=data.get("pipeline_version", "v1"),
        context_applied=data.get("context_applied", False),
        priors_applied=data.get("priors_applied", False),
        artifacts_produced=data.get("artifacts_produced", []),
        policy_decisions=data.get("policy_decisions", []),
        timestamp=data.get("timestamp", ""),
        notes=data.get("notes", []),
    )
