"""Consolidated Markdown trust report combining human eval, robustness, and context impact results.

Reads the JSON dicts produced by each evaluation stream and renders a
single human-readable Markdown report with overview, per-stream summaries,
a deterministic trust assessment, recommendations, and an appendix.
"""

from __future__ import annotations

import datetime
import os


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _timestamp() -> str:
    """Return the current UTC timestamp in ISO-8601 format.

    Returns:
        ISO-8601 timestamp string.
    """
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _streams_present(
    human_eval_data: dict | None,
    robustness_data: dict | None,
    context_impact_data: dict | None,
) -> list[str]:
    """List which evaluation streams are included.

    Args:
        human_eval_data: Human evaluation summary dict or None.
        robustness_data: Robustness analysis dict or None.
        context_impact_data: Context impact analysis dict or None.

    Returns:
        List of stream name strings that are present.
    """
    streams: list[str] = []
    if human_eval_data is not None:
        streams.append("Human Evaluation")
    if robustness_data is not None:
        streams.append("Robustness")
    if context_impact_data is not None:
        streams.append("Context Impact")
    return streams


def _overview_section(
    human_eval_data: dict | None,
    robustness_data: dict | None,
    context_impact_data: dict | None,
    timestamp: str,
) -> str:
    """Render the overview section.

    Args:
        human_eval_data: Human evaluation summary dict or None.
        robustness_data: Robustness analysis dict or None.
        context_impact_data: Context impact analysis dict or None.
        timestamp: ISO-8601 generation timestamp.

    Returns:
        Markdown string for the overview section.
    """
    streams = _streams_present(human_eval_data, robustness_data, context_impact_data)
    stream_text = ", ".join(streams) if streams else "None"
    lines = [
        "## Overview",
        "",
        f"- **Generated at:** {timestamp}",
        f"- **Evaluation streams included:** {stream_text}",
    ]
    return "\n".join(lines)


def _human_eval_section(data: dict | None) -> str:
    """Render the Human Evaluation Summary section.

    Args:
        data: Human evaluation summary dict or None.

    Returns:
        Markdown string for the human evaluation section.
    """
    lines = ["## Human Evaluation Summary", ""]
    if data is None:
        lines.append("_Not available._")
        return "\n".join(lines)

    overall_avg = data.get("overall_avg", 0.0)
    scenario_count = data.get("scenario_count", 0)
    evaluator_count = data.get("evaluator_count", 0)
    category_averages = data.get("category_averages", {})
    notes = data.get("notes", [])

    lines.append(f"- **Overall average rating:** {overall_avg}")
    lines.append(f"- **Scenarios evaluated:** {scenario_count}")
    lines.append(f"- **Evaluators:** {evaluator_count}")
    lines.append("")

    if category_averages:
        lines.append("### Category Averages")
        lines.append("")
        lines.append("| Category | Average |")
        lines.append("|---|---|")
        for cat, avg in sorted(category_averages.items()):
            lines.append(f"| {cat} | {avg} |")
        lines.append("")

    if notes:
        lines.append("### Key Observations")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def _robustness_section(data: dict | None) -> str:
    """Render the Robustness Summary section.

    Args:
        data: Robustness analysis dict (with ``summary`` key) or None.

    Returns:
        Markdown string for the robustness section.
    """
    lines = ["## Robustness Summary", ""]
    if data is None:
        lines.append("_Not available._")
        return "\n".join(lines)

    summary = data.get("summary", data)
    robust_count = summary.get("robust_count", 0)
    sensitive_count = summary.get("sensitive_count", 0)
    fragile_count = summary.get("fragile_count", 0)
    avg_validity_delta = summary.get("avg_validity_delta", 0.0)
    avg_opportunity_delta = summary.get("avg_opportunity_delta", 0.0)
    per_strategy = summary.get("per_strategy_summary", {})
    notes = summary.get("notes", [])

    lines.append(f"- **Robust:** {robust_count}")
    lines.append(f"- **Sensitive:** {sensitive_count}")
    lines.append(f"- **Fragile:** {fragile_count}")
    lines.append(f"- **Avg validity delta:** {avg_validity_delta}")
    lines.append(f"- **Avg opportunity delta:** {avg_opportunity_delta}")
    lines.append("")

    if per_strategy:
        lines.append("### Per-Strategy Breakdown")
        lines.append("")
        lines.append("| Strategy | Robust | Sensitive | Fragile |")
        lines.append("|---|---|---|---|")
        for strategy, counts in sorted(per_strategy.items()):
            r = counts.get("robust", 0)
            s = counts.get("sensitive", 0)
            f = counts.get("fragile", 0)
            lines.append(f"| {strategy} | {r} | {s} | {f} |")
        lines.append("")

    if notes:
        lines.append("### Key Observations")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def _context_impact_section(data: dict | None) -> str:
    """Render the Context Impact Summary section.

    Args:
        data: Context impact analysis dict (with ``summary`` key) or None.

    Returns:
        Markdown string for the context impact section.
    """
    lines = ["## Context Impact Summary", ""]
    if data is None:
        lines.append("_Not available._")
        return "\n".join(lines)

    summary = data.get("summary", data)
    helped = summary.get("scenarios_helped", [])
    neutral = summary.get("scenarios_neutral", [])
    degraded = summary.get("scenarios_degraded", [])
    avg_validity_delta = summary.get("avg_validity_delta", 0.0)
    avg_opportunity_delta = summary.get("avg_opportunity_delta", 0.0)
    notes = summary.get("notes", [])

    lines.append(f"- **Helped:** {len(helped)}")
    lines.append(f"- **Neutral:** {len(neutral)}")
    lines.append(f"- **Degraded:** {len(degraded)}")
    lines.append(f"- **Avg validity delta:** {avg_validity_delta}")
    lines.append(f"- **Avg opportunity delta:** {avg_opportunity_delta}")
    lines.append("")

    if notes:
        lines.append("### Key Observations")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Trust assessment
