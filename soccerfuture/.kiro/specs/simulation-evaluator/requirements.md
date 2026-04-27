# Requirements Document

## Introduction

This feature refactors the existing football play simulation evaluator into a modular, testable architecture (`simulation_evaluator_v2`). The evaluator compares simulated play branches against real continuation windows and scores them on physical validity and tactical opportunity, with gating logic to reject impossible outcomes. The refactor preserves the existing JSON output structure while decomposing the evaluation pipeline into independent scoring modules: gating, validation (alignment + physical plausibility), predictive fidelity, tactical consistency, decision value, and aggregate scoring.

## Glossary

- **Branch**: A simulated continuation of a real football play from a specific decision point, represented as a sequence of timestamped player positions and events.
- **Continuation_Window**: The set of plausible real-world outcomes from the same decision point a branch originates from.
- **Evaluator**: The top-level orchestrator (`simulation_evaluator_v2`) that runs the full evaluation pipeline on a branch.
- **Gating_Module**: The module responsible for binary pass/fail checks that hard-reject branches before scoring begins.
- **Validation_Module**: The module responsible for checking structural correctness and field-level data integrity of a branch.
- **Alignment_Module**: The module responsible for temporally and spatially aligning a branch to its corresponding continuation window.
- **Predictive_Fidelity_Module**: The module responsible for scoring how well a branch's predicted outcomes match observed real-world patterns.
- **Physical_Plausibility_Module**: The module responsible for scoring whether player movements and events in a branch obey physical constraints (speed limits, acceleration bounds, field boundaries).
- **Tactical_Consistency_Module**: The module responsible for scoring whether a branch's play formations and player roles are tactically coherent.
- **Decision_Value_Module**: The module responsible for scoring the tactical opportunity a branch represents relative to the continuation window.
- **Aggregate_Module**: The module responsible for combining sub-scores into final validity and opportunity scores with full sub-metric transparency.
- **Validity_Score**: A normalized 0–1 score representing how physically plausible a branch is, derived from physical plausibility, alignment, and predictive fidelity sub-scores.
- **Opportunity_Score**: A normalized 0–1 score representing the tactical value of a branch relative to the continuation window, derived from tactical consistency and decision value sub-scores.
- **Gating_Flags**: A set of boolean flags indicating whether a branch passed each gate. All flags must be true for the branch to proceed to scoring.
- **Explanation**: A human-readable string describing why a gate failed or why a score is low.
- **Sub_Metric**: A named, numeric component of an aggregate score that traces how the aggregate was derived.
- **Evaluation_Report**: The complete JSON-serializable output for a single branch, containing validity_score, opportunity_score, gating_flags, and explanations.

## Requirements

### Requirement 1: Evaluator Module Structure

**User Story:** As a sports AI engineer, I want the evaluator decomposed into independent scoring modules, so that I can develop, test, and reason about each scoring dimension in isolation.

#### Acceptance Criteria

1. THE Evaluator SHALL expose independent modules for gating, validation, alignment, predictive fidelity, physical plausibility, tactical consistency, decision value, and aggregate scoring under `src/scoring/`.
2. THE Evaluator SHALL ensure that no scoring module under `src/scoring/` imports from any other scoring module under `src/scoring/`.
3. THE Evaluator SHALL compose scoring modules exclusively at the orchestration layer in `src/simulation_evaluator_v2.py`.
4. WHEN a new scoring module is added, THE Evaluator SHALL require that the module exposes type-hinted public functions with Google-style docstrings.

### Requirement 2: Evaluation Pipeline Ordering

**User Story:** As a football analyst, I want branches to be rejected early if they are physically impossible, so that I only review tactically meaningful results.

#### Acceptance Criteria

1. THE Evaluator SHALL execute the evaluation pipeline in strict order: gating, then validity scoring, then opportunity scoring.
2. WHEN a branch fails any gate, THE Evaluator SHALL skip validity and opportunity scoring for that branch.
3. WHEN a branch fails validity scoring below a configured threshold, THE Evaluator SHALL skip opportunity scoring for that branch.
4. THE Evaluator SHALL never allow an opportunity score to override or mask a gating failure.

### Requirement 3: Gating Logic

**User Story:** As a football analyst, I want impossible branches hard-rejected with clear explanations, so that I can trust the remaining results are physically plausible.

