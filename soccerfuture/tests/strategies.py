"""Reusable Hypothesis strategies for simulation-evaluator property tests.

Provides composable strategies for generating random instances of the
project's core data models (SubMetrics, EvaluationReport, etc.) and
branch dictionaries for gating property tests.
"""

from __future__ import annotations

import math

from hypothesis import strategies as st

from src.models.branch import PlayerPosition
from src.models.evaluation_report import EvaluationReport, SubMetrics
from src.models.pipeline_report import PipelineReport, RankedBranch
from src.models.play_state import PlayState
from src.telemetry import TelemetryCollector
from src.utils.constants import (
    FIELD_LENGTH,
    FIELD_WIDTH,
    MAX_HUMAN_SPRINT_SPEED,
    MAX_TIMESTAMP_GAP,
)


# ---------------------------------------------------------------------------
# Manifest strategy
# ---------------------------------------------------------------------------

def manifest_strategy() -> st.SearchStrategy[dict]:
    """Generate valid benchmark manifest dicts.

    Produces manifests with:
    - version: short text
    - pipeline_config: dict with n, k, seed, validity_weight, opportunity_weight
    - scenarios: list of 1-3 scenario dicts with all required keys
    """
    unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

    pipeline_config = st.fixed_dictionaries({
        "n": st.integers(min_value=1, max_value=100),
        "k": st.integers(min_value=1, max_value=50),
        "seed": st.integers(min_value=0, max_value=2**31 - 1),
        "validity_weight": unit,
        "opportunity_weight": unit,
    })

    expected_top_k_entry = st.fixed_dictionaries({
        "branch_id": st.text(min_size=1, max_size=20),
        "composite_score": unit,
    })

    strategy_counts = st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.integers(min_value=0, max_value=50),
        min_size=1,
        max_size=5,
    )

    scenario = st.fixed_dictionaries({
        "scenario_file": st.text(min_size=1, max_size=50),
        "gating_pass_count": st.integers(min_value=0, max_value=100),
        "top_branch_min_score": unit,
        "bottom_branch_max_score": unit,
        "strategy_counts": strategy_counts,
        "expected_top_k": st.lists(expected_top_k_entry, min_size=1, max_size=5),
    })

    return st.fixed_dictionaries({
        "version": st.text(min_size=1, max_size=30),
        "pipeline_config": pipeline_config,
        "scenarios": st.lists(scenario, min_size=1, max_size=3),
    })


# ---------------------------------------------------------------------------
# SubMetrics strategy
# ---------------------------------------------------------------------------

def sub_metrics_strategy() -> st.SearchStrategy[SubMetrics]:
    """Generate random SubMetrics with all float fields in [0, 1]."""
    unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    return st.builds(
        SubMetrics,
        speed_score=unit,
        acceleration_score=unit,
        deceleration_score=unit,
        position_accuracy=unit,
        event_timing_accuracy=unit,
        formation_consistency=unit,
        role_consistency_score=unit,
        formation_coherence_score=unit,
        ball_progression=unit,
        turnover_risk_delta=unit,
        scoring_probability_delta=unit,
        alignment_residual=unit,
        plausibility_score=unit,
        fidelity_score=unit,
        tactical_consistency_score=unit,
        decision_value_score=unit,
        compactness_score=unit,
        defensive_density_score=unit,
        formation_shape_score=unit,
        branch_window_similarity=unit,
    )


# ---------------------------------------------------------------------------
# EvaluationReport strategy
# ---------------------------------------------------------------------------

