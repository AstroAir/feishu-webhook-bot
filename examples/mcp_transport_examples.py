"""Examples demonstrating each MCP transport type.

This file contains examples for:
1. stdio transport (subprocess-based)
2. HTTP streamable transport
3. SSE transport (deprecated)
4. Error recovery and fallback

Prerequisites:
- Install: pip install 'pydantic-ai-slim[mcp]'
- Set OPENAI_API_KEY environment variable
- Have MCP servers available for testing

Usage:
    python examples/mcp_transport_examples.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_webhook_bot.ai import AIAgent, AIConfig, MCPConfig
from feishu_webhook_bot.core.logger import setup_logging

setup_logging(level="INFO")
logger = logging.getLogger(__name__)


async def example_stdio_transport():
    """Example 1: stdio transport with Python code execution.

    This is the recommended transport type for local MCP servers.
    The server runs as a subprocess and communicates via stdin/stdout.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 1: stdio Transport (Python Code Execution)")
    logger.info("=" * 60 + "\n")

    # Configure MCP with stdio transport
    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        mcp=MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "python-runner",
                    "command": "uv",
                    "args": "run mcp-run-python stdio",
                }
            ],
            timeout_seconds=30,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        logger.info("Asking AI to execute Python code...")
        response = await agent.chat(
            user_id="user1", message="Calculate the first 10 Fibonacci numbers using Python"
        )
        logger.info("Response:\n%s\n", response)

        # Check MCP stats
        stats = await agent.get_stats()
        logger.info("MCP Stats:")
        logger.info("  - Enabled: %s", stats["mcp_stats"]["enabled"])
        logger.info("  - Started: %s", stats["mcp_stats"]["started"])
        logger.info("  - Servers: %s", stats["mcp_stats"]["server_count"])

    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
    finally:
        await agent.stop()


async def example_stdio_with_list_args():
    """Example 2: stdio transport with list arguments.

    Shows how to pass arguments as a list instead of a string.
    Useful for complex command-line arguments.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: stdio Transport with List Arguments")
    logger.info("=" * 60 + "\n")

    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        mcp=MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "filesystem",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                }
            ],
            timeout_seconds=30,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        logger.info("Asking AI to list files...")
        response = await agent.chat(user_id="user1", message="List all .txt files in the directory")
        logger.info("Response:\n%s\n", response)

    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
    finally:
        await agent.stop()


async def example_http_streamable_transport():
    """Example 3: HTTP streamable transport.

    Modern HTTP-based transport using streaming.
    Requires an MCP server running on HTTP.

    Note: This example assumes you have an MCP server running on localhost:3001
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: HTTP Streamable Transport")
    logger.info("=" * 60 + "\n")

    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        mcp=MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "weather-api",
                    "url": "http://localhost:3001/mcp",
                }
            ],
            timeout_seconds=30,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        logger.info("Asking AI to use HTTP MCP server...")
        response = await agent.chat(user_id="user1", message="What's the weather like?")
        logger.info("Response:\n%s\n", response)

    except Exception as e:
        logger.error("Error (expected if server not running): %s", e)
        logger.info("To run this example, start an MCP server on http://localhost:3001/mcp")
    finally:
        await agent.stop()


async def example_sse_transport():
    """Example 4: SSE transport (deprecated).

    HTTP Server-Sent Events transport.
    This transport is deprecated in favor of streamable HTTP.

    Note: This example assumes you have an MCP server running on localhost:3002
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: SSE Transport (Deprecated)")
    logger.info("=" * 60 + "\n")

    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        mcp=MCPConfig(
            enabled=True,
            servers=[
                {
                    "name": "legacy-api",
                    "url": "http://localhost:3002/sse",  # Must end with /sse
                }
            ],
            timeout_seconds=30,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        logger.info("Asking AI to use SSE MCP server...")
        response = await agent.chat(user_id="user1", message="Hello from SSE transport")
        logger.info("Response:\n%s\n", response)

    except Exception as e:
        logger.error("Error (expected if server not running): %s", e)
        logger.info("Note: SSE transport is deprecated. Use streamable HTTP instead.")
    finally:
        await agent.stop()


async def example_multiple_transports():
    """Example 5: Multiple MCP servers with different transports.

    Shows how to use multiple MCP servers simultaneously,
    each with a different transport type.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: Multiple Transports")
    logger.info("=" * 60 + "\n")

    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        mcp=MCPConfig(
            enabled=True,
            servers=[
                # stdio transport
                {
                    "name": "python-runner",
                    "command": "uv",
                    "args": "run mcp-run-python stdio",
                },
                # HTTP streamable transport
                {
                    "name": "weather-api",
                    "url": "http://localhost:3001/mcp",
                },
                # SSE transport (deprecated)
                {
                    "name": "legacy-api",
                    "url": "http://localhost:3002/sse",
                },
            ],
            timeout_seconds=30,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        logger.info("Asking AI to use multiple MCP servers...")
        response = await agent.chat(
            user_id="user1", message="Calculate 5! using Python, then check the weather"
        )
        logger.info("Response:\n%s\n", response)

        # Check stats
        stats = await agent.get_stats()
        logger.info("\nMCP Stats:")
        logger.info("  - Total servers configured: %s", len(config.mcp.servers))
        logger.info("  - MCP started: %s", stats["mcp_stats"]["started"])

    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
    finally:
        await agent.stop()


async def example_error_recovery():
    """Example 6: Error recovery and graceful degradation.

    Shows how the agent continues working even when MCP servers fail.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 6: Error Recovery and Graceful Degradation")
    logger.info("=" * 60 + "\n")

    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        tools_enabled=True,
        web_search_enabled=True,
        mcp=MCPConfig(
            enabled=True,
            servers=[
                # Invalid server - will fail
                {
                    "name": "invalid-server",
                    "command": "nonexistent-command",
                    "args": "invalid",
                },
            ],
            timeout_seconds=5,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        logger.info("Testing with invalid MCP server...")
        logger.info("Agent should continue working with built-in tools\n")

        response = await agent.chat(user_id="user1", message="What is 2 + 2?")
        logger.info("Response:\n%s\n", response)
        logger.info("✓ Agent worked despite MCP failure!")

        # Check stats
        stats = await agent.get_stats()
        logger.info("\nStats:")
        logger.info("  - MCP enabled: %s", stats["mcp_stats"]["enabled"])
        logger.info("  - MCP started: %s", stats["mcp_stats"]["started"])
        logger.info("  - Built-in tools available: %s", stats["tools_enabled"])

    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
    finally:
        await agent.stop()


async def main():
    """Run all examples."""
    logger.info("=" * 60)
    logger.info("MCP Transport Type Examples")
    logger.info("=" * 60)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not set!")
        logger.info("Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    # Run examples
    # Note: Comment out examples that require servers you don't have

    await example_stdio_transport()
    # await example_stdio_with_list_args()  # Requires filesystem server
    # await example_http_streamable_transport()  # Requires HTTP server
    # await example_sse_transport()  # Requires SSE server
    # await example_multiple_transports()  # Requires multiple servers
    await example_error_recovery()

    logger.info("\n" + "=" * 60)
    logger.info("Examples completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
