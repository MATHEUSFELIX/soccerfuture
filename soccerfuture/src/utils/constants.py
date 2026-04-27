"""Named constants for the simulation evaluator.

All threshold constants, field dimensions, and magic numbers used across
scoring modules are defined here. Scoring modules import from this file
rather than hard-coding values.
"""

# Field dimensions (meters)
FIELD_LENGTH: float = 105.0
FIELD_WIDTH: float = 68.0

# Soccer field areas (meters)
PENALTY_AREA_LENGTH: float = 16.5
PENALTY_AREA_WIDTH: float = 40.3
GOAL_AREA_LENGTH: float = 5.5
GOAL_AREA_WIDTH: float = 18.3
CENTER_CIRCLE_RADIUS: float = 9.15
CORNER_ARC_RADIUS: float = 1.0

# Physical thresholds
MAX_HUMAN_SPRINT_SPEED: float = 10.0  # meters per second
MAX_ACCELERATION: float = 7.0  # meters per second squared
MAX_DECELERATION: float = 8.0  # meters per second squared

# Temporal thresholds
MAX_TIMESTAMP_GAP: float = 0.5  # seconds — max allowed gap between frames
TEMPORAL_TOLERANCE: float = 0.05  # seconds — alignment tolerance

# Scoring
DEFAULT_VALIDITY_THRESHOLD: float = 0.35
SIGNIFICANT_DIVERGENCE_THRESHOLD: float = 0.3  # fidelity below this = significant divergence

# Alignment
ALIGNMENT_RESIDUAL_TOLERANCE: float = 1.0  # meters — residual above this is flagged

# --- Tactical Consistency v2 (v3 upgrade) ---
MAX_FORMATION_AREA: float = FIELD_WIDTH * 40.0       # 2720.0 sq meters
IDEAL_COMPACTNESS_RATIO: float = 0.3
DEFENSIVE_DENSITY_RADIUS: float = 10.0               # meters
EXPECTED_DEFENDERS_NEAR_BALL: float = 3.0
MAX_LINE_GAP_VARIANCE: float = 25.0                  # meters²

# --- Context-Aware Speed Thresholds ---
CONTACT_SPEED_THRESHOLD: float = 15.0                # meters/second
CONTACT_TIME_WINDOW: float = 0.5                     # seconds
CONTACT_EVENT_TYPES: frozenset[str] = frozenset({
    "tackle", "foul", "dispossession",
})

# --- Reality Anchor ---
REALITY_ANCHOR_SIMILARITY_THRESHOLD: float = 0.2
REALITY_ANCHOR_DAMPENING_FACTOR: float = 1.0
SIMILARITY_MAX_DISTANCE: float = 15.0                # meters
SIMILARITY_EVENT_TOLERANCE: float = 0.3              # seconds

# --- Branch Generation ---
# Constants governing the branch generation pipeline. Used by the Branch
# Generator and Pipeline Orchestrator to control perturbation strategies,
# snapshot cadence, and default pipeline configuration.

GENERATION_TIMESTEP: float = 0.2
"""Seconds between generated position snapshots within a branch."""

SPEED_SAFETY_FACTOR: float = 0.85
"""Fraction of MAX_HUMAN_SPRINT_SPEED used as the safe ceiling during generation."""

MAX_ROUTE_ANGLE_DELTA: float = 0.8
"""Maximum route deviation in radians (~45°) applied by the route-variation strategy."""

MIN_SPEED_FACTOR: float = 0.3
"""Minimum speed scaling factor for the speed-variation strategy."""

MAX_SPEED_FACTOR: float = 1.0
"""Maximum speed scaling factor (1.0 = full safe speed) for the speed-variation strategy."""

GENERATION_SNAPSHOTS_MIN: int = 3
"""Minimum number of position snapshots generated per player per branch."""

GENERATION_SNAPSHOTS_MAX: int = 5
"""Maximum number of position snapshots generated per player per branch."""

DEFAULT_N: int = 20
"""Default number of branches to generate per pipeline run."""

DEFAULT_K: int = 5
"""Default number of top-ranked branches to keep after filtering."""

DEFAULT_SEED: int = 42
"""Default RNG seed for deterministic branch generation."""

DEFAULT_VALIDITY_WEIGHT: float = 0.5
"""Default weight for the validity component of the composite score."""

DEFAULT_OPPORTUNITY_WEIGHT: float = 0.5
"""Default weight for the opportunity component of the composite score."""
