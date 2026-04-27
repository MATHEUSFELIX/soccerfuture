# Requirements Document

## Introduction

This feature connects the existing v3 simulation evaluator with a new branch generation system to form an end-to-end pipeline. The pipeline takes an initial play state (a snapshot of a football game situation), generates 10–30 alternative branches from that state using rule-based perturbation strategies, evaluates each branch through the v3 evaluator, ranks branches by a composite score combining validity and opportunity, keeps the top K branches, and exports a structured JSON report. This is Sprint 1 of the integration effort — the first time the system operates as a real pipeline rather than isolated module tests.

## Glossary

- **Play_State**: A snapshot of a football game situation at a decision point, including field position, down, distance, score differential, game clock, and player positions. This is the input to the Branch_Generator.
- **Branch_Generator**: The module that takes a Play_State and produces N alternative Branch objects using rule-based perturbation strategies with seeded randomness.
- **Pipeline_Orchestrator**: The top-level module that coordinates branch generation, evaluation, ranking, filtering, and report assembly.
- **Pipeline_Report**: The structured JSON output containing the Play_State, all generated branches with evaluation reports, the top K ranked branches, and generation metadata.
- **Perturbation_Strategy**: A rule-based method for varying player routes, speeds, or decisions from a base Play_State to produce a distinct Branch.
- **Composite_Score**: A weighted combination of validity_score and opportunity_score used to rank branches. Default weights are configurable.
- **Continuation_Window**: The real-world outcome data derived from the Play_State that branches are evaluated against (existing model).
- **Branch**: A simulated continuation of a play from a decision point, containing player positions, events, roles, and metadata (existing model).
- **Evaluator**: The v3 simulation evaluator that scores branches on validity and opportunity (existing module at `src/simulation_evaluator_v2.py`).
- **Seed**: An integer value that initializes the random number generator to produce deterministic, reproducible branch generation results.

## Requirements

### Requirement 1: Play State Model

**User Story:** As a pipeline user, I want to define a game situation as a structured Play_State, so that the Branch_Generator has a well-defined input to generate branches from.

#### Acceptance Criteria

1. THE Play_State SHALL contain the following fields: field_position (float, yards from own end zone), down (int, 1–4), distance (float, yards to first down), score_differential (int, own score minus opponent score), game_clock (float, seconds remaining), and player_positions (list of PlayerPosition objects at the decision point).
2. THE Play_State SHALL contain a decision_point_timestamp (float, seconds from play start) that anchors the moment of divergence.
3. THE Play_State SHALL contain a player_roles mapping (dict of player_id to role string) consistent with the existing Branch model's player_roles field.
4. THE Play_State SHALL contain an optional metadata dict for additional context (e.g., formation name, weather).
5. THE Play_State SHALL be JSON-serializable via `dataclasses.asdict()` and reconstructable from a JSON-deserialized dict.
6. FOR ALL valid Play_State objects, serializing to JSON via `json.dumps(asdict(ps))` then deserializing via `json.loads` and reconstructing SHALL produce an equivalent Play_State (round-trip property).

### Requirement 2: Branch Generator — Core Generation

**User Story:** As a pipeline user, I want the Branch_Generator to produce N alternative branches from a Play_State, so that I can explore different play outcomes.

#### Acceptance Criteria

1. WHEN a valid Play_State and a count N (10 ≤ N ≤ 30) are provided, THE Branch_Generator SHALL produce exactly N Branch objects.
2. THE Branch_Generator SHALL accept a seed parameter (int) that initializes the random number generator.
3. WHEN the same Play_State, N, and seed are provided, THE Branch_Generator SHALL produce identical Branch objects (deterministic output).
4. WHEN different seeds are provided for the same Play_State and N, THE Branch_Generator SHALL produce at least one differing Branch across the two result sets.
5. THE Branch_Generator SHALL assign each generated Branch a unique branch_id containing a sequential index (e.g., "gen-001", "gen-002").
6. THE Branch_Generator SHALL set each generated Branch's decision_point_timestamp to match the Play_State's decision_point_timestamp.

### Requirement 3: Branch Generator — Perturbation Strategies

