"""Tests for AI features including caching, retry logic, and tools."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from feishu_webhook_bot.ai.conversation import ConversationManager, ConversationState
from feishu_webhook_bot.ai.exceptions import (
    AIServiceUnavailableError,
)
from feishu_webhook_bot.ai.retry import CircuitBreaker
from feishu_webhook_bot.ai.tools import (
    SearchCache,
    ToolRegistry,
    clear_search_cache,
    convert_units,
    format_date,
    get_search_cache_stats,
    register_default_tools,
)


class TestSearchCache:
    """Test search result caching functionality."""

    def test_cache_initialization(self) -> None:
        """Test cache initialization with default parameters."""
        cache = SearchCache()
        assert cache._max_size == 100
        assert cache._ttl.total_seconds() == 3600  # 60 minutes
        assert len(cache._cache) == 0

    def test_cache_set_and_get(self) -> None:
        """Test setting and getting cached values."""
        cache = SearchCache()
        cache.set("test query", 5, "test result")

        result = cache.get("test query", 5)
        assert result == "test result"

    def test_cache_miss(self) -> None:
        """Test cache miss returns None."""
        cache = SearchCache()
        result = cache.get("nonexistent query", 5)
        assert result is None

    def test_cache_normalization(self) -> None:
        """Test query normalization for cache keys."""
        cache = SearchCache()
        cache.set("Test Query", 5, "result1")

        # Should hit cache with different case
        result = cache.get("test query", 5)
        assert result == "result1"

    def test_cache_eviction(self) -> None:
        """Test cache eviction when max size is reached."""
        cache = SearchCache(max_size=2)
        cache.set("query1", 5, "result1")
        cache.set("query2", 5, "result2")
        cache.set("query3", 5, "result3")  # Should evict oldest

        assert len(cache._cache) == 2
        assert cache.get("query1", 5) is None  # Evicted
        assert cache.get("query2", 5) == "result2"
        assert cache.get("query3", 5) == "result3"

    def test_cache_stats(self) -> None:
        """Test cache statistics tracking."""
        cache = SearchCache()
        cache.set("query1", 5, "result1")

        # Hit
        cache.get("query1", 5)
        # Miss
        cache.get("query2", 5)

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 50.0

    def test_cache_clear(self) -> None:
        """Test clearing the cache."""
        cache = SearchCache()
        cache.set("query1", 5, "result1")
        cache.set("query2", 5, "result2")

        cache.clear()

        assert len(cache._cache) == 0
        assert cache._hits == 0
        assert cache._misses == 0


class TestTools:
    """Test tool implementations."""

    @pytest.mark.anyio
    async def test_convert_units_length(self) -> None:
        """Test length unit conversion."""
        result = await convert_units(100, "km", "miles")
        assert "100 km" in result
        assert "miles" in result
        assert "62.1" in result  # Approximate conversion

    @pytest.mark.anyio
    async def test_convert_units_weight(self) -> None:
        """Test weight unit conversion."""
        result = await convert_units(1, "kg", "lb")
        assert "1 kg" in result
        assert "2.2" in result  # Approximate conversion

    @pytest.mark.anyio
    async def test_convert_units_temperature(self) -> None:
        """Test temperature conversion."""
        result = await convert_units(0, "celsius", "fahrenheit")
        assert "0°C" in result
        assert "32" in result

    @pytest.mark.anyio
    async def test_convert_units_time(self) -> None:
        """Test time unit conversion."""
        result = await convert_units(60, "minutes", "hours")
        assert "60 minutes" in result
        assert "1.0000 hours" in result

    @pytest.mark.anyio
    async def test_convert_units_invalid(self) -> None:
        """Test invalid unit conversion."""
        result = await convert_units(100, "invalid", "units")
        assert "Error" in result or "Cannot convert" in result

    @pytest.mark.anyio
    async def test_format_date_iso(self) -> None:
        """Test ISO date formatting."""
        result = await format_date("2025-01-08", "iso")
        assert "2025-01-08" in result

    @pytest.mark.anyio
    async def test_get_search_cache_stats(self) -> None:
        """Test getting cache statistics."""
        result = await get_search_cache_stats()
        data = json.loads(result)
        assert "size" in data
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate_percent" in data

    @pytest.mark.anyio
    async def test_clear_search_cache_tool(self) -> None:
        """Test clearing search cache via tool."""
        result = await clear_search_cache()
        assert "cleared" in result.lower() or "success" in result.lower()


class TestToolRegistry:
    """Test tool registry features."""

    def test_registry_with_metadata(self) -> None:
        """Test tool registration with metadata."""
        registry = ToolRegistry()

        async def test_tool(arg: str) -> str:
            return f"Result: {arg}"

        registry.register(
            "test_tool",
            test_tool,
            description="A test tool",
            category="testing",
            requires_permission=True,
        )

        info = registry.get_tool_info("test_tool")
        assert info is not None
        assert info["name"] == "test_tool"
        assert info["description"] == "A test tool"
        assert info["category"] == "testing"
        assert info["requires_permission"] is True

    @pytest.mark.anyio
    async def test_registry_execute_tool(self) -> None:
        """Test tool execution with tracking."""
        registry = ToolRegistry()

        async def test_tool(arg: str) -> str:
            return f"Result: {arg}"

        registry.register("test_tool", test_tool)

        result = await registry.execute_tool("test_tool", "test")
        assert result == "Result: test"

        info = registry.get_tool_info("test_tool")
        assert info["usage_count"] == 1
        assert info["error_count"] == 0

    @pytest.mark.anyio
    async def test_registry_execute_tool_error(self) -> None:
        """Test tool execution error tracking."""
        registry = ToolRegistry()

        async def failing_tool() -> str:
            raise ValueError("Test error")

        registry.register("failing_tool", failing_tool)

        with pytest.raises(ValueError):
            await registry.execute_tool("failing_tool")

        info = registry.get_tool_info("failing_tool")
        assert info["error_count"] == 1

    def test_registry_get_tools_by_category(self) -> None:
        """Test getting tools by category."""
        registry = ToolRegistry()
        register_default_tools(registry)

        search_tools = registry.get_tools_by_category("search")
        assert "web_search" in search_tools

        calc_tools = registry.get_tools_by_category("calculation")
        assert "calculate" in calc_tools
        assert "convert_units" in calc_tools

    def test_registry_stats(self) -> None:
        """Test registry statistics."""
        registry = ToolRegistry()
        register_default_tools(registry)

        stats = registry.get_stats()
        assert stats["total_tools"] >= 8  # At least 8 default tools
        assert "categories" in stats
        assert len(stats["categories"]) >= 4  # At least 4 categories


class TestConversation:
    """Test conversation management features."""

    def test_conversation_token_tracking(self) -> None:
        """Test token usage tracking in conversations."""
        conv = ConversationState("user123")

        from pydantic_ai.messages import ModelRequest

        messages = [ModelRequest(parts=[{"content": "Hello"}])]

        conv.add_messages(messages, input_tokens=10, output_tokens=20)

        assert conv.input_tokens == 10
        assert conv.output_tokens == 20
        assert conv.message_count == 1

    def test_conversation_analytics(self) -> None:
        """Test conversation analytics."""
        conv = ConversationState("user123")

        from pydantic_ai.messages import ModelRequest

        messages = [ModelRequest(parts=[{"content": "Hello"}])]
        conv.add_messages(messages, input_tokens=10, output_tokens=20)

        analytics = conv.get_analytics()
        assert analytics["user_id"] == "user123"
        assert analytics["message_count"] == 1
        assert analytics["input_tokens"] == 10
        assert analytics["output_tokens"] == 20
        assert analytics["total_tokens"] == 30
        assert "duration_seconds" in analytics

    def test_conversation_export(self) -> None:
        """Test conversation export to dict."""
        conv = ConversationState("user123")
        conv.context["key"] = "value"
        conv.summary = "Test summary"

        data = conv.export_to_dict()
        assert data["user_id"] == "user123"
        assert data["context"]["key"] == "value"
        assert data["summary"] == "Test summary"
        assert "created_at" in data
        assert "last_activity" in data

    def test_conversation_import(self) -> None:
        """Test conversation import from dict."""
        data = {
            "user_id": "user456",
            "context": {"key": "value"},
            "summary": "Imported summary",
            "input_tokens": 100,
            "output_tokens": 200,
            "message_count": 5,
            "created_at": datetime.now(UTC).isoformat(),
            "last_activity": datetime.now(UTC).isoformat(),
        }

        conv = ConversationState.import_from_dict(data)
        assert conv.user_id == "user456"
        assert conv.context["key"] == "value"
        assert conv.summary == "Imported summary"
        assert conv.input_tokens == 100
        assert conv.output_tokens == 200
        assert conv.message_count == 5

    @pytest.mark.anyio
    async def test_conversation_manager_export_import(self) -> None:
        """Test conversation manager export/import."""
        manager = ConversationManager()

        # Create a conversation
        conv = await manager.get_conversation("user789")
        conv.context["test"] = "data"

        # Export
        json_data = await manager.export_conversation("user789")
        data = json.loads(json_data)
        assert data["user_id"] == "user789"
        assert data["context"]["test"] == "data"

        # Delete and import
        await manager.delete_conversation("user789")
        user_id = await manager.import_conversation(json_data)
        assert user_id == "user789"

        # Verify imported conversation
        conv2 = await manager.get_conversation("user789")
        assert conv2.context["test"] == "data"


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_initialization(self) -> None:
        """Test circuit breaker initialization."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 30.0
        assert breaker.state == "CLOSED"

    def test_circuit_breaker_success(self) -> None:
        """Test circuit breaker with successful calls."""
        breaker = CircuitBreaker()

        def success_func() -> str:
            return "success"

        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == "CLOSED"

    def test_circuit_breaker_opens_on_failures(self) -> None:
        """Test circuit breaker opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=2)

        def failing_func() -> None:
            raise ValueError("Test error")

        # First failure
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == "CLOSED"

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == "OPEN"

        # Third call should fail immediately
        with pytest.raises(AIServiceUnavailableError):
            breaker.call(failing_func)
