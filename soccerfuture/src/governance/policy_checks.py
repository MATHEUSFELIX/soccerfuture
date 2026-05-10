"""Policy checks for governance guardrails.

Evaluates whether a pipeline run should proceed, warn, or be blocked
based on input quality, artifact completeness, and confidence thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass, field


VALID_POLICY_OUTCOMES = {"allow", "warn", "block"}


@dataclass
class PolicyCheckResult:
    """Result of a single policy check.

    Attributes:
        check_name: Name of the policy check.
        outcome: One of "allow", "warn", "block".
        reason: Human-readable reason for the outcome.
    """

    check_name: str
    outcome: str
    reason: str = ""

    def __post_init__(self) -> None:
        if self.outcome not in VALID_POLICY_OUTCOMES:
            raise ValueError(
                f"outcome must be one of {sorted(VALID_POLICY_OUTCOMES)}, "
                f"got '{self.outcome}'"
            )


@dataclass
class PolicyEvaluation:
    """Aggregate policy evaluation for a run.

    Attributes:
        checks: List of individual check results.
        overall_outcome: Aggregate outcome (block if any block, warn if any warn).
        blocked: Whether the run should be blocked.
        warnings: List of warning messages.
    """

    checks: list[PolicyCheckResult] = field(default_factory=list)
    overall_outcome: str = "allow"
    blocked: bool = False
    warnings: list[str] = field(default_factory=list)


def check_input_quality(quality_grade: str) -> PolicyCheckResult:
    """Check whether input quality is acceptable for pipeline execution.

    Args:
        quality_grade: Quality grade from the assessor.

    Returns:
        PolicyCheckResult with appropriate outcome.
    """
    if quality_grade == "rejected":
        return PolicyCheckResult("input_quality", "block", "Input quality is rejected")
    if quality_grade == "poor":
        return PolicyCheckResult("input_quality", "warn", "Input quality is poor")
    return PolicyCheckResult("input_quality", "allow", "Input quality acceptable")


def check_confidence_threshold(confidence: float, threshold: float = 0.3) -> PolicyCheckResult:
    """Check whether confidence meets minimum threshold.

    Args:
        confidence: Confidence value (0.0–1.0).
        threshold: Minimum acceptable confidence.

    Returns:
        PolicyCheckResult with appropriate outcome.
    """
    if confidence < threshold:
        return PolicyCheckResult(
            "confidence_threshold", "warn",
            f"Confidence {confidence:.2f} below threshold {threshold}",
        )
    return PolicyCheckResult("confidence_threshold", "allow", "Confidence acceptable")


def check_artifacts_present(artifact_names: list[str], required: list[str] | None = None) -> PolicyCheckResult:
    """Check whether required artifacts are present.

    Args:
        artifact_names: List of artifact names that exist.
        required: List of required artifact names. Defaults to basic set.

    Returns:
        PolicyCheckResult with appropriate outcome.
    """
    if required is None:
        required = ["pipeline_report", "analyst_summary"]

    missing = [r for r in required if r not in artifact_names]
    if missing:
        return PolicyCheckResult(
            "artifacts_present", "warn",
            f"Missing artifacts: {', '.join(missing)}",
        )
    return PolicyCheckResult("artifacts_present", "allow", "All required artifacts present")


def evaluate_policy(
    quality_grade: str = "good",
    confidence: float = 1.0,
    artifact_names: list[str] | None = None,
) -> PolicyEvaluation:
    """Run all policy checks and compute aggregate outcome.

    Args:
        quality_grade: Input quality grade.
        confidence: Confidence value.
        artifact_names: List of artifact names present.

    Returns:
        A PolicyEvaluation with all check results and aggregate outcome.
    """
    checks: list[PolicyCheckResult] = []
    checks.append(check_input_quality(quality_grade))
    checks.append(check_confidence_threshold(confidence))
    checks.append(check_artifacts_present(artifact_names or []))

    blocked = any(c.outcome == "block" for c in checks)
    warnings = [c.reason for c in checks if c.outcome == "warn"]

    if blocked:
        overall = "block"
    elif warnings:
        overall = "warn"
    else:
        overall = "allow"

    return PolicyEvaluation(
        checks=checks,
        overall_outcome=overall,
        blocked=blocked,
        warnings=warnings,
    )
