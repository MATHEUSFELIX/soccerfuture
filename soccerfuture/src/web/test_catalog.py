"""Test catalog for explainability.

Provides structured descriptions of test categories so non-builders
can understand what the test suite validates and why it matters.
"""

from __future__ import annotations

TEST_CATALOG: list[dict] = [
    {
        "id": "domain_models",
        "title": "Domain Models",
        "purpose": "Validates that core data contracts (PlayState, MatchContext, MatchPriors, VideoClip, TrackedState) serialize, deserialize, and validate correctly.",
        "why_it_matters": "If data contracts break, every downstream module receives corrupted inputs.",
        "examples": [
            "PlayState round-trip serialization",
            "MatchContext accepts valid data",
            "MatchPriors rejects out-of-range values",
            "TrackedState handles partial entities",
        ],
        "test_paths": ["tests/domain/", "tests/models/"],
    },
    {
        "id": "pipeline",
        "title": "Pipeline",
        "purpose": "Validates that the tactical engine generates, scores, and ranks branches correctly.",
        "why_it_matters": "This is the core product — if ranking is wrong, analysis is wrong.",
        "examples": [
            "Branch generation produces N branches",
            "Gating rejects physically impossible branches",
            "Composite scoring weights validity and opportunity",
            "Top-K selection is deterministic",
        ],
        "test_paths": ["tests/scoring/", "tests/generation/", "tests/test_pipeline*.py"],
    },
    {
        "id": "context_and_priors",
        "title": "Context and Priors",
        "purpose": "Validates that match context and priors influence ranking in a bounded, explainable way.",
        "why_it_matters": "Prevents external information from silently dominating play-state evidence.",
        "examples": [
            "Low-confidence priors are suppressed",
            "Adjustments are clamped to safe bounds",
            "Tri-mode comparison detects incremental value",
            "Baseline remains stable without context",
        ],
        "test_paths": ["tests/services/test_context_enricher.py", "tests/services/test_scenario_policy.py", "tests/test_priors_regression.py"],
    },
    {
        "id": "viewer",
        "title": "Viewer",
        "purpose": "Validates that pipeline results render visually without breaking layout.",
        "why_it_matters": "Analysts need to inspect outputs visually, not just read JSON.",
        "examples": [
            "Field renders with correct dimensions",
            "Branch trajectories display correctly",
            "Context panel shows when context is present",
            "Priors panel shows when priors are present",
        ],
        "test_paths": ["tests/viewer/"],
    },
    {
        "id": "video_to_state",
        "title": "Video-to-State",
        "purpose": "Validates that video/tracking data converts into usable PlayState objects.",
        "why_it_matters": "This is the bridge between real-world footage and tactical simulation.",
        "examples": [
            "Tracking fixture converts to PlayState",
            "Incomplete payload generates alerts",
            "Rejected input never enters pipeline",
            "Builder notes expose assumptions",
        ],
        "test_paths": ["tests/domain/test_video_clip.py", "tests/domain/test_tracked_state.py", "tests/services/test_video_state_builder.py"],
    },
    {
        "id": "runtime_ingestion",
        "title": "Runtime Ingestion",
        "purpose": "Validates handling of imperfect, dirty, or incomplete real-world payloads.",
        "why_it_matters": "Real data is rarely clean — the system must handle noise gracefully.",
        "examples": [
            "Schema detection identifies payload version",
            "Normalizer fixes field name aliases",
            "Quality assessor grades payloads deterministically",
            "Rejected payloads are stored but never processed",
        ],
        "test_paths": ["tests/integrations/test_commentator_schema_registry.py", "tests/integrations/test_commentator_payload_normalizer.py", "tests/runtime/"],
    },
    {
        "id": "workflow_and_review",
        "title": "Workflow and Review",
        "purpose": "Validates that the system generates complete bundles, summaries, and review materials.",
        "why_it_matters": "Without structured review, the system is a black box to stakeholders.",
        "examples": [
            "Single-scenario workflow produces all artifacts",
            "Batch mode generates per-scenario bundles",
            "Review packs summarize bundles concisely",
            "Readiness classification is deterministic",
        ],
        "test_paths": ["tests/workflows/", "tests/review/"],
    },
    {
        "id": "governance_and_observability",
        "title": "Governance and Observability",
        "purpose": "Validates traceability, logging, metrics, and policy enforcement.",
        "why_it_matters": "Helps answer 'why did the system decide this?' and 'is this run trustworthy?'",
        "examples": [
            "Provenance records track full lineage",
            "Policy checks block rejected inputs",
            "Audit report summarizes decisions",
            "Structured logs are machine-readable",
        ],
        "test_paths": ["tests/governance/"],
    },
    {
        "id": "api_and_cli",
        "title": "API and CLI",
        "purpose": "Validates that the product is operable through commands and endpoints.",
        "why_it_matters": "Even a great engine fails as a product if nobody can use it.",
        "examples": [
            "Workflow submit endpoint processes scenarios",
            "Status endpoint returns run state",
            "Feedback endpoint persists reviews",
            "CLI commands route correctly",
        ],
        "test_paths": ["tests/api/", "tests/cli_app/"],
    },
    {
        "id": "pilot_evaluation",
        "title": "Pilot Evaluation",
        "purpose": "Validates structured pilot execution and evidence-based reporting.",
        "why_it_matters": "Pilots determine whether the product is ready for broader adoption.",
        "examples": [
            "Pilot plan validates required fields",
            "Metrics compute readiness rates",
            "Report separates observations from recommendations",
            "Success criteria are evaluated deterministically",
        ],
        "test_paths": ["tests/pilot/"],
    },
]


def get_test_catalog() -> list[dict]:
    """Return the full test catalog."""
    return TEST_CATALOG


def get_catalog_summary() -> dict:
    """Return a summary of the test catalog.

    Returns:
        Dict with total categories and category names.
    """
    return {
        "total_categories": len(TEST_CATALOG),
        "categories": [c["title"] for c in TEST_CATALOG],
    }
