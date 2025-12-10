"""Example demonstrating multiple AI model providers.

This example shows how to:
1. Configure different AI model providers (OpenAI, Anthropic, Google, Groq, Cohere, Ollama)
2. Use provider-specific configuration options
3. Implement fallback models for reliability
4. Handle provider-specific features and limitations

Prerequisites:
- Install pydantic-ai: pip install pydantic-ai
- Set API keys for the providers you want to use:
  - OPENAI_API_KEY for OpenAI
  - ANTHROPIC_API_KEY for Anthropic (Claude)
  - GOOGLE_API_KEY for Google Gemini
  - GROQ_API_KEY for Groq
  - COHERE_API_KEY for Cohere
  - For Ollama: Install and run Ollama locally (http://localhost:11434)
"""

import asyncio
import os

from feishu_webhook_bot.ai import AIAgent, AIConfig, ModelProviderConfig
from feishu_webhook_bot.core.logger import get_logger

logger = get_logger("multi_provider_example")


async def example_openai():
    """Example 1: OpenAI (GPT-4)."""
    logger.info("\n=== Example 1: OpenAI (GPT-4) ===\n")

    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        system_prompt="You are a helpful AI assistant.",
        temperature=0.7,
        max_tokens=500,
        tools_enabled=True,
        web_search_enabled=True,
        provider_config=ModelProviderConfig(
            provider="openai",
            timeout=60.0,
            max_retries=2,
            organization_id=os.getenv("OPENAI_ORG_ID"),  # Optional
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        response = await agent.chat(user_id="user1", message="What are the key features of GPT-4?")
        logger.info("OpenAI Response:\n%s\n", response)
    finally:
        await agent.stop()


async def example_anthropic():
    """Example 2: Anthropic (Claude)."""
    logger.info("\n=== Example 2: Anthropic (Claude) ===\n")

    config = AIConfig(
        enabled=True,
        model="anthropic:claude-3-5-sonnet-20241022",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        system_prompt="You are Claude, an AI assistant created by Anthropic.",
        temperature=0.7,
        max_tokens=1000,
        tools_enabled=True,
        provider_config=ModelProviderConfig(
            provider="anthropic",
            timeout=90.0,
            max_retries=3,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        response = await agent.chat(
            user_id="user1", message="Explain the concept of constitutional AI in simple terms."
        )
        logger.info("Anthropic Response:\n%s\n", response)
    finally:
        await agent.stop()


async def example_google_gemini():
    """Example 3: Google Gemini."""
    logger.info("\n=== Example 3: Google Gemini ===\n")

    config = AIConfig(
        enabled=True,
        model="google:gemini-1.5-pro",
        api_key=os.getenv("GOOGLE_API_KEY"),
        system_prompt="You are a helpful AI assistant powered by Google Gemini.",
        temperature=0.8,
        max_tokens=800,
        tools_enabled=True,
        provider_config=ModelProviderConfig(
            provider="google",
            timeout=60.0,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        response = await agent.chat(
            user_id="user1", message="What makes Gemini different from other AI models?"
        )
        logger.info("Google Gemini Response:\n%s\n", response)
    finally:
        await agent.stop()


async def example_groq():
    """Example 4: Groq (Fast inference)."""
    logger.info("\n=== Example 4: Groq (Fast Inference) ===\n")

    config = AIConfig(
        enabled=True,
        model="groq:llama-3.1-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        system_prompt="You are a helpful AI assistant running on Groq's fast inference platform.",
        temperature=0.7,
        max_tokens=500,
        tools_enabled=True,
        provider_config=ModelProviderConfig(
            provider="groq",
            timeout=30.0,  # Groq is very fast
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        response = await agent.chat(
            user_id="user1", message="What are the advantages of fast AI inference?"
        )
        logger.info("Groq Response:\n%s\n", response)
    finally:
        await agent.stop()


async def example_cohere():
    """Example 5: Cohere."""
    logger.info("\n=== Example 5: Cohere ===\n")

    config = AIConfig(
        enabled=True,
        model="cohere:command-r-plus",
        api_key=os.getenv("COHERE_API_KEY"),
        system_prompt="You are a helpful AI assistant powered by Cohere.",
        temperature=0.7,
        max_tokens=500,
        tools_enabled=True,
        provider_config=ModelProviderConfig(
            provider="cohere",
            timeout=60.0,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        response = await agent.chat(
            user_id="user1", message="What are Cohere's strengths in enterprise AI?"
        )
        logger.info("Cohere Response:\n%s\n", response)
    finally:
        await agent.stop()


async def example_ollama():
    """Example 6: Ollama (Local models)."""
    logger.info("\n=== Example 6: Ollama (Local Models) ===\n")

    config = AIConfig(
        enabled=True,
        model="ollama:llama3.1",  # Or any model you have installed in Ollama
        system_prompt="You are a helpful AI assistant running locally via Ollama.",
        temperature=0.7,
        max_tokens=500,
        tools_enabled=False,  # Tool calling may not be supported by all Ollama models
        provider_config=ModelProviderConfig(
            provider="ollama",
            base_url="http://localhost:11434/v1",  # Ollama's OpenAI-compatible endpoint
            timeout=120.0,  # Local inference can be slower
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        response = await agent.chat(
            user_id="user1", message="What are the benefits of running AI models locally?"
        )
        logger.info("Ollama Response:\n%s\n", response)
    finally:
        await agent.stop()


async def example_with_fallback():
    """Example 7: Using fallback models for reliability."""
    logger.info("\n=== Example 7: Fallback Models ===\n")

    config = AIConfig(
        enabled=True,
        model="openai:gpt-4o",  # Primary model
        fallback_models=[
            "anthropic:claude-3-5-sonnet-20241022",  # First fallback
            "groq:llama-3.1-70b-versatile",  # Second fallback
        ],
        system_prompt="You are a helpful AI assistant with fallback support.",
        temperature=0.7,
        max_tokens=500,
        tools_enabled=True,
        provider_config=ModelProviderConfig(
            timeout=60.0,
            max_retries=2,
        ),
    )

    agent = AIAgent(config)
    agent.start()

    try:
        response = await agent.chat(
            user_id="user1", message="Explain the importance of fallback systems in production AI."
        )
        logger.info("Response (with fallback support):\n%s\n", response)
    finally:
        await agent.stop()


async def main():
    """Run all examples."""
    logger.info("=== Multi-Provider AI Examples ===\n")
    logger.info("This example demonstrates using different AI model providers.\n")

    # Check which API keys are available
    available_providers = []
    if os.getenv("OPENAI_API_KEY"):
        available_providers.append("OpenAI")
    if os.getenv("ANTHROPIC_API_KEY"):
        available_providers.append("Anthropic")
    if os.getenv("GOOGLE_API_KEY"):
        available_providers.append("Google")
    if os.getenv("GROQ_API_KEY"):
        available_providers.append("Groq")
    if os.getenv("COHERE_API_KEY"):
        available_providers.append("Cohere")

    logger.info(
        "Available providers: %s\n",
        ", ".join(available_providers) if available_providers else "None",
    )

    if not available_providers:
        logger.warning("No API keys found. Please set at least one provider's API key.")
        logger.info("\nExample API key setup:")
        logger.info("  export OPENAI_API_KEY='your-key'")
        logger.info("  export ANTHROPIC_API_KEY='your-key'")
        logger.info("  export GOOGLE_API_KEY='your-key'")
        logger.info("  export GROQ_API_KEY='your-key'")
        logger.info("  export COHERE_API_KEY='your-key'")
        return

    # Run examples for available providers
    if "OpenAI" in available_providers:
        await example_openai()

    if "Anthropic" in available_providers:
        await example_anthropic()

    if "Google" in available_providers:
        await example_google_gemini()

    if "Groq" in available_providers:
        await example_groq()

    if "Cohere" in available_providers:
        await example_cohere()

    # Ollama example (if running locally)
    # Uncomment to test:
    # await example_ollama()

    # Fallback example (requires at least 2 providers)
    if len(available_providers) >= 2:
        await example_with_fallback()

    logger.info("\n=== All examples completed ===")


if __name__ == "__main__":
    asyncio.run(main())
