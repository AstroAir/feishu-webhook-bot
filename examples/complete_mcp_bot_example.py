"""Complete end-to-end example of a Feishu bot with MCP integration.

This example demonstrates:
1. Setting up a Feishu bot with MCP support
2. Configuring multiple MCP servers (stdio and HTTP)
3. Handling webhook events with AI responses
4. Error recovery and graceful degradation
5. Combining MCP tools with built-in tools

Prerequisites:
- Install dependencies: pip install 'pydantic-ai-slim[mcp]' duckduckgo-search
- Set environment variables:
  - OPENAI_API_KEY: Your OpenAI API key
  - FEISHU_APP_ID: Your Feishu app ID
  - FEISHU_APP_SECRET: Your Feishu app secret
  - FEISHU_VERIFICATION_TOKEN: Your Feishu verification token
  - FEISHU_ENCRYPT_KEY: Your Feishu encrypt key (optional)
- Have MCP servers available (e.g., mcp-run-python)

Usage:
    python examples/complete_mcp_bot_example.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from feishu_webhook_bot import BotConfig, FeishuBot
from feishu_webhook_bot.ai import AIConfig, MCPConfig, StreamingConfig
from feishu_webhook_bot.core.logger import setup_logging

# Setup logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)


def check_prerequisites():
    """Check if all prerequisites are met."""
    missing = []

    # Check environment variables
    required_env_vars = [
        "OPENAI_API_KEY",
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_VERIFICATION_TOKEN",
    ]

    for var in required_env_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        logger.info("Please set the following environment variables:")
        for var in missing:
            logger.info("  export %s='your-value-here'", var)
        return False

    return True


def create_bot_config():
    """Create bot configuration with MCP support.

    Returns:
        BotConfig: Configured bot instance
    """
    # Configure MCP servers
    mcp_config = MCPConfig(
        enabled=True,
        servers=[
            # Python code execution via stdio
            {
                "name": "python-runner",
                "command": "uv",
                "args": "run mcp-run-python stdio",
            },
            # You can add more MCP servers here:
            # {
            #     "name": "filesystem",
            #     "command": "npx",
            #     "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            # },
            # {
            #     "name": "weather-api",
            #     "url": "http://localhost:3001/mcp",
            # },
        ],
        timeout_seconds=30,
    )

    # Configure AI with MCP and other features
    ai_config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        system_prompt=(
            "You are a helpful AI assistant integrated with Feishu. "
            "You can execute Python code, search the web, and help users with various tasks. "
            "When executing code, always explain what you're doing and show the results clearly."
        ),
        max_conversation_turns=10,
        conversation_timeout_minutes=30,
        temperature=0.7,
        max_tokens=1000,
        # Enable built-in tools
        tools_enabled=True,
        web_search_enabled=True,
        web_search_max_results=5,
        # Enable MCP
        mcp=mcp_config,
        # Optional: Enable streaming for real-time responses
        streaming=StreamingConfig(
            enabled=False,  # Set to True for streaming
            debounce_ms=100,
        ),
        # Optional: Enable structured output validation
        structured_output_enabled=False,
        output_validators_enabled=False,
    )

    # Configure bot
    bot_config = BotConfig(
        app_id=os.getenv("FEISHU_APP_ID"),
        app_secret=os.getenv("FEISHU_APP_SECRET"),
        verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN"),
        encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY"),
        # AI configuration
        ai_config=ai_config,
        # Event server configuration
        event_server_enabled=True,
        event_server_host="0.0.0.0",
        event_server_port=8080,
        event_server_path="/webhook",
    )

    return bot_config


async def test_ai_capabilities(bot: FeishuBot):
    """Test AI capabilities before starting the bot.

    Args:
        bot: FeishuBot instance
    """
    if not bot.ai_agent:
        logger.warning("AI agent not available")
        return

    logger.info("Testing AI capabilities...")

    # Test 1: Basic conversation
    logger.info("\n=== Test 1: Basic Conversation ===")
    try:
        response = await bot.ai_agent.chat(
            user_id="test_user", message="Hello! Can you introduce yourself?"
        )
        logger.info("Response: %s", response)
    except Exception as e:
        logger.error("Test 1 failed: %s", e)

    # Test 2: Web search
    logger.info("\n=== Test 2: Web Search ===")
    try:
        response = await bot.ai_agent.chat(
            user_id="test_user", message="What's the latest news about AI?"
        )
        logger.info("Response: %s", response[:200] + "...")
    except Exception as e:
        logger.error("Test 2 failed: %s", e)

    # Test 3: Python code execution via MCP
    logger.info("\n=== Test 3: Python Code Execution (MCP) ===")
    try:
        response = await bot.ai_agent.chat(
            user_id="test_user", message="Calculate the factorial of 10 using Python code"
        )
        logger.info("Response: %s", response)
    except Exception as e:
        logger.error("Test 3 failed: %s", e)

    # Test 4: Complex task combining multiple tools
    logger.info("\n=== Test 4: Complex Task (Multiple Tools) ===")
    try:
        response = await bot.ai_agent.chat(
            user_id="test_user",
            message=(
                "Search for the current Bitcoin price, "
                "then calculate its value in EUR using Python "
                "(assume 1 BTC = 0.9 EUR for calculation)"
            ),
        )
        logger.info("Response: %s", response[:200] + "...")
    except Exception as e:
        logger.error("Test 4 failed: %s", e)

    # Get AI stats
    logger.info("\n=== AI Agent Statistics ===")
    try:
        stats = await bot.ai_agent.get_stats()
        logger.info("Model: %s", stats["model"])
        logger.info("Tools enabled: %s", stats["tools_enabled"])
        logger.info("Web search enabled: %s", stats["web_search_enabled"])
        logger.info("MCP enabled: %s", stats["mcp_stats"]["enabled"])
        logger.info("MCP started: %s", stats["mcp_stats"]["started"])
        logger.info("MCP servers: %s", stats["mcp_stats"]["server_count"])
    except Exception as e:
        logger.error("Failed to get stats: %s", e)


async def main():
    """Main function to run the bot."""
    logger.info("=== Feishu Bot with MCP Integration ===\n")

    # Check prerequisites
    if not check_prerequisites():
        logger.error("Prerequisites not met. Exiting.")
        return

    # Create bot configuration
    logger.info("Creating bot configuration...")
    config = create_bot_config()

    # Create bot
    logger.info("Creating bot instance...")
    bot = FeishuBot(config)

    # Start bot
    logger.info("Starting bot...")
    bot.start()

    try:
        # Test AI capabilities
        await test_ai_capabilities(bot)

        # Keep bot running
        logger.info("\n=== Bot is running ===")
        logger.info("Event server: http://0.0.0.0:8080/webhook")
        logger.info("Configure this URL in your Feishu app settings")
        logger.info("Press Ctrl+C to stop\n")

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
    finally:
        # Stop bot
        logger.info("Stopping bot...")
        await bot.stop()
        logger.info("Bot stopped")


if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
