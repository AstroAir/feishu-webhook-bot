"""Tool registry and built-in tools for AI agent."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from duckduckgo_search import DDGS

from ..core.logger import get_logger

logger = get_logger("ai.tools")


def ai_tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to mark a function as an AI tool for bulk registration.

    This decorator marks a function so it can be easily discovered and registered
    with an AIAgent using the register_tools_from_module method.

    Args:
        name: Optional tool name (defaults to function name)
        description: Optional tool description (defaults to function docstring)

    Returns:
        Decorator function

    Example:
        @ai_tool(name="calculator", description="Perform calculations")
        def calculate_expression(expression: str) -> str:
            return str(eval(expression))
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func._ai_tool_metadata = {
            "name": name,
            "description": description,
        }
        return func

    return decorator


# Search result cache
class SearchCache:
    """Simple in-memory cache for search results."""

    def __init__(self, ttl_minutes: int = 60, max_size: int = 100) -> None:
        """Initialize search cache.

        Args:
            ttl_minutes: Time-to-live for cached results in minutes
            max_size: Maximum number of cached entries
        """
        self._cache: dict[str, tuple[str, datetime]] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, max_results: int) -> str:
        """Create cache key from query and max_results."""
        key_str = f"{query.lower().strip()}:{max_results}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, query: str, max_results: int) -> str | None:
        """Get cached result if available and not expired."""
        key = self._make_key(query, max_results)
        if key in self._cache:
            result, timestamp = self._cache[key]
            if datetime.now(UTC) - timestamp < self._ttl:
                self._hits += 1
                logger.debug("Cache hit for query: %s", query[:50])
                return result
            else:
                # Expired, remove it
                del self._cache[key]
        self._misses += 1
        return None

    def set(self, query: str, max_results: int, result: str) -> None:
        """Cache a search result."""
        # Evict oldest entry if cache is full
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
            logger.debug("Evicted oldest cache entry")

        key = self._make_key(query, max_results)
        self._cache[key] = (result, datetime.now(UTC))
        logger.debug("Cached result for query: %s", query[:50])

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Search cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "ttl_minutes": self._ttl.total_seconds() / 60,
        }


# Global search cache instance
_search_cache = SearchCache(ttl_minutes=60, max_size=100)


class ToolRegistry:
    """Registry for AI agent tools with analytics and access control.

    This class manages the registration and execution of tools that
    the AI agent can call to perform various tasks. It includes:
    - Tool registration and retrieval
    - Usage analytics and logging
    - Tool metadata and documentation
    - Access control (future enhancement)
    """

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: dict[str, Callable[..., Any]] = {}
        self._tool_metadata: dict[str, dict[str, Any]] = {}
        self._usage_stats: dict[str, int] = {}
        self._error_counts: dict[str, int] = {}
        logger.info("ToolRegistry initialized")

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        description: str | None = None,
        category: str = "general",
        requires_permission: bool = False,
    ) -> None:
        """Register a tool function with metadata.

        Args:
            name: Name of the tool
            func: Tool function to register
            description: Human-readable description of the tool
            category: Tool category (e.g., 'search', 'calculation', 'formatting')
            requires_permission: Whether this tool requires special permission
        """
        self._tools[name] = func
        self._tool_metadata[name] = {
            "description": description or func.__doc__ or "No description available",
            "category": category,
            "requires_permission": requires_permission,
            "registered_at": datetime.now(UTC).isoformat(),
        }
        self._usage_stats[name] = 0
        self._error_counts[name] = 0
        logger.debug("Registered tool: %s (category: %s)", name, category)

    def get_tool(self, name: str) -> Callable[..., Any] | None:
        """Get a registered tool by name.

        Args:
            name: Name of the tool

        Returns:
            Tool function or None if not found
        """
        return self._tools.get(name)

    async def execute_tool(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a tool and track usage statistics.

        Args:
            name: Name of the tool to execute
            *args: Positional arguments for the tool
            **kwargs: Keyword arguments for the tool

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool is not found
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry")

        try:
            # Track usage
            self._usage_stats[name] = self._usage_stats.get(name, 0) + 1
            logger.debug("Executing tool: %s (usage count: %d)", name, self._usage_stats[name])

            # Execute tool
            if asyncio.iscoroutinefunction(tool):
                result = await tool(*args, **kwargs)
            else:
                result = tool(*args, **kwargs)

            return result

        except Exception as exc:
            # Track errors
            self._error_counts[name] = self._error_counts.get(name, 0) + 1
            logger.error("Tool execution failed: %s - %s", name, exc, exc_info=True)
            raise

    def list_tools(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_tool_info(self, name: str) -> dict[str, Any] | None:
        """Get detailed information about a tool.

        Args:
            name: Name of the tool

        Returns:
            Tool metadata including description, category, usage stats
        """
        if name not in self._tools:
            return None

        metadata = self._tool_metadata.get(name, {})
        return {
            "name": name,
            "description": metadata.get("description", "No description"),
            "category": metadata.get("category", "general"),
            "requires_permission": metadata.get("requires_permission", False),
            "registered_at": metadata.get("registered_at"),
            "usage_count": self._usage_stats.get(name, 0),
            "error_count": self._error_counts.get(name, 0),
        }

    def get_tools_by_category(self, category: str) -> list[str]:
        """Get all tools in a specific category.

        Args:
            category: Category name

        Returns:
            List of tool names in the category
        """
        return [
            name
            for name, metadata in self._tool_metadata.items()
            if metadata.get("category") == category
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get overall tool registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        total_usage = sum(self._usage_stats.values())
        total_errors = sum(self._error_counts.values())
        error_rate = (total_errors / total_usage * 100) if total_usage > 0 else 0

        # Get most used tools
        most_used = sorted(self._usage_stats.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_tools": len(self._tools),
            "total_usage": total_usage,
            "total_errors": total_errors,
            "error_rate_percent": round(error_rate, 2),
            "most_used_tools": [{"name": name, "count": count} for name, count in most_used],
            "categories": list(
                set(m.get("category", "general") for m in self._tool_metadata.values())
            ),
        }

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
        category: str = "custom",
        requires_permission: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator for registering custom tools with the registry.

        This decorator allows easy registration of tool functions by using it as
        a function decorator. The decorated function is automatically registered
        with this registry.

        Args:
            name: Tool name (defaults to function name)
            description: Tool description (defaults to function docstring)
            category: Tool category (defaults to "custom")
            requires_permission: Whether this tool requires special permission

        Returns:
            Decorator function

        Example:
            @registry.tool(name="my_tool", description="Does something useful")
            async def my_tool(query: str) -> str:
                return f"Result for {query}"
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or func.__name__
            tool_desc = description or func.__doc__ or "No description"
            self.register(tool_name, func, tool_desc, category, requires_permission)
            return func

        return decorator


# Built-in tools


async def web_search(
    query: str,
    max_results: int = 5,
    use_cache: bool = True,
    max_retries: int = 3,
) -> str:
    """Search the web for information with caching and retry logic.

    This function searches the web using DuckDuckGo with the following features:
    - Result caching to avoid redundant searches
    - Automatic retry with exponential backoff on failures
    - Robust error handling and logging
    - Improved result formatting for AI comprehension

    Args:
        query: Search query
        max_results: Maximum number of results to return (1-20)
        use_cache: Whether to use cached results if available
        max_retries: Maximum number of retry attempts on failure

    Returns:
        JSON string with search results, including:
        - results: List of search results with title, url, snippet
        - query: Original search query
        - count: Number of results returned
        - cached: Whether results were from cache
        - timestamp: When the search was performed
    """
    logger.info(
        "Performing web search: %s (max_results=%d, use_cache=%s)", query, max_results, use_cache
    )

    # Validate and sanitize query
    if not query or not query.strip():
        return json.dumps(
            {"error": "Empty query", "query": query, "message": "Search query cannot be empty"}
        )

    query = query.strip()
    max_results = max(1, min(max_results, 20))  # Clamp to 1-20

    # Check cache first
    if use_cache:
        cached_result = _search_cache.get(query, max_results)
        if cached_result:
            logger.info("Returning cached results for query: %s", query[:50])
            # Parse and add cached flag
            try:
                result_data = json.loads(cached_result)
                result_data["cached"] = True
                return json.dumps(result_data, indent=2)
            except json.JSONDecodeError:
                logger.warning("Failed to parse cached result, will fetch fresh")

    # Perform search with retry logic
    last_error = None
    for attempt in range(max_retries):
        try:
            # Run the blocking search in a thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, lambda: DDGS().text(query, max_results=max_results)
            )

            if not results:
                logger.warning("No search results found for query: %s", query)
                result = json.dumps(
                    {
                        "results": [],
                        "query": query,
                        "count": 0,
                        "cached": False,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "message": "No results found",
                    }
                )
                # Cache empty results too to avoid repeated searches
                if use_cache:
                    _search_cache.set(query, max_results, result)
                return result

            # Format results with detailed information
            formatted_results = []
            for idx, search_result in enumerate(results, 1):
                title = search_result.get("title", "").strip()
                url = search_result.get("href", "").strip()
                snippet = search_result.get("body", "").strip()

                # Clean up snippet - remove extra whitespace
                snippet = re.sub(r"\s+", " ", snippet)

                formatted_results.append(
                    {
                        "position": idx,
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "relevance_score": 1.0 - (idx - 1) * 0.1,  # Simple relevance scoring
                    }
                )

            logger.info("Found %d search results for query: %s", len(formatted_results), query)

            result = json.dumps(
                {
                    "results": formatted_results,
                    "query": query,
                    "count": len(formatted_results),
                    "cached": False,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                indent=2,
            )

            # Cache successful results
            if use_cache:
                _search_cache.set(query, max_results, result)

            return result

        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2**attempt
                logger.warning(
                    "Web search attempt %d/%d failed: %s. Retrying in %ds...",
                    attempt + 1,
                    max_retries,
                    exc,
                    wait_time,
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    "Web search failed after %d attempts: %s", max_retries, exc, exc_info=True
                )

    # All retries failed
    return json.dumps(
        {
            "error": str(last_error),
            "query": query,
            "count": 0,
            "cached": False,
            "timestamp": datetime.now(UTC).isoformat(),
            "message": f"Search failed after {max_retries} attempts: {str(last_error)}",
        }
    )


async def get_current_time(timezone_name: str = "UTC") -> str:
    """Get the current time.

    Args:
        timezone_name: Timezone name (currently only UTC is supported)

    Returns:
        Current time as ISO format string
    """
    logger.debug("Getting current time for timezone: %s", timezone_name)
    current_time = datetime.now(UTC)
    return current_time.isoformat()


async def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression.

    Args:
        expression: Mathematical expression to evaluate

    Returns:
        Result of the calculation as a string
    """
    logger.debug("Calculating expression: %s", expression)

    try:
        # Only allow safe mathematical operations
        allowed_chars = set("0123456789+-*/()., ")
        if not all(c in allowed_chars for c in expression):
            return (
                "Error: Expression contains invalid characters. "
                "Only numbers and basic operators (+, -, *, /, parentheses) are allowed."
            )

        # Evaluate the expression
        result = eval(expression, {"__builtins__": {}}, {})
        logger.info("Calculation result: %s = %s", expression, result)
        return str(result)

    except Exception as exc:
        logger.error("Calculation failed: %s", exc, exc_info=True)
        return f"Error: {str(exc)}"


