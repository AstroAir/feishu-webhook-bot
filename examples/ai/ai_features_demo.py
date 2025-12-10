"""Example demonstrating AI features.

This example shows how to use:
- Search result caching
- Token tracking and analytics
- Tool registry with metadata
- Conversation export/import
- Circuit breaker for error handling
- Performance metrics
"""

from __future__ import annotations

import asyncio
import os

from feishu_webhook_bot.ai import (
    AIAgent,
    AIConfig,
    CircuitBreaker,
    ConversationManager,
    ToolRegistry,
)
from feishu_webhook_bot.ai.tools import (
    clear_search_cache,
    get_search_cache_stats,
    register_default_tools,
)


async def show_caching() -> None:
    """Demonstrate search result caching."""
    print("\n=== Search Result Caching ===")

    # Get cache stats before
    stats_before = await get_search_cache_stats()
    print(f"Cache stats before: {stats_before}")

    # Perform a search (this will cache the result)
    # Note: In real usage, this would be called through the AI agent
    print("First search will be cached...")

    # Get cache stats after
    stats_after = await get_search_cache_stats()
    print(f"Cache stats after: {stats_after}")

    # Clear cache
    result = await clear_search_cache()
    print(f"Clear cache: {result}")


async def show_token_tracking() -> None:
    """Demonstrate token usage tracking."""
    print("\n=== Token Usage Tracking ===")

    manager = ConversationManager()

    # Create a conversation
    conv = await manager.get_conversation("user123")

    # Simulate adding messages with token counts
    from pydantic_ai.messages import ModelRequest, ModelResponse

    request = ModelRequest(parts=[{"content": "Hello, how are you?"}])
    response = ModelResponse(
        parts=[{"content": "I'm doing well, thank you!"}], timestamp="2025-01-08T00:00:00Z"
    )

    conv.add_messages([request, response], input_tokens=10, output_tokens=15)

    # Get analytics
    analytics = conv.get_analytics()
    print("Conversation analytics:")
    print(f"  User ID: {analytics['user_id']}")
    print(f"  Messages: {analytics['message_count']}")
    print(f"  Input tokens: {analytics['input_tokens']}")
    print(f"  Output tokens: {analytics['output_tokens']}")
    print(f"  Total tokens: {analytics['total_tokens']}")
    print(f"  Duration: {analytics['duration_seconds']:.2f}s")


async def show_conversation_export_import() -> None:
    """Demonstrate conversation export and import."""
    print("\n=== Conversation Export/Import ===")

    manager = ConversationManager()

    # Create a conversation with some data
    conv = await manager.get_conversation("user456")
    conv.context["user_name"] = "Alice"
    conv.context["preferences"] = {"language": "en", "timezone": "UTC"}
    conv.summary = "Discussion about AI features"

    # Export conversation
    json_data = await manager.export_conversation("user456")
    print("Exported conversation (first 200 chars):")
    print(json_data[:200] + "...")

    # Delete the conversation
    await manager.delete_conversation("user456")
    print("Conversation deleted")

    # Import it back
    user_id = await manager.import_conversation(json_data)
    print(f"Conversation imported for user: {user_id}")

    # Verify the data
    conv2 = await manager.get_conversation(user_id)
    print(f"Restored context: {conv2.context}")
    print(f"Restored summary: {conv2.summary}")


async def show_tool_registry() -> None:
    """Demonstrate tool registry features."""
    print("\n=== Tool Registry ===")

    registry = ToolRegistry()
    register_default_tools(registry)

    # Get tools by category
    search_tools = registry.get_tools_by_category("search")
    print(f"Search tools: {search_tools}")

    calc_tools = registry.get_tools_by_category("calculation")
    print(f"Calculation tools: {calc_tools}")

    # Get tool info
    tool_info = registry.get_tool_info("web_search")
    if tool_info:
        print(f"\nTool: {tool_info['name']}")
        print(f"  Description: {tool_info['description']}")
        print(f"  Category: {tool_info['category']}")
        print(f"  Usage count: {tool_info['usage_count']}")

    # Get registry stats
    stats = registry.get_stats()
    print("\nRegistry stats:")
    print(f"  Total tools: {stats['total_tools']}")
    print(f"  Categories: {stats['categories']}")


async def show_circuit_breaker() -> None:
    """Demonstrate circuit breaker functionality."""
    print("\n=== Circuit Breaker ===")

    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)

    # Successful call
    def success_func() -> str:
        return "Success!"

    result = breaker.call(success_func)
    print(f"Successful call: {result}")
    print(f"Circuit state: {breaker.state}")

    # Simulate failures
    def failing_func() -> None:
        raise ValueError("Simulated error")

    print("\nSimulating failures...")
    for i in range(3):
        try:
            breaker.call(failing_func)
        except ValueError:
            print(f"  Failure {i + 1}, state: {breaker.state}")

    # Circuit should be open now
    print(f"\nCircuit state after failures: {breaker.state}")

    # Try to call - should fail immediately
    try:
        breaker.call(success_func)
    except Exception as e:
        print(f"Call blocked by circuit breaker: {type(e).__name__}")


async def show_performance_metrics() -> None:
    """Demonstrate performance metrics tracking."""
    print("\n=== Performance Metrics ===")

    # Check if API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set - skipping agent metrics demo")
        print("Set OPENAI_API_KEY to see full metrics tracking")
        return

    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o-mini",
        tools_enabled=True,
        web_search_enabled=False,  # Disable to avoid actual searches
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # Simulate some interactions
        await agent.chat("user789", "Hello!")
        await agent.chat("user789", "What's 2+2?")

        # Get performance stats
        stats = agent.get_stats()
        print("Agent performance metrics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Successful: {stats['successful_requests']}")
        print(f"  Failed: {stats['failed_requests']}")
        print(f"  Avg response time: {stats['avg_response_time_ms']:.2f}ms")
        print(f"  Total tokens: {stats['total_tokens']}")
        print(f"  Cache hit rate: {stats['cache_hit_rate_percent']:.1f}%")
    finally:
        agent.stop()


async def main() -> None:
    """Run all demonstrations."""
    print("=" * 60)
    print("AI Features Demonstration")
    print("=" * 60)

    await show_caching()
    await show_token_tracking()
    await show_conversation_export_import()
    await show_tool_registry()
    await show_circuit_breaker()
    await show_performance_metrics()

    print("\n" + "=" * 60)
    print("Demonstration complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
