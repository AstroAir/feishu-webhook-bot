"""Tests for BingSearchProvider.

Tests cover:
- Provider properties and configuration
- Advanced features (search_news, search_images, search_videos, search_entities, get_suggestions)
"""

from __future__ import annotations

from feishu_webhook_bot.ai.search.base import SearchProviderType
from feishu_webhook_bot.ai.search.providers import BingSearchProvider


class TestBingProvider:
    """Tests for BingSearchProvider."""

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = BingSearchProvider(api_key="test-key")
        assert provider.name == "Bing"
        assert provider.provider_type == SearchProviderType.BING
        assert provider.is_configured is True

    def test_provider_not_configured(self) -> None:
        """Test provider without API key."""
        provider = BingSearchProvider()
        assert provider.is_configured is False

    def test_provider_stats(self) -> None:
        """Test provider statistics."""
        provider = BingSearchProvider(api_key="test-key")
        stats = provider.get_stats()

        assert stats["name"] == "Bing"
        assert stats["configured"] is True


class TestBingAdvancedFeatures:
    """Tests for Bing advanced features."""

    def test_bing_has_search_news(self) -> None:
        """Test that Bing provider has search_news method."""
        provider = BingSearchProvider(api_key="test-key")
        assert hasattr(provider, "search_news")
        assert callable(provider.search_news)

    def test_bing_has_search_images(self) -> None:
        """Test that Bing provider has search_images method."""
        provider = BingSearchProvider(api_key="test-key")
        assert hasattr(provider, "search_images")
        assert callable(provider.search_images)

    def test_bing_has_search_videos(self) -> None:
        """Test that Bing provider has search_videos method."""
        provider = BingSearchProvider(api_key="test-key")
        assert hasattr(provider, "search_videos")
        assert callable(provider.search_videos)

    def test_bing_has_search_entities(self) -> None:
        """Test that Bing provider has search_entities method."""
        provider = BingSearchProvider(api_key="test-key")
        assert hasattr(provider, "search_entities")
        assert callable(provider.search_entities)

    def test_bing_has_get_suggestions(self) -> None:
        """Test that Bing provider has get_suggestions method."""
        provider = BingSearchProvider(api_key="test-key")
        assert hasattr(provider, "get_suggestions")
        assert callable(provider.get_suggestions)
