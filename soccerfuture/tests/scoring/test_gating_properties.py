"""Property-based tests for the gating module.

Feature: simulation-evaluator
Properties 3–6: Out-of-bounds rejection, excessive speed rejection,
temporal discontinuity rejection, and gating result consistency.
"""

from hypothesis import given, settings

from src.scoring.gating import run_gates
from tests.strategies import (
    any_branch_strategy,
    excessive_speed_branch_strategy,
    out_of_bounds_branch_strategy,
    temporal_discontinuity_branch_strategy,
)


# ── Property 3: Out-of-bounds positions cause gating rejection ───────────


@given(branch=out_of_bounds_branch_strategy())
@settings(max_examples=100)
def test_out_of_bounds_positions_cause_gating_rejection(branch: dict) -> None:
    """Property 3: Out-of-bounds positions cause gating rejection.

    **Validates: Requirements 3.2**

    For any branch containing at least one player position outside the
    soccer field boundaries (x: 0–68m, y: 0–105m, no end zones), the
    Gating Module shall reject the branch with field_bounds flag set to
    false.
    """
    result = run_gates(branch)

    assert result.passed is False, "Branch with out-of-bounds position should fail gating"
    assert result.flags["field_bounds"] is False, (
        "field_bounds flag should be False for out-of-bounds positions"
    )
    assert len(result.explanations) > 0, (
        "Explanations should be non-empty when gating fails"
    )


# ── Property 4: Excessive speed causes gating rejection ──────────────────


@given(branch=excessive_speed_branch_strategy())
@settings(max_examples=100)
def test_excessive_speed_causes_gating_rejection(branch: dict) -> None:
    """Property 4: Excessive speed causes gating rejection.

    **Validates: Requirements 3.3**

    For any branch containing at least one player whose speed between
    consecutive frames exceeds MAX_HUMAN_SPRINT_SPEED, the Gating Module
    shall reject the branch with max_speed flag set to false.
    """
    result = run_gates(branch)

    assert result.passed is False, "Branch with excessive speed should fail gating"
    assert result.flags["max_speed"] is False, (
        "max_speed flag should be False when speed exceeds MAX_HUMAN_SPRINT_SPEED"
    )
    assert len(result.explanations) > 0, (
        "Explanations should be non-empty when gating fails"
    )


# ── Property 5: Temporal discontinuity causes gating rejection ───────────


@given(branch=temporal_discontinuity_branch_strategy())
@settings(max_examples=100)
def test_temporal_discontinuity_causes_gating_rejection(branch: dict) -> None:
    """Property 5: Temporal discontinuity causes gating rejection.

    **Validates: Requirements 3.4**

    For any branch containing timestamps with gaps exceeding
    MAX_TIMESTAMP_GAP, the Gating Module shall reject the branch with
    temporal_continuity flag set to false.
    """
    result = run_gates(branch)

    assert result.passed is False, "Branch with temporal discontinuity should fail gating"
    assert result.flags["temporal_continuity"] is False, (
        "temporal_continuity flag should be False for large timestamp gaps"
    )
    assert len(result.explanations) > 0, (
        "Explanations should be non-empty when gating fails"
    )


# ── Property 6: Gating result consistency ────────────────────────────────


@given(branch=any_branch_strategy())
@settings(max_examples=100)
def test_gating_result_consistency(branch: dict) -> None:
    """Property 6: Gating result consistency.

    **Validates: Requirements 3.5, 3.6**

    For any branch, the GatingResult flags and explanations shall be
    consistent:
    - If passed is False, at least one flag is False and explanations
      is non-empty.
    - If passed is True, all flags are True and explanations is empty.
    """
    result = run_gates(branch)

    if result.passed:
        assert all(result.flags.values()), (
            f"When passed=True, all flags should be True, got {result.flags}"
        )
        assert result.explanations == [], (
            f"When passed=True, explanations should be empty, got {result.explanations}"
        )
    else:
        assert not all(result.flags.values()), (
            f"When passed=False, at least one flag should be False, got {result.flags}"
        )
        assert len(result.explanations) > 0, (
            "When passed=False, explanations should be non-empty"
        )
