"""Unit tests for src/review/review_feedback_schema.py."""

import json

import pytest

from src.review.review_feedback_schema import (
    ReviewFeedback,
    dict_to_feedback,
    feedback_to_dict,
)


def _make_feedback(**overrides) -> ReviewFeedback:
    defaults = dict(
        scenario_id="s1",
        reviewer_id="r1",
        top_1_plausibility="yes",
        top_3_usefulness="yes",
        summary_clarity=4,
        confidence_sufficiency=3,
    )
    defaults.update(overrides)
    return ReviewFeedback(**defaults)


class TestValidCreation:
    def test_basic_creation(self):
        fb = _make_feedback()
        assert fb.scenario_id == "s1"
        assert fb.summary_clarity == 4

    def test_optional_fields_default(self):
        fb = _make_feedback()
        assert fb.blockers == []
        assert fb.missing_capabilities == []
        assert fb.notes == ""

    def test_with_all_fields(self):
        fb = _make_feedback(
            blockers=["no real data"],
            missing_capabilities=["video support"],
            priority_suggestions=["improve speed"],
            notes="Good overall",
        )
        assert fb.blockers == ["no real data"]
        assert fb.notes == "Good overall"


class TestValidation:
    def test_invalid_plausibility_raises(self):
        with pytest.raises(ValueError, match="top_1_plausibility"):
            _make_feedback(top_1_plausibility="maybe")

    def test_invalid_usefulness_raises(self):
        with pytest.raises(ValueError, match="top_3_usefulness"):
            _make_feedback(top_3_usefulness="kinda")

    def test_clarity_below_min_raises(self):
        with pytest.raises(ValueError, match="summary_clarity"):
            _make_feedback(summary_clarity=0)

    def test_clarity_above_max_raises(self):
        with pytest.raises(ValueError, match="summary_clarity"):
            _make_feedback(summary_clarity=6)

    def test_confidence_below_min_raises(self):
        with pytest.raises(ValueError, match="confidence_sufficiency"):
            _make_feedback(confidence_sufficiency=0)

    def test_confidence_above_max_raises(self):
        with pytest.raises(ValueError, match="confidence_sufficiency"):
            _make_feedback(confidence_sufficiency=6)

    @pytest.mark.parametrize("val", ["yes", "no", "uncertain"])
    def test_valid_plausibility_values(self, val):
        fb = _make_feedback(top_1_plausibility=val)
        assert fb.top_1_plausibility == val

    @pytest.mark.parametrize("val", ["yes", "partially", "no", "uncertain"])
    def test_valid_usefulness_values(self, val):
        fb = _make_feedback(top_3_usefulness=val)
        assert fb.top_3_usefulness == val


class TestSerialization:
    def test_round_trip(self):
        fb = _make_feedback(blockers=["b1"], notes="test")
        d = feedback_to_dict(fb)
        restored = dict_to_feedback(d)
        assert restored.scenario_id == fb.scenario_id
        assert restored.blockers == fb.blockers
        assert restored.notes == fb.notes

    def test_json_serializable(self):
        fb = _make_feedback()
        d = feedback_to_dict(fb)
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

    def test_missing_required_field_raises(self):
        with pytest.raises(KeyError, match="scenario_id"):
            dict_to_feedback({"reviewer_id": "r1"})

    def test_invalid_value_in_dict_raises(self):
        d = feedback_to_dict(_make_feedback())
        d["summary_clarity"] = 99
        with pytest.raises(ValueError):
            dict_to_feedback(d)
