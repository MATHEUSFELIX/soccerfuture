"""Structured review feedback schema.

Defines the ReviewFeedback dataclass for capturing consistent reviewer
responses across scenarios, with validation and serialization helpers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

RATING_MIN: int = 1
RATING_MAX: int = 5

VALID_PLAUSIBILITY_VALUES = {"yes", "no", "uncertain"}
VALID_USEFULNESS_VALUES = {"yes", "partially", "no", "uncertain"}


@dataclass
class ReviewFeedback:
    """Structured feedback from a single reviewer on a single scenario.

    Attributes:
        scenario_id: Identifier of the reviewed scenario.
        reviewer_id: Identifier of the reviewer.
        top_1_plausibility: Whether the top-1 branch is plausible
            ("yes", "no", "uncertain").
        top_3_usefulness: Whether the top-3 branches are useful
            ("yes", "partially", "no", "uncertain").
        summary_clarity: Rating of summary clarity (1–5).
        confidence_sufficiency: Rating of confidence information (1–5).
        blockers: List of blockers for real use.
        missing_capabilities: List of missing capabilities noted.
        priority_suggestions: List of priority suggestions.
        notes: Freeform reviewer notes.
    """

    scenario_id: str
    reviewer_id: str
    top_1_plausibility: str
    top_3_usefulness: str
    summary_clarity: int
    confidence_sufficiency: int
    blockers: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    priority_suggestions: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate feedback fields."""
        if self.top_1_plausibility not in VALID_PLAUSIBILITY_VALUES:
            raise ValueError(
                f"top_1_plausibility must be one of {sorted(VALID_PLAUSIBILITY_VALUES)}, "
                f"got '{self.top_1_plausibility}'"
            )
        if self.top_3_usefulness not in VALID_USEFULNESS_VALUES:
            raise ValueError(
                f"top_3_usefulness must be one of {sorted(VALID_USEFULNESS_VALUES)}, "
                f"got '{self.top_3_usefulness}'"
            )
        if not (RATING_MIN <= self.summary_clarity <= RATING_MAX):
            raise ValueError(
                f"summary_clarity must be between {RATING_MIN} and {RATING_MAX}, "
                f"got {self.summary_clarity}"
            )
        if not (RATING_MIN <= self.confidence_sufficiency <= RATING_MAX):
            raise ValueError(
                f"confidence_sufficiency must be between {RATING_MIN} and {RATING_MAX}, "
                f"got {self.confidence_sufficiency}"
            )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def feedback_to_dict(fb: ReviewFeedback) -> dict:
    """Convert a ReviewFeedback to a JSON-serializable dict.

    Args:
        fb: The feedback instance to serialize.

    Returns:
        A plain dict suitable for ``json.dumps``.
    """
    return asdict(fb)


def dict_to_feedback(data: dict) -> ReviewFeedback:
    """Reconstruct a ReviewFeedback from a dict.

    Args:
        data: Dict previously produced by ``feedback_to_dict``
            or loaded from a JSON file.

    Returns:
        A validated ReviewFeedback instance.

    Raises:
        KeyError: If required fields are missing.
        ValueError: If field values are out of range.
    """
    required = ["scenario_id", "reviewer_id", "top_1_plausibility",
                "top_3_usefulness", "summary_clarity", "confidence_sufficiency"]
    missing = [f for f in required if f not in data]
    if missing:
        raise KeyError(f"Missing required feedback fields: {', '.join(missing)}")

    return ReviewFeedback(
        scenario_id=data["scenario_id"],
        reviewer_id=data["reviewer_id"],
        top_1_plausibility=data["top_1_plausibility"],
        top_3_usefulness=data["top_3_usefulness"],
        summary_clarity=data["summary_clarity"],
        confidence_sufficiency=data["confidence_sufficiency"],
        blockers=data.get("blockers", []),
        missing_capabilities=data.get("missing_capabilities", []),
        priority_suggestions=data.get("priority_suggestions", []),
        notes=data.get("notes", ""),
    )
