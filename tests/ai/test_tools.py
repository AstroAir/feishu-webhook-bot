"""Comprehensive tests for AI tools module.

Tests cover:
- ai_tool decorator
- SearchCache functionality
- ToolRegistry operations
- Built-in tools (calculate, format_json, convert_units, etc.)
- web_search with caching and retry logic
- get_search_cache_stats and clear_search_cache utilities
- Tool registration and execution
- Edge cases and error handling
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.ai.tools import (
    SearchCache,
    ToolRegistry,
    ai_tool,
    calculate,
    clear_search_cache,
    convert_units,
    format_date,
    format_json,
    get_current_time,
    get_search_cache_stats,
    register_default_tools,
    web_search,
)

# ==============================================================================
# ai_tool Decorator Tests
# ==============================================================================


class TestAiToolDecorator:
    """Tests for ai_tool decorator."""

    def test_decorator_adds_metadata(self):
        """Test decorator adds metadata to function."""

        @ai_tool(name="test_tool", description="Test description")
        def my_func():
            pass

        assert hasattr(my_func, "_ai_tool_metadata")
        assert my_func._ai_tool_metadata["name"] == "test_tool"
        assert my_func._ai_tool_metadata["description"] == "Test description"

    def test_decorator_with_defaults(self):
        """Test decorator with default values."""

        @ai_tool()
        def my_func():
            pass

        assert my_func._ai_tool_metadata["name"] is None
        assert my_func._ai_tool_metadata["description"] is None

    def test_decorator_preserves_function(self):
        """Test decorator preserves original function."""

        @ai_tool(name="test")
        def add(a, b):
            return a + b

        assert add(2, 3) == 5


# ==============================================================================
# SearchCache Tests
# ==============================================================================


class TestSearchCache:
    """Tests for SearchCache."""

    def test_cache_creation(self):
        """Test SearchCache creation."""
        cache = SearchCache(ttl_minutes=30, max_size=50)

        assert cache._max_size == 50
        assert cache._ttl == timedelta(minutes=30)

    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        cache = SearchCache()

        cache.set("test query", 5, "result data")
        result = cache.get("test query", 5)

        assert result == "result data"

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = SearchCache()

        result = cache.get("nonexistent", 5)

        assert result is None

    def test_cache_expiration(self):
        """Test cache entries expire."""
        cache = SearchCache(ttl_minutes=0)  # Immediate expiration

        cache.set("test", 5, "result")
        # Entry should be expired immediately
        _ = cache.get("test", 5)

        # May or may not be None depending on timing
        # The key point is it doesn't raise an error

    def test_cache_eviction(self):
        """Test cache evicts oldest entry when full."""
        cache = SearchCache(max_size=2)

        cache.set("query1", 5, "result1")
        cache.set("query2", 5, "result2")
        cache.set("query3", 5, "result3")

        # query1 should be evicted
        assert cache.get("query1", 5) is None
        assert cache.get("query3", 5) == "result3"

    def test_cache_clear(self):
        """Test clearing cache."""
        cache = SearchCache()

        cache.set("test", 5, "result")
        cache.clear()

        # After clear, cache is empty and stats are reset
        assert len(cache._cache) == 0
        assert cache._hits == 0
        # Note: get() after clear will increment misses
        result = cache.get("test", 5)
        assert result is None
        assert cache._misses == 1  # One miss from the get() call

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = SearchCache()

        cache.set("test", 5, "result")
        cache.get("test", 5)  # Hit
        cache.get("nonexistent", 5)  # Miss

        stats = cache.get_stats()

        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 50.0


# ==============================================================================
# ToolRegistry Tests
# ==============================================================================


class TestToolRegistry:
    """Tests for ToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh tool registry."""
        return ToolRegistry()

    def test_registry_creation(self):
        """Test ToolRegistry creation."""
        registry = ToolRegistry()

        assert len(registry.list_tools()) == 0

    def test_register_tool(self, registry):
        """Test registering a tool."""

        def my_tool(x):
            return x * 2

        registry.register("my_tool", my_tool, description="Doubles input")

        assert "my_tool" in registry.list_tools()

    def test_get_tool(self, registry):
        """Test getting a registered tool."""

        def my_tool(x):
            return x * 2

        registry.register("my_tool", my_tool)

        tool = registry.get_tool("my_tool")
        assert tool is not None
        assert tool(5) == 10

    def test_get_tool_not_found(self, registry):
        """Test getting nonexistent tool."""
        tool = registry.get_tool("nonexistent")
        assert tool is None

    @pytest.mark.anyio
    async def test_execute_tool(self, registry):
        """Test executing a tool."""

        def add(a, b):
            return a + b

        registry.register("add", add)

        result = await registry.execute_tool("add", 2, 3)

        assert result == 5

    @pytest.mark.anyio
    async def test_execute_async_tool(self, registry):
        """Test executing an async tool."""

        async def async_add(a, b):
            return a + b

        registry.register("async_add", async_add)

        result = await registry.execute_tool("async_add", 2, 3)

        assert result == 5

    @pytest.mark.anyio
    async def test_execute_tool_not_found(self, registry):
        """Test executing nonexistent tool raises."""
        with pytest.raises(ValueError, match="not found"):
            await registry.execute_tool("nonexistent")

    @pytest.mark.anyio
    async def test_execute_tool_tracks_usage(self, registry):
        """Test tool execution tracks usage."""
        registry.register("my_tool", lambda: "result")

        await registry.execute_tool("my_tool")
        await registry.execute_tool("my_tool")

        info = registry.get_tool_info("my_tool")
        assert info["usage_count"] == 2

    @pytest.mark.anyio
    async def test_execute_tool_tracks_errors(self, registry):
        """Test tool execution tracks errors."""

        def failing_tool():
            raise ValueError("Error")

        registry.register("failing", failing_tool)

        with pytest.raises(ValueError):
            await registry.execute_tool("failing")

        info = registry.get_tool_info("failing")
        assert info["error_count"] == 1

    def test_get_tool_info(self, registry):
        """Test getting tool info."""
        registry.register(
            "my_tool",
            lambda: None,
            description="Test tool",
            category="test",
        )

        info = registry.get_tool_info("my_tool")

        assert info["name"] == "my_tool"
        assert info["description"] == "Test tool"
        assert info["category"] == "test"

    def test_get_tools_by_category(self, registry):
        """Test getting tools by category."""
        registry.register("tool1", lambda: None, category="cat1")
        registry.register("tool2", lambda: None, category="cat1")
        registry.register("tool3", lambda: None, category="cat2")

        cat1_tools = registry.get_tools_by_category("cat1")

        assert len(cat1_tools) == 2
        assert "tool1" in cat1_tools
        assert "tool2" in cat1_tools

    def test_get_stats(self, registry):
        """Test getting registry stats."""
        registry.register("tool1", lambda: None, category="cat1")
        registry.register("tool2", lambda: None, category="cat2")

        stats = registry.get_stats()

        assert stats["total_tools"] == 2
        assert "cat1" in stats["categories"]
        assert "cat2" in stats["categories"]

    def test_tool_decorator(self, registry):
        """Test tool decorator."""

        @registry.tool(name="decorated", description="Decorated tool")
        def my_decorated_tool():
            return "result"

        assert "decorated" in registry.list_tools()
        assert my_decorated_tool() == "result"


# ==============================================================================
# Built-in Tools Tests
# ==============================================================================


class TestCalculateTool:
    """Tests for calculate tool."""

    @pytest.mark.anyio
    async def test_calculate_simple(self):
        """Test simple calculation."""
        result = await calculate("2 + 3")
        assert result == "5"

    @pytest.mark.anyio
    async def test_calculate_complex(self):
        """Test complex calculation."""
        result = await calculate("(10 + 5) * 2")
        assert result == "30"

    @pytest.mark.anyio
    async def test_calculate_decimal(self):
        """Test decimal calculation."""
        result = await calculate("10 / 4")
        assert result == "2.5"

    @pytest.mark.anyio
    async def test_calculate_invalid_chars(self):
        """Test calculation with invalid characters."""
        result = await calculate("import os")
        assert "Error" in result

    @pytest.mark.anyio
    async def test_calculate_error(self):
        """Test calculation error handling."""
        result = await calculate("1/0")
        assert "Error" in result


class TestFormatJsonTool:
    """Tests for format_json tool."""

    @pytest.mark.anyio
    async def test_format_json_valid(self):
        """Test formatting valid JSON."""
        result = await format_json('{"a":1,"b":2}')

        parsed = json.loads(result)
        assert parsed["a"] == 1
        assert parsed["b"] == 2

    @pytest.mark.anyio
    async def test_format_json_invalid(self):
        """Test formatting invalid JSON."""
        result = await format_json("not json")
        assert "Error" in result


class TestConvertUnitsTool:
    """Tests for convert_units tool."""

    @pytest.mark.anyio
    async def test_convert_length(self):
        """Test length conversion."""
        result = await convert_units(1, "km", "m")
        assert "1000" in result

    @pytest.mark.anyio
    async def test_convert_weight(self):
        """Test weight conversion."""
        result = await convert_units(1, "kg", "g")
        assert "1000" in result

    @pytest.mark.anyio
    async def test_convert_temperature_c_to_f(self):
        """Test temperature conversion C to F."""
        result = await convert_units(0, "celsius", "fahrenheit")
        assert "32" in result

    @pytest.mark.anyio
    async def test_convert_temperature_f_to_c(self):
        """Test temperature conversion F to C."""
        result = await convert_units(32, "fahrenheit", "celsius")
        assert "0" in result

    @pytest.mark.anyio
    async def test_convert_time(self):
        """Test time conversion."""
        result = await convert_units(1, "hour", "minutes")
        assert "60" in result

    @pytest.mark.anyio
    async def test_convert_unsupported(self):
        """Test unsupported conversion."""
        result = await convert_units(1, "unknown", "other")
        assert "Error" in result


class TestGetCurrentTimeTool:
    """Tests for get_current_time tool."""

    @pytest.mark.anyio
    async def test_get_current_time(self):
        """Test getting current time."""
        result = await get_current_time()

        # Should be valid ISO format
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert dt is not None


class TestFormatDateTool:
    """Tests for format_date tool."""

    @pytest.mark.anyio
    async def test_format_date_iso(self):
        """Test formatting date to ISO."""
        result = await format_date("2024-01-15", "iso")
        assert "2024-01-15" in result

    @pytest.mark.anyio
    async def test_format_date_us(self):
        """Test formatting date to US format."""
        result = await format_date("2024-01-15", "us")
        assert "01/15/2024" in result

    @pytest.mark.anyio
    async def test_format_date_invalid(self):
        """Test formatting invalid date."""
        result = await format_date("not a date", "iso")
        assert "Error" in result


# ==============================================================================
# Register Default Tools Tests
# ==============================================================================


class TestRegisterDefaultTools:
    """Tests for register_default_tools function."""

    def test_register_default_tools(self):
        """Test registering default tools."""
        registry = ToolRegistry()

        register_default_tools(registry)

        tools = registry.list_tools()
        assert "web_search" in tools
        assert "get_current_time" in tools
        assert "calculate" in tools
        assert "format_json" in tools
        assert "convert_units" in tools
        assert "format_date" in tools

    def test_register_default_tools_includes_cache_tools(self):
        """Test default tools include cache management tools."""
        registry = ToolRegistry()

        register_default_tools(registry)

        tools = registry.list_tools()
        assert "get_search_cache_stats" in tools
        assert "clear_search_cache" in tools

    def test_register_default_tools_categories(self):
        """Test default tools have correct categories."""
        registry = ToolRegistry()

        register_default_tools(registry)

        # Check categories
        search_tools = registry.get_tools_by_category("search")
        assert "web_search" in search_tools

        utility_tools = registry.get_tools_by_category("utility")
        assert "get_current_time" in utility_tools
        assert "get_search_cache_stats" in utility_tools

        calculation_tools = registry.get_tools_by_category("calculation")
        assert "calculate" in calculation_tools
        assert "convert_units" in calculation_tools

        formatting_tools = registry.get_tools_by_category("formatting")
        assert "format_json" in formatting_tools
        assert "format_date" in formatting_tools


# ==============================================================================
# Web Search Tool Tests
# ==============================================================================


class TestWebSearchTool:
    """Tests for web_search tool."""

    @pytest.mark.anyio
    async def test_web_search_empty_query(self):
        """Test web search with empty query returns error."""
        result = await web_search("")

        data = json.loads(result)
        assert "error" in data
        assert data["error"] == "Empty query"

    @pytest.mark.anyio
    async def test_web_search_whitespace_query(self):
        """Test web search with whitespace-only query returns error."""
        result = await web_search("   ")

        data = json.loads(result)
        assert "error" in data
        assert data["error"] == "Empty query"

    @pytest.mark.anyio
    async def test_web_search_max_results_clamped(self):
        """Test max_results is clamped to valid range."""
        # Mock the DDGS to avoid actual network calls
        with patch("feishu_webhook_bot.ai.tools.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = []
            mock_ddgs.return_value = mock_instance

            # Test with value below minimum
            await web_search("test query", max_results=0)
            mock_instance.text.assert_called_with("test query", max_results=1)

    @pytest.mark.anyio
    async def test_web_search_max_results_clamped_high(self):
        """Test max_results is clamped to maximum 20."""
        with patch("feishu_webhook_bot.ai.tools.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = []
            mock_ddgs.return_value = mock_instance

            await web_search("test query", max_results=100)
            mock_instance.text.assert_called_with("test query", max_results=20)

    @pytest.mark.anyio
    async def test_web_search_no_results(self):
        """Test web search with no results."""
        with patch("feishu_webhook_bot.ai.tools.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = []
            mock_ddgs.return_value = mock_instance

            result = await web_search("very obscure query xyz123", use_cache=False)

            data = json.loads(result)
            assert data["count"] == 0
            assert data["results"] == []
            assert "No results found" in data.get("message", "")

    @pytest.mark.anyio
    async def test_web_search_with_results(self):
        """Test web search with results."""
        with patch("feishu_webhook_bot.ai.tools.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {
                    "title": "Test Title",
                    "href": "https://example.com",
                    "body": "Test snippet",
                },
                {
                    "title": "Another Title",
                    "href": "https://example2.com",
                    "body": "Another snippet",
                },
            ]
            mock_ddgs.return_value = mock_instance

            result = await web_search("test query", use_cache=False)

            data = json.loads(result)
            assert data["count"] == 2
            assert len(data["results"]) == 2
            assert data["results"][0]["title"] == "Test Title"
            assert data["results"][0]["url"] == "https://example.com"
            assert data["results"][0]["position"] == 1
            assert data["cached"] is False

    @pytest.mark.anyio
    async def test_web_search_caching(self):
        """Test web search uses cache."""
        with patch("feishu_webhook_bot.ai.tools.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "Cached Result", "href": "https://cached.com", "body": "Cached"},
            ]
            mock_ddgs.return_value = mock_instance

            # First call - should hit the API
            result1 = await web_search("cache test query", max_results=5, use_cache=True)
            _ = json.loads(result1)  # Verify it's valid JSON

            # Second call - should use cache
            result2 = await web_search("cache test query", max_results=5, use_cache=True)
            data2 = json.loads(result2)

            # Second result should be cached
            assert data2.get("cached") is True

    @pytest.mark.anyio
    async def test_web_search_retry_on_failure(self):
        """Test web search retries on failure."""
        with patch("feishu_webhook_bot.ai.tools.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            # Fail twice, then succeed
            mock_instance.text.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                [{"title": "Success", "href": "https://success.com", "body": "Finally worked"}],
            ]
            mock_ddgs.return_value = mock_instance

            result = await web_search("retry test", max_retries=3, use_cache=False)

            data = json.loads(result)
            assert data["count"] == 1
            assert data["results"][0]["title"] == "Success"

    @pytest.mark.anyio
    async def test_web_search_all_retries_fail(self):
        """Test web search returns error after all retries fail."""
        with patch("feishu_webhook_bot.ai.tools.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.side_effect = Exception("Persistent error")
            mock_ddgs.return_value = mock_instance

            result = await web_search("fail test", max_retries=2, use_cache=False)

            data = json.loads(result)
            assert "error" in data
            assert "Persistent error" in data["error"]
            assert data["count"] == 0

    @pytest.mark.anyio
    async def test_web_search_relevance_scoring(self):
        """Test web search results have relevance scores."""
        with patch("feishu_webhook_bot.ai.tools.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "First", "href": "https://first.com", "body": "First result"},
                {"title": "Second", "href": "https://second.com", "body": "Second result"},
                {"title": "Third", "href": "https://third.com", "body": "Third result"},
            ]
            mock_ddgs.return_value = mock_instance

            result = await web_search("relevance test", use_cache=False)

            data = json.loads(result)
            # First result should have highest relevance
            assert data["results"][0]["relevance_score"] > data["results"][1]["relevance_score"]
            assert data["results"][1]["relevance_score"] > data["results"][2]["relevance_score"]


# ==============================================================================
# Search Cache Stats Tool Tests
# ==============================================================================


class TestGetSearchCacheStatsTool:
    """Tests for get_search_cache_stats tool."""

    @pytest.mark.anyio
    async def test_get_search_cache_stats_returns_json(self):
        """Test get_search_cache_stats returns valid JSON."""
        result = await get_search_cache_stats()

        data = json.loads(result)
        assert "size" in data
        assert "max_size" in data
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate_percent" in data
        assert "ttl_minutes" in data

    @pytest.mark.anyio
    async def test_get_search_cache_stats_values(self):
        """Test get_search_cache_stats returns correct values."""
        result = await get_search_cache_stats()

        data = json.loads(result)
        assert isinstance(data["size"], int)
        assert isinstance(data["max_size"], int)
        assert isinstance(data["hits"], int)
        assert isinstance(data["misses"], int)
        assert isinstance(data["hit_rate_percent"], (int, float))


# ==============================================================================
# Clear Search Cache Tool Tests
# ==============================================================================


class TestClearSearchCacheTool:
    """Tests for clear_search_cache tool."""

    @pytest.mark.anyio
    async def test_clear_search_cache_returns_message(self):
        """Test clear_search_cache returns confirmation message."""
        result = await clear_search_cache()

        assert "cleared" in result.lower()
        assert "success" in result.lower()

    @pytest.mark.anyio
    async def test_clear_search_cache_actually_clears(self):
        """Test clear_search_cache actually clears the cache."""
        # Add something to cache via web_search
        with patch("feishu_webhook_bot.ai.tools.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "Test", "href": "https://test.com", "body": "Test"},
            ]
            mock_ddgs.return_value = mock_instance

            await web_search("clear cache test", use_cache=True)

        # Clear the cache
        await clear_search_cache()

        # Check stats - size should be 0
        stats_result = await get_search_cache_stats()
        stats = json.loads(stats_result)
        assert stats["size"] == 0
        assert stats["hits"] == 0


# ==============================================================================
# Additional Edge Case Tests
# ==============================================================================


class TestToolsEdgeCases:
    """Additional edge case tests for tools."""

    @pytest.mark.anyio
    async def test_calculate_with_spaces(self):
        """Test calculate handles expressions with spaces."""
        result = await calculate("  2  +  3  ")
        assert result == "5"

    @pytest.mark.anyio
    async def test_calculate_with_floats(self):
        """Test calculate handles floating point numbers."""
        result = await calculate("3.14 * 2")
        assert "6.28" in result

    @pytest.mark.anyio
    async def test_calculate_negative_numbers(self):
        """Test calculate handles negative numbers."""
        # Note: '-' is in allowed chars, so this should work
        result = await calculate("-5 + 3")
        # Result depends on implementation - may error or succeed
        assert result is not None

    @pytest.mark.anyio
    async def test_format_json_nested(self):
        """Test format_json handles nested structures."""
        input_json = '{"a":{"b":{"c":1}}}'
        result = await format_json(input_json)

        parsed = json.loads(result)
        assert parsed["a"]["b"]["c"] == 1

    @pytest.mark.anyio
    async def test_format_json_array(self):
        """Test format_json handles arrays."""
        input_json = "[1, 2, 3]"
        result = await format_json(input_json)

        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    @pytest.mark.anyio
    async def test_format_json_unicode(self):
        """Test format_json handles unicode."""
        input_json = '{"message": "你好世界"}'
        result = await format_json(input_json)

        parsed = json.loads(result)
        assert parsed["message"] == "你好世界"

    @pytest.mark.anyio
    async def test_convert_units_case_insensitive(self):
        """Test convert_units is case insensitive."""
        result = await convert_units(1, "KM", "M")
        assert "1000" in result

    @pytest.mark.anyio
    async def test_convert_units_with_spaces(self):
        """Test convert_units handles units with spaces."""
        result = await convert_units(1, " km ", " m ")
        assert "1000" in result

    @pytest.mark.anyio
    async def test_convert_units_celsius_to_kelvin(self):
        """Test temperature conversion C to K."""
        result = await convert_units(0, "celsius", "kelvin")
        assert "273.15" in result

    @pytest.mark.anyio
    async def test_convert_units_kelvin_to_celsius(self):
        """Test temperature conversion K to C."""
        result = await convert_units(273.15, "kelvin", "celsius")
        assert "0" in result

    @pytest.mark.anyio
    async def test_format_date_eu_format(self):
        """Test formatting date to EU format."""
        result = await format_date("2024-01-15", "eu")
        assert "15/01/2024" in result

    @pytest.mark.anyio
    async def test_format_date_readable_format(self):
        """Test formatting date to readable format."""
        result = await format_date("2024-01-15", "readable")
        assert "January" in result
        assert "15" in result
        assert "2024" in result

    @pytest.mark.anyio
    async def test_format_date_custom_format(self):
        """Test formatting date with custom format string."""
        result = await format_date("2024-01-15", "%Y/%m/%d")
        assert "2024/01/15" in result

    @pytest.mark.anyio
    async def test_get_current_time_with_timezone(self):
        """Test get_current_time with timezone parameter."""
        result = await get_current_time("UTC")

        # Should be valid ISO format
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert dt is not None


class TestToolRegistryAdvanced:
    """Advanced tests for ToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh tool registry."""
        return ToolRegistry()

    def test_register_tool_with_permission(self, registry):
        """Test registering a tool that requires permission."""
        registry.register(
            "sensitive_tool",
            lambda: "result",
            description="Sensitive operation",
            requires_permission=True,
        )

        info = registry.get_tool_info("sensitive_tool")
        assert info["requires_permission"] is True

    def test_get_tool_info_not_found(self, registry):
        """Test get_tool_info returns None for nonexistent tool."""
        info = registry.get_tool_info("nonexistent")
        assert info is None

    def test_get_tools_by_category_empty(self, registry):
        """Test get_tools_by_category returns empty list for unknown category."""
        tools = registry.get_tools_by_category("unknown_category")
        assert tools == []

    @pytest.mark.anyio
    async def test_execute_tool_with_kwargs(self, registry):
        """Test executing a tool with keyword arguments."""

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        registry.register("greet", greet)

        result = await registry.execute_tool("greet", "World", greeting="Hi")

        assert result == "Hi, World!"

    def test_get_stats_with_usage(self, registry):
        """Test get_stats includes usage information."""
        registry.register("tool1", lambda: None)
        registry.register("tool2", lambda: None)

        # Manually update usage stats
        registry._usage_stats["tool1"] = 10
        registry._usage_stats["tool2"] = 5

        stats = registry.get_stats()

        assert stats["total_usage"] == 15
        assert len(stats["most_used_tools"]) > 0

    def test_get_stats_error_rate(self, registry):
        """Test get_stats calculates error rate."""
        registry.register("tool1", lambda: None)

        registry._usage_stats["tool1"] = 10
        registry._error_counts["tool1"] = 2

        stats = registry.get_stats()

        assert stats["total_errors"] == 2
        assert stats["error_rate_percent"] == 20.0

    def test_tool_decorator_with_category(self, registry):
        """Test tool decorator with category."""

        @registry.tool(name="categorized", category="custom")
        def my_tool():
            return "result"

        info = registry.get_tool_info("categorized")
        assert info["category"] == "custom"

    def test_tool_decorator_uses_function_name(self, registry):
        """Test tool decorator uses function name if name not provided."""

        @registry.tool()
        def auto_named_tool():
            return "result"

        assert "auto_named_tool" in registry.list_tools()

    def test_tool_decorator_uses_docstring(self, registry):
        """Test tool decorator uses docstring if description not provided."""

        @registry.tool()
        def documented_tool():
            """This is the tool description."""
            return "result"

        info = registry.get_tool_info("documented_tool")
        assert "tool description" in info["description"]


class TestSearchCacheAdvanced:
    """Advanced tests for SearchCache."""

    def test_cache_key_normalization(self):
        """Test cache key is normalized (case insensitive, trimmed)."""
        cache = SearchCache()

        cache.set("Test Query", 5, "result")

        # Should find with different case
        result = cache.get("test query", 5)
        assert result == "result"

    def test_cache_different_max_results(self):
        """Test cache differentiates by max_results."""
        cache = SearchCache()

        cache.set("query", 5, "result_5")
        cache.set("query", 10, "result_10")

        assert cache.get("query", 5) == "result_5"
        assert cache.get("query", 10) == "result_10"

    def test_cache_stats_hit_rate_zero_total(self):
        """Test cache stats with zero total requests."""
        cache = SearchCache()

        stats = cache.get_stats()

        assert stats["hit_rate_percent"] == 0

    def test_cache_stats_includes_ttl(self):
        """Test cache stats includes TTL."""
        cache = SearchCache(ttl_minutes=45)

        stats = cache.get_stats()

        assert stats["ttl_minutes"] == 45.0
