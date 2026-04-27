"""Benchmark manifest loader and writer.

Pure functions for loading, validating, serializing, and saving the
benchmark manifest (``data/benchmark_manifest.json``).  No class state;
all I/O goes through Python's built-in ``json`` module.
"""

import json
from typing import Any

# --- Required key sets (kept as module-level frozensets for clarity) ---

_REQUIRED_TOP_LEVEL_KEYS: frozenset[str] = frozenset({
    "version",
    "pipeline_config",
    "scenarios",
})

_REQUIRED_PIPELINE_CONFIG_KEYS: frozenset[str] = frozenset({
    "n",
    "k",
    "seed",
    "validity_weight",
    "opportunity_weight",
})

_REQUIRED_SCENARIO_KEYS: frozenset[str] = frozenset({
    "scenario_file",
    "gating_pass_count",
    "top_branch_min_score",
    "bottom_branch_max_score",
    "strategy_counts",
    "expected_top_k",
})


def load_manifest(path: str) -> dict:
    """Load and validate a benchmark manifest from a JSON file.

    Args:
        path: File path to benchmark_manifest.json.

    Returns:
        Validated manifest dict with keys: version, pipeline_config,
        scenarios.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        ValueError: If required keys are missing or malformed.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data: dict = json.load(fh)
    validate_manifest(data)
    return data


def validate_manifest(data: dict) -> None:
    """Validate manifest structure.

    Checks for required top-level keys (version, pipeline_config,
    scenarios), required per-scenario keys, and required pipeline_config
    keys.

    Args:
        data: Manifest dict to validate.

    Raises:
        ValueError: With descriptive message identifying the missing or
            invalid key.
    """
    for key in sorted(_REQUIRED_TOP_LEVEL_KEYS):
        if key not in data:
            raise ValueError(f"Missing required key: {key}")

    _validate_pipeline_config(data["pipeline_config"])
    _validate_scenarios(data["scenarios"])


def _validate_pipeline_config(config: Any) -> None:
    """Check that *config* contains all required pipeline_config keys."""
    if not isinstance(config, dict):
        raise ValueError("pipeline_config must be a dict")
    for key in sorted(_REQUIRED_PIPELINE_CONFIG_KEYS):
        if key not in config:
            raise ValueError(
                f"Missing required pipeline_config key: {key}"
            )


def _validate_scenarios(scenarios: Any) -> None:
    """Check that every scenario entry contains all required keys."""
    if not isinstance(scenarios, list):
        raise ValueError("scenarios must be a list")
    for idx, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError(f"Scenario at index {idx} must be a dict")
        for key in sorted(_REQUIRED_SCENARIO_KEYS):
            if key not in scenario:
                name = scenario.get("scenario_file", f"index {idx}")
                raise ValueError(
                    f"Scenario '{name}' missing required key: {key}"
                )


def manifest_to_dict(manifest: dict) -> dict:
    """Produce a JSON-serializable dict from a manifest.

    This is the identity function for well-formed manifests (they are
    already plain dicts), but serves as the explicit "print" half of
    the round-trip contract.

    Args:
        manifest: Validated manifest dict.

    Returns:
        JSON-serializable dict.
    """
    return dict(manifest)


def save_manifest(manifest: dict, path: str) -> None:
    """Write a manifest dict to a JSON file with 2-space indentation.

    Args:
        manifest: Validated manifest dict.
        path: Output file path.
    """
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
