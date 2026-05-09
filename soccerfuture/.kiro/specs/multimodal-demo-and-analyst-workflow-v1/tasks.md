# Tasks

- [x] Create `src/workflows/analyst_workflow_runner.py`

- [x] Implement single-scenario workflow orchestration for:
  - input load
  - optional extraction
  - pipeline execution
  - report generation
  - viewer generation
  - summary generation
  - bundle write

- [x] Create `src/workflows/scenario_bundle.py`

- [x] Define deterministic bundle structure and artifact reference utilities

- [x] Create `src/workflows/analyst_summary.py`

- [x] Render analyst-facing Markdown summaries including:
  - scenario overview
  - source type
  - extraction notes
  - top branches
  - explanation highlights
  - confidence/caveats
  - context/prior influence
  - artifact references

- [x] Create `src/workflows/batch_demo_runner.py`

- [x] Implement batch execution over selected scenarios

- [x] Create `src/workflows/demo_index.py`

- [x] Generate aggregate index artifacts in:
  - JSON
  - Markdown

- [x] Add step-level status tracking for:
  - load
  - extract
  - pipeline
  - report
  - viewer
  - summary
  - bundle write

- [x] Define machine-readable run status artifact format

- [x] Add support for partial-success workflows with clear failure visibility

- [x] Add unit tests for:
  - bundle structure generation
  - analyst summary rendering
  - demo index generation
  - step status handling

- [x] Add integration tests for:
  - full single-run workflow with fixture inputs
  - full batch-run workflow with fixture inputs
  - partial-failure behavior
  - deterministic artifact generation

- [x] Add regression tests ensuring:
  - existing pipeline behavior remains unchanged
  - workflow packaging remains deterministic

- [x] Add fixture scenario lists for batch workflow execution

- [x] Document the analyst workflow and demo bundle process in the README
