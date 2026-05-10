"""Unit tests for src/integrations/commentator_payload_normalizer.py."""

import pytest

from src.integrations.commentator_payload_normalizer import (
    NormalizationResult,
    normalize_payload,
)


def _valid_payload() -> dict:
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


class TestNormalizePayload:
    def test_valid_payload_not_rejected(self):
        result = normalize_payload(_valid_payload())
        assert result.rejected is False
        assert "players" in result.payload
        assert "ball_positions" in result.payload

    def test_non_dict_rejected(self):
        result = normalize_payload("not a dict")
        assert result.rejected is True

    def test_missing_clip_reference_rejected(self):
        payload = {"players": [{"player_id": "p1", "x": 1, "y": 2, "timestamp": 0, "confidence": 0.9}],
                   "ball_positions": [{"x": 1, "y": 2, "timestamp": 0, "confidence": 0.9}]}
        result = normalize_payload(payload)
        assert result.rejected is True

    def test_empty_players_rejected(self):
        payload = _valid_payload()
        payload["players"] = []
        result = normalize_payload(payload)
        assert result.rejected is True

    def test_alias_clip_to_clip_reference(self):
        payload = _valid_payload()
        payload["clip"] = payload.pop("clip_reference")
        result = normalize_payload(payload)
        assert result.rejected is False
        assert "clip_reference" in result.payload
        assert any("clip" in fix for fix in result.applied_fixes)

    def test_alias_player_id_field(self):
        payload = _valid_payload()
        payload["players"] = [{"id": "p1", "x": 10, "y": 20, "timestamp": 1, "confidence": 0.9}]
        result = normalize_payload(payload)
        assert result.rejected is False
        assert result.payload["players"][0].get("player_id") == "p1"

    def test_string_numeric_coercion(self):
        payload = _valid_payload()
        payload["players"] = [{"player_id": "p1", "x": "10.5", "y": "20.3", "timestamp": "1.0", "confidence": "0.9"}]
        result = normalize_payload(payload)
        assert result.rejected is False
        assert result.payload["players"][0]["x"] == 10.5

    def test_missing_confidence_defaults(self):
        payload = _valid_payload()
        payload["players"] = [{"player_id": "p1", "x": 10, "y": 20, "timestamp": 1}]
        result = normalize_payload(payload)
        assert result.rejected is False
        assert result.payload["players"][0]["confidence"] == 0.5
        assert any("confidence" in fix for fix in result.applied_fixes)

    def test_missing_frame_rate_defaults(self):
        payload = _valid_payload()
        del payload["frame_rate"]
        result = normalize_payload(payload)
        assert result.rejected is False
        assert result.payload["frame_rate"] == 25.0
