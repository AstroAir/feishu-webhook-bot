"""Tests for SearchCache.

Tests cover:
- Cache initialization
- Set and get operations
- Cache statistics
- Cache eviction
- Cache clearing
"""

from __future__ import annotations

from feishu_webhook_bot.ai.search.base import SearchResponse, SearchResult
from feishu_webhook_bot.ai.search.cache import SearchCache

# ==============================================================================
# SearchCache Tests
# ==============================================================================


class TestSearchCache:
    """Tests for SearchCache."""

    def test_cache_set_and_get(self) -> None:
        """Test setting and getting cached results."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        response = SearchResponse(
            results=[SearchResult(title="Test", url="https://test.com", snippet="Test")],
            query="test query",
            provider="Test",
        )

        cache.set("test query", 10, response)
        cached = cache.get("test query", 10)

        assert cached is not None
        assert cached.query == "test query"
        assert cached.cached is True

    def test_cache_miss(self) -> None:
        """Test cache miss."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        result = cache.get("nonexistent", 10)
        assert result is None

    def test_cache_stats(self) -> None:
        """Test cache statistics."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        response = SearchResponse(
            results=[],
            query="test",
            provider="Test",
        )

        cache.set("test", 10, response)
        cache.get("test", 10)  # Hit
        cache.get("nonexistent", 10)  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_cache_clear(self) -> None:
        """Test clearing cache."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        response = SearchResponse(results=[], query="test", provider="Test")

        cache.set("test", 10, response)
        assert cache.get("test", 10) is not None

        cache.clear()
        assert cache.get("test", 10) is None
        stats = cache.get_stats()
        assert stats["size"] == 0

    def test_cache_max_size_eviction(self) -> None:
        """Test cache eviction when max size reached."""
        cache = SearchCache(ttl_minutes=60, max_size=3)

        for i in range(5):
            response = SearchResponse(results=[], query=f"query{i}", provider="Test")
            cache.set(f"query{i}", 10, response)

        stats = cache.get_stats()
        assert stats["size"] <= 3

    def test_cache_different_max_results(self) -> None:
        """Test cache handles different max_results as different keys."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        response5 = SearchResponse(results=[], query="test", provider="Test")
        response10 = SearchResponse(results=[], query="test", provider="Test")

        cache.set("test", 5, response5)
        cache.set("test", 10, response10)

        # Both should be retrievable with their specific max_results
        assert cache.get("test", 5) is not None
        assert cache.get("test", 10) is not None
        # But with wrong max_results should be None
        assert cache.get("test", 15) is None

    def test_cache_hit_rate(self) -> None:
        """Test cache hit rate calculation."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        response = SearchResponse(results=[], query="test", provider="Test")

        cache.set("test", 10, response)

        # 2 hits
        cache.get("test", 10)
        cache.get("test", 10)
        # 2 misses
        cache.get("other", 10)
        cache.get("another", 10)

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        # hit_rate_percent is calculated as percentage
        assert stats["hit_rate_percent"] == 50.0
