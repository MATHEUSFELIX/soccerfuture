---
inclusion: always
---

# Project Structure

## Directory Layout

```
src/                  # Core evaluator source code
  scoring/            # Scoring modules (validity, opportunity, gating)
  models/             # Data models and type definitions
  utils/              # Shared helpers and constants
tests/                # Unit and regression tests (mirrors src/ layout)
data/                 # Demo inputs, fixture files, and sample branches
.kiro/
  specs/              # Kiro feature specs
  steering/           # Persistent project instructions
```

## Architecture Conventions

- Each scoring dimension (validity, opportunity, gating) lives in its own module under `src/scoring/`.
- Evaluator functions must be small and single-purpose. No monolithic evaluators.
- Every scoring function must return transparent sub-metrics alongside the final score. No opaque aggregate numbers.
- Data models defining branch, play, and evaluation structures belong in `src/models/`.
- Shared utilities and named constants go in `src/utils/`. No magic numbers or unnamed thresholds.

## File & Module Rules

- One public class or logical unit per file. Keep files focused.
- File names use `snake_case`.
- Test files mirror source paths: `src/scoring/validity.py` → `tests/scoring/test_validity.py`.
- Input/output contracts use JSON. Schema definitions should live alongside the models they describe.

## Code Organization Principles

- Prefer pure functions with explicit inputs and outputs over hidden state.
- Scoring modules must not depend on each other directly. Compose at the evaluator/orchestration layer.
- Keep third-party dependencies minimal. No heavyweight ML libraries in MVP scope.
- All named constants must have descriptive names and be defined in a single, importable location.
