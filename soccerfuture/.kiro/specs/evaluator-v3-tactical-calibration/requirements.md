# Requirements Document

## Introduction

This feature upgrades the football play simulation evaluator from v2 to v3 by addressing three calibration failures identified through benchmark error analysis. The v2 evaluator scored 80% accuracy (12/15 branches correct) against a manually-classified benchmark. Error analysis revealed that the tactical consistency module is too permissive (always scoring ~1.0), the opportunity score formula lacks a reality anchor for neutral branches, and the gating module uses a single hard speed threshold that incorrectly rejects contact-driven movements like sacks. The v3 upgrade introduces a compactness and density model for tactical consistency, a reality-anchor mechanism for opportunity calibration, and context-aware speed thresholds for gating — targeting 100% benchmark accuracy (15/15 branches within expected ranges) while preserving the existing modular architecture and JSON output structure.

## Glossary

- **Evaluator**: The top-level orchestrator (`simulation_evaluator_v2.py`) that runs the full evaluation pipeline on a branch, to be upgraded to v3.
- **Tactical_Consistency_Module**: The module under `src/scoring/tactical_consistency.py` responsible for scoring whether a branch's formations and player roles are tactically coherent.
- **Compactness_Score**: A new sub-metric measuring how tight or spread a team's formation is relative to the play context, derived from the convex hull area or bounding box of player positions.
- **Defensive_Density_Score**: A new sub-metric measuring the concentration of defensive players around key offensive players (e.g., the ball carrier or QB).
- **Line_Integrity_Score**: A new sub-metric measuring whether offensive and defensive line players maintain a coherent line shape without excessive gaps.
- **Reality_Anchor**: A mechanism in the opportunity score formula that centers the score toward 0.5 when a branch's outcomes closely match the continuation window outcomes.
- **Branch_Window_Similarity**: A numeric measure of how closely a branch's trajectory and events match the continuation window, used by the Reality_Anchor to dampen opportunity scores toward 0.5.
- **Context_Aware_Speed_Threshold**: A speed limit that varies based on player position and game context (e.g., contact situations allow higher speeds than free-running).
- **Contact_Context**: A game situation where a player is being physically engaged by an opponent (e.g., sack, tackle, block), which can produce speeds exceeding normal sprint limits.
- **Gating_Module**: The module under `src/scoring/gating.py` responsible for binary pass/fail checks that hard-reject branches before scoring.
- **Aggregate_Module**: The module under `src/scoring/aggregate.py` responsible for combining sub-scores into final validity and opportunity scores.
- **Opportunity_Score**: A normalized 0–1 score representing the tactical value of a branch relative to the continuation window.
- **Benchmark**: The set of 15 manually-classified branches in `data/benchmark_input.json` with expected ranges in `data/benchmark_annotated.json`.
- **Evaluation_Report**: The complete JSON-serializable output for a single branch.
- **Sub_Metric**: A named, numeric component of an aggregate score that traces how the aggregate was derived.

## Requirements

### Requirement 1: Tactical Consistency v2 — Compactness and Density Model

**User Story:** As a football analyst, I want the tactical consistency module to evaluate team compactness, defensive density, and line integrity, so that branches with valid role zones but tactically incoherent formations score lower on tactical consistency.

#### Acceptance Criteria

1. THE Tactical_Consistency_Module SHALL compute a Compactness_Score normalized to the 0–1 range, measuring how tight or spread the team formation is at each timestamp snapshot.
2. THE Tactical_Consistency_Module SHALL compute a Defensive_Density_Score normalized to the 0–1 range, measuring the concentration of defensive players around key offensive players (ball carrier or QB).
3. THE Tactical_Consistency_Module SHALL compute a Line_Integrity_Score normalized to the 0–1 range, measuring whether offensive line and defensive line players maintain a coherent line shape without excessive gaps.
4. THE Tactical_Consistency_Module SHALL incorporate the Compactness_Score, Defensive_Density_Score, and Line_Integrity_Score into the aggregate consistency_score alongside the existing role_consistency_score and formation_coherence_score.
5. WHEN a branch has all players in valid role zones but the overall formation shape is tactically incoherent (e.g., excessive spread for a run play, no defensive density around the ball carrier), THE Tactical_Consistency_Module SHALL assign a consistency_score below 0.7.
6. THE Tactical_Consistency_Module SHALL expose the Compactness_Score, Defensive_Density_Score, and Line_Integrity_Score as named Sub_Metrics in the TacticalConsistencyResult dataclass.
7. THE Tactical_Consistency_Module SHALL define all compactness, density, and line integrity threshold constants as named constants in `src/utils/constants.py`.

### Requirement 2: Opportunity Score Reality Anchor

**User Story:** As a football analyst, I want branches that mirror reality to score opportunity near 0.5, so that neutral branches are not inflated by a permissive tactical consistency score.

#### Acceptance Criteria

1. THE Aggregate_Module SHALL compute a Branch_Window_Similarity measure comparing the branch's trajectory and events against the continuation window outcomes.
2. WHEN the Branch_Window_Similarity exceeds a configured threshold (indicating the branch closely mirrors reality), THE Aggregate_Module SHALL dampen the opportunity score toward 0.5 proportionally to the similarity.
3. WHEN a branch produces outcomes nearly identical to the continuation window, THE Aggregate_Module SHALL assign an opportunity score within the range [0.4, 0.6].
4. WHEN a branch produces outcomes clearly better than the continuation window, THE Reality_Anchor SHALL not suppress the opportunity score below 0.6.
5. WHEN a branch produces outcomes clearly worse than the continuation window, THE Reality_Anchor SHALL not inflate the opportunity score above 0.4.
6. THE Aggregate_Module SHALL expose the Branch_Window_Similarity as a named Sub_Metric in the EvaluationReport.
7. THE Aggregate_Module SHALL define the similarity threshold and dampening parameters as named constants in `src/utils/constants.py`.

