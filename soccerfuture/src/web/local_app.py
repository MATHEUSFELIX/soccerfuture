"""Local FastAPI web application for Football Tactical OS.

Provides a friendly browser-based interface for running demos,
inspecting runs, viewing healthcheck, and understanding test coverage.

Start with: python -m src.web.local_app
Or via CLI: python -m src.cli_app.app app
"""

from __future__ import annotations

import os
import webbrowser
from threading import Timer

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.cli_app.commands import cmd_healthcheck, cmd_list_runs, cmd_run_demo
from src.web.artifact_loader import load_run_detail, load_runs_list
from src.web.test_catalog import get_test_catalog

app = FastAPI(title="Football Tactical OS", docs_url=None, redoc_url=None)

# ---------------------------------------------------------------------------
# HTML rendering helpers (inline Jinja2-style, no external templates needed)
# ---------------------------------------------------------------------------

_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #f8f9fa; color: #333; }
.container { max-width: 1000px; margin: 0 auto; padding: 2rem; }
header { background: #1a365d; color: white; padding: 1.5rem 2rem; }
header h1 { margin: 0; font-size: 1.5rem; }
header p { margin: 0.3rem 0 0; opacity: 0.8; font-size: 0.9rem; }
nav { background: #2d4a7a; padding: 0.5rem 2rem; }
nav a { color: #cbd5e0; text-decoration: none; margin-right: 1.5rem; font-size: 0.9rem; }
nav a:hover { color: white; }
.card { background: white; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.btn { display: inline-block; padding: 0.6rem 1.2rem; background: #2b6cb0; color: white; text-decoration: none; border-radius: 4px; font-size: 0.9rem; border: none; cursor: pointer; }
.btn:hover { background: #2c5282; }
.btn-success { background: #38a169; }
.btn-success:hover { background: #2f855a; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
th, td { padding: 0.6rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
th { background: #edf2f7; font-weight: 600; }
.status-success { color: #38a169; font-weight: bold; }
.status-failed { color: #e53e3e; font-weight: bold; }
.status-partial { color: #d69e2e; font-weight: bold; }
.status-ok { color: #38a169; }
.status-warning { color: #d69e2e; }
.status-error { color: #e53e3e; }
pre { background: #edf2f7; padding: 1rem; border-radius: 4px; overflow-x: auto; font-size: 0.85rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
"""

_NAV = """
<nav>
<a href="/">Home</a>
<a href="/runs">Runs</a>
<a href="/healthcheck">Healthcheck</a>
<a href="/tests">Test Health</a>
</nav>
"""


def _page(title: str, content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{title} — Football Tactical OS</title>
<style>{_CSS}</style></head>
<body>
<header><h1>Football Tactical OS</h1><p>Tactical simulation analysis platform</p></header>
{_NAV}
<div class="container">{content}</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def home():
    """Home page with quick actions."""
    hc = cmd_healthcheck()
    status_class = f"status-{hc.status}"
    runs = load_runs_list()

    content = f"""
    <h2>Dashboard</h2>
    <div class="grid">
        <div class="card">
            <h3>System Status</h3>
            <p class="{status_class}" style="font-size:1.2rem">{hc.status.upper()}</p>
        </div>
        <div class="card">
            <h3>Available Runs</h3>
            <p style="font-size:1.2rem">{len(runs)}</p>
        </div>
    </div>
    <h2>Quick Actions</h2>
    <div class="card">
        <a href="/run-demo" class="btn btn-success">Run Official Demo</a>
        <a href="/runs" class="btn">View Runs</a>
        <a href="/healthcheck" class="btn">Healthcheck</a>
        <a href="/tests" class="btn">Test Health</a>
    </div>
    """
    return _page("Home", content)


@app.get("/run-demo", response_class=HTMLResponse)
async def run_demo():
    """Execute the official demo and show results."""
    result = cmd_run_demo()

    if result.success:
        steps_html = "".join(
            f"<tr><td>{s['name']}</td><td class='status-{s['status']}'>{s['status']}</td></tr>"
            for s in result.steps
        )
        artifacts_html = "".join(
            f"<li><strong>{name}:</strong> <code>{path}</code></li>"
            for name, path in sorted(result.artifacts.items())
        )
        content = f"""
        <h2>Demo Completed ✓</h2>
        <div class="card">
            <p><strong>Scenario:</strong> {result.scenario_id}</p>
            <p><strong>Status:</strong> <span class="status-success">{result.status}</span></p>
        </div>
        <div class="card">
            <h3>Steps</h3>
            <table><tr><th>Step</th><th>Status</th></tr>{steps_html}</table>
        </div>
        <div class="card">
            <h3>Artifacts</h3>
            <ul>{artifacts_html}</ul>
        </div>
        <a href="/runs/{result.scenario_id}" class="btn">View Details</a>
        <a href="/" class="btn">Back to Home</a>
        """
    else:
        content = f"""
        <h2>Demo Failed</h2>
        <div class="card">
            <p style="color:red"><strong>Error:</strong> {result.error_message}</p>
            {"<p><strong>Suggestion:</strong> " + result.suggestion + "</p>" if result.suggestion else ""}
        </div>
        <a href="/" class="btn">Back to Home</a>
        """
    return _page("Run Demo", content)


@app.get("/runs", response_class=HTMLResponse)
async def runs_list():
    """List all available runs."""
    runs = load_runs_list()

    if not runs:
        content = "<h2>Runs</h2><div class='card'><p>No runs found. Run a demo first.</p></div>"
    else:
        rows = ""
        for r in runs:
            status_class = f"status-{r['status']}"
            top = r.get("top_branch") or "—"
            rows += f"<tr><td><a href='/runs/{r['scenario_id']}'>{r['scenario_id']}</a></td>"
            rows += f"<td>{r['source_type']}</td>"
            rows += f"<td class='{status_class}'>{r['status']}</td>"
            rows += f"<td>{top}</td></tr>"

        content = f"""
        <h2>Runs ({len(runs)})</h2>
        <div class="card">
            <table>
            <tr><th>Scenario</th><th>Source</th><th>Status</th><th>Top Branch</th></tr>
            {rows}
            </table>
        </div>
        """
    return _page("Runs", content)


@app.get("/runs/{scenario_id}", response_class=HTMLResponse)
async def run_detail(scenario_id: str):
    """Show detail for a single run."""
    detail = load_run_detail("output/runs", scenario_id)

    if "error" in detail:
        content = f"<h2>Run Not Found</h2><p>{detail['error']}</p>"
        return _page("Run Detail", content)

    status = detail.get("run_status", {})
    overall = status.get("overall_status", "unknown")
    status_class = f"status-{overall}"

    # Top branches
    branches_html = ""
    report = detail.get("pipeline_report", {})
    ranked = report.get("ranked_branches", [])
    if ranked:
        rows = "".join(
            f"<tr><td>{i}</td><td>{b.get('branch_id','?')}</td><td>{b.get('composite_score',0):.3f}</td></tr>"
            for i, b in enumerate(ranked[:5], 1)
        )
        branches_html = f"<table><tr><th>#</th><th>Branch</th><th>Score</th></tr>{rows}</table>"

    # Summary
    summary = detail.get("analyst_summary", "")
    summary_html = f"<pre>{summary}</pre>" if summary else "<p>No summary available.</p>"

    content = f"""
    <h2>Run: {scenario_id}</h2>
    <div class="card">
        <p><strong>Status:</strong> <span class="{status_class}">{overall}</span></p>
        <p><strong>Source:</strong> {status.get('source_type', '?')}</p>
    </div>
    <div class="card"><h3>Top Branches</h3>{branches_html or '<p>No branches.</p>'}</div>
    <div class="card"><h3>Analyst Summary</h3>{summary_html}</div>
    <a href="/runs" class="btn">Back to Runs</a>
    """
    return _page(f"Run: {scenario_id}", content)


@app.get("/healthcheck", response_class=HTMLResponse)
async def healthcheck_page():
    """Show system healthcheck results."""
    hc = cmd_healthcheck()

    rows = "".join(
        f"<tr><td>{c['name']}</td><td class='status-{c['status']}'>{c['status']}</td><td>{c.get('detail','')}</td></tr>"
        for c in hc.checks
    )
    status_class = f"status-{hc.status}"

    content = f"""
    <h2>System Healthcheck</h2>
    <div class="card">
        <p><strong>Overall:</strong> <span class="{status_class}" style="font-size:1.2rem">{hc.status.upper()}</span></p>
    </div>
    <div class="card">
        <table><tr><th>Check</th><th>Status</th><th>Detail</th></tr>{rows}</table>
    </div>
    """
    return _page("Healthcheck", content)


@app.get("/tests", response_class=HTMLResponse)
async def test_catalog_page():
    """Show the test health / test catalog page."""
    catalog = get_test_catalog()

    cards = ""
    for cat in catalog:
        examples = "".join(f"<li>{ex}</li>" for ex in cat.get("examples", []))
        cards += f"""
        <div class="card">
            <h3>{cat['title']}</h3>
            <p><strong>Purpose:</strong> {cat['purpose']}</p>
            <p><strong>Why it matters:</strong> {cat['why_it_matters']}</p>
            <ul>{examples}</ul>
        </div>
        """

    content = f"""
    <h2>Test Health</h2>
    <div class="card">
        <p><strong>Categories:</strong> {len(catalog)}</p>
        <p>Each category below explains what the tests validate and why it matters for product quality.</p>
    </div>
    {cards}
    """
    return _page("Test Health", content)


# ---------------------------------------------------------------------------
# Server startup
# ---------------------------------------------------------------------------


def start_server(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True):
    """Start the local web server.

    Args:
        host: Host to bind to.
        port: Port to listen on.
        open_browser: Whether to open the browser automatically.
    """
    import uvicorn

    if open_browser:
        Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
