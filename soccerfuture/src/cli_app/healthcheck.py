"""System health check for the Football Tactical OS.

Validates environment, fixtures, and module availability.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class HealthCheckResult:
    """Result of a system health check.

    Attributes:
        status: Overall status ("ok", "warning", "error").
        checks: List of individual check results.
        notes: Summary notes.
    """

    status: str
    checks: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def run_healthcheck() -> HealthCheckResult:
    """Run system health checks.

    Checks:
      - Play states directory exists and has files
      - Commentator fixtures exist
      - Core modules importable
      - Output directory writable

    Returns:
        A HealthCheckResult with status and details.
    """
    checks: list[dict] = []
    issues: list[str] = []

    # Check play states
    ps_dir = "data/play_states"
    if os.path.isdir(ps_dir):
        count = len([f for f in os.listdir(ps_dir) if f.endswith(".json")])
        checks.append({"name": "play_states", "status": "ok", "detail": f"{count} files"})
    else:
        checks.append({"name": "play_states", "status": "error", "detail": "Directory not found"})
        issues.append("Play states directory missing")

    # Check commentator fixtures
    cf_dir = "data/fixtures/commentator"
    if os.path.isdir(cf_dir):
        count = len([f for f in os.listdir(cf_dir) if f.endswith(".json")])
        checks.append({"name": "commentator_fixtures", "status": "ok", "detail": f"{count} files"})
    else:
        checks.append({"name": "commentator_fixtures", "status": "warning", "detail": "Directory not found"})
        issues.append("Commentator fixtures missing")

    # Check core imports
    try:
        from src.pipeline import run_pipeline  # noqa: F401
        checks.append({"name": "pipeline_import", "status": "ok", "detail": "importable"})
    except ImportError as e:
        checks.append({"name": "pipeline_import", "status": "error", "detail": str(e)})
        issues.append("Pipeline module not importable")

    # Check output directory
    out_dir = "output"
    try:
        os.makedirs(out_dir, exist_ok=True)
        checks.append({"name": "output_dir", "status": "ok", "detail": "writable"})
    except OSError as e:
        checks.append({"name": "output_dir", "status": "error", "detail": str(e)})
        issues.append("Output directory not writable")

    # Determine overall status
    statuses = {c["status"] for c in checks}
    if "error" in statuses:
        status = "error"
    elif "warning" in statuses:
        status = "warning"
    else:
        status = "ok"

    notes = [f"Ran {len(checks)} checks."]
    if issues:
        notes.append(f"Issues: {'; '.join(issues)}")

    return HealthCheckResult(status=status, checks=checks, notes=notes)
