"""Audit report generation.

Produces a Markdown audit report summarizing run lineage, policy
decisions, and artifact provenance for governance review.
"""

from __future__ import annotations

from src.governance.policy_checks import PolicyEvaluation
from src.governance.provenance import ProvenanceRecord


def generate_audit_report(
    provenance_records: list[ProvenanceRecord],
    policy_evaluations: list[PolicyEvaluation] | None = None,
) -> str:
    """Generate a Markdown audit report.

    Args:
        provenance_records: List of provenance records for all runs.
        policy_evaluations: Optional list of policy evaluations (parallel to provenance).

    Returns:
        Complete Markdown audit report string.
    """
    lines: list[str] = []
    lines.append("# Audit Report")
    lines.append("")

    total = len(provenance_records)
    lines.append(f"**Total runs audited:** {total}")
    lines.append("")

    # Summary counts
    blocked_count = 0
    warned_count = 0
    if policy_evaluations:
        blocked_count = sum(1 for pe in policy_evaluations if pe.blocked)
        warned_count = sum(1 for pe in policy_evaluations if pe.overall_outcome == "warn")

    lines.append(f"- Blocked: {blocked_count}")
    lines.append(f"- Warned: {warned_count}")
    lines.append(f"- Clean: {total - blocked_count - warned_count}")
    lines.append("")

    # Per-run details
    lines.append("## Run Details")
    lines.append("")

    for i, prov in enumerate(provenance_records):
        lines.append(f"### {prov.scenario_id} ({prov.run_id})")
        lines.append("")
        lines.append(f"- **Input:** {prov.input_source} ({prov.input_type})")
        lines.append(f"- **Extraction:** {'Yes' if prov.extraction_applied else 'No'}")
        lines.append(f"- **Context:** {'Yes' if prov.context_applied else 'No'}")
        lines.append(f"- **Priors:** {'Yes' if prov.priors_applied else 'No'}")
        lines.append(f"- **Artifacts:** {', '.join(prov.artifacts_produced) or '—'}")

        if policy_evaluations and i < len(policy_evaluations):
            pe = policy_evaluations[i]
            lines.append(f"- **Policy outcome:** {pe.overall_outcome}")
            if pe.warnings:
                for w in pe.warnings:
                    lines.append(f"  - ⚠ {w}")

        if prov.notes:
            for note in prov.notes:
                lines.append(f"  - {note}")
        lines.append("")

    return "\n".join(lines)
