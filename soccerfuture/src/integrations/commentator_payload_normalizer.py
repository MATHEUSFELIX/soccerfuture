"""Commentator payload normalizer.

Deterministically normalizes incoming payloads to the canonical v1
format, handling field name variants, missing optional fields, and
type coercion where safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.utils.constants import VIDEO_DEFAULT_FRAME_RATE


@dataclass
class NormalizationResult:
    """Result of payload normalization.

    Attributes:
        payload: The normalized payload dict (v1 canonical format).
        applied_fixes: List of normalization actions taken.
        warnings: Non-critical issues found during normalization.
        rejected: Whether the payload was too malformed to normalize.
        rejection_reason: Reason for rejection, if applicable.
    """

    payload: dict
    applied_fixes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rejected: bool = False
    rejection_reason: str = ""


# ---------------------------------------------------------------------------
# Field name aliases
# ---------------------------------------------------------------------------

_PLAYER_FIELD_ALIASES: dict[str, str] = {
    "id": "player_id",
    "playerId": "player_id",
    "player_id": "player_id",
    "pos_x": "x",
    "pos_y": "y",
    "time": "timestamp",
    "t": "timestamp",
    "conf": "confidence",
}

_BALL_FIELD_ALIASES: dict[str, str] = {
    "pos_x": "x",
    "pos_y": "y",
    "time": "timestamp",
    "t": "timestamp",
    "conf": "confidence",
}

_CLIP_FIELD_ALIASES: dict[str, str] = {
    "path": "source_path",
    "file": "source_path",
    "source": "source_path",
    "start": "start_time",
    "end": "end_time",
}


# ---------------------------------------------------------------------------
# Normalization logic
# ---------------------------------------------------------------------------


def _normalize_dict_keys(entry: dict, aliases: dict[str, str]) -> dict:
    """Normalize dict keys using an alias mapping.

    Args:
        entry: Raw dict with potentially aliased keys.
        aliases: Mapping of alias -> canonical key name.

    Returns:
        Dict with canonical key names.
    """
    normalized: dict = {}
    for key, value in entry.items():
        canonical = aliases.get(key, key)
        normalized[canonical] = value
    return normalized


def _coerce_numeric(value, field_name: str) -> float | None:
    """Attempt to coerce a value to float.

    Args:
        value: The value to coerce.
        field_name: Name of the field (for diagnostics).

    Returns:
        Float value, or None if coercion fails.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def normalize_payload(payload: dict) -> NormalizationResult:
    """Normalize a commentator payload to canonical v1 format.

    Handles:
      - Field name aliases for players, ball, and clip_reference
      - Numeric type coercion for coordinates and timestamps
      - Default frame_rate when missing
      - Rejection of critically malformed payloads

    Args:
        payload: Raw dict from a commentator source.

    Returns:
        A NormalizationResult with the normalized payload and diagnostics.
    """
    if not isinstance(payload, dict):
        return NormalizationResult(
            payload={},
            rejected=True,
            rejection_reason="Payload is not a dict",
        )

    applied_fixes: list[str] = []
    warnings: list[str] = []

    # --- Normalize clip_reference ---
    clip_ref = payload.get("clip_reference", payload.get("clip", payload.get("video")))
    if clip_ref is None:
        return NormalizationResult(
            payload=payload,
            rejected=True,
            rejection_reason="No clip_reference, clip, or video field found",
        )
    if "clip" in payload and "clip_reference" not in payload:
        applied_fixes.append("Renamed 'clip' to 'clip_reference'")
    if "video" in payload and "clip_reference" not in payload and "clip" not in payload:
        applied_fixes.append("Renamed 'video' to 'clip_reference'")

    normalized_clip = _normalize_dict_keys(clip_ref, _CLIP_FIELD_ALIASES)

    # --- Normalize players ---
    players_raw = payload.get("players", payload.get("player_tracks", []))
    if "player_tracks" in payload and "players" not in payload:
        applied_fixes.append("Renamed 'player_tracks' to 'players'")

    if not isinstance(players_raw, list) or len(players_raw) == 0:
        return NormalizationResult(
            payload=payload,
            rejected=True,
            rejection_reason="No valid players data found",
        )

    normalized_players: list[dict] = []
    for i, entry in enumerate(players_raw):
        if not isinstance(entry, dict):
            warnings.append(f"Player entry {i} is not a dict, skipped")
            continue
        norm = _normalize_dict_keys(entry, _PLAYER_FIELD_ALIASES)

        # Coerce numeric fields
        for num_field in ("x", "y", "timestamp", "confidence"):
            if num_field in norm:
                coerced = _coerce_numeric(norm[num_field], num_field)
                if coerced is not None:
                    norm[num_field] = coerced
                else:
                    warnings.append(f"Player entry {i}: could not coerce {num_field}")

        # Default confidence if missing
        if "confidence" not in norm:
            norm["confidence"] = 0.5
            applied_fixes.append(f"Player entry {i}: defaulted confidence to 0.5")

        normalized_players.append(norm)

    if not normalized_players:
        return NormalizationResult(
            payload=payload,
            rejected=True,
            rejection_reason="All player entries were invalid",
        )

    # --- Normalize ball_positions ---
    ball_raw = payload.get("ball_positions", payload.get("ball", []))
    if "ball" in payload and "ball_positions" not in payload:
        applied_fixes.append("Renamed 'ball' to 'ball_positions'")

    if not isinstance(ball_raw, list) or len(ball_raw) == 0:
        return NormalizationResult(
            payload=payload,
            rejected=True,
            rejection_reason="No valid ball_positions data found",
        )

    normalized_ball: list[dict] = []
    for i, entry in enumerate(ball_raw):
        if not isinstance(entry, dict):
            warnings.append(f"Ball entry {i} is not a dict, skipped")
            continue
        norm = _normalize_dict_keys(entry, _BALL_FIELD_ALIASES)

        for num_field in ("x", "y", "timestamp", "confidence"):
            if num_field in norm:
                coerced = _coerce_numeric(norm[num_field], num_field)
                if coerced is not None:
                    norm[num_field] = coerced
                else:
                    warnings.append(f"Ball entry {i}: could not coerce {num_field}")

        if "confidence" not in norm:
            norm["confidence"] = 0.5
            applied_fixes.append(f"Ball entry {i}: defaulted confidence to 0.5")

        normalized_ball.append(norm)

    if not normalized_ball:
        return NormalizationResult(
            payload=payload,
            rejected=True,
            rejection_reason="All ball entries were invalid",
        )

    # --- Frame rate ---
    frame_rate = payload.get("frame_rate", VIDEO_DEFAULT_FRAME_RATE)
    if "frame_rate" not in payload:
        applied_fixes.append(f"Defaulted frame_rate to {VIDEO_DEFAULT_FRAME_RATE}")

    # --- Assemble normalized payload ---
    normalized_payload = {
        "players": normalized_players,
        "ball_positions": normalized_ball,
        "clip_reference": normalized_clip,
        "frame_rate": frame_rate,
    }

    return NormalizationResult(
        payload=normalized_payload,
        applied_fixes=applied_fixes,
        warnings=warnings,
        rejected=False,
    )
