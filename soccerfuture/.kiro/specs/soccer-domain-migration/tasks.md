# Implementation Plan: Soccer Domain Migration

## Overview

Migrate the entire codebase from American football to soccer (association football) domain following a bottom-up strategy: constants → models → scoring modules → branch generator → viewer → demo scenarios → tests/strategies → steering docs. Each layer builds on the previous. The pipeline architecture remains unchanged — only terminology, constants, data models, and domain logic change.

## Tasks

- [x] 1. Migrate global constants (`src/utils/constants.py`)
  - Update `FIELD_LENGTH` from 100.0 to 105.0 (meters)
  - Update `FIELD_WIDTH` from 53.33 to 68.0 (meters)
  - Remove `END_ZONE_DEPTH`
  - Add soccer field area constants: `PENALTY_AREA_LENGTH = 16.5`, `PENALTY_AREA_WIDTH = 40.3`, `GOAL_AREA_LENGTH = 5.5`, `GOAL_AREA_WIDTH = 18.3`, `CENTER_CIRCLE_RADIUS = 9.15`, `CORNER_ARC_RADIUS = 1.0`
  - Update `MAX_HUMAN_SPRINT_SPEED` from 12.0 to 10.0 (m/s)
  - Update `MAX_ACCELERATION` from 8.0 to 7.0 (m/s²)
  - Update `MAX_DECELERATION` from 10.0 to 8.0 (m/s²)
  - Update `CONTACT_SPEED_THRESHOLD` from 25.0 to 15.0 (m/s)
  - Update `CONTACT_EVENT_TYPES` to `{"tackle", "foul", "dispossession"}`
  - Update `MAX_FORMATION_AREA` to `FIELD_WIDTH * 40.0` (2720.0 m²)
  - Replace all "yards" references in comments with "meters"
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 5.1, 5.2, 5.3, 4.3, 13.1, 13.2, 13.3_

- [x] 2. Migrate data models (`src/models/`)
  - [x] 2.1 Update PlayState (`src/models/play_state.py`)
    - Remove fields: `field_position`, `down`, `distance`
    - Add fields: `match_time` (float), `possession_team` (str), `ball_position` (dict), `game_phase` (str)
    - Keep fields: `score_differential`, `game_clock`, `player_positions`, `decision_point_timestamp`, `player_roles`, `metadata`
    - Update `play_state_to_dict` and `dict_to_play_state` for new fields
    - Update required fields validation in `dict_to_play_state` to: `match_time`, `possession_team`, `ball_position`, `game_phase`, `score_differential`, `game_clock`, `player_positions`, `decision_point_timestamp`
    - Update docstrings from yards to meters
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 13.3, 13.4_

  - [x] 2.2 Update Branch and EventMarker docstrings (`src/models/branch.py`)
    - Update `PlayerPosition` docstring: "yards" → "meters", coordinate descriptions for soccer field
    - Update `EventMarker` docstring: list soccer event types instead of American football
    - Update `Branch` docstring: reference soccer plays instead of football plays
    - _Requirements: 4.1, 13.3, 13.4_

  - [x] 2.3 Update EvaluationReport/SubMetrics (`src/models/evaluation_report.py`)
    - Rename `yard_gain_differential` to `ball_progression` in SubMetrics
    - Rename `line_integrity_score` to `formation_shape_score` in SubMetrics
    - Update all docstrings to reference soccer terminology
    - _Requirements: 6.2, 6.5, 7.1, 7.5, 13.3, 13.4_

- [x] 3. Checkpoint — Verify constants and models compile
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Migrate scoring modules (`src/scoring/`)
  - [x] 4.1 Update Gating (`src/scoring/gating.py`)
    - Update `_check_field_bounds`: limits to x ∈ [0, 68], y ∈ [0, 105] (no end zones)
    - Remove import of `END_ZONE_DEPTH`
    - Update explanation messages: "yd/s" → "m/s", field bounds references in meters
    - _Requirements: 1.4, 5.5, 13.3, 13.4_

  - [x] 4.2 Update Physical Plausibility (`src/scoring/physical_plausibility.py`)
    - Update docstrings and comments: "yards" → "meters", "yd/s" → "m/s"
    - Adjust speed scoring curve comment for soccer speeds (7–9 m/s common)
    - _Requirements: 5.4, 13.3, 13.4_

  - [x] 4.3 Update Tactical Consistency (`src/scoring/tactical_consistency.py`)
    - Replace `_ROLE_ZONES` with soccer positions: GK, CB, LB, RB, CDM, CM, CAM, LW, RW, ST (zones per design table)
    - Remove American football role zones: QB, WR, RB, TE, OL, DL, LB, CB, S, K, P
    - Rename `line_integrity_score` → `formation_shape_score` in `TacticalConsistencyResult` and `_compute_line_integrity` → `_compute_formation_shape`
    - Update `_compute_defensive_density`: ball carrier events to `{"dribble", "pass_received", "reception"}`, defensive roles to `{"CB", "LB", "RB", "CDM"}`, fallback key player from QB → ST
    - Update aggregate weights to include `formation_shape_score`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 13.3, 13.4_

  - [x] 4.4 Update Decision Value (`src/scoring/decision_value.py`)
    - Rename `yard_gain_differential` → `ball_progression` in `DecisionValueResult`
    - Rename `_MAX_YARD_RANGE` → `_MAX_METER_RANGE = 105.0`
    - Update turnover types to `{"interception", "dispossession"}`
    - Update scoring types to `{"goal"}`
    - Update docstrings and comments for soccer terminology
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 13.3, 13.4_

