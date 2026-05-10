# Tasks — Production Observability and Governance

## Pre-Stage Gate
- [x] Run the full test suite before starting.
- [x] Confirm all tests pass.
- [x] Stop and fix any failure before implementation.

## Implementation Tasks
- [x] Create provenance model.
- [x] Create structured logger wrapper.
- [x] Create metrics collector.
- [x] Create policy checks for rejected/low-confidence inputs and missing artifacts.
- [x] Generate audit report.
- [x] Wire observability into workflow runner and runtime ingestion.
- [x] Add tests for provenance, metrics, policy checks, and audit output.
- [x] Update README with governance workflow.

## Test Gate
- [x] Add/update unit tests.
- [x] Add/update integration tests.
- [x] Add/update regression tests.
- [x] Run targeted tests for this stage.
- [x] Run the full test suite.
- [x] Confirm all tests pass.

## Documentation Gate
- [x] Update README/docs.
- [x] Document any new commands, artifacts, or workflow changes.

## Completion Gate
- [x] Confirm acceptance criteria are complete.
- [x] Confirm no regressions.
- [x] Commit completed stage.
- [x] Only then proceed to the next stage.
