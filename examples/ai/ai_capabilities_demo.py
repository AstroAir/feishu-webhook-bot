"""Examples demonstrating AI capabilities.

This example demonstrates:
1. Structured output validation using Pydantic models
2. Streaming responses for real-time AI interactions
3. Output validators with retry logic
4. Multi-agent orchestration (A2A)
5. MCP (Model Context Protocol) integration
"""

import asyncio
import os

from feishu_webhook_bot.ai import (
    AIAgent,
    AIConfig,
    MCPConfig,
    MultiAgentConfig,
    StreamingConfig,
)


async def example_structured_output():
    """Example: Structured output validation with Pydantic models."""
    print("\n=== Example 1: Structured Output Validation ===\n")

    # Configure AI with structured output enabled
    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        structured_output_enabled=True,
        system_prompt="You are a helpful assistant. Always provide confident, detailed responses.",
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # Chat with structured output
        response = await agent.chat(
            user_id="user123",
            message="What is the capital of France?",
        )

        print(f"Response: {response}")
        print(f"Type: {type(response)}")

    finally:
        await agent.stop()


async def example_streaming_response():
    """Example: Streaming responses for real-time AI interactions."""
    print("\n=== Example 2: Streaming Responses ===\n")

    # Configure AI with streaming enabled
    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        streaming=StreamingConfig(
            enabled=True,
            debounce_ms=50,
        ),
        system_prompt="You are a helpful assistant.",
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # Stream the response
        print("Streaming response: ", end="", flush=True)

        async for chunk in agent.chat_stream(
            user_id="user123",
            message="Tell me a short story about a robot learning to paint.",
        ):
            print(chunk, end="", flush=True)

        print("\n")

    finally:
        await agent.stop()


async def example_output_validators():
    """Example: Output validators with retry logic."""
    print("\n=== Example 3: Output Validators with Retry ===\n")

    # Configure AI with output validators enabled
    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        structured_output_enabled=True,
        output_validators_enabled=True,
        retry_on_validation_error=True,
        max_retries=3,
        system_prompt="You are a helpful assistant.",
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # This should trigger validation and potentially retry
        response = await agent.chat(
            user_id="user123",
            message="What is 2+2?",
        )

        print(f"Response: {response}")

    finally:
        await agent.stop()


async def example_multi_agent_sequential():
    """Example: Multi-agent orchestration in sequential mode."""
    print("\n=== Example 4: Multi-Agent Sequential Orchestration ===\n")

    # Configure AI with multi-agent enabled
    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        multi_agent=MultiAgentConfig(
            enabled=True,
            orchestration_mode="sequential",
            max_agents=3,
        ),
        system_prompt="You are a helpful assistant.",
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # Use multi-agent orchestration
        response = await agent.chat(
            user_id="user123",
            message="What are the latest developments in quantum computing?",
        )

        print(f"Multi-agent response:\n{response}")

        # Get orchestrator stats
        stats = await agent.get_stats()
        print(f"\nOrchestrator stats: {stats['orchestrator_stats']}")

    finally:
        await agent.stop()


async def example_multi_agent_concurrent():
    """Example: Multi-agent orchestration in concurrent mode."""
    print("\n=== Example 5: Multi-Agent Concurrent Orchestration ===\n")

    # Configure AI with concurrent multi-agent
    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        multi_agent=MultiAgentConfig(
            enabled=True,
            orchestration_mode="concurrent",
            max_agents=3,
        ),
        system_prompt="You are a helpful assistant.",
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # Use concurrent multi-agent orchestration
        response = await agent.chat(
            user_id="user123",
            message="Explain the benefits of renewable energy.",
        )

        print(f"Concurrent multi-agent response:\n{response}")

    finally:
        await agent.stop()


async def example_mcp_integration():
    """Example: MCP (Model Context Protocol) integration."""
    print("\n=== Example 6: MCP Integration ===\n")

    # Configure AI with MCP enabled
    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        mcp=MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "filesystem",
                    "command": "mcp-server-filesystem",
                    "args": "--root /tmp",
                },
            ],
            timeout_seconds=30,
        ),
        system_prompt="You are a helpful assistant with access to MCP tools.",
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # Get MCP stats
        stats = await agent.get_stats()
        print(f"MCP stats: {stats['mcp_stats']}")

        # Chat with MCP-enabled agent
        response = await agent.chat(
            user_id="user123",
            message="Hello! What can you help me with?",
        )

        print(f"Response: {response}")

    finally:
        await agent.stop()


async def example_combined_features():
    """Example: Combining multiple features."""
    print("\n=== Example 7: Combined Features ===\n")

    # Configure AI with multiple features
    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        structured_output_enabled=True,
        output_validators_enabled=True,
        streaming=StreamingConfig(
            enabled=True,
            debounce_ms=100,
        ),
        multi_agent=MultiAgentConfig(
            enabled=False,  # Disable for this example to show streaming
            orchestration_mode="sequential",
        ),
        mcp=MCPConfig(
            enabled=False,  # Disable for this example
        ),
        system_prompt="You are a helpful, knowledgeable assistant.",
    )

    agent = AIAgent(config)
    agent.start()

    try:
        # Get comprehensive stats
        stats = await agent.get_stats()
        print("Agent configuration:")
        print(f"  - Model: {stats['model']}")
        print(f"  - Streaming: {stats['streaming_enabled']}")
        print(f"  - Structured output: {stats['structured_output_enabled']}")
        print(f"  - Output validators: {stats['output_validators_enabled']}")
        print(f"  - MCP: {stats['mcp_stats']['enabled']}")
        print(f"  - Multi-agent: {stats['orchestrator_stats']['enabled']}")
        print()

        # Stream a response
        print("Streaming response: ", end="", flush=True)
        async for chunk in agent.chat_stream(
            user_id="user123",
            message="Explain the concept of machine learning in simple terms.",
        ):
            print(chunk, end="", flush=True)
        print("\n")

    finally:
        await agent.stop()


async def main():
    """Run all examples."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Please set it to run these examples.")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        return

    print("=" * 70)
    print("AI Capabilities Examples")
    print("=" * 70)

    # Run examples
    # Note: Comment out examples you don't want to run
    await example_structured_output()
    await example_streaming_response()
    await example_output_validators()
    await example_multi_agent_sequential()
    await example_multi_agent_concurrent()
    await example_mcp_integration()
    await example_combined_features()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
