"""Evaluator configuration model.

Provides optional threshold overrides for the evaluation pipeline.
JSON-serializable via ``dataclasses.asdict()``.
"""

from dataclasses import dataclass


@dataclass
class EvaluatorConfig:
    """Configuration overrides for the evaluation pipeline.

    Default values match the named constants in ``src/utils/constants.py``.
    Pass an instance to ``evaluate_branch`` or ``evaluate_all`` to override
    thresholds for testing or tuning.

    Attributes:
        validity_threshold: Minimum validity score to proceed to opportunity
            scoring. Defaults to 0.5.
        max_speed_override: If set, overrides MAX_HUMAN_SPRINT_SPEED for
            gating. None means use the default constant.
        temporal_tolerance_override: If set, overrides TEMPORAL_TOLERANCE for
            alignment. None means use the default constant.
    """

    validity_threshold: float = 0.35
    max_speed_override: float | None = None
    temporal_tolerance_override: float | None = None
