"""JSON serialization helpers for evaluation reports.

Provides round-trip conversion between ``EvaluationReport`` dataclass
instances and plain dictionaries suitable for ``json.dumps``.
"""

from dataclasses import asdict

from src.models.evaluation_report import EvaluationReport, SubMetrics


def report_to_dict(report: EvaluationReport) -> dict:
    """Convert an EvaluationReport dataclass to a JSON-serializable dict.

    Uses ``dataclasses.asdict()`` internally.  Preserves existing output
    field names so downstream consumers are unaffected.

    Args:
        report: The evaluation report to serialize.

    Returns:
        A plain dictionary that can be passed directly to ``json.dumps``.
    """
    return asdict(report)


def dict_to_report(data: dict) -> EvaluationReport:
    """Reconstruct an EvaluationReport from a JSON-deserialized dict.

    Inverse of ``report_to_dict`` for round-trip testing.  Handles the
    nested ``SubMetrics`` dataclass automatically.

    Args:
        data: A dictionary previously produced by ``report_to_dict``
            (or equivalent ``json.loads`` output).

    Returns:
        A fully reconstructed ``EvaluationReport`` instance.

    Raises:
        KeyError: If *data* is missing a required field.
        TypeError: If *data* contains values of the wrong type for
            the dataclass constructor.
    """
    sub_metrics_data = data["sub_metrics"]
    sub_metrics = SubMetrics(**sub_metrics_data)

    return EvaluationReport(
        branch_id=data["branch_id"],
        validity_score=data["validity_score"],
        opportunity_score=data["opportunity_score"],
        gating_flags=data["gating_flags"],
        explanations=data["explanations"],
        sub_metrics=sub_metrics,
        passed_gating=data["passed_gating"],
        passed_validity=data["passed_validity"],
    )
