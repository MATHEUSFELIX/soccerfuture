"""Semantic regression tests for pipeline tactical behavior.

Validates that the pipeline produces tactically appropriate branches for
each demo scenario. These tests encode domain-level expectations about
which branch families should dominate or be suppressed, beyond structural
correctness.

Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 12.1, 12.2, 12.3, 12.4
"""

import json
from collections import defaultdict

import pytest

from src.models.pipeline_report import PipelineReport
from src.models.play_state import dict_to_play_state
from src.pipeline import PipelineConfig, run_pipeline

# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

_CONFIG = PipelineConfig(n=20, k=5, seed=42)

_SET_PIECE_PATH = "data/play_states/set_piece_penalty_area.json"
_BUILD_UP_PATH = "data/play_states/build_up_from_defense.json"
_COUNTER_ATTACK_PATH = "data/play_states/counter_attack_midfield.json"

_ALL_SCENARIO_PATHS = {
    "set_piece": _SET_PIECE_PATH,
    "build_up": _BUILD_UP_PATH,
    "counter_attack": _COUNTER_ATTACK_PATH,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_strategy(branch: dict) -> str:
    """Extract the perturbation strategy from a branch dict."""
    return branch.get("metadata", {}).get("strategy", "unknown")


def _group_positions_by_player(positions: list[dict]) -> dict[str, list[dict]]:
    """Group a flat positions list into per-player lists ordered by timestamp."""
    by_player: dict[str, list[dict]] = defaultdict(list)
    for p in positions:
        by_player[p["player_id"]].append(p)
    for plist in by_player.values():
        plist.sort(key=lambda p: p["timestamp"])
    return dict(by_player)


def _run_scenario(path: str) -> PipelineReport:
    """Load a scenario file and run the pipeline with default config."""
    with open(path) as f:
        ps = dict_to_play_state(json.load(f))
    return run_pipeline(ps, _CONFIG)


# ---------------------------------------------------------------------------
# Module-scoped fixtures — run pipeline once per scenario, reuse across tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def set_piece_report() -> PipelineReport:
    """Run pipeline on set_piece_penalty_area once for all set-piece tests."""
    return _run_scenario(_SET_PIECE_PATH)


@pytest.fixture(scope="module")
def build_up_report() -> PipelineReport:
    """Run pipeline on build_up_from_defense once for all build-up tests."""
    return _run_scenario(_BUILD_UP_PATH)


@pytest.fixture(scope="module")
def all_scenario_reports() -> dict[str, PipelineReport]:
    """Run pipeline on all 3 scenarios for cross-scenario tests."""
    return {name: _run_scenario(path) for name, path in _ALL_SCENARIO_PATHS.items()}


# ---------------------------------------------------------------------------
# Set-piece tests (Req 3)
# ---------------------------------------------------------------------------


class TestSetPieceBehavior:
    """Tactical expectations for the set_piece_penalty_area scenario."""

    def test_set_piece_no_excessive_forward_movement(
        self, set_piece_report: PipelineReport
    ) -> None:
        """No top-K branch should have a majority of positions projecting
        more than 20 meters beyond the ball position in a set piece.

        Validates: Requirements 3.1
        """
        with open(_SET_PIECE_PATH) as f:
            ball_y = json.load(f)["ball_position"]["y"]

        for rb in set_piece_report.ranked_branches:
            positions = rb.branch.get("positions", [])
            by_player = _group_positions_by_player(positions)

            far_forward_players = 0
            total_players = len(by_player)

            for player_id, plist in by_player.items():
                far_count = sum(
                    1 for p in plist if p["y"] > ball_y + 20
                )
                if far_count > len(plist) / 2:
                    far_forward_players += 1

            assert far_forward_players <= total_players / 2, (
                f"Set-piece branch {rb.branch_id} has {far_forward_players} of "
                f"{total_players} players with majority of positions >20m "
                f"beyond ball (ball_y={ball_y}). Set-piece scenarios should "
                f"favor structured positioning, not long runs."
            )

    def test_set_piece_has_decision_variation_in_top_k(
        self, set_piece_report: PipelineReport
    ) -> None:
        """At least one top-K branch should use the decision_variation strategy,
        representing tactical alternatives near the penalty area.

        Validates: Requirements 3.2
        """
        strategies = [
            _get_strategy(rb.branch) for rb in set_piece_report.ranked_branches
        ]
        assert "decision_variation" in strategies, (
            f"Set-piece top-K branches use strategies {strategies} but none is "
            f"'decision_variation'. Near the penalty area, the pipeline should "
            f"surface at least one tactical alternative."
        )

    def test_set_piece_average_score_above_threshold(
        self, set_piece_report: PipelineReport
    ) -> None:
        """The average composite score of top-K branches should exceed 0.3.

        Validates: Requirements 3.3
        """
        scores = [rb.composite_score for rb in set_piece_report.ranked_branches]
        avg = sum(scores) / len(scores) if scores else 0.0
        assert avg > 0.3, (
            f"Set-piece top-K average composite score is {avg:.4f}, which is "
            f"below the 0.3 threshold. The pipeline should produce viable "
            f"branches for a set-piece near the penalty area."
        )


# ---------------------------------------------------------------------------
# Build-up tests (Req 4)
# ---------------------------------------------------------------------------


class TestBuildUpBehavior:
    """Tactical expectations for the build_up_from_defense scenario."""

    def test_build_up_has_route_variation_in_top_k(
        self, build_up_report: PipelineReport
    ) -> None:
        """At least one top-K branch should use the route_variation strategy,
        representing passing options for building up from defense.

        Validates: Requirements 4.1
        """
        strategies = [
            _get_strategy(rb.branch) for rb in build_up_report.ranked_branches
        ]
        assert "route_variation" in strategies, (
            f"Build-up top-K branches use strategies {strategies} but none "
            f"is 'route_variation'. When building from defense, the "
            f"pipeline should surface at least one passing option."
        )

    def test_build_up_no_stagnant_branches_in_top_k(
        self, build_up_report: PipelineReport
    ) -> None:
        """No top-K branch should have all player positions within 2 meters
        of their starting positions (ultra-conservative stagnation).

        Validates: Requirements 4.2
        """
        for rb in build_up_report.ranked_branches:
            positions = rb.branch.get("positions", [])
            by_player = _group_positions_by_player(positions)

            all_stagnant = True
            for player_id, plist in by_player.items():
                if not plist:
                    continue
                start_y = plist[0]["y"]
                start_x = plist[0]["x"]
                for p in plist[1:]:
                    dy = abs(p["y"] - start_y)
                    dx = abs(p["x"] - start_x)
                    displacement = (dx ** 2 + dy ** 2) ** 0.5
                    if displacement > 2.0:
                        all_stagnant = False
                        break
                if not all_stagnant:
                    break

            assert not all_stagnant, (
                f"Build-up branch {rb.branch_id} has all player positions "
                f"within 2 meters of their starting positions. When building "
                f"from defense, ultra-conservative stagnation should not "
                f"appear in top-K."
            )

    def test_build_up_average_score_above_threshold(
        self, build_up_report: PipelineReport
    ) -> None:
        """The average composite score of top-K branches should exceed 0.25.

        Validates: Requirements 4.3
        """
        scores = [rb.composite_score for rb in build_up_report.ranked_branches]
        avg = sum(scores) / len(scores) if scores else 0.0
        assert avg > 0.25, (
            f"Build-up top-K average composite score is {avg:.4f}, which "
            f"is below the 0.25 threshold. The pipeline should produce viable "
            f"branches for building up from defense."
        )


# ---------------------------------------------------------------------------
# Physical failure tests (Req 5) — cross-scenario
# ---------------------------------------------------------------------------


class TestPhysicalFailureRejection:
    """Validate that the pipeline never promotes physically implausible branches."""

    def test_all_scenarios_top_k_passed_gating(
        self, all_scenario_reports: dict[str, PipelineReport]
    ) -> None:
        """Every top-K branch across all scenarios must have passed_gating=True.

        Validates: Requirements 5.1
        """
        for scenario_name, report in all_scenario_reports.items():
            for rb in report.ranked_branches:
                er = rb.evaluation_report
                assert er["passed_gating"] is True, (
                    f"[{scenario_name}] Top-K branch {rb.branch_id} has "
                    f"passed_gating=False. The pipeline must never promote a "
                    f"branch that failed physical gating checks."
                )

    def test_all_scenarios_top_k_validity_above_minimum(
        self, all_scenario_reports: dict[str, PipelineReport]
    ) -> None:
        """Every top-K branch across all scenarios must have validity_score > 0.2.

        Validates: Requirements 5.2
        """
        for scenario_name, report in all_scenario_reports.items():
            for rb in report.ranked_branches:
                er = rb.evaluation_report
                validity = er["validity_score"]
                assert validity > 0.2, (
                    f"[{scenario_name}] Top-K branch {rb.branch_id} has "
                    f"validity_score={validity:.4f}, which is below the 0.2 "
                    f"minimum. Promoted branches must be physically plausible."
                )

    def test_all_scenarios_gating_failures_have_explanations(
        self, all_scenario_reports: dict[str, PipelineReport]
    ) -> None:
        """Every branch that failed gating must have at least one explanation.

        Validates: Requirements 5.3
        """
        for scenario_name, report in all_scenario_reports.items():
            for eb in report.evaluated_branches:
                er = eb["evaluation_report"]
                if not er["passed_gating"]:
                    explanations = er.get("explanations", [])
                    assert len(explanations) > 0, (
                        f"[{scenario_name}] Branch {er['branch_id']} failed "
                        f"gating but has no explanations. Every gating failure "
                        f"must include a human-readable reason."
                    )
