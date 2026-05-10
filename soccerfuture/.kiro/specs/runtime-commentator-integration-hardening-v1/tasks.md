# Tasks

- [x] Create `src/integrations/commentator_schema_registry.py`

- [x] Implement schema version detection and structural validation

- [x] Create `src/integrations/commentator_payload_normalizer.py`

- [x] Implement deterministic field normalization with:
  - field name aliases
  - numeric coercion
  - default confidence
  - default frame_rate
  - rejection of critically malformed payloads

- [x] Create `src/services/input_quality_assessor.py`

- [x] Implement quality grading:
  - good
  - acceptable
  - poor
  - rejected

- [x] Create `src/services/extraction_diagnostics.py`

- [x] Generate machine-readable diagnostics combining:
  - schema detection
  - normalization
  - quality assessment

- [x] Create `src/evaluation/ingestion_robustness_report.py`

- [x] Generate aggregate robustness report with:
  - acceptance/rejection counts
  - grade distribution
  - common warnings
  - common rejection reasons
  - Markdown rendering

- [x] Add unit tests for:
  - schema detection
  - payload normalization
  - quality grading
  - diagnostics generation
  - rejection rules
  - ingestion robustness reporting

- [x] Add regression tests ensuring:
  - clean fixture compatibility preserved
  - deterministic behavior in fixture mode

- [x] Document ingestion hardening workflow in the README
