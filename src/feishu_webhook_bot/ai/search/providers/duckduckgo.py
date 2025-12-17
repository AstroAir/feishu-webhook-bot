"""DuckDuckGo search provider - free, no API key required."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from duckduckgo_search import DDGS

from ....core.logger import get_logger
from ..base import (
    SearchProvider,
    SearchProviderError,
    SearchProviderType,
    SearchResponse,
    SearchResult,
)

logger = get_logger("ai.search.duckduckgo")


class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo search provider.

    Features:
    - Free to use, no API key required
    - Privacy-focused search
    - Good general web search results
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        region: str = "wt-wt",
        safesearch: str = "moderate",
    ) -> None:
        """Initialize DuckDuckGo provider.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            region: Region for search results (wt-wt = worldwide)
            safesearch: Safe search level (on, moderate, off)
        """
        super().__init__(api_key=None, timeout=timeout, max_retries=max_retries)
        self.region = region
        self.safesearch = safesearch

    @property
    def name(self) -> str:
        return "DuckDuckGo"

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.DUCKDUCKGO

    @property
    def requires_api_key(self) -> bool:
        return False

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> SearchResponse:
        """Search using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (region, safesearch)

        Returns:
            SearchResponse with results
        """
        self._increment_request()
        logger.info("DuckDuckGo search: %s", query[:100])

        region = options.get("region", self.region)
        safesearch = options.get("safesearch", self.safesearch)

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                # Run blocking search in thread pool
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    None,
                    lambda: DDGS().text(
                        query,
                        max_results=max_results,
                        region=region,
                        safesearch=safesearch,
                    ),
                )

                # Convert to SearchResult objects
                search_results: list[SearchResult] = []
                for idx, item in enumerate(results or [], 1):
                    title = item.get("title", "").strip()
                    url = item.get("href", "").strip()
                    snippet = item.get("body", "").strip()

                    # Clean up snippet
                    snippet = re.sub(r"\s+", " ", snippet)

                    # Extract domain as source
                    source = None
                    if url:
                        try:
                            from urllib.parse import urlparse

                            source = urlparse(url).netloc
                        except Exception:
                            pass

                    search_results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            position=idx,
                            relevance_score=1.0 - (idx - 1) * 0.05,
                            source=source,
                            raw_data=item,
                        )
                    )

                logger.info("DuckDuckGo returned %d results", len(search_results))

                return SearchResponse(
                    results=search_results,
                    query=query,
                    provider=self.name,
                    total_results=len(search_results),
                    metadata={"region": region, "safesearch": safesearch},
                )

            except Exception as exc:
                last_error = exc
                self._increment_error()

                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "DuckDuckGo search attempt %d/%d failed: %s. Retrying in %ds...",
                        attempt + 1,
                        self.max_retries,
                        exc,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "DuckDuckGo search failed after %d attempts: %s",
                        self.max_retries,
                        exc,
                    )

        raise SearchProviderError(
            f"DuckDuckGo search failed: {last_error}",
            provider=self.name,
        )
