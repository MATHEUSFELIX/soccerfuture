"""Commentator payload schema registry.

Detects payload schema versions, validates required structure, and
reports compatibility status for incoming tracking payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Schema version definitions
# ---------------------------------------------------------------------------

SCHEMA_V1_REQUIRED_KEYS = {"players", "ball_positions", "clip_reference"}
SCHEMA_V1_CLIP_REQUIRED_KEYS = {"source_path", "start_time", "end_time"}
SCHEMA_V1_PLAYER_REQUIRED_KEYS = {"player_id", "x", "y", "timestamp", "confidence"}
SCHEMA_V1_BALL_REQUIRED_KEYS = {"x", "y", "timestamp", "confidence"}

KNOWN_SCHEMA_VERSIONS = {"v1"}


@dataclass
class SchemaDetectionResult:
    """Result of schema version detection.

    Attributes:
        version: Detected schema version ("v1" or "unknown").
        compatible: Whether the payload is structurally compatible.
        missing_keys: Top-level keys that are missing.
        warnings: Non-critical structural issues.
        errors: Critical structural issues preventing ingestion.
    """

    version: str
    compatible: bool
    missing_keys: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Detection logic
# ---------------------------------------------------------------------------


def detect_schema_version(payload: dict) -> SchemaDetectionResult:
    """Detect the schema version of a commentator payload.

    Currently supports v1 detection. Returns "unknown" if the payload
    does not match any known schema.

    Args:
        payload: Raw dict from a commentator fixture or data source.

    Returns:
        A SchemaDetectionResult with version, compatibility, and diagnostics.
    """
    if not isinstance(payload, dict):
        return SchemaDetectionResult(
            version="unknown",
            compatible=False,
            errors=["Payload is not a dict"],
        )

    # Check v1 required top-level keys
    missing_top = sorted(SCHEMA_V1_REQUIRED_KEYS - set(payload.keys()))
    if missing_top:
        return SchemaDetectionResult(
            version="unknown",
            compatible=False,
            missing_keys=missing_top,
            errors=[f"Missing required top-level keys: {', '.join(missing_top)}"],
        )

    warnings: list[str] = []
    errors: list[str] = []

    # Validate clip_reference structure
    clip_ref = payload.get("clip_reference")
    if not isinstance(clip_ref, dict):
        errors.append("clip_reference is not a dict")
    else:
        missing_clip = sorted(SCHEMA_V1_CLIP_REQUIRED_KEYS - set(clip_ref.keys()))
        if missing_clip:
            errors.append(f"clip_reference missing keys: {', '.join(missing_clip)}")

    # Validate players structure
    players = payload.get("players")
    if not isinstance(players, list):
        errors.append("players is not a list")
    elif len(players) == 0:
        errors.append("players list is empty")
    else:
        # Check first player entry
        first_player = players[0]
        if isinstance(first_player, dict):
            missing_p = sorted(SCHEMA_V1_PLAYER_REQUIRED_KEYS - set(first_player.keys()))
            if missing_p:
                warnings.append(f"First player entry missing keys: {', '.join(missing_p)}")

    # Validate ball_positions structure
    ball_positions = payload.get("ball_positions")
    if not isinstance(ball_positions, list):
        errors.append("ball_positions is not a list")
    elif len(ball_positions) == 0:
        errors.append("ball_positions list is empty")
    else:
        first_ball = ball_positions[0]
        if isinstance(first_ball, dict):
            missing_b = sorted(SCHEMA_V1_BALL_REQUIRED_KEYS - set(first_ball.keys()))
            if missing_b:
                warnings.append(f"First ball entry missing keys: {', '.join(missing_b)}")

    # Optional field warnings
    if "frame_rate" not in payload:
        warnings.append("frame_rate not present; will use default")

    compatible = len(errors) == 0
    version = "v1" if compatible else "unknown"

    return SchemaDetectionResult(
        version=version,
        compatible=compatible,
        missing_keys=missing_top if not compatible else [],
        warnings=warnings,
        errors=errors,
    )


def validate_payload_structure(payload: dict) -> SchemaDetectionResult:
    """Validate a payload and return full diagnostics.

    Alias for detect_schema_version with the same behavior.

    Args:
        payload: Raw dict to validate.

    Returns:
        A SchemaDetectionResult.
    """
    return detect_schema_version(payload)