- [x] 5. Checkpoint — Verify scoring modules
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Migrate branch generator (`src/generation/branch_generator.py`)
  - Remove import of `END_ZONE_DEPTH`
  - Replace `_ROLE_BASE_VECTORS` with soccer position vectors: GK (0.0, 0.1), CB (0.0, 0.3), LB (-0.3, 0.7), RB (0.3, 0.7), CDM (0.0, 0.4), CM (0.1, 0.6), CAM (0.0, 0.8), LW (-0.4, 0.8), RW (0.4, 0.8), ST (0.0, 0.9)
  - Update field bounds clamping: y ∈ [0, 105] (no end zones)
  - Update `_decision_events`: generate pass, dribble, shot instead of throw, catch, handoff
  - Update `_decision_vector`: adjust for soccer tactics (pass play → passe, run play → drible)
  - Update `_find_role_player` calls: search ST, CM, LW instead of QB, WR, RB
  - Update `_default_events`: generate "kick_off" or "pass" instead of "snap"
  - Update docstrings: "yards" → "meters"
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 2.3, 4.4, 13.3, 13.4_

- [x] 7. Migrate viewer (`src/viewer/`)
  - [x] 7.1 Update viewer constants (`src/viewer/constants.py`)
    - Replace `FIELD_LENGTH_YARDS` → `FIELD_LENGTH_M = 105.0`, `FIELD_WIDTH_YARDS` → `FIELD_WIDTH_M = 68.0`
    - Remove: `END_ZONE_DEPTH_YARDS`, `END_ZONE_COLOR`, `SCRIMMAGE_LINE_COLOR`, `FIRST_DOWN_LINE_COLOR`, `YARD_LINE_WIDTH`, `YARD_LABEL_FONTSIZE`
    - Add: `PENALTY_AREA_COLOR`, `GOAL_AREA_COLOR`, `CENTER_CIRCLE_COLOR`, `MIDFIELD_LINE_WIDTH`, `BALL_MARKER_SIZE`, `BALL_MARKER_COLOR`
    - Update `ROLE_COLORS` to map soccer positions: GK, CB, LB, RB, CDM, CM, CAM, LW, RW, ST
    - _Requirements: 8.3, 8.4, 13.3_

  - [x] 7.2 Update viewer 2D (`src/viewer/viewer_2d.py`)
    - Rewrite `draw_field`: render FIFA soccer field (penalty areas, goal areas, center circle, midfield line, corner arcs, goals) — remove end zones, yard lines, hashmarks
    - Remove `draw_scrimmage_and_first_down` function
    - Add `draw_ball_position(ax, ball_position)` function to mark ball position on field
    - Update `draw_scenario_info`: display match_time, possession_team, game_phase instead of down, distance, field_position
    - Update `render_pipeline_report`: use `draw_ball_position` instead of `draw_scrimmage_and_first_down`
    - Update `render_single_branch`: use `draw_ball_position` instead of `draw_scrimmage_and_first_down`
    - Update all imports to use new constant names
    - _Requirements: 8.1, 8.2, 8.5, 8.6, 13.3, 13.4_

