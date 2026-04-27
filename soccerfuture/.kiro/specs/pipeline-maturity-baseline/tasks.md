# Implementation Plan: Pipeline Maturity Baseline

## Overview

Transition the branch generation pipeline from "build" mode to "prove utility and control drift" mode by adding a frozen benchmark manifest, semantic regression tests, generator diversity analysis, per-execution telemetry, and branch-level explainability. Implementation follows the dependency order: manifest loader → telemetry → explainability → pipeline modifications → scripts → generated data → tests.

## Tasks

- [x] 1. Implement Manifest Loader — `src/utils/manifest.py`
  - [x] 1.1 Create `src/utils/manifest.py` with `load_manifest`, `validate_manifest`, `manifest_to_dict`, and `save_manifest` functions
    - `load_manifest(path)` reads JSON, calls `validate_manifest`, returns validated dict
    - `validate_manifest(data)` checks required top-level keys (`version`, `pipeline_config`, `scenarios`), required per-scenario keys (`scenario_file`, `gating_pass_count`, `top_branch_min_score`, `bottom_branch_max_score`, `strategy_counts`, `expected_top_k`), and required `pipeline_config` keys (`n`, `k`, `seed`, `validity_weight`, `opportunity_weight`); raises `ValueError` with descriptive message on failure
    - `manifest_to_dict(manifest)` returns JSON-serializable dict (identity for well-formed manifests)
    - `save_manifest(manifest, path)` writes JSON with 2-space indentation
    - Raises `FileNotFoundError` for missing files, `json.JSONDecodeError` for invalid JSON
    - _Requirements: 13.1, 13.2, 13.3_

  - [x] 1.2 Write unit tests for manifest loader — `tests/utils/test_manifest.py`
    - Test `load_manifest` on valid file returns dict with required keys
    - Test `validate_manifest` raises `ValueError` on missing top-level keys
    - Test `validate_manifest` raises `ValueError` on missing scenario keys
    - Test `validate_manifest` raises `ValueError` on missing pipeline_config keys
    - Test `save_manifest` writes valid JSON readable by `load_manifest`
    - Test `load_manifest` raises `FileNotFoundError` on missing file
    - Test `load_manifest` raises `json.JSONDecodeError` on invalid JSON
    - _Requirements: 13.1, 13.2, 13.3_

  - [x] 1.3 Write property test: Manifest round-trip serialization
    - **Property 1: Benchmark manifest round-trip serialization**
    - Add `manifest_strategy()` to `tests/strategies.py` generating valid manifest dicts
    - For any valid manifest, `save_manifest` → `load_manifest` round-trip produces equivalent dict
    - **Validates: Requirements 13.1, 13.3, 13.4**

  - [x] 1.4 Write property test: Invalid manifest raises descriptive error
    - **Property 2: Invalid manifest raises descriptive error**
    - For any dict missing required top-level keys, `validate_manifest` raises `ValueError` identifying the missing key
    - **Validates: Requirements 13.2**

- [x] 2. Implement Telemetry Collector — `src/telemetry.py`
  - [x] 2.1 Create `src/telemetry.py` with `TelemetryCollector` dataclass
    - Fields: `branches_generated`, `hard_fail_count`, `score_filtered_count`, `avg_score_by_strategy`, `scenario_id`, `stage_timings`
    - `start_stage(stage_name)` records start time; `end_stage(stage_name)` computes elapsed seconds
    - `record_branch_result(strategy, composite_score, passed_gating, passed_validity)` updates counts and running averages
    - `to_dict()` returns JSON-serializable dict with keys: `branches_generated`, `hard_fail_count`, `score_filtered_count`, `avg_score_by_strategy`, `avg_score_by_scenario`, `time_per_stage`
    - Handle edge cases: `end_stage` without `start_stage` → 0.0; division by zero in averages → 0.0
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 2.2 Write unit tests for telemetry — `tests/test_telemetry.py`
    - Test stage timing records correct elapsed seconds
    - Test `record_branch_result` updates counts and averages correctly
    - Test `to_dict` produces JSON-serializable output with all required keys
    - Test `time_per_stage` contains `generation`, `evaluation`, `ranking` after recording
    - Test branch accounting invariant: `hard_fail_count + score_filtered_count + gating_pass_count == branches_generated`
    - Test edge case: `end_stage` without `start_stage` records 0.0
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 2.3 Write property test: Telemetry completeness
    - **Property 3: Telemetry completeness**
    - Add `telemetry_collector_strategy()` to `tests/strategies.py`
    - For any TelemetryCollector with recorded results, `to_dict()` contains all required keys and is JSON-serializable
    - **Validates: Requirements 7.1, 7.2, 7.4**

  - [x] 2.4 Write property test: Branch accounting invariant
    - **Property 4: Branch accounting invariant**
    - For any sequence of `record_branch_result` calls, `hard_fail_count + score_filtered_count + gating_pass_count == branches_generated`
    - **Validates: Requirements 7.3**

