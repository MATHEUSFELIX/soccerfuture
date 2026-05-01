# Implementation Plan: Context Impact Evaluation v1

## Overview

Evaluate the real impact of match-context integration on pipeline behavior by comparing executions with and without context. This phase produces evidence, not additional ranking logic.

## Tasks

- [x] 1. Create `src/evaluation/__init__.py` and `src/evaluation/context_impact_analysis.py` with ContextImpactResult and ContextImpactSummary models, paired execution runner, per-scenario diff logic, aggregate metrics, classification rules, and JSON output

- [x] 2. Add explicit configurable thresholds/constants for impact classification (helpful/neutral/degrading)

- [x] 3. Implement batch execution over selected fixture scenarios with deterministic results

- [x] 4. Create `src/evaluation/context_impact_report.py` to generate Markdown reports from JSON analysis output including overview, aggregate metrics, helped/neutral/degraded scenarios, operational observations, and recommendations

- [x] 5. Optionally include Viewer 2D artifact references if available without making them mandatory

- [x] 6. Add unit tests for per-scenario diff logic, aggregate metric computation, helpful/neutral/degrading classification, and markdown report generation

- [x] 7. Add integration tests for paired no-context/with-context pipeline execution, JSON output schema stability, and deterministic batch results from fixtures

- [x] 8. Add regression tests ensuring no-context baseline remains unchanged

- [x] 9. Add a CLI script entry point for running the analysis locally and generating the Markdown summary from JSON output

- [x] 10. Commit and push to GitHub