def evaluation_report_strategy() -> st.SearchStrategy[EvaluationReport]:
    """Generate random EvaluationReport instances.

    - branch_id: arbitrary non-empty text
    - validity_score / opportunity_score: floats in [0, 1]
    - gating_flags: dict of str → bool (1-5 entries)
    - explanations: list of str (0-5 entries)
    - sub_metrics: from sub_metrics_strategy
    - passed_gating / passed_validity: booleans
    """
    unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    flag_keys = st.text(min_size=1, max_size=20)
    return st.builds(
        EvaluationReport,
        branch_id=st.text(min_size=1, max_size=50),
        validity_score=unit,
        opportunity_score=unit,
        gating_flags=st.dictionaries(flag_keys, st.booleans(), min_size=1, max_size=5),
        explanations=st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=5),
        sub_metrics=sub_metrics_strategy(),
        passed_gating=st.booleans(),
        passed_validity=st.booleans(),
    )


# ---------------------------------------------------------------------------
# Position / Branch strategies for gating property tests
# ---------------------------------------------------------------------------

# Finite floats that avoid NaN/Inf edge cases in arithmetic
_finite_float = st.floats(
    min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
)

# Valid in-bounds coordinates
_valid_x = st.floats(min_value=0.0, max_value=FIELD_WIDTH, allow_nan=False, allow_infinity=False)
_valid_y = st.floats(
    min_value=0.0,
    max_value=FIELD_LENGTH,
    allow_nan=False,
    allow_infinity=False,
)


def _position(
    player_id: str,
    x: st.SearchStrategy[float] = _valid_x,
    y: st.SearchStrategy[float] = _valid_y,
    timestamp: st.SearchStrategy[float] | None = None,
) -> st.SearchStrategy[dict]:
    """Build a single position dict strategy."""
    if timestamp is None:
        timestamp = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    return st.fixed_dictionaries(
        {"player_id": st.just(player_id), "x": x, "y": y, "timestamp": timestamp}
    )