- [x] 3. Implement Explainability Module — `src/explainability.py`
  - [x] 3.1 Create `src/explainability.py` with `build_ranking_explanation` and `build_filter_reason` functions
    - Define `_SUB_METRIC_NAMES`, `_VALIDITY_METRICS`, `_OPPORTUNITY_METRICS`, `_PROMOTION_THRESHOLD`, `_PENALTY_THRESHOLD` constants
    - `build_ranking_explanation(evaluation_report, validity_threshold)` analyzes sub_metrics to produce `promoted_factors`, `penalized_factors`, `top_scoring_block`, `bottom_scoring_block`, and optional `near_threshold_warning`
    - When `validity_score > 0.7`, ensure highest plausibility/fidelity sub-metric in `promoted_factors` (Req 8.3)
    - When `opportunity_score < 0.4`, ensure lowest tactical/decision sub-metric in `penalized_factors` (Req 8.4)
    - When `validity_score` within 0.1 of threshold, add `near_threshold_warning` (Req 8.5)
    - `build_filter_reason(evaluation_report, passed_gating, validity_threshold)` returns "Rejected: " or "Filtered: " prefixed string
    - Graceful degradation: missing `sub_metrics` → empty factors, `"unknown"` blocks; missing `explanations` → generic reason
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2_

  - [x] 3.2 Write unit tests for explainability — `tests/test_explainability.py`
    - Test `build_ranking_explanation` produces all required keys
    - Test promoted_factors populated when sub-metrics above 0.6
    - Test penalized_factors populated when sub-metrics below 0.4
    - Test `near_threshold_warning` present when validity near threshold
    - Test high-validity branch (>0.7) references plausibility/fidelity in promoted_factors
    - Test low-opportunity branch (<0.4) references tactical/decision in penalized_factors
    - Test `build_filter_reason` returns "Rejected: " prefix for gating failures
    - Test `build_filter_reason` returns "Filtered: " prefix for validity failures
    - Test graceful handling of missing sub_metrics and explanations
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2_

  - [x] 3.3 Write property test: Ranking explanation structure
    - **Property 7: Ranking explanation structure**
    - Add `evaluation_report_dict_strategy()` to `tests/strategies.py`
    - For any evaluation report dict, `build_ranking_explanation` returns dict with `promoted_factors` (list), `penalized_factors` (list), `top_scoring_block` (str), `bottom_scoring_block` (str)
    - **Validates: Requirements 8.1, 8.2**

  - [x] 3.4 Write property test: High-validity promoted factors
    - **Property 8: High-validity branches reference plausibility/fidelity in promoted factors**
    - For any evaluation report with `validity_score > 0.7`, `promoted_factors` includes at least one plausibility/fidelity sub-metric
    - **Validates: Requirements 8.3**

  - [x] 3.5 Write property test: Low-opportunity penalized factors
    - **Property 9: Low-opportunity branches reference tactical/decision in penalized factors**
    - For any evaluation report with `opportunity_score < 0.4`, `penalized_factors` includes at least one tactical/decision sub-metric
    - **Validates: Requirements 8.4**

  - [x] 3.6 Write property test: Near-threshold warning
    - **Property 10: Near-threshold branches receive warning**
    - For any evaluation report where `validity_score` is within 0.1 of the validity threshold, `ranking_explanation` contains non-empty `near_threshold_warning`
    - **Validates: Requirements 8.5**

  - [x] 3.7 Write property test: Filter reason prefix correctness
    - **Property 11: Filter reason prefix correctness**
    - For any branch that failed gating, `build_filter_reason` returns string starting with "Rejected: "; for validity-filtered branches, starts with "Filtered: "
    - **Validates: Requirements 9.1, 9.2**

  - [x] 3.8 Write property test: Gating failure explanations non-empty
    - **Property 6: Gating failure explanations are non-empty**
    - For any evaluation report with `passed_gating=False`, the `explanations` list contains at least one non-empty string
    - **Validates: Requirements 5.3**

