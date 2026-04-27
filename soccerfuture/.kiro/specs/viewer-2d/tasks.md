# Implementation Plan: Viewer 2D

## Overview

Build the 2D viewer module in strict dependency order: visual constants → field rendering → player/branch rendering → info panels → composition functions → CLI script → tests. Each module builds on the previous, with checkpoints after each major component. The viewer consumes existing `PipelineReport` data and renders it using matplotlib — no pipeline logic is modified.

## Tasks

- [x] 1. Create visual constants module `src/viewer/constants.py`
  - Create `src/viewer/__init__.py` (empty package init)
  - Create `src/viewer/constants.py` with all visual constants as defined in the design
  - Import `FIELD_LENGTH`, `FIELD_WIDTH`, `END_ZONE_DEPTH` from `src/utils/constants.py`
  - Define field dimension aliases: `FIELD_LENGTH_YARDS`, `FIELD_WIDTH_YARDS`, `END_ZONE_DEPTH_YARDS`
  - Define `ROLE_COLORS` dict (QB, WR, RB, TE, OL) and `DEFAULT_ROLE_COLOR`
  - Define `BRANCH_COLORS` list (at least 7 distinct colors)
  - Define marker sizes: `PLAYER_MARKER_SIZE`, `PLAYER_MARKER_SINGLE`, `PLAYER_LABEL_FONTSIZE`
  - Define trajectory constants: `TRAJECTORY_LINE_WIDTH`, `TRAJECTORY_LINE_WIDTH_SINGLE`, `ARROW_HEAD_WIDTH`, `ARROW_HEAD_LENGTH`
  - Define field colors: `FIELD_COLOR`, `END_ZONE_COLOR`, `LINE_COLOR`, `SCRIMMAGE_LINE_COLOR`, `FIRST_DOWN_LINE_COLOR`
  - Define line widths: `YARD_LINE_WIDTH`, `SCRIMMAGE_LINE_WIDTH`, `YARD_LABEL_FONTSIZE`
  - Define figure layout: `FIGURE_WIDTH`, `FIGURE_HEIGHT`, `FIELD_AXES_RECT`, `EXPLANATION_AXES_RECT`, `TELEMETRY_AXES_RECT`
  - Define font sizes: `TITLE_FONTSIZE`, `PANEL_TITLE_FONTSIZE`, `PANEL_TEXT_FONTSIZE`
  - No magic numbers — every visual value is a named constant
  - _Requirements: 11.1, 11.2, 11.3_

- [x] 2. Implement field rendering functions in `src/viewer/viewer_2d.py`
  - [x] 2.1 Implement `draw_field(ax)` function
    - Draw the main field rectangle (100 × 53.33 yards) with `FIELD_COLOR` background
    - Draw two end zones below y=0 and above y=100 with `END_ZONE_COLOR`
    - Draw yard lines every 10 yards with numeric labels
    - Draw hashmarks at standard positions
    - Set axis limits, remove ticks, set aspect ratio to equal
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 2.2 Implement `draw_scrimmage_and_first_down(ax, field_position, distance)` function
    - Draw line of scrimmage at `field_position` with `SCRIMMAGE_LINE_COLOR` and `SCRIMMAGE_LINE_WIDTH`
    - Draw first-down line at `field_position + distance` with `FIRST_DOWN_LINE_COLOR`
    - Both lines span the full field width
    - _Requirements: 1.4, 1.5_

- [x] 3. Implement player and branch rendering functions
  - [x] 3.1 Implement `draw_player_positions(ax, player_positions, player_roles)` function
    - Scatter plot each player at (x, y) with color from `ROLE_COLORS` based on role
    - Use `DEFAULT_ROLE_COLOR` for unknown roles
    - Label each marker with `player_id` using `PLAYER_LABEL_FONTSIZE`
    - Add a legend mapping colors to roles
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 3.2 Implement `draw_branches(ax, ranked_branches)` function
    - For each ranked branch, assign a color from `BRANCH_COLORS` (cycling if needed)
    - For each player in each branch, extract positions sorted by timestamp
    - Draw line segments connecting consecutive positions
    - Add directional arrows using `ARROW_HEAD_WIDTH` and `ARROW_HEAD_LENGTH`
    - Add legend with `branch_id` and `composite_score` for each branch
    - Use `TRAJECTORY_LINE_WIDTH` for line thickness
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x] 3.3 Implement `draw_single_branch(ax, ranked_branch, color)` function
    - Same trajectory logic as `draw_branches` but for a single branch
    - Use `PLAYER_MARKER_SINGLE` and `TRAJECTORY_LINE_WIDTH_SINGLE` for enhanced visibility
    - _Requirements: 8.1, 8.2_

