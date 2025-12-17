"""Bing Web Search API provider.

Bing Search API supports:
- web: Web search
- news: News search
- images: Image search
- videos: Video search
- entities: Entity search
- suggestions: Autosuggest
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

logger = get_logger("ai.search.bing")

BING_API_BASE = "https://api.bing.microsoft.com/v7.0"
BING_WEB_URL = f"{BING_API_BASE}/search"
BING_NEWS_URL = f"{BING_API_BASE}/news/search"
BING_IMAGES_URL = f"{BING_API_BASE}/images/search"
BING_VIDEOS_URL = f"{BING_API_BASE}/videos/search"
BING_ENTITIES_URL = f"{BING_API_BASE}/entities"
BING_SUGGESTIONS_URL = f"{BING_API_BASE}/suggestions"


class BingSearchProvider(SearchProvider):
    """Bing Web Search API provider.

    Features:
    - Microsoft's official search API
    - Reliable and stable
    - Good coverage of web content
    - Supports market and language filtering
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        market: str = "en-US",
        safesearch: str = "Moderate",
    ) -> None:
        """Initialize Bing Search provider.

        Args:
            api_key: Bing Search API key (Azure Cognitive Services)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            market: Market code (e.g., en-US, zh-CN)
            safesearch: Safe search level (Off, Moderate, Strict)
        """
        super().__init__(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.market = market
        self.safesearch = safesearch

    @property
    def name(self) -> str:
        return "Bing"

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.BING

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> SearchResponse:
        """Search using Bing Web Search API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (market, safesearch, freshness)

        Returns:
            SearchResponse with results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Bing Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Bing search: %s", query[:100])

        market = options.get("market", self.market)
        safesearch = options.get("safesearch", self.safesearch)
        freshness = options.get("freshness")  # Day, Week, Month

        params: dict[str, Any] = {
            "q": query,
            "count": max_results,
            "mkt": market,
            "safeSearch": safesearch,
            "textDecorations": False,
            "textFormat": "Raw",
        }

        if freshness:
            params["freshness"] = freshness

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        BING_WEB_URL,
                        params=params,
                        headers=headers,
                    )

                    if response.status_code == 401:
                        raise SearchAuthenticationError(
                            "Invalid Bing Search API key",
                            provider=self.name,
                        )
                    elif response.status_code == 429:
                        raise SearchRateLimitError(
                            "Bing Search rate limit exceeded",
                            provider=self.name,
                        )
                    elif response.status_code != 200:
                        raise SearchProviderError(
                            f"Bing Search API error: {response.status_code} - {response.text}",
                            provider=self.name,
                        )

                    data = response.json()

                # Convert to SearchResult objects
                search_results: list[SearchResult] = []
                web_pages = data.get("webPages", {}).get("value", [])

                for idx, item in enumerate(web_pages, 1):
                    url = item.get("url", "")

                    # Parse date if available
                    published_date = None
                    if item.get("dateLastCrawled"):
                        with contextlib.suppress(Exception):
                            published_date = datetime.fromisoformat(
                                item["dateLastCrawled"].replace("Z", "+00:00")
                            )

                    search_results.append(
                        SearchResult(
                            title=item.get("name", ""),
                            url=url,
                            snippet=item.get("snippet", ""),
                            position=idx,
                            relevance_score=1.0 - (idx - 1) * 0.05,
                            published_date=published_date,
                            source=(
                                item.get("displayUrl", "").split("/")[0]
                                if item.get("displayUrl")
                                else None
                            ),
                            raw_data=item,
                        )
                    )

                logger.info("Bing returned %d results", len(search_results))

                return SearchResponse(
                    results=search_results,
                    query=query,
                    provider=self.name,
                    total_results=data.get("webPages", {}).get("totalEstimatedMatches"),
                    metadata={
                        "market": market,
                        "query_context": data.get("queryContext"),
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
                        "Bing search attempt %d/%d failed: %s. Retrying in %ds...",
                        attempt + 1,
                        self.max_retries,
                        exc,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Bing search failed after %d attempts: %s",
                        self.max_retries,
                        exc,
                    )

        raise SearchProviderError(
            f"Bing search failed: {last_error}",
            provider=self.name,
        )

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> SearchResponse:
        """Search news articles using Bing News API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (market, freshness, category)

        Returns:
            SearchResponse with news results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Bing Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Bing news search: %s", query[:100])

        market = options.get("market", self.market)
        freshness = options.get("freshness")  # Day, Week, Month
        category = options.get("category")  # Business, Entertainment, Health, etc.

        params: dict[str, Any] = {
            "q": query,
            "count": max_results,
            "mkt": market,
            "safeSearch": self.safesearch,
        }

        if freshness:
            params["freshness"] = freshness
        if category:
            params["category"] = category

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    BING_NEWS_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Bing Search API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Bing Search rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Bing News API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

            search_results: list[SearchResult] = []
            news_items = data.get("value", [])

            for idx, item in enumerate(news_items, 1):
                url = item.get("url", "")

                published_date = None
                if item.get("datePublished"):
                    with contextlib.suppress(Exception):
                        published_date = datetime.fromisoformat(
                            item["datePublished"].replace("Z", "+00:00")
                        )

                search_results.append(
                    SearchResult(
                        title=item.get("name", ""),
                        url=url,
                        snippet=item.get("description", ""),
                        position=idx,
                        relevance_score=1.0 - (idx - 1) * 0.05,
                        published_date=published_date,
                        source=item.get("provider", [{}])[0].get("name"),
                        raw_data=item,
                    )
                )

            logger.info("Bing news returned %d results", len(search_results))

            return SearchResponse(
                results=search_results,
                query=query,
                provider=f"{self.name} News",
                total_results=data.get("totalEstimatedMatches"),
                metadata={"type": "news", "market": market},
            )

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Bing news search failed: {exc}",
                provider=self.name,
            ) from exc

    async def search_images(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> dict[str, Any]:
        """Search images using Bing Images API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (market, size, color, imageType)

        Returns:
            Dict with image results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Bing Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Bing image search: %s", query[:100])

        market = options.get("market", self.market)
        size = options.get("size")  # Small, Medium, Large, Wallpaper
        color = options.get("color")  # ColorOnly, Monochrome, specific colors
        image_type = options.get("imageType")  # Photo, Clipart, Line, etc.

        params: dict[str, Any] = {
            "q": query,
            "count": max_results,
            "mkt": market,
            "safeSearch": self.safesearch,
        }

        if size:
            params["size"] = size
        if color:
            params["color"] = color
        if image_type:
            params["imageType"] = image_type

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    BING_IMAGES_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Bing Search API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Bing Search rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Bing Images API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

            images = [
                {
                    "title": img.get("name", ""),
                    "url": img.get("contentUrl", ""),
                    "thumbnail": img.get("thumbnailUrl"),
                    "host_page": img.get("hostPageUrl"),
                    "width": img.get("width"),
                    "height": img.get("height"),
                    "content_size": img.get("contentSize"),
                    "encoding_format": img.get("encodingFormat"),
                }
                for img in data.get("value", [])
            ]

            logger.info("Bing images returned %d results", len(images))

            return {
                "images": images,
                "query": query,
                "total": data.get("totalEstimatedMatches"),
            }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Bing image search failed: {exc}",
                provider=self.name,
            ) from exc

    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> dict[str, Any]:
        """Search videos using Bing Videos API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (market, freshness, resolution)

        Returns:
            Dict with video results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Bing Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Bing video search: %s", query[:100])

        market = options.get("market", self.market)
        freshness = options.get("freshness")  # Day, Week, Month
        resolution = options.get("resolution")  # 480p, 720p, 1080p

        params: dict[str, Any] = {
            "q": query,
            "count": max_results,
            "mkt": market,
            "safeSearch": self.safesearch,
        }

        if freshness:
            params["freshness"] = freshness
        if resolution:
            params["resolution"] = resolution

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    BING_VIDEOS_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Bing Search API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Bing Search rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Bing Videos API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

            videos = [
                {
                    "title": vid.get("name", ""),
                    "url": vid.get("contentUrl", ""),
                    "description": vid.get("description", ""),
                    "thumbnail": vid.get("thumbnailUrl"),
                    "duration": vid.get("duration"),
                    "publisher": vid.get("publisher", [{}])[0].get("name"),
                    "view_count": vid.get("viewCount"),
                    "date_published": vid.get("datePublished"),
                }
                for vid in data.get("value", [])
            ]

            logger.info("Bing videos returned %d results", len(videos))

            return {
                "videos": videos,
                "query": query,
                "total": data.get("totalEstimatedMatches"),
            }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Bing video search failed: {exc}",
                provider=self.name,
            ) from exc

    async def search_entities(
        self,
        query: str,
        **options: Any,
    ) -> dict[str, Any]:
        """Search entities using Bing Entity Search API.

        Args:
            query: Search query
            **options: Additional options (market)

        Returns:
            Dict with entity information
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Bing Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Bing entity search: %s", query[:100])

        market = options.get("market", self.market)

        params = {
            "q": query,
            "mkt": market,
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    BING_ENTITIES_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Bing Search API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Bing Search rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Bing Entities API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

            entities = []
            for entity in data.get("entities", {}).get("value", []):
                entities.append(
                    {
                        "name": entity.get("name", ""),
                        "description": entity.get("description", ""),
                        "url": entity.get("url"),
                        "image": entity.get("image", {}).get("thumbnailUrl"),
                        "entity_type": entity.get("entityPresentationInfo", {}).get(
                            "entityTypeDisplayHint"
                        ),
                    }
                )

            places = []
            for place in data.get("places", {}).get("value", []):
                places.append(
                    {
                        "name": place.get("name", ""),
                        "address": place.get("address", {}),
                        "telephone": place.get("telephone"),
                        "url": place.get("url"),
                    }
                )

            logger.info(
                "Bing entities returned %d entities, %d places",
                len(entities),
                len(places),
            )

            return {
                "entities": entities,
                "places": places,
                "query": query,
            }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Bing entity search failed: {exc}",
                provider=self.name,
            ) from exc

    async def get_suggestions(
        self,
        query: str,
        **options: Any,
    ) -> list[str]:
        """Get search suggestions using Bing Autosuggest API.

        Args:
            query: Partial search query
            **options: Additional options (market)

        Returns:
            List of suggested queries
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Bing Search API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Bing suggestions: %s", query[:100])

        market = options.get("market", self.market)

        params = {
            "q": query,
            "mkt": market,
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    BING_SUGGESTIONS_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Bing Search API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Bing Search rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Bing Suggestions API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

            suggestions = []
            for group in data.get("suggestionGroups", []):
                for suggestion in group.get("searchSuggestions", []):
                    suggestions.append(suggestion.get("displayText", ""))

            logger.info("Bing suggestions returned %d items", len(suggestions))

            return suggestions

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Bing suggestions failed: {exc}",
                provider=self.name,
            ) from exc
