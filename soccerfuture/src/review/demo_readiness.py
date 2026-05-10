"""Demo readiness classification for scenario bundles.

Evaluates each bundle against review-readiness checks and classifies
it as ready, partially_ready, or not_ready.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


VALID_READINESS_LABELS = {"ready", "partially_ready", "not_ready"}


@dataclass
class ReadinessResult:
    """Result of readiness evaluation for one scenario bundle.

    Attributes:
        scenario_id: Unique scenario identifier.
        label: One of "ready", "partially_ready", "not_ready".
        checks_passed: List of check names that passed.
        checks_failed: List of check names that failed.
        reasons: Human-readable reasons for non-readiness.
    """

    scenario_id: str
    label: str
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Readiness checks
# ---------------------------------------------------------------------------

REQUIRED_CHECKS = [
    "summary_present",
    "viewer_artifact_present",
    "top_1_branch_present",
    "no_critical_failure",
    "source_metadata_present",
    "confidence_info_present",
]


def _check_summary_present(bundle_path: str) -> bool:
    """Check if analyst_summary.md exists and is non-empty."""
    path = os.path.join(bundle_path, "analyst_summary.md")
    if not os.path.isfile(path):
        return False
    return os.path.getsize(path) > 0


def _check_viewer_artifact_present(bundle_path: str) -> bool:
    """Check if viewer_artifact.json exists."""
    return os.path.isfile(os.path.join(bundle_path, "viewer_artifact.json"))


def _check_top_1_branch_present(bundle_path: str) -> bool:
    """Check if pipeline_report.json has at least one ranked branch."""
    report_path = os.path.join(bundle_path, "pipeline_report.json")
    if not os.path.isfile(report_path):
        return False
    try:
        with open(report_path, "r", encoding="utf-8") as fh:
            report = json.load(fh)
        ranked = report.get("ranked_branches", [])
        return len(ranked) >= 1
    except (json.JSONDecodeError, OSError):
        return False


def _check_no_critical_failure(bundle_path: str) -> bool:
    """Check that run_status.json does not show overall 'failed'."""
    status_path = os.path.join(bundle_path, "run_status.json")
    if not os.path.isfile(status_path):
        return False
    try:
        with open(status_path, "r", encoding="utf-8") as fh:
            status = json.load(fh)
        return status.get("overall_status") != "failed"
    except (json.JSONDecodeError, OSError):
        return False


def _check_source_metadata_present(bundle_path: str) -> bool:
    """Check if input_reference.json exists."""
    return os.path.isfile(os.path.join(bundle_path, "input_reference.json"))


def _check_confidence_info_present(bundle_path: str) -> bool:
    """Check if pipeline_report.json has metadata with execution info."""
    report_path = os.path.join(bundle_path, "pipeline_report.json")
    if not os.path.isfile(report_path):
        return False
    try:
        with open(report_path, "r", encoding="utf-8") as fh:
            report = json.load(fh)
        metadata = report.get("metadata", {})
        return "execution_time_seconds" in metadata
    except (json.JSONDecodeError, OSError):
        return False


_CHECK_FUNCTIONS = {
    "summary_present": _check_summary_present,
    "viewer_artifact_present": _check_viewer_artifact_present,
    "top_1_branch_present": _check_top_1_branch_present,
    "no_critical_failure": _check_no_critical_failure,
    "source_metadata_present": _check_source_metadata_present,
    "confidence_info_present": _check_confidence_info_present,
}


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def evaluate_readiness(
    bundle_path: str,
    scenario_id: str | None = None,
) -> ReadinessResult:
    """Evaluate readiness of a scenario bundle for stakeholder demo.

    Classification rules:
      - **ready**: All checks pass.
      - **partially_ready**: At least 4 checks pass (including no_critical_failure).
      - **not_ready**: Fewer than 4 checks pass OR no_critical_failure fails.

    Args:
        bundle_path: Path to the scenario bundle directory.
        scenario_id: Override scenario_id (auto-detected from path if None).

    Returns:
        A ReadinessResult with label, passed/failed checks, and reasons.
    """
    sid = scenario_id or os.path.basename(bundle_path)
    passed: list[str] = []
    failed: list[str] = []
    reasons: list[str] = []

    for check_name in REQUIRED_CHECKS:
        check_fn = _CHECK_FUNCTIONS[check_name]
        if check_fn(bundle_path):
            passed.append(check_name)
        else:
            failed.append(check_name)
            reasons.append(f"Check failed: {check_name}")

    # Classification
    critical_ok = "no_critical_failure" in passed
    if not critical_ok:
        label = "not_ready"
    elif len(passed) == len(REQUIRED_CHECKS):
        label = "ready"
    elif len(passed) >= 4:
        label = "partially_ready"
    else:
        label = "not_ready"

    return ReadinessResult(
        scenario_id=sid,
        label=label,
        checks_passed=passed,
        checks_failed=failed,
        reasons=reasons,
    )