- [x] 8. Checkpoint — Verify viewer compiles
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Create soccer demo scenarios and update render script
  - [x] 9.1 Create `data/play_states/counter_attack_midfield.json`
    - Formation 4-3-3, match_time ~45min, game_phase "transition", ball_position at midfield
    - 11 players with soccer roles (GK, CB×2, LB, RB, CDM, CM, CAM, LW, RW, ST)
    - All positions within field bounds (x: 0–68, y: 0–105)
    - _Requirements: 9.1, 9.5_

  - [x] 9.2 Create `data/play_states/build_up_from_defense.json`
    - Formation 4-4-2, match_time ~15min, game_phase "open_play", ball_position in defensive third
    - 11 players with soccer roles
    - All positions within field bounds
    - _Requirements: 9.2, 9.5_

  - [x] 9.3 Create `data/play_states/set_piece_penalty_area.json`
    - Free kick positioning, match_time ~75min, game_phase "set_piece", ball_position near penalty area
    - 11 players with soccer roles
    - All positions within field bounds
    - _Requirements: 9.3, 9.5_

  - [x] 9.4 Remove old American football scenarios
    - Delete `data/play_states/first_and_ten_midfield.json`
    - Delete `data/play_states/second_and_long_after_sack.json`
    - Delete `data/play_states/third_and_short_goal_line.json`
    - _Requirements: 9.4_

  - [x] 9.5 Update render viewer script (`scripts/render_viewer.py`)
    - Update `DEMO_SCENARIOS` list to reference the 3 new soccer JSON files
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 10. Migrate test strategies (`tests/strategies.py`)
  - Update `_PLAYER_ROLES` to `["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"]`
  - Update `play_state_strategy()`: generate PlayStates with `match_time`, `possession_team`, `ball_position`, `game_phase` instead of `down`, `distance`, `field_position`
  - Update `_valid_x` to range [0, FIELD_WIDTH] (0–68m)
  - Update `_valid_y` to range [0, FIELD_LENGTH] (0–105m, no END_ZONE_DEPTH)
  - Update `valid_positions_strategy()`: bounds without end zones
  - Update `out_of_bounds_branch_strategy()`: violations at x<0, x>68, y<0, y>105 (no end zone offsets)
  - Remove import of `END_ZONE_DEPTH`
  - Update `evaluation_report_dict_strategy()`: `ball_progression` instead of `yard_gain_differential`, `formation_shape_score` instead of `line_integrity_score`
  - Update `sub_metrics_strategy()`: same field renames
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 2.4_

- [x] 11. Checkpoint — Verify strategies and demo scenarios
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Update all test files for soccer domain
  - [x] 12.1 Update model tests (`tests/models/test_play_state.py`, `tests/models/test_models.py`)
    - Update test data to use soccer fields (match_time, possession_team, ball_position, game_phase)
    - Remove references to down, distance, field_position
    - Update assertions for new field names
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 11.5_

  - [x] 12.2 Update gating tests (`tests/scoring/test_gating.py`)
    - Update test data to use soccer field bounds (x: 0–68, y: 0–105, no end zones)
    - Update speed threshold assertions to m/s values
    - Update contact event types in test data
    - _Requirements: 1.4, 5.5, 11.5_

  - [x] 12.3 Update physical plausibility tests (`tests/scoring/test_physical_plausibility.py`)
    - Update test data to use meters and m/s
    - Adjust expected scores for new thresholds
    - _Requirements: 5.4, 11.5_

  - [x] 12.4 Update tactical consistency tests (`tests/scoring/test_tactical_consistency.py`)
    - Update test data to use soccer roles and positions
    - Update assertions for `formation_shape_score` instead of `line_integrity_score`
    - Update defensive density test data with soccer events and roles
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 11.5_

  - [x] 12.5 Update decision value tests (`tests/scoring/test_decision_value.py`)
    - Update test data to use soccer events (goal, interception, dispossession)
    - Update assertions for `ball_progression` instead of `yard_gain_differential`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 11.5_

  - [x] 12.6 Update branch generator tests (`tests/generation/test_branch_generator.py`)
    - Update test PlayStates with soccer fields and roles
    - Update event type assertions for soccer events
    - Update field bounds assertions
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.5_

  - [x] 12.7 Update viewer tests (`tests/viewer/test_constants.py`, `tests/viewer/test_viewer_2d.py`, `tests/viewer/test_telemetry_panel.py`)
    - Update constant assertions for new soccer viewer constants
    - Update field rendering tests for FIFA field elements
    - Update scenario info tests for match_time, possession_team, game_phase
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 11.6_

  - [x] 12.8 Update property test files for soccer domain
    - Update `tests/models/test_play_state_properties.py` for soccer PlayState fields
    - Update `tests/scoring/test_gating_properties.py` for soccer field bounds
    - Update `tests/scoring/test_decision_value_properties.py` for soccer events and ball_progression
    - Update `tests/scoring/test_tactical_consistency_properties.py` for soccer roles and zones
    - Update `tests/scoring/test_physical_plausibility_properties.py` for m/s thresholds
    - Update `tests/generation/test_branch_generator_properties.py` for soccer events and bounds
    - Update `tests/scoring/test_validation_properties.py` for soccer field names
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 12.9 Update remaining test files
    - Update `tests/test_demo_play_states.py` for new soccer scenario files
    - Update `tests/test_pipeline.py`, `tests/test_pipeline_integration.py`, `tests/test_pipeline_properties.py` for soccer PlayState data
    - Update `tests/test_evaluator_v2.py`, `tests/test_evaluator_v2_properties.py` for soccer data
    - Update `tests/scripts/test_render_viewer.py` for new demo scenario paths
    - Update any other test files referencing American football data
    - _Requirements: 9.4, 9.5, 11.5, 11.6_

