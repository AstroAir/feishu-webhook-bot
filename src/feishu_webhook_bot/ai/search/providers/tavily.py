"""Tavily search provider - AI-optimized search engine.

Tavily API supports:
- search: AI-optimized web search
- qna_search: Direct Q&A with AI-generated answers
- extract: Extract content from URLs
- get_search_context: Get search context for RAG
"""

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

logger = get_logger("ai.search.tavily")

TAVILY_API_BASE = "https://api.tavily.com"
TAVILY_SEARCH_URL = f"{TAVILY_API_BASE}/search"
TAVILY_EXTRACT_URL = f"{TAVILY_API_BASE}/extract"


class TavilySearchProvider(SearchProvider):
    """Tavily search provider.

    Features:
    - AI-optimized search results
    - High-quality content extraction
    - Supports different search depths
    - Includes AI-generated answer summaries
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        search_depth: str = "basic",
        include_answer: bool = True,
        include_raw_content: bool = False,
    ) -> None:
        """Initialize Tavily provider.

        Args:
            api_key: Tavily API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            search_depth: Search depth (basic or advanced)
            include_answer: Include AI-generated answer
            include_raw_content: Include raw page content
        """
        super().__init__(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.search_depth = search_depth
        self.include_answer = include_answer
        self.include_raw_content = include_raw_content

    @property
    def name(self) -> str:
        return "Tavily"

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.TAVILY

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> SearchResponse:
        """Search using Tavily API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (search_depth, include_domains, exclude_domains)

        Returns:
            SearchResponse with results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Tavily API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Tavily search: %s", query[:100])

        search_depth = options.get("search_depth", self.search_depth)
        include_answer = options.get("include_answer", self.include_answer)
        include_domains = options.get("include_domains", [])
        exclude_domains = options.get("exclude_domains", [])

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": self.include_raw_content,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(TAVILY_SEARCH_URL, json=payload)

                    if response.status_code == 401:
                        raise SearchAuthenticationError(
                            "Invalid Tavily API key",
                            provider=self.name,
                        )
                    elif response.status_code == 429:
                        raise SearchRateLimitError(
                            "Tavily rate limit exceeded",
                            provider=self.name,
                        )
                    elif response.status_code != 200:
                        raise SearchProviderError(
                            f"Tavily API error: {response.status_code} - {response.text}",
                            provider=self.name,
                        )

                    data = response.json()

                # Convert to SearchResult objects
                search_results: list[SearchResult] = []
                for idx, item in enumerate(data.get("results", []), 1):
                    search_results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("content", ""),
                            position=idx,
                            relevance_score=item.get("score", 1.0 - (idx - 1) * 0.05),
                            source=item.get("url", "").split("/")[2] if item.get("url") else None,
                            raw_data=item,
                        )
                    )

                logger.info("Tavily returned %d results", len(search_results))

                metadata = {
                    "search_depth": search_depth,
                    "response_time": data.get("response_time"),
                }

                # Include AI answer if available
                if data.get("answer"):
                    metadata["ai_answer"] = data["answer"]

                return SearchResponse(
                    results=search_results,
                    query=query,
                    provider=self.name,
                    total_results=len(search_results),
                    metadata=metadata,
                )

            except (SearchAuthenticationError, SearchRateLimitError):
                raise
            except Exception as exc:
                last_error = exc
                self._increment_error()

                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Tavily search attempt %d/%d failed: %s. Retrying in %ds...",
                        attempt + 1,
                        self.max_retries,
                        exc,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Tavily search failed after %d attempts: %s",
                        self.max_retries,
                        exc,
                    )

        raise SearchProviderError(
            f"Tavily search failed: {last_error}",
            provider=self.name,
        )

    async def qna_search(
        self,
        query: str,
        **options: Any,
    ) -> dict[str, Any]:
        """Get a direct AI-generated answer for a question.

        Args:
            query: Question to answer
            **options: Additional options (search_depth, include_domains, exclude_domains)

        Returns:
            Dict with answer and supporting information
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Tavily API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Tavily Q&A search: %s", query[:100])

        search_depth = options.get("search_depth", "advanced")
        include_domains = options.get("include_domains", [])
        exclude_domains = options.get("exclude_domains", [])

        payload: dict[str, Any] = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "include_answer": True,
            "max_results": 5,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(TAVILY_SEARCH_URL, json=payload)

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Tavily API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Tavily rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Tavily API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

                return {
                    "answer": data.get("answer", ""),
                    "query": query,
                    "sources": [
                        {"title": r.get("title"), "url": r.get("url")}
                        for r in data.get("results", [])[:3]
                    ],
                    "response_time": data.get("response_time"),
                }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Tavily Q&A search failed: {exc}",
                provider=self.name,
            ) from exc

    async def extract(
        self,
        urls: list[str],
        **options: Any,
    ) -> dict[str, Any]:
        """Extract content from URLs.

        Args:
            urls: List of URLs to extract content from
            **options: Additional options (extract_depth)

        Returns:
            Dict with extracted content for each URL
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Tavily API key is required",
                provider=self.name,
            )

        if not urls:
            return {"results": [], "failed_results": []}

        self._increment_request()
        logger.info("Tavily extract: %d URLs", len(urls))

        extract_depth = options.get("extract_depth", "basic")

        payload: dict[str, Any] = {
            "api_key": self.api_key,
            "urls": urls[:10],  # Limit to 10 URLs
            "extract_depth": extract_depth,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
                response = await client.post(TAVILY_EXTRACT_URL, json=payload)

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Tavily API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Tavily rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Tavily extract error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

                return {
                    "results": [
                        {
                            "url": r.get("url"),
                            "raw_content": r.get("raw_content", ""),
                        }
                        for r in data.get("results", [])
                    ],
                    "failed_results": data.get("failed_results", []),
                }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Tavily extract failed: {exc}",
                provider=self.name,
            ) from exc

    async def get_search_context(
        self,
        query: str,
        max_tokens: int = 4000,
        **options: Any,
    ) -> str:
        """Get search context optimized for RAG applications.

        Args:
            query: Search query
            max_tokens: Maximum tokens for context
            **options: Additional options

        Returns:
            Concatenated search context as string
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Tavily API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Tavily get_search_context: %s", query[:100])

        # Use advanced search for better context
        response = await self.search(
            query,
            max_results=5,
            search_depth="advanced",
            include_answer=True,
            **options,
        )

        # Build context from results
        context_parts = []

        # Add AI answer if available
        if response.metadata.get("ai_answer"):
            context_parts.append(f"Summary: {response.metadata['ai_answer']}\n")

        # Add search results
        for result in response.results:
            snippet = result.snippet[:500] if result.snippet else ""
            context_parts.append(f"Source: {result.title}\nURL: {result.url}\n{snippet}\n")

        context = "\n---\n".join(context_parts)

        # Rough token estimation (4 chars per token)
        if len(context) > max_tokens * 4:
            context = context[: max_tokens * 4]

        return context