def valid_positions_strategy(
    min_positions: int = 2, max_positions: int = 10
) -> st.SearchStrategy[list[dict]]:
    """Generate a list of in-bounds, temporally ordered, slow-moving positions.

    Positions are for a single player with small deltas so speed stays
    well below MAX_HUMAN_SPRINT_SPEED and timestamps are tightly spaced.
    """

    @st.composite
    def _build(draw: st.DrawFn) -> list[dict]:
        n = draw(st.integers(min_value=min_positions, max_value=max_positions))
        pid = draw(st.text(min_size=1, max_size=5, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
        x = draw(_valid_x)
        y = draw(_valid_y)
        t = draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
        positions: list[dict] = []
        for _ in range(n):
            positions.append({"player_id": pid, "x": x, "y": y, "timestamp": t})
            # Small delta so speed ≈ 0
            dx = draw(st.floats(min_value=-0.05, max_value=0.05, allow_nan=False, allow_infinity=False))
            dy = draw(st.floats(min_value=-0.05, max_value=0.05, allow_nan=False, allow_infinity=False))
            x = max(0.0, min(FIELD_WIDTH, x + dx))
            y = max(0.0, min(FIELD_LENGTH, y + dy))
            t += draw(st.floats(min_value=0.01, max_value=MAX_TIMESTAMP_GAP - 0.01, allow_nan=False, allow_infinity=False))
        return positions

    return _build()


def out_of_bounds_branch_strategy() -> st.SearchStrategy[dict]:
    """Generate a branch with at least one position outside field boundaries.

    Picks one of four violation types (x<0, x>FIELD_WIDTH, y<0,
    y>FIELD_LENGTH) and injects it into an otherwise valid position list.
    No end zones — violations occur at the raw field boundaries.
    """

    @st.composite
    def _build(draw: st.DrawFn) -> dict:
        # Start with some valid positions
        valid = draw(valid_positions_strategy(min_positions=1, max_positions=5))

        # Generate one out-of-bounds position
        violation = draw(st.sampled_from(["x_low", "x_high", "y_low", "y_high"]))
        pid = "OOB1"
        ts = valid[0]["timestamp"]  # reuse a valid timestamp

        if violation == "x_low":
            x = draw(st.floats(min_value=-1000.0, max_value=-0.01, allow_nan=False, allow_infinity=False))
            y = draw(_valid_y)
        elif violation == "x_high":
            x = draw(st.floats(min_value=FIELD_WIDTH + 0.01, max_value=1000.0, allow_nan=False, allow_infinity=False))
            y = draw(_valid_y)
        elif violation == "y_low":
            x = draw(_valid_x)
            y = draw(st.floats(min_value=-1000.0, max_value=-0.01, allow_nan=False, allow_infinity=False))
        else:  # y_high
            x = draw(_valid_x)
            y = draw(st.floats(min_value=FIELD_LENGTH + 0.01, max_value=1000.0, allow_nan=False, allow_infinity=False))

        bad_pos = {"player_id": pid, "x": x, "y": y, "timestamp": ts}
        return {"positions": valid + [bad_pos]}

    return _build()


def excessive_speed_branch_strategy() -> st.SearchStrategy[dict]:
    """Generate a branch where at least one player exceeds MAX_HUMAN_SPRINT_SPEED.

    Creates two consecutive positions for the same player where
    distance / dt > MAX_HUMAN_SPRINT_SPEED.
    """

    @st.composite
    def _build(draw: st.DrawFn) -> dict:
        pid = "FAST1"
        x1 = draw(_valid_x)
        y1 = draw(_valid_y)
        t1 = draw(st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False))
        dt = draw(st.floats(min_value=0.01, max_value=0.5, allow_nan=False, allow_infinity=False))
        t2 = t1 + dt

        # Need distance > MAX_HUMAN_SPRINT_SPEED * dt
        min_distance = MAX_HUMAN_SPRINT_SPEED * dt + 0.01
        # Pick a direction angle and compute displacement
        angle = draw(st.floats(min_value=0.0, max_value=2 * math.pi, allow_nan=False, allow_infinity=False))
        dist = draw(st.floats(min_value=min_distance, max_value=min_distance + 50.0, allow_nan=False, allow_infinity=False))
        x2 = x1 + dist * math.cos(angle)
        y2 = y1 + dist * math.sin(angle)

        pos1 = {"player_id": pid, "x": x1, "y": y1, "timestamp": t1}
        pos2 = {"player_id": pid, "x": x2, "y": y2, "timestamp": t2}
        return {"positions": [pos1, pos2]}

    return _build()


def temporal_discontinuity_branch_strategy() -> st.SearchStrategy[dict]:
    """Generate a branch with a timestamp gap exceeding MAX_TIMESTAMP_GAP.

    Creates positions for a single player where at least one consecutive
    pair has a gap > MAX_TIMESTAMP_GAP.
    """

    @st.composite
    def _build(draw: st.DrawFn) -> dict:
        pid = "TGAP1"
        x = draw(_valid_x)
        y = draw(_valid_y)
        t1 = draw(st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False))
        gap = draw(st.floats(
            min_value=MAX_TIMESTAMP_GAP + 0.01,
            max_value=MAX_TIMESTAMP_GAP + 10.0,
            allow_nan=False,
            allow_infinity=False,
        ))
        t2 = t1 + gap

        # Keep positions close so speed gate doesn't also fail
        dx = draw(st.floats(min_value=-0.01, max_value=0.01, allow_nan=False, allow_infinity=False))
        dy = draw(st.floats(min_value=-0.01, max_value=0.01, allow_nan=False, allow_infinity=False))

        pos1 = {"player_id": pid, "x": x, "y": y, "timestamp": t1}
        pos2 = {"player_id": pid, "x": x + dx, "y": y + dy, "timestamp": t2}
        return {"positions": [pos1, pos2]}

    return _build()


def any_branch_strategy() -> st.SearchStrategy[dict]:
    """Generate an arbitrary branch (valid or invalid) for consistency checks.

    Randomly picks from valid branches, out-of-bounds, excessive speed,
    temporal discontinuity, or a mix.
    """
    return st.one_of(
        # Valid branch
        valid_positions_strategy().map(lambda p: {"positions": p}),
        # Various invalid branches
        out_of_bounds_branch_strategy(),
        excessive_speed_branch_strategy(),
        temporal_discontinuity_branch_strategy(),
    )


