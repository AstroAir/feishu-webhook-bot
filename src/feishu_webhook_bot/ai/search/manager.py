"""Search manager for unified search across multiple providers."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ...core.logger import get_logger
from .base import (
    SearchError,
    SearchProvider,
    SearchResponse,
    SearchResult,
)
from .cache import SearchCache, get_search_cache

logger = get_logger("ai.search.manager")


class SearchManager:
    """Unified search manager supporting multiple providers.

    Features:
    - Multiple provider support with priority ordering
    - Automatic failover to backup providers
    - Result caching
    - Concurrent search across providers (optional)
    - Provider health monitoring
    """

    def __init__(
        self,
        providers: list[SearchProvider] | None = None,
        cache: SearchCache | None = None,
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
        enable_failover: bool = True,
        concurrent_search: bool = False,
    ) -> None:
        """Initialize the search manager.

        Args:
            providers: List of search providers (ordered by priority)
            cache: Custom cache instance (uses global cache if None)
            enable_cache: Whether to enable result caching
            cache_ttl_minutes: Cache TTL in minutes
            enable_failover: Whether to failover to backup providers
            concurrent_search: Whether to search all providers concurrently
        """
        self._providers: dict[str, SearchProvider] = {}
        self._provider_order: list[str] = []
        self._cache = cache or (get_search_cache(cache_ttl_minutes) if enable_cache else None)
        self._enable_cache = enable_cache
        self._enable_failover = enable_failover
        self._concurrent_search = concurrent_search

        # Statistics
        self._total_searches = 0
        self._successful_searches = 0
        self._failed_searches = 0
        self._cache_hits = 0
        self._failover_count = 0

        # Register initial providers
        if providers:
            for provider in providers:
                self.register_provider(provider)

        logger.info(
            "SearchManager initialized (providers=%d, cache=%s, failover=%s)",
            len(self._providers),
            enable_cache,
            enable_failover,
        )

    def register_provider(
        self,
        provider: SearchProvider,
        priority: int | None = None,
    ) -> None:
        """Register a search provider.

        Args:
            provider: Search provider to register
            priority: Priority order (lower = higher priority, None = append)
        """
        provider_name = provider.name
        self._providers[provider_name] = provider

        if priority is not None and 0 <= priority < len(self._provider_order):
            self._provider_order.insert(priority, provider_name)
        else:
            self._provider_order.append(provider_name)

        logger.info(
            "Registered search provider: %s (configured=%s, priority=%d)",
            provider_name,
            provider.is_configured,
            self._provider_order.index(provider_name),
        )

    def unregister_provider(self, provider_name: str) -> bool:
        """Unregister a search provider.

        Args:
            provider_name: Name of the provider to remove

        Returns:
            True if provider was removed
        """
        if provider_name in self._providers:
            del self._providers[provider_name]
            self._provider_order.remove(provider_name)
            logger.info("Unregistered search provider: %s", provider_name)
            return True
        return False

    def get_provider(self, name: str) -> SearchProvider | None:
        """Get a provider by name.

        Args:
            name: Provider name

        Returns:
            SearchProvider or None
        """
        return self._providers.get(name)

    def get_configured_providers(self) -> list[SearchProvider]:
        """Get all configured (ready to use) providers.

        Returns:
            List of configured providers in priority order
        """
        return [
            self._providers[name]
            for name in self._provider_order
            if self._providers[name].is_configured
        ]

    async def search(
        self,
        query: str,
        max_results: int = 10,
        provider: str | None = None,
        use_cache: bool = True,
        **options: Any,
    ) -> SearchResponse:
        """Perform a search query.

        Args:
            query: Search query string
            max_results: Maximum number of results
            provider: Specific provider to use (None for auto-select)
            use_cache: Whether to use cached results
            **options: Provider-specific options

        Returns:
            SearchResponse with results

        Raises:
            SearchError: If all providers fail
        """
        self._total_searches += 1
        start_time = time.time()

        # Validate query
        if not query or not query.strip():
            raise SearchError("Search query cannot be empty")

        query = query.strip()
        max_results = max(1, min(max_results, 50))

        logger.info("Searching for: %s (max_results=%d)", query[:100], max_results)

        # Check cache first
        if use_cache and self._enable_cache and self._cache:
            cached = self._cache.get(query, max_results, provider, **options)
            if cached:
                self._cache_hits += 1
                self._successful_searches += 1
                logger.info("Returning cached results for: %s", query[:50])
                return cached

        # Determine which providers to use
        if provider:
            providers_to_try = [self._providers[provider]] if provider in self._providers else []
        else:
            providers_to_try = self.get_configured_providers()

        if not providers_to_try:
            self._failed_searches += 1
            raise SearchError("No configured search providers available")

        # Perform search
        if self._concurrent_search and len(providers_to_try) > 1:
            response = await self._search_concurrent(
                query, max_results, providers_to_try, **options
            )
        else:
            response = await self._search_sequential(
                query, max_results, providers_to_try, **options
            )

        # Update search time
        response.search_time_ms = (time.time() - start_time) * 1000

        # Cache successful results
        if use_cache and self._enable_cache and self._cache and response.has_results:
            self._cache.set(query, max_results, response, provider, **options)

        self._successful_searches += 1
        logger.info(
            "Search completed: %d results from %s in %.2fms",
            response.count,
            response.provider,
            response.search_time_ms,
        )

        return response

    async def _search_sequential(
        self,
        query: str,
        max_results: int,
        providers: list[SearchProvider],
        **options: Any,
    ) -> SearchResponse:
        """Search providers sequentially with failover.

        Args:
            query: Search query
            max_results: Maximum results
            providers: Providers to try
            **options: Additional options

        Returns:
            SearchResponse from first successful provider

        Raises:
            SearchError: If all providers fail
        """
        last_error: Exception | None = None

        for i, provider in enumerate(providers):
            try:
                logger.debug("Trying provider: %s", provider.name)
                response = await provider.search(query, max_results, **options)

                if i > 0:
                    self._failover_count += 1
                    logger.info("Failover to %s succeeded", provider.name)

                return response

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Provider %s failed: %s",
                    provider.name,
                    str(exc),
                )

                if not self._enable_failover:
                    break

        self._failed_searches += 1
        raise SearchError(
            f"All search providers failed. Last error: {last_error}",
            provider=providers[-1].name if providers else None,
        )

    async def _search_concurrent(
        self,
        query: str,
        max_results: int,
        providers: list[SearchProvider],
        **options: Any,
    ) -> SearchResponse:
        """Search all providers concurrently and merge results.

        Args:
            query: Search query
            max_results: Maximum results
            providers: Providers to search
            **options: Additional options

        Returns:
            Merged SearchResponse

        Raises:
            SearchError: If all providers fail
        """
        tasks = [provider.search(query, max_results, **options) for provider in providers]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful responses
        successful_responses: list[SearchResponse] = []
        for result in results:
            if isinstance(result, SearchResponse):
                successful_responses.append(result)

        if not successful_responses:
            self._failed_searches += 1
            errors = [str(r) for r in results if isinstance(r, Exception)]
            raise SearchError(f"All providers failed: {'; '.join(errors)}")

        # Merge results from all providers
        return self._merge_responses(query, successful_responses, max_results)

    def _merge_responses(
        self,
        query: str,
        responses: list[SearchResponse],
        max_results: int,
    ) -> SearchResponse:
        """Merge results from multiple providers.

        Args:
            query: Original query
            responses: List of responses to merge
            max_results: Maximum results to return

        Returns:
            Merged SearchResponse
        """
        # Collect all results with provider info
        all_results: list[tuple[SearchResult, str]] = []
        for response in responses:
            for result in response.results:
                all_results.append((result, response.provider))

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_results: list[SearchResult] = []

        for result, provider in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                # Add provider info to metadata
                result.raw_data["source_provider"] = provider
                unique_results.append(result)

        # Sort by relevance score and limit
        unique_results.sort(key=lambda r: r.relevance_score, reverse=True)
        final_results = unique_results[:max_results]

        # Re-assign positions
        for i, result in enumerate(final_results, 1):
            result.position = i

        providers_used = list(set(r.provider for r in responses))

        return SearchResponse(
            results=final_results,
            query=query,
            provider=",".join(providers_used),
            total_results=len(unique_results),
            metadata={"merged_from": providers_used},
        )

    async def health_check(self) -> dict[str, bool]:
        """Check health of all providers.

        Returns:
            Dictionary mapping provider names to health status
        """
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results

    def get_stats(self) -> dict[str, Any]:
        """Get search manager statistics.

        Returns:
            Dictionary with statistics
        """
        success_rate = (
            self._successful_searches / self._total_searches * 100
            if self._total_searches > 0
            else 0.0
        )

        return {
            "total_searches": self._total_searches,
            "successful_searches": self._successful_searches,
            "failed_searches": self._failed_searches,
            "success_rate_percent": round(success_rate, 2),
            "cache_hits": self._cache_hits,
            "failover_count": self._failover_count,
            "provider_count": len(self._providers),
            "configured_providers": len(self.get_configured_providers()),
            "providers": {name: provider.get_stats() for name, provider in self._providers.items()},
            "cache_stats": self._cache.get_stats() if self._cache else None,
        }

    def clear_cache(self) -> None:
        """Clear the search cache."""
        if self._cache:
            self._cache.clear()
            logger.info("Search cache cleared")


# Global search manager instance
_global_manager: SearchManager | None = None


def get_search_manager() -> SearchManager:
    """Get the global search manager instance.

    Returns:
        SearchManager instance
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = SearchManager()
    return _global_manager


def set_search_manager(manager: SearchManager) -> None:
    """Set the global search manager instance.

    Args:
        manager: SearchManager to use globally
    """
    global _global_manager
    _global_manager = manager
    logger.info("Global search manager updated")
