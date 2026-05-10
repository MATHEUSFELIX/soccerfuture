"""Unit tests for observability and governance modules."""

import json

import pytest

from src.observability.structured_logger import LogEntry, StructuredLogger
from src.observability.metrics_collector import MetricsCollector, MetricsSnapshot
from src.governance.provenance import ProvenanceRecord, provenance_to_dict, dict_to_provenance
from src.governance.policy_checks import (
    PolicyCheckResult,
    PolicyEvaluation,
    check_artifacts_present,
    check_confidence_threshold,
    check_input_quality,
    evaluate_policy,
)
from src.governance.audit_report import generate_audit_report


# ---------------------------------------------------------------------------
# StructuredLogger
# ---------------------------------------------------------------------------


class TestStructuredLogger:
    def test_info_creates_entry(self):
        logger = StructuredLogger()
        logger.info("test_event", "hello")
        assert len(logger.entries) == 1
        assert logger.entries[0].level == "INFO"

    def test_warn_creates_entry(self):
        logger = StructuredLogger()
        logger.warn("warning", "something off")
        assert logger.entries[0].level == "WARN"

    def test_error_creates_entry(self):
        logger = StructuredLogger()
        logger.error("failure", "broke")
        assert logger.entries[0].level == "ERROR"

    def test_context_captured(self):
        logger = StructuredLogger()
        logger.info("ev", "msg", scenario_id="s1", step="load")
        assert logger.entries[0].context == {"scenario_id": "s1", "step": "load"}

    def test_to_list(self):
        logger = StructuredLogger()
        logger.info("a", "b")
        result = logger.to_list()
        assert isinstance(result, list)
        assert result[0]["event"] == "a"

    def test_to_json(self):
        logger = StructuredLogger()
        logger.info("a", "b")
        j = logger.to_json()
        parsed = json.loads(j)
        assert len(parsed) == 1


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------


class TestMetricsCollector:
    def test_increment_counter(self):
        mc = MetricsCollector()
        mc.increment("runs")
        mc.increment("runs")
        assert mc.get_counter("runs") == 2

    def test_set_gauge(self):
        mc = MetricsCollector()
        mc.set_gauge("confidence", 0.85)
        assert mc.get_gauge("confidence") == 0.85

    def test_snapshot(self):
        mc = MetricsCollector()
        mc.increment("x")
        mc.set_gauge("y", 1.5)
        snap = mc.snapshot()
        assert isinstance(snap, MetricsSnapshot)
        assert snap.counters["x"] == 1
        assert snap.gauges["y"] == 1.5

    def test_to_dict(self):
        mc = MetricsCollector()
        mc.increment("a")
        d = mc.to_dict()
        assert d["counters"]["a"] == 1


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_creation(self):
        p = ProvenanceRecord(run_id="r1", scenario_id="s1")
        assert p.run_id == "r1"
        assert p.timestamp != ""

    def test_round_trip(self):
        p = ProvenanceRecord(
            run_id="r1", scenario_id="s1",
            artifacts_produced=["report", "summary"],
            notes=["test run"],
        )
        d = provenance_to_dict(p)
        restored = dict_to_provenance(d)
        assert restored.run_id == "r1"
        assert restored.artifacts_produced == ["report", "summary"]

    def test_json_serializable(self):
        p = ProvenanceRecord(run_id="r1", scenario_id="s1")
        d = provenance_to_dict(p)
        j = json.dumps(d)
        assert isinstance(j, str)


# ---------------------------------------------------------------------------
# PolicyChecks
# ---------------------------------------------------------------------------


class TestPolicyChecks:
    def test_rejected_quality_blocks(self):
        result = check_input_quality("rejected")
        assert result.outcome == "block"

    def test_poor_quality_warns(self):
        result = check_input_quality("poor")
        assert result.outcome == "warn"

    def test_good_quality_allows(self):
        result = check_input_quality("good")
        assert result.outcome == "allow"

    def test_low_confidence_warns(self):
        result = check_confidence_threshold(0.1)
        assert result.outcome == "warn"

    def test_high_confidence_allows(self):
        result = check_confidence_threshold(0.8)
        assert result.outcome == "allow"

    def test_missing_artifacts_warns(self):
        result = check_artifacts_present(["pipeline_report"])
        assert result.outcome == "warn"

    def test_all_artifacts_allows(self):
        result = check_artifacts_present(["pipeline_report", "analyst_summary"])
        assert result.outcome == "allow"

    def test_invalid_outcome_raises(self):
        with pytest.raises(ValueError):
            PolicyCheckResult("test", "invalid")

    def test_evaluate_policy_all_good(self):
        pe = evaluate_policy("good", 0.9, ["pipeline_report", "analyst_summary"])
        assert pe.overall_outcome == "allow"
        assert pe.blocked is False

    def test_evaluate_policy_blocked(self):
        pe = evaluate_policy("rejected", 0.9, [])
        assert pe.overall_outcome == "block"
        assert pe.blocked is True

    def test_evaluate_policy_warned(self):
        pe = evaluate_policy("poor", 0.9, ["pipeline_report", "analyst_summary"])
        assert pe.overall_outcome == "warn"
        assert pe.blocked is False


# ---------------------------------------------------------------------------
# AuditReport
# ---------------------------------------------------------------------------


class TestAuditReport:
    def test_basic_report(self):
        records = [ProvenanceRecord(run_id="r1", scenario_id="s1")]
        report = generate_audit_report(records)
        assert "# Audit Report" in report
        assert "s1" in report

    def test_report_with_policy(self):
        records = [ProvenanceRecord(run_id="r1", scenario_id="s1")]
        policies = [PolicyEvaluation(
            overall_outcome="warn", blocked=False, warnings=["low conf"],
        )]
        report = generate_audit_report(records, policies)
        assert "warn" in report
        assert "low conf" in report

    def test_empty_records(self):
        report = generate_audit_report([])
        assert "Total runs audited:** 0" in report
