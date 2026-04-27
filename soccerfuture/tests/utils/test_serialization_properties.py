"""Property-based tests for EvaluationReport round-trip serialization.

Feature: simulation-evaluator, Property 16: Evaluation report round-trip serialization

Validates: Requirements 9.5, 10.6
"""

import json

from hypothesis import given, settings

from src.models.evaluation_report import EvaluationReport
from src.utils.serialization import dict_to_report, report_to_dict
from tests.strategies import evaluation_report_strategy


class TestRoundTripSerializationProperty:
    """Property 16: Evaluation report round-trip serialization.

    For any valid EvaluationReport, serializing via report_to_dict + json.dumps
    then deserializing via json.loads + dict_to_report produces an equivalent
    EvaluationReport.
    """

    @given(report=evaluation_report_strategy())
    @settings(max_examples=100)
    def test_round_trip_serialization(self, report: EvaluationReport) -> None:
        """**Validates: Requirements 9.5, 10.6**

        Feature: simulation-evaluator, Property 16: Evaluation report round-trip serialization
        """
        # Serialize
        as_dict = report_to_dict(report)
        json_str = json.dumps(as_dict)

        # Deserialize
        restored_dict = json.loads(json_str)
        restored = dict_to_report(restored_dict)

        # Assert equivalence
        assert restored.branch_id == report.branch_id
        assert restored.validity_score == report.validity_score
        assert restored.opportunity_score == report.opportunity_score
        assert restored.gating_flags == report.gating_flags
        assert restored.explanations == report.explanations
        assert restored.passed_gating == report.passed_gating
        assert restored.passed_validity == report.passed_validity
        assert restored.sub_metrics == report.sub_metrics
        assert restored == report
