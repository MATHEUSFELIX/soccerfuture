# Implementation Plan: Simulation Evaluator v2

## Overview

Refactor the football play simulation evaluator into a modular architecture under `src/scoring/`, with an orchestration layer in `src/simulation_evaluator_v2.py`. Implementation follows the pipeline order: validation → gating → alignment → validity scoring → opportunity scoring → aggregate. Each task builds incrementally, wiring modules together as they are created. All scoring is deterministic and rule-based with no ML dependencies.

## Tasks

- [x] 1. Set up project structure, constants, and data models
  - [x] 1.1 Create `src/utils/constants.py` with all named constants (field dimensions, physical thresholds, temporal thresholds, scoring thresholds, alignment tolerances)
    - Define FIELD_LENGTH, FIELD_WIDTH, END_ZONE_DEPTH, MAX_HUMAN_SPRINT_SPEED, MAX_ACCELERATION, MAX_DECELERATION, MAX_TIMESTAMP_GAP, TEMPORAL_TOLERANCE, DEFAULT_VALIDITY_THRESHOLD, SIGNIFICANT_DIVERGENCE_THRESHOLD, ALIGNMENT_RESIDUAL_TOLERANCE
    - _Requirements: 3.7, 5.5, 12.3_

  - [x] 1.2 Create data models in `src/models/`
    - Create `src/models/branch.py` with PlayerPosition, EventMarker, and Branch dataclasses
    - Create `src/models/continuation_window.py` with ContinuationWindow dataclass
    - Create `src/models/evaluation_report.py` with SubMetrics and EvaluationReport dataclasses
    - Create `src/models/config.py` with EvaluatorConfig dataclass
    - Create `src/models/__init__.py` re-exporting all models
    - All models must be JSON-serializable via `dataclasses.asdict()`
    - _Requirements: 9.1, 9.4, 12.1, 12.5_

  - [x] 1.3 Create `src/utils/serialization.py` with `report_to_dict` and `dict_to_report` helpers
    - `report_to_dict` converts EvaluationReport to a JSON-serializable dict
    - `dict_to_report` reconstructs an EvaluationReport from a dict
    - Create `src/utils/__init__.py`
    - _Requirements: 9.4, 9.5_

  - [x] 1.4 Create `data/evaluator_demo_input.json` with demo input data
    - Include at least one realistic branch with valid player positions, ordered timestamps, and plausible speeds
    - Include at least one teleport branch with physically impossible player movement (position change exceeding max displacement for elapsed time)
    - Include corresponding continuation windows for each branch
    - _Requirements: 11.1_

  - [x] 1.5 Write unit tests for data models and serialization in `tests/models/test_models.py` and `tests/utils/test_serialization.py`
    - Test dataclass instantiation and field access
    - Test `report_to_dict` round-trip on a known report
    - Test `dict_to_report` raises on malformed dict
    - _Requirements: 9.4, 9.5_

  - [x] 1.6 Write property test for round-trip serialization
    - **Property 16: Evaluation report round-trip serialization**
    - Generate random EvaluationReport instances via hypothesis; serialize with `report_to_dict` + `json.dumps`, deserialize with `json.loads` + `dict_to_report`, assert equivalence
    - **Validates: Requirements 9.5, 10.6**

- [x] 2. Implement validation and gating modules
  - [x] 2.1 Implement `src/scoring/validation.py` with `validate_branch` function
    - Define ValidationResult dataclass (is_valid, missing_fields, error_message)
    - Check that branch dict contains all required fields (branch_id, decision_point_timestamp, positions, events, player_roles, metadata)
    - Return descriptive error identifying missing fields
    - Create `src/scoring/__init__.py`
    - _Requirements: 4.1, 4.2, 12.1, 12.4_

  - [x] 2.2 Write property test for validation missing-field detection
    - **Property 7: Validation identifies exactly the missing fields**
    - Generate branch dicts with random subsets of required fields removed; verify missing_fields matches exactly
    - **Validates: Requirements 4.1, 4.2**

  - [x] 2.3 Implement `src/scoring/gating.py` with `run_gates` function
    - Define GatingResult dataclass (passed, flags, explanations)
    - Implement field_bounds gate: reject if any player position outside field boundaries
    - Implement max_speed gate: reject if any player speed between consecutive frames exceeds MAX_HUMAN_SPRINT_SPEED
    - Implement temporal_continuity gate: reject if timestamps out of order or gaps exceed MAX_TIMESTAMP_GAP
    - All thresholds sourced from `src/utils/constants.py`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 2.4 Write unit tests for validation module in `tests/scoring/test_validation.py`
    - Test complete branch passes validation
    - Test branch missing `positions` fails with correct error
    - Test branch missing multiple fields lists all missing fields
    - _Requirements: 4.1, 4.2_

  - [x] 2.5 Write unit tests for gating module in `tests/scoring/test_gating.py`
    - Test realistic branch passes all gates
    - Test out-of-bounds branch fails field_bounds gate
    - Test teleport branch fails max_speed gate
    - Test disordered timestamps fail temporal_continuity gate
    - Test multiple gate failures are all reported
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 2.6 Write property test for out-of-bounds gating rejection
    - **Property 3: Out-of-bounds positions cause gating rejection**
    - Generate branches with at least one player position outside field boundaries; verify gating rejects with field_bounds=false
    - **Validates: Requirements 3.2**

  - [x] 2.7 Write property test for excessive speed gating rejection
    - **Property 4: Excessive speed causes gating rejection**
    - Generate branches with at least one player whose speed between consecutive frames exceeds MAX_HUMAN_SPRINT_SPEED; verify gating rejects with max_speed=false
    - **Validates: Requirements 3.3**

  - [x] 2.8 Write property test for temporal discontinuity gating rejection
    - **Property 5: Temporal discontinuity causes gating rejection**
    - Generate branches with out-of-order timestamps or gaps exceeding MAX_TIMESTAMP_GAP; verify gating rejects with temporal_continuity=false
    - **Validates: Requirements 3.4**

  - [x] 2.9 Write property test for gating result consistency
    - **Property 6: Gating result consistency**
    - Generate any branch; verify that if passed=false then at least one flag is false and explanations is non-empty, and if passed=true then all flags are true and explanations is empty
    - **Validates: Requirements 3.5, 3.6**

