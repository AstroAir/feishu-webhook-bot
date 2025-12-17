"""Exa search provider - semantic search engine.

Exa API supports:
- search: Neural/keyword search
- search_and_contents: Search with full text content
- find_similar: Find similar pages to a URL
- find_similar_and_contents: Find similar with content
- get_contents: Get content from URLs/IDs
- answer: AI-generated answers with citations
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

logger = get_logger("ai.search.exa")

EXA_API_BASE = "https://api.exa.ai"
EXA_SEARCH_URL = f"{EXA_API_BASE}/search"
EXA_FIND_SIMILAR_URL = f"{EXA_API_BASE}/findSimilar"
EXA_CONTENTS_URL = f"{EXA_API_BASE}/contents"
EXA_ANSWER_URL = f"{EXA_API_BASE}/answer"


class ExaSearchProvider(SearchProvider):
    """Exa search provider.

    Features:
    - Semantic/neural search
    - Code-friendly results
    - High-quality content for AI applications
    - Supports keyword and neural search modes
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        use_autoprompt: bool = True,
        search_type: str = "neural",
    ) -> None:
        """Initialize Exa provider.

        Args:
            api_key: Exa API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            use_autoprompt: Use Exa's autoprompt feature
            search_type: Search type (neural, keyword, auto)
        """
        super().__init__(api_key=api_key, timeout=timeout, max_retries=max_retries)
        self.use_autoprompt = use_autoprompt
        self.search_type = search_type

    @property
    def name(self) -> str:
        return "Exa"

    @property
    def provider_type(self) -> SearchProviderType:
        return SearchProviderType.EXA

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> SearchResponse:
        """Search using Exa API.

        Args:
            query: Search query
            max_results: Maximum results to return
            **options: Additional options (search_type, include_domains, exclude_domains)

        Returns:
            SearchResponse with results
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Exa API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Exa search: %s", query[:100])

        search_type = options.get("search_type", self.search_type)
        use_autoprompt = options.get("use_autoprompt", self.use_autoprompt)
        include_domains = options.get("include_domains", [])
        exclude_domains = options.get("exclude_domains", [])

        payload: dict[str, Any] = {
            "query": query,
            "numResults": max_results,
            "type": search_type,
            "useAutoprompt": use_autoprompt,
            "contents": {
                "text": True,
            },
        }

        if include_domains:
            payload["includeDomains"] = include_domains
        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        EXA_SEARCH_URL,
                        json=payload,
                        headers=headers,
                    )

                    if response.status_code == 401:
                        raise SearchAuthenticationError(
                            "Invalid Exa API key",
                            provider=self.name,
                        )
                    elif response.status_code == 429:
                        raise SearchRateLimitError(
                            "Exa rate limit exceeded",
                            provider=self.name,
                        )
                    elif response.status_code != 200:
                        raise SearchProviderError(
                            f"Exa API error: {response.status_code} - {response.text}",
                            provider=self.name,
                        )

                    data = response.json()

                # Convert to SearchResult objects
                search_results: list[SearchResult] = []
                for idx, item in enumerate(data.get("results", []), 1):
                    url = item.get("url", "")
                    search_results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=url,
                            snippet=item.get("text", "")[:500] if item.get("text") else "",
                            position=idx,
                            relevance_score=item.get("score", 1.0 - (idx - 1) * 0.05),
                            source=url.split("/")[2] if url else None,
                            raw_data=item,
                        )
                    )

                logger.info("Exa returned %d results", len(search_results))

                return SearchResponse(
                    results=search_results,
                    query=query,
                    provider=self.name,
                    total_results=len(search_results),
                    metadata={
                        "search_type": search_type,
                        "autoprompt_string": data.get("autopromptString"),
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
                        "Exa search attempt %d/%d failed: %s. Retrying in %ds...",
                        attempt + 1,
                        self.max_retries,
                        exc,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Exa search failed after %d attempts: %s",
                        self.max_retries,
                        exc,
                    )

        raise SearchProviderError(
            f"Exa search failed: {last_error}",
            provider=self.name,
        )

    async def find_similar(
        self,
        url: str,
        max_results: int = 10,
        exclude_source_domain: bool = True,
        **options: Any,
    ) -> SearchResponse:
        """Find pages similar to a given URL.

        Args:
            url: URL to find similar pages for
            max_results: Maximum results to return
            exclude_source_domain: Exclude results from the source domain
            **options: Additional options (include_domains, exclude_domains)

        Returns:
            SearchResponse with similar pages
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Exa API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Exa find_similar: %s", url[:100])

        include_domains = options.get("include_domains", [])
        exclude_domains = options.get("exclude_domains", [])

        payload: dict[str, Any] = {
            "url": url,
            "numResults": max_results,
            "excludeSourceDomain": exclude_source_domain,
            "contents": {"text": True},
        }

        if include_domains:
            payload["includeDomains"] = include_domains
        if exclude_domains:
            payload["excludeDomains"] = exclude_domains

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    EXA_FIND_SIMILAR_URL,
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Exa API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Exa rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Exa API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

            search_results: list[SearchResult] = []
            for idx, item in enumerate(data.get("results", []), 1):
                result_url = item.get("url", "")
                search_results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=result_url,
                        snippet=item.get("text", "")[:500] if item.get("text") else "",
                        position=idx,
                        relevance_score=item.get("score", 1.0 - (idx - 1) * 0.05),
                        source=result_url.split("/")[2] if result_url else None,
                        raw_data=item,
                    )
                )

            return SearchResponse(
                results=search_results,
                query=f"similar:{url}",
                provider=self.name,
                total_results=len(search_results),
                metadata={"source_url": url},
            )

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Exa find_similar failed: {exc}",
                provider=self.name,
            ) from exc

    async def get_contents(
        self,
        ids_or_urls: list[str],
        **options: Any,
    ) -> dict[str, Any]:
        """Get content from URLs or Exa result IDs.

        Args:
            ids_or_urls: List of URLs or Exa result IDs
            **options: Additional options (text, highlights)

        Returns:
            Dict with content for each URL/ID
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Exa API key is required",
                provider=self.name,
            )

        if not ids_or_urls:
            return {"contents": []}

        self._increment_request()
        logger.info("Exa get_contents: %d items", len(ids_or_urls))

        text_options = options.get("text", {"max_characters": 2000})
        highlights = options.get("highlights", False)

        payload: dict[str, Any] = {
            "ids": ids_or_urls[:10],  # Limit to 10
            "text": text_options,
        }

        if highlights:
            payload["highlights"] = (
                highlights if isinstance(highlights, dict) else {"num_sentences": 3}
            )

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
                response = await client.post(
                    EXA_CONTENTS_URL,
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Exa API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Exa rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Exa API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

                return {
                    "contents": [
                        {
                            "id": r.get("id"),
                            "url": r.get("url"),
                            "title": r.get("title"),
                            "text": r.get("text", ""),
                            "highlights": r.get("highlights", []),
                        }
                        for r in data.get("results", [])
                    ]
                }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Exa get_contents failed: {exc}",
                provider=self.name,
            ) from exc

    async def answer(
        self,
        query: str,
        **options: Any,
    ) -> dict[str, Any]:
        """Get an AI-generated answer with citations.

        Args:
            query: Question to answer
            **options: Additional options (text, include_domains)

        Returns:
            Dict with answer and citations
        """
        if not self.api_key:
            raise SearchAuthenticationError(
                "Exa API key is required",
                provider=self.name,
            )

        self._increment_request()
        logger.info("Exa answer: %s", query[:100])

        include_text = options.get("text", True)
        include_domains = options.get("include_domains", [])

        payload: dict[str, Any] = {
            "query": query,
            "text": include_text,
        }

        if include_domains:
            payload["includeDomains"] = include_domains

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
                response = await client.post(
                    EXA_ANSWER_URL,
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 401:
                    raise SearchAuthenticationError(
                        "Invalid Exa API key",
                        provider=self.name,
                    )
                elif response.status_code == 429:
                    raise SearchRateLimitError(
                        "Exa rate limit exceeded",
                        provider=self.name,
                    )
                elif response.status_code != 200:
                    raise SearchProviderError(
                        f"Exa API error: {response.status_code}",
                        provider=self.name,
                    )

                data = response.json()

                return {
                    "answer": data.get("answer", ""),
                    "query": query,
                    "citations": [
                        {
                            "url": c.get("url"),
                            "title": c.get("title"),
                            "text": c.get("text", "")[:500] if c.get("text") else "",
                        }
                        for c in data.get("citations", [])
                    ],
                }

        except (SearchAuthenticationError, SearchRateLimitError):
            raise
        except Exception as exc:
            self._increment_error()
            raise SearchProviderError(
                f"Exa answer failed: {exc}",
                provider=self.name,
            ) from exc
