"""Tests for AI capabilities."""

from unittest.mock import patch

import pytest
from pydantic_ai import models
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from feishu_webhook_bot.ai import (
    AgentOrchestrator,
    AIAgent,
    AIConfig,
    AIServiceUnavailableError,
    AnalysisAgent,
    ConfigurationError,
    ConversationNotFoundError,
    MCPClient,
    MCPConfig,
    ModelResponseError,
    MultiAgentConfig,
    RateLimitError,
    ResponseAgent,
    SearchAgent,
    StreamingConfig,
    TokenLimitExceededError,
    ToolExecutionError,
)

# Mark all tests in this module to use asyncio backend
pytestmark = pytest.mark.anyio(backends=["asyncio"])

# Prevent accidental real model requests during testing
models.ALLOW_MODEL_REQUESTS = False


class TestStreamingConfig:
    """Tests for StreamingConfig."""

    def test_streaming_config_defaults(self):
        """Test StreamingConfig default values."""
        config = StreamingConfig()
        assert config.enabled is False
        assert config.debounce_ms == 100

    def test_streaming_config_custom(self):
        """Test StreamingConfig with custom values."""
        config = StreamingConfig(enabled=True, debounce_ms=50)
        assert config.enabled is True
        assert config.debounce_ms == 50


class TestMCPConfig:
    """Tests for MCPConfig."""

    def test_mcp_config_defaults(self):
        """Test MCPConfig default values."""
        config = MCPConfig()
        assert config.enabled is False
        assert config.servers == []
        assert config.timeout_seconds == 30

    def test_mcp_config_custom(self):
        """Test MCPConfig with custom values."""
        config = MCPConfig(
            enabled=True,
            servers=[{"name": "test", "command": "test-cmd", "args": "--test"}],
            timeout_seconds=60,
        )
        assert config.enabled is True
        assert len(config.servers) == 1
        assert config.timeout_seconds == 60


class TestMultiAgentConfig:
    """Tests for MultiAgentConfig."""

    def test_multi_agent_config_defaults(self):
        """Test MultiAgentConfig default values."""
        config = MultiAgentConfig()
        assert config.enabled is False
        assert config.orchestration_mode == "sequential"
        assert config.max_agents == 10

    def test_multi_agent_config_custom(self):
        """Test MultiAgentConfig with custom values."""
        config = MultiAgentConfig(
            enabled=True,
            orchestration_mode="concurrent",
            max_agents=5,
        )
        assert config.enabled is True
        assert config.orchestration_mode == "concurrent"
        assert config.max_agents == 5


