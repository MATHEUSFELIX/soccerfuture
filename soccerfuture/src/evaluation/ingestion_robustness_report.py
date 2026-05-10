"""Ingestion robustness report generation.

Produces a Markdown report summarizing how well the ingestion layer
handles a set of dirty and clean fixture payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.services.extraction_diagnostics import ExtractionDiagnostics


@dataclass
class IngestionRobustnessReport:
    """Aggregate report on ingestion robustness across multiple payloads.

    Attributes:
        total_payloads: Total number of payloads tested.
        accepted_count: Number accepted (good + acceptable + poor).
        rejected_count: Number rejected.
        good_count: Number graded "good".
        acceptable_count: Number graded "acceptable".
        poor_count: Number graded "poor".
        avg_player_count: Average player count across accepted payloads.
        avg_confidence: Average confidence across accepted payloads.
        common_warnings: Most frequent warnings.
        common_rejection_reasons: Most frequent rejection reasons.
        notes: Summary notes.
    """

    total_payloads: int
    accepted_count: int
    rejected_count: int
    good_count: int
    acceptable_count: int
    poor_count: int
    avg_player_count: float
    avg_confidence: float
    common_warnings: list[str] = field(default_factory=list)
    common_rejection_reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def compute_ingestion_robustness(
    diagnostics_list: list[ExtractionDiagnostics],
) -> IngestionRobustnessReport:
    """Compute aggregate ingestion robustness metrics.

    Args:
        diagnostics_list: List of per-payload diagnostics.

    Returns:
        An IngestionRobustnessReport with aggregate metrics.
    """
    if not diagnostics_list:
        return IngestionRobustnessReport(
            total_payloads=0,
            accepted_count=0,
            rejected_count=0,
            good_count=0,
            acceptable_count=0,
            poor_count=0,
            avg_player_count=0.0,
            avg_confidence=0.0,
            notes=["No payloads to evaluate."],
        )

    total = len(diagnostics_list)
    rejected_count = sum(1 for d in diagnostics_list if d.rejected)
    accepted = [d for d in diagnostics_list if not d.rejected]
    accepted_count = len(accepted)

    good_count = sum(1 for d in diagnostics_list if d.quality_grade == "good")
    acceptable_count = sum(1 for d in diagnostics_list if d.quality_grade == "acceptable")
    poor_count = sum(1 for d in diagnostics_list if d.quality_grade == "poor")

    avg_player_count = 0.0
    avg_confidence = 0.0
    if accepted:
        avg_player_count = round(sum(d.player_count for d in accepted) / len(accepted), 2)
        avg_confidence = round(sum(d.avg_confidence for d in accepted) / len(accepted), 4)

    # Common warnings
    from collections import Counter
    warning_counter: Counter = Counter()
    for d in diagnostics_list:
        for w in d.warnings:
            warning_counter[w] += 1
    common_warnings = [w for w, _ in warning_counter.most_common(5)]

    # Common rejection reasons
    rejection_counter: Counter = Counter()
    for d in diagnostics_list:
        if d.rejected and d.rejection_reason:
            rejection_counter[d.rejection_reason] += 1
    common_rejection_reasons = [r for r, _ in rejection_counter.most_common(5)]

    notes = [
        f"Tested {total} payload(s): {accepted_count} accepted, {rejected_count} rejected.",
    ]

    return IngestionRobustnessReport(
        total_payloads=total,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        good_count=good_count,
        acceptable_count=acceptable_count,
        poor_count=poor_count,
        avg_player_count=avg_player_count,
        avg_confidence=avg_confidence,
        common_warnings=common_warnings,
        common_rejection_reasons=common_rejection_reasons,
        notes=notes,
    )


def render_robustness_report_markdown(
    report: IngestionRobustnessReport,
) -> str:
    """Render the ingestion robustness report as Markdown.

    Args:
        report: The computed robustness report.

    Returns:
        Markdown string.
    """
    lines: list[str] = []
    lines.append("# Ingestion Robustness Report")
    lines.append("")
    lines.append(f"- **Total payloads tested:** {report.total_payloads}")
    lines.append(f"- **Accepted:** {report.accepted_count}")
    lines.append(f"- **Rejected:** {report.rejected_count}")
    lines.append(f"- **Good:** {report.good_count}")
    lines.append(f"- **Acceptable:** {report.acceptable_count}")
    lines.append(f"- **Poor:** {report.poor_count}")
    lines.append(f"- **Avg player count (accepted):** {report.avg_player_count}")
    lines.append(f"- **Avg confidence (accepted):** {report.avg_confidence}")
    lines.append("")

    if report.common_warnings:
        lines.append("## Common Warnings")
        lines.append("")
        for w in report.common_warnings:
            lines.append(f"- {w}")
        lines.append("")

    if report.common_rejection_reasons:
        lines.append("## Common Rejection Reasons")
        lines.append("")
        for r in report.common_rejection_reasons:
            lines.append(f"- {r}")
        lines.append("")

    return "\n".join(lines)
