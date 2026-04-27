"""Lightweight per-execution pipeline telemetry collector.

Provides timing instrumentation and branch-result accounting for the
pipeline orchestrator.  No external dependencies — uses only the
standard library and ``dataclasses``.
"""

import time
from dataclasses import dataclass, field


@dataclass
class TelemetryCollector:
    """Collects per-execution pipeline telemetry.

    Attributes:
        branches_generated: Total branches produced by the generator.
        hard_fail_count: Branches that failed gating.
        score_filtered_count: Branches that passed gating but fell below
            the validity threshold.
        avg_score_by_strategy: Running average composite score per
            perturbation strategy.
        scenario_id: Identifier for the scenario being evaluated.
        stage_timings: Wall-clock seconds per pipeline stage.
    """

    branches_generated: int = 0
    hard_fail_count: int = 0
    score_filtered_count: int = 0
    avg_score_by_strategy: dict[str, float] = field(default_factory=dict)
    scenario_id: str = ""
    _stage_starts: dict[str, float] = field(default_factory=dict, repr=False)
    stage_timings: dict[str, float] = field(default_factory=dict)
    _strategy_counts: dict[str, int] = field(default_factory=dict, repr=False)
    _strategy_totals: dict[str, float] = field(default_factory=dict, repr=False)

    def start_stage(self, stage_name: str) -> None:
        """Record the start time of a pipeline stage.

        Args:
            stage_name: Name of the stage (e.g. ``"generation"``).
        """
        self._stage_starts[stage_name] = time.monotonic()

    def end_stage(self, stage_name: str) -> None:
        """Record the end time and compute elapsed seconds for a stage.

        If ``start_stage`` was never called for *stage_name*, the elapsed
        time is recorded as ``0.0``.

        Args:
            stage_name: Name of the stage to finish.
        """
        start = self._stage_starts.pop(stage_name, None)
        if start is None:
            self.stage_timings[stage_name] = 0.0
        else:
            self.stage_timings[stage_name] = time.monotonic() - start

    def record_branch_result(
        self,
        strategy: str,
        composite_score: float,
        passed_gating: bool,
        passed_validity: bool,
    ) -> None:
        """Record the outcome of evaluating a single branch.

        Updates ``branches_generated``, ``hard_fail_count``,
        ``score_filtered_count``, and the running average for the given
        *strategy*.

        Args:
            strategy: Perturbation strategy name (e.g. ``"route_variation"``).
            composite_score: The branch's composite score.
            passed_gating: Whether the branch passed all gating checks.
            passed_validity: Whether the branch met the validity threshold.
        """
        self.branches_generated += 1

        if not passed_gating:
            self.hard_fail_count += 1
        elif not passed_validity:
            self.score_filtered_count += 1

        # Update running average for the strategy.
        self._strategy_counts[strategy] = self._strategy_counts.get(strategy, 0) + 1
        self._strategy_totals[strategy] = (
            self._strategy_totals.get(strategy, 0.0) + composite_score
        )
        count = self._strategy_counts[strategy]
        self.avg_score_by_strategy[strategy] = (
            self._strategy_totals[strategy] / count if count > 0 else 0.0
        )

    def to_dict(self) -> dict:
        """Produce the telemetry dict for inclusion in PipelineReport metadata.

        Returns:
            Dict with keys: ``branches_generated``, ``hard_fail_count``,
            ``score_filtered_count``, ``avg_score_by_strategy``,
            ``avg_score_by_scenario``, ``time_per_stage``.
        """
        return {
            "branches_generated": self.branches_generated,
            "hard_fail_count": self.hard_fail_count,
            "score_filtered_count": self.score_filtered_count,
            "avg_score_by_strategy": dict(self.avg_score_by_strategy),
            "avg_score_by_scenario": self.scenario_id,
            "time_per_stage": dict(self.stage_timings),
        }
