"""Brave search provider - privacy-focused search engine.

Brave Search API supports:
- web: Web search
- news: News search
- images: Image search
- videos: Video search
- summarizer: AI-powered summarization
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime
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

logger = get_logger("ai.search.brave")

BRAVE_API_BASE = "https://api.search.brave.com/res/v1"
BRAVE_WEB_URL = f"{BRAVE_API_BASE}/web/search"
BRAVE_NEWS_URL = f"{BRAVE_API_BASE}/news/search"
BRAVE_IMAGES_URL = f"{BRAVE_API_BASE}/images/search"
BRAVE_VIDEOS_URL = f"{BRAVE_API_BASE}/videos/search"
BRAVE_SUMMARIZER_URL = f"{BRAVE_API_BASE}/summarizer/search"


class BraveSearchProvider(SearchProvider):
    """Brave Search provider.

    Features:
    - Privacy-focused search
    - Independent search index
    - No tracking
    - Good for general web search
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        country: str = "us",
        search_lang: str = "en",
        safesearch: str = "moderate",
    ) -> None:
        """Initialize Brave Search provider.

        Args:
            api_key: Brave Search API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            country: Country code for results
            search_lang: Search language
            safesearch: Safe search level (off, moderate, strict)
        """
        super().__init__(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.country = country
        self.search_lang = search_lang
        self.safesearch = safesearch

    @property
    def name(self) -> str:
        return "Brave"

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.BRAVE

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> SearchResponse:
        """Search using Brave Search API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (country, search_lang, safesearch)

        Returns:
            SearchResponse with results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Brave Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Brave search: %s", query[:100])

        country = options.get("country", self.country)
        search_lang = options.get("search_lang", self.search_lang)
        safesearch = options.get("safesearch", self.safesearch)

        params = {
            "q": query,
            "count": max_results,
            "country": country,
            "search_lang": search_lang,
            "safesearch": safesearch,
        }

        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
        }

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        BRAVE_WEB_URL,
                        params=params,
                        headers=headers,
                    )

                    if response.status_code == 401:
                        raise SearchAuthenticationError(
                            "Invalid Brave Search API key",
                            provider=self.name,
                        )
                    elif response.status_code == 429:
                        raise SearchRateLimitError(
                            "Brave Search rate limit exceeded",
                            provider=self.name,
                        )
                    elif response.status_code != 200:
                        raise SearchProviderError(
                            f"Brave Search API error: {response.status_code} - {response.text}",
                            provider=self.name,
                        )

                    data = response.json()

                # Convert to SearchResult objects
                search_results: list[SearchResult] = []
                web_results = data.get("web", {}).get("results", [])

                for idx, item in enumerate(web_results, 1):
                    url = item.get("url", "")

                    # Parse published date if available
                    published_date = None
                    if item.get("page_age"):
                        with contextlib.suppress(Exception):
                            published_date = datetime.fromisoformat(
                                item["page_age"].replace("Z", "+00:00")
                            )

                    search_results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=url,
                            snippet=item.get("description", ""),
                            position=idx,
                            relevance_score=1.0 - (idx - 1) * 0.05,
                            published_date=published_date,
                            source=url.split("/")[2] if url else None,
                            raw_data=item,
                        )
                    )

                logger.info("Brave returned %d results", len(search_results))

                return SearchResponse(
                    results=search_results,
                    query=query,
                    provider=self.name,
                    total_results=data.get("web", {}).get("total_results"),
                    metadata={
                        "country": country,
                        "search_lang": search_lang,
                        "query_info": data.get("query"),
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
                        "Brave search attempt %d/%d failed: %s. Retrying in %ds...",
                        attempt + 1,
                        self.max_retries,
                        exc,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Brave search failed after %d attempts: %s",
                        self.max_retries,
                        exc,
                    )

        raise SearchProviderError(
            f"Brave search failed: {last_error}",
            provider=self.name,
        )

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> SearchResponse:
        """Search news articles using Brave News API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (country, search_lang, freshness)

        Returns:
            SearchResponse with news results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Brave Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Brave news search: %s", query[:100])

        country = options.get("country", self.country)
        search_lang = options.get("search_lang", self.search_lang)
        freshness = options.get("freshness")  # pd (past day), pw (past week), pm (past month)

        params: dict[str, Any] = {
            "q": query,
            "count": max_results,
            "country": country,
            "search_lang": search_lang,
        }

        if freshness:
            params["freshness"] = freshness

        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    BRAVE_NEWS_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Brave Search API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Brave Search rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Brave News API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

            search_results: list[SearchResult] = []
            news_results = data.get("results", [])

            for idx, item in enumerate(news_results, 1):
                url = item.get("url", "")

                published_date = None
                if item.get("age"):
                    with contextlib.suppress(Exception):
                        published_date = datetime.fromisoformat(item["age"].replace("Z", "+00:00"))

                search_results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=url,
                        snippet=item.get("description", ""),
                        position=idx,
                        relevance_score=1.0 - (idx - 1) * 0.05,
                        published_date=published_date,
                        source=item.get("meta_url", {}).get("hostname"),
                        raw_data=item,
                    )
                )

            logger.info("Brave news returned %d results", len(search_results))

            return SearchResponse(
                results=search_results,
                query=query,
                provider=f"{self.name} News",
                total_results=len(search_results),
                metadata={"type": "news", "country": country},
            )

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Brave news search failed: {exc}",
                provider=self.name,
            ) from exc

    async def search_images(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> dict[str, Any]:
        """Search images using Brave Images API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (country, safesearch)

        Returns:
            Dict with image results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Brave Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Brave image search: %s", query[:100])

        country = options.get("country", self.country)
        safesearch = options.get("safesearch", self.safesearch)

        params = {
            "q": query,
            "count": max_results,
            "country": country,
            "safesearch": safesearch,
        }

        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    BRAVE_IMAGES_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Brave Search API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Brave Search rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Brave Images API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

            images = [
                {
                    "title": img.get("title", ""),
                    "url": img.get("url", ""),
                    "thumbnail": img.get("thumbnail", {}).get("src"),
                    "source": img.get("source", ""),
                    "width": img.get("properties", {}).get("width"),
                    "height": img.get("properties", {}).get("height"),
                }
                for img in data.get("results", [])
            ]

            logger.info("Brave images returned %d results", len(images))

            return {
                "images": images,
                "query": query,
                "total": len(images),
            }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Brave image search failed: {exc}",
                provider=self.name,
            ) from exc

    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> dict[str, Any]:
        """Search videos using Brave Videos API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (country, safesearch)

        Returns:
            Dict with video results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Brave Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Brave video search: %s", query[:100])

        country = options.get("country", self.country)
        safesearch = options.get("safesearch", self.safesearch)

        params = {
            "q": query,
            "count": max_results,
            "country": country,
            "safesearch": safesearch,
        }

        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    BRAVE_VIDEOS_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Brave Search API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Brave Search rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Brave Videos API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

            videos = [
                {
                    "title": vid.get("title", ""),
                    "url": vid.get("url", ""),
                    "description": vid.get("description", ""),
                    "thumbnail": vid.get("thumbnail", {}).get("src"),
                    "duration": vid.get("video", {}).get("duration"),
                    "publisher": vid.get("meta_url", {}).get("hostname"),
                }
                for vid in data.get("results", [])
            ]

            logger.info("Brave videos returned %d results", len(videos))

            return {
                "videos": videos,
                "query": query,
                "total": len(videos),
            }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Brave video search failed: {exc}",
                provider=self.name,
            ) from exc

    async def get_summary(
        self,
        query: str,
        **options: Any,
    ) -> dict[str, Any]:
        """Get AI-powered summary for a query using Brave Summarizer.

        Args:
            query: Search query
            **options: Additional options

        Returns:
            Dict with summary and sources
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Brave Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Brave summarizer: %s", query[:100])

        # First, get a web search with summary key
        params = {
            "q": query,
            "summary": 1,
        }

        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
            "Api-Version": "2023-10-11",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get summary key from web search
                response = await client.get(
                    BRAVE_WEB_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code != 200:
                    raise SearchProviderError(
                        f"Brave API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()
                summary_key = data.get("summarizer", {}).get("key")

                if not summary_key:
                    return {
                        "summary": None,
                        "query": query,
                        "message": "No summary available for this query",
                    }

                # Get the actual summary
                summarizer_headers = {
                    "X-Subscription-Token": self.api_key,
                    "Accept": "application/json",
                    "Api-Version": "2024-04-23",
                }

                summary_response = await client.get(
                    BRAVE_SUMMARIZER_URL,
                    params={"key": summary_key, "entity_info": 1},
                    headers=summarizer_headers,
                )

                if summary_response.status_code != 200:
                    return {
                        "summary": None,
                        "query": query,
                        "message": "Failed to get summary",
                    }

                summary_data = summary_response.json()

                return {
                    "summary": summary_data.get("summary", [{}])[0].get("data"),
                    "query": query,
                    "title": summary_data.get("title"),
                    "entities": summary_data.get("entities_info", []),
                }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Brave summarizer failed: {exc}",
                provider=self.name,
            ) from exc
