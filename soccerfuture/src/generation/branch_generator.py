"""Branch generator module.

Produces N alternative branches from a PlayState using three perturbation
strategies (route variation, speed variation, decision variation) and
synthesizes a ContinuationWindow baseline for evaluation.

All randomness uses a local ``random.Random(seed)`` instance — no global
state is mutated.
"""

import math
import random
from dataclasses import dataclass, field

from src.models.play_state import PlayState
from src.utils.constants import (
    FIELD_LENGTH,
    FIELD_WIDTH,
    GENERATION_SNAPSHOTS_MAX,
    GENERATION_SNAPSHOTS_MIN,
    GENERATION_TIMESTEP,
    MAX_HUMAN_SPRINT_SPEED,
    MAX_ROUTE_ANGLE_DELTA,
    MAX_SPEED_FACTOR,
    MAX_TIMESTAMP_GAP,
    MIN_SPEED_FACTOR,
    SPEED_SAFETY_FACTOR,
)

# Derived safe speed ceiling used throughout generation.
_SAFE_SPEED = MAX_HUMAN_SPRINT_SPEED * SPEED_SAFETY_FACTOR

# Strategy name constants.
STRATEGY_ROUTE = "route_variation"
STRATEGY_SPEED = "speed_variation"
STRATEGY_DECISION = "decision_variation"

# Round-robin ordering of strategies.
_STRATEGY_CYCLE = [STRATEGY_ROUTE, STRATEGY_SPEED, STRATEGY_DECISION]

# Base movement vectors per role (dx, dy per timestep at unit speed).
_ROLE_BASE_VECTORS: dict[str, tuple[float, float]] = {
    "GK": (0.0, 0.1),    # minimal movement near goal
    "CB": (0.0, 0.3),    # central defensive coverage
    "LB": (-0.3, 0.7),   # left flank overlap
    "RB": (0.3, 0.7),    # right flank overlap
    "CDM": (0.0, 0.4),   # central defensive midfield coverage
    "CM": (0.1, 0.6),    # box-to-box movement
    "CAM": (0.0, 0.8),   # attacking midfield movement
    "LW": (-0.4, 0.8),   # left wing run
    "RW": (0.4, 0.8),    # right wing run
    "ST": (0.0, 0.9),    # striker movement in the box
}
_DEFAULT_VECTOR: tuple[float, float] = (0.0, 0.5)


@dataclass
class GenerationResult:
    """Output of the branch generator.

    Attributes:
        branches: List of generated Branch dicts.
        continuation_window: Synthesized ContinuationWindow dict.
        strategy_counts: How many branches used each strategy.
    """

    branches: list[dict]
    continuation_window: dict
    strategy_counts: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_branches(
    play_state: PlayState,
    n: int = 20,
    seed: int = 42,
) -> GenerationResult:
    """Generate N branches from a PlayState using seeded RNG.

    Uses a local ``random.Random(seed)`` instance — no global state mutation.
    Distributes branches across three perturbation strategies in a
    round-robin pattern to ensure strategy diversity.

    Args:
        play_state: The game situation to branch from.
        n: Number of branches to generate (10–30).
        seed: RNG seed for deterministic output.

    Returns:
        GenerationResult with N branches and one ContinuationWindow.

    Raises:
        ValueError: If *n* is outside [10, 30].
    """
    if n < 10 or n > 30:
        raise ValueError(
            f"n must be between 10 and 30 inclusive, got {n}"
        )

    rng = random.Random(seed)
    strategy_counts: dict[str, int] = {s: 0 for s in _STRATEGY_CYCLE}
    branches: list[dict] = []

    for i in range(n):
        strategy = _STRATEGY_CYCLE[i % len(_STRATEGY_CYCLE)]
        branch = _build_branch(play_state, i, strategy, rng, seed)
        branches.append(branch)
        strategy_counts[strategy] += 1

    continuation_window = synthesize_continuation_window(play_state, rng)

    return GenerationResult(
        branches=branches,
        continuation_window=continuation_window,
        strategy_counts=strategy_counts,
    )


