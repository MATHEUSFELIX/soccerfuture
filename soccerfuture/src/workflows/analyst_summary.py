"""Analyst-facing Markdown summary renderer.

Produces concise, human-readable summaries of pipeline runs for analyst
review. Focuses on what was analyzed, what ranked highest, and why.
"""

from __future__ import annotations


def render_analyst_summary(
    scenario_id: str,
    source_type: str,
    pipeline_report: dict | None,
    extraction_notes: list[str] | None = None,
    context_applied: bool = False,
    priors_applied: bool = False,
    confidence_notes: list[str] | None = None,
    artifact_references: dict[str, str] | None = None,
) -> str:
    """Render an analyst-facing Markdown summary.

    Args:
        scenario_id: Unique scenario identifier.
        source_type: Input source type ("structured", "video", "commentator").
        pipeline_report: Serialized PipelineReport dict, or None if pipeline failed.
        extraction_notes: Notes from state extraction, if applicable.
        context_applied: Whether match context influenced the result.
        priors_applied: Whether match priors influenced the result.
        confidence_notes: Notes about confidence or completeness.
        artifact_references: Mapping of artifact name to path.

    Returns:
        Complete Markdown summary string.
    """
    sections: list[str] = []

    # --- Header ---
    sections.append(f"# Analyst Summary: {scenario_id}")
    sections.append("")

    # --- Scenario Overview ---
    sections.append("## Scenario Overview")
    sections.append("")
    sections.append(f"- **Scenario ID:** {scenario_id}")
    sections.append(f"- **Source type:** {source_type}")
    sections.append(f"- **Context applied:** {'Yes' if context_applied else 'No'}")
    sections.append(f"- **Priors applied:** {'Yes' if priors_applied else 'No'}")
    sections.append("")

    # --- Extraction Notes ---
    if extraction_notes:
        sections.append("## Extraction Notes")
        sections.append("")
        for note in extraction_notes:
            sections.append(f"- {note}")
        sections.append("")

    # --- Top Branches ---
    sections.append("## Top Branches")
    sections.append("")

    if pipeline_report is None:
        sections.append("_Pipeline did not produce results._")
        sections.append("")
    else:
        ranked = pipeline_report.get("ranked_branches", [])
        if not ranked:
            sections.append("_No branches passed gating._")
            sections.append("")
        else:
            for i, rb in enumerate(ranked[:5], 1):
                branch_id = rb.get("branch_id", "unknown")
                score = rb.get("composite_score", 0.0)
                sections.append(f"{i}. **{branch_id}** — composite score: {score:.3f}")

                # Explanation highlights
                eval_report = rb.get("evaluation_report", {})
                explanation = eval_report.get("ranking_explanation", {})
                promoted = explanation.get("promoted_factors", [])
                if promoted:
                    sections.append(f"   - Strengths: {', '.join(promoted[:3])}")

            sections.append("")

    # --- Explanation Highlights ---
    if pipeline_report is not None:
        ranked = pipeline_report.get("ranked_branches", [])
        if ranked:
            top = ranked[0]
            eval_report = top.get("evaluation_report", {})
            explanation = eval_report.get("ranking_explanation", {})
            penalized = explanation.get("penalized_factors", [])
            top_block = explanation.get("top_scoring_block", "")
            bottom_block = explanation.get("bottom_scoring_block", "")

            sections.append("## Explanation Highlights")
            sections.append("")
            if top_block:
                sections.append(f"- **Top scoring dimension:** {top_block}")
            if bottom_block:
                sections.append(f"- **Bottom scoring dimension:** {bottom_block}")
            if penalized:
                sections.append(f"- **Penalized factors:** {', '.join(penalized[:3])}")
            sections.append("")

    # --- Confidence and Caveats ---
    sections.append("## Confidence and Caveats")
    sections.append("")
    if confidence_notes:
        for note in confidence_notes:
            sections.append(f"- {note}")
    else:
        sections.append("- No specific confidence concerns noted.")
    sections.append("")

    # --- Context/Prior Influence ---
    if context_applied or priors_applied:
        sections.append("## Context and Prior Influence")
        sections.append("")
        if context_applied:
            sections.append("- Match context was applied to this analysis.")
        if priors_applied:
            sections.append("- Match priors influenced ranking adjustments.")

        # Pull influence level from metadata if available
        if pipeline_report is not None:
            metadata = pipeline_report.get("metadata", {})
            influence = metadata.get("priors_influence_level")
            if influence:
                sections.append(f"- Prior influence level: {influence}")
        sections.append("")

    # --- Artifact References ---
    if artifact_references:
        sections.append("## Artifacts")
        sections.append("")
        for name, path in sorted(artifact_references.items()):
            sections.append(f"- **{name}:** `{path}`")
        sections.append("")

    return "\n".join(sections)
