# Design

## Overview
This spec introduces optional match-context enrichment using targeted soccerdata queries.

The integration is intentionally constrained:
- explicit team selection only
- lazy fetching only
- file-based cache
- deterministic enrichment rules
- no dependency on context for normal pipeline execution

The design goal is to increase contextual intelligence without turning the app into a broad crawler or breaking the current baseline.

---

## Architecture

### New Modules
- `src/domain/match_context.py`
- `src/integrations/soccerdata_adapter.py`
- `src/integrations/soccerdata_cache.py`
- `src/services/context_enricher.py`

### Existing Modules to Extend
- `pipeline.py`
- `pipeline_report.py`
- `explainability.py`
- `viewer_2d.py`

---

## Data Flow

```text
Explicit team selection
  -> soccerdata_adapter
  -> soccerdata_cache
  -> MatchContext
  -> context_enricher
  -> Pipeline
  -> PipelineReport
  -> Viewer 2D
```

### Execution Modes

#### Mode A — No Context
```text
PlayState -> Pipeline -> Report -> Viewer
```

#### Mode B — With Context
```text
PlayState + MatchContext -> ContextEnricher -> Pipeline -> Report -> Viewer
```

The no-context path must preserve current behavior.

---

## Domain Model

### MatchContext
A normalized model representing externally fetched team-level context.

#### Fields
- `home_team: str`
- `away_team: str`
- `competition: str | None`
- `season: str | None`
- `lookback_matches: int`
- `source: str`
- `cache_status: str`
- `home_metrics: TeamContextMetrics`
- `away_metrics: TeamContextMetrics`
- `comparative_signals: ComparativeSignals`
- `fetched_at: str | None`

### TeamContextMetrics
Represents summarized team-level metrics.

#### Fields
- `matches_sampled: int`
- `wins: int`
- `draws: int`
- `losses: int`
- `goals_for_avg: float | None`
- `goals_against_avg: float | None`
- `xg_for_avg: float | None`
- `xg_against_avg: float | None`
- `form_points: int | None`
- `elo: float | None`
- `style_tags: list[str]`

### ComparativeSignals
Represents normalized comparative context.

#### Fields
- `stronger_team: str | None`
- `form_edge: str | None`
- `attack_edge: str | None`
- `defense_edge: str | None`
- `notes: list[str]`

### ContextSignals
Deterministic signals derived from MatchContext for the pipeline.

#### Fields
- `aggression_bias: float`
- `risk_tolerance: float`
- `retention_bias: float`
- `likely_game_state_pressure: float`
- `notes: list[str]`

---

## Adapter Design

### Function Contract
```python
get_match_context(
    home_team: str,
    away_team: str,
    competition: str | None = None,
    season: str | None = None,
    lookback_matches: int = 10,
    use_cache: bool = True,
) -> MatchContext
```

### Rules
1. The adapter must only fetch data for explicitly selected teams.
2. The adapter must not crawl full competitions or broad datasets.
3. The adapter must be testable with fixtures and mocks.
4. The adapter must return normalized MatchContext objects only.

### Failure Handling
Possible outcomes:
- success with fresh fetch
- success from cache
- fallback with partial metrics
- explicit failure with clear error

The adapter must never silently return malformed context.

---

## Cache Design

### Cache Key
```text
{home_team}_{away_team}_{competition}_{season}_{lookback_matches}
```

### Cache Contents
Each cache entry stores:
- raw normalized MatchContext payload
- source name
- fetched_at timestamp
- version metadata if useful

### Cache Policy
- file-based cache
- TTL-configurable
- bypass supported
- explicit cache hit/miss status surfaced in MatchContext

---

## Context Enricher Design

### Purpose
Convert MatchContext into deterministic pipeline-ready signals.

### Inputs
- `MatchContext`

### Outputs
- `ContextSignals`

### Initial Heuristic Strategy
The enricher should derive bias and pressure signals from comparative metrics.

Examples:
- stronger recent attack edge -> slightly higher aggression bias
- weaker defense -> reduced retention bias
- high form disparity -> stronger pressure note
- unclear or missing values -> neutral defaults with note

### Constraints
- deterministic only
- explainable outputs
- graceful degradation on missing values
- no learned model behavior

---

## Pipeline Integration Design

### Changes
The pipeline accepts optional `match_context` and optional `context_signals`.

### Required Behavior
- no-context flow remains stable
- context-aware flow adds metadata and explainability
- scoring logic may read context signals, but only through explicit interfaces

### Telemetry
Telemetry should capture:
- whether context was requested
- whether context was applied
- cache hit/miss
- fetch time if available
- source name

---

## Reporting Design

### PipelineReport Extensions
Add:
- `match_context`
- `context_signals`

### Explainability Extensions
Explainability may include:
- context was applied or not
- context was neutral or directional
- key comparative edges
- any fallback or partial-data caveat

Examples:
- “Recent attacking edge slightly increased aggressive branch preference.”
- “No external context applied; ranking based only on play-state analysis.”
- “Context was partial; neutral defaults were used for missing values.”

---

## Viewer Design

### Match Context Panel
Add a minimal panel showing:
- home vs away teams
- competition / season
- lookback sample size
- comparative edges
- cache status
- 2–3 short notes

### Rendering Constraints
- the panel must be optional
- no-context rendering must remain unchanged except for empty/omitted panel logic
- visual layout must not break existing viewer composition

---

## Testing Strategy

### Unit Tests
- MatchContext serialization and validation
- adapter contract behavior
- cache read/write/TTL logic
- context enricher deterministic outputs

### Integration Tests
- pipeline execution with context
- pipeline execution without context
- report contents
- viewer rendering with and without context

### Regression Tests
- no-context baseline remains stable
- context integration does not silently alter output schemas

### Fixture Strategy
Use deterministic fixture payloads instead of live network access.

---

## Risks

### Risk 1
Adapter scope creep into broad crawling.
#### Mitigation
Explicit contract requiring selected teams only.

### Risk 2
Context silently changing ranking behavior.
#### Mitigation
Report + explainability + regression tests.

### Risk 3
Cache inconsistency or stale data confusion.
#### Mitigation
TTL + cache status visibility.

### Risk 4
Missing or partial external data causing brittle logic.
#### Mitigation
Neutral defaults + explanatory notes.

---

## Definition of Done
The implementation is complete when:
1. MatchContext exists and serializes cleanly.
2. soccerdata adapter fetches only explicitly selected teams.
3. file-based cache works with TTL and status reporting.
4. context enricher returns deterministic signals.
5. pipeline supports optional context without breaking no-context behavior.
6. PipelineReport includes context sections.
7. Viewer 2D shows a minimal context panel.
8. tests and regressions pass without requiring live external fetches.