# ---------------------------------------------------------------------------
# PlayState strategy
# ---------------------------------------------------------------------------

# Valid soccer player roles
_PLAYER_ROLES = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"]

# Game phases for soccer
_GAME_PHASES = ["open_play", "set_piece", "transition", "dead_ball"]


def play_state_strategy() -> st.SearchStrategy[PlayState]:
    """Generate valid PlayState instances for property-based testing.

    Produces PlayStates with:
    - match_time: float 0–90+
    - possession_team: short text
    - ball_position: dict with x (0–68) and y (0–105)
    - game_phase: one of open_play, set_piece, transition, dead_ball
    - score_differential: int -50 to 50
    - game_clock: float 0–5400
    - 5–11 player positions within field bounds
    - valid player_roles mapping
    - decision_point_timestamp: float 0–10
    """

    @st.composite
    def _build(draw: st.DrawFn) -> PlayState:
        n_players = draw(st.integers(min_value=5, max_value=11))
        decision_ts = draw(
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)
        )

        player_ids = [f"P{i}" for i in range(1, n_players + 1)]
        positions = []
        roles: dict[str, str] = {}
        for pid in player_ids:
            x = draw(_valid_x)
            y = draw(_valid_y)
            positions.append(PlayerPosition(player_id=pid, x=x, y=y, timestamp=decision_ts))
            role = draw(st.sampled_from(_PLAYER_ROLES))
            roles[pid] = role

        return PlayState(
            match_time=draw(
                st.floats(min_value=0.0, max_value=120.0, allow_nan=False, allow_infinity=False)
            ),
            possession_team=draw(
                st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz")
            ),
            ball_position={
                "x": draw(_valid_x),
                "y": draw(_valid_y),
            },
            game_phase=draw(st.sampled_from(_GAME_PHASES)),
            score_differential=draw(st.integers(min_value=-50, max_value=50)),
            game_clock=draw(
                st.floats(min_value=0.0, max_value=5400.0, allow_nan=False, allow_infinity=False)
            ),
            player_positions=positions,
            decision_point_timestamp=decision_ts,
            player_roles=roles,
            metadata={},
        )

    return _build()


# ---------------------------------------------------------------------------
# RankedBranch strategy
# ---------------------------------------------------------------------------

def ranked_branch_strategy() -> st.SearchStrategy[RankedBranch]:
    """Generate random RankedBranch instances for property-based testing.

    Produces RankedBranches with:
    - branch_id: short non-empty text
    - composite_score: float in [0, 1]
    - evaluation_report: small dict with string keys and float values
    - branch: small dict with string keys and string values
    """
    return st.builds(
        RankedBranch,
        branch_id=st.text(min_size=1, max_size=20),
        composite_score=st.floats(
            min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
        ),
        evaluation_report=st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=0,
            max_size=3,
        ),
        branch=st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.text(min_size=0, max_size=20),
            min_size=0,
            max_size=3,
        ),
    )


# ---------------------------------------------------------------------------
# PipelineReport strategy
# ---------------------------------------------------------------------------

def pipeline_report_strategy() -> st.SearchStrategy[PipelineReport]:
    """Generate valid PipelineReport instances for property-based testing.

    Produces PipelineReports with:
    - play_state: small dict with string keys and JSON-serializable values
    - evaluated_branches: list of small dicts (0-5 entries)
    - ranked_branches: list of RankedBranch (0-5 entries)
    - metadata: small dict with string keys and simple values
    - errors: list of short strings (0-3 entries)
    """
    _simple_values = st.one_of(
        st.text(min_size=0, max_size=20),
        st.integers(min_value=-100, max_value=100),
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        st.booleans(),
    )
    _str_dict = st.dictionaries(
        st.text(min_size=1, max_size=10),
        _simple_values,
        min_size=0,
        max_size=5,
    )
    return st.builds(
        PipelineReport,
        play_state=_str_dict,
        evaluated_branches=st.lists(_str_dict, min_size=0, max_size=5),
        ranked_branches=st.lists(ranked_branch_strategy(), min_size=0, max_size=5),
        metadata=_str_dict,
        errors=st.lists(st.text(min_size=0, max_size=50), min_size=0, max_size=3),
    )


