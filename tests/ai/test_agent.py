"""Comprehensive tests for AI Agent module.

Tests cover:
- AIResponse model validation
- AIAgentDependencies initialization
- AIAgent initialization and configuration
- Tool registration
- Metrics tracking
- API key handling
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.ai.agent import AIAgent, AIAgentDependencies, AIResponse
from feishu_webhook_bot.ai.config import AIConfig
from feishu_webhook_bot.ai.conversation import ConversationManager
from feishu_webhook_bot.ai.tools import ToolRegistry

# ==============================================================================
# AIResponse Tests
# ==============================================================================


class TestAIResponse:
    """Tests for AIResponse model."""

    def test_response_with_defaults(self):
        """Test AIResponse with default values."""
        response = AIResponse(message="Hello, world!")

        assert response.message == "Hello, world!"
        assert response.confidence == 1.0
        assert response.sources_used == []
        assert response.tools_called == []

    def test_response_with_all_fields(self):
        """Test AIResponse with all fields specified."""
        response = AIResponse(
            message="The weather is sunny.",
            confidence=0.95,
            sources_used=["weather.com", "accuweather.com"],
            tools_called=["get_weather", "format_response"],
        )

        assert response.message == "The weather is sunny."
        assert response.confidence == 0.95
        assert len(response.sources_used) == 2
        assert len(response.tools_called) == 2

    def test_response_confidence_bounds(self):
        """Test AIResponse confidence must be between 0 and 1."""
        # Valid confidence values
        response_low = AIResponse(message="test", confidence=0.0)
        response_high = AIResponse(message="test", confidence=1.0)

        assert response_low.confidence == 0.0
        assert response_high.confidence == 1.0

        # Invalid confidence values
        with pytest.raises(ValueError):
            AIResponse(message="test", confidence=-0.1)

        with pytest.raises(ValueError):
            AIResponse(message="test", confidence=1.1)

    def test_response_serialization(self):
        """Test AIResponse can be serialized to dict."""
        response = AIResponse(
            message="Test message",
            confidence=0.8,
            sources_used=["source1"],
            tools_called=["tool1"],
        )

        data = response.model_dump()

        assert data["message"] == "Test message"
        assert data["confidence"] == 0.8
        assert data["sources_used"] == ["source1"]
        assert data["tools_called"] == ["tool1"]


# ==============================================================================
# AIAgentDependencies Tests
# ==============================================================================


class TestAIAgentDependencies:
    """Tests for AIAgentDependencies."""

    def test_dependencies_creation(self):
        """Test AIAgentDependencies creation."""
        config = AIConfig()
        conversation_manager = ConversationManager()
        tool_registry = ToolRegistry()

        deps = AIAgentDependencies(
            user_id="user123",
            config=config,
            conversation_manager=conversation_manager,
            tool_registry=tool_registry,
        )

        assert deps.user_id == "user123"
        assert deps.config == config
        assert deps.conversation_manager == conversation_manager
        assert deps.tool_registry == tool_registry


# ==============================================================================
# AIAgent Initialization Tests
# ==============================================================================


class TestAIAgentInitialization:
    """Tests for AIAgent initialization."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_creation_default_config(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent creation with default configuration."""
        config = AIConfig()

        agent = AIAgent(config)

        assert agent.config == config
        assert agent.conversation_manager is not None
        assert agent.tool_registry is not None
        assert agent.mcp_client is not None
        assert agent.orchestrator is not None
        assert agent.circuit_breaker is not None

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_metrics_initialized(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent metrics are initialized."""
        config = AIConfig()

        agent = AIAgent(config)

        assert agent._metrics["total_requests"] == 0
        assert agent._metrics["successful_requests"] == 0
        assert agent._metrics["failed_requests"] == 0
        assert agent._metrics["total_response_time"] == 0.0
        assert agent._metrics["total_input_tokens"] == 0
        assert agent._metrics["total_output_tokens"] == 0

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_custom_model(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent with custom model."""
        config = AIConfig(model="anthropic:claude-3-opus")

        agent = AIAgent(config)

        assert agent.config.model == "anthropic:claude-3-opus"

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_streaming_enabled(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent with streaming enabled."""
        config = AIConfig()
        config.streaming.enabled = True

        agent = AIAgent(config)

        assert agent.config.streaming.enabled is True

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_mcp_enabled(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent with MCP enabled."""
        config = AIConfig()
        config.mcp.enabled = True

        agent = AIAgent(config)

        assert agent.config.mcp.enabled is True


# ==============================================================================
# AIAgent API Key Handling Tests
# ==============================================================================


class TestAIAgentAPIKeyHandling:
    """Tests for AIAgent API key handling."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_get_env_var_name_openai(self, mock_agent_class, mock_planner_agent):
        """Test environment variable name for OpenAI."""
        config = AIConfig(model="openai:gpt-4")
        agent = AIAgent(config)

        env_var = agent._get_env_var_name("openai:gpt-4")

        assert env_var == "OPENAI_API_KEY"

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_get_env_var_name_anthropic(self, mock_agent_class, mock_planner_agent):
        """Test environment variable name for Anthropic."""
        config = AIConfig(model="anthropic:claude-3")
        agent = AIAgent(config)

        env_var = agent._get_env_var_name("anthropic:claude-3")

        assert env_var == "ANTHROPIC_API_KEY"

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_get_env_var_name_google(self, mock_agent_class, mock_planner_agent):
        """Test environment variable name for Google."""
        config = AIConfig(model="google:gemini-pro")
        agent = AIAgent(config)

        env_var = agent._get_env_var_name("google:gemini-pro")

        assert env_var == "GOOGLE_API_KEY"

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_get_env_var_name_unknown_provider(self, mock_agent_class, mock_planner_agent):
        """Test environment variable name for unknown provider."""
        config = AIConfig(model="custom:model")
        agent = AIAgent(config)

        env_var = agent._get_env_var_name("custom:model")

        assert env_var == "CUSTOM_API_KEY"


# ==============================================================================
# AIAgent Tool Registration Tests
# ==============================================================================


class TestAIAgentToolRegistration:
    """Tests for AIAgent tool registration."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_register_custom_tool(self, mock_agent_class, mock_planner_agent):
        """Test registering a custom tool."""
        config = AIConfig()
        agent = AIAgent(config)

        def custom_tool(arg: str) -> str:
            """A custom tool."""
            return f"Result: {arg}"

        agent.register_tool(custom_tool)

        assert "custom_tool" in agent.tool_registry._tools

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_register_tool_with_custom_name(self, mock_agent_class, mock_planner_agent):
        """Test registering a tool with custom name."""
        config = AIConfig()
        agent = AIAgent(config)

        def my_func(arg: str) -> str:
            """A function."""
            return arg

        agent.register_tool(my_func, name="custom_name")

        assert "custom_name" in agent.tool_registry._tools

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_register_tool_with_custom_description(self, mock_agent_class, mock_planner_agent):
        """Test registering a tool with custom description."""
        config = AIConfig()
        agent = AIAgent(config)

        def my_func(arg: str) -> str:
            return arg

        agent.register_tool(my_func, description="Custom description")

        # Tool is registered in the registry
        assert "my_func" in agent.tool_registry._tools

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_register_tools_from_module(self, mock_agent_class, mock_planner_agent):
        """Test registering tools from a module."""
        config = AIConfig()
        agent = AIAgent(config)

        # Create a mock module with tools
        mock_module = MagicMock()
        mock_module.__name__ = "test_module"

        def tool_func():
            """A tool function."""
            pass

        tool_func._ai_tool_metadata = {"name": "test_tool", "description": "Test"}
        mock_module.tool_func = tool_func

        # Mock dir() to return our function
        with patch("builtins.dir", return_value=["tool_func"]):
            count = agent.register_tools_from_module(mock_module)

        assert count == 1


# ==============================================================================
# AIAgent Metrics Tests
# ==============================================================================


class TestAIAgentMetrics:
    """Tests for AIAgent metrics tracking."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_metrics_initialized(self, mock_agent_class, mock_planner_agent):
        """Test metrics are initialized correctly."""
        config = AIConfig()
        agent = AIAgent(config)

        assert agent._metrics["total_requests"] == 0
        assert agent._metrics["successful_requests"] == 0
        assert agent._metrics["failed_requests"] == 0
        assert agent._metrics["total_response_time"] == 0.0

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_metrics_can_be_modified(self, mock_agent_class, mock_planner_agent):
        """Test metrics can be modified."""
        config = AIConfig()
        agent = AIAgent(config)

        # Modify metrics
        agent._metrics["total_requests"] = 100
        agent._metrics["successful_requests"] = 90

        assert agent._metrics["total_requests"] == 100
        assert agent._metrics["successful_requests"] == 90


# ==============================================================================
# AIAgent Configuration Tests
# ==============================================================================


class TestAIAgentConfiguration:
    """Tests for AIAgent configuration options."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_tools_disabled(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent with tools disabled."""
        config = AIConfig(tools_enabled=False)

        agent = AIAgent(config)

        assert agent.config.tools_enabled is False

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_web_search_disabled(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent with web search disabled."""
        config = AIConfig(web_search_enabled=False)

        agent = AIAgent(config)

        assert agent.config.web_search_enabled is False

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_structured_output_disabled(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent with structured output disabled."""
        config = AIConfig(structured_output_enabled=False)

        agent = AIAgent(config)

        assert agent.config.structured_output_enabled is False

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_output_validators_disabled(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent with output validators disabled."""
        config = AIConfig(output_validators_enabled=False)

        agent = AIAgent(config)

        assert agent.config.output_validators_enabled is False

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_custom_system_prompt(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent with custom system prompt."""
        custom_prompt = "You are a helpful assistant specialized in Python."
        config = AIConfig(system_prompt=custom_prompt)

        agent = AIAgent(config)

        assert agent.config.system_prompt == custom_prompt

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_custom_timeout(self, mock_agent_class, mock_planner_agent):
        """Test AIAgent with custom conversation timeout."""
        config = AIConfig(conversation_timeout_minutes=60)

        agent = AIAgent(config)

        assert agent.config.conversation_timeout_minutes == 60


# ==============================================================================
# AIAgent Conversation Tests
# ==============================================================================


class TestAIAgentConversation:
    """Tests for AIAgent conversation management."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    @pytest.mark.anyio
    async def test_get_conversation_state(self, mock_agent_class, mock_planner_agent):
        """Test getting conversation state for a user."""
        config = AIConfig()
        agent = AIAgent(config)

        state = await agent.conversation_manager.get_conversation("user123")

        assert state.user_id == "user123"
        assert state.messages == []

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    @pytest.mark.anyio
    async def test_clear_conversation(self, mock_agent_class, mock_planner_agent):
        """Test clearing a conversation."""
        config = AIConfig()
        agent = AIAgent(config)

        # Create a conversation and add a message
        state = await agent.conversation_manager.get_conversation("user123")
        state.add_messages([{"role": "user", "content": "Hello"}])

        # Clear it using the agent's method
        await agent.clear_conversation("user123")

        # Get it again - should be fresh
        new_state = await agent.conversation_manager.get_conversation("user123")
        assert new_state.messages == []


# ==============================================================================
# AIAgent Model Switching Tests
# ==============================================================================


class TestAIAgentModelSwitching:
    """Tests for AIAgent model switching functionality."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    @pytest.mark.anyio
    async def test_switch_model_success(self, mock_agent_class, mock_planner_agent):
        """Test successful model switching."""
        config = AIConfig(model="openai:gpt-4o")
        agent = AIAgent(config)

        await agent.switch_model("anthropic:claude-3-5-sonnet-20241022")

        assert agent.config.model == "anthropic:claude-3-5-sonnet-20241022"

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    @pytest.mark.anyio
    async def test_switch_model_updates_pydantic_agent(self, mock_agent_class, mock_planner_agent):
        """Test model switch updates the pydantic-ai agent."""
        config = AIConfig(model="openai:gpt-4o")
        agent = AIAgent(config)

        # Agent should be created
        initial_call_count = mock_agent_class.call_count

        await agent.switch_model("openai:gpt-4o-mini")

        # Agent should be recreated
        assert mock_agent_class.call_count > initial_call_count

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    @pytest.mark.anyio
    async def test_get_current_model(self, mock_agent_class, mock_planner_agent):
        """Test getting current model."""
        config = AIConfig(model="openai:gpt-4o")
        agent = AIAgent(config)

        current_model = agent.current_model

        assert current_model == "openai:gpt-4o"


# ==============================================================================
# AIAgent Statistics Tests
# ==============================================================================


class TestAIAgentStatistics:
    """Tests for AIAgent statistics functionality."""

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    @pytest.mark.anyio
    async def test_get_stats_initial(self, mock_agent_class, mock_planner_agent, mock_agents_agent):
        """Test getting initial statistics."""
        config = AIConfig()
        agent = AIAgent(config)

        stats = await agent.get_stats()

        assert stats["performance"]["total_requests"] == 0
        assert stats["performance"]["successful_requests"] == 0
        assert stats["performance"]["failed_requests"] == 0
        assert stats["performance"]["average_response_time_seconds"] == 0

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    @pytest.mark.anyio
    async def test_get_stats_includes_model_info(
        self, mock_agent_class, mock_planner_agent, mock_agents_agent
    ):
        """Test statistics include model information."""
        config = AIConfig(model="openai:gpt-4o")
        agent = AIAgent(config)

        stats = await agent.get_stats()

        assert stats["model"] == "openai:gpt-4o"

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    @pytest.mark.anyio
    async def test_get_stats_includes_token_counts(
        self, mock_agent_class, mock_planner_agent, mock_agents_agent
    ):
        """Test statistics include token counts."""
        config = AIConfig()
        agent = AIAgent(config)

        stats = await agent.get_stats()

        assert "total_input_tokens" in stats["performance"]
        assert "total_output_tokens" in stats["performance"]

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    @pytest.mark.anyio
    async def test_stats_after_metrics_update(
        self, mock_agent_class, mock_planner_agent, mock_agents_agent
    ):
        """Test statistics after manual metrics update."""
        config = AIConfig()
        agent = AIAgent(config)

        # Simulate some activity
        agent._metrics["total_requests"] = 100
        agent._metrics["successful_requests"] = 95
        agent._metrics["failed_requests"] = 5
        agent._metrics["total_response_time"] = 50.0
        agent._metrics["total_input_tokens"] = 10000
        agent._metrics["total_output_tokens"] = 5000

        stats = await agent.get_stats()

        assert stats["performance"]["total_requests"] == 100
        assert stats["performance"]["successful_requests"] == 95
        assert stats["performance"]["failed_requests"] == 5
        assert round(stats["performance"]["average_response_time_seconds"], 3) == 0.526  # 50.0/95
        assert stats["performance"]["total_input_tokens"] == 10000
        assert stats["performance"]["total_output_tokens"] == 5000


# ==============================================================================
# AIAgent Conversation Store Tests
# ==============================================================================


class TestAIAgentConversationStore:
    """Tests for AIAgent conversation store integration."""

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_set_conversation_store(self, mock_agent_class, mock_planner_agent, mock_agents_agent):
        """Test setting conversation store."""
        config = AIConfig()
        agent = AIAgent(config)

        # Create a mock conversation store
        mock_store = MagicMock()
        mock_store.enabled = True

        agent.set_conversation_store(mock_store)

        assert agent.conversation_store == mock_store

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_set_conversation_store_none(
        self, mock_agent_class, mock_planner_agent, mock_agents_agent
    ):
        """Test setting conversation store to None."""
        config = AIConfig()
        agent = AIAgent(config)

        agent.set_conversation_store(None)

        assert agent.conversation_store is None


# ==============================================================================
# AIAgent MCP Integration Tests
# ==============================================================================


class TestAIAgentMCPIntegration:
    """Tests for AIAgent MCP integration."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_mcp_client_initialized(self, mock_agent_class, mock_planner_agent):
        """Test MCP client is initialized."""
        config = AIConfig()
        agent = AIAgent(config)

        assert agent.mcp_client is not None

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_mcp_enabled_config(self, mock_agent_class, mock_planner_agent):
        """Test agent respects MCP enabled config."""
        config = AIConfig()
        config.mcp.enabled = True

        agent = AIAgent(config)

        assert agent.config.mcp.enabled is True

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_mcp_disabled_config(self, mock_agent_class, mock_planner_agent):
        """Test agent respects MCP disabled config."""
        config = AIConfig()
        config.mcp.enabled = False

        agent = AIAgent(config)

        assert agent.config.mcp.enabled is False


# ==============================================================================
# AIAgent Multi-Agent Integration Tests
# ==============================================================================


class TestAIAgentMultiAgentIntegration:
    """Tests for AIAgent multi-agent integration."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_orchestrator_initialized(self, mock_agent_class, mock_planner_agent):
        """Test orchestrator is initialized."""
        config = AIConfig()
        agent = AIAgent(config)

        assert agent.orchestrator is not None

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_multi_agent_enabled_config(
        self, mock_agent_class, mock_planner_agent, mock_agents_agent
    ):
        """Test agent respects multi-agent enabled config."""
        config = AIConfig()
        config.multi_agent.enabled = True

        agent = AIAgent(config)

        assert agent.config.multi_agent.enabled is True
        assert agent.orchestrator.config.enabled is True

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_multi_agent_disabled_config(self, mock_agent_class, mock_planner_agent):
        """Test agent respects multi-agent disabled config."""
        config = AIConfig()
        config.multi_agent.enabled = False

        agent = AIAgent(config)

        assert agent.config.multi_agent.enabled is False


# ==============================================================================
# AIAgent Circuit Breaker Tests
# ==============================================================================


class TestAIAgentCircuitBreaker:
    """Tests for AIAgent circuit breaker functionality."""

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_circuit_breaker_initialized(
        self, mock_agent_class, mock_planner_agent, mock_agents_agent
    ):
        """Test circuit breaker is initialized."""
        config = AIConfig()
        agent = AIAgent(config)

        assert agent.circuit_breaker is not None

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_circuit_breaker_state(self, mock_agent_class, mock_planner_agent, mock_agents_agent):
        """Test circuit breaker initial state."""
        config = AIConfig()
        agent = AIAgent(config)

        # Initial state should be CLOSED (string value)
        assert agent.circuit_breaker.state == "CLOSED"


# ==============================================================================
# AIAgent Edge Cases Tests
# ==============================================================================


class TestAIAgentEdgeCases:
    """Edge case tests for AIAgent."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_empty_system_prompt(self, mock_agent_class, mock_planner_agent):
        """Test agent with empty system prompt."""
        config = AIConfig(system_prompt="")
        agent = AIAgent(config)

        assert agent.config.system_prompt == ""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_unicode_system_prompt(self, mock_agent_class, mock_planner_agent):
        """Test agent with unicode system prompt."""
        config = AIConfig(system_prompt="你是一个有帮助的助手。")
        agent = AIAgent(config)

        assert "助手" in agent.config.system_prompt

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_fallback_models(self, mock_agent_class, mock_planner_agent):
        """Test agent with fallback models configured."""
        config = AIConfig(
            model="openai:gpt-4o",
            fallback_models=["openai:gpt-4o-mini", "anthropic:claude-3-5-haiku-20241022"],
        )
        agent = AIAgent(config)

        assert len(agent.config.fallback_models) == 2

    @patch("feishu_webhook_bot.ai.multi_agent.agents.Agent")
    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_all_features_enabled(
        self, mock_agent_class, mock_planner_agent, mock_agents_agent
    ):
        """Test agent with all features enabled."""
        config = AIConfig(
            enabled=True,
            tools_enabled=True,
            web_search_enabled=True,
            structured_output_enabled=True,
            output_validators_enabled=True,
        )
        config.mcp.enabled = True
        config.multi_agent.enabled = True
        config.streaming.enabled = True

        agent = AIAgent(config)

        assert agent.config.tools_enabled is True
        assert agent.config.web_search_enabled is True
        assert agent.config.mcp.enabled is True
        assert agent.config.multi_agent.enabled is True
        assert agent.config.streaming.enabled is True

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    @patch("feishu_webhook_bot.ai.agent.Agent")
    def test_agent_with_all_features_disabled(self, mock_agent_class, mock_planner_agent):
        """Test agent with all features disabled."""
        config = AIConfig(
            enabled=False,
            tools_enabled=False,
            web_search_enabled=False,
            structured_output_enabled=False,
            output_validators_enabled=False,
        )
        config.mcp.enabled = False
        config.multi_agent.enabled = False
        config.streaming.enabled = False

        agent = AIAgent(config)

        assert agent.config.tools_enabled is False
        assert agent.config.web_search_enabled is False
        assert agent.config.mcp.enabled is False
        assert agent.config.multi_agent.enabled is False
        assert agent.config.streaming.enabled is False
