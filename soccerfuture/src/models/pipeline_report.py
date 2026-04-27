"""Data models for the branch generation pipeline report.

Defines the RankedBranch and PipelineReport dataclasses that capture
the complete output of the branch generation pipeline, including
evaluated branches, rankings, metadata, and errors.
"""

from dataclasses import dataclass, field


@dataclass
class RankedBranch:
    """A branch with its composite score for ranking.

    Attributes:
        branch_id: Identifier of the branch.
        composite_score: Weighted combination of validity and opportunity.
        evaluation_report: Full evaluation report as a dict.
        branch: The original branch dict.
    """

    branch_id: str
    composite_score: float
    evaluation_report: dict
    branch: dict


@dataclass
class PipelineReport:
    """Complete output of the branch generation pipeline.

    Attributes:
        play_state: The input PlayState as a dict.
        evaluated_branches: All generated branches paired with evaluation reports.
        ranked_branches: Top K branches sorted by composite score.
        metadata: Generation metadata (seed, n, k, gating_pass_count,
            execution_time_seconds).
        errors: List of error messages from branch-level or generator-level
            failures.
        match_context: Optional serialized MatchContext dict, if provided.
        context_signals: Optional serialized ContextSignals dict, if derived.
    """

    play_state: dict
    evaluated_branches: list[dict]
    ranked_branches: list[RankedBranch]
    metadata: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    match_context: dict | None = None
    context_signals: dict | None = None

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict.

        Nested ``RankedBranch`` objects are converted to plain dicts.

        Returns:
            Plain dict suitable for ``json.dumps()``.
        """
        return {
            "play_state": self.play_state,
            "evaluated_branches": self.evaluated_branches,
            "ranked_branches": [
                {
                    "branch_id": rb.branch_id,
                    "composite_score": rb.composite_score,
                    "evaluation_report": rb.evaluation_report,
                    "branch": rb.branch,
                }
                for rb in self.ranked_branches
            ],
            "metadata": self.metadata,
            "errors": self.errors,
            "match_context": self.match_context,
            "context_signals": self.context_signals,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineReport":
        """Reconstruct a PipelineReport from a JSON-deserialized dict.

        Nested ranked branch entries are converted back into
        ``RankedBranch`` instances.

        Args:
            data: Dict previously produced by ``to_dict()``.

        Returns:
            Reconstructed PipelineReport.
        """
        ranked_branches = [
            RankedBranch(
                branch_id=rb["branch_id"],
                composite_score=rb["composite_score"],
                evaluation_report=rb["evaluation_report"],
                branch=rb["branch"],
            )
            for rb in data.get("ranked_branches", [])
        ]
        return cls(
            play_state=data.get("play_state", {}),
            evaluated_branches=data.get("evaluated_branches", []),
            ranked_branches=ranked_branches,
            metadata=data.get("metadata", {}),
            errors=data.get("errors", []),
            match_context=data.get("match_context"),
            context_signals=data.get("context_signals"),
        )
