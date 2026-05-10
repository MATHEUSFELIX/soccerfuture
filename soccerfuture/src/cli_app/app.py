"""Typer-based CLI entry point for Football Tactical OS.

Provides both direct commands for automation and an interactive
mode for guided analyst workflows.

Usage:
    python -m src.cli_app.app interactive
    python -m src.cli_app.app run-demo
    python -m src.cli_app.app run-scenario --input data/play_states/file.json
    python -m src.cli_app.app healthcheck
    python -m src.cli_app.app list-runs
    python -m src.cli_app.app generate-review-site
"""

from __future__ import annotations

import typer

from src.cli_app.commands import (
    cmd_generate_review_site,
    cmd_healthcheck,
    cmd_list_runs,
    cmd_run_demo,
    cmd_run_scenario,
)
from src.cli_app.renderers import (
    console,
    render_artifacts,
    render_banner,
    render_error,
    render_healthcheck,
    render_runs_table,
    render_step_progress,
)

app = typer.Typer(name="football-os", help="Football Tactical OS CLI")


@app.command()
def interactive() -> None:
    """Launch the interactive guided menu."""
    from src.cli_app.prompts import (
        prompt_main_menu,
        prompt_next_action,
        prompt_run_menu,
        prompt_review_menu,
        prompt_system_menu,
        prompt_file_path,
    )

    render_banner()

    while True:
        action = prompt_main_menu()

        if action == "exit":
            console.print("[dim]Goodbye.[/dim]")
            break

        elif action == "run":
            sub = prompt_run_menu()
            if sub == "demo":
                console.print("\n[bold]Running official demo...[/bold]")
                result = cmd_run_demo()
                if result.success:
                    render_step_progress(result.steps)
                    render_artifacts(result.artifacts)
                else:
                    render_error(result.error_message, result.suggestion)

            elif sub == "scenario":
                path = prompt_file_path("Path to PlayState JSON:")
                if path:
                    console.print(f"\n[bold]Running scenario from {path}...[/bold]")
                    result = cmd_run_scenario(path)
                    if result.success:
                        render_step_progress(result.steps)
                        render_artifacts(result.artifacts)
                    else:
                        render_error(result.error_message, result.suggestion)

        elif action == "review":
            sub = prompt_review_menu()
            if sub == "review_site":
                console.print("\n[bold]Generating review site...[/bold]")
                result = cmd_generate_review_site()
                if result.success:
                    render_artifacts(result.artifacts)
                else:
                    render_error(result.error_message)

        elif action == "system":
            sub = prompt_system_menu()
            if sub == "healthcheck":
                hc = cmd_healthcheck()
                render_healthcheck(hc)
            elif sub == "list_runs":
                runs = cmd_list_runs()
                render_runs_table(runs)

        elif action == "reports":
            runs = cmd_list_runs()
            render_runs_table(runs)

        elif action == "pilot":
            console.print("[dim]Pilot workflows available via: football-os run-pilot[/dim]")


@app.command(name="run-demo")
def run_demo_cmd() -> None:
    """Run the official demo scenario."""
    render_banner()
    console.print("\n[bold]Running official demo...[/bold]")
    result = cmd_run_demo()
    if result.success:
        render_step_progress(result.steps)
        render_artifacts(result.artifacts)
        console.print(f"\n[green]Demo completed: {result.status}[/green]")
    else:
        render_error(result.error_message, result.suggestion)
        raise typer.Exit(code=1)


@app.command(name="run-scenario")
def run_scenario_cmd(
    input: str = typer.Option(..., "--input", help="Path to PlayState JSON"),
    output_root: str = typer.Option("output/runs", "--output", help="Output root"),
) -> None:
    """Run a single scenario from a PlayState JSON file."""
    console.print(f"\n[bold]Running scenario from {input}...[/bold]")
    result = cmd_run_scenario(input, output_root=output_root)
    if result.success:
        render_step_progress(result.steps)
        render_artifacts(result.artifacts)
        console.print(f"\n[green]Completed: {result.status}[/green]")
    else:
        render_error(result.error_message, result.suggestion)
        raise typer.Exit(code=1)


@app.command()
def healthcheck() -> None:
    """Run system health check."""
    hc = cmd_healthcheck()
    render_healthcheck(hc)
    if hc.status != "ok":
        raise typer.Exit(code=1)


@app.command(name="list-runs")
def list_runs_cmd(
    output_root: str = typer.Option("output/runs", "--runs", help="Runs directory"),
) -> None:
    """List available workflow runs."""
    runs = cmd_list_runs(output_root)
    render_runs_table(runs)


@app.command(name="generate-review-site")
def generate_review_site_cmd(
    runs_root: str = typer.Option("output/runs", "--runs", help="Runs directory"),
    output_dir: str = typer.Option("output/review_site", "--output", help="Output directory"),
) -> None:
    """Generate the static review site."""
    console.print("[bold]Generating review site...[/bold]")
    result = cmd_generate_review_site(runs_root, output_dir)
    if result.success:
        render_artifacts(result.artifacts)
        console.print("[green]Review site generated.[/green]")
    else:
        render_error(result.error_message)
        raise typer.Exit(code=1)


@app.command(name="app")
def web_app_cmd(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to listen on"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser"),
) -> None:
    """Start the local web application in the browser."""
    from src.web.local_app import start_server
    console.print(f"[bold]Starting Football Tactical OS at http://{host}:{port}[/bold]")
    start_server(host=host, port=port, open_browser=not no_browser)


if __name__ == "__main__":
    app()
