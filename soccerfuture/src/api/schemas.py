"""API request and response schemas.

Defines typed dataclasses for API inputs and outputs, with
validation and serialization helpers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class WorkflowSubmitRequest:
    """Request to submit a scenario for workflow execution.

    Attributes:
        scenario_id: Unique scenario identifier.
        play_state: PlayState dict to process.
        source_type: Input source type.
        pipeline_config: Optional pipeline config overrides.
    """

    scenario_id: str
    play_state: dict
    source_type: str = "structured"
    pipeline_config: dict | None = None

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id is required")
        if not isinstance(self.play_state, dict):
            raise ValueError("play_state must be a dict")


@dataclass
class WorkflowSubmitResponse:
    """Response after submitting a workflow job.

    Attributes:
        scenario_id: The scenario that was submitted.
        status: Execution status ("success", "partial", "failed").
        bundle_path: Path to the generated bundle.
        errors: List of error messages, if any.
    """

    scenario_id: str
    status: str
    bundle_path: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass
class RunStatusResponse:
    """Response for fetching run status.

    Attributes:
        scenario_id: The scenario queried.
        overall_status: Overall run status.
        step_statuses: List of step status dicts.
        artifact_references: Mapping of artifact name to path.
    """

    scenario_id: str
    overall_status: str
    step_statuses: list[dict] = field(default_factory=list)
    artifact_references: dict[str, str] = field(default_factory=dict)


@dataclass
class FeedbackSubmitRequest:
    """Request to submit reviewer feedback.

    Attributes:
        scenario_id: Scenario being reviewed.
        reviewer_id: Reviewer identifier.
        feedback: Feedback data dict.
    """

    scenario_id: str
    reviewer_id: str
    feedback: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id is required")
        if not self.reviewer_id:
            raise ValueError("reviewer_id is required")


@dataclass
class FeedbackSubmitResponse:
    """Response after submitting feedback.

    Attributes:
        scenario_id: The scenario feedback was submitted for.
        accepted: Whether the feedback was accepted.
        errors: Validation errors, if any.
    """

    scenario_id: str
    accepted: bool
    errors: list[str] = field(default_factory=list)


def response_to_dict(response) -> dict:
    """Convert any response dataclass to a JSON-serializable dict."""
    return asdict(response)
