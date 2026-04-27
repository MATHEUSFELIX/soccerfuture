"""Property-based tests for the validation module.

Feature: soccer-domain-migration, Property 7: Validation identifies exactly the missing fields
"""

from hypothesis import given, settings, strategies as st

from src.scoring.validation import REQUIRED_BRANCH_FIELDS, validate_branch


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


# Strategy: draw a non-empty subset of required fields to remove.
_fields_to_remove = st.lists(
    st.sampled_from(REQUIRED_BRANCH_FIELDS),
    min_size=1,
    max_size=len(REQUIRED_BRANCH_FIELDS),
    unique=True,
)


@given(removed=_fields_to_remove)
@settings(max_examples=100)
def test_validation_identifies_exactly_missing_fields(removed: list[str]) -> None:
    """Property 7: Validation identifies exactly the missing fields.

    **Validates: Requirements 4.1, 4.2**

    For any branch dictionary with a random non-empty subset of required
    fields removed, validate_branch must return is_valid=False and
    missing_fields must contain exactly the removed field names.
    """
    branch = _complete_branch()
    for field in removed:
        del branch[field]

    result = validate_branch(branch)

    assert result.is_valid is False, "Branch with missing fields should be invalid"
    assert set(result.missing_fields) == set(removed), (
        f"Expected missing_fields={set(removed)}, got {set(result.missing_fields)}"
    )