- [x] 3. Checkpoint — Validation and gating
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement alignment and validity scoring modules
  - [x] 4.1 Implement `src/scoring/alignment.py` with `align` function
    - Define AlignmentResult dataclass (aligned_branch, aligned_window, temporal_offset, spatial_offset, residual_magnitude)
    - Align branch to continuation window using decision-point timestamp as anchor
    - Compute temporal and spatial offsets; flag residual if it exceeds ALIGNMENT_RESIDUAL_TOLERANCE
    - _Requirements: 4.3, 4.4, 4.5_

  - [x] 4.2 Implement `src/scoring/physical_plausibility.py` with `score_physical_plausibility` function
    - Define PhysicalPlausibilityResult dataclass (plausibility_score, speed_score, acceleration_score, deceleration_score)
    - Evaluate speed, acceleration, deceleration against thresholds from constants
    - Teleportation-like movements (displacement exceeding max possible for elapsed time) receive 0.0
    - Clamp outputs to [0.0, 1.0]; replace NaN with 0.0
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 4.3 Implement `src/scoring/predictive_fidelity.py` with `score_predictive_fidelity` function
    - Define PredictiveFidelityResult dataclass (fidelity_score, position_accuracy, event_timing_accuracy, formation_consistency)
    - Compare branch outcomes against continuation window using deterministic, rule-based logic
    - Branches diverging significantly from all window outcomes receive fidelity < 0.3
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 4.4 Write unit tests for alignment in `tests/scoring/test_alignment.py`
    - Test known offset produces expected aligned positions
    - Test zero-offset case is identity
    - Test large residual is flagged in output
    - _Requirements: 4.3, 4.4, 4.5_

  - [x] 4.5 Write unit tests for physical plausibility in `tests/scoring/test_physical_plausibility.py`
    - Test stationary players score 1.0
    - Test moderate movement scores between 0 and 1
    - Test teleportation scores 0.0
    - _Requirements: 5.1, 5.3, 5.4_

  - [x] 4.6 Write unit tests for predictive fidelity in `tests/scoring/test_predictive_fidelity.py`
    - Test identical branch and window score 1.0
    - Test completely unrelated branch and window score < 0.3
    - _Requirements: 6.1, 6.3_

  - [x] 4.7 Write property test for alignment anchor
    - **Property 8: Alignment anchors on decision-point timestamp**
    - Generate branch + window with known decision-point timestamps; verify aligned data offsets are computed relative to the shared anchor
    - **Validates: Requirements 4.3, 4.4**

  - [x] 4.8 Write property test for large alignment residual
    - **Property 9: Large alignment residual appears in output**
    - Generate alignments where residual exceeds ALIGNMENT_RESIDUAL_TOLERANCE; verify residual_magnitude is non-zero in output
    - **Validates: Requirements 4.5**

  - [x] 4.9 Write property test for teleportation plausibility
    - **Property 10: Teleportation yields zero plausibility for that segment**
    - Generate branches with teleportation movements; verify the affected segment receives plausibility score 0.0
    - **Validates: Requirements 5.4**

  - [x] 4.10 Write property test for significant divergence fidelity
    - **Property 11: Significant divergence yields low fidelity**
    - Generate branches completely unrelated to the continuation window; verify fidelity_score < 0.3
    - **Validates: Requirements 6.3**

