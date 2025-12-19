"""Tests for BraveSearchProvider.

Tests cover:
- Provider properties and configuration
- Advanced features (search_news, search_images, search_videos, get_summary)
"""

from __future__ import annotations

from feishu_webhook_bot.ai.search.base import SearchProviderType
from feishu_webhook_bot.ai.search.providers import BraveSearchProvider


class TestBraveProvider:
    """Tests for BraveSearchProvider."""

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = BraveSearchProvider(api_key="test-key")
        assert provider.name == "Brave"
        assert provider.provider_type == SearchProviderType.BRAVE
        assert provider.is_configured is True

    def test_provider_not_configured(self) -> None:
        """Test provider without API key."""
        provider = BraveSearchProvider()
        assert provider.is_configured is False

    def test_provider_stats(self) -> None:
        """Test provider statistics."""
        provider = BraveSearchProvider(api_key="test-key")
        stats = provider.get_stats()

        assert stats["name"] == "Brave"
        assert stats["configured"] is True


class TestBraveAdvancedFeatures:
    """Tests for Brave advanced features."""

    def test_brave_has_search_news(self) -> None:
        """Test that Brave provider has search_news method."""
        provider = BraveSearchProvider(api_key="test-key")
        assert hasattr(provider, "search_news")
        assert callable(provider.search_news)

    def test_brave_has_search_images(self) -> None:
        """Test that Brave provider has search_images method."""
        provider = BraveSearchProvider(api_key="test-key")
        assert hasattr(provider, "search_images")
        assert callable(provider.search_images)

    def test_brave_has_search_videos(self) -> None:
        """Test that Brave provider has search_videos method."""
        provider = BraveSearchProvider(api_key="test-key")
        assert hasattr(provider, "search_videos")
        assert callable(provider.search_videos)

    def test_brave_has_get_summary(self) -> None:
        """Test that Brave provider has get_summary method."""
        provider = BraveSearchProvider(api_key="test-key")
        assert hasattr(provider, "get_summary")
        assert callable(provider.get_summary)
