# Tasks

- [x] Create `src/review/review_pack.py`

- [x] Implement generation of concise stakeholder-facing review packs from scenario bundles

- [x] Create `src/review/review_feedback_schema.py`

- [x] Define structured feedback schema with bounded fields and optional notes

- [x] Create `src/review/review_feedback_ingest.py`

- [x] Implement deterministic ingestion and aggregation of reviewer feedback

- [x] Surface aggregate metrics including:
  - top-1 plausibility rate
  - top-3 usefulness rate
  - summary clarity rate
  - confidence sufficiency rate
  - blocker frequencies
  - requested improvement frequencies
  - high-disagreement scenarios

- [x] Create `src/review/demo_readiness.py`

- [x] Implement deterministic readiness checks and labels:
  - ready
  - partially_ready
  - not_ready

- [x] Create `src/review/review_index.py`

- [x] Generate:
  - review_index.json
  - review_index.md

- [x] Create `src/review/stakeholder_report.py`

- [x] Generate Markdown stakeholder review report from:
  - review packs
  - readiness outputs
  - feedback aggregates

- [x] Add support for preserving partial artifacts when review-layer steps fail

- [x] Add unit tests for:
  - review pack generation
  - feedback schema validation
  - feedback ingestion
  - readiness classification
  - review index generation
  - stakeholder report rendering

- [x] Add integration tests for:
  - bundle -> review pack flow
  - feedback ingestion -> aggregate report flow
  - deterministic readiness evaluation across scenario sets

- [x] Add regression tests ensuring:
  - analyst workflow outputs remain unchanged
  - review-layer outputs remain deterministic in fixture mode

- [x] Add fixture review feedback records for deterministic tests

- [x] Document stakeholder review and demo-hardening workflow in the README
