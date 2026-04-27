"""Property-based tests for PipelineReport serialization.

Feature: branch-generation-pipeline
- Property 15: PipelineReport round-trip serialization

Validates: Requirements 8.5, 8.6
"""

import json

from hypothesis import given, settings

from src.models.pipeline_report import PipelineReport
from tests.strategies import pipeline_report_strategy


class TestPipelineReportRoundTripProperty:
    """Property 15: PipelineReport round-trip serialization.

    For any valid PipelineReport, calling to_dict(), converting to JSON
    via json.dumps, deserializing via json.loads, and reconstructing via
    PipelineReport.from_dict() SHALL produce an equivalent PipelineReport.
    """

    @given(report=pipeline_report_strategy())
    @settings(max_examples=100)
    def test_round_trip_serialization(self, report: PipelineReport) -> None:
        """**Validates: Requirements 8.5, 8.6**

        Feature: branch-generation-pipeline, Property 15: PipelineReport round-trip serialization
        """
        # Serialize
        as_dict = report.to_dict()
        json_str = json.dumps(as_dict)

        # Deserialize
        restored_dict = json.loads(json_str)
        restored = PipelineReport.from_dict(restored_dict)

        # Assert equivalence on all fields
        assert restored.play_state == report.play_state
        assert restored.evaluated_branches == report.evaluated_branches
        assert restored.metadata == report.metadata
        assert restored.errors == report.errors

        # Assert ranked branches match
        assert len(restored.ranked_branches) == len(report.ranked_branches)
        for orig_rb, rest_rb in zip(report.ranked_branches, restored.ranked_branches):
            assert rest_rb.branch_id == orig_rb.branch_id
            assert rest_rb.composite_score == orig_rb.composite_score
            assert rest_rb.evaluation_report == orig_rb.evaluation_report
            assert rest_rb.branch == orig_rb.branch
