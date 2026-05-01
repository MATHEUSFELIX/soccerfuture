"""Robustness evaluation suite with degradation strategies and paired execution.

Provides deterministic degradation strategies that produce modified copies
of a PlayState, paired pipeline execution (baseline vs degraded), and
batch orchestration for running all strategies across multiple scenarios.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Callable

from src.models.play_state import PlayState
from src.pipeline import PipelineConfig, run_pipeline
from src.utils.constants import FIELD_LENGTH, FIELD_WIDTH

# ---------------------------------------------------------------------------
# Field bounds for clamping
# ---------------------------------------------------------------------------

_X_MIN: float = 0.0
_X_MAX: float = FIELD_WIDTH   # 68.0
_Y_MIN: float = 0.0
_Y_MAX: float = FIELD_LENGTH  # 105.0


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to the closed interval [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Degradation strategies
# ---------------------------------------------------------------------------


def degrade_noise(
    play_state: PlayState,
    seed: int = 42,
    noise_scale: float = 2.0,
) -> PlayState:
    """Add Gaussian noise to all player positions (bounded to field).

    Each player position's x and y coordinates are perturbed by
    independent Gaussian samples with mean 0 and standard deviation
    *noise_scale*, then clamped to the field bounds.

    Args:
        play_state: The original play state (not mutated).
        seed: RNG seed for deterministic degradation.
        noise_scale: Standard deviation of the Gaussian noise.

    Returns:
        A deep copy of *play_state* with noisy positions.
    """
    degraded = copy.deepcopy(play_state)
    rng = random.Random(seed)
    for pos in degraded.player_positions:
        pos.x = _clamp(pos.x + rng.gauss(0, noise_scale), _X_MIN, _X_MAX)
        pos.y = _clamp(pos.y + rng.gauss(0, noise_scale), _Y_MIN, _Y_MAX)
    return degraded


def degrade_missing_players(
    play_state: PlayState,
    seed: int = 42,
    drop_count: int = 2,
) -> PlayState:
    """Remove *drop_count* random players from positions and roles.

    Players are selected uniformly at random (without replacement) from
    the current player_positions list. Their corresponding entries in
    player_roles are also removed.

    Args:
        play_state: The original play state (not mutated).
        seed: RNG seed for deterministic degradation.
        drop_count: Number of players to remove.

    Returns:
        A deep copy of *play_state* with fewer players.
    """
    degraded = copy.deepcopy(play_state)
    rng = random.Random(seed)

    if not degraded.player_positions:
        return degraded

    actual_drop = min(drop_count, len(degraded.player_positions))
    to_drop = rng.sample(degraded.player_positions, actual_drop)
    drop_ids = {p.player_id for p in to_drop}

    degraded.player_positions = [
        p for p in degraded.player_positions if p.player_id not in drop_ids
    ]
    degraded.player_roles = {
        pid: role
        for pid, role in degraded.player_roles.items()
        if pid not in drop_ids
    }
    return degraded


def degrade_time_shift(
    play_state: PlayState,
    shift_seconds: float = 5.0,
) -> PlayState:
    """Shift match_time and game_clock by *shift_seconds*.

    match_time is increased and game_clock is decreased by the shift
    amount. game_clock is clamped to a minimum of 0.

    Args:
        play_state: The original play state (not mutated).
        shift_seconds: Number of seconds to shift forward.

    Returns:
        A deep copy of *play_state* with shifted times.
    """
    degraded = copy.deepcopy(play_state)
    degraded.match_time = degraded.match_time + shift_seconds
    degraded.game_clock = max(0.0, degraded.game_clock - shift_seconds)
    return degraded


def degrade_position_swap(
    play_state: PlayState,
    seed: int = 42,
) -> PlayState:
    """Swap positions of two random players.

    Two distinct players are chosen uniformly at random and their x/y
    coordinates are exchanged. If fewer than two players exist, the
    state is returned unchanged.

    Args:
        play_state: The original play state (not mutated).
        seed: RNG seed for deterministic degradation.

    Returns:
        A deep copy of *play_state* with two players' positions swapped.
    """
    degraded = copy.deepcopy(play_state)
    rng = random.Random(seed)

    if len(degraded.player_positions) < 2:
        return degraded

    a, b = rng.sample(range(len(degraded.player_positions)), 2)
    pa = degraded.player_positions[a]
    pb = degraded.player_positions[b]
    pa.x, pb.x = pb.x, pa.x
    pa.y, pb.y = pb.y, pa.y
    return degraded


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

DEGRADATION_STRATEGIES: dict[str, Callable] = {
    "noise": degrade_noise,
    "missing_players": degrade_missing_players,
    "time_shift": degrade_time_shift,
    "position_swap": degrade_position_swap,
}

# ---------------------------------------------------------------------------
# Paired execution
# ---------------------------------------------------------------------------


def _extract_top_n_ids(report: object, n: int) -> list[str]:
    """Extract the top-N branch IDs from a pipeline report.

    Args:
        report: A completed PipelineReport.
        n: Number of top branch IDs to return.

    Returns:
        List of branch_id strings, up to *n* entries.
    """
    return [rb.branch_id for rb in report.ranked_branches[:n]]


def _avg_score(report: object, key: str) -> float:
    """Compute the average of a score field across ranked branches.

    Args:
        report: A completed PipelineReport.
        key: The evaluation report key to average.

    Returns:
        The mean value, or 0.0 if no ranked branches exist.
    """
    scores = [
        rb.evaluation_report.get(key, 0.0)
        for rb in report.ranked_branches
    ]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


@dataclass
class RobustnessResult:
    """Per-scenario, per-strategy comparison between baseline and degraded runs.

    Attributes:
        scenario_id: Identifier for the scenario.
        strategy: Name of the degradation strategy applied.
        baseline_top_1: Top-1 branch ID from the baseline run.
        degraded_top_1: Top-1 branch ID from the degraded run.
        top_1_changed: Whether the top-1 branch changed.
        baseline_top_3: Top-3 branch IDs from the baseline run.
        degraded_top_3: Top-3 branch IDs from the degraded run.
        top_3_changed: Whether the top-3 ranking changed.
        avg_validity_delta: Degraded avg validity minus baseline avg validity.
        avg_opportunity_delta: Degraded avg opportunity minus baseline avg opportunity.
        gating_pass_delta: Degraded gating pass count minus baseline gating pass count.
        notes: Human-readable observations about the comparison.
    """

    scenario_id: str
    strategy: str
    baseline_top_1: str | None
    degraded_top_1: str | None
    top_1_changed: bool
    baseline_top_3: list[str]
    degraded_top_3: list[str]
    top_3_changed: bool
    avg_validity_delta: float
    avg_opportunity_delta: float
    gating_pass_delta: int
    notes: list[str] = field(default_factory=list)


def run_robustness_scenario(
    play_state: PlayState,
    strategy_name: str,
    scenario_id: str,
    config: PipelineConfig | None = None,
) -> RobustnessResult:
    """Run baseline and degraded pipeline, compare results.

    Executes the pipeline on the original play state (baseline) and on
    a degraded copy produced by the named strategy, then computes deltas
    for validity, opportunity, gating pass counts, and ranking changes.

    Args:
        play_state: The original game situation.
        strategy_name: Key into DEGRADATION_STRATEGIES.
        scenario_id: Identifier for this scenario.
        config: Optional pipeline configuration overrides.

    Returns:
        A RobustnessResult capturing the diff between baseline and degraded.

    Raises:
        KeyError: If *strategy_name* is not in DEGRADATION_STRATEGIES.
    """
    if strategy_name not in DEGRADATION_STRATEGIES:
        raise KeyError(
            f"Unknown degradation strategy: {strategy_name!r}. "
            f"Available: {list(DEGRADATION_STRATEGIES.keys())}"
        )

    degrade_fn = DEGRADATION_STRATEGIES[strategy_name]
    degraded_state = degrade_fn(play_state)

    baseline_report = run_pipeline(play_state, config=config)
    degraded_report = run_pipeline(degraded_state, config=config)

    # Extract top-N IDs
    baseline_top_1_list = _extract_top_n_ids(baseline_report, 1)
    degraded_top_1_list = _extract_top_n_ids(degraded_report, 1)
    baseline_top_3 = _extract_top_n_ids(baseline_report, 3)
    degraded_top_3 = _extract_top_n_ids(degraded_report, 3)

    baseline_top_1 = baseline_top_1_list[0] if baseline_top_1_list else None
    degraded_top_1 = degraded_top_1_list[0] if degraded_top_1_list else None

    top_1_changed = baseline_top_1 != degraded_top_1
    top_3_changed = baseline_top_3 != degraded_top_3

    # Compute score deltas
    baseline_avg_validity = _avg_score(baseline_report, "validity_score")
    degraded_avg_validity = _avg_score(degraded_report, "validity_score")
    baseline_avg_opportunity = _avg_score(baseline_report, "opportunity_score")
    degraded_avg_opportunity = _avg_score(degraded_report, "opportunity_score")

    avg_validity_delta = round(degraded_avg_validity - baseline_avg_validity, 6)
    avg_opportunity_delta = round(
        degraded_avg_opportunity - baseline_avg_opportunity, 6
    )

    # Gating pass counts
    baseline_pass_count = baseline_report.metadata.get("gating_pass_count", 0)
    degraded_pass_count = degraded_report.metadata.get("gating_pass_count", 0)
    gating_pass_delta = degraded_pass_count - baseline_pass_count

    # Notes
    notes: list[str] = []
    if top_1_changed:
        notes.append(
            f"Top-1 changed from {baseline_top_1} to {degraded_top_1}."
        )
    if top_3_changed:
        notes.append("Top-3 ranking order changed after degradation.")
    if avg_validity_delta < -0.05:
        notes.append(
            f"Validity dropped by {abs(avg_validity_delta):.4f} after {strategy_name}."
        )
    if avg_opportunity_delta < -0.05:
        notes.append(
            f"Opportunity dropped by {abs(avg_opportunity_delta):.4f} after {strategy_name}."
        )
    if gating_pass_delta < 0:
        notes.append(
            f"Gating pass count decreased by {abs(gating_pass_delta)} after {strategy_name}."
        )

    return RobustnessResult(
        scenario_id=scenario_id,
        strategy=strategy_name,
        baseline_top_1=baseline_top_1,
        degraded_top_1=degraded_top_1,
        top_1_changed=top_1_changed,
        baseline_top_3=baseline_top_3,
        degraded_top_3=degraded_top_3,
        top_3_changed=top_3_changed,
        avg_validity_delta=avg_validity_delta,
        avg_opportunity_delta=avg_opportunity_delta,
        gating_pass_delta=gating_pass_delta,
        notes=notes,
    )


def run_robustness_batch(
    scenarios: list[dict],
    strategies: list[str] | None = None,
    config: PipelineConfig | None = None,
) -> list[RobustnessResult]:
    """Run all strategies on all scenarios.

    Each scenario dict must contain ``"scenario_id"`` and ``"play_state"``
    keys. If *strategies* is None, all registered strategies are used.

    Args:
        scenarios: List of scenario dicts with ``scenario_id`` and
            ``play_state`` keys.
        strategies: Optional list of strategy names to apply. Defaults
            to all registered strategies.
        config: Optional pipeline configuration overrides.

    Returns:
        List of RobustnessResult objects, one per (scenario, strategy) pair.
    """
    strategy_names = strategies or list(DEGRADATION_STRATEGIES.keys())
    results: list[RobustnessResult] = []

    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        play_state = scenario["play_state"]
        for strategy_name in strategy_names:
            result = run_robustness_scenario(
                play_state=play_state,
                strategy_name=strategy_name,
                scenario_id=scenario_id,
                config=config,
            )
            results.append(result)

    return results
