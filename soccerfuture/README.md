# Soccer Play Simulation Evaluator

Evaluates simulated soccer play branches by comparing them against real continuation windows. Each branch is scored on physical validity and tactical opportunity, with gating logic to reject impossible outcomes.

## Quick Start

```bash
pip install -r requirements.txt
pytest tests/ -x -q
```

## Match Context Integration

The pipeline supports optional pre-match context to enrich branch evaluation with team-level tactical signals.

### Fetching Context

Use `get_match_context` to retrieve context for two named teams:

```python
from src.integrations.soccerdata_adapter import get_match_context

ctx = get_match_context(
    home_team="FC Porto",
    away_team="SL Benfica",
    competition="Primeira Liga",
    season="2024",
    lookback_matches=10,
    use_cache=True,
)
```

This fetches data only for the explicitly named teams — no broad crawling or automatic team discovery.

### Passing Context to the Pipeline

Pass the `MatchContext` as an optional argument to `run_pipeline`:

```python
from src.pipeline import run_pipeline, PipelineConfig
from src.models.play_state import dict_to_play_state

report = run_pipeline(play_state, PipelineConfig(), match_context=ctx)
```

When `match_context` is `None` (the default), the pipeline behaves exactly as before — context is fully optional.

### What the Report Includes

When context is provided, the `PipelineReport` includes:

- `match_context`: Serialized `MatchContext` dict (teams, metrics, comparative edges).
- `context_signals`: Derived `ContextSignals` dict (aggression bias, risk tolerance, retention bias, game-state pressure, and explanatory notes).
- `metadata["context_requested"]`: `True` when a `MatchContext` was passed.
- `metadata["context_applied"]`: `True` when `ContextSignals` were derived.
- `metadata["context_cache_status"]`: Cache status (`"hit"`, `"miss"`, `"bypass"`).

When context is absent, `match_context` and `context_signals` are `None`, and the metadata flags are `False`.

### Cache Behavior

The soccerdata adapter uses a file-based cache with TTL support:

- Cache is enabled by default (`use_cache=True`).
- Set `use_cache=False` to bypass the cache entirely.
- Expired entries are re-fetched automatically.
- Cache status is reported in the `MatchContext.cache_status` field (`"hit"`, `"miss"`, `"expired"`, `"bypass"`).

### Visualization

When match context is present, the 2D viewer adds a fourth panel showing team names, comparative edges, cache status, and derived signal notes. Without context, the viewer renders the standard three-panel layout.

## Human Evaluation and Robustness

The project includes a trust evaluation framework for measuring pipeline reliability outside controlled fixtures.

### Human Evaluation

Generate structured evaluation packs for human reviewers, then ingest their ratings to produce aggregate summaries.

```bash
# Generate an evaluation pack from all play states in data/play_states/
python scripts/trust_eval.py human-pack --output output/human_eval_pack.json
```

Each pack contains pipeline reports paired with standard questions (ranking quality, explanation clarity, physical plausibility, tactical coherence, overall trust). Evaluators rate each question on a 1–5 scale.

After collecting responses, ingest them programmatically:

```python
from src.evaluation.human_eval_results import HumanEvalResponse, ingest_responses

responses = [
    HumanEvalResponse(
        scenario_id="counter_attack_midfield",
        evaluator_id="analyst_1",
        ratings={"q_ranking": 4, "q_explanation": 3, "q_plausibility": 4,
                 "q_tactical": 3, "q_overall": 4},
    ),
]
summary = ingest_responses(responses, protocol)
```

### Robustness Analysis

Test pipeline stability under degraded inputs using four deterministic strategies: noise injection, missing players, time shift, and position swap.

```bash
# Run robustness analysis across all strategies and play states
python scripts/trust_eval.py robustness --output output/robustness.json
```

Each scenario is run as a baseline/degraded pair. Results are classified as **robust**, **sensitive**, or **fragile** based on validity/opportunity deltas and ranking stability.

### Consolidated Trust Report

Combine human evaluation, robustness, and context impact results into a single Markdown report with trust assessment and recommendations.

```bash
# Generate trust report (all inputs are optional)
python scripts/trust_eval.py trust-report \
    --human-eval output/human_eval.json \
    --robustness output/robustness.json \
    --context-impact output/context_impact.json \
    --output output/trust_report.md
```

The report includes per-stream summaries, a deterministic trust level (High / Moderate / Low), and actionable recommendations. Missing streams are noted but do not block report generation.

## Project Structure

```
src/
  domain/           # Domain models (MatchContext, ContextSignals)
  evaluation/       # Human eval protocol, robustness suite, trust report
  integrations/     # Soccerdata adapter and cache
  models/           # Pipeline report, play state, branch models
  scoring/          # Validity, opportunity, gating scoring modules
  services/         # Context enricher
  viewer/           # 2D visualization
  utils/            # Shared constants and helpers
scripts/            # CLI entry points (trust_eval.py, render_viewer.py, etc.)
tests/              # Unit, integration, and regression tests
data/               # Play states, fixtures, benchmarks
```
