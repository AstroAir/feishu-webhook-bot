"""Advanced AI Agent Usage Examples.

This example demonstrates advanced features of the AI Agent including:
- Custom tool registration
- MCP server integration
- Multi-agent orchestration
- Streaming responses
- Conversation management
- Performance metrics

Prerequisites:
    pip install feishu-webhook-bot pydantic-ai

Usage:
    python ai_agent_advanced_example.py
"""

from __future__ import annotations

import asyncio
from typing import Any

from feishu_webhook_bot.ai.agent import AIAgent
from feishu_webhook_bot.ai.config import AIConfig, MCPConfig, MultiAgentConfig, StreamingConfig
from feishu_webhook_bot.ai.tools import ai_tool


# ==============================================================================
# Custom Tool Examples
# ==============================================================================


@ai_tool(name="get_weather", description="Get current weather for a city")
async def get_weather(city: str) -> str:
    """Get weather information for a city.

    Args:
        city: Name of the city

    Returns:
        Weather information as a string
    """
    # In a real implementation, this would call a weather API
    weather_data = {
        "Beijing": "Sunny, 25°C",
        "Shanghai": "Cloudy, 22°C",
        "Shenzhen": "Rainy, 28°C",
        "default": "Weather data unavailable",
    }
    return weather_data.get(city, weather_data["default"])


@ai_tool(name="translate_text", description="Translate text between languages")
async def translate_text(text: str, source_lang: str = "en", target_lang: str = "zh") -> str:
    """Translate text between languages.

    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code

    Returns:
        Translated text
    """
    # In a real implementation, this would call a translation API
    return f"[Translated from {source_lang} to {target_lang}]: {text}"


