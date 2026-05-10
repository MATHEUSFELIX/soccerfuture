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

## Match Priors Integration

The pipeline supports optional match-level priors derived from MatchPredict signals. Priors provide macro match expectations (aggression, risk, tempo, goal expectation, pressure) that lightly refine branch ranking without overpowering play-state evidence.

### Fetching Priors

Use `get_match_priors` to retrieve priors for two named teams:

```python
from src.integrations.matchpredict_adapter import get_match_priors

priors = get_match_priors(
    home_team="FC Porto",
    away_team="SL Benfica",
    competition="Primeira Liga",
    season="2024",
    use_fixtures=True,  # deterministic fixture mode for tests
)
```

When no fixture or data source is available, the adapter returns safe-default fallback priors with `fallback_used=True` and low confidence.

### Passing Priors to the Pipeline

Pass `MatchPriors` as an optional argument alongside context:

```python
from src.pipeline import run_pipeline, PipelineConfig

report = run_pipeline(
    play_state,
    PipelineConfig(),
    match_context=ctx,       # optional
    match_priors=priors,     # optional
)
```

When `match_priors` is `None` (the default), the pipeline behaves exactly as before — priors are fully optional.

### How Priors Influence Ranking

Priors are translated into bounded `ScenarioPolicySignals` by the scenario policy service:

- Each prior dimension's deviation from neutral (0.5) is scaled by confidence and clamped to ±0.15.
- Tie-break bias is clamped to ±0.10.
- When confidence is below 0.3, all adjustments are suppressed to zero.
- Influence level is classified as "none", "light", or "moderate".

Priors never replace core play-state scoring — they only slightly shift branch preference and help resolve close alternatives.

### What the Report Includes

When priors are provided, the `PipelineReport` includes:

- `match_priors`: Serialized `MatchPriors` dict.
- `scenario_policy_signals`: Derived `ScenarioPolicySignals` dict (adjustments, tie-break bias, influence level, notes).
- `metadata["priors_requested"]`: `True` when priors were passed.
- `metadata["priors_applied"]`: `True` when signals were derived.
- `metadata["priors_source"]`: Source identifier (e.g. "matchpredict").
- `metadata["priors_confidence"]`: Confidence value (0.0–1.0).
- `metadata["priors_influence_level"]`: "none", "light", or "moderate".

### Tri-Mode Evaluation

Compare pipeline output across three modes to measure the incremental value of priors:

```python
from src.evaluation.context_impact_analysis import run_tri_mode_analysis

result = run_tri_mode_analysis(
    play_state, match_context, match_priors, scenario_id="demo",
)
```

This runs the pipeline three times (baseline, context only, context + priors) and reports top-1/top-3 changes, score deltas, and influence classification.

### Visualization

When priors are present, the 2D viewer adds a compact priors panel showing prior values, confidence, influence level, and derived notes. The panel is separate from the match context panel to keep play-state evidence, context, and priors visually distinct.

## Video-to-State Integration

The pipeline supports video-derived PlayState inputs through a fixture-first ingestion layer. Real or commentator-derived tracking data can be converted into PlayState objects and evaluated by the existing pipeline.

### Loading Tracking Data

Use the commentator adapter to load fixture-based tracking data:

```python
from src.integrations.commentator_adapter import get_tracked_state

tracked = get_tracked_state("sample_clip_01", use_fixtures=True)
```

This returns a `TrackedState` containing player positions, ball positions, clip reference, frame rate, and data gaps (low-confidence intervals).

### Building PlayState from Tracking

Convert tracked data into a pipeline-compatible PlayState:

```python
from src.services.video_state_builder import build_play_state

play_state = build_play_state(
    tracked,
    decision_point_timestamp=10.0,
    possession_team="Team A",
    match_time=35.0,
    game_phase="open_play",
)
```

The builder selects the closest player/ball positions to the decision point, flags low-confidence players in metadata, and preserves clip traceability.

### Running the Full Video Pipeline

Use `run_video_pipeline` for the complete flow (tracking → PlayState → pipeline evaluation):

```python
from src.services.video_pipeline_eval import run_video_pipeline

result = run_video_pipeline(
    clip=tracked.clip_reference,
    tracked=tracked,
    decision_point_timestamp=10.0,
)
# result.play_state — the extracted PlayState
# result.pipeline_report — full PipelineReport
# result.errors — any conversion or pipeline errors
# result.metadata — execution timing, fixture_mode flag
```

### Domain Models

- `VideoClip`: Source clip metadata (path, start/end time, source info).
- `TrackedState`: Player positions, ball positions, data gaps, clip reference.
- `VideoPipelineResult`: Complete result with clip, PlayState, report, errors, metadata.

### Fixture Data

Deterministic fixtures are stored in `data/fixtures/commentator/`:
- `sample_clip_01.json` — minimal 2-player tracking
- `sample_clip_02.json` — full 11-player tracking with low-confidence entries

No live inference or GPU dependencies are required for tests.

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

## Stakeholder Review and Demo Hardening

The project includes a review layer for preparing scenarios for stakeholder demos and capturing structured feedback.

### Review Packs

Generate concise stakeholder-facing review packs from existing scenario bundles:

```python
from src.review.review_pack import generate_review_pack

pack = generate_review_pack("output/runs/scenario_001")
# pack.top_branches — top-ranked branch summaries
# pack.summary_text — analyst summary content
# pack.run_status — overall workflow status
```

### Demo Readiness

Evaluate whether a bundle is ready for stakeholder presentation:

