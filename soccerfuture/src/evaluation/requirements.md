# Requirements

## Overview
Evaluate whether the app is trustworthy outside controlled fixture validation by testing:
1. human agreement with ranking and explainability
2. robustness under degraded or noisy inputs

This phase is about confidence, not new intelligence.

---

## User Story 1
As a product or research owner,
I want a lightweight human evaluation protocol,
so that I can measure whether analysts agree with branch ranking, explanations, and context impact.

### Acceptance Criteria
1. The system defines a reproducible human evaluation protocol.
2. The protocol covers:
   - top-1 plausibility
   - top-3 usefulness
   - explanation usefulness
   - context impact judgment
3. The protocol can be run on a fixed set of scenarios.
4. Results are recorded in a machine-readable format.
5. The protocol distinguishes:
   - agreement
   - disagreement
   - uncertainty

---

## User Story 2
As a maintainer,
I want a human evaluation runner,
so that prepared scenarios can be exported and reviewed consistently.

### Acceptance Criteria
1. The system can prepare an evaluation pack for selected scenarios.
2. Each evaluation item contains:
   - scenario id
   - viewer artifact or render reference if available
   - no-context result
   - with-context result
   - top branches
   - explanation snippets
3. The evaluation pack is deterministic and reproducible.
4. The output can be consumed manually or through simple forms/spreadsheets.

---

## User Story 3
As a developer,
I want robustness tests under controlled degradation,
so that I can measure ranking stability and failure quality.

### Acceptance Criteria
1. The system generates degraded variants of existing scenarios.
2. Supported degradations include:
   - small positional noise
   - missing player
   - partial context
   - ambiguous formation metadata
   - cache miss / fallback path
3. The robustness runner compares original vs degraded outputs.
4. The system records:
   - top-1 stability
   - top-3 stability
   - score drift
   - context classification drift
   - failure type

---

## User Story 4
As a maintainer,
I want robustness classification,
so that I can separate acceptable sensitivity from brittle behavior.

### Acceptance Criteria
1. The system classifies degraded-run outcomes into:
   - stable
   - sensitive but acceptable
   - brittle
   - failed clearly
2. Classification uses explicit deterministic thresholds.
3. Thresholds are configurable and visible.
4. The classification is included in machine-readable output and human-readable reports.

---

## User Story 5
As an analyst,
I want a consolidated human + robustness report,
so that I can judge whether the system is ready for broader use.

### Acceptance Criteria
1. The system generates a Markdown summary report.
2. The report includes:
   - human agreement metrics
   - robustness metrics
   - scenarios with strongest agreement
   - scenarios with strongest disagreement
   - brittle scenarios
   - clear recommendations
3. The report separates observed results from interpretation.
4. The report highlights whether the system appears:
   - trustworthy
   - conditionally trustworthy
   - too brittle for broader use

---

## User Story 6
As a maintainer,
I want regression and fixture-based validation for the new evaluation layer,
so that future changes do not distort trust metrics.

### Acceptance Criteria
1. Tests validate deterministic human-evaluation pack generation.
2. Tests validate robustness degradation generation.
3. Tests validate stability metric computation.
4. Tests validate classification outputs.
5. Tests validate report generation.
6. Tests do not require live network access.

---

## Non-Goals
This phase does not include:
- MatchPredict integration
- video model changes
- new ranking heuristics
- LLM-based reviewer automation
- UI redesign beyond what is necessary to inspect results
- large-scale annotation platform work
