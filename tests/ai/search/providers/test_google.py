"""Tests for GoogleSearchProvider.

Tests cover:
- Provider properties and configuration
- CX requirement
"""

from __future__ import annotations

from feishu_webhook_bot.ai.search.base import SearchProviderType
from feishu_webhook_bot.ai.search.providers import GoogleSearchProvider


class TestGoogleProvider:
    """Tests for GoogleSearchProvider."""

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = GoogleSearchProvider(api_key="test-key", cx="test-cx")
        assert provider.name == "Google"
        assert provider.provider_type == SearchProviderType.GOOGLE
        assert provider.is_configured is True

    def test_provider_requires_cx(self) -> None:
        """Test that Google provider requires CX."""
        provider = GoogleSearchProvider(api_key="test-key")
        assert provider.is_configured is False

    def test_provider_not_configured_without_api_key(self) -> None:
        """Test provider without API key."""
        provider = GoogleSearchProvider()
        assert provider.is_configured is False

    def test_provider_not_configured_with_only_cx(self) -> None:
        """Test provider with only CX (no API key)."""
        provider = GoogleSearchProvider(cx="test-cx")
        assert provider.is_configured is False

    def test_provider_stats(self) -> None:
        """Test provider statistics."""
        provider = GoogleSearchProvider(api_key="test-key", cx="test-cx")
        stats = provider.get_stats()

        assert stats["name"] == "Google"
        assert stats["configured"] is True