# ---------------------------------------------------------------------------


def _compute_trust_level(
    human_eval_data: dict | None,
    robustness_data: dict | None,
) -> str:
    """Compute the deterministic trust level string.

    Rules:
      - High trust: human_eval overall_avg >= 3.5 AND robustness fragile_count == 0
      - Moderate trust: human_eval overall_avg >= 3.0 AND robustness fragile_count <= 2
      - Otherwise: Low trust — review recommended

    When a stream is missing, the condition for that stream is treated as
    satisfied (optimistic default), but a note is appended separately.

    Args:
        human_eval_data: Human evaluation summary dict or None.
        robustness_data: Robustness analysis dict or None.

    Returns:
        Trust level string.
    """
    overall_avg: float | None = None
    fragile_count: int | None = None

    if human_eval_data is not None:
        overall_avg = human_eval_data.get("overall_avg", 0.0)
    if robustness_data is not None:
        summary = robustness_data.get("summary", robustness_data)
        fragile_count = summary.get("fragile_count", 0)

    # Evaluate conditions with available data
    human_high = overall_avg is None or overall_avg >= 3.5
    human_moderate = overall_avg is None or overall_avg >= 3.0
    robust_high = fragile_count is None or fragile_count == 0
    robust_moderate = fragile_count is None or fragile_count <= 2

    if human_high and robust_high:
        return "High trust"
    if human_moderate and robust_moderate:
        return "Moderate trust"
    return "Low trust — review recommended"


def _missing_stream_notes(
    human_eval_data: dict | None,
    robustness_data: dict | None,
    context_impact_data: dict | None,
) -> list[str]:
    """Generate notes about missing evaluation streams.

    Args:
        human_eval_data: Human evaluation summary dict or None.
        robustness_data: Robustness analysis dict or None.
        context_impact_data: Context impact analysis dict or None.

    Returns:
        List of note strings for missing streams.
    """
    notes: list[str] = []
    if human_eval_data is None:
        notes.append("Assessment limited by missing Human Evaluation data.")
    if robustness_data is None:
        notes.append("Assessment limited by missing Robustness data.")
    if context_impact_data is None:
        notes.append("Assessment limited by missing Context Impact data.")
    return notes