```python
from src.review.demo_readiness import evaluate_readiness

result = evaluate_readiness("output/runs/scenario_001")
# result.label — "ready", "partially_ready", or "not_ready"
# result.checks_passed / result.checks_failed
# result.reasons — why it's not ready
```

Checks include: summary present, viewer artifact present, top-1 branch present, no critical failure, source metadata present, confidence info present.

### Structured Feedback

Capture reviewer feedback using a structured schema:

```python
from src.review.review_feedback_schema import ReviewFeedback
from src.review.review_feedback_ingest import ingest_feedback

feedback = [
    ReviewFeedback(
        scenario_id="s1", reviewer_id="analyst_1",
        top_1_plausibility="yes", top_3_usefulness="partially",
        summary_clarity=4, confidence_sufficiency=3,
        blockers=["needs real tracking data"],
    ),
]
aggregate = ingest_feedback(feedback)
```

### Stakeholder Report

Generate a Markdown report combining readiness and feedback:

```python
from src.review.stakeholder_report import generate_stakeholder_report

report = generate_stakeholder_report(readiness_results, feedback_aggregate=aggregate)
```

The report includes review coverage, readiness distribution, strongest/weakest scenarios, blockers, requested improvements, and recommendations.

## Analyst Workflow and Demo Bundles

The project includes a workflow packaging layer that turns existing components into a repeatable analyst-facing flow.

### Single-Scenario Workflow

Run the full end-to-end workflow for one scenario:

```python
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig
from src.workflows.analyst_workflow_runner import run_analyst_workflow

manifest = run_analyst_workflow(
    scenario_id="counter_attack_01",
    play_state=play_state,
    source_type="structured",
    output_root="output/runs",
    pipeline_config=PipelineConfig(n=15, k=3, seed=42),
)
```

This produces a bundle directory with:
- `run_status.json` — machine-readable step statuses
- `input_reference.json` — input metadata
- `extracted_play_state.json` — the PlayState used
- `pipeline_report.json` — full pipeline output
- `viewer_artifact.json` — viewer rendering reference
- `analyst_summary.md` — concise analyst-facing summary

### Batch Demo Mode

Run multiple scenarios and generate an aggregate index:

```python
from src.workflows.batch_demo_runner import run_batch_demo

scenarios = [
    {"scenario_id": "s1", "play_state": play_state_1},
    {"scenario_id": "s2", "play_state": play_state_2},
]
manifests, index_entries = run_batch_demo(
    scenarios, output_root="output/runs",
)
```

This generates per-scenario bundles plus `demo_index.json` and `demo_index.md` for browsing results.

### Step-Level Status

Each workflow run records per-step status (load, extract, pipeline, report, viewer, summary). Partial failures are surfaced clearly — if the viewer fails but the report succeeds, the run is marked "partial" rather than "failed".

## Ingestion Hardening

The commentator/tracking ingestion boundary includes hardening layers for handling imperfect payloads safely.

### Schema Detection

Detect payload schema version and validate structure:

```python
from src.integrations.commentator_schema_registry import detect_schema_version

result = detect_schema_version(raw_payload)
# result.version — "v1" or "unknown"
# result.compatible — whether ingestion can proceed
# result.errors / result.warnings
```

### Payload Normalization

Normalize field names, coerce types, and apply safe defaults:

```python
from src.integrations.commentator_payload_normalizer import normalize_payload

norm = normalize_payload(raw_payload)
# norm.payload — canonical v1 format
# norm.applied_fixes — what was changed
# norm.rejected — whether payload is unusable
```

Handles aliases (`id` → `player_id`, `clip` → `clip_reference`), string-to-float coercion, and missing confidence defaults.

### Quality Assessment

Grade normalized payloads on a deterministic scale:

```python
from src.services.input_quality_assessor import assess_quality

assessment = assess_quality(normalized_payload)
# assessment.grade — "good", "acceptable", "poor", or "rejected"
# assessment.player_count, assessment.avg_player_confidence
# assessment.issues — quality concerns
```

### Extraction Diagnostics

Combine all checks into a single machine-readable record:

```python
from src.services.extraction_diagnostics import build_diagnostics

diag = build_diagnostics("scenario_01", schema_result, norm_result, quality_result)
# diag.rejected, diag.quality_grade, diag.warnings, diag.errors
```

### Ingestion Robustness Report

Aggregate diagnostics across multiple payloads:

```python
from src.evaluation.ingestion_robustness_report import compute_ingestion_robustness

report = compute_ingestion_robustness(diagnostics_list)
# report.accepted_count, report.rejected_count
# report.common_warnings, report.common_rejection_reasons
```

## Project Structure

```
src/
  domain/           # Domain models (MatchContext, MatchPriors, VideoClip, TrackedState)
  evaluation/       # Human eval protocol, robustness suite, trust report, tri-mode analysis
  integrations/     # Soccerdata adapter, MatchPredict adapter, commentator adapter, cache
  models/           # Pipeline report, play state, branch models
  review/           # Stakeholder review packs, feedback, readiness, index, report
  scoring/          # Validity, opportunity, gating scoring modules
  services/         # Context enricher, scenario policy, video state builder
  viewer/           # 2D visualization
  workflows/        # Analyst workflow runner, batch demo, scenario bundles, demo index
  utils/            # Shared constants and helpers
scripts/            # CLI entry points (trust_eval.py, render_viewer.py, etc.)
tests/              # Unit, integration, and regression tests
data/               # Play states, fixtures (soccerdata, matchpredict, commentator), benchmarks
```
