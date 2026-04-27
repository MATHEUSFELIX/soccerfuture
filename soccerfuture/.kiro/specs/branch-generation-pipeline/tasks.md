# Implementation Plan: Branch Generation Pipeline

## Overview

Build the end-to-end branch generation pipeline in strict dependency order: constants → models → generator → pipeline orchestrator → CLI → demo data → tests. Each module builds on the previous, with checkpoints after each major component to validate incrementally. The pipeline wires the new branch generator to the existing v3 simulation evaluator, producing ranked reports from play state inputs.

## Tasks

- [x] 1. Add generation constants to `src/utils/constants.py`
  - Append the branch generation constants block: `GENERATION_TIMESTEP`, `SPEED_SAFETY_FACTOR`, `MAX_ROUTE_ANGLE_DELTA`, `MIN_SPEED_FACTOR`, `MAX_SPEED_FACTOR`, `GENERATION_SNAPSHOTS_MIN`, `GENERATION_SNAPSHOTS_MAX`, `DEFAULT_N`, `DEFAULT_K`, `DEFAULT_SEED`, `DEFAULT_VALIDITY_WEIGHT`, `DEFAULT_OPPORTUNITY_WEIGHT`
  - All constants must have descriptive names and docstring-level comments
  - _Requirements: 3.4, 3.5, 5.4_

