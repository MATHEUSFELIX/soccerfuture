"""Property-based tests for Branch Generator.

Feature: branch-generation-pipeline
- Property 2: Generator produces exactly N branches
- Property 3: Deterministic generation with same seed
- Property 4: Different seeds produce different output
- Property 5: Unique sequential branch IDs
- Property 6: Decision point timestamps match PlayState
- Property 7: At least three perturbation strategies used
- Property 8: Generated branches conform to Branch structure
- Property 9: Generated timestamps are ordered with valid gaps
- Property 10: At least 70% gating-compliant speeds
- Property 11: Synthesized ContinuationWindow is well-formed

Validates: Requirements 2.1, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4
"""

import math
import re
from collections import defaultdict

from hypothesis import given, settings
from hypothesis import strategies as st

from src.generation.branch_generator import generate_branches
from src.models.play_state import PlayState
from src.utils.constants import MAX_HUMAN_SPRINT_SPEED, MAX_TIMESTAMP_GAP
from tests.strategies import play_state_strategy

# Strategy for N in [10, 30]
_n_strategy = st.integers(min_value=10, max_value=30)
# Strategy for seeds
_seed_strategy = st.integers(min_value=0, max_value=2**31 - 1)


class TestProperty2GeneratorProducesExactlyNBranches:
    """Property 2: Generator produces exactly N branches.

    For any valid PlayState and any N in [10, 30], calling
    generate_branches(play_state, n=N, seed=s) SHALL return a
    GenerationResult containing exactly N branches.
    """

    @given(ps=play_state_strategy(), n=_n_strategy, seed=_seed_strategy)
    @settings(max_examples=100)
    def test_produces_exactly_n_branches(self, ps: PlayState, n: int, seed: int) -> None:
        """**Validates: Requirements 2.1**"""
        result = generate_branches(ps, n=n, seed=seed)
        assert len(result.branches) == n


class TestProperty3DeterministicGenerationWithSameSeed:
    """Property 3: Deterministic generation with same seed.

    For any valid PlayState, N, and seed, calling generate_branches twice
    with the same arguments SHALL produce identical branch lists.
    """

    @given(ps=play_state_strategy(), n=_n_strategy, seed=_seed_strategy)
    @settings(max_examples=100)
    def test_same_seed_produces_identical_branches(self, ps: PlayState, n: int, seed: int) -> None:
        """**Validates: Requirements 2.3**"""
        result_a = generate_branches(ps, n=n, seed=seed)
        result_b = generate_branches(ps, n=n, seed=seed)
        assert result_a.branches == result_b.branches
        assert result_a.continuation_window == result_b.continuation_window
        assert result_a.strategy_counts == result_b.strategy_counts


class TestProperty4DifferentSeedsProduceDifferentOutput:
    """Property 4: Different seeds produce different output.

    For any valid PlayState and N, calling generate_branches with two
    distinct seeds SHALL produce at least one differing branch.
    """

    @given(
        ps=play_state_strategy(),
        n=_n_strategy,
        seeds=st.tuples(
            st.integers(min_value=0, max_value=2**31 - 1),
            st.integers(min_value=0, max_value=2**31 - 1),
        ).filter(lambda t: t[0] != t[1]),
    )
    @settings(max_examples=100)
    def test_different_seeds_produce_different_output(
        self, ps: PlayState, n: int, seeds: tuple[int, int]
    ) -> None:
        """**Validates: Requirements 2.4**"""
        seed_a, seed_b = seeds
        result_a = generate_branches(ps, n=n, seed=seed_a)
        result_b = generate_branches(ps, n=n, seed=seed_b)
        assert result_a.branches != result_b.branches


class TestProperty5UniqueSequentialBranchIDs:
    """Property 5: Unique sequential branch IDs.

    For any generation run, all branch_ids SHALL be unique and SHALL match
    the pattern "gen-NNN" where NNN is a zero-padded sequential index
    starting from 001.
    """

    @given(ps=play_state_strategy(), n=_n_strategy, seed=_seed_strategy)
    @settings(max_examples=100)
    def test_unique_sequential_branch_ids(self, ps: PlayState, n: int, seed: int) -> None:
        """**Validates: Requirements 2.5**"""
        result = generate_branches(ps, n=n, seed=seed)
        branch_ids = [b["branch_id"] for b in result.branches]

        # All unique
        assert len(set(branch_ids)) == len(branch_ids)

        # Match pattern and sequential
        pattern = re.compile(r"^gen-(\d{3})$")
        for i, bid in enumerate(branch_ids):
            m = pattern.match(bid)
            assert m is not None, f"branch_id {bid!r} does not match gen-NNN pattern"
            assert int(m.group(1)) == i + 1