- [x] 4. Checkpoint — Verify field and player rendering
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement info panel rendering functions
  - [x] 5.1 Implement `draw_scenario_info(fig, play_state)` function
    - Format down & distance as title (e.g., "1st & 10")
    - Display field position in yards (e.g., "Own 50")
    - Display score differential
    - Conditionally display formation from `metadata["formation"]` if present
    - Conditionally display description from `metadata["description"]` if present
    - Use `fig.suptitle()` with `TITLE_FONTSIZE`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x] 5.2 Implement `draw_explanation_panel(ax, ranked_branches)` function
    - For each branch: display `branch_id`, `validity_score`, `opportunity_score`, `composite_score`
    - Display `promoted_factors` and `penalized_factors` from `ranking_explanation`
    - Display `top_scoring_block` and `bottom_scoring_block`
    - If `near_threshold_warning` is present, display it with visual emphasis
    - Use `PANEL_TITLE_FONTSIZE` and `PANEL_TEXT_FONTSIZE`
    - Turn off axis frame and ticks for clean text panel
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [x] 5.3 Implement `draw_telemetry_panel(ax, metadata)` function
    - Extract telemetry from `metadata["telemetry"]` if present
    - Display `branches_generated`, `hard_fail_count`, `score_filtered_count`
    - Display `avg_score_by_strategy` as key-value pairs
    - Display `time_per_stage` as key-value pairs
    - If telemetry is missing, display "Telemetry data not available"
    - Turn off axis frame and ticks for clean text panel
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 6. Implement composition functions
  - [x] 6.1 Implement `render_pipeline_report(report_dict)` function
    - Create figure with `FIGURE_WIDTH` × `FIGURE_HEIGHT`
    - Create field axes at `FIELD_AXES_RECT`, explanation axes at `EXPLANATION_AXES_RECT`, telemetry axes at `TELEMETRY_AXES_RECT`
    - Call `draw_field` → `draw_scrimmage_and_first_down` → `draw_player_positions` → `draw_branches` on field axes
    - Call `draw_explanation_panel` on explanation axes
    - Call `draw_telemetry_panel` on telemetry axes
    - Call `draw_scenario_info` on figure
    - Return the composed `matplotlib.figure.Figure`
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x] 6.2 Implement `render_single_branch(report_dict, branch_index)` function
    - Validate `branch_index` — raise `ValueError` if `ranked_branches` is empty, `IndexError` if out of range
    - Create figure with same layout as `render_pipeline_report`
    - Draw field, scrimmage/first-down, player positions, then single branch with `draw_single_branch`
    - Show full explanation for the selected branch
    - Return the composed `matplotlib.figure.Figure`
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 7. Checkpoint — Verify viewer module
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement CLI script `scripts/render_viewer.py`
  - [x] 8.1 Implement argument parsing and `main()` function
    - Parse `--from-json <path>` and `--save-json <path>` optional arguments using `argparse`
    - Define `DEMO_SCENARIOS` list with paths to the 3 demo play state JSON files
    - Define `OUTPUT_DIR = "output/viewer"`
    - Create output directory if it doesn't exist
    - _Requirements: 7.1, 7.2, 10.1_
  - [x] 8.2 Implement `load_report_from_json(path)` and `save_report_to_json(report_dict, path)` helpers
    - `load_report_from_json`: read JSON file, return dict; raise `FileNotFoundError` / `json.JSONDecodeError` on failure
    - `save_report_to_json`: write dict as JSON with 2-space indent
    - _Requirements: 10.1, 10.2, 10.3_
  - [x] 8.3 Implement `run_scenario(scenario_file)` function
    - Load PlayState JSON from file
    - Parse via `dict_to_play_state`
    - Execute pipeline via `run_pipeline`
    - Return `report.to_dict()`
    - _Requirements: 7.1, 7.3_
  - [x] 8.4 Wire main flow: iterate scenarios, render, save PNGs, print summary
    - If `--from-json`: load single report, render, save PNG
    - Otherwise: loop over `DEMO_SCENARIOS`, run each, optionally save JSON, render, save PNG
    - Use `fig.savefig()` with `dpi=150`, `bbox_inches="tight"`
    - Print summary to stdout with scenario names and output paths
    - Exit code 0 on success, 1 on any failure
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 10.1, 10.2, 10.3, 10.4_

- [x] 9. Checkpoint — Verify CLI script
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Write unit tests for viewer module
  - [x] 10.1 Create `tests/viewer/__init__.py` and `tests/viewer/test_constants.py`
    - Verify all required constants are defined and have correct types
    - Verify `ROLE_COLORS` contains entries for QB, WR, RB, TE, OL
    - Verify `BRANCH_COLORS` has at least 5 entries
    - Verify layout rects are lists of 4 floats
    - _Requirements: 11.1, 11.2, 11.3_
  - [x] 10.2 Create `tests/viewer/test_viewer_2d.py` with tests for field rendering
    - Test `draw_field` produces an axes with correct limits and patches
    - Test `draw_scrimmage_and_first_down` adds lines at correct positions
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [x] 10.3 Add tests for player and branch rendering
    - Test `draw_player_positions` with sample positions and roles — verify scatter artists created
    - Test `draw_branches` with sample ranked branches — verify line artists created
    - Test `draw_single_branch` uses enhanced marker/line sizes
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 8.1, 8.2_
  - [x] 10.4 Add tests for panel rendering
    - Test `draw_scenario_info` sets figure suptitle with down & distance
    - Test `draw_explanation_panel` renders text for each branch's explanation
    - Test `draw_telemetry_panel` renders telemetry data when present
    - Test `draw_telemetry_panel` shows fallback message when telemetry is missing
    - _Requirements: 4.1, 4.5, 5.1, 5.5, 6.1, 6.2, 6.3_
  - [x] 10.5 Add tests for composition functions
    - Test `render_pipeline_report` returns a `matplotlib.figure.Figure` with expected axes count
    - Test `render_single_branch` returns a figure for valid branch index
    - Test `render_single_branch` raises `IndexError` for out-of-range index
    - Test `render_single_branch` raises `ValueError` for empty ranked_branches
    - _Requirements: 8.1, 8.3, 9.1, 9.3_

- [x] 11. Write unit tests for CLI script
  - [x] 11.1 Create `tests/scripts/test_render_viewer.py`
    - Test `load_report_from_json` with valid JSON file
    - Test `load_report_from_json` raises on missing file
    - Test `save_report_to_json` writes valid JSON with 2-space indent
    - Test `main()` with `--from-json` flag using a fixture report JSON
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major component
- The design has no Correctness Properties section, so property-based tests are not included
- Unit tests validate rendering output by inspecting matplotlib artist objects and figure structure
- The build order (constants → field → players/branches → panels → composition → CLI → tests) ensures no forward dependencies
