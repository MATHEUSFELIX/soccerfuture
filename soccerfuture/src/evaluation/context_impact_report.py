"""Markdown report generation from context impact analysis JSON output.

Reads the dict produced by ``load_analysis_json()`` and renders a
human-readable Markdown report with overview, aggregate metrics,
per-classification scenario lists, operational observations, and
deterministic recommendations.
"""

from __future__ import annotations


def _overview_section(metadata: dict) -> str:
    """Render the overview header section.

    Args:
        metadata: The ``metadata`` dict from the analysis JSON.

    Returns:
        Markdown string for the overview section.
    """
    generated_at = metadata.get("generated_at", "unknown")
    scenario_count = metadata.get("scenario_count", 0)
    lines = [
        "# Context Impact Evaluation Report",
        "",
        f"- **Generated at:** {generated_at}",
        f"- **Scenarios evaluated:** {scenario_count}",
    ]
    return "\n".join(lines)


def _aggregate_metrics_section(summary: dict) -> str:
    """Render the aggregate metrics table.

    Args:
        summary: The ``summary`` dict from the analysis JSON.

    Returns:
        Markdown string for the aggregate metrics section.
    """
    lines = [
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Scenario count | {summary.get('scenario_count', 0)} |",
        f"| Top-1 changed | {summary.get('top_1_changed_count', 0)} |",
        f"| Top-3 changed | {summary.get('top_3_changed_count', 0)} |",
        f"| Neutral context | {summary.get('neutral_context_count', 0)} |",
        f"| Avg validity delta | {summary.get('avg_validity_delta', 0.0)} |",
        f"| Avg opportunity delta | {summary.get('avg_opportunity_delta', 0.0)} |",
        f"| Cache hits | {summary.get('cache_hit_count', 0)} |",
        f"| Cache misses | {summary.get('cache_miss_count', 0)} |",
    ]
    return "\n".join(lines)


def _find_result_by_id(
    results: list[dict], scenario_id: str
) -> dict | None:
    """Find a result dict by scenario_id.

    Args:
        results: List of per-scenario result dicts.
        scenario_id: The ID to look up.

    Returns:
        The matching result dict, or ``None``.
    """
    for r in results:
        if r.get("scenario_id") == scenario_id:
            return r
    return None


def _viewer_artifact_lines(result: dict) -> list[str]:
    """Render viewer artifact references for a single scenario result.

    If the result has a non-None ``viewer_artifacts`` dict, includes
    references to no-context and with-context render paths. Silently
    skips if viewer_artifacts is None or missing.

    Args:
        result: A per-scenario result dict.

    Returns:
        List of Markdown lines (may be empty).
    """
    artifacts = result.get("viewer_artifacts")
    if not artifacts or not isinstance(artifacts, dict):
        return []
    lines: list[str] = []
    no_ctx = artifacts.get("no_context")
    with_ctx = artifacts.get("with_context")
    if no_ctx:
        lines.append(f"  - No-context render: `{no_ctx}`")
    if with_ctx:
        lines.append(f"  - With-context render: `{with_ctx}`")
    return lines


def _scenarios_section(
    title: str,
    scenario_ids: list[str],
    results: list[dict],
    include_notes: bool = False,
) -> str:
    """Render a section listing scenarios by classification.

    Args:
        title: Section heading (e.g. "Scenarios Helped").
        scenario_ids: IDs of scenarios in this classification.
        results: Full list of per-scenario result dicts.
        include_notes: Whether to append notes for each scenario.

    Returns:
        Markdown string for the section.
    """
    lines = [f"## {title}", ""]
    if not scenario_ids:
        lines.append("_None._")
        return "\n".join(lines)
    for sid in scenario_ids:
        result = _find_result_by_id(results, sid)
        notes = ""
        if include_notes and result:
            scenario_notes = result.get("notes", [])
            if scenario_notes:
                notes = " — " + "; ".join(scenario_notes)
        lines.append(f"- `{sid}`{notes}")
        if result:
            lines.extend(_viewer_artifact_lines(result))
    return "\n".join(lines)


def _operational_observations_section(summary: dict) -> str:
    """Render operational observations.

    Args:
        summary: The ``summary`` dict from the analysis JSON.

    Returns:
        Markdown string for the operational observations section.
    """
    lines = [
        "## Operational Observations",
        "",
        f"- Partial context count: {summary.get('partial_context_count', 0)}",
        f"- Fallback count: {summary.get('fallback_count', 0)}",
        f"- Cache hits: {summary.get('cache_hit_count', 0)}",
        f"- Cache misses: {summary.get('cache_miss_count', 0)}",
    ]
    return "\n".join(lines)


def _recommendations_section(summary: dict) -> str:
    """Render deterministic recommendations based on classification data.

    Rules:
      - All neutral: minimal impact message.
      - Any degraded: review thresholds message.
      - Any helped and none degraded: positive impact message.
      - Otherwise: mixed results message.

    Args:
        summary: The ``summary`` dict from the analysis JSON.

    Returns:
        Markdown string for the recommendations section.
    """
    helped = summary.get("scenarios_helped", [])
    degraded = summary.get("scenarios_degraded", [])
    neutral = summary.get("scenarios_neutral", [])

    if not helped and not degraded:
        text = (
            "Context integration appears to have minimal impact. "
            "Consider reviewing enrichment heuristics."
        )
    elif degraded:
        text = (
            "Some scenarios degraded with context. "
            "Review classification thresholds and enrichment rules."
        )
    elif helped and not degraded:
        text = (
            "Context integration shows positive impact "
            "without degradation."
        )
    else:
        text = "Mixed results. Further tuning of enrichment heuristics recommended."

    return "\n".join(["## Recommendations", "", text])


def generate_markdown_report(analysis_data: dict) -> str:
    """Generate a full Markdown report from analysis JSON data.

    Args:
        analysis_data: The dict returned by ``load_analysis_json()``,
            containing ``results``, ``summary``, and ``metadata`` keys.

    Returns:
        A complete Markdown string with overview, aggregate metrics,
        helped/neutral/degraded scenario lists, operational observations,
        and recommendations.
    """
    metadata = analysis_data.get("metadata", {})
    summary = analysis_data.get("summary", {})
    results = analysis_data.get("results", [])

    sections = [
        _overview_section(metadata),
        _aggregate_metrics_section(summary),
        _scenarios_section(
            "Scenarios Helped",
            summary.get("scenarios_helped", []),
            results,
            include_notes=True,
        ),
        _scenarios_section(
            "Scenarios Neutral",
            summary.get("scenarios_neutral", []),
            results,
            include_notes=False,
        ),
        _scenarios_section(
            "Scenarios Degraded",
            summary.get("scenarios_degraded", []),
            results,
            include_notes=True,
        ),
        _operational_observations_section(summary),
        _recommendations_section(summary),
    ]
    return "\n\n".join(sections) + "\n"


def save_markdown_report(analysis_data: dict, output_path: str) -> None:
    """Generate a Markdown report and write it to a file.

    Args:
        analysis_data: The dict returned by ``load_analysis_json()``.
        output_path: File path to write the Markdown output.
    """
    md = generate_markdown_report(analysis_data)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(md)
