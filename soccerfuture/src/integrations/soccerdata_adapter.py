"""Adapter for fetching targeted match context from soccerdata.

Provides a single entry point — ``get_match_context`` — that fetches
pre-match context for exactly two named teams, with optional caching.
The adapter NEVER crawls full leagues or discovers teams automatically.
"""

import datetime
import json
import os
from collections.abc import Callable

from src.domain.match_context import (
    ComparativeSignals,
    MatchContext,
    TeamContextMetrics,
    match_context_to_dict,
)
from src.integrations.soccerdata_cache import SoccerdataCache, build_cache_key

_FIXTURES_DIR = os.path.join("data", "fixtures", "soccerdata")


def _fixture_filename(home_team: str, away_team: str) -> str:
    """Build the fixture filename from team names.

    Lowercases and replaces spaces with dashes, then joins with ``_``.
    """
    home = home_team.lower().replace(" ", "-")
    away = away_team.lower().replace(" ", "-")
    return f"{home}_{away}.json"


def _fetch_from_soccerdata(
    home_team: str,
    away_team: str,
    competition: str | None,
    season: str | None,
    lookback_matches: int,
) -> dict:
    """Load raw match context from a local fixture file.

    Looks for ``data/fixtures/soccerdata/{home}_{away}.json`` where team
    names are lowercased with spaces replaced by dashes.

    Args:
        home_team: Name of the home team.
        away_team: Name of the away team.
        competition: Ignored for fixture loading.
        season: Ignored for fixture loading.
        lookback_matches: Ignored for fixture loading.

    Returns:
        The parsed JSON dict from the fixture file.

    Raises:
        FileNotFoundError: If no fixture file exists for the given teams.
    """
    filename = _fixture_filename(home_team, away_team)
    path = os.path.join(_FIXTURES_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No soccerdata fixture found for {home_team} vs {away_team} "
            f"at {path}"
        )
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _normalize_to_match_context(
    raw: dict,
    home_team: str,
    away_team: str,
    lookback_matches: int,
    cache_status: str,
    competition: str | None,
    season: str | None,
) -> MatchContext:
    """Convert a raw data dict into a fully typed MatchContext.

    Args:
        raw: Raw dict from the data fetcher or fixture file.
        home_team: Home team name.
        away_team: Away team name.
        lookback_matches: Number of lookback matches requested.
        cache_status: One of "hit", "miss", "expired", or "bypass".
        competition: Competition name, if any.
        season: Season identifier, if any.

    Returns:
        A populated MatchContext instance.
    """
    home_raw = raw.get("home_metrics", {})
    away_raw = raw.get("away_metrics", {})
    comp_raw = raw.get("comparative_signals", {})

    home_metrics = TeamContextMetrics(
        matches_sampled=home_raw.get("matches_sampled", 0),
        wins=home_raw.get("wins", 0),
        draws=home_raw.get("draws", 0),
        losses=home_raw.get("losses", 0),
        goals_for_avg=home_raw.get("goals_for_avg"),
        goals_against_avg=home_raw.get("goals_against_avg"),
        xg_for_avg=home_raw.get("xg_for_avg"),
        xg_against_avg=home_raw.get("xg_against_avg"),
        form_points=home_raw.get("form_points"),
        elo=home_raw.get("elo"),
        style_tags=home_raw.get("style_tags", []),
    )
    away_metrics = TeamContextMetrics(
        matches_sampled=away_raw.get("matches_sampled", 0),
        wins=away_raw.get("wins", 0),
        draws=away_raw.get("draws", 0),
        losses=away_raw.get("losses", 0),
        goals_for_avg=away_raw.get("goals_for_avg"),
        goals_against_avg=away_raw.get("goals_against_avg"),
        xg_for_avg=away_raw.get("xg_for_avg"),
        xg_against_avg=away_raw.get("xg_against_avg"),
        form_points=away_raw.get("form_points"),
        elo=away_raw.get("elo"),
        style_tags=away_raw.get("style_tags", []),
    )
    comparative_signals = ComparativeSignals(
        stronger_team=comp_raw.get("stronger_team"),
        form_edge=comp_raw.get("form_edge"),
        attack_edge=comp_raw.get("attack_edge"),
        defense_edge=comp_raw.get("defense_edge"),
        notes=comp_raw.get("notes", []),
    )

    return MatchContext(
        home_team=home_team,
        away_team=away_team,
        lookback_matches=lookback_matches,
        source="soccerdata",
        cache_status=cache_status,
        home_metrics=home_metrics,
        away_metrics=away_metrics,
        comparative_signals=comparative_signals,
        competition=competition,
        season=season,
        fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


def get_match_context(
    home_team: str,
    away_team: str,
    competition: str | None = None,
    season: str | None = None,
    lookback_matches: int = 10,
    use_cache: bool = True,
    cache: SoccerdataCache | None = None,
    data_fetcher: Callable | None = None,
) -> MatchContext:
    """Fetch targeted match context for two named teams.

    The adapter fetches data ONLY for the explicitly provided *home_team*
    and *away_team*. It never crawls full leagues, discovers teams, or
    fetches broad datasets.

    Args:
        home_team: Name of the home team.
        away_team: Name of the away team.
        competition: Optional competition filter.
        season: Optional season filter.
        lookback_matches: Number of recent matches to consider.
        use_cache: Whether to use the cache. When False the cache is
            bypassed entirely.
        cache: An optional SoccerdataCache instance. A default instance
            is created when not provided and *use_cache* is True.
        data_fetcher: Optional callable with signature
            ``(home_team, away_team, competition, season, lookback_matches)``
            returning a raw dict. Falls back to ``_fetch_from_soccerdata``.

    Returns:
        A MatchContext populated from the fetched (or cached) data.

    Raises:
        FileNotFoundError: When using the default fetcher and no fixture
            file exists for the given teams.
    """
    fetcher = data_fetcher if data_fetcher is not None else _fetch_from_soccerdata

    # --- cache bypass path ---
    if not use_cache:
        raw = fetcher(home_team, away_team, competition, season, lookback_matches)
        return _normalize_to_match_context(
            raw, home_team, away_team, lookback_matches,
            cache_status="bypass",
            competition=competition,
            season=season,
        )

    # --- cache-enabled path ---
    if cache is None:
        cache = SoccerdataCache()

    key = build_cache_key(home_team, away_team, competition, season, lookback_matches)
    cached_payload, status = cache.get(key)

    if status == "hit" and cached_payload is not None:
        return _normalize_to_match_context(
            cached_payload, home_team, away_team, lookback_matches,
            cache_status="hit",
            competition=competition,
            season=season,
        )

    # miss or expired — fetch fresh data
    raw = fetcher(home_team, away_team, competition, season, lookback_matches)
    cache.put(key, raw)

    return _normalize_to_match_context(
        raw, home_team, away_team, lookback_matches,
        cache_status=status,  # "miss" or "expired"
        competition=competition,
        season=season,
    )
