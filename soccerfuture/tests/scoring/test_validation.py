"""Unit tests for the validation module.

Tests structural validation of branch dictionaries via validate_branch.

Requirements: 4.1, 4.2
"""

import pytest

from src.scoring.validation import (
    REQUIRED_BRANCH_FIELDS,
    ValidationResult,
    validate_branch,
)


def _complete_branch() -> dict:
    """Return a minimal branch dict with all required fields present."""
    return {
        "branch_id": "b-001",
        "decision_point_timestamp": 1.0,
        "positions": [],
        "events": [],
        "player_roles": {},
        "metadata": {},
    }


class TestValidateBranchPasses:
    """A complete branch should pass validation."""

    def test_complete_branch_is_valid(self) -> None:
        result = validate_branch(_complete_branch())

        assert result.is_valid is True
        assert result.missing_fields == []
        assert result.error_message == ""


class TestValidateBranchSingleMissing:
    """A branch missing a single required field should fail with the correct error."""

    def test_missing_positions(self) -> None:
        branch = _complete_branch()
        del branch["positions"]

        result = validate_branch(branch)

        assert result.is_valid is False
        assert result.missing_fields == ["positions"]
        assert "positions" in result.error_message

    def test_missing_branch_id(self) -> None:
        branch = _complete_branch()
        del branch["branch_id"]

        result = validate_branch(branch)

        assert result.is_valid is False
        assert result.missing_fields == ["branch_id"]
        assert "branch_id" in result.error_message


class TestValidateBranchMultipleMissing:
    """A branch missing multiple fields should list all missing fields."""

    def test_missing_positions_and_events(self) -> None:
        branch = _complete_branch()
        del branch["positions"]
        del branch["events"]

        result = validate_branch(branch)

        assert result.is_valid is False
        assert set(result.missing_fields) == {"positions", "events"}
        assert "positions" in result.error_message
        assert "events" in result.error_message

    def test_missing_all_fields(self) -> None:
        result = validate_branch({})

        assert result.is_valid is False
        assert set(result.missing_fields) == set(REQUIRED_BRANCH_FIELDS)
        for field in REQUIRED_BRANCH_FIELDS:
            assert field in result.error_message
