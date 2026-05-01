# Design

## Overview
This spec adds a trust-validation layer on top of the existing system.

It has two components:
1. human evaluation
2. robustness evaluation

The purpose is to measure whether the app remains convincing and stable outside ideal fixture conditions.

---

## Architecture

### New Modules
- `src/evaluation/human_eval_protocol.py`
- `src/evaluation/human_eval_pack.py`
- `src/evaluation/human_eval_results.py`
- `src/evaluation/robustness_suite.py`
- `src/evaluation/robustness_metrics.py`
- `src/evaluation/trust_report.py`

### Existing Modules to Reuse
- `pipeline.py`
- `pipeline_report.py`
- `viewer_2d.py`
- `context_impact_analysis.py`
- `context_impact_report.py`

---

## Part A — Human Evaluation

### Goal
Measure whether humans agree with:
- top-1 branch
- top-3 usefulness
- explanation usefulness
- context impact classification

### Evaluation Pack
Each pack item should include:
- `scenario_id`
- `play_state_reference`
- `no_context_output_reference`
- `with_context_output_reference`
- `viewer_artifact_reference` if available
- `top_branches_summary`
- `explanation_summary`

### Human Questions
Each reviewed item should collect structured answers for:
- `top_1_plausible: yes | no | unsure`
- `top_3_useful: yes | no | unsure`
- `explanation_helpful: yes | no | unsure`
- `context_impact_label: helpful | neutral | degrading | unsure`
- `notes: str`

### HumanEvalResult Model
Suggested fields:
- `scenario_id`
- `reviewer_id`
- `top_1_plausible`
- `top_3_useful`
- `explanation_helpful`
- `context_impact_label`
- `notes`

### HumanEvalSummary Model
Suggested fields:
- `scenario_count`
- `review_count`
- `top_1_agreement_rate`
- `top_3_usefulness_rate`
- `explanation_helpfulness_rate`
- `context_label_agreement_rate`
- `high_disagreement_scenarios`
- `notes`

---

## Part B — Robustness Evaluation

### Goal
Test whether the system stays stable under controlled input degradation.

### Robustness Variants
For each selected scenario, generate variants:
- small positional noise
- missing player
- partial context
- ambiguous formation metadata
- cache miss path
- fallback path where supported

### Robustness Runner
For each original scenario:
1. run baseline
2. create degraded variants
3. run pipeline on each degraded variant
4. compare outputs against original

### Metrics
Per degraded variant:
- `top_1_changed: bool`
- `top_3_overlap_ratio: float`
- `validity_drift: float`
- `opportunity_drift: float`
- `context_label_changed: bool`
- `failure_mode: str | None`

### Classification
Classify each degraded run into:
- `stable`
- `sensitive_but_acceptable`
- `brittle`
- `failed_clearly`

### Example Heuristic Logic
- stable: top-1 unchanged and score drift below threshold
- sensitive_but_acceptable: top-1 may change but top-3 overlap remains high and no hard failure
- brittle: large ranking drift or erratic classification change
- failed_clearly: explicit error surfaced properly

Thresholds must be configurable and explicit.

---

## Output Design

### Machine-Readable Outputs
1. `human_eval_pack.json`
2. `human_eval_results.json`
3. `robustness_results.json`
4. `trust_summary.json`

### Human-Readable Outputs
1. `human_eval_protocol.md`
2. `trust_report.md`

---

## Reporting Design

### Trust Report Sections
- overview
- evaluation scope
- human agreement summary
- robustness summary
- strongest scenarios
- disagreement scenarios
- brittle scenarios
- operational notes
- recommendations

### Judgment Categories
The report may classify the system overall as:
- trustworthy
- conditionally trustworthy
- not yet trustworthy enough for broader use

This classification must be based on explicit observed metrics, not vague narrative.

---

## CLI / Scripts

### Human Evaluation
- prepare evaluation pack
- ingest evaluation results
- compute agreement summary

### Robustness
- run robustness suite on selected scenarios
- generate machine-readable results
- generate consolidated report

---

## Testing Strategy

### Unit Tests
- pack generation
- result parsing
- agreement metric computation
- degradation generation
- drift metric computation
- robustness classification
- report rendering

### Integration Tests
- paired pipeline execution through robustness runner
- deterministic evaluation pack generation
- trust summary generation from fixture data

### Regression Tests
- existing pipeline behavior remains unchanged
- evaluation layers remain deterministic with fixtures

---

## Risks

### Risk 1
Human protocol is too vague and produces noisy feedback.
#### Mitigation
Use structured multiple-choice fields with optional notes.

### Risk 2
Robustness degradations are too extreme or unrealistic.
#### Mitigation
Use bounded, configurable degradation strategies.

### Risk 3
Trust report becomes subjective.
#### Mitigation
Separate observed metrics from recommendations.

### Risk 4
Viewer artifacts become a blocker.
#### Mitigation
Viewer references are optional, not required.

---

## Definition of Done
This phase is complete when:
1. Human evaluation packs can be generated reproducibly.
2. Human evaluation results can be ingested and summarized.
3. Robustness variants can be generated and analyzed.
4. Stability classifications are computed deterministically.
5. A consolidated trust report is generated.
6. Tests and regressions pass using fixture-based inputs only.
