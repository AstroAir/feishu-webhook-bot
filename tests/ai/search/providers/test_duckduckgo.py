"""Tests for DuckDuckGoProvider.

Tests cover:
- Provider properties
- Search functionality
- Statistics
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.ai.search.base import SearchProviderType
from feishu_webhook_bot.ai.search.providers import DuckDuckGoProvider


class TestDuckDuckGoProvider:
    """Tests for DuckDuckGoProvider."""

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = DuckDuckGoProvider()
        assert provider.name == "DuckDuckGo"
        assert provider.provider_type == SearchProviderType.DUCKDUCKGO
        assert provider.requires_api_key is False
        assert provider.is_configured is True

    @pytest.mark.asyncio
    async def test_search_with_mock(self) -> None:
        """Test search with mocked DDGS."""
        provider = DuckDuckGoProvider()

        mock_results = [
            {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet 1"},
            {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet 2"},
        ]

        with patch("feishu_webhook_bot.ai.search.providers.duckduckgo.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = mock_results
            mock_ddgs.return_value = mock_instance

            response = await provider.search("test query", max_results=5)

            assert response.query == "test query"
            assert response.provider == "DuckDuckGo"
            assert len(response.results) == 2
            assert response.results[0].title == "Result 1"

    def test_provider_stats(self) -> None:
        """Test provider statistics."""
        provider = DuckDuckGoProvider()
        stats = provider.get_stats()

        assert stats["name"] == "DuckDuckGo"
        assert stats["configured"] is True
        assert stats["request_count"] == 0

    @pytest.mark.asyncio
    async def test_search_empty_results(self) -> None:
        """Test search with empty results."""
        provider = DuckDuckGoProvider()

        with patch("feishu_webhook_bot.ai.search.providers.duckduckgo.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = []
            mock_ddgs.return_value = mock_instance

            response = await provider.search("no results query", max_results=5)

            assert response.query == "no results query"
            assert len(response.results) == 0
            assert response.has_results is False

    @pytest.mark.asyncio
    async def test_search_with_region(self) -> None:
        """Test search with region parameter."""
        provider = DuckDuckGoProvider(region="cn-zh")

        with patch("feishu_webhook_bot.ai.search.providers.duckduckgo.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "Chinese Result", "href": "https://example.cn", "body": "中文内容"},
            ]
            mock_ddgs.return_value = mock_instance

            response = await provider.search("测试", max_results=5)

            assert len(response.results) == 1