**User Story:** As a pipeline user, I want generated branches to represent diverse play alternatives, so that the pipeline explores a meaningful range of outcomes.

#### Acceptance Criteria

1. THE Branch_Generator SHALL apply at least three distinct Perturbation_Strategy types: route variation (changing player movement directions), speed variation (adjusting player speeds within physical limits), and decision variation (altering event sequences such as pass vs. run).
2. WHEN generating N branches, THE Branch_Generator SHALL use a mix of Perturbation_Strategy types across the set, not a single strategy for all branches.
3. THE Branch_Generator SHALL populate each generated Branch with positions, events, player_roles, and metadata fields conforming to the existing Branch dataclass structure.
4. THE Branch_Generator SHALL generate player positions with timestamps ordered chronologically and with gaps not exceeding MAX_TIMESTAMP_GAP (0.5 seconds).
5. THE Branch_Generator SHALL generate at least 70% of branches with all player speeds at or below MAX_HUMAN_SPRINT_SPEED (12.0 yards/second), ensuring the majority pass the Evaluator's gating checks.

### Requirement 4: Branch Generator — Continuation Window Synthesis

**User Story:** As a pipeline user, I want the Branch_Generator to produce a Continuation_Window from the Play_State, so that the Evaluator has a baseline for comparison.

#### Acceptance Criteria

1. WHEN a valid Play_State is provided, THE Branch_Generator SHALL produce a single ContinuationWindow object representing the "what actually happened" baseline.
2. THE synthesized ContinuationWindow SHALL have its decision_point_timestamp matching the Play_State's decision_point_timestamp.
3. THE synthesized ContinuationWindow SHALL contain at least one outcome with positions derived from the Play_State's player_positions and plausible yard_gain, turnover, and scoring_play fields.
4. THE synthesized ContinuationWindow SHALL conform to the existing ContinuationWindow dataclass structure.

### Requirement 5: Pipeline Orchestrator — End-to-End Flow

**User Story:** As a pipeline user, I want a single entry point that takes a Play_State and returns a ranked report, so that I do not need to manually wire generation and evaluation together.

#### Acceptance Criteria

1. WHEN a valid Play_State is provided, THE Pipeline_Orchestrator SHALL call the Branch_Generator to produce N branches and a ContinuationWindow.
2. WHEN branches and a ContinuationWindow are produced, THE Pipeline_Orchestrator SHALL call the Evaluator's evaluate_branch function on each branch paired with the ContinuationWindow.
3. THE Pipeline_Orchestrator SHALL accept a configuration object specifying N (number of branches to generate), K (number of top branches to keep), seed (RNG seed), and composite score weights (validity_weight, opportunity_weight).
4. THE Pipeline_Orchestrator SHALL use default values of N=20, K=5, seed=42, validity_weight=0.5, opportunity_weight=0.5 when no configuration is provided.

### Requirement 6: Pipeline Orchestrator — Ranking and Filtering

**User Story:** As a pipeline user, I want branches ranked by a composite score and filtered to the top K, so that I see only the most promising alternatives.

#### Acceptance Criteria

1. THE Pipeline_Orchestrator SHALL compute a Composite_Score for each branch as `validity_weight * validity_score + opportunity_weight * opportunity_score`.
2. THE Pipeline_Orchestrator SHALL rank all evaluated branches by Composite_Score in descending order.
3. WHEN two branches have equal Composite_Scores, THE Pipeline_Orchestrator SHALL use branch_id as a tiebreaker (lexicographic ascending).
4. THE Pipeline_Orchestrator SHALL select the top K branches from the ranked list.
5. WHEN fewer than K branches pass gating, THE Pipeline_Orchestrator SHALL return only the branches that passed gating, without padding.

### Requirement 7: Pipeline Orchestrator — Error Handling

**User Story:** As a pipeline user, I want the pipeline to handle failures gracefully, so that a single bad branch does not crash the entire run.

#### Acceptance Criteria

