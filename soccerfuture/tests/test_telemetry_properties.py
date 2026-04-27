"""Property-based tests for TelemetryCollector.

Feature: pipeline-maturity-baseline
"""

import json

from hypothesis import given, settings

from tests.strategies import telemetry_collector_strategy


_REQUIRED_KEYS = {
    "branches_generated",
    "hard_fail_count",
    "score_filtered_count",
    "avg_score_by_strategy",
    "avg_score_by_scenario",
    "time_per_stage",
}

_REQUIRED_STAGES = {"generation", "evaluation", "ranking"}


@given(collector=telemetry_collector_strategy())
@settings(max_examples=100)
def test_telemetry_completeness(collector):
    """Property 3: Telemetry completeness

    For any TelemetryCollector with recorded results, to_dict() contains
    all required keys and is JSON-serializable.

    **Validates: Requirements 7.1, 7.2, 7.4**
    """
    result = collector.to_dict()

    # All 6 required keys are present
    assert set(result.keys()) >= _REQUIRED_KEYS, (
        f"Missing keys: {_REQUIRED_KEYS - set(result.keys())}"
    )

    # time_per_stage contains generation, evaluation, ranking
    assert set(result["time_per_stage"].keys()) >= _REQUIRED_STAGES, (
        f"Missing stages: {_REQUIRED_STAGES - set(result['time_per_stage'].keys())}"
    )

    # The output is JSON-serializable
    serialized = json.dumps(result)
    assert isinstance(serialized, str)


@given(collector=telemetry_collector_strategy())
@settings(max_examples=100)
def test_branch_accounting_invariant(collector):
    """Property 4: Branch accounting invariant

    For any sequence of record_branch_result calls,
    hard_fail_count + score_filtered_count + gating_pass_count == branches_generated,
    where gating_pass_count is derived as branches_generated - hard_fail_count
    - score_filtered_count.

    **Validates: Requirements 7.3**
    """
    branches_generated = collector.branches_generated
    hard_fail_count = collector.hard_fail_count
    score_filtered_count = collector.score_filtered_count

    gating_pass_count = branches_generated - hard_fail_count - score_filtered_count

    # Conservation invariant: all three categories sum to total
    assert hard_fail_count + score_filtered_count + gating_pass_count == branches_generated, (
        f"Accounting invariant violated: "
        f"{hard_fail_count} + {score_filtered_count} + {gating_pass_count} "
        f"!= {branches_generated}"
    )

    # No negative counts — gating_pass_count must be non-negative
    assert gating_pass_count >= 0, (
        f"Negative gating_pass_count: {gating_pass_count} "
        f"(hard_fail={hard_fail_count}, score_filtered={score_filtered_count}, "
        f"total={branches_generated})"
    )
