# Test Explainability

This document explains what each test category validates and why it matters for product quality.

## Domain Models
**Purpose:** Validates that core data contracts (PlayState, MatchContext, MatchPriors, VideoClip, TrackedState) serialize, deserialize, and validate correctly.

**Why it matters:** If data contracts break, every downstream module receives corrupted inputs.

**Examples:**
- PlayState round-trip serialization
- MatchContext accepts valid data
- MatchPriors rejects out-of-range values
- TrackedState handles partial entities

---

## Pipeline
**Purpose:** Validates that the tactical engine generates, scores, and ranks branches correctly.

**Why it matters:** This is the core product — if ranking is wrong, analysis is wrong.

**Examples:**
- Branch generation produces N branches
- Gating rejects physically impossible branches
- Composite scoring weights validity and opportunity
- Top-K selection is deterministic

---

## Context and Priors
**Purpose:** Validates that match context and priors influence ranking in a bounded, explainable way.

**Why it matters:** Prevents external information from silently dominating play-state evidence.

**Examples:**
- Low-confidence priors are suppressed
- Adjustments are clamped to safe bounds
- Tri-mode comparison detects incremental value
- Baseline remains stable without context

---

## Viewer
**Purpose:** Validates that pipeline results render visually without breaking layout.

**Why it matters:** Analysts need to inspect outputs visually, not just read JSON.

**Examples:**
- Field renders with correct dimensions
- Branch trajectories display correctly
- Context panel shows when context is present
- Priors panel shows when priors are present

---

## Video-to-State
**Purpose:** Validates that video/tracking data converts into usable PlayState objects.

**Why it matters:** This is the bridge between real-world footage and tactical simulation.

**Examples:**
- Tracking fixture converts to PlayState
- Incomplete payload generates alerts
- Rejected input never enters pipeline
- Builder notes expose assumptions

---

## Runtime Ingestion
**Purpose:** Validates handling of imperfect, dirty, or incomplete real-world payloads.

**Why it matters:** Real data is rarely clean — the system must handle noise gracefully.

**Examples:**
- Schema detection identifies payload version
- Normalizer fixes field name aliases
- Quality assessor grades payloads deterministically
- Rejected payloads are stored but never processed

---

## Workflow and Review
**Purpose:** Validates that the system generates complete bundles, summaries, and review materials.

**Why it matters:** Without structured review, the system is a black box to stakeholders.

**Examples:**
- Single-scenario workflow produces all artifacts
- Batch mode generates per-scenario bundles
- Review packs summarize bundles concisely
- Readiness classification is deterministic

---

## Governance and Observability
**Purpose:** Validates traceability, logging, metrics, and policy enforcement.

**Why it matters:** Helps answer "why did the system decide this?" and "is this run trustworthy?"

**Examples:**
- Provenance records track full lineage
- Policy checks block rejected inputs
- Audit report summarizes decisions
- Structured logs are machine-readable

---

## API and CLI
**Purpose:** Validates that the product is operable through commands and endpoints.

**Why it matters:** Even a great engine fails as a product if nobody can use it.

**Examples:**
- Workflow submit endpoint processes scenarios
- Status endpoint returns run state
- Feedback endpoint persists reviews
- CLI commands route correctly

---

## Pilot Evaluation
**Purpose:** Validates structured pilot execution and evidence-based reporting.

**Why it matters:** Pilots determine whether the product is ready for broader adoption.

**Examples:**
- Pilot plan validates required fields
- Metrics compute readiness rates
- Report separates observations from recommendations
- Success criteria are evaluated deterministically