def synthesize_continuation_window(
    play_state: PlayState,
    rng: random.Random,
) -> dict:
    """Synthesize a ContinuationWindow from a PlayState.

    Creates a baseline "what actually happened" window with:
    - window_id: ``"synth-cw-001"``
    - decision_point_timestamp matching PlayState
    - One outcome with positions projected forward 2–3 timesteps

    Args:
        play_state: Source game situation.
        rng: Seeded Random instance.

    Returns:
        ContinuationWindow as a plain dict.
    """
    n_steps = rng.randint(2, 3)
    projected = _project_positions_forward(
        play_state.player_positions,
        play_state.decision_point_timestamp,
        n_steps,
        rng,
    )

    avg_y_gain = _average_y_displacement(
        play_state.player_positions, projected
    )

    outcome: dict = {
        "positions": projected,
        "meter_gain": round(avg_y_gain, 2),
        "turnover": False,
        "scoring_play": False,
    }

    return {
        "window_id": "synth-cw-001",
        "decision_point_timestamp": play_state.decision_point_timestamp,
        "outcomes": [outcome],
        "metadata": {
            "source": "branch_generator",
            "projection_steps": n_steps,
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_branch(
    play_state: PlayState,
    index: int,
    strategy: str,
    rng: random.Random,
    seed: int,
) -> dict:
    """Construct a single branch dict using the given strategy.

    Args:
        play_state: Source game situation.
        index: Zero-based branch index (used for branch_id).
        strategy: One of the ``STRATEGY_*`` constants.
        rng: Seeded Random instance.
        seed: Original seed (stored in metadata).

    Returns:
        Branch dict conforming to the Branch dataclass structure.
    """
    branch_id = f"gen-{index + 1:03d}"
    ts = play_state.decision_point_timestamp

    if strategy == STRATEGY_ROUTE:
        positions, events = _route_variation(play_state, rng)
    elif strategy == STRATEGY_SPEED:
        positions, events = _speed_variation(play_state, rng)
    else:
        positions, events = _decision_variation(play_state, rng)

    return {
        "branch_id": branch_id,
        "decision_point_timestamp": ts,
        "positions": positions,
        "events": events,
        "player_roles": dict(play_state.player_roles),
        "metadata": {
            "strategy": strategy,
            "seed": seed,
            "source": "branch_generator",
        },
    }


# ---------------------------------------------------------------------------
# Perturbation strategy: Route Variation
# ---------------------------------------------------------------------------


def _route_variation(
    play_state: PlayState,
    rng: random.Random,
) -> tuple[list[dict], list[dict]]:
    """Apply route-variation perturbation.

    Rotates each player's base movement vector by a random angle within
    ``[-MAX_ROUTE_ANGLE_DELTA, +MAX_ROUTE_ANGLE_DELTA]`` and generates
    3–5 position snapshots at ``GENERATION_TIMESTEP`` intervals.

    Args:
        play_state: Source game situation.
        rng: Seeded Random instance.

    Returns:
        Tuple of (positions list, events list).
    """
    n_snapshots = rng.randint(GENERATION_SNAPSHOTS_MIN, GENERATION_SNAPSHOTS_MAX)
    positions: list[dict] = []

    for pp in play_state.player_positions:
        role = play_state.player_roles.get(pp.player_id, "")
        base_dx, base_dy = _ROLE_BASE_VECTORS.get(role, _DEFAULT_VECTOR)
        angle = rng.uniform(-MAX_ROUTE_ANGLE_DELTA, MAX_ROUTE_ANGLE_DELTA)
        dx, dy = _rotate_vector(base_dx, base_dy, angle)
        speed = rng.uniform(_SAFE_SPEED * 0.4, _SAFE_SPEED)
        dx, dy = _scale_to_speed(dx, dy, speed)

        cur_x, cur_y = pp.x, pp.y
        for step in range(n_snapshots):
            t = play_state.decision_point_timestamp + (step + 1) * GENERATION_TIMESTEP
            cur_x = _clamp(cur_x + dx * GENERATION_TIMESTEP, 0.0, FIELD_WIDTH)
            cur_y = _clamp(
                cur_y + dy * GENERATION_TIMESTEP,
                0.0,
                FIELD_LENGTH,
            )
            positions.append(_pos_dict(pp.player_id, cur_x, cur_y, t))

    events = _default_events(play_state)
    return positions, events


# ---------------------------------------------------------------------------
# Perturbation strategy: Speed Variation
# ---------------------------------------------------------------------------


def _speed_variation(
    play_state: PlayState,
    rng: random.Random,
) -> tuple[list[dict], list[dict]]:
    """Apply speed-variation perturbation.

    Keeps base movement directions but scales each player's speed by an
    independent random factor in ``[MIN_SPEED_FACTOR, MAX_SPEED_FACTOR]``,
    clamped to the safe speed ceiling.

    Args:
        play_state: Source game situation.
        rng: Seeded Random instance.

    Returns:
        Tuple of (positions list, events list).
    """
    n_snapshots = rng.randint(GENERATION_SNAPSHOTS_MIN, GENERATION_SNAPSHOTS_MAX)
    positions: list[dict] = []

    for pp in play_state.player_positions:
        role = play_state.player_roles.get(pp.player_id, "")
        base_dx, base_dy = _ROLE_BASE_VECTORS.get(role, _DEFAULT_VECTOR)
        factor = rng.uniform(MIN_SPEED_FACTOR, MAX_SPEED_FACTOR)
        speed = min(factor * _SAFE_SPEED, _SAFE_SPEED)
        dx, dy = _scale_to_speed(base_dx, base_dy, speed)

        cur_x, cur_y = pp.x, pp.y
        for step in range(n_snapshots):
            t = play_state.decision_point_timestamp + (step + 1) * GENERATION_TIMESTEP
            cur_x = _clamp(cur_x + dx * GENERATION_TIMESTEP, 0.0, FIELD_WIDTH)
            cur_y = _clamp(
                cur_y + dy * GENERATION_TIMESTEP,
                0.0,
                FIELD_LENGTH,
            )
            positions.append(_pos_dict(pp.player_id, cur_x, cur_y, t))

    events = _default_events(play_state)
    return positions, events


# ---------------------------------------------------------------------------
# Perturbation strategy: Decision Variation
# ---------------------------------------------------------------------------


def _decision_variation(
    play_state: PlayState,
    rng: random.Random,
) -> tuple[list[dict], list[dict]]:
    """Apply decision-variation perturbation.

    Alters the event sequence (e.g. pass vs. run) and adjusts player
    positions to be consistent with the altered events.

    Args:
        play_state: Source game situation.
        rng: Seeded Random instance.

    Returns:
        Tuple of (positions list, events list).
    """
    n_snapshots = rng.randint(GENERATION_SNAPSHOTS_MIN, GENERATION_SNAPSHOTS_MAX)
    is_pass_play = rng.choice([True, False])
    positions: list[dict] = []
    ts = play_state.decision_point_timestamp

    for pp in play_state.player_positions:
        role = play_state.player_roles.get(pp.player_id, "")
        dx, dy = _decision_vector(role, is_pass_play, rng)
        speed = rng.uniform(_SAFE_SPEED * 0.3, _SAFE_SPEED)
        dx, dy = _scale_to_speed(dx, dy, speed)

        cur_x, cur_y = pp.x, pp.y
        for step in range(n_snapshots):
            t = ts + (step + 1) * GENERATION_TIMESTEP
            cur_x = _clamp(cur_x + dx * GENERATION_TIMESTEP, 0.0, FIELD_WIDTH)
            cur_y = _clamp(
                cur_y + dy * GENERATION_TIMESTEP,
                0.0,
                FIELD_LENGTH,
            )
            positions.append(_pos_dict(pp.player_id, cur_x, cur_y, t))

    events = _decision_events(play_state, is_pass_play, rng)
    return positions, events


def _decision_vector(
    role: str,
    is_pass_play: bool,
    rng: random.Random,
) -> tuple[float, float]:
    """Return a movement vector adjusted for the play-type decision.

    Args:
        role: Player role string.
        is_pass_play: Whether the altered decision is a pass play.
        rng: Seeded Random instance.

    Returns:
        (dx, dy) unit-ish direction vector.
    """
    if is_pass_play:
        # Pass play: attackers push forward, midfielders support
        if role in ("LW", "RW", "ST", "CAM"):
            return (rng.uniform(-0.3, 0.3), 1.0)
        if role == "GK":
            return (rng.uniform(-0.1, 0.1), 0.0)
        return (0.0, 0.3)
    # Dribble play: ball carrier drives forward, others hold shape
    if role == "ST":
        return (rng.uniform(-0.5, 0.5), 0.8)
    if role in ("CM", "CAM"):
        return (rng.uniform(-0.3, 0.3), 0.6)
    if role == "GK":
        return (rng.uniform(-0.1, 0.1), 0.0)
    return (0.0, 0.4)


def _decision_events(
    play_state: PlayState,
    is_pass_play: bool,
    rng: random.Random,
) -> list[dict]:
    """Generate events consistent with the altered decision.

    Args:
        play_state: Source game situation.
        is_pass_play: Whether the altered decision is a pass play.
        rng: Seeded Random instance.

    Returns:
        List of event dicts.
    """
    ts = play_state.decision_point_timestamp
    st_id = _find_role_player(play_state, "ST")
    cm_id = _find_role_player(play_state, "CM")
    lw_id = _find_role_player(play_state, "LW")

    events: list[dict] = []
    if is_pass_play and cm_id:
        events.append(_event_dict("pass", ts + 0.3, cm_id))
        target = st_id or lw_id
        if target:
            events.append(_event_dict("pass", ts + 0.6, target))
    elif st_id:
        events.append(_event_dict("dribble", ts + 0.2, st_id))
        events.append(_event_dict("shot", ts + 0.4, st_id))
    else:
        # Fallback: generic kick_off event
        pid = play_state.player_positions[0].player_id if play_state.player_positions else "unknown"
        events.append(_event_dict("kick_off", ts + 0.1, pid))

    return events


# ---------------------------------------------------------------------------
# Shared utility helpers
# ---------------------------------------------------------------------------


def _rotate_vector(
    dx: float, dy: float, angle: float
) -> tuple[float, float]:
    """Rotate a 2D vector by *angle* radians.

    Args:
        dx: X component.
        dy: Y component.
        angle: Rotation angle in radians.

    Returns:
        Rotated (dx, dy).
    """
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a


def _scale_to_speed(
    dx: float, dy: float, speed: float
) -> tuple[float, float]:
    """Scale a direction vector so its magnitude equals *speed*.

    Args:
        dx: X component of direction.
        dy: Y component of direction.
        speed: Desired magnitude (meters/second).

    Returns:
        Scaled (dx, dy).
    """
    mag = math.hypot(dx, dy)
    if mag < 1e-9:
        return (0.0, speed)
    return (dx / mag * speed, dy / mag * speed)


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to [lo, hi].

    Args:
        value: Input value.
        lo: Lower bound.
        hi: Upper bound.

    Returns:
        Clamped value.
    """
    return max(lo, min(hi, value))


def _pos_dict(
    player_id: str, x: float, y: float, timestamp: float
) -> dict:
    """Create a position dict.

    Args:
        player_id: Player identifier.
        x: X coordinate.
        y: Y coordinate.
        timestamp: Timestamp in seconds.

    Returns:
        Dict with player_id, x, y, timestamp keys.
    """
    return {
        "player_id": player_id,
        "x": round(x, 4),
        "y": round(y, 4),
        "timestamp": round(timestamp, 4),
    }


def _event_dict(
    event_type: str,
    timestamp: float,
    player_id: str,
    metadata: dict | None = None,
) -> dict:
    """Create an event dict.

    Args:
        event_type: Type of event.
        timestamp: Event timestamp.
        player_id: Involved player.
        metadata: Optional extra data.

    Returns:
        Dict conforming to EventMarker structure.
    """
    return {
        "event_type": event_type,
        "timestamp": round(timestamp, 4),
        "player_id": player_id,
        "metadata": metadata or {},
    }


def _default_events(play_state: PlayState) -> list[dict]:
    """Generate a minimal default event list for route/speed strategies.

    Args:
        play_state: Source game situation.

    Returns:
        List containing a single kick_off or pass event.
    """
    ts = play_state.decision_point_timestamp
    pid = (
        play_state.player_positions[0].player_id
        if play_state.player_positions
        else "unknown"
    )
    return [_event_dict("kick_off", ts + 0.1, pid)]


def _find_role_player(
    play_state: PlayState, role: str
) -> str | None:
    """Find the first player_id with the given role.

    Args:
        play_state: Source game situation.
        role: Role string to search for.

    Returns:
        player_id or None if not found.
    """
    for pid, r in play_state.player_roles.items():
        if r == role:
            return pid
    return None


def _project_positions_forward(
    player_positions: list,
    base_timestamp: float,
    n_steps: int,
    rng: random.Random,
) -> list[dict]:
    """Project player positions forward with small random deltas.

    Args:
        player_positions: Base PlayerPosition objects.
        base_timestamp: Starting timestamp.
        n_steps: Number of timesteps to project.
        rng: Seeded Random instance.

    Returns:
        List of position dicts.
    """
    positions: list[dict] = []
    for pp in player_positions:
        cur_x, cur_y = pp.x, pp.y
        for step in range(n_steps):
            t = base_timestamp + (step + 1) * GENERATION_TIMESTEP
            dx = rng.uniform(-0.5, 0.5)
            dy = rng.uniform(0.0, 1.0)
            cur_x = _clamp(cur_x + dx, 0.0, FIELD_WIDTH)
            cur_y = _clamp(
                cur_y + dy,
                0.0,
                FIELD_LENGTH,
            )
            positions.append(_pos_dict(pp.player_id, cur_x, cur_y, t))
    return positions


def _average_y_displacement(
    original: list, projected: list[dict]
) -> float:
    """Compute average forward (y-axis) displacement.

    Args:
        original: Original PlayerPosition objects.
        projected: Projected position dicts.

    Returns:
        Average y displacement in meters.
    """
    if not original:
        return 0.0
    orig_y = {pp.player_id: pp.y for pp in original}
    total = 0.0
    count = 0
    for p in projected:
        pid = p["player_id"]
        if pid in orig_y:
            total += p["y"] - orig_y[pid]
            count += 1
    return total / count if count > 0 else 0.0
