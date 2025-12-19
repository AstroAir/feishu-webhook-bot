"""Tests for ExaSearchProvider.

Tests cover:
- Provider properties and configuration
- Advanced features (find_similar, get_contents, answer)
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.ai.search.base import SearchProviderType
from feishu_webhook_bot.ai.search.providers import ExaSearchProvider


class TestExaProvider:
    """Tests for ExaSearchProvider."""

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = ExaSearchProvider(api_key="test-key")
        assert provider.name == "Exa"
        assert provider.provider_type == SearchProviderType.EXA
        assert provider.is_configured is True

    def test_provider_not_configured(self) -> None:
        """Test provider without API key."""
        provider = ExaSearchProvider()
        assert provider.is_configured is False

    def test_provider_stats(self) -> None:
        """Test provider statistics."""
        provider = ExaSearchProvider(api_key="test-key")
        stats = provider.get_stats()

        assert stats["name"] == "Exa"
        assert stats["configured"] is True


class TestExaAdvancedFeatures:
    """Tests for Exa advanced features."""

    def test_exa_has_find_similar(self) -> None:
        """Test that Exa provider has find_similar method."""
        provider = ExaSearchProvider(api_key="test-key")
        assert hasattr(provider, "find_similar")
        assert callable(provider.find_similar)

    def test_exa_has_get_contents(self) -> None:
        """Test that Exa provider has get_contents method."""
        provider = ExaSearchProvider(api_key="test-key")
        assert hasattr(provider, "get_contents")
        assert callable(provider.get_contents)

    def test_exa_has_answer(self) -> None:
        """Test that Exa provider has answer method."""
        provider = ExaSearchProvider(api_key="test-key")
        assert hasattr(provider, "answer")
        assert callable(provider.answer)

    @pytest.mark.asyncio
    async def test_get_contents_empty_ids(self) -> None:
        """Test get_contents with empty IDs returns empty result."""
        provider = ExaSearchProvider(api_key="test-key")
        result = await provider.get_contents([])
        assert result == {"contents": []}
