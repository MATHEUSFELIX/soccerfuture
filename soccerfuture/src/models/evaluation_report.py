"""Data models for evaluation output.

Defines the evaluation report and its sub-metrics. These are the primary
output structures produced by the evaluator pipeline.
JSON-serializable via ``dataclasses.asdict()``.
"""

from dataclasses import dataclass, field


@dataclass
class SubMetrics:
    """Detailed sub-metrics that trace how aggregate scores were derived.

    Every field corresponds to a specific scoring dimension so that analysts
    can understand exactly how validity and opportunity scores were computed.

    Attributes:
        speed_score: Physical plausibility sub-score for player speed (m/s).
        acceleration_score: Physical plausibility sub-score for acceleration (m/s²).
        deceleration_score: Physical plausibility sub-score for deceleration (m/s²).
        position_accuracy: Predictive fidelity sub-score for position matching (meters).
        event_timing_accuracy: Predictive fidelity sub-score for event timing.
        formation_consistency: Predictive fidelity sub-score for formation shape.
        role_consistency_score: Tactical consistency sub-score for role adherence
            across soccer positions (GK, CB, LB, RB, CDM, CM, CAM, LW, RW, ST).
        formation_coherence_score: Tactical consistency sub-score for formation coherence.
        ball_progression: Decision value sub-metric for ball progression
            in meters toward the opponent goal, normalised to [0, 1].
        turnover_risk_delta: Decision value sub-metric for turnover risk change
            (interception, dispossession).
        scoring_probability_delta: Decision value sub-metric for goal
            scoring probability change.
        alignment_residual: Alignment sub-metric for residual offset magnitude.
        plausibility_score: Aggregate physical plausibility score.
        fidelity_score: Aggregate predictive fidelity score.
        tactical_consistency_score: Aggregate tactical consistency score.
        decision_value_score: Aggregate decision value score.
        compactness_score: Tactical consistency sub-score for formation compactness.
        defensive_density_score: Tactical consistency sub-score for defensive
            player concentration around key attacking players.
        formation_shape_score: Tactical consistency sub-score for tactical
            formation shape maintenance (e.g. 4-3-3, 4-4-2, 3-5-2).
        branch_window_similarity: Similarity measure between branch trajectory
            and continuation window, used by the reality anchor mechanism.
    """

    speed_score: float = 0.0
    acceleration_score: float = 0.0
    deceleration_score: float = 0.0
    position_accuracy: float = 0.0
    event_timing_accuracy: float = 0.0
    formation_consistency: float = 0.0
    role_consistency_score: float = 0.0
    formation_coherence_score: float = 0.0
    ball_progression: float = 0.0
    turnover_risk_delta: float = 0.0
    scoring_probability_delta: float = 0.0
    alignment_residual: float = 0.0
    plausibility_score: float = 0.0
    fidelity_score: float = 0.0
    tactical_consistency_score: float = 0.0
    decision_value_score: float = 0.0
    # --- New v3 fields ---
    compactness_score: float = 0.0
    defensive_density_score: float = 0.0
    formation_shape_score: float = 0.0
    branch_window_similarity: float = 0.0


@dataclass
class EvaluationReport:
    """Complete evaluation output for a single branch.

    Contains the final validity and opportunity scores, gating flags,
    human-readable explanations, and the full set of sub-metrics for
    traceability. All spatial metrics use meters and all speed metrics
    use meters per second.

    Attributes:
        branch_id: Identifier of the evaluated branch.
        validity_score: Normalized 0–1 score for physical plausibility.
        opportunity_score: Normalized 0–1 score for tactical value.
        gating_flags: Boolean flags for each gate (all True means passed).
        explanations: Human-readable reasons for failures or low scores.
        sub_metrics: Detailed sub-metrics from all scoring modules.
        passed_gating: Whether the branch passed all gating checks.
        passed_validity: Whether the branch met the validity threshold.
    """

    branch_id: str
    validity_score: float
    opportunity_score: float
    gating_flags: dict[str, bool] = field(default_factory=dict)
    explanations: list[str] = field(default_factory=list)
    sub_metrics: SubMetrics = field(default_factory=SubMetrics)
    passed_gating: bool = False
    passed_validity: bool = False