class TestProperty6DecisionPointTimestampsMatchPlayState:
    """Property 6: Decision point timestamps match PlayState.

    For any valid PlayState, every generated branch's decision_point_timestamp
    and the ContinuationWindow's decision_point_timestamp SHALL equal the
    PlayState's decision_point_timestamp.
    """

    @given(ps=play_state_strategy(), n=_n_strategy, seed=_seed_strategy)
    @settings(max_examples=100)
    def test_decision_point_timestamps_match(self, ps: PlayState, n: int, seed: int) -> None:
        """**Validates: Requirements 2.6, 4.2**"""
        result = generate_branches(ps, n=n, seed=seed)

        for branch in result.branches:
            assert branch["decision_point_timestamp"] == ps.decision_point_timestamp, (
                f"Branch {branch['branch_id']} has decision_point_timestamp "
                f"{branch['decision_point_timestamp']}, expected {ps.decision_point_timestamp}"
            )

        assert result.continuation_window["decision_point_timestamp"] == ps.decision_point_timestamp


class TestProperty7AtLeastThreePerturbationStrategiesUsed:
    """Property 7: At least three perturbation strategies used.

    For any generation run with N >= 3, the GenerationResult's strategy_counts
    SHALL contain at least three distinct strategy keys, and no single strategy
    SHALL account for all N branches.
    """

    @given(ps=play_state_strategy(), n=_n_strategy, seed=_seed_strategy)
    @settings(max_examples=100)
    def test_at_least_three_strategies_used(self, ps: PlayState, n: int, seed: int) -> None:
        """**Validates: Requirements 3.1, 3.2**"""
        result = generate_branches(ps, n=n, seed=seed)
        counts = result.strategy_counts

        assert len(counts) >= 3, (
            f"Expected >= 3 strategy keys, got {len(counts)}: {list(counts.keys())}"
        )

        for strategy, count in counts.items():
            assert count < n, (
                f"Strategy {strategy!r} accounts for all {n} branches"
            )


class TestProperty8GeneratedBranchesConformToBranchStructure:
    """Property 8: Generated branches conform to Branch structure.

    Each branch SHALL have branch_id, decision_point_timestamp, positions,
    events, player_roles, metadata. Positions are non-empty lists of dicts
    with player_id, x, y, timestamp.
    """

    _REQUIRED_BRANCH_KEYS = {
        "branch_id",
        "decision_point_timestamp",
        "positions",
        "events",
        "player_roles",
        "metadata",
    }
    _REQUIRED_POSITION_KEYS = {"player_id", "x", "y", "timestamp"}

    @given(ps=play_state_strategy(), n=_n_strategy, seed=_seed_strategy)
    @settings(max_examples=100)
    def test_branches_conform_to_structure(self, ps: PlayState, n: int, seed: int) -> None:
        """**Validates: Requirements 3.3**"""
        result = generate_branches(ps, n=n, seed=seed)

        for branch in result.branches:
            # Top-level keys
            missing = self._REQUIRED_BRANCH_KEYS - set(branch.keys())
            assert not missing, (
                f"Branch {branch.get('branch_id')} missing keys: {missing}"
            )

            # Positions non-empty
            assert isinstance(branch["positions"], list)
            assert len(branch["positions"]) > 0, (
                f"Branch {branch['branch_id']} has empty positions"
            )

            # Each position has required keys
            for pos in branch["positions"]:
                assert isinstance(pos, dict)
                pos_missing = self._REQUIRED_POSITION_KEYS - set(pos.keys())
                assert not pos_missing, (
                    f"Position in branch {branch['branch_id']} missing keys: {pos_missing}"
                )


