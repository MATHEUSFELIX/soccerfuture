"""File-based cache for soccerdata match context lookups.

Provides deterministic cache key generation and a simple JSON-file-backed
cache with TTL expiry support.
"""

import datetime
import json
import os


def build_cache_key(
    home_team: str,
    away_team: str,
    competition: str | None,
    season: str | None,
    lookback_matches: int,
) -> str:
    """Build a deterministic cache key from match context parameters.

    Args:
        home_team: Name of the home team.
        away_team: Name of the away team.
        competition: Competition name, or None.
        season: Season identifier, or None.
        lookback_matches: Number of historical matches to consider.

    Returns:
        A lowercase, dash-separated key string with the format
        ``{home}_{away}_{competition}_{season}_{lookback}``.
        None values are replaced with ``"none"`` and spaces become dashes.
    """
    parts = [
        home_team,
        away_team,
        competition if competition is not None else "none",
        season if season is not None else "none",
        str(lookback_matches),
    ]
    raw = "_".join(parts)
    return raw.lower().replace(" ", "-")


class SoccerdataCache:
    """JSON-file-backed cache with TTL expiry for soccerdata payloads.

    Each entry is stored as a single JSON file under *cache_dir* keyed by
    the deterministic cache key.  Files contain the payload, an ISO-8601
    ``fetched_at`` timestamp, and a schema ``version`` string.

    Attributes:
        cache_dir: Directory where cache files are stored.
        ttl_seconds: Time-to-live in seconds before an entry is considered
            expired.
    """

    def __init__(
        self, cache_dir: str = ".cache/soccerdata", ttl_seconds: int = 86400
    ) -> None:
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds

    def _path_for(self, key: str) -> str:
        """Return the filesystem path for a given cache key."""
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str) -> tuple[dict | None, str]:
        """Retrieve a cached payload by key.

        Args:
            key: The cache key (as produced by ``build_cache_key``).

        Returns:
            A tuple of ``(payload_or_None, status)`` where *status* is one of
            ``"hit"``, ``"miss"``, or ``"expired"``.
        """
        path = self._path_for(key)
        if not os.path.exists(path):
            return None, "miss"

        with open(path, "r", encoding="utf-8") as fh:
            entry = json.load(fh)

        fetched_at = datetime.datetime.fromisoformat(entry["fetched_at"])
        now = datetime.datetime.now(datetime.timezone.utc)
        if (now - fetched_at).total_seconds() > self.ttl_seconds:
            return None, "expired"

        return entry["payload"], "hit"

    def put(self, key: str, payload: dict) -> None:
        """Write a payload to the cache with the current UTC timestamp.

        Creates *cache_dir* on first write if it does not already exist.

        Args:
            key: The cache key.
            payload: JSON-serializable dict to store.
        """
        os.makedirs(self.cache_dir, exist_ok=True)
        entry = {
            "payload": payload,
            "fetched_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "version": "1",
        }
        path = self._path_for(key)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(entry, fh)

    def clear(self, key: str) -> None:
        """Remove a specific cache entry.

        No error is raised if the entry does not exist.

        Args:
            key: The cache key to remove.
        """
        path = self._path_for(key)
        if os.path.exists(path):
            os.remove(path)
