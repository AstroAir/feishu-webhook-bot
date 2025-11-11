"""Example demonstrating MCP (Model Context Protocol) integration.

This example shows how to:
1. Configure MCP servers with different transport types
2. Use MCP servers as toolsets with the AI agent
3. Enable MCP sampling for server-initiated LLM calls
4. Handle MCP server connection errors

Prerequisites:
- Install pydantic-ai with MCP support: pip install 'pydantic-ai-slim[mcp]'
- Set OPENAI_API_KEY environment variable
- Have MCP servers available (e.g., mcp-run-python)
"""

import asyncio
import os

from feishu_webhook_bot.ai import AIAgent, AIConfig, MCPConfig


async def example_stdio_mcp_server():
    """Example using stdio transport MCP server.

    This example uses the mcp-run-python server which allows the AI to
    execute Python code safely.
    """
    print("\n=== Example 1: stdio MCP Server ===\n")

    # Configure MCP with stdio transport
    mcp_config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": "run mcp-run-python stdio",  # Can be string or list
            }
        ],
        timeout_seconds=30,
    )

    # Create AI config with MCP enabled
    config = AIConfig(
        model="openai:gpt-4o",
        tools_enabled=True,
        mcp=mcp_config,
    )

    # Create and start agent
    agent = AIAgent(config)
    agent.start()

    try:
        # Ask the AI to use Python to solve a problem
        response = await agent.chat(
            user_id="user1", message="Calculate the factorial of 10 using Python code"
        )
        print(f"Response: {response}\n")

    finally:
        await agent.stop()


async def example_http_mcp_server():
    """Example using HTTP streamable transport MCP server.

    This example shows how to connect to an MCP server via HTTP.
    """
    print("\n=== Example 2: HTTP Streamable MCP Server ===\n")

    # Configure MCP with HTTP transport
    mcp_config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "weather-api",
                "url": "http://localhost:3001/mcp",  # Streamable HTTP
            }
        ],
        timeout_seconds=30,
    )

    # Create AI config with MCP enabled
    config = AIConfig(
        model="openai:gpt-4o",
        tools_enabled=True,
        mcp=mcp_config,
    )

    # Create and start agent
    agent = AIAgent(config)
    agent.start()

    try:
        # Ask the AI to use the weather API
        response = await agent.chat(
            user_id="user1", message="What's the weather like in San Francisco?"
        )
        print(f"Response: {response}\n")

    finally:
        await agent.stop()


async def example_multiple_mcp_servers():
    """Example using multiple MCP servers simultaneously.

    This shows how to configure multiple MCP servers with different
    transport types.
    """
    print("\n=== Example 3: Multiple MCP Servers ===\n")

    # Configure multiple MCP servers
    mcp_config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": ["run", "mcp-run-python", "stdio"],  # List format
            },
            {
                "name": "file-system",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            },
            {
                "name": "weather-api",
                "url": "http://localhost:3001/mcp",
            },
        ],
        timeout_seconds=30,
    )

    # Create AI config with MCP enabled
    config = AIConfig(
        model="openai:gpt-4o",
        tools_enabled=True,
        web_search_enabled=True,  # Can combine with built-in tools
        mcp=mcp_config,
    )

    # Create and start agent
    agent = AIAgent(config)
    agent.start()

    try:
        # The AI can now use tools from all MCP servers
        response = await agent.chat(
            user_id="user1",
            message="Calculate fibonacci(15) using Python, then save the result to /tmp/fib.txt",
        )
        print(f"Response: {response}\n")

        # Check agent stats
        stats = await agent.get_stats()
        print(f"MCP Stats: {stats['mcp_stats']}\n")

    finally:
        await agent.stop()


async def example_mcp_error_handling():
    """Example showing MCP error handling.

    This demonstrates how the agent handles MCP server connection failures
    gracefully.
    """
    print("\n=== Example 4: MCP Error Handling ===\n")

    # Configure MCP with an invalid server
    mcp_config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "invalid-server",
                "command": "nonexistent-command",
                "args": ["arg1", "arg2"],
            }
        ],
        timeout_seconds=5,
    )

    # Create AI config with MCP enabled
    config = AIConfig(
        model="openai:gpt-4o",
        tools_enabled=True,
        mcp=mcp_config,
    )

    # Create and start agent
    agent = AIAgent(config)
    agent.start()

    try:
        # The agent will continue to work even if MCP fails
        response = await agent.chat(user_id="user1", message="Hello! Can you help me?")
        print(f"Response (without MCP): {response}\n")

    finally:
        await agent.stop()


async def example_mcp_with_feishu_bot():
    """Example integrating MCP with Feishu webhook bot.

    This shows how to use MCP in a production Feishu bot setup.
    """
    print("\n=== Example 5: MCP with Feishu Bot ===\n")

    from feishu_webhook_bot import BotConfig, FeishuBot

    # Configure MCP
    mcp_config = MCPConfig(
        enabled=True,
        servers=[
            {
                "name": "python-runner",
                "command": "uv",
                "args": "run mcp-run-python stdio",
            }
        ],
    )

    # Configure AI with MCP
    ai_config = AIConfig(
        model="openai:gpt-4o",
        tools_enabled=True,
        web_search_enabled=True,
        mcp=mcp_config,
        system_prompt="You are a helpful assistant in a Feishu workspace. "
        "You can execute Python code and search the web to help users.",
    )

    # Configure bot
    bot_config = BotConfig(
        app_id="your-app-id",
        app_secret="your-app-secret",
        verification_token="your-verification-token",
        encrypt_key="your-encrypt-key",
        ai_config=ai_config,
    )

    # Create bot
    FeishuBot(bot_config)

    print("Feishu bot with MCP support configured!")
    print("The bot can now:")
    print("- Execute Python code via MCP")
    print("- Search the web")
    print("- Use all built-in tools")
    print("\nStart the bot with: bot.start()")


async def main():
    """Run all examples."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Some examples will fail.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'\n")

    # Run examples
    # Note: Uncomment the examples you want to run

    # Example 1: stdio MCP server (requires mcp-run-python)
    # await example_stdio_mcp_server()

    # Example 2: HTTP MCP server (requires running MCP server on localhost:3001)
    # await example_http_mcp_server()

    # Example 3: Multiple MCP servers
    # await example_multiple_mcp_servers()

    # Example 4: Error handling
    # await example_mcp_error_handling()

    # Example 5: Feishu bot integration
    await example_mcp_with_feishu_bot()

    print("\n✅ Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
