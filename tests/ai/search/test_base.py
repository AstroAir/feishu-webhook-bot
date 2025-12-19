"""Tests for search base types and models.

Tests cover:
- SearchResult model
- SearchResponse model
- SearchError exception
- SearchProviderType enum
"""

from __future__ import annotations

from feishu_webhook_bot.ai.search.base import (
    SearchProviderType,
    SearchResponse,
    SearchResult,
)

# ==============================================================================
# SearchResult Tests
# ==============================================================================


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_search_result(self) -> None:
        """Test creating a SearchResult."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            position=1,
            relevance_score=0.95,
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.position == 1
        assert result.relevance_score == 0.95

    def test_search_result_defaults(self) -> None:
        """Test SearchResult default values."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
        )
        assert result.position == 1
        assert result.relevance_score == 1.0
        assert result.published_date is None
        assert result.source is None
        assert result.raw_data == {}

    def test_search_result_with_metadata(self) -> None:
        """Test SearchResult with raw_data metadata."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            raw_data={"key": "value", "nested": {"a": 1}},
        )
        assert result.raw_data["key"] == "value"
        assert result.raw_data["nested"]["a"] == 1

    def test_search_result_with_source(self) -> None:
        """Test SearchResult with source information."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            source="Wikipedia",
        )
        assert result.source == "Wikipedia"

    def test_search_result_with_published_date(self) -> None:
        """Test SearchResult with published date."""
        from datetime import datetime

        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            published_date="2024-01-15",
        )
        # published_date is converted to datetime
        assert result.published_date == datetime(2024, 1, 15, 0, 0)


# ==============================================================================
# SearchResponse Tests
# ==============================================================================


class TestSearchResponse:
    """Tests for SearchResponse model."""

    def test_create_search_response(self) -> None:
        """Test creating a SearchResponse."""
        results = [
            SearchResult(title="Result 1", url="https://example.com/1", snippet="Snippet 1"),
            SearchResult(title="Result 2", url="https://example.com/2", snippet="Snippet 2"),
        ]
        response = SearchResponse(
            results=results,
            query="test query",
            provider="TestProvider",
        )
        assert response.query == "test query"
        assert response.provider == "TestProvider"
        assert response.count == 2
        assert response.has_results is True

    def test_empty_response(self) -> None:
        """Test empty SearchResponse."""
        response = SearchResponse(
            results=[],
            query="test",
            provider="Test",
        )
        assert response.count == 0
        assert response.has_results is False

    def test_response_with_single_result(self) -> None:
        """Test SearchResponse with single result."""
        results = [
            SearchResult(title="Only Result", url="https://example.com", snippet="Snippet"),
        ]
        response = SearchResponse(
            results=results,
            query="single",
            provider="Test",
        )
        assert response.count == 1
        assert response.has_results is True

    def test_response_cached_flag(self) -> None:
        """Test SearchResponse cached flag."""
        response = SearchResponse(
            results=[],
            query="test",
            provider="Test",
            cached=True,
        )
        assert response.cached is True


# ==============================================================================
# SearchProviderType Tests
# ==============================================================================


class TestSearchProviderType:
    """Tests for SearchProviderType enum."""

    def test_all_provider_types(self) -> None:
        """Test all provider type values."""
        assert SearchProviderType.DUCKDUCKGO.value == "duckduckgo"
        assert SearchProviderType.TAVILY.value == "tavily"
        assert SearchProviderType.EXA.value == "exa"
        assert SearchProviderType.BRAVE.value == "brave"
        assert SearchProviderType.BING.value == "bing"
        assert SearchProviderType.GOOGLE.value == "google"
