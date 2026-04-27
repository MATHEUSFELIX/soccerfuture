"""Tests for soccerdata_adapter module.

Covers successful fixture fetch, cache hit/bypass behaviour,
missing fixture errors, and targeted-fetch-only constraint.
All tests use tmp_path for cache dirs and fixture-based or mock
data fetchers — no live network access.
"""

import json
import os
from unittest.mock import MagicMock

import pytest

from src.domain.match_context import MatchContext
from src.integrations.soccerdata_adapter import get_match_context
from src.integrations.soccerdata_cache import SoccerdataCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_RAW: dict = {
    "home_team": "TeamA",
    "away_team": "TeamB",
    "lookback_matches": 10,
    "home_metrics": {
        "matches_sampled": 10, "wins": 6, "draws": 2, "losses": 2,
        "goals_for_avg": 1.8, "goals_against_avg": 0.9,
        "xg_for_avg": 1.7, "xg_against_avg": 1.0,
        "form_points": 20, "elo": 1650.0, "style_tags": ["high-press"],
    },
    "away_metrics": {
        "matches_sampled": 10, "wins": 4, "draws": 3, "losses": 3,
        "goals_for_avg": 1.2, "goals_against_avg": 1.1,
        "xg_for_avg": 1.3, "xg_against_avg": 1.2,
        "form_points": 15, "elo": 1580.0, "style_tags": ["counter"],
    },
    "comparative_signals": {
        "stronger_team": "TeamA", "form_edge": "TeamA",
        "attack_edge": "TeamA", "defense_edge": "TeamA",
        "notes": ["TeamA dominates recent form"],
    },
}


def _make_fetcher(raw: dict | None = None):
    """Return a mock data_fetcher that yields *raw* (defaults to _SAMPLE_RAW)."""
    data = raw if raw is not None else _SAMPLE_RAW
    fetcher = MagicMock(return_value=data)
    return fetcher


# ---------------------------------------------------------------------------
# 1. Successful fetch from fixture
# ---------------------------------------------------------------------------


class TestSuccessfulFetch:
    """Calling get_match_context with a mock fetcher returns a valid MatchContext."""

    def test_returns_valid_match_context(self, tmp_path) -> None:
        cache = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=3600)
        fetcher = _make_fetcher()

        ctx = get_match_context(
            "TeamA", "TeamB",
            cache=cache,
            data_fetcher=fetcher,
        )

        assert isinstance(ctx, MatchContext)
        assert ctx.home_team == "TeamA"
        assert ctx.away_team == "TeamB"
        assert ctx.source == "soccerdata"
        assert ctx.home_metrics.wins == 6
        assert ctx.away_metrics.style_tags == ["counter"]
        assert ctx.comparative_signals.stronger_team == "TeamA"


# ---------------------------------------------------------------------------
# 2. Cache hit
# ---------------------------------------------------------------------------


class TestCacheHit:
    """Second call with the same params returns cache_status='hit'."""

    def test_second_call_is_cache_hit(self, tmp_path) -> None:
        cache = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=3600)
        fetcher = _make_fetcher()

        first = get_match_context(
            "TeamA", "TeamB",
            cache=cache,
            data_fetcher=fetcher,
        )
        second = get_match_context(
            "TeamA", "TeamB",
            cache=cache,
            data_fetcher=fetcher,
        )

        assert first.cache_status == "miss"
        assert second.cache_status == "hit"
        # Fetcher should only be called once (second call served from cache)
        assert fetcher.call_count == 1


# ---------------------------------------------------------------------------
# 3. Cache bypass
# ---------------------------------------------------------------------------


class TestCacheBypass:
    """Calling with use_cache=False returns cache_status='bypass'."""

    def test_bypass_returns_bypass_status(self, tmp_path) -> None:
        cache = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=3600)
        fetcher = _make_fetcher()

        ctx = get_match_context(
            "TeamA", "TeamB",
            use_cache=False,
            cache=cache,
            data_fetcher=fetcher,
        )

        assert ctx.cache_status == "bypass"


# ---------------------------------------------------------------------------
# 4. Missing fixture raises FileNotFoundError
# ---------------------------------------------------------------------------


class TestMissingFixture:
    """Default fetcher raises FileNotFoundError for unknown teams."""

    def test_missing_fixture_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="No soccerdata fixture found"):
            get_match_context(
                "Nonexistent FC", "Ghost United",
                use_cache=False,
            )


# ---------------------------------------------------------------------------
# 5. Adapter only fetches selected teams
# ---------------------------------------------------------------------------


class TestTargetedFetchOnly:
    """The data_fetcher is called with exactly the provided team names."""

    def test_fetcher_called_with_exact_teams(self, tmp_path) -> None:
        cache = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=3600)
        fetcher = _make_fetcher()

        get_match_context(
            "TeamA", "TeamB",
            competition="PL",
            season="2024",
            lookback_matches=5,
            cache=cache,
            data_fetcher=fetcher,
        )

        fetcher.assert_called_once_with("TeamA", "TeamB", "PL", "2024", 5)