@ai_tool(name="search_database", description="Search internal database")
async def search_database(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search the internal database.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        List of search results
    """
    # In a real implementation, this would query a database
    return [
        {"id": 1, "title": f"Result for '{query}'", "relevance": 0.95},
        {"id": 2, "title": f"Related to '{query}'", "relevance": 0.85},
    ][:limit]


# ==============================================================================
# Basic Agent Usage
# ==============================================================================


async def basic_agent_example():
    """Demonstrate basic AI agent usage."""
    print("\n" + "=" * 60)
    print("Basic AI Agent Example")
    print("=" * 60)

    # Create agent with default configuration
    config = AIConfig(
        model="openai:gpt-4o-mini",  # Use a smaller model for testing
        system_prompt="You are a helpful assistant for a Feishu bot.",
        tools_enabled=True,
        web_search_enabled=False,  # Disable web search for this example
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # Simple chat
        response = await agent.chat("user123", "Hello! What can you help me with?")
        print("\nUser: Hello! What can you help me with?")
        print(f"Assistant: {response}")

        # Follow-up question (uses conversation history)
        response = await agent.chat("user123", "Can you calculate 15 * 7 + 23?")
        print("\nUser: Can you calculate 15 * 7 + 23?")
        print(f"Assistant: {response}")

        # Get conversation stats
        stats = await agent.get_stats()
        print("\nAgent Stats:")
        print(f"  Total Requests: {stats['performance']['total_requests']}")
        print(f"  Success Rate: {stats['performance']['success_rate_percent']}%")

    finally:
        await agent.stop()


# ==============================================================================
# Custom Tools Example
# ==============================================================================


async def custom_tools_example():
    """Demonstrate custom tool registration."""
    print("\n" + "=" * 60)
    print("Custom Tools Example")
    print("=" * 60)

    config = AIConfig(
        model="openai:gpt-4o-mini",
        system_prompt=(
            "You are a helpful assistant with access to weather, translation, "
            "and database search tools. Use them when appropriate."
        ),
        tools_enabled=True,
    )

    agent = AIAgent(config)

    # Register custom tools
    agent.register_tool(get_weather)
    agent.register_tool(translate_text)
    agent.register_tool(search_database)

    agent.start()

    try:
        # Ask about weather (should use get_weather tool)
        response = await agent.chat("user456", "What's the weather like in Beijing?")
        print("\nUser: What's the weather like in Beijing?")
        print(f"Assistant: {response}")

        # Ask for translation (should use translate_text tool)
        response = await agent.chat("user456", "Translate 'Hello World' to Chinese")
        print("\nUser: Translate 'Hello World' to Chinese")
        print(f"Assistant: {response}")

    finally:
        await agent.stop()


# ==============================================================================
# Streaming Response Example
# ==============================================================================


async def streaming_example():
    """Demonstrate streaming responses."""
    print("\n" + "=" * 60)
    print("Streaming Response Example")
    print("=" * 60)

    config = AIConfig(
        model="openai:gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
        streaming=StreamingConfig(
            enabled=True,
            chunk_size=10,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        print("\nUser: Tell me a short story about a robot.")
        print("Assistant: ", end="", flush=True)

        # Stream the response
        async for chunk in agent.chat_stream("user789", "Tell me a short story about a robot."):
            print(chunk, end="", flush=True)

        print()  # New line after streaming

    finally:
        await agent.stop()


# ==============================================================================
# Multi-Agent Orchestration Example
# ==============================================================================


async def multi_agent_example():
    """Demonstrate multi-agent orchestration."""
    print("\n" + "=" * 60)
    print("Multi-Agent Orchestration Example")
    print("=" * 60)

    config = AIConfig(
        model="openai:gpt-4o-mini",
        multi_agent=MultiAgentConfig(
            enabled=True,
            mode="sequential",  # or "parallel", "hierarchical"
            agents=[
                {
                    "name": "researcher",
                    "role": "Research and gather information",
                    "model": "openai:gpt-4o-mini",
                },
                {
                    "name": "writer",
                    "role": "Write and format content",
                    "model": "openai:gpt-4o-mini",
                },
            ],
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # This will use multi-agent orchestration
        response = await agent.chat(
            "user_multi",
            "Research the benefits of AI in healthcare and write a brief summary."
        )
        print("\nUser: Research the benefits of AI in healthcare and write a brief summary.")
        print(f"Assistant: {response}")

        # Get orchestrator stats
        stats = await agent.get_stats()
        print(f"\nOrchestrator Stats: {stats['orchestrator_stats']}")

    finally:
        await agent.stop()


# ==============================================================================
# MCP Integration Example
# ==============================================================================


async def mcp_integration_example():
    """Demonstrate MCP server integration."""
    print("\n" + "=" * 60)
    print("MCP Integration Example")
    print("=" * 60)

    # Note: This requires MCP servers to be running
    config = AIConfig(
        model="openai:gpt-4o-mini",
        mcp=MCPConfig(
            enabled=True,
            servers=[
                # Example: Python code runner MCP server
                {
                    "name": "python-runner",
                    "command": "uv",
                    "args": "run mcp-run-python stdio",
                },
                # Example: HTTP-based MCP server
                # {
                #     "name": "api-server",
                #     "url": "http://localhost:3000/mcp",
                # },
            ],
            timeout_seconds=30,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # Check MCP status
        stats = await agent.get_stats()
        mcp_stats = stats["mcp_stats"]
        print("\nMCP Status:")
        print(f"  Enabled: {mcp_stats['enabled']}")
        print(f"  Started: {mcp_stats['started']}")
        print(f"  Server Count: {mcp_stats['server_count']}")

        if mcp_stats["started"]:
            # Discover available tools from MCP servers
            tools = await agent.mcp_client.discover_tools()
            print("\nDiscovered MCP Tools:")
            for tool in tools:
                print(f"  - {tool['server']}/{tool['name']}: {tool['description']}")

    finally:
        await agent.stop()


# ==============================================================================
# Conversation Management Example
# ==============================================================================


async def conversation_management_example():
    """Demonstrate conversation management features."""
    print("\n" + "=" * 60)
    print("Conversation Management Example")
    print("=" * 60)

    config = AIConfig(
        model="openai:gpt-4o-mini",
        conversation_timeout_minutes=30,
        max_conversation_turns=10,
    )

    agent = AIAgent(config)
    agent.start()

    try:
        user_id = "user_conv"

        # Have a multi-turn conversation
        messages = [
            "My name is Alice.",
            "What's my name?",
            "I like programming in Python.",
            "What language do I like?",
        ]

        for msg in messages:
            response = await agent.chat(user_id, msg)
            print(f"\nUser: {msg}")
            print(f"Assistant: {response}")

        # Get conversation state
        conv = await agent.conversation_manager.get_conversation(user_id)
        print("\nConversation Stats:")
        print(f"  Message Count: {conv.message_count}")
        print(f"  Input Tokens: {conv.input_tokens}")
        print(f"  Output Tokens: {conv.output_tokens}")

        # Clear conversation
        await agent.clear_conversation(user_id)
        print("\nConversation cleared.")

        # Verify it's cleared
        response = await agent.chat(user_id, "What's my name?")
        print("\nUser: What's my name?")
        print(f"Assistant: {response}")

    finally:
        await agent.stop()


# ==============================================================================
# Structured Output Example
# ==============================================================================


async def structured_output_example():
    """Demonstrate structured output with AIResponse."""
    print("\n" + "=" * 60)
    print("Structured Output Example")
    print("=" * 60)

    config = AIConfig(
        model="openai:gpt-4o-mini",
        structured_output_enabled=True,
        output_validators_enabled=True,
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # The response will be validated and structured
        response = await agent.chat(
            "user_struct",
            "What is the capital of France? Please be confident in your answer."
        )
        print("\nUser: What is the capital of France?")
        print(f"Assistant: {response}")

        # If structured output is enabled, the internal response is an AIResponse object
        # with fields like confidence, sources_used, tools_called

    finally:
        await agent.stop()


# ==============================================================================
# Main Entry Point
# ==============================================================================


async def main():
    """Run all examples."""
    print("=" * 60)
    print("AI Agent Advanced Examples")
    print("=" * 60)
    print("\nNote: These examples require valid API keys to be set.")
    print("Set OPENAI_API_KEY environment variable before running.")

    # Uncomment the examples you want to run:

    # await basic_agent_example()
    # await custom_tools_example()
    # await streaming_example()
    # await multi_agent_example()
    # await mcp_integration_example()
    # await conversation_management_example()
    # await structured_output_example()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nTo run specific examples, uncomment them in the main() function.")


if __name__ == "__main__":
    asyncio.run(main())
