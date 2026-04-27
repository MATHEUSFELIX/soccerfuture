# Tasks

- [ ] Create `src/domain/match_context.py` with:
  - `MatchContext`
  - `TeamContextMetrics`
  - `ComparativeSignals`
  - `ContextSignals`
  - serialization and validation support

- [ ] Add unit tests for `match_context.py` covering:
  - round-trip serialization
  - required field validation
  - optional field defaults
  - invalid payload failures

- [ ] Create `src/integrations/soccerdata_adapter.py` with targeted API:
  - `get_match_context(home_team, away_team, competition=None, season=None, lookback_matches=10, use_cache=True)`

- [ ] Ensure the adapter fetches context only for explicitly selected teams

- [ ] Ensure the adapter never performs broad crawling or automatic team discovery

- [ ] Create deterministic fixture-based adapter tests with no live network dependency

- [ ] Create `src/integrations/soccerdata_cache.py` with:
  - deterministic cache key generation
  - file-based storage
  - TTL handling
  - cache hit/miss status reporting
  - optional cache bypass

- [ ] Add cache tests covering:
  - write/read round-trip
  - TTL expiry
  - cache miss behavior
  - bypass behavior

- [ ] Create `src/services/context_enricher.py` to derive deterministic `ContextSignals` from `MatchContext`

- [ ] Add tests for context enrichment covering:
  - neutral defaults
  - comparative edges
  - partial-data handling
  - note generation

- [ ] Extend the pipeline to accept optional match context

- [ ] Ensure no-context pipeline behavior remains stable

- [ ] Add telemetry fields for:
  - context requested
  - context applied
  - cache status
  - source
  - fetch timing if available

- [ ] Extend `pipeline_report.py` to include:
  - `match_context`
  - `context_signals`

- [ ] Extend `explainability.py` to include context-aware notes and no-context notes

- [ ] Extend `viewer_2d.py` with a minimal optional Match Context panel

- [ ] Add Viewer tests for:
  - rendering with context
  - rendering without context
  - panel layout stability

- [ ] Add integration tests for:
  - pipeline with context
  - pipeline without context
  - report schema stability

- [ ] Add regression tests confirming that no-context execution preserves prior baseline behavior

- [ ] Add deterministic fixture data under `data/fixtures/soccerdata/`

- [ ] Document the targeted match-context workflow in the README
