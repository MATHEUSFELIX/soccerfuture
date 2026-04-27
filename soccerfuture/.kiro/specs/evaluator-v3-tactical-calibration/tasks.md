# Implementation Plan: Evaluator v3 — Tactical Calibration

## Overview

Upgrade the football play simulation evaluator from v2 to v3 by implementing three targeted calibration fixes: compactness/density/line-integrity sub-metrics for tactical consistency, a reality-anchor mechanism for opportunity scoring, and context-aware speed thresholds for gating. Changes follow the existing pipeline order (constants → models → scoring modules → orchestrator → tests) and preserve modular architecture throughout.

## Tasks

- [x] 1. Add v3 constants to `src/utils/constants.py`
  - Add tactical consistency constants: `MAX_FORMATION_AREA`, `IDEAL_COMPACTNESS_RATIO`, `DEFENSIVE_DENSITY_RADIUS`, `EXPECTED_DEFENDERS_NEAR_BALL`, `MAX_LINE_GAP_VARIANCE`
  - Add context-aware speed constants: `CONTACT_SPEED_THRESHOLD`, `CONTACT_TIME_WINDOW`, `CONTACT_EVENT_TYPES`
  - Add reality anchor constants: `REALITY_ANCHOR_SIMILARITY_THRESHOLD`, `REALITY_ANCHOR_DAMPENING_FACTOR`, `SIMILARITY_MAX_DISTANCE`, `SIMILARITY_EVENT_TOLERANCE`
  - All constants must be typed and use descriptive names per design Section 5
  - _Requirements: 1.7, 2.7, 3.5_

- [x] 2. Expand SubMetrics dataclass in `src/models/evaluation_report.py`
  - Add four new float fields with default 0.0: `compactness_score`, `defensive_density_score`, `line_integrity_score`, `branch_window_similarity`
  - Preserve all existing fields unchanged — no renames, no removals
  - Update the class docstring to document the new fields
  - _Requirements: 4.1, 4.3, 4.5_