def _trust_assessment_section(
    human_eval_data: dict | None,
    robustness_data: dict | None,
    context_impact_data: dict | None,
) -> str:
    """Render the Trust Assessment section.

    Args:
        human_eval_data: Human evaluation summary dict or None.
        robustness_data: Robustness analysis dict or None.
        context_impact_data: Context impact analysis dict or None.

    Returns:
        Markdown string for the trust assessment section.
    """
    trust_level = _compute_trust_level(human_eval_data, robustness_data)
    missing_notes = _missing_stream_notes(
        human_eval_data, robustness_data, context_impact_data
    )

    lines = [
        "## Trust Assessment",
        "",
        f"**Overall trust level:** {trust_level}",
    ]
    if missing_notes:
        lines.append("")
        for note in missing_notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def _recommendations_section(
    human_eval_data: dict | None,
    robustness_data: dict | None,
    context_impact_data: dict | None,
) -> str:
    """Render deterministic recommendations based on findings.

    Args:
        human_eval_data: Human evaluation summary dict or None.
        robustness_data: Robustness analysis dict or None.
        context_impact_data: Context impact analysis dict or None.

    Returns:
        Markdown string for the recommendations section.
    """
    lines = ["## Recommendations", ""]
    recommendations: list[str] = []

    # Human eval recommendations
    if human_eval_data is not None:
        overall_avg = human_eval_data.get("overall_avg", 0.0)
        if overall_avg < 3.0:
            recommendations.append(
                "Human evaluation scores are below 3.0. "
                "Review branch ranking and explanation quality."
            )
        elif overall_avg < 3.5:
            recommendations.append(
                "Human evaluation scores are moderate (3.0–3.5). "
                "Consider targeted improvements to explanation clarity."
            )
    else:
        recommendations.append(
            "Conduct human evaluation to validate ranking and explanation quality."
        )

    # Robustness recommendations
    if robustness_data is not None:
        summary = robustness_data.get("summary", robustness_data)
        fragile_count = summary.get("fragile_count", 0)
        if fragile_count > 2:
            recommendations.append(
                f"{fragile_count} fragile result(s) detected. "
                "Investigate degradation strategies causing instability."
            )
        elif fragile_count > 0:
            recommendations.append(
                f"{fragile_count} fragile result(s) detected. "
                "Monitor and consider threshold adjustments."
            )
    else:
        recommendations.append(
            "Run robustness evaluation to assess stability under degraded inputs."
        )

    # Context impact recommendations
    if context_impact_data is not None:
        summary = context_impact_data.get("summary", context_impact_data)
        degraded = summary.get("scenarios_degraded", [])
        if degraded:
            recommendations.append(
                f"{len(degraded)} scenario(s) degraded by context. "
                "Review enrichment heuristics and classification thresholds."
            )
    else:
        recommendations.append(
            "Run context impact analysis to measure enrichment effectiveness."
        )

    if not recommendations:
        recommendations.append("No specific recommendations at this time.")

    for rec in recommendations:
        lines.append(f"- {rec}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Appendix
# ---------------------------------------------------------------------------


def _appendix_section(
    human_eval_data: dict | None,
    robustness_data: dict | None,
    context_impact_data: dict | None,
    timestamp: str,
) -> str:
    """Render the appendix with data sources and generation metadata.

    Args:
        human_eval_data: Human evaluation summary dict or None.
        robustness_data: Robustness analysis dict or None.
        context_impact_data: Context impact analysis dict or None.
        timestamp: ISO-8601 generation timestamp.

    Returns:
        Markdown string for the appendix section.
    """
    lines = [
        "## Appendix",
        "",
        "### Data Sources",
        "",
    ]

    if human_eval_data is not None:
        lines.append("- Human Evaluation: provided")
    else:
        lines.append("- Human Evaluation: not provided")

    if robustness_data is not None:
        lines.append("- Robustness: provided")
    else:
        lines.append("- Robustness: not provided")

    if context_impact_data is not None:
        lines.append("- Context Impact: provided")
    else:
        lines.append("- Context Impact: not provided")

    lines.append("")
    lines.append("### Generation Metadata")
    lines.append("")
    lines.append(f"- **Timestamp:** {timestamp}")
    lines.append("- **Generator:** src/evaluation/trust_report.py")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_trust_report(
    human_eval_data: dict | None = None,
    robustness_data: dict | None = None,
    context_impact_data: dict | None = None,
) -> str:
    """Generate a consolidated Markdown trust report.

    Combines human evaluation, robustness, and context impact results
    into a single report with overview, per-stream summaries, trust
    assessment, recommendations, and appendix.

    Each input can be None; the corresponding section will show
    "Not available" and the trust assessment will note the missing stream.

    Args:
        human_eval_data: Dict from human evaluation summary JSON, or None.
        robustness_data: Dict from robustness analysis JSON, or None.
        context_impact_data: Dict from context impact analysis JSON, or None.

    Returns:
        Complete Markdown report string.
    """
    timestamp = _timestamp()

    sections = [
        "# Consolidated Trust Report",
        _overview_section(
            human_eval_data, robustness_data, context_impact_data, timestamp
        ),
        _human_eval_section(human_eval_data),
        _robustness_section(robustness_data),
        _context_impact_section(context_impact_data),
        _trust_assessment_section(
            human_eval_data, robustness_data, context_impact_data
        ),
        _recommendations_section(
            human_eval_data, robustness_data, context_impact_data
        ),
        _appendix_section(
            human_eval_data, robustness_data, context_impact_data, timestamp
        ),
    ]
    return "\n\n".join(sections) + "\n"


def save_trust_report(
    human_eval_data: dict | None = None,
    robustness_data: dict | None = None,
    context_impact_data: dict | None = None,
    output_path: str = "output/trust_report.md",
) -> None:
    """Generate a consolidated trust report and write it to a file.

    Creates parent directories if they do not exist.

    Args:
        human_eval_data: Dict from human evaluation summary JSON, or None.
        robustness_data: Dict from robustness analysis JSON, or None.
        context_impact_data: Dict from context impact analysis JSON, or None.
        output_path: File path to write the Markdown output.
    """
    md = generate_trust_report(
        human_eval_data=human_eval_data,
        robustness_data=robustness_data,
        context_impact_data=context_impact_data,
    )
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(md)
