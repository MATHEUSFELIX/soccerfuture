"""Unit tests for PipelineReport and RankedBranch models.

Tests dataclass construction, to_dict JSON serializability,
from_dict round-trip reconstruction, and default field values.

Requirements: 8.1, 8.5, 8.7
"""

import json

from src.models.pipeline_report import PipelineReport, RankedBranch


def _make_ranked_branch(**overrides) -> RankedBranch:
    """Create a RankedBranch with sensible defaults."""
    defaults = dict(
        branch_id="gen-001",
        composite_score=0.75,
        evaluation_report={"validity_score": 0.8, "opportunity_score": 0.7},
        branch={"positions": [{"player_id": "P1", "x": 10.0, "y": 20.0}]},
    )
    defaults.update(overrides)
    return RankedBranch(**defaults)


def _make_pipeline_report(**overrides) -> PipelineReport:
    """Create a PipelineReport with sensible defaults."""
    defaults = dict(
        play_state={"match_time": 45.0, "possession_team": "home"},
        evaluated_branches=[
            {"branch_id": "gen-001", "validity_score": 0.8},
            {"branch_id": "gen-002", "validity_score": 0.6},
        ],
        ranked_branches=[_make_ranked_branch()],
        metadata={"seed": 42, "n_generated": 20, "k_requested": 5},
        errors=[],
    )
    defaults.update(overrides)
    return PipelineReport(**defaults)


class TestRankedBranchConstruction:
    """Tests for RankedBranch dataclass instantiation."""

    def test_construction_with_all_fields(self) -> None:
        rb = RankedBranch(
            branch_id="gen-005",
            composite_score=0.92,
            evaluation_report={"validity_score": 0.95, "opportunity_score": 0.89},
            branch={"positions": [], "events": []},
        )
        assert rb.branch_id == "gen-005"
        assert rb.composite_score == 0.92
        assert rb.evaluation_report == {"validity_score": 0.95, "opportunity_score": 0.89}
        assert rb.branch == {"positions": [], "events": []}


class TestPipelineReportConstruction:
    """Tests for PipelineReport dataclass instantiation."""

    def test_construction_with_all_fields(self) -> None:
        ranked = [_make_ranked_branch()]
        report = PipelineReport(
            play_state={"match_time": 30.0, "game_phase": "open_play"},
            evaluated_branches=[{"branch_id": "gen-001"}],
            ranked_branches=ranked,
            metadata={"seed": 42},
            errors=["branch gen-003 failed"],
        )
        assert report.play_state == {"match_time": 30.0, "game_phase": "open_play"}
        assert report.evaluated_branches == [{"branch_id": "gen-001"}]
        assert report.ranked_branches == ranked
        assert report.metadata == {"seed": 42}
        assert report.errors == ["branch gen-003 failed"]

    def test_default_empty_errors_list(self) -> None:
        report = PipelineReport(
            play_state={},
            evaluated_branches=[],
            ranked_branches=[],
        )
        assert report.errors == []
        assert isinstance(report.errors, list)

    def test_default_empty_metadata(self) -> None:
        report = PipelineReport(
            play_state={},
            evaluated_branches=[],
            ranked_branches=[],
        )
        assert report.metadata == {}


class TestPipelineReportToDict:
    """Tests for PipelineReport.to_dict serialization."""

    def test_to_dict_produces_json_serializable_output(self) -> None:
        report = _make_pipeline_report()
        result = report.to_dict()

        # json.dumps must succeed without error
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_to_dict_contains_expected_keys(self) -> None:
        report = _make_pipeline_report()
        result = report.to_dict()

        expected_keys = {
            "play_state",
            "evaluated_branches",
            "ranked_branches",
            "metadata",
            "errors",
            "match_context",
            "context_signals",
        }
        assert set(result.keys()) == expected_keys

    def test_to_dict_ranked_branches_are_plain_dicts(self) -> None:
        report = _make_pipeline_report()
        result = report.to_dict()

        for rb in result["ranked_branches"]:
            assert isinstance(rb, dict)
            assert "branch_id" in rb
            assert "composite_score" in rb
            assert "evaluation_report" in rb
            assert "branch" in rb


class TestPipelineReportFromDict:
    """Tests for PipelineReport.from_dict deserialization."""

    def test_from_dict_round_trip(self) -> None:
        original = _make_pipeline_report()
        d = original.to_dict()
        restored = PipelineReport.from_dict(d)

        assert restored.play_state == original.play_state
        assert restored.evaluated_branches == original.evaluated_branches
        assert restored.metadata == original.metadata
        assert restored.errors == original.errors
        assert len(restored.ranked_branches) == len(original.ranked_branches)
        for orig_rb, rest_rb in zip(original.ranked_branches, restored.ranked_branches):
            assert rest_rb.branch_id == orig_rb.branch_id
            assert rest_rb.composite_score == orig_rb.composite_score
            assert rest_rb.evaluation_report == orig_rb.evaluation_report
            assert rest_rb.branch == orig_rb.branch

    def test_from_dict_via_json_round_trip(self) -> None:
        original = _make_pipeline_report()
        d = original.to_dict()
        json_str = json.dumps(d)
        restored_dict = json.loads(json_str)
        restored = PipelineReport.from_dict(restored_dict)

        assert restored.play_state == original.play_state
        assert restored.errors == original.errors
        assert len(restored.ranked_branches) == len(original.ranked_branches)

    def test_from_dict_with_empty_report(self) -> None:
        report = PipelineReport(
            play_state={},
            evaluated_branches=[],
            ranked_branches=[],
        )
        d = report.to_dict()
        restored = PipelineReport.from_dict(d)

        assert restored.play_state == {}
        assert restored.evaluated_branches == []
        assert restored.ranked_branches == []
        assert restored.metadata == {}
        assert restored.errors == []
