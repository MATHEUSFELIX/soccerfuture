"""Branch validation module.

Checks structural correctness of a raw branch dictionary before any
scoring proceeds.  This module must NOT import from any other scoring
module under ``src/scoring/``.
"""

from dataclasses import dataclass, field


REQUIRED_BRANCH_FIELDS: list[str] = [
    "branch_id",
    "decision_point_timestamp",
    "positions",
    "events",
    "player_roles",
    "metadata",
]
"""Fields that every branch dictionary must contain."""


@dataclass
class ValidationResult:
    """Result of validating a branch dictionary.

    Attributes:
        is_valid: True when the branch contains all required fields.
        missing_fields: Names of any required fields not present in the branch.
        error_message: Human-readable description of the problem, or an
            empty string when the branch is valid.
    """

    is_valid: bool
    missing_fields: list[str] = field(default_factory=list)
    error_message: str = ""


def validate_branch(branch: dict) -> ValidationResult:
    """Verify that a branch contains all required fields.

    Args:
        branch: Raw branch dictionary from input JSON.

    Returns:
        ValidationResult with ``is_valid=True`` if all required fields are
        present, otherwise ``is_valid=False`` with ``missing_fields``
        populated and a descriptive ``error_message``.
    """
    missing: list[str] = [
        f for f in REQUIRED_BRANCH_FIELDS if f not in branch
    ]

    if not missing:
        return ValidationResult(is_valid=True)

    message = (
        f"Branch is missing required field(s): {', '.join(missing)}"
    )
    return ValidationResult(
        is_valid=False,
        missing_fields=missing,
        error_message=message,
    )