- [x] 3. Implement tactical consistency v2 in `src/scoring/tactical_consistency.py`
  - [x] 3.1 Update `TacticalConsistencyResult` dataclass with three new fields
    - Add `compactness_score`, `defensive_density_score`, `line_integrity_score` fields
    - Update docstring to document all six fields
    - _Requirements: 1.6, 7.3_

  - [x] 3.2 Implement `_compute_compactness` helper
    - Compute bounding box area from latest position snapshot
    - Normalize against `MAX_FORMATION_AREA` and `IDEAL_COMPACTNESS_RATIO`
    - Clamp result to [0, 1]; return 1.0 for single player or empty positions
    - _Requirements: 1.1_

  - [x] 3.3 Implement `_compute_defensive_density` helper
    - Identify ball carrier or QB from `player_roles` and `events`
    - Count defensive players (DL, LB, CB, S) within `DEFENSIVE_DENSITY_RADIUS` of key player
    - Score = `min(1.0, count / EXPECTED_DEFENDERS_NEAR_BALL)`; return 0.5 if no defenders
    - _Requirements: 1.2_

  - [x] 3.4 Implement `_compute_line_integrity` helper
    - Separate OL and DL players by role from latest snapshot
    - Compute consecutive x-gap variance for each group with ≥2 players
    - Score = `1.0 - min(1.0, variance / MAX_LINE_GAP_VARIANCE)`; average OL and DL scores
    - Return 1.0 if neither group has ≥2 players
    - _Requirements: 1.3_

  - [x] 3.5 Update `score_tactical_consistency` to use v3 weighted formula
    - Compute all five sub-metrics and aggregate with weights: 0.25 role + 0.20 formation + 0.20 compactness + 0.20 density + 0.15 line integrity
    - Return updated `TacticalConsistencyResult` with all six fields populated
    - _Requirements: 1.4, 1.5_

  - [ ]* 3.6 Write unit tests for tactical consistency v2 sub-metrics
    - Test compactness: tight formation scores high, excessively spread scores low
    - Test defensive density: clustered defenders score high, no defenders near ball scores low
    - Test line integrity: evenly spaced OL scores high, large gaps score low
    - Test weighted average matches expected formula
    - Test incoherent formation with valid roles scores below 0.7
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 3.7 Write property test: tactical consistency score equals weighted average (Property 2)
    - **Property 2: Tactical consistency score equals weighted average of sub-metrics**
    - **Validates: Requirements 1.4**

  - [ ]* 3.8 Write property test: TacticalConsistencyResult round-trip serialization (Property 11)
    - **Property 11: TacticalConsistencyResult round-trip serialization**
    - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 4. Checkpoint — Tactical consistency module
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement context-aware speed thresholds in `src/scoring/gating.py`
  - [x] 5.1 Update `_check_max_speed` to accept events and apply context-aware thresholds
    - Add `events` parameter (list[dict] | None)
    - For each speed measurement, compute midpoint timestamp
    - Scan events for contact types (`CONTACT_EVENT_TYPES`) within `CONTACT_TIME_WINDOW`
    - If contact context: apply `CONTACT_SPEED_THRESHOLD`; otherwise apply `MAX_HUMAN_SPRINT_SPEED`
    - Include applied threshold and contact context in rejection explanations
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

  - [x] 5.2 Update `run_gates` to pass events to `_check_max_speed`
    - Extract `events` from branch dict and pass to `_check_max_speed`
    - No signature change to `run_gates` — still takes a branch dict
    - _Requirements: 3.2, 3.3_

  - [ ]* 5.3 Write unit tests for context-aware speed gating
    - Test: sack event + speed 20 yd/s passes (contact context)
    - Test: speed 20 yd/s with no contact events fails
    - Test: speed 26 yd/s with contact event fails (exceeds contact threshold)
    - Test: explanation mentions threshold value and contact context
    - Test: no events behaves like v2 (base threshold only)
    - _Requirements: 3.2, 3.3, 3.4, 3.6_

  - [ ]* 5.4 Write property test: contact context allows elevated speed threshold (Property 6)
    - **Property 6: Contact context allows elevated speed threshold**
    - **Validates: Requirements 3.2, 3.3**

  - [ ]* 5.5 Write property test: speed exceeding contact threshold causes rejection (Property 7)
    - **Property 7: Speed exceeding contact threshold causes rejection**
    - **Validates: Requirements 3.4**

  - [ ]* 5.6 Write property test: speed rejection explanation includes threshold and context (Property 8)
    - **Property 8: Speed rejection explanation includes threshold and context**
    - **Validates: Requirements 3.6**

- [x] 6. Checkpoint — Gating module
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement reality anchor in `src/scoring/aggregate.py`
  - [x] 7.1 Add `continuation_window` field to `AggregateInput` dataclass
    - Add `continuation_window: dict` field
    - Update docstring
    - _Requirements: 2.1, 6.3_

  - [x] 7.2 Implement `_compute_branch_window_similarity` function
    - Compute position similarity: average Euclidean distance normalized by `SIMILARITY_MAX_DISTANCE`
    - Compute event similarity: fraction of branch events matched in window within `SIMILARITY_EVENT_TOLERANCE`
    - Combined: `0.6 * pos_sim + 0.4 * event_sim`
    - Return similarity in [0, 1]
    - _Requirements: 2.1_

  - [x] 7.3 Apply reality anchor dampening in `compute_aggregate`
    - After computing raw opportunity, check if similarity ≥ `REALITY_ANCHOR_SIMILARITY_THRESHOLD`
    - Apply dampening formula: pull toward 0.5 proportionally to similarity strength
    - Enforce guardrails: raw > 0.6 cannot be pulled below 0.6; raw < 0.4 cannot be pushed above 0.4
    - Populate `branch_window_similarity` in SubMetrics
    - Populate new tactical sub-metrics (compactness, density, line integrity) from TacticalConsistencyResult
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 4.2_

  - [ ]* 7.4 Write unit tests for reality anchor
    - Test: branch identical to window gets similarity ~1.0 and opportunity in [0.4, 0.6]
    - Test: branch clearly better gets opportunity > 0.6 even with high similarity
    - Test: branch clearly worse gets opportunity < 0.4 even with high similarity
    - Test: `branch_window_similarity` populated in sub_metrics
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 7.5 Write property test: reality anchor moves opportunity toward 0.5 (Property 3)
    - **Property 3: Reality anchor moves opportunity toward 0.5**
    - **Validates: Requirements 2.2**

  - [ ]* 7.6 Write property test: near-identical branches score opportunity in [0.4, 0.6] (Property 4)
    - **Property 4: Near-identical branches score opportunity in [0.4, 0.6]**
    - **Validates: Requirements 2.3**

  - [ ]* 7.7 Write property test: reality anchor respects directional bounds (Property 5)
    - **Property 5: Reality anchor respects directional bounds**
    - **Validates: Requirements 2.4, 2.5**

