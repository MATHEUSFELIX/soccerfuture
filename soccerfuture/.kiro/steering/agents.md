---
inclusion: always
---

# AI Assistant Rules — Soccer Play Simulation Evaluator

## Project Context

You are working on a soccer play simulation evaluator. It scores simulated play branches on physical validity and tactical opportunity, with gating logic to reject impossible outcomes. Refer to `product.md` for domain definitions, `tech.md` for stack and style, and `structure.md` for layout.

## Evaluation Pipeline Semantics

- The evaluation pipeline has a strict ordering: gating → validity → opportunity.
- Physical validity is a hard gate. A branch that fails validity must be rejected before opportunity is ever considered.
- Tactical opportunity scores are only meaningful on branches that pass all gates.
- Never allow a high opportunity score to override or mask a gating failure.

## Change-Making Discipline

- Preserve the modular separation of scoring dimensions. Never merge validity, opportunity, or gating logic into a single function or module.
- When modifying any evaluator, keep existing JSON output shapes stable. Add new fields; do not rename or remove existing ones unless the change is an intentional, versioned migration.
- When adding a new score or metric, always include:
  1. Sub-metric fields that break down how the score was derived.
  2. An explanation-friendly name suitable for analyst-facing output.
  3. Corresponding unit tests (and property-based tests where applicable).

## Code Generation Guardrails

- Prefer explicit, named metrics over vague heuristic summaries. Every number in the output should be traceable to a clear computation.
- Do not introduce cross-imports between scoring modules (`src/scoring/`). Composition happens at the orchestration layer only.
- Do not add heavyweight dependencies. Scoring must remain deterministic and rule-based unless learned models are explicitly requested.
- All new public functions require type hints, a Google-style docstring, and at least one test.

## Review Checklist (apply before finalizing any change)

1. Does the change preserve module independence across scoring dimensions?
2. Are all new outputs JSON-serializable and accompanied by sub-metrics?
3. Does every rejection path produce a human-readable explanation?
4. Are tests added or updated to cover the new or changed behavior?
5. Is the gating → validity → opportunity ordering still respected?