#### Acceptance Criteria

1. THE Gating_Module SHALL perform binary pass/fail checks on each branch.
2. WHEN a branch contains player positions outside the football field boundaries, THE Gating_Module SHALL reject the branch.
3. WHEN a branch contains player speeds exceeding the maximum human sprint speed threshold, THE Gating_Module SHALL reject the branch.
4. WHEN a branch contains temporal discontinuities (e.g., timestamps out of order or gaps exceeding the allowed tolerance), THE Gating_Module SHALL reject the branch.
5. WHEN a branch fails any gate, THE Gating_Module SHALL return a Gating_Flags structure with the failing flag set to false and an Explanation describing the failure reason.
6. WHEN a branch passes all gates, THE Gating_Module SHALL return a Gating_Flags structure with all flags set to true and an empty explanations list.
7. THE Gating_Module SHALL define all threshold constants (field boundaries, max speed, temporal tolerance) as named constants in `src/utils/`.

### Requirement 4: Validation and Alignment

**User Story:** As a sports AI engineer, I want branches validated for structural correctness and aligned to their continuation windows, so that downstream scoring operates on clean, comparable data.

#### Acceptance Criteria

1. THE Validation_Module SHALL verify that each branch contains all required fields (player positions, timestamps, event markers) before scoring proceeds.
2. IF a branch is missing required fields, THEN THE Validation_Module SHALL return a descriptive error identifying the missing fields.
3. THE Alignment_Module SHALL temporally align a branch to its corresponding Continuation_Window using the branch's decision-point timestamp.
4. THE Alignment_Module SHALL spatially align player positions to a common coordinate frame before scoring.
5. WHEN alignment produces residual offsets exceeding a configured tolerance, THE Alignment_Module SHALL include the residual magnitude in its output as a Sub_Metric.

### Requirement 5: Physical Plausibility Scoring

**User Story:** As a football analyst, I want each branch scored on whether player movements obey physical constraints, so that I can filter out unrealistic simulations.

#### Acceptance Criteria

1. THE Physical_Plausibility_Module SHALL compute a Validity_Score normalized to the 0–1 range for each branch.
2. THE Physical_Plausibility_Module SHALL evaluate player speed, acceleration, and deceleration against configurable physical thresholds.
3. THE Physical_Plausibility_Module SHALL return Sub_Metrics for each physical dimension (speed_score, acceleration_score, deceleration_score) alongside the aggregate plausibility score.
4. WHEN any player in a branch exhibits teleportation-like movement (position change exceeding the maximum physically possible displacement for the elapsed time), THE Physical_Plausibility_Module SHALL assign a plausibility score of 0.0 for that player's movement segment.
5. THE Physical_Plausibility_Module SHALL define all physical threshold constants as named constants in `src/utils/`.

### Requirement 6: Predictive Fidelity Scoring

**User Story:** As a tactical researcher, I want to know how well a branch's predicted outcomes match real-world patterns, so that I can assess simulation quality.

#### Acceptance Criteria

1. THE Predictive_Fidelity_Module SHALL compute a fidelity score normalized to the 0–1 range by comparing branch outcomes against the Continuation_Window.
2. THE Predictive_Fidelity_Module SHALL return Sub_Metrics breaking down fidelity by position accuracy, event timing accuracy, and formation consistency.
3. WHEN a branch diverges significantly from all outcomes in the Continuation_Window, THE Predictive_Fidelity_Module SHALL assign a fidelity score below 0.3.
4. THE Predictive_Fidelity_Module SHALL use deterministic, rule-based comparison logic with no machine-learning dependencies.

### Requirement 7: Tactical Consistency Scoring

**User Story:** As a football analyst, I want branches scored on whether formations and player roles are tactically coherent, so that I can identify realistic play alternatives.

#### Acceptance Criteria

1. THE Tactical_Consistency_Module SHALL compute a consistency score normalized to the 0–1 range for each branch.
2. THE Tactical_Consistency_Module SHALL evaluate whether player roles remain consistent with their assigned positions throughout the branch.
3. THE Tactical_Consistency_Module SHALL return Sub_Metrics for role_consistency_score and formation_coherence_score alongside the aggregate consistency score.
4. WHEN a branch contains a player performing actions inconsistent with the player's assigned role, THE Tactical_Consistency_Module SHALL reduce the role_consistency_score proportionally.

