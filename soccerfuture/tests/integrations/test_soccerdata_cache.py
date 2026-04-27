"""Tests for soccerdata_cache module.

Covers cache key determinism, write/read round-trip, cache miss,
TTL expiry, clear, and bypass behavior.
"""

from src.integrations.soccerdata_cache import SoccerdataCache, build_cache_key


# --- build_cache_key determinism ---


class TestBuildCacheKey:
    """Tests for build_cache_key determinism and formatting."""

    def test_same_inputs_produce_same_key(self) -> None:
        key1 = build_cache_key("TeamA", "TeamB", "PL", "2024", 5)
        key2 = build_cache_key("TeamA", "TeamB", "PL", "2024", 5)
        assert key1 == key2

    def test_different_inputs_produce_different_keys(self) -> None:
        key1 = build_cache_key("TeamA", "TeamB", "PL", "2024", 5)
        key2 = build_cache_key("TeamC", "TeamD", "PL", "2024", 5)
        assert key1 != key2

    def test_none_values_become_none_string(self) -> None:
        key = build_cache_key("Home", "Away", None, None, 3)
        assert "none" in key

    def test_spaces_become_dashes(self) -> None:
        key = build_cache_key("Man City", "Man United", "Premier League", "2024", 5)
        assert " " not in key
        assert "man-city" in key

    def test_output_is_lowercase(self) -> None:
        key = build_cache_key("TEAM_A", "TEAM_B", "PL", "2024", 5)
        assert key == key.lower()


# --- Write/read round-trip ---


class TestCacheRoundTrip:
    """Tests for cache put/get round-trip."""

    def test_write_then_read_returns_hit(self, tmp_path: object) -> None:
        cache = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=3600)
        payload = {"home": "TeamA", "away": "TeamB", "goals": 2}
        key = "test-round-trip"

        cache.put(key, payload)
        result, status = cache.get(key)

        assert status == "hit"
        assert result == payload


# --- Cache miss ---


class TestCacheMiss:
    """Tests for cache miss on non-existent keys."""

    def test_get_nonexistent_key_returns_miss(self, tmp_path: object) -> None:
        cache = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=3600)
        result, status = cache.get("never-written-key")

        assert status == "miss"
        assert result is None


# --- TTL expiry ---


class TestCacheTTLExpiry:
    """Tests for TTL-based cache expiry."""

    def test_expired_entry_returns_expired(self, tmp_path: object) -> None:
        # Write with a normal TTL cache
        writer = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=3600)
        writer.put("ttl-key", {"data": "value"})

        # Read with a zero-TTL cache so the entry is immediately expired
        reader = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=0)
        result, status = reader.get("ttl-key")

        assert status == "expired"
        assert result is None


# --- Clear ---


class TestCacheClear:
    """Tests for cache entry removal."""

    def test_clear_removes_entry(self, tmp_path: object) -> None:
        cache = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=3600)
        cache.put("clear-key", {"data": "to-remove"})
        cache.clear("clear-key")

        result, status = cache.get("clear-key")
        assert status == "miss"


# --- Bypass behavior ---


class TestCacheBypass:
    """Tests that cache.get returns 'miss' for non-existent keys.

    The adapter uses this status to decide whether to bypass the cache
    and fetch fresh data.
    """

    def test_miss_status_for_absent_key(self, tmp_path: object) -> None:
        cache = SoccerdataCache(cache_dir=str(tmp_path), ttl_seconds=3600)
        result, status = cache.get("absent-key")

        assert status == "miss"
        assert result is None