- [x] 5. Checkpoint — Alignment and validity scoring
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement opportunity scoring modules
  - [x] 6.1 Implement `src/scoring/tactical_consistency.py` with `score_tactical_consistency` function
    - Define TacticalConsistencyResult dataclass (consistency_score, role_consistency_score, formation_coherence_score)
    - Evaluate whether players maintain role-consistent behavior throughout the branch
    - Role violations reduce role_consistency_score proportionally
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 6.2 Implement `src/scoring/decision_value.py` with `score_decision_value` function
    - Define DecisionValueResult dataclass (opportunity_score, yard_gain_differential, turnover_risk_delta, scoring_probability_delta)
    - Compare branch expected outcomes against real continuation; branches worse than reality receive < 0.5
    - Deterministic, rule-based scoring
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 6.3 Write unit tests for tactical consistency in `tests/scoring/test_tactical_consistency.py`
    - Test role-consistent branch scores high
    - Test role-violating branch scores lower
    - _Requirements: 7.1, 7.4_

  - [x] 6.4 Write unit tests for decision value in `tests/scoring/test_decision_value.py`
    - Test branch better than reality scores > 0.5
    - Test branch worse than reality scores < 0.5
    - _Requirements: 8.1, 8.3_

  - [x] 6.5 Write property test for role violations reducing tactical consistency
    - **Property 12: Role violations reduce tactical consistency**
    - Generate a branch, inject a role-inconsistent action; verify role_consistency_score decreases compared to the same branch without the violation
    - **Validates: Requirements 7.4**

  - [x] 6.6 Write property test for worse-than-reality opportunity
    - **Property 13: Worse-than-reality yields low opportunity**
    - Generate branches whose expected outcomes are strictly worse than the continuation window; verify opportunity_score < 0.5
    - **Validates: Requirements 8.3**

- [x] 7. Checkpoint — Opportunity scoring
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement aggregate module and orchestrator
  - [x] 8.1 Implement `src/scoring/aggregate.py` with `compute_aggregate` function
    - Define AggregateInput dataclass collecting all upstream scoring results
    - Compute validity_score as weighted combination of plausibility, fidelity, and alignment residual
    - Compute opportunity_score as weighted combination of tactical consistency and decision value
    - Preserve all sub-metrics in the EvaluationReport for full traceability
    - _Requirements: 9.1, 9.2_

  - [x] 8.2 Implement `src/simulation_evaluator_v2.py` with `evaluate_branch` and `evaluate_all` functions
    - Compose all scoring modules in strict pipeline order: validation → gating → alignment → physical plausibility + predictive fidelity → tactical consistency + decision value → aggregate
    - Implement early termination: return error report on validation failure, return gated report (validity=0, opportunity=0) on gating failure, return low-validity report (opportunity=0) when validity below threshold
    - Catch scoring exceptions and convert to error-state reports with explanations
    - Accept optional EvaluatorConfig for threshold overrides
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 9.3_

  - [x] 8.3 Add `__main__.py` entry point in `src/` so the evaluator is runnable via `python -m src.simulation_evaluator_v2`
    - Load `data/evaluator_demo_input.json`, call `evaluate_all`, print formatted JSON to stdout
    - _Requirements: 11.2, 11.3_

  - [x] 8.4 Write unit tests for aggregate module in `tests/scoring/test_aggregate.py`
    - Test all sub-scores combined produce correct validity and opportunity
    - Test all sub-metrics are present in the report
    - _Requirements: 9.1, 9.2_

  - [x] 8.5 Write property test for gating failure zeroing downstream scores
    - **Property 1: Gating failure zeroes downstream scores**
    - Generate branches that fail gating; verify validity_score=0.0 and opportunity_score=0.0
    - **Validates: Requirements 2.1, 2.2, 2.4**

  - [x] 8.6 Write property test for low validity skipping opportunity
    - **Property 2: Low validity skips opportunity scoring**
    - Generate branches that pass gating but receive validity below threshold; verify opportunity_score=0.0
    - **Validates: Requirements 2.3**

  - [x] 8.7 Write property test for all scores in [0, 1]
    - **Property 14: All scores and sub-metrics are in [0, 1]**
    - Generate any valid branch processed by the evaluator; verify every score and sub-metric field is a float in [0.0, 1.0]
    - **Validates: Requirements 5.1, 5.3, 6.1, 6.2, 7.1, 7.3, 8.1, 8.2, 10.5**

  - [x] 8.8 Write property test for aggregate report completeness and JSON-serializability
    - **Property 15: Aggregate report completeness and JSON-serializability**
    - Generate random valid scoring results; verify the EvaluationReport contains all required fields and `json.dumps` succeeds
    - **Validates: Requirements 9.1, 9.2, 9.4**

- [x] 9. Checkpoint — Aggregate and orchestrator
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Regression tests and final integration
  - [x] 10.1 Implement regression tests in `tests/test_evaluator_v2.py`
    - Load `data/evaluator_demo_input.json` at test time (not inline)
    - Test realistic branch passes all gates and receives validity_score > 0.5
    - Test teleport branch fails gating with explanation mentioning teleportation-like movement
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 10.2 Write integration tests for end-to-end pipeline in `tests/test_evaluator_v2.py`
    - Test `evaluate_all` processes multiple branches and returns correct number of reports
    - Test error-state reports are valid JSON and conform to EvaluationReport schema
    - _Requirements: 9.3, 9.4_

- [x] 11. Final checkpoint — All tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation after each pipeline stage.
- Property tests validate the 16 correctness properties defined in the design document.
- Unit tests validate specific examples and edge cases.
- All scoring modules under `src/scoring/` must remain independent — no cross-imports.
- Hypothesis strategies for branch/window generation should live in `tests/conftest.py` or `tests/strategies.py` for reuse.
