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

## Project Structure

```
src/
  domain/           # Domain models (MatchContext, ContextSignals)
  integrations/     # Soccerdata adapter and cache
  models/           # Pipeline report, play state, branch models
  scoring/          # Validity, opportunity, gating scoring modules
  services/         # Context enricher
  viewer/           # 2D visualization
  utils/            # Shared constants and helpers
tests/              # Unit, integration, and regression tests
data/               # Play states, fixtures, benchmarks
```
