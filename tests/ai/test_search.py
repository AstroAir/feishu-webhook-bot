"""Tests for the AI search module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.ai.config import SearchProviderConfig, WebSearchConfig
from feishu_webhook_bot.ai.search.base import (
    SearchError,
    SearchProviderType,
    SearchResponse,
    SearchResult,
)
from feishu_webhook_bot.ai.search.cache import SearchCache
from feishu_webhook_bot.ai.search.manager import SearchManager
from feishu_webhook_bot.ai.search.providers import (
    BingSearchProvider,
    BraveSearchProvider,
    DuckDuckGoProvider,
    ExaSearchProvider,
    GoogleSearchProvider,
    TavilySearchProvider,
)


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


class TestSearchCache:
    """Tests for SearchCache."""

    def test_cache_set_and_get(self) -> None:
        """Test setting and getting cached results."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        response = SearchResponse(
            results=[SearchResult(title="Test", url="https://test.com", snippet="Test")],
            query="test query",
            provider="Test",
        )

        cache.set("test query", 10, response)
        cached = cache.get("test query", 10)

        assert cached is not None
        assert cached.query == "test query"
        assert cached.cached is True

    def test_cache_miss(self) -> None:
        """Test cache miss."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        result = cache.get("nonexistent", 10)
        assert result is None

    def test_cache_stats(self) -> None:
        """Test cache statistics."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        response = SearchResponse(
            results=[],
            query="test",
            provider="Test",
        )

        cache.set("test", 10, response)
        cache.get("test", 10)  # Hit
        cache.get("nonexistent", 10)  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_cache_clear(self) -> None:
        """Test clearing cache."""
        cache = SearchCache(ttl_minutes=60, max_size=100)
        response = SearchResponse(results=[], query="test", provider="Test")

        cache.set("test", 10, response)
        assert cache.get("test", 10) is not None

        cache.clear()
        assert cache.get("test", 10) is None
        stats = cache.get_stats()
        assert stats["size"] == 0

    def test_cache_max_size_eviction(self) -> None:
        """Test cache eviction when max size reached."""
        cache = SearchCache(ttl_minutes=60, max_size=3)

        for i in range(5):
            response = SearchResponse(results=[], query=f"query{i}", provider="Test")
            cache.set(f"query{i}", 10, response)

        stats = cache.get_stats()
        assert stats["size"] <= 3


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


class TestExaProvider:
    """Tests for ExaSearchProvider."""

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = ExaSearchProvider(api_key="test-key")
        assert provider.name == "Exa"
        assert provider.provider_type == SearchProviderType.EXA
        assert provider.is_configured is True


class TestBraveProvider:
    """Tests for BraveSearchProvider."""

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = BraveSearchProvider(api_key="test-key")
        assert provider.name == "Brave"
        assert provider.provider_type == SearchProviderType.BRAVE
        assert provider.is_configured is True


class TestBingProvider:
    """Tests for BingSearchProvider."""

    def test_provider_properties(self) -> None:
        """Test provider properties."""
        provider = BingSearchProvider(api_key="test-key")
        assert provider.name == "Bing"
        assert provider.provider_type == SearchProviderType.BING
        assert provider.is_configured is True


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
