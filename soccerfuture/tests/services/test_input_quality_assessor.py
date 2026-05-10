"""Unit tests for src/services/input_quality_assessor.py."""

import pytest

from src.services.input_quality_assessor import (
    QualityAssessment,
    assess_quality,
    MIN_PLAYERS_GOOD,
    MIN_PLAYERS_ACCEPTABLE,
    MIN_PLAYERS_POOR,
)


def _make_payload(player_count=11, confidence=0.9, ball_count=2):
    players = [
        {"player_id": f"p{i}", "x": float(i), "y": float(i), "timestamp": 1.0, "confidence": confidence}
        for i in range(player_count)
    ]
    ball = [
        {"x": 10.0, "y": 20.0, "timestamp": 1.0, "confidence": confidence}
        for _ in range(ball_count)
    ]
    return {"players": players, "ball_positions": ball}


class TestAssessQuality:
    def test_good_quality(self):
        payload = _make_payload(player_count=11, confidence=0.9)
        result = assess_quality(payload)
        assert result.grade == "good"

    def test_acceptable_quality(self):
        payload = _make_payload(player_count=7, confidence=0.6)
        result = assess_quality(payload)
        assert result.grade == "acceptable"

    def test_poor_quality(self):
        payload = _make_payload(player_count=3, confidence=0.3)
        result = assess_quality(payload)
        assert result.grade == "poor"

    def test_rejected_too_few_players(self):
        payload = _make_payload(player_count=1)
        result = assess_quality(payload)
        assert result.grade == "rejected"

    def test_rejected_no_ball(self):
        payload = _make_payload(ball_count=0)
        result = assess_quality(payload)
        assert result.grade == "rejected"

    def test_player_count_reported(self):
        payload = _make_payload(player_count=8)
        result = assess_quality(payload)
        assert result.player_count == 8

    def test_avg_confidence_reported(self):
        payload = _make_payload(confidence=0.75)
        result = assess_quality(payload)
        assert result.avg_player_confidence == 0.75

    def test_issues_populated_for_low_confidence(self):
        payload = _make_payload(player_count=11, confidence=0.3)
        result = assess_quality(payload)
        assert len(result.issues) > 0

    def test_deterministic(self):
        payload = _make_payload()
        r1 = assess_quality(payload)
        r2 = assess_quality(payload)
        assert r1.grade == r2.grade
        assert r1.player_count == r2.player_count
