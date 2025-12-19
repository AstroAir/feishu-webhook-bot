"""Tests for TavilySearchProvider.

Tests cover:
- Provider properties and configuration
- Search functionality
- Advanced features (QnA, extract, search context)
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.ai.search.base import SearchProviderType
from feishu_webhook_bot.ai.search.providers import TavilySearchProvider


class TestTavilyProvider:
    """Tests for TavilySearchProvider."""

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = TavilySearchProvider(api_key="test-key")
        assert provider.name == "Tavily"
        assert provider.provider_type == SearchProviderType.TAVILY
        assert provider.requires_api_key is True
        assert provider.is_configured is True

    def test_provider_not_configured(self) -> None:
        """Test provider without API key."""
        provider = TavilySearchProvider()
        assert provider.is_configured is False

    @pytest.mark.asyncio
    async def test_search_requires_api_key(self) -> None:
        """Test that search requires API key."""
        provider = TavilySearchProvider()

        with pytest.raises(Exception) as exc_info:
            await provider.search("test")

        assert "API key" in str(exc_info.value)

    def test_provider_stats(self) -> None:
        """Test provider statistics."""
        provider = TavilySearchProvider(api_key="test-key")
        stats = provider.get_stats()

        assert stats["name"] == "Tavily"
        assert stats["configured"] is True


class TestTavilyAdvancedFeatures:
    """Tests for Tavily advanced features."""

    def test_tavily_has_qna_search(self) -> None:
        """Test that Tavily provider has qna_search method."""
        provider = TavilySearchProvider(api_key="test-key")
        assert hasattr(provider, "qna_search")
        assert callable(provider.qna_search)

    def test_tavily_has_extract(self) -> None:
        """Test that Tavily provider has extract method."""
        provider = TavilySearchProvider(api_key="test-key")
        assert hasattr(provider, "extract")
        assert callable(provider.extract)

    def test_tavily_has_get_search_context(self) -> None:
        """Test that Tavily provider has get_search_context method."""
        provider = TavilySearchProvider(api_key="test-key")
        assert hasattr(provider, "get_search_context")
        assert callable(provider.get_search_context)

    @pytest.mark.asyncio
    async def test_extract_empty_urls(self) -> None:
        """Test extract with empty URLs returns empty result."""
        provider = TavilySearchProvider(api_key="test-key")
        result = await provider.extract([])
        assert result == {"results": [], "failed_results": []}
