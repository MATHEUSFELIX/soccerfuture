"""Questionary-based interactive prompts for the CLI.

Wraps questionary calls for testability — each function returns
the user's selection as a string.
"""

from __future__ import annotations

import questionary


def prompt_main_menu() -> str:
    """Show the main menu and return the selected action.

    Returns:
        One of: "run", "review", "pilot", "reports", "system", "exit".
    """
    choices = [
        questionary.Choice("Run workflow", value="run"),
        questionary.Choice("Review", value="review"),
        questionary.Choice("Pilot", value="pilot"),
        questionary.Choice("Reports", value="reports"),
        questionary.Choice("System", value="system"),
        questionary.Choice("Exit", value="exit"),
    ]
    return questionary.select("What would you like to do?", choices=choices).ask() or "exit"


def prompt_run_menu() -> str:
    """Show the run sub-menu.

    Returns:
        One of: "demo", "scenario", "batch", "runtime", "back".
    """
    choices = [
        questionary.Choice("Run official demo", value="demo"),
        questionary.Choice("Run single scenario", value="scenario"),
        questionary.Choice("Run batch scenarios", value="batch"),
        questionary.Choice("Run runtime ingestion", value="runtime"),
        questionary.Choice("Back", value="back"),
    ]
    return questionary.select("Run menu:", choices=choices).ask() or "back"


def prompt_review_menu() -> str:
    """Show the review sub-menu.

    Returns:
        One of: "review_site", "feedback", "stakeholder", "back".
    """
    choices = [
        questionary.Choice("Generate review site", value="review_site"),
        questionary.Choice("Ingest feedback", value="feedback"),
        questionary.Choice("Generate stakeholder report", value="stakeholder"),
        questionary.Choice("Back", value="back"),
    ]
    return questionary.select("Review menu:", choices=choices).ask() or "back"


def prompt_system_menu() -> str:
    """Show the system sub-menu.

    Returns:
        One of: "healthcheck", "list_runs", "config", "back".
    """
    choices = [
        questionary.Choice("Health check", value="healthcheck"),
        questionary.Choice("List runs", value="list_runs"),
        questionary.Choice("Show config", value="config"),
        questionary.Choice("Back", value="back"),
    ]
    return questionary.select("System menu:", choices=choices).ask() or "back"


def prompt_file_path(message: str = "Enter file path:") -> str:
    """Prompt for a file path.

    Args:
        message: Prompt message.

    Returns:
        The entered file path string.
    """
    return questionary.path(message).ask() or ""


def prompt_next_action() -> str:
    """Prompt for next action after a run completes.

    Returns:
        One of: "another", "review_site", "exit".
    """
    choices = [
        questionary.Choice("Run another scenario", value="another"),
        questionary.Choice("Generate review site", value="review_site"),
        questionary.Choice("Exit", value="exit"),
    ]
    return questionary.select("What would you like to do next?", choices=choices).ask() or "exit"
