# Tasks

- [ ] Create `src/evaluation/human_eval_protocol.py` defining the review questions and output schema

- [ ] Create `src/evaluation/human_eval_pack.py` to generate deterministic human review packs from selected scenarios

- [ ] Create `src/evaluation/human_eval_results.py` to ingest structured reviewer answers and compute aggregate agreement metrics

- [ ] Define models for:
  - human evaluation item
  - human evaluation result
  - human evaluation summary

- [ ] Add support for optional viewer artifact references in evaluation packs

- [ ] Create `src/evaluation/robustness_suite.py` to generate degraded scenario variants

- [ ] Support bounded degradation types:
  - positional noise
  - missing player
  - partial context
  - ambiguous formation metadata
  - cache miss / fallback where supported

- [ ] Create `src/evaluation/robustness_metrics.py` to compare original vs degraded runs

- [ ] Compute metrics including:
  - top-1 changed
  - top-3 overlap ratio
  - validity drift
  - opportunity drift
  - context classification drift
  - failure mode

- [ ] Implement deterministic robustness classifications:
  - stable
  - sensitive_but_acceptable
  - brittle
  - failed_clearly

- [ ] Add configurable thresholds/constants for robustness classification

- [ ] Create `src/evaluation/trust_report.py` to combine:
  - human evaluation summary
  - robustness summary
  - recommendations

- [ ] Generate machine-readable outputs:
  - human_eval_pack.json
  - human_eval_results.json
  - robustness_results.json
  - trust_summary.json

- [ ] Generate human-readable outputs:
  - human_eval_protocol.md
  - trust_report.md

- [ ] Add CLI or script entry point for generating the human evaluation pack

- [ ] Add CLI or script entry point for ingesting human evaluation results

- [ ] Add CLI or script entry point for running the robustness suite

- [ ] Add CLI or script entry point for generating the consolidated trust report

- [ ] Add unit tests for:
  - evaluation pack generation
  - human result parsing
  - agreement metric computation
  - degradation generation
  - robustness drift metrics
  - robustness classification
  - trust report rendering

- [ ] Add integration tests for:
  - pipeline execution through degraded variants
  - deterministic pack generation from fixtures
  - end-to-end trust summary generation

- [ ] Add regression tests ensuring existing pipeline behavior remains unchanged

- [ ] Add fixture scenarios and fixture reviewer results for deterministic tests

- [ ] Document how to run human evaluation and robustness evaluation in the README
