#!/usr/bin/env python3
"""Example of using Feishu Bot with AI capabilities.

This example demonstrates:
1. Setting up a bot with AI agent
2. Handling incoming messages with AI responses
3. Using conversation history for multi-turn dialogues
4. Leveraging web search and other tools

Prerequisites:
- Set environment variables:
  - FEISHU_WEBHOOK_URL: Your Feishu webhook URL
  - OPENAI_API_KEY: Your OpenAI API key (or other provider)
  - FEISHU_VERIFICATION_TOKEN: Feishu verification token for events

Usage:
    python examples/ai_bot_example.py
"""

import asyncio
import os
from pathlib import Path

from feishu_webhook_bot import FeishuBot, get_logger

logger = get_logger("example")


async def test_ai_chat():
    """Test AI chat functionality directly."""
    from feishu_webhook_bot.ai import AIAgent, AIConfig

    # Create AI configuration
    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        system_prompt="You are a helpful AI assistant.",
        max_conversation_turns=5,
        temperature=0.7,
        web_search_enabled=True,
    )

    # Create AI agent
    agent = AIAgent(config)
    agent.start()

    try:
        # Test conversation
        user_id = "test_user"

        # First message
        logger.info("Sending first message...")
        response1 = await agent.chat(user_id, "What is the capital of France?")
        logger.info("Response 1: %s", response1)

        # Follow-up message (uses conversation history)
        logger.info("Sending follow-up message...")
        response2 = await agent.chat(user_id, "What is its population?")
        logger.info("Response 2: %s", response2)

        # Web search example
        logger.info("Testing web search...")
        response3 = await agent.chat(user_id, "What are the latest news about AI technology?")
        logger.info("Response 3: %s", response3)

        # Get statistics
        stats = await agent.get_stats()
        logger.info("Agent stats: %s", stats)

    finally:
        await agent.stop()


def main():
    """Main function to run the AI-enabled bot."""
    # Check for required environment variables
    required_vars = ["FEISHU_WEBHOOK_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error("Missing required environment variables: %s", ", ".join(missing_vars))
        logger.info("Please set the following environment variables:")
        logger.info("  FEISHU_WEBHOOK_URL: Your Feishu webhook URL")
        logger.info("  OPENAI_API_KEY: Your OpenAI API key")
        logger.info("  FEISHU_VERIFICATION_TOKEN: (Optional) Feishu verification token")
        return

    # Load configuration
    config_path = Path(__file__).parent / "ai_bot_config.yaml"

    if not config_path.exists():
        logger.error("Configuration file not found: %s", config_path)
        logger.info("Please create the configuration file or use a different path")
        return

    try:
        # Create and start bot
        logger.info("Loading configuration from: %s", config_path)
        bot = FeishuBot.from_config(str(config_path))

        logger.info("Starting AI-enabled Feishu Bot...")
        logger.info("The bot will:")
        logger.info("  1. Listen for incoming messages on http://0.0.0.0:8080/webhook")
        logger.info("  2. Process messages with AI agent")
        logger.info("  3. Send responses back via webhook")
        logger.info("")
        logger.info("To test the bot:")
        logger.info("  1. Configure Feishu to send events to your server")
        logger.info("  2. Send a message to the bot")
        logger.info("  3. The AI will respond with intelligent answers")
        logger.info("")
        logger.info("Press Ctrl+C to stop the bot")

        # Start the bot
        bot.start()

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as exc:
        logger.error("Error running bot: %s", exc, exc_info=True)


def test_direct_chat():
    """Test AI chat directly without the full bot."""
    logger.info("Testing AI chat functionality...")
    asyncio.run(test_ai_chat())


if __name__ == "__main__":
    # Uncomment one of the following:

    # Option 1: Run the full bot with event server
    main()

    # Option 2: Test AI chat directly
    # test_direct_chat()
