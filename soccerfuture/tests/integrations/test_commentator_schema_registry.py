"""Unit tests for src/integrations/commentator_schema_registry.py."""

import pytest

from src.integrations.commentator_schema_registry import (
    SchemaDetectionResult,
    detect_schema_version,
    validate_payload_structure,
)


def _valid_v1_payload() -> dict:
    return {
        "players": [
            {"player_id": "p1", "x": 10.0, "y": 20.0, "timestamp": 1.0, "confidence": 0.9},
        ],
        "ball_positions": [
            {"x": 10.0, "y": 20.0, "timestamp": 1.0, "confidence": 0.9},
        ],
        "clip_reference": {
            "source_path": "/test.mp4",
            "start_time": 0.0,
            "end_time": 5.0,
        },
        "frame_rate": 25.0,
    }


class TestDetectSchemaVersion:
    def test_valid_v1_detected(self):
        result = detect_schema_version(_valid_v1_payload())
        assert result.version == "v1"
        assert result.compatible is True

    def test_missing_players_unknown(self):
        payload = _valid_v1_payload()
        del payload["players"]
        result = detect_schema_version(payload)
        assert result.version == "unknown"
        assert result.compatible is False
        assert "players" in result.missing_keys

    def test_missing_clip_reference_unknown(self):
        payload = _valid_v1_payload()
        del payload["clip_reference"]
        result = detect_schema_version(payload)
        assert result.version == "unknown"
        assert result.compatible is False

    def test_empty_players_error(self):
        payload = _valid_v1_payload()
        payload["players"] = []
        result = detect_schema_version(payload)
        assert result.compatible is False
        assert any("empty" in e for e in result.errors)

    def test_non_dict_payload(self):
        result = detect_schema_version("not a dict")
        assert result.version == "unknown"
        assert result.compatible is False

    def test_missing_frame_rate_warning(self):
        payload = _valid_v1_payload()
        del payload["frame_rate"]
        result = detect_schema_version(payload)
        assert result.compatible is True
        assert any("frame_rate" in w for w in result.warnings)

    def test_deterministic(self):
        payload = _valid_v1_payload()
        r1 = detect_schema_version(payload)
        r2 = detect_schema_version(payload)
        assert r1.version == r2.version
        assert r1.compatible == r2.compatible

    def test_validate_is_alias(self):
        payload = _valid_v1_payload()
        r1 = detect_schema_version(payload)
        r2 = validate_payload_structure(payload)
        assert r1.version == r2.version
