"""Tests for AI integration."""

from unittest.mock import MagicMock

import pytest
from pydantic_ai import models
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from feishu_webhook_bot.ai import AIAgent, AIConfig, ConversationManager, ToolRegistry

# Use anyio for async tests with asyncio backend only
pytestmark = pytest.mark.anyio(backends=["asyncio"])

# Prevent accidental real model requests during testing
models.ALLOW_MODEL_REQUESTS = False


class TestAIConfig:
    """Test AI configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AIConfig()
        assert config.enabled is False
        assert config.model == "openai:gpt-4o"
        assert config.temperature == 0.7
        assert config.max_conversation_turns == 10
        assert config.web_search_enabled is True
        assert config.tools_enabled is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = AIConfig(
            enabled=True,
            model="anthropic:claude-3-5-sonnet-20241022",
            temperature=0.5,
            max_conversation_turns=5,
            web_search_enabled=False,
        )
        assert config.enabled is True
        assert config.model == "anthropic:claude-3-5-sonnet-20241022"
        assert config.temperature == 0.5
        assert config.max_conversation_turns == 5
        assert config.web_search_enabled is False


class TestConversationManager:
    """Test conversation management."""

    async def test_get_conversation(self):
        """Test getting or creating a conversation."""
        manager = ConversationManager(timeout_minutes=30)
        conv = await manager.get_conversation("user1")
        assert conv.user_id == "user1"
        assert len(conv.messages) == 0

    async def test_conversation_persistence(self):
        """Test that conversations persist across calls."""
        manager = ConversationManager(timeout_minutes=30)
        conv1 = await manager.get_conversation("user1")
        conv2 = await manager.get_conversation("user1")
        assert conv1 is conv2

    async def test_clear_conversation(self):
        """Test clearing conversation history."""
        manager = ConversationManager(timeout_minutes=30)
        conv = await manager.get_conversation("user1")
        conv.messages.append(MagicMock())  # Add a mock message
        assert len(conv.messages) == 1

        await manager.clear_conversation("user1")
        assert len(conv.messages) == 0

    async def test_delete_conversation(self):
        """Test deleting a conversation."""
        manager = ConversationManager(timeout_minutes=30)
        await manager.get_conversation("user1")
        await manager.delete_conversation("user1")

        # Getting conversation again should create a new one
        conv = await manager.get_conversation("user1")
        assert len(conv.messages) == 0

    async def test_get_stats(self):
        """Test getting conversation statistics."""
        manager = ConversationManager(timeout_minutes=30)
        await manager.get_conversation("user1")
        await manager.get_conversation("user2")

        stats = await manager.get_stats()
        assert stats["total_conversations"] == 2
        assert stats["timeout_minutes"] == 30


class TestToolRegistry:
    """Test tool registry."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()

        async def test_tool(param: str) -> str:
            return f"Result: {param}"

        registry.register("test_tool", test_tool)
        assert "test_tool" in registry.list_tools()

    def test_get_tool(self):
        """Test getting a registered tool."""
        registry = ToolRegistry()

        async def test_tool(param: str) -> str:
            return f"Result: {param}"

        registry.register("test_tool", test_tool)
        tool = registry.get_tool("test_tool")
        assert tool is test_tool

    def test_get_nonexistent_tool(self):
        """Test getting a tool that doesn't exist."""
        registry = ToolRegistry()
        tool = registry.get_tool("nonexistent")
        assert tool is None


class TestAIAgent:
    """Test AI agent."""

    async def test_agent_initialization(self):
        """Test AI agent initialization with TestModel."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-api-key",  # Fake API key to prevent initialization error
        )
        agent = AIAgent(config)
        with agent._agent.override(model=TestModel()):
            assert agent.config == config
            assert agent.conversation_manager is not None
            assert agent.tool_registry is not None

    async def test_agent_chat(self):
        """Test AI agent chat functionality with TestModel."""

        # Create a custom function model that returns a greeting
        def chat_response(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart("Hello, World!")])

        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-api-key",  # Fake API key to prevent initialization error
            temperature=0.0,
        )
        agent = AIAgent(config)
        agent.start()

        try:
            with agent._agent.override(model=FunctionModel(chat_response)):
                # Simple test message
                response = await agent.chat("test_user", "Say 'Hello, World!' and nothing else.")
                assert isinstance(response, str)
                assert len(response) > 0
                # The response should contain "Hello"
                assert "hello" in response.lower()
        finally:
            await agent.stop()

    async def test_agent_stats(self):
        """Test getting agent statistics with TestModel."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-api-key",  # Fake API key to prevent initialization error
        )
        agent = AIAgent(config)

        with agent._agent.override(model=TestModel()):
            stats = await agent.get_stats()
            assert "model" in stats
            assert "tools_enabled" in stats
            assert "web_search_enabled" in stats
            assert "conversation_stats" in stats


class TestBotIntegration:
    """Test AI integration with FeishuBot."""

    def test_bot_with_ai_config(self):
        """Test bot initialization with AI configuration."""
        from feishu_webhook_bot import BotConfig, FeishuBot
        from feishu_webhook_bot.ai.config import AIConfig

        ai_config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
        )

        config = BotConfig(
            webhooks=[],
            ai=ai_config,
        )

        bot = FeishuBot(config)
        # AI agent should be initialized if enabled
        # Note: It might be None if API key is not set
        assert hasattr(bot, "ai_agent")

    def test_bot_without_ai_config(self):
        """Test bot initialization without AI configuration."""
        from feishu_webhook_bot import BotConfig, FeishuBot

        config = BotConfig(webhooks=[])
        bot = FeishuBot(config)
        assert bot.ai_agent is None
