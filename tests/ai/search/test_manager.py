"""Tests for SearchManager.

Tests cover:
- Manager initialization
- Provider registration
- Search operations
- Failover handling
- Statistics
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.ai.config import SearchProviderConfig, WebSearchConfig
from feishu_webhook_bot.ai.search.base import SearchError
from feishu_webhook_bot.ai.search.manager import SearchManager
from feishu_webhook_bot.ai.search.providers import (
    DuckDuckGoProvider,
    TavilySearchProvider,
)

# ==============================================================================
# SearchManager Tests
# ==============================================================================


class TestSearchManager:
    """Tests for SearchManager."""

    def test_create_manager(self) -> None:
        """Test creating a SearchManager."""
        manager = SearchManager()
        assert manager is not None
        stats = manager.get_stats()
        assert stats["provider_count"] == 0

    def test_register_provider(self) -> None:
        """Test registering a provider."""
        manager = SearchManager()
        provider = DuckDuckGoProvider()

        manager.register_provider(provider)

        assert manager.get_provider("DuckDuckGo") is not None
        stats = manager.get_stats()
        assert stats["provider_count"] == 1

    def test_get_configured_providers(self) -> None:
        """Test getting configured providers."""
        manager = SearchManager()
        manager.register_provider(DuckDuckGoProvider())
        manager.register_provider(TavilySearchProvider())  # Not configured

        configured = manager.get_configured_providers()
        assert len(configured) == 1
        assert configured[0].name == "DuckDuckGo"

    @pytest.mark.asyncio
    async def test_search_with_provider(self) -> None:
        """Test search using a specific provider."""
        manager = SearchManager()
        provider = DuckDuckGoProvider()
        manager.register_provider(provider)

        mock_results = [
            {"title": "Result", "href": "https://example.com", "body": "Snippet"},
        ]

        with patch("feishu_webhook_bot.ai.search.providers.duckduckgo.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = mock_results
            mock_ddgs.return_value = mock_instance

            response = await manager.search("test", max_results=5)

            assert response.provider == "DuckDuckGo"
            assert len(response.results) == 1

    @pytest.mark.asyncio
    async def test_search_no_providers(self) -> None:
        """Test search with no providers configured."""
        manager = SearchManager()

        with pytest.raises(SearchError) as exc_info:
            await manager.search("test")

        assert "No configured search providers" in str(exc_info.value)

    def test_manager_stats(self) -> None:
        """Test manager statistics."""
        manager = SearchManager()
        manager.register_provider(DuckDuckGoProvider())

        stats = manager.get_stats()
        assert stats["total_searches"] == 0
        assert stats["provider_count"] == 1
        assert "DuckDuckGo" in stats["providers"]

    def test_register_multiple_providers(self) -> None:
        """Test registering multiple providers."""
        manager = SearchManager()
        manager.register_provider(DuckDuckGoProvider())
        manager.register_provider(TavilySearchProvider(api_key="test-key"))

        stats = manager.get_stats()
        assert stats["provider_count"] == 2


# ==============================================================================
# WebSearchConfig Tests
# ==============================================================================


class TestWebSearchConfig:
    """Tests for WebSearchConfig."""

    def test_default_config(self) -> None:
        """Test default WebSearchConfig."""
        config = WebSearchConfig()
        assert config.enabled is True
        assert config.default_provider == "duckduckgo"
        assert config.max_results == 5
        assert config.cache_enabled is True
        assert config.enable_failover is True
        assert len(config.providers) == 1

    def test_custom_config(self) -> None:
        """Test custom WebSearchConfig."""
        config = WebSearchConfig(
            enabled=True,
            max_results=10,
            providers=[
                SearchProviderConfig(provider="duckduckgo", priority=0),
                SearchProviderConfig(provider="tavily", api_key="test-key", priority=10),
            ],
        )
        assert config.max_results == 10
        assert len(config.providers) == 2


# ==============================================================================
# SearchProviderConfig Tests
# ==============================================================================


class TestSearchProviderConfig:
    """Tests for SearchProviderConfig."""

    def test_create_config(self) -> None:
        """Test creating SearchProviderConfig."""
        config = SearchProviderConfig(
            provider="tavily",
            enabled=True,
            api_key="test-key",
            priority=10,
        )
        assert config.provider == "tavily"
        assert config.enabled is True
        assert config.api_key == "test-key"
        assert config.priority == 10

    def test_default_values(self) -> None:
        """Test default values."""
        config = SearchProviderConfig(provider="duckduckgo")
        assert config.enabled is True
        assert config.api_key is None
        assert config.priority == 100
        assert config.options == {}


# ==============================================================================
# InitSearchManager Tests
# ==============================================================================


class TestInitSearchManager:
    """Tests for init_search_manager function."""

    def test_init_with_duckduckgo(self) -> None:
        """Test initializing manager with DuckDuckGo."""
        from feishu_webhook_bot.ai.tools import init_search_manager

        config = WebSearchConfig(
            providers=[
                SearchProviderConfig(provider="duckduckgo", priority=0),
            ]
        )

        manager = init_search_manager(config)
        assert manager is not None
        assert len(manager.get_configured_providers()) == 1

    def test_init_with_multiple_providers(self) -> None:
        """Test initializing manager with multiple providers."""
        from feishu_webhook_bot.ai.tools import init_search_manager

        config = WebSearchConfig(
            providers=[
                SearchProviderConfig(provider="duckduckgo", priority=0),
                SearchProviderConfig(provider="tavily", api_key="test", priority=10),
            ]
        )

        manager = init_search_manager(config)
        assert manager is not None
        # DuckDuckGo is configured, Tavily has API key so also configured
        assert len(manager.get_configured_providers()) == 2

    def test_init_disabled_provider(self) -> None:
        """Test that disabled providers are not added."""
        from feishu_webhook_bot.ai.tools import init_search_manager

        config = WebSearchConfig(
            providers=[
                SearchProviderConfig(provider="duckduckgo", priority=0, enabled=False),
            ]
        )

        manager = init_search_manager(config)
        assert len(manager.get_configured_providers()) == 0