- [x] 4. Checkpoint — Manifest, Telemetry, and Explainability modules
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Modify Pipeline Orchestrator — `src/pipeline.py`
  - [x] 5.1 Wire telemetry into `run_pipeline`
    - Instantiate `TelemetryCollector` at start of execution
    - Wrap generation, evaluation, and ranking stages with `start_stage`/`end_stage` calls
    - Call `record_branch_result` after each branch evaluation with strategy, composite_score, passed_gating, passed_validity
    - Include `telemetry.to_dict()` in `PipelineReport.metadata["telemetry"]`
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 5.2 Wire explainability into `run_pipeline`
    - After ranking, call `build_ranking_explanation` for each branch in `ranked_branches` and attach as `ranking_explanation` in the evaluation_report dict
    - For each `evaluated_branches` entry not in top-K, call `build_filter_reason` and attach as `filter_reason`
    - Ensure `filter_reason` is only present on non-top-K branches (Req 9.3)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3_

  - [x] 5.3 Write integration tests for pipeline telemetry + explainability — `tests/test_pipeline_integration.py`
    - Test pipeline produces `metadata["telemetry"]` with all required keys
    - Test ranked branches have `ranking_explanation` dict with correct structure
    - Test filtered branches have `filter_reason` string with correct prefix
    - Test `filter_reason` absent on top-K branches
    - Test telemetry branch accounting invariant holds end-to-end
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 9.1, 9.2, 9.3_

  - [x] 5.4 Write property test: Top-K branch quality invariant
    - **Property 5: Top-K branch quality invariant**
    - For any pipeline execution producing ranked branches, every branch in `ranked_branches` has `passed_gating=True` and `validity_score >= validity_threshold`
    - **Validates: Requirements 5.1, 5.2**

  - [x] 5.5 Write property test: Filter reason exclusivity
    - **Property 12: Filter reason exclusivity**
    - For any pipeline execution, `filter_reason` is present only on `evaluated_branches` entries whose `branch_id` is not in `ranked_branches`
    - **Validates: Requirements 9.3**

- [x] 6. Checkpoint — Pipeline integration complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Baseline Generation Script — `scripts/generate_baseline.py`
  - [x] 7.1 Create `scripts/generate_baseline.py`
    - Run pipeline on all 3 demo scenarios (`first_and_ten_midfield`, `third_and_short_goal_line`, `second_and_long_after_sack`) with default config (N=20, K=5, seed=42)
    - Extract per-scenario entry: `scenario_file`, `gating_pass_count`, `top_branch_min_score`, `bottom_branch_max_score`, `strategy_counts`, `expected_top_k` (branch_ids and composite_scores)
    - Assemble manifest with `version: "v1.0-baseline"`, `pipeline_config` section, and `scenarios` list
    - Write to `data/benchmark_manifest.json` via `save_manifest`
    - Print summary to stdout: per-scenario gating count, top branch_id and score, strategy distribution
    - Exit code 0 on success, 1 on failure
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 11.1, 11.2, 11.3, 11.4_