### Requirement 3: Context-Aware Speed Thresholds

**User Story:** As a football analyst, I want the gating module to use context-aware speed limits, so that physically plausible contact-driven movements (e.g., a QB being sacked at 25 yd/s) are not incorrectly rejected.

#### Acceptance Criteria

1. THE Gating_Module SHALL support position-aware speed thresholds that vary by player role (e.g., QB, RB, WR, OL, DL).
2. THE Gating_Module SHALL support context-aware speed thresholds that allow higher speeds during Contact_Context situations (e.g., sack, tackle events within a configurable time window of the speed measurement).
3. WHEN a player's speed exceeds the base sprint threshold but a Contact_Context event is present within the configurable time window, THE Gating_Module SHALL apply the elevated contact speed threshold instead of the base threshold.
4. WHEN a player's speed exceeds both the base sprint threshold and the contact speed threshold, THE Gating_Module SHALL reject the branch with the max_speed flag set to false.
5. THE Gating_Module SHALL define the base speed threshold, contact speed threshold, contact time window, and any position-specific overrides as named constants in `src/utils/constants.py`.
6. THE Gating_Module SHALL include the applied threshold and context in the Explanation when rejecting a branch for excessive speed.

### Requirement 4: Sub-Metric Expansion for Traceability

**User Story:** As a sports AI engineer, I want the evaluation report to include the new sub-metrics from v3 modules, so that every aggregate score remains fully traceable.

#### Acceptance Criteria

1. THE SubMetrics dataclass in `src/models/evaluation_report.py` SHALL include new fields for compactness_score, defensive_density_score, line_integrity_score, and branch_window_similarity.
2. THE Aggregate_Module SHALL populate all new Sub_Metric fields in the EvaluationReport when computing the aggregate.
3. THE Evaluator SHALL preserve all existing Sub_Metric fields in the EvaluationReport. No existing fields shall be renamed or removed.
4. FOR ALL valid EvaluationReports produced by the v3 Evaluator, serializing to JSON then deserializing back SHALL produce an equivalent EvaluationReport (round-trip property).
5. THE new Sub_Metric fields SHALL each be a float normalized to the 0–1 range.

### Requirement 5: Benchmark Regression Target

**User Story:** As a sports AI engineer, I want the v3 evaluator to pass all 15 benchmark branches within their expected ranges, so that the calibration improvements are validated against known ground truth.

#### Acceptance Criteria

1. WHEN the v3 Evaluator processes branch B13 (worse-big-loss, sack at high speed), THE Evaluator SHALL pass gating and assign an opportunity score within [0.0, 0.3].
2. WHEN the v3 Evaluator processes branch B14 (neutral-same-as-reality), THE Evaluator SHALL assign an opportunity score within [0.4, 0.6].
3. WHEN the v3 Evaluator processes branch B15 (neutral-lateral-move), THE Evaluator SHALL assign an opportunity score within [0.4, 0.6].
4. WHEN the v3 Evaluator processes all 15 benchmark branches, THE Evaluator SHALL produce results where every branch's validity_score and opportunity_score fall within the expected ranges defined in `data/benchmark_annotated.json`.
5. THE test suite SHALL include a regression test that runs all 15 benchmark branches through the v3 Evaluator and verifies each branch against its annotated expected ranges.
6. THE test suite SHALL include a regression test that verifies the 12 branches that already passed in v2 continue to pass in v3 (no regressions).

### Requirement 6: Architectural Preservation

**User Story:** As a sports AI engineer, I want the v3 changes to preserve the existing modular architecture, so that scoring modules remain independently testable and composable.

#### Acceptance Criteria

1. THE Tactical_Consistency_Module SHALL not import from any other scoring module under `src/scoring/`.
2. THE Gating_Module SHALL not import from any other scoring module under `src/scoring/`.
3. THE Aggregate_Module SHALL receive all upstream results via its AggregateInput dataclass and not call scoring modules directly.
4. THE v3 Evaluator SHALL maintain the strict pipeline ordering: gating, then validity scoring, then opportunity scoring.
5. THE v3 Evaluator SHALL ensure that a gating failure still results in validity_score=0.0 and opportunity_score=0.0 with no downstream scoring.
6. THE v3 Evaluator SHALL ensure that all scores and sub-metrics remain normalized to the [0, 1] range.
7. THE v3 Evaluator SHALL ensure all EvaluationReport fields remain JSON-serializable using Python's built-in `json` module.

### Requirement 7: Tactical Consistency Parsing and Round-Trip

**User Story:** As a sports AI engineer, I want the TacticalConsistencyResult to be serializable and deserializable, so that I can persist and reload tactical scoring results.

#### Acceptance Criteria

1. THE TacticalConsistencyResult dataclass SHALL be convertible to a JSON-serializable dict via `dataclasses.asdict()`.
2. FOR ALL valid TacticalConsistencyResult instances, converting to dict then reconstructing from dict SHALL produce an equivalent TacticalConsistencyResult (round-trip property).
3. THE TacticalConsistencyResult SHALL include all new sub-metric fields (compactness_score, defensive_density_score, line_integrity_score) alongside the existing fields.
