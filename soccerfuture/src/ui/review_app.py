"""Static HTML review app generator.

Generates a browsable set of HTML pages from scenario bundles,
review packs, readiness results, and feedback records. No web
framework required — produces static files for local browsing.
"""

from __future__ import annotations

import json
import os

from src.ui.review_data_loader import ScenarioViewData, load_all_scenarios


def _html_header(title: str) -> str:
    """Generate HTML header with minimal styling."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; line-height: 1.6; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
th {{ background: #f5f5f5; }}
.ready {{ color: green; font-weight: bold; }}
.partial {{ color: orange; font-weight: bold; }}
.not-ready {{ color: red; font-weight: bold; }}
.success {{ color: green; }}
.failed {{ color: red; }}
a {{ color: #0066cc; }}
pre {{ background: #f8f8f8; padding: 1rem; overflow-x: auto; border-radius: 4px; }}
</style>
</head>
<body>
"""


def _html_footer() -> str:
    """Generate HTML footer."""
    return "</body>\n</html>\n"


def _readiness_class(label: str | None) -> str:
    """Map readiness label to CSS class."""
    if label == "ready":
        return "ready"
    elif label == "partially_ready":
        return "partial"
    elif label == "not_ready":
        return "not-ready"
    return ""


def render_index_page(scenarios: list[ScenarioViewData]) -> str:
    """Render the scenario list index page as HTML.

    Args:
        scenarios: List of loaded scenario data.

    Returns:
        Complete HTML string for the index page.
    """
    html = _html_header("Analyst Review — Scenario Index")
    html += "<h1>Analyst Review — Scenario Index</h1>\n"
    html += f"<p><strong>Total scenarios:</strong> {len(scenarios)}</p>\n"

    html += "<table>\n"
    html += "<tr><th>Scenario</th><th>Source</th><th>Status</th>"
    html += "<th>Top-1 Branch</th><th>Readiness</th><th>Details</th></tr>\n"

    for s in scenarios:
        top_1 = s.top_branches[0]["branch_id"] if s.top_branches else "—"
        readiness = s.readiness_label or "—"
        r_class = _readiness_class(s.readiness_label)
        status_class = "success" if s.overall_status == "success" else "failed"

        html += f"<tr>"
        html += f"<td>{s.scenario_id}</td>"
        html += f"<td>{s.source_type}</td>"
        html += f"<td class='{status_class}'>{s.overall_status}</td>"
        html += f"<td>{top_1}</td>"
        html += f"<td class='{r_class}'>{readiness}</td>"
        html += f"<td><a href='{s.scenario_id}.html'>View</a></td>"
        html += f"</tr>\n"

    html += "</table>\n"
    html += _html_footer()
    return html


def render_scenario_detail_page(scenario: ScenarioViewData) -> str:
    """Render a scenario detail page as HTML.

    Args:
        scenario: Loaded scenario data.

    Returns:
        Complete HTML string for the detail page.
    """
    html = _html_header(f"Scenario: {scenario.scenario_id}")
    html += f"<h1>Scenario: {scenario.scenario_id}</h1>\n"
    html += f"<p><a href='index.html'>← Back to index</a></p>\n"

    # Overview
    html += "<h2>Overview</h2>\n"
    html += "<ul>\n"
    html += f"<li><strong>Source type:</strong> {scenario.source_type}</li>\n"
    html += f"<li><strong>Status:</strong> {scenario.overall_status}</li>\n"
    html += f"<li><strong>Readiness:</strong> {scenario.readiness_label or '—'}</li>\n"
    html += "</ul>\n"

    # Top branches
    html += "<h2>Top Branches</h2>\n"
    if scenario.top_branches:
        html += "<table><tr><th>#</th><th>Branch ID</th><th>Score</th></tr>\n"
        for i, b in enumerate(scenario.top_branches, 1):
            html += f"<tr><td>{i}</td><td>{b['branch_id']}</td>"
            html += f"<td>{b['composite_score']:.3f}</td></tr>\n"
        html += "</table>\n"
    else:
        html += "<p>No ranked branches available.</p>\n"

    # Analyst summary
    html += "<h2>Analyst Summary</h2>\n"
    if scenario.analyst_summary:
        html += f"<pre>{scenario.analyst_summary}</pre>\n"
    else:
        html += "<p>No summary available.</p>\n"

    # Feedback
    html += "<h2>Feedback</h2>\n"
    if scenario.feedback_records:
        html += f"<p>{len(scenario.feedback_records)} feedback record(s) received.</p>\n"
        for fb in scenario.feedback_records:
            html += f"<pre>{json.dumps(fb, indent=2)}</pre>\n"
    else:
        html += "<p>No feedback received yet.</p>\n"

    # Viewer artifact
    html += "<h2>Viewer Artifact</h2>\n"
    if scenario.viewer_artifact:
        html += f"<pre>{json.dumps(scenario.viewer_artifact, indent=2)}</pre>\n"
    else:
        html += "<p>No viewer artifact available.</p>\n"

    html += _html_footer()
    return html


def generate_review_site(
    runs_root: str,
    output_dir: str,
    feedback_dir: str | None = None,
) -> list[str]:
    """Generate a complete static review site from scenario bundles.

    Args:
        runs_root: Root directory containing scenario bundles.
        output_dir: Directory to write the generated HTML files.
        feedback_dir: Optional directory containing feedback JSON files.

    Returns:
        List of generated file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    scenarios = load_all_scenarios(runs_root)

    # Load feedback if available
    if feedback_dir:
        from src.ui.review_data_loader import load_feedback_for_scenario
        for s in scenarios:
            s.feedback_records = load_feedback_for_scenario(feedback_dir, s.scenario_id)

    generated_files: list[str] = []

    # Index page
    index_html = render_index_page(scenarios)
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(index_html)
    generated_files.append(index_path)

    # Detail pages
    for s in scenarios:
        detail_html = render_scenario_detail_page(s)
        detail_path = os.path.join(output_dir, f"{s.scenario_id}.html")
        with open(detail_path, "w", encoding="utf-8") as fh:
            fh.write(detail_html)
        generated_files.append(detail_path)

    return generated_files


def export_feedback_template(
    scenario_id: str,
    output_path: str,
) -> str:
    """Export an empty feedback template JSON for a scenario.

    Args:
        scenario_id: Scenario to create the template for.
        output_path: Path to write the template JSON.

    Returns:
        Path to the written template file.
    """
    template = {
        "scenario_id": scenario_id,
        "reviewer_id": "",
        "top_1_plausibility": "",
        "top_3_usefulness": "",
        "summary_clarity": 0,
        "confidence_sufficiency": 0,
        "blockers": [],
        "missing_capabilities": [],
        "priority_suggestions": [],
        "notes": "",
    }
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(template, fh, indent=2)
    return output_path
