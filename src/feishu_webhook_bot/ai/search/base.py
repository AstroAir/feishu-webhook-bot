"""Base classes and interfaces for search providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SearchError(Exception):
    """Base exception for search-related errors."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        """Initialize search error.

        Args:
            message: Error message
            provider: Name of the provider that raised the error
        """
        self.provider = provider
        super().__init__(message)


class SearchProviderError(SearchError):
    """Error from a specific search provider."""

    pass


class SearchRateLimitError(SearchError):
    """Rate limit exceeded for a search provider."""

    pass


class SearchAuthenticationError(SearchError):
    """Authentication failed for a search provider."""

    pass


class SearchProviderType(str, Enum):
    """Supported search provider types."""

    DUCKDUCKGO = "duckduckgo"
    TAVILY = "tavily"
    EXA = "exa"
    BRAVE = "brave"
    BING = "bing"
    GOOGLE = "google"


class SearchResult(BaseModel):
    """Standardized search result from any provider.

    Attributes:
        title: Result title
        url: Result URL
        snippet: Text snippet/description
        position: Position in search results (1-indexed)
        relevance_score: Relevance score (0.0-1.0)
        published_date: Publication date if available
        source: Source domain
        raw_data: Raw data from the provider
    """

    title: str = Field(description="Result title")
    url: str = Field(description="Result URL")
    snippet: str = Field(description="Text snippet or description")
    position: int = Field(default=1, ge=1, description="Position in results")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Relevance score")
    published_date: datetime | None = Field(default=None, description="Publication date")
    source: str | None = Field(default=None, description="Source domain")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw provider data")


class SearchResponse(BaseModel):
    """Response from a search operation.

    Attributes:
        results: List of search results
        query: Original search query
        provider: Provider that returned the results
        total_results: Total number of results available
        cached: Whether results were from cache
        timestamp: When the search was performed
        search_time_ms: Time taken for search in milliseconds
        metadata: Additional metadata from the provider
    """

    results: list[SearchResult] = Field(default_factory=list, description="Search results")
    query: str = Field(description="Original search query")
    provider: str = Field(description="Search provider name")
    total_results: int | None = Field(default=None, description="Total results available")
    cached: bool = Field(default=False, description="Whether from cache")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Search timestamp",
    )
    search_time_ms: float = Field(default=0.0, description="Search time in milliseconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def count(self) -> int:
        """Get the number of results returned."""
        return len(self.results)

    @property
    def has_results(self) -> bool:
        """Check if any results were returned."""
        return len(self.results) > 0


class SearchProvider(ABC):
    """Abstract base class for search providers.

    All search providers must implement this interface to ensure
    consistent behavior across different search engines.
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the search provider.

        Args:
            api_key: API key for the provider (if required)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._request_count = 0
        self._error_count = 0

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the provider name."""
        pass

    @property
    @abstractmethod
    def provider_type(self) -> SearchProviderType:
        """Get the provider type."""
        pass

    @property
    def requires_api_key(self) -> bool:
        """Check if this provider requires an API key."""
        return True

    @property
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        if self.requires_api_key:
            return bool(self.api_key)
        return True

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        **options: Any,
    ) -> SearchResponse:
        """Perform a search query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            **options: Provider-specific options

        Returns:
            SearchResponse with results

        Raises:
            SearchError: If search fails
        """
        pass

    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible.

        Returns:
            True if provider is healthy
        """
        if not self.is_configured:
            return False

        try:
            response = await self.search("test", max_results=1)
            return response.has_results or True  # Even empty results mean it's working
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get provider statistics.

        Returns:
            Dictionary with provider statistics
        """
        return {
            "name": self.name,
            "type": self.provider_type.value,
            "configured": self.is_configured,
            "requires_api_key": self.requires_api_key,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": (
                self._error_count / self._request_count if self._request_count > 0 else 0.0
            ),
        }

    def _increment_request(self) -> None:
        """Increment request counter."""
        self._request_count += 1

    def _increment_error(self) -> None:
        """Increment error counter."""
        self._error_count += 1
