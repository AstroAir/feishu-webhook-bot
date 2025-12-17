"""Search result caching for improved performance."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from ...core.logger import get_logger
from .base import SearchResponse

logger = get_logger("ai.search.cache")


class SearchCache:
    """In-memory cache for search results with TTL support.

    Features:
    - Configurable TTL (time-to-live)
    - LRU-style eviction when max size reached
    - Cache statistics tracking
    - Provider-aware caching
    """

    def __init__(
        self,
        ttl_minutes: int = 60,
        max_size: int = 500,
    ) -> None:
        """Initialize search cache.

        Args:
            ttl_minutes: Time-to-live for cached results in minutes
            max_size: Maximum number of cached entries
        """
        self._cache: dict[str, tuple[SearchResponse, datetime]] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        logger.info(
            "SearchCache initialized (ttl=%d min, max_size=%d)",
            ttl_minutes,
            max_size,
        )

    def _make_key(
        self,
        query: str,
        max_results: int,
        provider: str | None = None,
        **options: Any,
    ) -> str:
        """Create cache key from query parameters.

        Args:
            query: Search query
            max_results: Maximum results requested
            provider: Provider name (optional)
            **options: Additional options

        Returns:
            Cache key string
        """
        key_data = {
            "query": query.lower().strip(),
            "max_results": max_results,
            "provider": provider,
            **{k: v for k, v in sorted(options.items()) if v is not None},
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    def get(
        self,
        query: str,
        max_results: int,
        provider: str | None = None,
        **options: Any,
    ) -> SearchResponse | None:
        """Get cached result if available and not expired.

        Args:
            query: Search query
            max_results: Maximum results requested
            provider: Provider name (optional)
            **options: Additional options

        Returns:
            Cached SearchResponse or None if not found/expired
        """
        key = self._make_key(query, max_results, provider, **options)

        if key in self._cache:
            response, timestamp = self._cache[key]
            if datetime.now(UTC) - timestamp < self._ttl:
                self._hits += 1
                logger.debug("Cache hit for query: %s", query[:50])
                # Return a copy with cached flag set
                return SearchResponse(
                    results=response.results,
                    query=response.query,
                    provider=response.provider,
                    total_results=response.total_results,
                    cached=True,
                    timestamp=response.timestamp,
                    search_time_ms=response.search_time_ms,
                    metadata=response.metadata,
                )
            else:
                # Expired, remove it
                del self._cache[key]
                logger.debug("Cache expired for query: %s", query[:50])

        self._misses += 1
        return None

    def set(
        self,
        query: str,
        max_results: int,
        response: SearchResponse,
        provider: str | None = None,
        **options: Any,
    ) -> None:
        """Cache a search response.

        Args:
            query: Search query
            max_results: Maximum results requested
            response: SearchResponse to cache
            provider: Provider name (optional)
            **options: Additional options
        """
        # Evict oldest entry if cache is full
        if len(self._cache) >= self._max_size:
            self._evict_oldest()

        key = self._make_key(query, max_results, provider, **options)
        self._cache[key] = (response, datetime.now(UTC))
        logger.debug("Cached result for query: %s", query[:50])

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry."""
        if not self._cache:
            return

        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
        del self._cache[oldest_key]
        logger.debug("Evicted oldest cache entry")

    def invalidate(
        self,
        query: str | None = None,
        provider: str | None = None,
    ) -> int:
        """Invalidate cache entries.

        Args:
            query: Specific query to invalidate (None for all)
            provider: Specific provider to invalidate (None for all)

        Returns:
            Number of entries invalidated
        """
        if query is None and provider is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Invalidated all %d cache entries", count)
            return count

        # Find matching entries
        keys_to_remove = []
        for key, (response, _) in self._cache.items():
            if query and query.lower() not in response.query.lower():
                continue
            if provider and response.provider != provider:
                continue
            keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

        logger.info("Invalidated %d cache entries", len(keys_to_remove))
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached results and reset statistics."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Search cache cleared")

    def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = datetime.now(UTC)
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items() if now - timestamp >= self._ttl
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info("Cleaned up %d expired cache entries", len(expired_keys))

        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "ttl_minutes": self._ttl.total_seconds() / 60,
        }


# Global search cache instance
_global_cache: SearchCache | None = None


def get_search_cache(
    ttl_minutes: int = 60,
    max_size: int = 500,
) -> SearchCache:
    """Get or create the global search cache instance.

    Args:
        ttl_minutes: TTL for cache entries
        max_size: Maximum cache size

    Returns:
        SearchCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = SearchCache(ttl_minutes=ttl_minutes, max_size=max_size)
    return _global_cache