async def format_json(data: str) -> str:
    """Format a JSON string for better readability.

    Args:
        data: JSON string to format

    Returns:
        Formatted JSON string
    """
    logger.debug("Formatting JSON data")

    try:
        parsed = json.loads(data)
        formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
        return formatted
    except json.JSONDecodeError as exc:
        logger.error("JSON formatting failed: %s", exc, exc_info=True)
        return f"Error: Invalid JSON - {str(exc)}"


async def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between common units.

    Supports length, weight, temperature, and time conversions.

    Args:
        value: Value to convert
        from_unit: Source unit (e.g., 'km', 'lb', 'celsius', 'hours')
        to_unit: Target unit (e.g., 'miles', 'kg', 'fahrenheit', 'minutes')

    Returns:
        Conversion result as a string
    """
    logger.debug("Converting %f %s to %s", value, from_unit, to_unit)

    # Normalize unit names
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()

    # Length conversions (to meters as base)
    length_to_meters = {
        "m": 1,
        "meter": 1,
        "meters": 1,
        "km": 1000,
        "kilometer": 1000,
        "kilometers": 1000,
        "cm": 0.01,
        "centimeter": 0.01,
        "centimeters": 0.01,
        "mm": 0.001,
        "millimeter": 0.001,
        "millimeters": 0.001,
        "mi": 1609.34,
        "mile": 1609.34,
        "miles": 1609.34,
        "yd": 0.9144,
        "yard": 0.9144,
        "yards": 0.9144,
        "ft": 0.3048,
        "foot": 0.3048,
        "feet": 0.3048,
        "in": 0.0254,
        "inch": 0.0254,
        "inches": 0.0254,
    }

    # Weight conversions (to kg as base)
    weight_to_kg = {
        "kg": 1,
        "kilogram": 1,
        "kilograms": 1,
        "g": 0.001,
        "gram": 0.001,
        "grams": 0.001,
        "mg": 0.000001,
        "milligram": 0.000001,
        "milligrams": 0.000001,
        "lb": 0.453592,
        "pound": 0.453592,
        "pounds": 0.453592,
        "oz": 0.0283495,
        "ounce": 0.0283495,
        "ounces": 0.0283495,
        "ton": 1000,
        "tonne": 1000,
        "tonnes": 1000,
    }

    # Time conversions (to seconds as base)
    time_to_seconds = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "seconds": 1,
        "min": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hr": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
        "w": 604800,
        "week": 604800,
        "weeks": 604800,
    }

    try:
        # Try length conversion
        if from_unit in length_to_meters and to_unit in length_to_meters:
            meters = value * length_to_meters[from_unit]
            result = meters / length_to_meters[to_unit]
            return f"{value} {from_unit} = {result:.4f} {to_unit}"

        # Try weight conversion
        if from_unit in weight_to_kg and to_unit in weight_to_kg:
            kg = value * weight_to_kg[from_unit]
            result = kg / weight_to_kg[to_unit]
            return f"{value} {from_unit} = {result:.4f} {to_unit}"

        # Try time conversion
        if from_unit in time_to_seconds and to_unit in time_to_seconds:
            seconds = value * time_to_seconds[from_unit]
            result = seconds / time_to_seconds[to_unit]
            return f"{value} {from_unit} = {result:.4f} {to_unit}"

        # Temperature conversions (special case)
        if from_unit in ["c", "celsius"] and to_unit in ["f", "fahrenheit"]:
            result = (value * 9 / 5) + 32
            return f"{value}°C = {result:.2f}°F"
        if from_unit in ["f", "fahrenheit"] and to_unit in ["c", "celsius"]:
            result = (value - 32) * 5 / 9
            return f"{value}°F = {result:.2f}°C"
        if from_unit in ["c", "celsius"] and to_unit in ["k", "kelvin"]:
            result = value + 273.15
            return f"{value}°C = {result:.2f}K"
        if from_unit in ["k", "kelvin"] and to_unit in ["c", "celsius"]:
            result = value - 273.15
            return f"{value}K = {result:.2f}°C"

        return (
            f"Error: Cannot convert from '{from_unit}' to '{to_unit}'. "
            "Unsupported unit combination."
        )

    except Exception as exc:
        logger.error("Unit conversion failed: %s", exc, exc_info=True)
        return f"Error: Conversion failed - {str(exc)}"


async def format_date(date_str: str, output_format: str = "iso") -> str:
    """Format a date string to a different format.

    Args:
        date_str: Date string to format (supports ISO format, common formats)
        output_format: Output format ('iso', 'us', 'eu', 'readable')

    Returns:
        Formatted date string
    """
    logger.debug("Formatting date: %s to format: %s", date_str, output_format)

    try:
        # Try to parse the date
        from dateutil import parser

        dt = parser.parse(date_str)

        # Format based on requested output
        if output_format == "iso":
            return dt.isoformat()
        elif output_format == "us":
            return dt.strftime("%m/%d/%Y %I:%M %p")
        elif output_format == "eu":
            return dt.strftime("%d/%m/%Y %H:%M")
        elif output_format == "readable":
            return dt.strftime("%B %d, %Y at %I:%M %p")
        else:
            return dt.strftime(output_format)

    except ImportError:
        # Fallback if dateutil is not available
        logger.warning("dateutil not available, using basic datetime parsing")
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if output_format == "iso":
                return dt.isoformat()
            else:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as exc:
            return f"Error: Failed to parse date - {str(exc)}"
    except Exception as exc:
        logger.error("Date formatting failed: %s", exc, exc_info=True)
        return f"Error: Failed to format date - {str(exc)}"


async def get_search_cache_stats() -> str:
    """Get statistics about the search cache.

    Returns:
        JSON string with cache statistics
    """
    stats = _search_cache.get_stats()
    return json.dumps(stats, indent=2)


async def clear_search_cache() -> str:
    """Clear the search result cache.

    Returns:
        Confirmation message
    """
    _search_cache.clear()
    return "Search cache cleared successfully"


def register_default_tools(registry: ToolRegistry) -> None:
    """Register default built-in tools with metadata.

    Args:
        registry: Tool registry to register tools with
    """
    registry.register(
        "web_search",
        web_search,
        description="Search the web for current information using DuckDuckGo",
        category="search",
    )
    registry.register(
        "get_current_time",
        get_current_time,
        description="Get the current date and time in ISO format",
        category="utility",
    )
    registry.register(
        "calculate",
        calculate,
        description="Perform mathematical calculations safely",
        category="calculation",
    )
    registry.register(
        "format_json",
        format_json,
        description="Format JSON strings for better readability",
        category="formatting",
    )
    registry.register(
        "convert_units",
        convert_units,
        description="Convert between common units (length, weight, temperature, time)",
        category="calculation",
    )
    registry.register(
        "format_date",
        format_date,
        description="Format date strings to different formats",
        category="formatting",
    )
    registry.register(
        "get_search_cache_stats",
        get_search_cache_stats,
        description="Get statistics about the search result cache",
        category="utility",
    )
    registry.register(
        "clear_search_cache",
        clear_search_cache,
        description="Clear the search result cache",
        category="utility",
        requires_permission=True,
    )
    logger.info(
        "Registered %d default tools across %d categories",
        len(registry.list_tools()),
        len(set(m.get("category") for m in registry._tool_metadata.values())),
    )
