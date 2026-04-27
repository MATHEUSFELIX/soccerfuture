# Requirements

## Overview
Add targeted, lazy, cached match-context integration using soccerdata so the app can enrich play analysis with selected-team context only.

The integration must remain optional and must not break the current pipeline baseline.

---

## User Story 1
As a developer,
I want a normalized MatchContext model,
so that all external context enters the app through a stable contract.

### Acceptance Criteria
1. The system defines a MatchContext model with:
   - home_team
   - away_team
   - competition
   - season
   - lookback_matches
   - source
   - cache_status
   - home_metrics
   - away_metrics
   - comparative_signals
   - fetched_at
2. The model supports round-trip serialization.
3. The model validates required fields and uses safe defaults for optional fields.
4. Invalid or incomplete payloads fail clearly.

---

## User Story 2
As a developer,
I want a targeted soccerdata adapter,
so that the system fetches only the teams I explicitly choose.

### Acceptance Criteria
1. The adapter exposes a function with explicit team selection inputs.
2. The adapter never crawls full leagues or broad datasets by default.
3. The adapter never fetches context unless home_team and away_team are explicitly provided.
4. The adapter returns a normalized MatchContext object.
5. The adapter surfaces clear errors when required upstream data is unavailable.

---

## User Story 3
As a developer,
I want local caching for match context,
so that repeated requests do not trigger unnecessary data fetches.

### Acceptance Criteria
1. The system stores cache entries using a deterministic cache key.
2. The cache records:
   - cache key
   - fetch timestamp
   - source metadata
3. The cache supports TTL-based invalidation.
4. The adapter can bypass cache when explicitly requested.
5. The resulting MatchContext exposes cache hit/miss status.

---

## User Story 4
As a developer,
I want deterministic context enrichment,
so that external team context can influence analysis without introducing opaque model behavior.

### Acceptance Criteria
1. The system includes a context enricher that transforms MatchContext into pipeline-ready context signals.
2. The context enricher uses deterministic rules only in this phase.
3. The context enricher works even when some metrics are missing.
4. The output includes explicit notes explaining derived signals.

---

## User Story 5
As a developer,
I want the pipeline to support optional match context,
so that the app can run both with and without external context.

### Acceptance Criteria
1. The pipeline accepts MatchContext as an optional input.
2. When no context is provided, baseline pipeline behavior remains stable.
3. When context is provided, the pipeline records that context was used.
4. Context integration must not silently alter output contracts.

---

## User Story 6
As an analyst,
I want reports to show what external context was used,
so that I can understand whether ranking was affected by team-level information.

### Acceptance Criteria
1. PipelineReport includes a match_context section.
2. PipelineReport includes a context_signals section.
3. The report explicitly shows:
   - source
   - cache status
   - selected teams
   - lookback window
4. Explainability includes context-aware notes when relevant.
5. If no context is present, the report states that ranking was based only on play-state analysis.

---

## User Story 7
As an analyst,
I want the Viewer 2D to display basic match context,
so that I can visually inspect team-level priors alongside branch ranking.

### Acceptance Criteria
1. The Viewer 2D includes a minimal Match Context panel.
2. The panel shows:
   - home and away teams
   - competition / season when available
   - sample size
   - key comparative edges
   - cache hit/miss
3. The Viewer still renders correctly when no context is provided.
4. The Viewer tests validate both with-context and no-context rendering.

---

## User Story 8
As a maintainer,
I want deterministic fixtures and regression tests,
so that context integration can evolve without destabilizing the system.

### Acceptance Criteria
1. The system includes deterministic soccerdata fixtures for tests.
2. Tests cover:
   - MatchContext schema
   - soccerdata adapter
   - cache
   - context enricher
   - pipeline integration
   - PipelineReport output
   - Viewer rendering
3. Regression tests confirm that no-context execution preserves prior baseline behavior.
4. No live network dependency is required for automated tests.

---

## Non-Goals
This phase does not include:
- full-league crawling
- automatic team discovery
- MatchPredict integration
- video ingestion integration
- learned priors
- LLM-based context generation
- broad historical warehouse creation
