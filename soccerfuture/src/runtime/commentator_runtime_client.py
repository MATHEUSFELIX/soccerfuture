"""Runtime client for loading commentator outputs.

Discovers and loads commentator tracking payloads from configured
sources (local path, watched directory, or provider).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field

from src.runtime.commentator_runtime_config import RuntimeConfig


@dataclass
class RuntimePayload:
    """A single loaded runtime payload with provenance.

    Attributes:
        payload: The raw dict loaded from the source.
        source_path: Path or reference where the payload was loaded from.
        source_type: How it was discovered.
        load_notes: Notes about the loading process.
    """

    payload: dict
    source_path: str
    source_type: str
    load_notes: list[str] = field(default_factory=list)


def load_from_local_path(path: str) -> RuntimePayload:
    """Load a single commentator payload from a local JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        A RuntimePayload with the parsed dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Runtime payload file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    return RuntimePayload(
        payload=data,
        source_path=path,
        source_type="local_path",
        load_notes=[f"Loaded from {path}"],
    )


def discover_from_watched_directory(directory: str) -> list[str]:
    """Discover JSON files in a watched directory.

    Args:
        directory: Path to the directory to scan.

    Returns:
        Sorted list of JSON file paths found.

    Raises:
        FileNotFoundError: If the directory does not exist.
    """
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Watched directory not found: {directory}")

    files = sorted(
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.endswith(".json")
    )
    return files


def load_from_watched_directory(directory: str) -> list[RuntimePayload]:
    """Load all JSON payloads from a watched directory.

    Args:
        directory: Path to the directory to scan.

    Returns:
        List of RuntimePayload instances, one per file.
    """
    paths = discover_from_watched_directory(directory)
    payloads: list[RuntimePayload] = []

    for path in paths:
        try:
            payload = load_from_local_path(path)
            payload.source_type = "watched_directory"
            payloads.append(payload)
        except (json.JSONDecodeError, OSError) as exc:
            payloads.append(RuntimePayload(
                payload={},
                source_path=path,
                source_type="watched_directory",
                load_notes=[f"Failed to load: {exc}"],
            ))

    return payloads


def load_from_provider(
    provider_name: str,
    provider_config: dict,
    fetcher: Callable[[str, dict], list[dict]] | None = None,
) -> list[RuntimePayload]:
    """Load payloads from a configured provider.

    Args:
        provider_name: Provider identifier.
        provider_config: Provider-specific configuration.
        fetcher: Optional callable that returns a list of raw dicts.
            Signature: (provider_name, provider_config) -> list[dict].

    Returns:
        List of RuntimePayload instances.
    """
    if fetcher is None:
        return [RuntimePayload(
            payload={},
            source_path=provider_name,
            source_type="provider",
            load_notes=[f"No fetcher configured for provider '{provider_name}'"],
        )]

    raw_list = fetcher(provider_name, provider_config)
    payloads: list[RuntimePayload] = []
    for i, raw in enumerate(raw_list):
        payloads.append(RuntimePayload(
            payload=raw,
            source_path=f"{provider_name}:{i}",
            source_type="provider",
            load_notes=[f"Fetched from provider '{provider_name}', index {i}"],
        ))
    return payloads


def load_payloads(
    config: RuntimeConfig,
    provider_fetcher: Callable | None = None,
) -> list[RuntimePayload]:
    """Load payloads according to the runtime configuration.

    Args:
        config: The runtime configuration.
        provider_fetcher: Optional provider fetcher callable.

    Returns:
        List of RuntimePayload instances.
    """
    if config.source_type == "local_path":
        return [load_from_local_path(config.source_path)]
    elif config.source_type == "watched_directory":
        return load_from_watched_directory(config.source_path)
    elif config.source_type == "provider":
        return load_from_provider(
            config.provider_name, config.provider_config, provider_fetcher,
        )
    else:
        raise ValueError(f"Unknown source_type: {config.source_type}")