- [x] 8. Implement Diversity Analysis Script — `scripts/analyze_diversity.py`
  - [x] 8.1 Create `scripts/analyze_diversity.py` with `compute_entropy`, `compute_strategy_dominance`, `analyze_scenario`, `print_report`, and `main` functions
    - `compute_entropy(counts)` computes Shannon entropy over strategy distribution
    - `compute_strategy_dominance(counts)` computes percentage of most dominant strategy
    - `analyze_scenario(scenario_file, report)` computes: unique passing count, strategy distribution, discard rate, entropy, strategy dominance, avg score by strategy
    - `print_report(analyses)` prints human-readable tables per scenario plus cross-scenario summary
    - Flag warning when strategy dominance exceeds 80%
    - Exit code 0 on success, 1 on failure
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 10.1, 10.2, 10.3, 10.4_

  - [x] 8.2 Write unit tests for diversity analysis pure functions — `tests/test_analyze_diversity.py`
    - Test `compute_entropy` returns 0 for single-category distribution
    - Test `compute_entropy` returns max entropy for uniform distribution
    - Test `compute_strategy_dominance` returns 100 for single-strategy
    - Test `compute_strategy_dominance` returns correct percentage for mixed distributions
    - _Requirements: 6.1, 6.2_

  - [x] 8.3 Write property test: Entropy and strategy dominance computation
    - **Property 13: Entropy and strategy dominance computation**
    - Add `strategy_counts_strategy()` to `tests/strategies.py`
    - For any non-empty distribution, `compute_entropy` returns non-negative value; `compute_strategy_dominance` returns value in [0, 100]; when single strategy > 80%, dominance > 80
    - **Validates: Requirements 6.2**

- [x] 9. Generate Benchmark Manifest Data
  - [x] 9.1 Run `scripts/generate_baseline.py` to produce `data/benchmark_manifest.json`
    - Verify the generated manifest conforms to the schema: `version`, `pipeline_config`, 3 scenario entries with all required keys
    - Verify the manifest loads successfully via `load_manifest`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1, 11.2_

- [x] 10. Checkpoint — Scripts and baseline data complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement Semantic Regression Tests — `tests/test_semantic_regression.py`
  - [x] 11.1 Create `tests/test_semantic_regression.py` with pytest fixtures and semantic tests
    - Module-scoped fixtures: `goal_line_report`, `sack_recovery_report`, `all_scenario_reports` — run pipeline once per scenario, reuse across tests
    - Goal-line tests (Req 3): `test_goal_line_no_long_routes_in_top_k` (no branch with majority of positions >15 yards downfield), `test_goal_line_has_decision_variation_in_top_k`, `test_goal_line_average_score_above_threshold` (>0.3)
    - Sack recovery tests (Req 4): `test_sack_recovery_has_route_variation_in_top_k`, `test_sack_recovery_no_stagnant_branches_in_top_k` (no branch with all positions within 2 yards of start), `test_sack_recovery_average_score_above_threshold` (>0.25)
    - Physical failure tests (Req 5): `test_all_scenarios_top_k_passed_gating`, `test_all_scenarios_top_k_validity_above_minimum` (>0.2), `test_all_scenarios_gating_failures_have_explanations`
    - Descriptive failure messages encoding tactical expectation and actual output
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 12.1, 12.2, 12.3, 12.4_

- [x] 12. Implement Baseline Regression Tests — `tests/test_baseline_regression.py`
  - [x] 12.1 Create `tests/test_baseline_regression.py` with manifest-based regression tests
    - Module-scoped fixtures: `manifest` (loads benchmark manifest), `scenario_reports` (runs pipeline per manifest scenario with manifest's config)
    - Parametrized tests per scenario: `test_gating_pass_count_within_tolerance` (±2), `test_top_branch_score_within_tolerance` (±0.05), `test_top_k_branch_ids_match_baseline` (exact match, same order)
    - Descriptive failure messages identifying scenario, expected value, actual value, and drifted metric
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 13. Final checkpoint — All tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major component group
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Build order follows dependencies: manifest loader → telemetry → explainability → pipeline modifications → scripts → generated data → tests
- All new modules use Python type hints, Google-style docstrings, and are JSON-serializable per tech.md conventions