- [x] 2. Implement PlayState model and serialization helpers
  - [x] 2.1 Create `src/models/play_state.py` with the `PlayState` dataclass
    - Fields: `field_position` (float), `down` (int), `distance` (float), `score_differential` (int), `game_clock` (float), `player_positions` (list[PlayerPosition]), `decision_point_timestamp` (float), `player_roles` (dict), `metadata` (dict)
    - Import `PlayerPosition` from `src/models/branch.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [x] 2.2 Implement `play_state_to_dict` and `dict_to_play_state` serialization helpers in the same file
    - `play_state_to_dict` uses `dataclasses.asdict()`
    - `dict_to_play_state` reconstructs nested `PlayerPosition` objects from dicts
    - `dict_to_play_state` raises `KeyError` with descriptive message on missing required fields
    - _Requirements: 1.5, 1.6, 12.1, 12.2, 12.3, 12.4_
  - [x] 2.3 Write unit tests for PlayState model in `tests/models/test_play_state.py`
    - Test construction with all fields, default metadata, `play_state_to_dict` output keys, `dict_to_play_state` round-trip, rejection of missing fields
    - _Requirements: 1.1, 1.5, 12.1, 12.2_
  - [x] 2.4 Write property test for PlayState round-trip serialization in `tests/models/test_play_state_properties.py`
    - **Property 1: PlayState round-trip serialization**
    - **Validates: Requirements 1.5, 1.6, 12.1, 12.3, 12.4**
  - [x] 2.5 Write property test for PlayState parser rejection in `tests/models/test_play_state_properties.py`
    - **Property 16: PlayState parser rejects invalid dicts with descriptive errors**
    - **Validates: Requirements 12.2**

- [x] 3. Checkpoint — Verify PlayState model
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement PipelineReport model
  - [x] 4.1 Create `src/models/pipeline_report.py` with `RankedBranch` and `PipelineReport` dataclasses
    - `RankedBranch`: `branch_id` (str), `composite_score` (float), `evaluation_report` (dict), `branch` (dict)
    - `PipelineReport`: `play_state` (dict), `evaluated_branches` (list[dict]), `ranked_branches` (list[RankedBranch]), `metadata` (dict), `errors` (list[str])
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.7_
  - [x] 4.2 Implement `to_dict` and `from_dict` methods on `PipelineReport`
    - `to_dict` converts the entire report to a JSON-serializable dict including nested `RankedBranch` objects
    - `from_dict` reconstructs `PipelineReport` with nested `RankedBranch` instances from a plain dict
    - _Requirements: 8.5, 8.6_
  - [x] 4.3 Write unit tests for PipelineReport model in `tests/models/test_pipeline_report.py`
    - Test construction, `to_dict` produces JSON-serializable output, `from_dict` round-trip, default empty errors list
    - _Requirements: 8.1, 8.5, 8.7_
  - [x] 4.4 Write property test for PipelineReport round-trip serialization in `tests/models/test_pipeline_report_properties.py`
    - **Property 15: PipelineReport round-trip serialization**
    - **Validates: Requirements 8.5, 8.6**

- [x] 5. Checkpoint — Verify models
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Branch Generator
  - [x] 6.1 Create `src/generation/__init__.py` package init
    - Empty init or re-export `generate_branches` and `GenerationResult`
    - _Requirements: 2.1_
  - [x] 6.2 Implement `GenerationResult` dataclass and `generate_branches` function in `src/generation/branch_generator.py`
    - `GenerationResult`: `branches` (list[dict]), `continuation_window` (dict), `strategy_counts` (dict[str, int])
    - `generate_branches(play_state, n=20, seed=42)` using a local `random.Random(seed)` instance — no global state
    - Validate N is in [10, 30], raise `ValueError` otherwise
    - Assign sequential branch_ids: "gen-001", "gen-002", etc.
    - Set each branch's `decision_point_timestamp` to match PlayState
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6_
  - [x] 6.3 Implement three perturbation strategies in `src/generation/branch_generator.py`
    - **Route variation**: Rotate position deltas by random angle within `MAX_ROUTE_ANGLE_DELTA`, generate 3–5 snapshots per player at `GENERATION_TIMESTEP` intervals, cap speeds at `MAX_HUMAN_SPRINT_SPEED * SPEED_SAFETY_FACTOR`
    - **Speed variation**: Scale player speeds by random factor in `[MIN_SPEED_FACTOR, MAX_SPEED_FACTOR]`, clamp to safe speed limit
    - **Decision variation**: Alter event sequences (e.g., pass vs. run), adjust positions to match altered events
    - Distribute strategies round-robin across N branches
    - Clamp all positions to field boundaries, ensure timestamps ordered with gaps ≤ `MAX_TIMESTAMP_GAP`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x] 6.4 Implement `synthesize_continuation_window` function in `src/generation/branch_generator.py`
    - Produce a single ContinuationWindow dict from PlayState with matching `decision_point_timestamp`
    - Include at least one outcome with positions, `yard_gain`, `turnover` (False), `scoring_play` (False)
    - Project player positions forward 2–3 timesteps with small random deltas
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 6.5 Write unit tests for Branch Generator in `tests/generation/test_branch_generator.py`
    - Create `tests/generation/__init__.py`
    - Test: exactly N branches generated, deterministic with same seed, different seeds differ, sequential branch_ids, required fields present, timestamps ordered, speeds within limits for majority, ContinuationWindow well-formed, ValueError for N outside [10, 30]
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3_
  - [x] 6.6 Write property tests for Branch Generator in `tests/generation/test_branch_generator_properties.py`
    - Add `play_state_strategy` to `tests/strategies.py` (or `tests/generation/strategies.py`) for generating valid PlayState instances
    - **Property 2: Generator produces exactly N branches** — Validates: Requirements 2.1
    - **Property 3: Deterministic generation with same seed** — Validates: Requirements 2.3
    - **Property 4: Different seeds produce different output** — Validates: Requirements 2.4
    - **Property 5: Unique sequential branch IDs** — Validates: Requirements 2.5
    - **Property 6: Decision point timestamps match PlayState** — Validates: Requirements 2.6, 4.2
    - **Property 7: At least three perturbation strategies used** — Validates: Requirements 3.1, 3.2
    - **Property 8: Generated branches conform to Branch structure** — Validates: Requirements 3.3
    - **Property 9: Generated timestamps are ordered with valid gaps** — Validates: Requirements 3.4
    - **Property 10: At least 70% gating-compliant speeds** — Validates: Requirements 3.5
    - **Property 11: Synthesized ContinuationWindow is well-formed** — Validates: Requirements 4.1, 4.3, 4.4

- [x] 7. Checkpoint — Verify Branch Generator
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Pipeline Orchestrator
  - [x] 8.1 Create `src/pipeline.py` with `PipelineConfig` dataclass and `run_pipeline` function
    - `PipelineConfig`: `n` (default 20), `k` (default 5), `seed` (default 42), `validity_weight` (default 0.5), `opportunity_weight` (default 0.5)
    - `run_pipeline(play_state, config=None)` → `PipelineReport`
    - Wire: generate branches → evaluate each via `evaluate_branch` → compute composite scores → rank → filter top K → assemble report
    - Record `execution_time_seconds` in metadata
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 9.1, 9.2_
  - [x] 8.2 Implement `compute_composite_score` function in `src/pipeline.py`
    - `composite = validity_weight * validity_score + opportunity_weight * opportunity_score`
    - _Requirements: 6.1_
  - [x] 8.3 Implement ranking and filtering logic in `src/pipeline.py`
    - Sort by composite score descending, tiebreak by branch_id lexicographic ascending
    - Select top K branches that passed gating
    - If fewer than K passed gating, return only those that passed (no padding)
    - _Requirements: 6.2, 6.3, 6.4, 6.5_
  - [x] 8.4 Implement error handling in `src/pipeline.py`
    - Catch exceptions from individual branch evaluations: skip branch, log error in `PipelineReport.errors`
    - Handle all-branches-fail: return report with empty ranked list and explanatory metadata
    - Handle generator exception: return error PipelineReport with message
    - Wrap entire `run_pipeline` in try/except so it never raises to caller
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - [x] 8.5 Write unit tests for Pipeline Orchestrator in `tests/test_pipeline.py`
    - Test: end-to-end with a simple PlayState, default config applied, composite score correctness, ranking order, tiebreaker, single branch failure handling, all branches fail, generator failure, never raises
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4_
  - [x] 8.6 Write property tests for Pipeline Orchestrator in `tests/test_pipeline_properties.py`
    - **Property 12: Composite score equals weighted sum** — Validates: Requirements 6.1
    - **Property 13: Ranking is descending by composite score with branch_id tiebreaker** — Validates: Requirements 6.2, 6.3
    - **Property 14: Pipeline never raises unhandled exceptions** — Validates: Requirements 7.4

- [x] 9. Checkpoint — Verify Pipeline Orchestrator
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement CLI entry point
  - [x] 10.1 Create `src/cli.py` with `main()` function using `argparse`
    - Positional argument: `play_state_path` (path to PlayState JSON file)
    - Optional arguments: `--n`, `--k`, `--seed`, `--validity-weight`, `--opportunity-weight`, `--output`
    - Load JSON file, parse into PlayState via `dict_to_play_state`, construct `PipelineConfig`, call `run_pipeline`
    - Write `PipelineReport.to_dict()` as formatted JSON to stdout (or `--output` file)
    - On errors (file not found, invalid JSON, invalid PlayState): print descriptive message to stderr, exit code 1
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  - [x] 10.2 Write unit tests for CLI in `tests/test_cli.py`
    - Test: valid file produces JSON output, missing file error, malformed JSON error, optional arguments accepted, `--output` writes to file
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 11. Checkpoint — Verify CLI
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Create demo play state JSON files
  - [x] 12.1 Create `data/play_states/first_and_ten_midfield.json`
    - 1st-and-10 at the 50-yard line, balanced situation, at least 5 player positions within field boundaries, appropriate roles, moderate game clock
    - _Requirements: 11.1, 11.2, 11.3_
  - [x] 12.2 Create `data/play_states/third_and_short_goal_line.json`
    - 3rd-and-2 at the opponent's 5-yard line, goal-line scenario with compressed field space, at least 5 player positions
    - _Requirements: 11.1, 11.2, 11.3_
  - [x] 12.3 Create `data/play_states/second_and_long_after_sack.json`
    - 2nd-and-15 at own 20 after a sack, long-yardage recovery scenario, at least 5 player positions
    - _Requirements: 11.1, 11.2, 11.3_
  - [x] 12.4 Write integration tests for demo play states in `tests/test_demo_play_states.py`
    - Each demo file loads successfully, each has ≥ 5 positions, each produces a valid PipelineReport when run through the pipeline
    - _Requirements: 11.4_

- [x] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major module
- Property tests validate the 16 correctness properties defined in the design document
- Unit tests validate specific examples and edge cases
- The build order (constants → models → generator → pipeline → CLI → demo data) ensures no forward dependencies