### Requirement 8: Decision Value Scoring

**User Story:** As a tactical researcher, I want to quantify the tactical opportunity a branch represents compared to what actually happened, so that I can identify high-value alternative decisions.

#### Acceptance Criteria

1. THE Decision_Value_Module SHALL compute an Opportunity_Score normalized to the 0–1 range for each branch relative to the Continuation_Window.
2. THE Decision_Value_Module SHALL return Sub_Metrics for yard_gain_differential, turnover_risk_delta, and scoring_probability_delta alongside the aggregate opportunity score.
3. WHEN a branch produces a worse expected outcome than the real continuation, THE Decision_Value_Module SHALL assign an opportunity score below 0.5.
4. THE Decision_Value_Module SHALL use deterministic, rule-based scoring logic with no machine-learning dependencies.

### Requirement 9: Aggregate Scoring and Output Structure

**User Story:** As a sports AI engineer, I want the evaluator to produce a stable JSON output structure with full sub-metric transparency, so that downstream systems can consume results without breaking.

#### Acceptance Criteria

1. THE Aggregate_Module SHALL combine sub-scores into a final Evaluation_Report containing validity_score, opportunity_score, gating_flags, and explanations.
2. THE Aggregate_Module SHALL include all Sub_Metrics from each scoring module in the Evaluation_Report so that every aggregate score is fully traceable.
3. THE Evaluator SHALL produce JSON output that preserves the existing output structure. New fields may be added but existing fields must not be renamed or removed.
4. THE Evaluator SHALL ensure all Evaluation_Report fields are JSON-serializable using Python's built-in `json` module.
5. FOR ALL valid Evaluation_Reports, serializing to JSON then deserializing back SHALL produce an equivalent Evaluation_Report (round-trip property).

### Requirement 10: Regression Testing

**User Story:** As a sports AI engineer, I want regression tests that verify known-good and known-bad branches produce expected results, so that refactoring does not introduce regressions.

#### Acceptance Criteria

1. THE test suite SHALL include a regression test verifying that a realistic branch (from `data/evaluator_demo_input.json`) passes all gates and receives a validity_score above 0.5.
2. THE test suite SHALL include a regression test verifying that a teleport branch (containing physically impossible player movement) fails the physical plausibility gate.
3. WHEN a teleport branch is evaluated, THE Evaluator SHALL include an Explanation identifying the teleportation-like movement as the rejection reason.
4. THE test suite SHALL load test data from `data/evaluator_demo_input.json` and not embed branch data inline in test files.
5. THE test suite SHALL include property-based tests (using hypothesis) verifying that all scores produced by the Evaluator are within the 0–1 range for any valid branch input.
6. FOR ALL branches processed by the Evaluator, serializing the Evaluation_Report to JSON then deserializing SHALL produce an equivalent report (round-trip property).

### Requirement 11: Demo Data and Entry Point

**User Story:** As a sports AI engineer, I want a demo input file and a clear entry point, so that I can quickly run the evaluator and verify it works end-to-end.

#### Acceptance Criteria

1. THE project SHALL include a demo input file at `data/evaluator_demo_input.json` containing at least one realistic branch and one teleport branch with their corresponding continuation windows.
2. THE Evaluator SHALL be runnable from the project root via `python -m src.simulation_evaluator_v2` using the demo input file.
3. WHEN run with the demo input, THE Evaluator SHALL print the Evaluation_Report for each branch to stdout as formatted JSON.

### Requirement 12: Code Quality and Dependency Constraints

**User Story:** As a sports AI engineer, I want the codebase to follow consistent quality standards with minimal dependencies, so that the evaluator remains maintainable and deterministic.

#### Acceptance Criteria

1. THE Evaluator SHALL use Python 3.11+ with type hints on all public function signatures.
2. THE Evaluator SHALL use only deterministic, rule-based scoring logic with no machine-learning library dependencies.
3. THE Evaluator SHALL define all threshold constants and magic numbers as named constants in `src/utils/`.
4. THE Evaluator SHALL include Google-style docstrings on all public functions and classes.
5. THE Evaluator SHALL use `dataclasses` or plain typed dicts for all data structures, avoiding Pydantic unless explicitly added.
