"""Rich-based terminal renderers for the CLI.

Provides formatted output for progress, results, errors, and tables.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def render_banner() -> None:
    """Render the Football Tactical OS banner."""
    console.print(Panel.fit(
        "[bold blue]Football Tactical OS[/bold blue]\n"
        "[dim]Tactical simulation analysis platform[/dim]",
        border_style="blue",
    ))


def render_step_progress(steps: list[dict]) -> None:
    """Render step-level progress.

    Args:
        steps: List of dicts with 'name' and 'status' keys.
    """
    for step in steps:
        name = step.get("name", "?")
        status = step.get("status", "?")
        if status == "success":
            console.print(f"  [green]✓[/green] {name}")
        elif status == "failed":
            console.print(f"  [red]✗[/red] {name}")
        elif status == "skipped":
            console.print(f"  [yellow]–[/yellow] {name} [dim](skipped)[/dim]")
        else:
            console.print(f"  [dim]?[/dim] {name}")


def render_artifacts(artifacts: dict[str, str]) -> None:
    """Render artifact paths.

    Args:
        artifacts: Mapping of artifact name to path.
    """
    if not artifacts:
        console.print("[dim]No artifacts generated.[/dim]")
        return
    console.print("\n[bold]Artifacts:[/bold]")
    for name, path in sorted(artifacts.items()):
        console.print(f"  • {name}: [cyan]{path}[/cyan]")


def render_error(message: str, suggestion: str = "") -> None:
    """Render a user-friendly error message.

    Args:
        message: The error message.
        suggestion: Optional suggested fix.
    """
    console.print(f"\n[red bold]Error:[/red bold] {message}")
    if suggestion:
        console.print(f"[yellow]Suggestion:[/yellow] {suggestion}")


def render_healthcheck(result) -> None:
    """Render health check results as a table.

    Args:
        result: A HealthCheckResult instance.
    """
    table = Table(title="System Health Check")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Detail")

    for check in result.checks:
        status = check["status"]
        if status == "ok":
            style = "green"
        elif status == "warning":
            style = "yellow"
        else:
            style = "red"
        table.add_row(check["name"], f"[{style}]{status}[/{style}]", check.get("detail", ""))

    console.print(table)
    console.print(f"\n[bold]Overall: [{('green' if result.status == 'ok' else 'red')}]{result.status}[/]")


def render_runs_table(runs: list[dict]) -> None:
    """Render a table of available runs.

    Args:
        runs: List of run summary dicts.
    """
    if not runs:
        console.print("[dim]No runs found.[/dim]")
        return

    table = Table(title="Available Runs")
    table.add_column("Scenario", style="bold")
    table.add_column("Status")
    table.add_column("Source")

    for run in runs:
        status = run.get("status", "?")
        style = "green" if status == "success" else "red" if status == "failed" else "yellow"
        table.add_row(
            run.get("scenario_id", "?"),
            f"[{style}]{status}[/{style}]",
            run.get("source_type", "?"),
        )

    console.print(table)