- [x] 8. Checkpoint — Aggregate module
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Wire v3 changes in orchestrator `src/simulation_evaluator_v2.py`
  - Pass `aligned_window` as `continuation_window` in `AggregateInput` constructor
  - No other orchestrator changes needed — pipeline ordering preserved
  - _Requirements: 6.3, 6.4, 6.5_

- [x] 10. Update Hypothesis strategies in `tests/strategies.py`
  - Add four new unit-float fields to `sub_metrics_strategy()`: `compactness_score`, `defensive_density_score`, `line_integrity_score`, `branch_window_similarity`
  - Add `tactical_consistency_result_strategy()` generating all 6 fields as unit floats
  - Add `contact_speed_branch_strategy()` for branches with contact events and speeds between base and contact thresholds
  - Add `near_identical_branch_window_strategy()` for branch/window pairs with tiny perturbations
  - Update `any_branch_strategy()` to include contact-speed branches
  - _Requirements: 4.1, 3.2_

- [x] 11. Update serialization and round-trip tests
  - [x] 11.1 Verify `src/utils/serialization.py` handles new SubMetrics fields
    - Confirm `dict_to_report` works with new fields (defaults handle missing keys)
    - Add defensive filtering if needed for backward compatibility
    - _Requirements: 4.4, 6.7_

  - [ ]* 11.2 Write property test: EvaluationReport round-trip with v3 fields (Property 9)
    - **Property 9: EvaluationReport round-trip serialization with v3 fields**
    - **Validates: Requirements 4.4, 6.7**

- [x] 12. Checkpoint — Integration wiring
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Write evaluator-level property tests
  - [ ]* 13.1 Write property test: all v3 scores and sub-metrics in [0, 1] (Property 1)
    - **Property 1: All v3 scores and sub-metrics are in [0, 1]**
    - **Validates: Requirements 1.1, 1.2, 1.3, 2.1, 4.5, 6.6**

  - [ ]* 13.2 Write property test: gating failure zeroes downstream scores (Property 10)
    - **Property 10: Gating failure zeroes downstream scores (v3 preserved)**
    - **Validates: Requirements 6.5**

- [x] 14. Write benchmark regression tests in `tests/test_benchmark_regression.py`
  - Load `data/benchmark_input.json` and `data/benchmark_annotated.json`
  - Run all 15 branches through the v3 evaluator
  - Verify each branch's validity_score and opportunity_score fall within annotated expected ranges
  - Specifically verify B13 passes gating and opportunity in [0.0, 0.3]
  - Specifically verify B14 opportunity in [0.4, 0.6]
  - Specifically verify B15 opportunity in [0.4, 0.6]
  - Verify the 12 branches that passed in v2 continue to pass (no regressions)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 15. Final checkpoint — Full test suite
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each module change
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The pipeline order (constants → models → tactical → gating → aggregate → orchestrator → tests) ensures no hanging code