# ---------------------------------------------------------------------------
# TelemetryCollector strategy
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Evaluation report dict strategy (as produced by dataclasses.asdict)
# ---------------------------------------------------------------------------

_SUB_METRIC_KEYS: list[str] = [
    "speed_score",
    "acceleration_score",
    "deceleration_score",
    "position_accuracy",
    "event_timing_accuracy",
    "formation_consistency",
    "role_consistency_score",
    "formation_coherence_score",
    "ball_progression",
    "turnover_risk_delta",
    "scoring_probability_delta",
    "alignment_residual",
    "plausibility_score",
    "fidelity_score",
    "tactical_consistency_score",
    "decision_value_score",
    "compactness_score",
    "defensive_density_score",
    "formation_shape_score",
    "branch_window_similarity",
]


def evaluation_report_dict_strategy() -> st.SearchStrategy[dict]:
    """Generate evaluation report dicts as produced by dataclasses.asdict on EvaluationReport.

    Produces dicts with:
    - branch_id: text
    - validity_score: float 0-1
    - opportunity_score: float 0-1
    - passed_gating: bool
    - passed_validity: bool
    - gating_flags: dict str->bool
    - explanations: list of str
    - sub_metrics: dict with all SubMetrics keys as float 0-1
    """
    unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

    sub_metrics = st.fixed_dictionaries(
        {key: unit for key in _SUB_METRIC_KEYS}
    )

    return st.fixed_dictionaries({
        "branch_id": st.text(min_size=1, max_size=50),
        "validity_score": unit,
        "opportunity_score": unit,
        "passed_gating": st.booleans(),
        "passed_validity": st.booleans(),
        "gating_flags": st.dictionaries(
            st.text(min_size=1, max_size=20), st.booleans(), min_size=1, max_size=5
        ),
        "explanations": st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=5),
        "sub_metrics": sub_metrics,
    })


# ---------------------------------------------------------------------------
# TelemetryCollector strategy
# ---------------------------------------------------------------------------

_STRATEGIES = ["route_variation", "speed_variation", "decision_variation"]


def strategy_counts_strategy() -> st.SearchStrategy[dict[str, int]]:
    """Generate strategy count distributions for entropy/dominance tests.

    Produces dicts with 1-5 strategy keys mapped to counts 1-50.
    """
    return st.dictionaries(
        st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"),
        st.integers(min_value=1, max_value=50),
        min_size=1,
        max_size=5,
    )


@st.composite
def telemetry_collector_strategy(draw: st.DrawFn) -> TelemetryCollector:
    """Generate a TelemetryCollector with recorded branch results and stage timings.

    Produces a collector that has:
    - 1-20 recorded branch results with random strategies, scores, and flags
    - Stage timings for generation, evaluation, and ranking
    """
    collector = TelemetryCollector()

    # Record stage timings (just start + end, no actual delay)
    for stage in ("generation", "evaluation", "ranking"):
        collector.start_stage(stage)
        collector.end_stage(stage)

    # Record 1-20 branch results
    n_branches = draw(st.integers(min_value=1, max_value=20))
    for _ in range(n_branches):
        strategy = draw(st.sampled_from(_STRATEGIES))
        composite_score = draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        )
        passed_gating = draw(st.booleans())
        passed_validity = draw(st.booleans())
        collector.record_branch_result(strategy, composite_score, passed_gating, passed_validity)

    return collector
