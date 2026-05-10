"""Runtime configuration for commentator ingestion.

Defines the RuntimeConfig model specifying how the runtime client
discovers and loads commentator outputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


VALID_SOURCE_TYPES = {"local_path", "watched_directory", "provider"}


@dataclass
class RuntimeConfig:
    """Configuration for the commentator runtime client.

    Attributes:
        source_type: How to discover outputs ("local_path",
            "watched_directory", or "provider").
        source_path: File or directory path for local/watched modes.
        provider_name: Provider identifier for provider mode.
        provider_config: Additional provider-specific configuration.
        confidence_threshold: Minimum confidence for quality gating.
        auto_reject: Whether to auto-reject low-quality payloads.
        artifact_store_path: Directory for persisting ingested artifacts.
        notes: Free-text configuration notes.
    """

    source_type: str
    source_path: str = ""
    provider_name: str = ""
    provider_config: dict = field(default_factory=dict)
    confidence_threshold: float = 0.5
    auto_reject: bool = True
    artifact_store_path: str = "output/runtime_artifacts"
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.source_type not in VALID_SOURCE_TYPES:
            raise ValueError(
                f"source_type must be one of {sorted(VALID_SOURCE_TYPES)}, "
                f"got '{self.source_type}'"
            )
        if self.source_type in ("local_path", "watched_directory") and not self.source_path:
            raise ValueError(
                f"source_path is required for source_type '{self.source_type}'"
            )
        if self.source_type == "provider" and not self.provider_name:
            raise ValueError(
                "provider_name is required for source_type 'provider'"
            )


def config_to_dict(config: RuntimeConfig) -> dict:
    """Convert a RuntimeConfig to a JSON-serializable dict."""
    return asdict(config)


def dict_to_config(data: dict) -> RuntimeConfig:
    """Reconstruct a RuntimeConfig from a dict.

    Args:
        data: Dict previously produced by config_to_dict.

    Returns:
        A validated RuntimeConfig instance.

    Raises:
        KeyError: If required fields are missing.
        ValueError: If validation fails.
    """
    if "source_type" not in data:
        raise KeyError("Missing required field: source_type")
    return RuntimeConfig(
        source_type=data["source_type"],
        source_path=data.get("source_path", ""),
        provider_name=data.get("provider_name", ""),
        provider_config=data.get("provider_config", {}),
        confidence_threshold=data.get("confidence_threshold", 0.5),
        auto_reject=data.get("auto_reject", True),
        artifact_store_path=data.get("artifact_store_path", "output/runtime_artifacts"),
        notes=data.get("notes", ""),
    )
