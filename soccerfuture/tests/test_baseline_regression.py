"""Baseline regression tests driven by the benchmark manifest.

Compares current pipeline output against the frozen v1.0-baseline
expectations in ``data/benchmark_manifest.json``.  Each scenario is
parametrized so that failures pinpoint the exact scenario and metric
that drifted.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import json
from typing import Any

import pytest

from src.models.pipeline_report import PipelineReport
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig, run_pipeline
from src.utils.manifest import load_manifest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MANIFEST_PATH = "data/benchmark_manifest.json"
_PLAY_STATES_DIR = "data/play_states"

# ---------------------------------------------------------------------------
# Module-scoped fixtures — load manifest once, run pipeline once per scenario
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def manifest() -> dict:
    """Load and validate the benchmark manifest."""
    return load_manifest(_MANIFEST_PATH)


@pytest.fixture(scope="module")
def scenario_reports(manifest: dict) -> list[tuple[dict, PipelineReport]]:
    """Run the pipeline for every manifest scenario using the manifest's config.

    Returns a list of (scenario_dict, PipelineReport) pairs, one per
    scenario, in the same order as ``manifest["scenarios"]``.
    """
    cfg_data = manifest["pipeline_config"]
    config = PipelineConfig(
        n=cfg_data["n"],
        k=cfg_data["k"],
        seed=cfg_data["seed"],
        validity_weight=cfg_data["validity_weight"],
        opportunity_weight=cfg_data["opportunity_weight"],
    )

    results: list[tuple[dict, PipelineReport]] = []
    for scenario in manifest["scenarios"]:
        path = f"{_PLAY_STATES_DIR}/{scenario['scenario_file']}"
        with open(path) as f:
            ps = dict_to_play_state(json.load(f))
        report = run_pipeline(ps, config)
        results.append((scenario, report))
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scenario_ids(manifest_path: str = _MANIFEST_PATH) -> list[str]:
    """Return scenario_file names for parametrize IDs."""
    m = load_manifest(manifest_path)
    return [s["scenario_file"] for s in m["scenarios"]]


def _scenario_indices(manifest_path: str = _MANIFEST_PATH) -> list[int]:
    """Return scenario indices for parametrize."""
    m = load_manifest(manifest_path)
    return list(range(len(m["scenarios"])))


# Pre-load IDs so parametrize can label each case at collection time.
_IDS = _scenario_ids()
_INDICES = _scenario_indices()


# ---------------------------------------------------------------------------
# Parametrized regression tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("idx", _INDICES, ids=_IDS)
class TestBaselineRegression:
    """Manifest-driven regression tests for each scenario.

    Validates: Requirements 2.1, 2.2, 2.3, 2.4
    """

    def test_gating_pass_count_within_tolerance(
        self,
        idx: int,
        scenario_reports: list[tuple[dict, PipelineReport]],
    ) -> None:
        """The number of branches passing gating must be within ±2 of baseline.

        Validates: Requirements 2.1
        """
        scenario, report = scenario_reports[idx]
        expected = scenario["gating_pass_count"]
        actual = report.metadata["gating_pass_count"]

        assert abs(actual - expected) <= 2, (
            f"[{scenario['scenario_file']}] Gating pass count drifted beyond "
            f"tolerance. Expected: {expected} (±2), Actual: {actual}, "
            f"Drift: {actual - expected:+d}. "
            f"Metric: gating_pass_count"
        )

    def test_top_branch_score_within_tolerance(
        self,
        idx: int,
        scenario_reports: list[tuple[dict, PipelineReport]],
    ) -> None:
        """The top-ranked branch's composite score must be within ±0.05 of baseline.

        Validates: Requirements 2.2
        """
        scenario, report = scenario_reports[idx]
        expected = scenario["top_branch_min_score"]
        actual = report.ranked_branches[0].composite_score

        assert abs(actual - expected) <= 0.05, (
            f"[{scenario['scenario_file']}] Top branch composite score drifted "
            f"beyond tolerance. Expected: {expected:.6f} (±0.05), "
            f"Actual: {actual:.6f}, Drift: {actual - expected:+.6f}. "
            f"Metric: top_branch_composite_score"
        )

    def test_top_k_branch_ids_match_baseline(
        self,
        idx: int,
        scenario_reports: list[tuple[dict, PipelineReport]],
    ) -> None:
        """The top-K branch IDs must match the baseline exactly (same order).

        Validates: Requirements 2.3
        """
        scenario, report = scenario_reports[idx]
        expected_ids = [e["branch_id"] for e in scenario["expected_top_k"]]
        actual_ids = [rb.branch_id for rb in report.ranked_branches]

        assert actual_ids == expected_ids, (
            f"[{scenario['scenario_file']}] Top-K branch IDs do not match "
            f"baseline. Expected: {expected_ids}, Actual: {actual_ids}. "
            f"Metric: top_k_branch_ids"
        )
