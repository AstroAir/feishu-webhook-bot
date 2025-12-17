"""Google Custom Search API provider."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ....core.logger import get_logger
from ..base import (
    SearchAuthenticationError,
    SearchProvider,
    SearchProviderError,
    SearchProviderType,
    SearchRateLimitError,
    SearchResponse,
    SearchResult,
)

logger = get_logger("ai.search.google")

GOOGLE_API_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchProvider(SearchProvider):
    """Google Custom Search API provider.

    Features:
    - Google's comprehensive search index
    - Highly customizable
    - Supports site-specific search
    - Requires both API key and Custom Search Engine ID
    """

    def __init__(
        self,
        api_key: str | None = None,
        cx: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        language: str = "en",
        safe: str = "active",
    ) -> None:
        """Initialize Google Custom Search provider.

        Args:
            api_key: Google API key
            cx: Custom Search Engine ID
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            language: Language code (e.g., en, zh)
            safe: Safe search level (active, off)
        """
        super().__init__(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.cx = cx
        self.language = language
        self.safe = safe

    @property
    def name(self) -> str:
        return "Google"

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.GOOGLE

    @property
    def is_configured(self) -> bool:
        """Check if both API key and CX are configured."""
        return bool(self.api_key and self.cx)

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> SearchResponse:
        """Search using Google Custom Search API.

        Args:
            query: Search query
            max_results: Maximum results to return (max 10 per request)
            **options: Additional options (language, safe, site_search)

        Returns:
            SearchResponse with results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Google API key is required",
                provider=self.name,
            )
        if not self.cx:
            raise SearchAuthenticationError(
                "Google Custom Search Engine ID (cx) is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Google search: %s", query[:100])

        language = options.get("language", self.language)
        safe = options.get("safe", self.safe)
        site_search = options.get("site_search")

        # Google CSE limits to 10 results per request
        num = min(max_results, 10)

        params: dict[str, Any] = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": num,
            "lr": f"lang_{language}",
            "safe": safe,
        }

        if site_search:
            params["siteSearch"] = site_search

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(GOOGLE_API_URL, params=params)

                    if response.status_code == 401:
                        raise SearchAuthenticationError(
                            "Invalid Google API key",
                            provider=self.name,
                        )
                    elif response.status_code == 429:
                        raise SearchRateLimitError(
                            "Google Custom Search rate limit exceeded",
                            provider=self.name,
                        )
                    elif response.status_code == 403:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", "Forbidden")
                        raise SearchAuthenticationError(
                            f"Google API access denied: {error_msg}",
                            provider=self.name,
                        )
                    elif response.status_code != 200:
                        raise SearchProviderError(
                            f"Google Search API error: {response.status_code} - {response.text}",
                            provider=self.name,
                        )

                    data = response.json()

                # Convert to SearchResult objects
                search_results: list[SearchResult] = []
                items = data.get("items", [])

                for idx, item in enumerate(items, 1):
                    url = item.get("link", "")

                    # Extract source from displayLink
                    source = item.get("displayLink")

                    search_results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=url,
                            snippet=item.get("snippet", ""),
                            position=idx,
                            relevance_score=1.0 - (idx - 1) * 0.05,
                            source=source,
                            raw_data=item,
                        )
                    )

                logger.info("Google returned %d results", len(search_results))

                # Get total results from searchInformation
                total_results = None
                search_info = data.get("searchInformation", {})
                if search_info.get("totalResults"):
                    import contextlib

                    with contextlib.suppress(ValueError):
                        total_results = int(search_info["totalResults"])

                return SearchResponse(
                    results=search_results,
                    query=query,
                    provider=self.name,
                    total_results=total_results,
                    metadata={
                        "language": language,
                        "search_time": search_info.get("searchTime"),
                        "formatted_total_results": search_info.get("formattedTotalResults"),
                    },
                )

            except (SearchAuthenticationError, SearchRateLimitError):
                raise
            except Exception as exc:
                last_error = exc
                self._increment_error()

                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Google search attempt %d/%d failed: %s. Retrying in %ds...",
                        attempt + 1,
                        self.max_retries,
                        exc,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Google search failed after %d attempts: %s",
                        self.max_retries,
                        exc,
                    )

        raise SearchProviderError(
            f"Google search failed: {last_error}",
            provider=self.name,
        )
