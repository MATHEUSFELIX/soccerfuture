"""Pilot plan schema.

Defines the structure for a pilot evaluation plan including
scenario sets, reviewer sets, and success metrics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class PilotPlan:
    """Definition of a structured pilot evaluation.

    Attributes:
        pilot_id: Unique pilot identifier.
        scenario_ids: List of scenario IDs to include.
        reviewer_ids: List of reviewer IDs participating.
        success_metrics: Dict of metric name to target threshold.
        description: Human-readable pilot description.
        notes: Additional planning notes.
    """

    pilot_id: str
    scenario_ids: list[str] = field(default_factory=list)
    reviewer_ids: list[str] = field(default_factory=list)
    success_metrics: dict[str, float] = field(default_factory=dict)
    description: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.pilot_id:
            raise ValueError("pilot_id is required")
        if not self.scenario_ids:
            raise ValueError("At least one scenario_id is required")


def plan_to_dict(plan: PilotPlan) -> dict:
    """Convert a PilotPlan to a JSON-serializable dict."""
    return asdict(plan)


def dict_to_plan(data: dict) -> PilotPlan:
    """Reconstruct a PilotPlan from a dict."""
    return PilotPlan(
        pilot_id=data.get("pilot_id", ""),
        scenario_ids=data.get("scenario_ids", []),
        reviewer_ids=data.get("reviewer_ids", []),
        success_metrics=data.get("success_metrics", {}),
        description=data.get("description", ""),
        notes=data.get("notes", []),
    )