class TestProperty9GeneratedTimestampsOrderedWithValidGaps:
    """Property 9: Generated timestamps are ordered with valid gaps.

    For each player's positions sorted by timestamp, consecutive timestamps
    SHALL be strictly increasing with gap <= MAX_TIMESTAMP_GAP.
    """

    @given(ps=play_state_strategy(), n=_n_strategy, seed=_seed_strategy)
    @settings(max_examples=100)
    def test_timestamps_ordered_with_valid_gaps(self, ps: PlayState, n: int, seed: int) -> None:
        """**Validates: Requirements 3.4**"""
        result = generate_branches(ps, n=n, seed=seed)

        for branch in result.branches:
            by_player: dict[str, list[dict]] = defaultdict(list)
            for pos in branch["positions"]:
                by_player[pos["player_id"]].append(pos)

            for pid, positions in by_player.items():
                positions.sort(key=lambda p: p["timestamp"])
                for a, b in zip(positions, positions[1:]):
                    assert a["timestamp"] < b["timestamp"], (
                        f"Branch {branch['branch_id']}, player {pid}: "
                        f"timestamp {a['timestamp']} not < {b['timestamp']}"
                    )
                    gap = b["timestamp"] - a["timestamp"]
                    assert gap <= MAX_TIMESTAMP_GAP, (
                        f"Branch {branch['branch_id']}, player {pid}: "
                        f"gap {gap:.4f}s exceeds MAX_TIMESTAMP_GAP {MAX_TIMESTAMP_GAP}s"
                    )


class TestProperty10AtLeast70PercentGatingCompliantSpeeds:
    """Property 10: At least 70% gating-compliant speeds.

    For any generation run, at least 70% of the generated branches SHALL
    have all player speeds <= MAX_HUMAN_SPRINT_SPEED.
    """

    @given(ps=play_state_strategy(), n=_n_strategy, seed=_seed_strategy)
    @settings(max_examples=100)
    def test_at_least_70_percent_compliant_speeds(self, ps: PlayState, n: int, seed: int) -> None:
        """**Validates: Requirements 3.5**"""
        result = generate_branches(ps, n=n, seed=seed)
        compliant = 0

        for branch in result.branches:
            by_player: dict[str, list[dict]] = defaultdict(list)
            for pos in branch["positions"]:
                by_player[pos["player_id"]].append(pos)

            all_ok = True
            for pid, positions in by_player.items():
                positions.sort(key=lambda p: p["timestamp"])
                for a, b in zip(positions, positions[1:]):
                    dt = b["timestamp"] - a["timestamp"]
                    if dt > 0:
                        dist = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
                        speed = dist / dt
                        if speed > MAX_HUMAN_SPRINT_SPEED:
                            all_ok = False
                            break
                if not all_ok:
                    break

            if all_ok:
                compliant += 1

        ratio = compliant / len(result.branches)
        assert ratio >= 0.70, (
            f"Only {compliant}/{len(result.branches)} branches "
            f"({ratio:.0%}) have compliant speeds, expected >= 70%"
        )


class TestProperty11SynthesizedContinuationWindowIsWellFormed:
    """Property 11: Synthesized ContinuationWindow is well-formed.

    For any valid PlayState, the synthesized ContinuationWindow SHALL contain
    a window_id, a decision_point_timestamp, at least one outcome with
    positions, meter_gain, turnover, and scoring_play fields, and a metadata dict.
    """

    @given(ps=play_state_strategy(), n=_n_strategy, seed=_seed_strategy)
    @settings(max_examples=100)
    def test_continuation_window_is_well_formed(self, ps: PlayState, n: int, seed: int) -> None:
        """**Validates: Requirements 4.1, 4.3, 4.4**"""
        result = generate_branches(ps, n=n, seed=seed)
        cw = result.continuation_window

        # Has window_id
        assert "window_id" in cw
        assert isinstance(cw["window_id"], str)

        # Has decision_point_timestamp matching PlayState
        assert "decision_point_timestamp" in cw
        assert cw["decision_point_timestamp"] == ps.decision_point_timestamp

        # Has at least one outcome
        assert "outcomes" in cw
        assert isinstance(cw["outcomes"], list)
        assert len(cw["outcomes"]) >= 1

        # Each outcome has required fields (meter_gain for soccer domain)
        for outcome in cw["outcomes"]:
            assert "positions" in outcome
            assert isinstance(outcome["positions"], list)
            assert "meter_gain" in outcome
            assert "turnover" in outcome
            assert "scoring_play" in outcome

        # Has metadata dict
        assert "metadata" in cw
        assert isinstance(cw["metadata"], dict)