class TestAIConfig:
    """Tests for AIConfig."""

    def test_ai_config_with_features(self):
        """Test AIConfig with features."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            structured_output_enabled=True,
            output_validators_enabled=True,
            streaming=StreamingConfig(enabled=True),
            mcp=MCPConfig(enabled=True),
            multi_agent=MultiAgentConfig(enabled=True),
        )

        assert config.structured_output_enabled is True
        assert config.output_validators_enabled is True
        assert config.streaming.enabled is True
        assert config.mcp.enabled is True
        assert config.multi_agent.enabled is True


class TestMCPClient:
    """Tests for MCPClient."""

    async def test_mcp_client_initialization(self):
        """Test MCPClient initialization."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)

        assert client.config == config
        assert not client.is_started()
        assert client.get_server_count() == 0

    async def test_mcp_client_start_disabled(self):
        """Test MCPClient start when disabled."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)

        await client.start()
        assert not client.is_started()

    async def test_mcp_client_stats(self):
        """Test MCPClient stats."""
        config = MCPConfig(enabled=False)
        client = MCPClient(config)

        stats = client.get_stats()
        assert stats["enabled"] is False
        assert stats["started"] is False
        assert stats["server_count"] == 0


class TestSpecializedAgents:
    """Tests for specialized agents."""

    def test_search_agent_initialization(self):
        """Test SearchAgent initialization."""
        agent = SearchAgent(model=TestModel())
        assert agent.name == "SearchAgent"
        assert agent.role == "search"

    def test_analysis_agent_initialization(self):
        """Test AnalysisAgent initialization."""
        agent = AnalysisAgent(model=TestModel())
        assert agent.name == "AnalysisAgent"
        assert agent.role == "analysis"

    def test_response_agent_initialization(self):
        """Test ResponseAgent initialization."""
        agent = ResponseAgent(model=TestModel())
        assert agent.name == "ResponseAgent"
        assert agent.role == "response"


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    def test_orchestrator_initialization_disabled(self):
        """Test AgentOrchestrator initialization when disabled."""
        config = MultiAgentConfig(enabled=False)
        orchestrator = AgentOrchestrator(config, model=TestModel())

        assert orchestrator.config == config
        stats = orchestrator.get_stats()
        assert stats["enabled"] is False

    def test_orchestrator_initialization_enabled(self):
        """Test AgentOrchestrator initialization when enabled."""
        config = MultiAgentConfig(enabled=True)
        orchestrator = AgentOrchestrator(config, model=TestModel())

        stats = orchestrator.get_stats()
        assert stats["enabled"] is True
        assert stats["agent_count"] == 10  # all specialized agents
        assert stats["mode"] == "sequential"

    async def test_orchestrator_disabled(self):
        """Test orchestrator when disabled."""
        config = MultiAgentConfig(enabled=False)
        orchestrator = AgentOrchestrator(config, model=TestModel())

        result = await orchestrator.orchestrate("test message")
        assert result == ""


class TestAIAgent:
    """Tests for AIAgent features."""

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    async def test_ai_agent_with_streaming_config(self, mock_planner_agent):
        """Test AIAgent with streaming configuration."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-api-key",  # Fake API key to prevent initialization error
            streaming=StreamingConfig(enabled=True, debounce_ms=50),
        )

        # Override the agent's model with TestModel after initialization
        agent = AIAgent(config)
        with agent._agent.override(model=TestModel()):
            assert agent.config.streaming.enabled is True
            assert agent.config.streaming.debounce_ms == 50

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    async def test_ai_agent_with_mcp_config(self, mock_planner_agent):
        """Test AIAgent with MCP configuration."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-api-key",  # Fake API key to prevent initialization error
            mcp=MCPConfig(enabled=False),
        )

        agent = AIAgent(config)
        with agent._agent.override(model=TestModel()):
            assert agent.mcp_client is not None
            assert not agent.mcp_client.is_started()

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    async def test_ai_agent_with_multi_agent_config(self, mock_planner_agent):
        """Test AIAgent with multi-agent configuration."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-api-key",  # Fake API key to prevent initialization error
            multi_agent=MultiAgentConfig(enabled=False),
        )

        agent = AIAgent(config)
        with agent._agent.override(model=TestModel()):
            assert agent.orchestrator is not None
            stats = agent.orchestrator.get_stats()
            assert stats["enabled"] is False

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    async def test_ai_agent_stats(self, mock_planner_agent):
        """Test AIAgent stats with features."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-api-key",  # Fake API key to prevent initialization error
            structured_output_enabled=True,
            output_validators_enabled=True,
            streaming=StreamingConfig(enabled=True),
            mcp=MCPConfig(enabled=False),
            multi_agent=MultiAgentConfig(enabled=False),
        )

        agent = AIAgent(config)
        with agent._agent.override(model=TestModel()):
            stats = await agent.get_stats()

            assert isinstance(stats["model"], str)
            assert stats["streaming_enabled"] is True
            assert stats["structured_output_enabled"] is True
            assert stats["output_validators_enabled"] is True
            assert "mcp_stats" in stats
            assert "orchestrator_stats" in stats

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    async def test_ai_agent_streaming_chat(self, mock_planner_agent):
        """Test AIAgent streaming chat with TestModel."""

        # Create a custom function model that returns streaming-like responses
        def streaming_response(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart("Hello")])

        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-api-key",  # Fake API key to prevent initialization error
            streaming=StreamingConfig(enabled=True, debounce_ms=10),
        )

        agent = AIAgent(config)
        agent.start()  # Not async

        try:
            with agent._agent.override(model=FunctionModel(streaming_response)):
                chunks = []
                async for chunk in agent.chat_stream("test_user", "Say 'hello' in one word"):
                    chunks.append(chunk)

                # Should receive at least one chunk
                assert len(chunks) > 0
                full_response = "".join(chunks)
                assert len(full_response) > 0

        finally:
            await agent.stop()


class TestAIExceptions:
    """Tests for AI-specific exception classes."""

    def test_ai_service_unavailable_error_records_service(self):
        exc = AIServiceUnavailableError(service="openai")
        assert exc.service == "openai"
        assert "currently unavailable" in str(exc)

    def test_tool_execution_error_includes_original(self):
        original = RuntimeError("boom")
        exc = ToolExecutionError("failed", tool_name="calculator", original_error=original)
        assert exc.tool_name == "calculator"
        assert exc.original_error is original
        assert "failed" in str(exc)

    def test_conversation_not_found_error_message(self):
        exc = ConversationNotFoundError("user-123")
        assert exc.user_id == "user-123"
        assert "user-123" in str(exc)

    def test_model_response_error_captures_payload(self):
        exc = ModelResponseError("invalid", response="bad")
        assert exc.response == "bad"
        assert str(exc) == "invalid"

    def test_token_limit_exceeded_error_details(self):
        exc = TokenLimitExceededError("too many", tokens_used=1500, token_limit=1000)
        assert exc.tokens_used == 1500
        assert exc.token_limit == 1000
        assert "too many" in str(exc)

    def test_rate_limit_error_retry_after(self):
        exc = RateLimitError(retry_after=3.5)
        assert exc.retry_after == 3.5
        assert "Rate limit" in str(exc)

    def test_configuration_error_records_key(self):
        exc = ConfigurationError("missing", config_key="api_key")
        assert exc.config_key == "api_key"
        assert "missing" in str(exc)

    @patch("feishu_webhook_bot.ai.multi_agent.planner.Agent")
    async def test_ai_agent_with_validators(self, mock_planner_agent):
        """Test AIAgent with output validators using TestModel."""
        # TestModel will generate valid responses that pass validation
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-api-key",  # Fake API key to prevent initialization error
            output_validators_enabled=True,
            retry_on_validation_error=True,
            max_retries=2,
        )

        agent = AIAgent(config)
        agent.start()  # Not async

        try:
            with agent._agent.override(model=TestModel()):
                response = await agent.chat("test_user", "What is 2+2?")
                assert len(response) > 0

        finally:
            await agent.stop()
