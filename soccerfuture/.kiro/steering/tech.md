---
inclusion: always
---

# Technology Stack

## Language & Runtime

- Python 3.11+
- Use type hints on all function signatures (parameters and return types).
- Use `dataclasses` or plain typed dicts for data structures. Avoid Pydantic unless explicitly added later.

## Dependencies

- Keep third-party dependencies minimal. No heavyweight ML or deep-learning libraries in MVP scope.
- Deterministic, rule-based scoring only until learned models are explicitly introduced.
- Standard library is preferred wherever it covers the need.

## Data & Serialization

- All input/output contracts use JSON.
- Use Python's built-in `json` module for serialization.
- Data models must be fully JSON-serializable. Avoid datetime objects or custom types that require special encoders unless a helper is provided in `src/utils/`.

## Testing

- Test framework: `pytest`
- Property-based testing: `hypothesis` (use for correctness-property tests).
- Run tests: `pytest tests/` from the project root.
- Test files mirror source paths: `src/scoring/validity.py` → `tests/scoring/test_validity.py`.
- Every new scoring function or model must have corresponding unit tests before it is considered complete.

## Code Style

- Follow PEP 8.
- File names use `snake_case`.
- One public class or logical unit per file.
- Prefer pure functions with explicit inputs and outputs. Avoid module-level mutable state.
- All named constants must be descriptive and defined in `src/utils/`. No magic numbers.
- Docstrings on every public function and class (Google style).

## Build & Run

- No compiled build step. Run source directly with `python -m`.
- No CLI framework required yet. Entry points are plain Python scripts or pytest invocations.
- If a `requirements.txt` or `pyproject.toml` is added, install with `pip install -r requirements.txt` or `pip install .`.

## Architecture Patterns

- Scoring modules (`src/scoring/`) are independent. They must not import from each other; compose at the orchestration layer.
- Functions should be small and single-purpose. If a function exceeds ~40 lines, consider splitting it.
- Every scoring function returns sub-metrics alongside the aggregate score. No opaque numbers.
- Gating logic is binary pass/fail with mandatory human-readable explanations on rejection.