- [x] 13. Checkpoint — Verify all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Write property-based tests for soccer domain migration
  - [x] 14.1 Write property test for PlayState round-trip serialization
    - **Property 1: PlayState round-trip serialization**
    - Test that any valid soccer PlayState survives `play_state_to_dict` → `dict_to_play_state` round-trip
    - Use updated `play_state_strategy()` with soccer fields
    - **Validates: Requirements 3.4**

  - [x] 14.2 Write property test for PlayState validation rejects missing soccer fields
    - **Property 2: PlayState validation rejects missing soccer fields**
    - Test that dicts missing any required soccer field raise KeyError from `dict_to_play_state`
    - **Validates: Requirements 3.5**

  - [x] 14.3 Write property test for gating soccer field bounds
    - **Property 3: Gating validates soccer field bounds without end zones**
    - Test that field bounds gate passes iff all positions have x ∈ [0, 68] and y ∈ [0, 105], no end zones
    - **Validates: Requirements 1.4, 5.5**

  - [x] 14.4 Write property test for speed thresholds in m/s
    - **Property 4: Gating and plausibility use meters-per-second speed thresholds**
    - Test that speeds > 10.0 m/s (no contact) or > 15.0 m/s (contact) fail the speed gate
    - Test that plausibility assigns speed_score 0.0 for players exceeding 10.0 m/s
    - **Validates: Requirements 5.4, 5.5**

  - [x] 14.5 Write property test for generated events are soccer events
    - **Property 5: Generated branches contain only soccer events**
    - Test that all events from `generate_branches` have event_type from the soccer event set
    - **Validates: Requirements 4.4, 10.2**

  - [x] 14.6 Write property test for generated positions within soccer bounds
    - **Property 6: Generated branches respect soccer field bounds and speed limits**
    - Test that all positions from `generate_branches` have x ∈ [0, 68], y ∈ [0, 105], speed ≤ 8.5 m/s
    - **Validates: Requirements 10.3, 10.4**

  - [x] 14.7 Write property test for tactical zone checks
    - **Property 7: Tactical zone checks are consistent for soccer positions**
    - Test that positions within defined zones for each soccer role are not flagged as violations
    - **Validates: Requirements 6.1**

  - [x] 14.8 Write property test for ball progression in meters
    - **Property 8: Ball progression measures forward progress in meters**
    - Test that ball_progression is normalized by FIELD_LENGTH (105.0) and branches with greater forward progress have ball_progression > 0.5
    - **Validates: Requirements 7.1, 7.4**

  - [x] 14.9 Write property test for turnover detection with soccer events
    - **Property 9: Turnover detection uses soccer events**
    - Test that branches with "interception" or "dispossession" events have elevated turnover risk, and branches without have turnover_risk_delta ≥ 0.5
    - **Validates: Requirements 7.2**

- [x] 15. Checkpoint — Verify all property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Update steering documentation
  - [x] 16.1 Update `product.md`
    - Replace "football" with "futebol" (soccer) in domain descriptions
    - Update target users to reference soccer analysts
    - Update domain context to reference soccer plays and branches
    - _Requirements: 12.1_

  - [x] 16.2 Update `agents.md`
    - Replace "Football Play Simulation Evaluator" with "Soccer Play Simulation Evaluator"
    - Update project context to reference soccer simulation
    - Maintain all architectural conventions unchanged
    - _Requirements: 12.2, 12.3_

- [x] 17. Final checkpoint — Ensure all tests pass and no yards references remain
  - Ensure all tests pass, ask the user if questions arise.
  - Verify no residual "yards" references exist in source code, docstrings, or comments (Requirement 13.4)

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each migration layer
- Property tests validate the 9 correctness properties defined in the design document
- The bottom-up migration order (constants → models → scoring → generator → viewer → demos → tests → steering) ensures no forward dependencies
- The pipeline architecture (gating → validity → opportunity → ranking → visualization) remains unchanged
