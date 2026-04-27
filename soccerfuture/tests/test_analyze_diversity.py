"""Unit and property tests for diversity analysis pure functions.

Validates: Requirements 6.1, 6.2
"""

import math

import pytest
from hypothesis import given, settings

from scripts.analyze_diversity import compute_entropy, compute_strategy_dominance
from tests.strategies import strategy_counts_strategy


# ---------------------------------------------------------------------------
# Unit tests — Task 8.2
# ---------------------------------------------------------------------------


class TestComputeEntropy:
    """Tests for compute_entropy."""

    def test_single_category_returns_zero(self) -> None:
        """Entropy of a single-category distribution is 0."""
        assert compute_entropy({"a": 10}) == 0.0

    def test_uniform_two_categories_returns_one(self) -> None:
        """Entropy of a uniform 2-category distribution is 1.0 bit."""
        assert compute_entropy({"a": 5, "b": 5}) == 1.0

    def test_uniform_three_categories(self) -> None:
        """Entropy of a uniform 3-category distribution is log2(3)."""
        result = compute_entropy({"a": 5, "b": 5, "c": 5})
        assert result == pytest.approx(math.log2(3), abs=1e-9)


class TestComputeStrategyDominance:
    """Tests for compute_strategy_dominance."""

    def test_single_strategy_returns_100(self) -> None:
        """A single strategy has 100% dominance."""
        assert compute_strategy_dominance({"a": 10}) == 100.0

    def test_mixed_distribution_70_30(self) -> None:
        """Dominance of {a:3, b:7} is 70%."""
        assert compute_strategy_dominance({"a": 3, "b": 7}) == 70.0

    def test_uniform_two_strategies(self) -> None:
        """Dominance of {a:5, b:5} is 50%."""
        assert compute_strategy_dominance({"a": 5, "b": 5}) == 50.0


# ---------------------------------------------------------------------------
# Property test — Task 8.3
# Property 13: Entropy and strategy dominance computation
# ---------------------------------------------------------------------------


class TestEntropyAndDominanceProperties:
    """Property-based tests for entropy and strategy dominance.

    **Validates: Requirements 6.2**
    """

    @given(counts=strategy_counts_strategy())
    @settings(max_examples=100)
    def test_entropy_non_negative_and_dominance_in_range(
        self, counts: dict[str, int]
    ) -> None:
        """For any non-empty distribution, entropy >= 0 and dominance in [0, 100].

        When a single strategy accounts for > 80% of total, dominance > 80.

        **Validates: Requirements 6.2**
        """
        entropy = compute_entropy(counts)
        dominance = compute_strategy_dominance(counts)

        assert entropy >= 0.0, f"Entropy must be non-negative, got {entropy}"
        assert 0.0 <= dominance <= 100.0, (
            f"Dominance must be in [0, 100], got {dominance}"
        )

        # When one strategy has > 80% of total, dominance must exceed 80
        total = sum(counts.values())
        if total > 0:
            max_count = max(counts.values())
            if (max_count / total) > 0.80:
                assert dominance > 80.0, (
                    f"Single strategy has {max_count}/{total} "
                    f"(>{80}%) but dominance is {dominance}"
                )