1. IF the Branch_Generator produces a branch that causes the Evaluator to raise an exception, THEN THE Pipeline_Orchestrator SHALL skip that branch, log the error in the Pipeline_Report's metadata, and continue evaluating remaining branches.
2. IF all generated branches fail evaluation, THEN THE Pipeline_Orchestrator SHALL return a Pipeline_Report with an empty ranked list and an explanatory message in metadata.
3. IF the Branch_Generator itself raises an exception, THEN THE Pipeline_Orchestrator SHALL return a Pipeline_Report with an error message and no branches.
4. THE Pipeline_Orchestrator SHALL never raise an unhandled exception to the caller.

### Requirement 8: Pipeline Report Model

**User Story:** As a pipeline user, I want a structured report containing all pipeline outputs, so that I can inspect generation results, evaluation scores, and rankings in one place.

#### Acceptance Criteria

1. THE Pipeline_Report SHALL contain the input Play_State.
2. THE Pipeline_Report SHALL contain a list of all generated branches paired with their EvaluationReport objects.
3. THE Pipeline_Report SHALL contain a ranked list of the top K branches with their Composite_Scores.
4. THE Pipeline_Report SHALL contain generation metadata: seed used, N generated, K requested, number of branches that passed gating, and total pipeline execution time in seconds.
5. THE Pipeline_Report SHALL be JSON-serializable via a `to_dict` method, and `json.dumps` on the result SHALL succeed without error.
6. FOR ALL valid Pipeline_Report objects, serializing to JSON then deserializing and reconstructing SHALL produce an equivalent Pipeline_Report (round-trip property).
7. THE Pipeline_Report SHALL contain an errors list capturing any branch-level or generator-level failures encountered during the run.

### Requirement 9: Pipeline Performance

**User Story:** As a pipeline user, I want the pipeline to complete quickly, so that I can iterate on play analysis without long waits.

#### Acceptance Criteria

1. WHEN N=20 branches are generated and evaluated, THE Pipeline_Orchestrator SHALL complete the full pipeline (generation + evaluation + ranking + report assembly) in less than 10 seconds on a standard development machine.
2. THE Pipeline_Orchestrator SHALL record the total execution time in the Pipeline_Report metadata.

### Requirement 10: CLI Entry Point

**User Story:** As a developer, I want a command-line interface to run the pipeline on a play state JSON file, so that I can test and demo the system without writing code.

#### Acceptance Criteria

1. WHEN a play state JSON file path is provided as a command-line argument, THE CLI SHALL load the file, parse it into a Play_State, and run the Pipeline_Orchestrator.
2. WHEN the pipeline completes, THE CLI SHALL write the Pipeline_Report as formatted JSON to stdout.
3. IF the play state JSON file is missing or malformed, THEN THE CLI SHALL print a descriptive error message to stderr and exit with a non-zero exit code.
4. THE CLI SHALL accept optional arguments for N, K, seed, validity_weight, and opportunity_weight to override pipeline defaults.
5. THE CLI SHALL accept an optional `--output` argument to write the report to a file instead of stdout.

### Requirement 11: Demo Play States

**User Story:** As a developer, I want realistic sample play state files, so that I can test and demo the pipeline without creating test data manually.

#### Acceptance Criteria

1. THE project SHALL include at least 3 demo play state JSON files under `data/play_states/`.
2. THE demo play states SHALL cover distinct game scenarios: a 1st-and-10 at midfield, a 3rd-and-short near the goal line, and a 2nd-and-long after a sack.
3. EACH demo play state SHALL contain at least 5 player positions with valid coordinates within field boundaries.
4. EACH demo play state SHALL be loadable by the CLI and produce a valid Pipeline_Report when run through the pipeline.

### Requirement 12: Parse and Print Play State JSON

**User Story:** As a developer, I want to parse play state JSON files into Play_State objects and print Play_State objects back to JSON, so that I can reliably load and save pipeline inputs.

#### Acceptance Criteria

1. WHEN a valid JSON dict is provided, THE Play_State parser SHALL construct a Play_State object with all fields populated.
2. WHEN an invalid JSON dict is provided (missing required fields), THE Play_State parser SHALL raise a descriptive error identifying the missing fields.
3. THE Play_State printer SHALL convert a Play_State object to a JSON-serializable dict preserving all fields.
4. FOR ALL valid Play_State objects, parsing the printed output SHALL produce an equivalent Play_State (round-trip property).
