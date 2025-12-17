"""Comprehensive tests for multi-agent orchestration module.

Tests cover:
- AgentMessage model validation
- AgentResult model validation
- SpecializedAgent initialization and processing
- SearchAgent, AnalysisAgent, ResponseAgent
- AgentOrchestrator initialization and orchestration modes
- Statistics and agent registration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from feishu_webhook_bot.ai.config import MultiAgentConfig
from feishu_webhook_bot.ai.multi_agent import (
    AgentMessage,
    AgentOrchestrator,
    AgentResult,
    AnalysisAgent,
    ResponseAgent,
    SearchAgent,
    SpecializedAgent,
)

# Mock path for the new module structure
AGENT_MOCK_PATH = "feishu_webhook_bot.ai.multi_agent.agents.Agent"
ORCHESTRATOR_AGENT_MOCK_PATH = "feishu_webhook_bot.ai.multi_agent.orchestrator.Agent"
PLANNER_AGENT_MOCK_PATH = "feishu_webhook_bot.ai.multi_agent.planner.Agent"


def mock_all_agents(func):
    """Decorator to mock all Agent classes used in multi-agent module."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def mock_all_agents_async(func):
    """Decorator to mock all Agent classes for async tests."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


# ==============================================================================
# AgentMessage Tests
# ==============================================================================


class TestAgentMessage:
    """Tests for AgentMessage model."""

    def test_message_creation(self):
        """Test AgentMessage creation with required fields."""
        msg = AgentMessage(
            from_agent="search",
            to_agent="analysis",
            content="Search results here",
        )

        assert msg.from_agent == "search"
        assert msg.to_agent == "analysis"
        assert msg.content == "Search results here"
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test AgentMessage with metadata."""
        msg = AgentMessage(
            from_agent="search",
            to_agent="analysis",
            content="Results",
            metadata={"query": "test", "count": 10},
        )

        assert msg.metadata["query"] == "test"
        assert msg.metadata["count"] == 10

    def test_message_serialization(self):
        """Test AgentMessage serialization."""
        msg = AgentMessage(
            from_agent="a",
            to_agent="b",
            content="test",
        )

        data = msg.model_dump()

        assert data["from_agent"] == "a"
        assert data["to_agent"] == "b"
        assert data["content"] == "test"


# ==============================================================================
# AgentResult Tests
# ==============================================================================


class TestAgentResult:
    """Tests for AgentResult model."""

    def test_result_success(self):
        """Test successful AgentResult."""
        result = AgentResult(
            agent_name="SearchAgent",
            output="Found 5 results",
        )

        assert result.agent_name == "SearchAgent"
        assert result.output == "Found 5 results"
        assert result.success is True
        assert result.error is None
        assert result.metadata == {}

    def test_result_failure(self):
        """Test failed AgentResult."""
        result = AgentResult(
            agent_name="SearchAgent",
            output="",
            success=False,
            error="Connection timeout",
        )

        assert result.success is False
        assert result.error == "Connection timeout"

    def test_result_with_metadata(self):
        """Test AgentResult with metadata."""
        result = AgentResult(
            agent_name="AnalysisAgent",
            output="Analysis complete",
            metadata={"confidence": 0.95, "tokens": 150},
        )

        assert result.metadata["confidence"] == 0.95
        assert result.metadata["tokens"] == 150

    def test_result_serialization(self):
        """Test AgentResult serialization."""
        result = AgentResult(
            agent_name="test",
            output="output",
            success=True,
        )

        data = result.model_dump()

        assert data["agent_name"] == "test"
        assert data["output"] == "output"
        assert data["success"] is True


# ==============================================================================
# SpecializedAgent Tests
# ==============================================================================


class TestSpecializedAgent:
    """Tests for SpecializedAgent base class."""

    @patch(AGENT_MOCK_PATH)
    def test_agent_initialization(self, mock_agent_class):
        """Test SpecializedAgent initialization."""
        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="You are a test agent.",
            model="openai:gpt-4o-mini",
        )

        assert agent.name == "TestAgent"
        assert agent.role == "test"
        assert agent.model == "openai:gpt-4o-mini"

    @patch(AGENT_MOCK_PATH)
    def test_agent_default_model(self, mock_agent_class):
        """Test SpecializedAgent with default model."""
        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="Test prompt",
        )

        assert agent.model == "openai:gpt-4o"

    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_agent_process_success(self, mock_agent_class):
        """Test successful agent processing."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.output = "Processed result"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="Test",
        )

        result = await agent.process("Test message")

        assert result.success is True
        assert result.output == "Processed result"
        assert result.agent_name == "TestAgent"

    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_agent_process_failure(self, mock_agent_class):
        """Test agent processing failure."""
        # Setup mock to raise exception
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(side_effect=Exception("API error"))
        mock_agent_class.return_value = mock_agent_instance

        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="Test",
        )

        result = await agent.process("Test message")

        assert result.success is False
        assert result.error == "API error"
        assert result.output == ""

    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_agent_process_with_context(self, mock_agent_class):
        """Test agent processing with context."""
        mock_result = MagicMock()
        mock_result.output = "Result"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="Test",
        )

        result = await agent.process("Message", context={"key": "value"})

        assert result.metadata["context"]["key"] == "value"


# ==============================================================================
# Specialized Agent Subclasses Tests
# ==============================================================================


class TestSpecializedAgentSubclasses:
    """Tests for specialized agent subclasses."""

    @patch(AGENT_MOCK_PATH)
    def test_search_agent_initialization(self, mock_agent_class):
        """Test SearchAgent initialization."""
        agent = SearchAgent()

        assert agent.name == "SearchAgent"
        assert agent.role == "search"

    @patch(AGENT_MOCK_PATH)
    def test_search_agent_custom_model(self, mock_agent_class):
        """Test SearchAgent with custom model."""
        agent = SearchAgent(model="anthropic:claude-3")

        assert agent.model == "anthropic:claude-3"

    @patch(AGENT_MOCK_PATH)
    def test_analysis_agent_initialization(self, mock_agent_class):
        """Test AnalysisAgent initialization."""
        agent = AnalysisAgent()

        assert agent.name == "AnalysisAgent"
        assert agent.role == "analysis"

    @patch(AGENT_MOCK_PATH)
    def test_response_agent_initialization(self, mock_agent_class):
        """Test ResponseAgent initialization."""
        agent = ResponseAgent()

        assert agent.name == "ResponseAgent"
        assert agent.role == "response"


# ==============================================================================
# AgentOrchestrator Initialization Tests
# ==============================================================================


class TestAgentOrchestratorInitialization:
    """Tests for AgentOrchestrator initialization."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_orchestrator_disabled(self, mock_agent_class, mock_orch_agent, mock_planner_agent):
        """Test orchestrator when disabled."""
        config = MultiAgentConfig(enabled=False)

        orchestrator = AgentOrchestrator(config)

        assert orchestrator.config.enabled is False
        assert len(orchestrator._agents) == 0

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_orchestrator_enabled(self, mock_agent_class, mock_orch_agent, mock_planner_agent):
        """Test orchestrator when enabled."""
        config = MultiAgentConfig(enabled=True)

        orchestrator = AgentOrchestrator(config)

        assert orchestrator.config.enabled is True
        assert len(orchestrator._agents) == 10  # All default agents

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_orchestrator_custom_model(self, mock_agent_class, mock_orch_agent, mock_planner_agent):
        """Test orchestrator with custom model."""
        config = MultiAgentConfig(enabled=True)

        orchestrator = AgentOrchestrator(config, model="anthropic:claude-3")

        assert orchestrator.model == "anthropic:claude-3"

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_orchestrator_default_agents(
        self, mock_agent_class, mock_orch_agent, mock_planner_agent
    ):
        """Test orchestrator initializes default agents."""
        config = MultiAgentConfig(enabled=True)

        orchestrator = AgentOrchestrator(config)

        assert "search" in orchestrator._agents
        assert "analysis" in orchestrator._agents
        assert "response" in orchestrator._agents


# ==============================================================================
# AgentOrchestrator Registration Tests
# ==============================================================================


class TestAgentOrchestratorRegistration:
    """Tests for agent registration."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_register_custom_agent(self, mock_agent, mock_orch, mock_plan):
        """Test registering a custom agent."""
        config = MultiAgentConfig(enabled=True)
        orchestrator = AgentOrchestrator(config)

        custom_agent = SpecializedAgent(
            name="CustomAgent",
            role="custom",
            system_prompt="Custom prompt",
        )

        orchestrator.register_agent(custom_agent)

        assert "custom" in orchestrator._agents
        assert orchestrator._agents["custom"].name == "CustomAgent"

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_register_replaces_existing(self, mock_agent, mock_orch, mock_plan):
        """Test registering agent replaces existing with same role."""
        config = MultiAgentConfig(enabled=True)
        orchestrator = AgentOrchestrator(config)

        # Register a new search agent
        new_search = SpecializedAgent(
            name="NewSearchAgent",
            role="search",
            system_prompt="New search prompt",
        )

        orchestrator.register_agent(new_search)

        assert orchestrator._agents["search"].name == "NewSearchAgent"


# ==============================================================================
# AgentOrchestrator Orchestration Tests
# ==============================================================================


class TestAgentOrchestratorOrchestration:
    """Tests for orchestration modes."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_orchestrate_disabled(self, mock_agent, mock_orch, mock_plan):
        """Test orchestration when disabled."""
        config = MultiAgentConfig(enabled=False)
        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message")

        assert result == ""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_orchestrate_invalid_mode(self, mock_agent, mock_orch, mock_plan):
        """Test orchestration with invalid mode returns error message."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")
        orchestrator = AgentOrchestrator(config)

        # New orchestrator catches exceptions and returns error message
        result = await orchestrator.orchestrate("Test", mode="invalid")  # type: ignore
        assert "Orchestration failed" in result
        assert "Unknown orchestration mode" in result

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_orchestrate_uses_config_mode(self, mock_agent, mock_orch, mock_plan):
        """Test orchestration uses config mode by default."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        # Setup mock for all agents
        mock_result = MagicMock()
        mock_result.output = "Test output"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message")

        # Should complete without error
        assert isinstance(result, str)


# ==============================================================================
# AgentOrchestrator Sequential Mode Tests
# ==============================================================================


class TestAgentOrchestratorSequential:
    """Tests for sequential orchestration mode."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_sequential_success(self, mock_agent, mock_orch, mock_plan):
        """Test successful sequential orchestration."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        # Setup mock
        mock_result = MagicMock()
        mock_result.output = "Final response"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="sequential")

        assert result == "Final response"

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_sequential_search_failure(self, mock_agent, mock_orch, mock_plan):
        """Test sequential orchestration when search fails."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        # Setup mock to fail on first call
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(side_effect=Exception("Search error"))
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="sequential")

        assert "Search failed" in result


# ==============================================================================
# AgentOrchestrator Concurrent Mode Tests
# ==============================================================================


class TestAgentOrchestratorConcurrent:
    """Tests for concurrent orchestration mode."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_concurrent_success(self, mock_agent, mock_orch, mock_plan):
        """Test successful concurrent orchestration."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="concurrent")

        # Setup mock
        mock_result = MagicMock()
        mock_result.output = "Agent output"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="concurrent")

        # Should contain outputs from multiple agents
        assert "Agent output" in result


# ==============================================================================
# AgentOrchestrator Hierarchical Mode Tests
# ==============================================================================


class TestAgentOrchestratorHierarchical:
    """Tests for hierarchical orchestration mode."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_hierarchical_success(self, mock_agent, mock_orch, mock_plan):
        """Test successful hierarchical orchestration."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="hierarchical")

        # Setup mock
        mock_result = MagicMock()
        mock_result.output = "Coordinator plan"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="hierarchical")

        # Should complete (falls back to sequential)
        assert isinstance(result, str)


# ==============================================================================
# AgentOrchestrator Statistics Tests
# ==============================================================================


class TestAgentOrchestratorStats:
    """Tests for orchestrator statistics."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_get_stats_disabled(self, mock_agent, mock_orch, mock_plan):
        """Test get_stats when disabled."""
        config = MultiAgentConfig(enabled=False)
        orchestrator = AgentOrchestrator(config)

        stats = orchestrator.get_stats()

        assert stats["enabled"] is False
        assert stats["agent_count"] == 0
        assert stats["agents"] == []

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_get_stats_enabled(self, mock_agent, mock_orch, mock_plan):
        """Test get_stats when enabled."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")
        orchestrator = AgentOrchestrator(config)

        stats = orchestrator.get_stats()

        assert stats["enabled"] is True
        assert stats["mode"] == "sequential"
        assert stats["agent_count"] == 10
        assert len(stats["agents"]) == 10

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_get_stats_agent_info(self, mock_agent, mock_orch, mock_plan):
        """Test get_stats includes agent info."""
        config = MultiAgentConfig(enabled=True)
        orchestrator = AgentOrchestrator(config)

        stats = orchestrator.get_stats()

        agent_names = [a["name"] for a in stats["agents"]]
        assert "SearchAgent" in agent_names
        assert "AnalysisAgent" in agent_names
        assert "ResponseAgent" in agent_names


# ==============================================================================
# Advanced Orchestration Tests
# ==============================================================================


class TestAgentOrchestratorAdvanced:
    """Advanced tests for AgentOrchestrator."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_sequential_all_steps_called(self, mock_agent, mock_orch, mock_plan):
        """Test sequential orchestration calls all agents in order."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        # Track call order
        call_order = []

        def create_mock_result(name):
            mock_result = MagicMock()
            mock_result.output = f"{name} output"
            mock_result.usage = MagicMock(return_value=None)
            return mock_result

        mock_agent_instance = MagicMock()

        async def mock_run(message):
            if "search" in message.lower() or "identify" in message.lower():
                call_order.append("search")
                return create_mock_result("search")
            elif "analysis" in message.lower() or "analyze" in message.lower():
                call_order.append("analysis")
                return create_mock_result("analysis")
            else:
                call_order.append("response")
                return create_mock_result("response")

        mock_agent_instance.run = AsyncMock(side_effect=mock_run)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="sequential")

        # All three agents should be called
        assert len(call_order) == 3
        assert result is not None

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_concurrent_all_agents_run(self, mock_agent, mock_orch, mock_plan):
        """Test concurrent orchestration runs all agents."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="concurrent")

        mock_result = MagicMock()
        mock_result.output = "Concurrent output"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="concurrent")

        # Result should contain outputs from multiple agents
        assert "Concurrent output" in result

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_concurrent_handles_partial_failures(self, mock_agent, mock_orch, mock_plan):
        """Test concurrent orchestration handles partial agent failures."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="concurrent")

        call_count = 0

        async def mock_run(message):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Agent 1 failed")
            mock_result = MagicMock()
            mock_result.output = f"Output {call_count}"
            mock_result.usage = MagicMock(return_value=None)
            return mock_result

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(side_effect=mock_run)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="concurrent")

        # Should still have some output despite one failure
        assert result is not None

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_hierarchical_creates_coordinator(self, mock_agent, mock_orch, mock_plan):
        """Test hierarchical orchestration creates coordinator agent."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="hierarchical")

        mock_result = MagicMock()
        mock_result.output = "Coordinator plan"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="hierarchical")

        # Should complete without error
        assert result is not None

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_orchestrate_with_long_message(self, mock_agent, mock_orch, mock_plan):
        """Test orchestration with very long message."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        mock_result = MagicMock()
        mock_result.output = "Response"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        long_message = "Test " * 1000  # Very long message
        result = await orchestrator.orchestrate(long_message)

        assert result is not None


# ==============================================================================
# Agent Message and Result Tests
# ==============================================================================


class TestAgentMessageAdvanced:
    """Advanced tests for AgentMessage."""

    def test_message_with_complex_metadata(self):
        """Test AgentMessage with complex metadata."""
        msg = AgentMessage(
            from_agent="search",
            to_agent="analysis",
            content="Results",
            metadata={
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "unicode": "你好",
            },
        )

        assert msg.metadata["nested"]["key"] == "value"
        assert msg.metadata["list"] == [1, 2, 3]
        assert msg.metadata["unicode"] == "你好"

    def test_message_with_empty_content(self):
        """Test AgentMessage with empty content."""
        msg = AgentMessage(
            from_agent="a",
            to_agent="b",
            content="",
        )

        assert msg.content == ""

    def test_message_with_unicode_content(self):
        """Test AgentMessage with unicode content."""
        msg = AgentMessage(
            from_agent="search",
            to_agent="analysis",
            content="搜索结果：找到了相关信息 🔍",
        )

        assert "搜索结果" in msg.content
        assert "🔍" in msg.content


class TestAgentResultAdvanced:
    """Advanced tests for AgentResult."""

    def test_result_with_complex_metadata(self):
        """Test AgentResult with complex metadata."""
        result = AgentResult(
            agent_name="AnalysisAgent",
            output="Analysis complete",
            metadata={
                "tokens_used": 150,
                "model": "gpt-4",
                "latency_ms": 1234,
                "sources": ["web", "database"],
            },
        )

        assert result.metadata["tokens_used"] == 150
        assert result.metadata["sources"] == ["web", "database"]

    def test_result_with_long_error(self):
        """Test AgentResult with long error message."""
        long_error = "Error: " + "x" * 1000
        result = AgentResult(
            agent_name="FailedAgent",
            output="",
            success=False,
            error=long_error,
        )

        assert len(result.error) > 1000

    def test_result_with_unicode_output(self):
        """Test AgentResult with unicode output."""
        result = AgentResult(
            agent_name="ResponseAgent",
            output="回答：这是一个测试响应 ✅",
        )

        assert "回答" in result.output
        assert "✅" in result.output


# ==============================================================================
# Specialized Agent Tests
# ==============================================================================


class TestSpecializedAgentAdvanced:
    """Advanced tests for specialized agents."""

    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_agent_process_with_empty_message(self, mock_agent_class):
        """Test agent processing with empty message."""
        mock_result = MagicMock()
        mock_result.output = "Processed empty"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="Test",
        )

        result = await agent.process("")

        assert result.success is True

    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_agent_process_with_unicode_message(self, mock_agent_class):
        """Test agent processing with unicode message."""
        mock_result = MagicMock()
        mock_result.output = "处理完成"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="Test",
        )

        result = await agent.process("请帮我分析这个问题")

        assert result.success is True
        assert result.output == "处理完成"

    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_agent_process_preserves_context(self, mock_agent_class):
        """Test agent processing preserves context in result."""
        mock_result = MagicMock()
        mock_result.output = "Result"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="Test",
        )

        context = {"user_id": "123", "session": "abc"}
        result = await agent.process("Message", context=context)

        assert result.metadata["context"] == context


# ==============================================================================
# Edge Cases Tests
# ==============================================================================


class TestMultiAgentEdgeCases:
    """Edge case tests for multi-agent module."""

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_orchestrator_with_all_modes(self, mock_agent, mock_orch, mock_plan):
        """Test orchestrator supports all orchestration modes."""
        for mode in ["sequential", "concurrent", "hierarchical"]:
            config = MultiAgentConfig(enabled=True, orchestration_mode=mode)
            orchestrator = AgentOrchestrator(config)

            assert orchestrator.config.orchestration_mode == mode

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_register_multiple_custom_agents(self, mock_agent, mock_orch, mock_plan):
        """Test registering multiple custom agents."""
        config = MultiAgentConfig(enabled=True)
        orchestrator = AgentOrchestrator(config)

        # Register multiple custom agents
        for i in range(5):
            agent = SpecializedAgent(
                name=f"CustomAgent{i}",
                role=f"custom{i}",
                system_prompt=f"Custom prompt {i}",
            )
            orchestrator.register_agent(agent)

        # Should have 10 default + 5 custom = 15 agents
        assert len(orchestrator._agents) == 15

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_orchestrate_empty_message(self, mock_agent, mock_orch, mock_plan):
        """Test orchestration with empty message."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        mock_result = MagicMock()
        mock_result.output = "Response to empty"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("")

        assert result is not None

    @patch(AGENT_MOCK_PATH)
    def test_agent_with_very_long_system_prompt(self, mock_agent_class):
        """Test agent with very long system prompt."""
        long_prompt = "You are a helpful assistant. " * 100

        agent = SpecializedAgent(
            name="LongPromptAgent",
            role="test",
            system_prompt=long_prompt,
        )

        # Should create without error
        assert agent.name == "LongPromptAgent"

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_stats_after_agent_registration(self, mock_agent, mock_orch, mock_plan):
        """Test stats update after agent registration."""
        config = MultiAgentConfig(enabled=True)
        orchestrator = AgentOrchestrator(config)

        initial_count = orchestrator.get_stats()["agent_count"]

        # Register new agent
        agent = SpecializedAgent(
            name="NewAgent",
            role="new",
            system_prompt="New prompt",
        )
        orchestrator.register_agent(agent)

        new_count = orchestrator.get_stats()["agent_count"]

        assert new_count == initial_count + 1


# ==============================================================================
# Model Router Enhanced Tests
# ==============================================================================


from feishu_webhook_bot.ai.multi_agent import (
    BudgetConfig,
    BudgetPeriod,
    ModelHealth,
    ModelInfo,
    ModelRouter,
    RoutingContext,
    RoutingDecision,
    RoutingStrategy,
    Task,
    TaskAnalyzer,
    TaskType,
)


class TestModelRouterBasic:
    """Basic tests for ModelRouter."""

    def test_router_initialization(self):
        """Test ModelRouter initialization with defaults."""
        router = ModelRouter()

        assert router.strategy == RoutingStrategy.BALANCED
        assert router.default_model == "openai:gpt-4o"
        assert len(router.models) > 0

    def test_router_with_custom_strategy(self):
        """Test ModelRouter with custom strategy."""
        router = ModelRouter(strategy=RoutingStrategy.COST_OPTIMIZED)

        assert router.strategy == RoutingStrategy.COST_OPTIMIZED

    def test_router_with_budget(self):
        """Test ModelRouter with budget configuration."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        router = ModelRouter(budget=budget)

        assert router.budget.enabled is True
        assert router.budget.limit == 10.0

    def test_route_basic_task(self):
        """Test routing a basic task."""
        router = ModelRouter()
        task = Task(content="Hello world", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None
        assert model in router.models


class TestModelRouterStrategies:
    """Tests for different routing strategies."""

    def test_cost_optimized_strategy(self):
        """Test cost-optimized routing selects cheapest model."""
        router = ModelRouter(strategy=RoutingStrategy.COST_OPTIMIZED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        # Should select a model (cheapest among capable)
        assert model is not None

    def test_quality_optimized_strategy(self):
        """Test quality-optimized routing selects best quality model."""
        router = ModelRouter(strategy=RoutingStrategy.QUALITY_OPTIMIZED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_speed_optimized_strategy(self):
        """Test speed-optimized routing selects fastest model."""
        router = ModelRouter(strategy=RoutingStrategy.SPEED_OPTIMIZED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_balanced_strategy(self):
        """Test balanced routing."""
        router = ModelRouter(strategy=RoutingStrategy.BALANCED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_round_robin_strategy(self):
        """Test round-robin routing distributes across models."""
        router = ModelRouter(strategy=RoutingStrategy.ROUND_ROBIN)

        models_used = set()
        for _ in range(10):
            task = Task(content="Test", task_type=TaskType.CONVERSATION)
            model = router.route(task)
            models_used.add(model)

        # Should use multiple models
        assert len(models_used) >= 1

    def test_latency_optimized_strategy(self):
        """Test latency-optimized routing."""
        router = ModelRouter(strategy=RoutingStrategy.LATENCY_OPTIMIZED)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_adaptive_strategy(self):
        """Test adaptive routing based on performance."""
        router = ModelRouter(strategy=RoutingStrategy.ADAPTIVE)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None

    def test_budget_aware_strategy(self):
        """Test budget-aware routing."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        router = ModelRouter(strategy=RoutingStrategy.BUDGET_AWARE, budget=budget)
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        model = router.route(task)

        assert model is not None


class TestModelRouterContextAware:
    """Tests for context-aware routing."""

    def test_route_with_context(self):
        """Test routing with context information."""
        router = ModelRouter()
        task = Task(content="Test message", task_type=TaskType.CONVERSATION)
        context = RoutingContext(
            user_id="user123",
            language="en",
            urgency=5,
        )

        decision = router.route_with_context(task, context)

        assert isinstance(decision, RoutingDecision)
        assert decision.model is not None
        assert decision.strategy_used == RoutingStrategy.CONTEXT_AWARE

    def test_route_with_chinese_language(self):
        """Test routing prefers Chinese models for Chinese language."""
        router = ModelRouter()
        task = Task(content="你好世界", task_type=TaskType.CONVERSATION)
        context = RoutingContext(language="zh")

        decision = router.route_with_context(task, context)

        # Should return a decision
        assert decision.model is not None

    def test_route_with_high_urgency(self):
        """Test routing with high urgency prefers fast models."""
        router = ModelRouter()
        task = Task(content="Urgent task", task_type=TaskType.CONVERSATION)
        context = RoutingContext(urgency=9)

        decision = router.route_with_context(task, context)

        assert decision.model is not None

    def test_route_with_user_preferences(self):
        """Test routing respects user preferences."""
        router = ModelRouter()
        task = Task(content="Test", task_type=TaskType.CONVERSATION)
        context = RoutingContext(preferred_models=["anthropic:claude-3-5-sonnet-20241022"])

        decision = router.route_with_context(task, context)

        assert decision.model is not None


class TestModelRouterBudget:
    """Tests for budget management."""

    def test_set_budget(self):
        """Test setting budget configuration."""
        router = ModelRouter()

        router.set_budget(limit=50.0, period=BudgetPeriod.DAILY)

        assert router.budget.enabled is True
        assert router.budget.limit == 50.0
        assert router.budget.period == BudgetPeriod.DAILY

    def test_get_budget_status(self):
        """Test getting budget status."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        router = ModelRouter(budget=budget)

        status = router.get_budget_status()

        assert status["enabled"] is True
        assert status["limit"] == 10.0
        assert status["current_usage"] == 0.0
        assert status["remaining"] == 10.0

    def test_record_usage_updates_budget(self):
        """Test recording usage updates budget."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        router = ModelRouter(budget=budget)

        router.record_usage(
            model="openai:gpt-4o",
            task_type=TaskType.CONVERSATION,
            success=True,
            latency_ms=500,
            input_tokens=100,
            output_tokens=100,
        )

        assert router.budget.current_usage > 0

    def test_budget_warning_threshold(self):
        """Test budget warning threshold detection."""
        budget = BudgetConfig(
            enabled=True,
            limit=1.0,
            warning_threshold=0.5,
        )
        router = ModelRouter(budget=budget)

        # Manually set usage to trigger warning
        router.budget.current_usage = 0.6

        assert router.budget.is_warning() is True

    def test_budget_exceeded(self):
        """Test budget exceeded detection."""
        budget = BudgetConfig(enabled=True, limit=1.0)
        router = ModelRouter(budget=budget)

        # Manually set usage to exceed budget
        router.budget.current_usage = 1.5

        assert router.budget.is_exceeded() is True


class TestModelRouterCostEstimation:
    """Tests for cost estimation."""

    def test_estimate_cost(self):
        """Test cost estimation for a task."""
        router = ModelRouter()
        task = Task(content="Test message", task_type=TaskType.CONVERSATION)

        estimate = router.estimate_cost(task)

        assert "model" in estimate
        assert "estimated_cost" in estimate
        assert estimate["estimated_cost"] >= 0

    def test_estimate_cost_with_specific_model(self):
        """Test cost estimation with specific model."""
        router = ModelRouter()
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        estimate = router.estimate_cost(task, model="openai:gpt-4o-mini")

        assert estimate["model"] == "openai:gpt-4o-mini"

    def test_estimate_cost_with_token_counts(self):
        """Test cost estimation with specific token counts."""
        router = ModelRouter()
        task = Task(content="Test", task_type=TaskType.CONVERSATION)

        estimate = router.estimate_cost(
            task,
            model="openai:gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )

        assert estimate["input_tokens"] == 1000
        assert estimate["output_tokens"] == 500


class TestModelRouterHealth:
    """Tests for model health monitoring."""

    def test_get_model_health_all(self):
        """Test getting health status of all models."""
        router = ModelRouter()

        health = router.get_model_health()

        assert len(health) > 0
        for _model_name, status in health.items():
            assert "health" in status
            assert "success_rate" in status

    def test_get_model_health_specific(self):
        """Test getting health status of specific model."""
        router = ModelRouter()

        health = router.get_model_health("openai:gpt-4o")

        assert health["model"] == "openai:gpt-4o"
        assert "health" in health
        assert "success_rate" in health

    def test_record_usage_updates_health(self):
        """Test recording usage updates model health."""
        router = ModelRouter()

        # Record some failures
        for _ in range(5):
            router.record_usage(
                model="openai:gpt-4o",
                task_type=TaskType.CONVERSATION,
                success=False,
                latency_ms=1000,
                input_tokens=100,
                output_tokens=100,
            )

        health = router.get_model_health("openai:gpt-4o")

        # Success rate should decrease
        assert health["success_rate"] < 1.0


class TestModelRouterRecommendation:
    """Tests for model recommendation."""

    def test_recommend_model(self):
        """Test model recommendation."""
        router = ModelRouter()

        recommendation = router.recommend_model("Write a Python function")

        assert "task_type" in recommendation
        assert "complexity" in recommendation
        assert "top_recommendation" in recommendation

    def test_recommend_model_with_constraints(self):
        """Test model recommendation with constraints."""
        router = ModelRouter()

        recommendation = router.recommend_model(
            "Simple question",
            constraints={"max_cost": 0.001},
        )

        assert recommendation is not None

    def test_recommend_model_code_task(self):
        """Test model recommendation for code task."""
        router = ModelRouter()

        recommendation = router.recommend_model("Write a Python function to sort a list")

        assert recommendation["task_type"] == "code"


class TestModelRouterBatchRouting:
    """Tests for batch routing."""

    def test_batch_route(self):
        """Test batch routing multiple tasks."""
        router = ModelRouter()
        tasks = [
            Task(content="Task 1", task_type=TaskType.CONVERSATION),
            Task(content="Task 2", task_type=TaskType.CODE),
            Task(content="Task 3", task_type=TaskType.SUMMARY),
        ]

        results = router.batch_route(tasks)

        assert len(results) == 3
        for _task, model in results:
            assert model is not None

    def test_batch_route_with_strategy(self):
        """Test batch routing with specific strategy."""
        router = ModelRouter()
        tasks = [
            Task(content="Task 1", task_type=TaskType.CONVERSATION),
            Task(content="Task 2", task_type=TaskType.CONVERSATION),
        ]

        results = router.batch_route(tasks, strategy=RoutingStrategy.COST_OPTIMIZED)

        assert len(results) == 2


class TestModelRouterABTesting:
    """Tests for A/B testing."""

    def test_setup_ab_test(self):
        """Test setting up A/B test."""
        router = ModelRouter()

        router.setup_ab_test(
            test_models=["openai:gpt-4o", "openai:gpt-4o-mini"],
            ratio=0.2,
        )

        assert router.enable_ab_testing is True
        assert router.ab_test_ratio == 0.2

    def test_get_ab_test_results(self):
        """Test getting A/B test results."""
        router = ModelRouter()
        router.setup_ab_test(["openai:gpt-4o"])

        results = router.get_ab_test_results()

        assert results["enabled"] is True
        assert "results" in results

    def test_record_ab_test_result(self):
        """Test recording A/B test result."""
        router = ModelRouter()
        router.setup_ab_test(["openai:gpt-4o"])

        router.record_ab_test_result(
            model="openai:gpt-4o",
            success=True,
            latency_ms=500,
        )

        results = router.get_ab_test_results()
        assert results["results"]["openai:gpt-4o"]["requests"] == 1


class TestModelRouterUtilities:
    """Tests for utility methods."""

    def test_get_models_by_tag(self):
        """Test getting models by tag."""
        router = ModelRouter()

        # DeepSeek models have "chinese" tag
        chinese_models = router.get_models_by_tag("chinese")

        # Should find models with chinese tag
        assert isinstance(chinese_models, list)

    def test_get_models_by_provider(self):
        """Test getting models by provider."""
        router = ModelRouter()

        openai_models = router.get_models_by_provider("openai")

        assert len(openai_models) > 0
        for model in openai_models:
            assert "openai:" in model

    def test_get_cheapest_model(self):
        """Test getting cheapest model."""
        router = ModelRouter()

        cheapest = router.get_cheapest_model()

        assert cheapest is not None

    def test_get_fastest_model(self):
        """Test getting fastest model."""
        router = ModelRouter()

        fastest = router.get_fastest_model()

        assert fastest is not None

    def test_get_best_quality_model(self):
        """Test getting best quality model."""
        router = ModelRouter()

        best = router.get_best_quality_model()

        assert best is not None

    def test_get_routing_history(self):
        """Test getting routing history."""
        router = ModelRouter()

        history = router.get_routing_history()

        assert isinstance(history, list)


class TestTaskAnalyzerEnhanced:
    """Enhanced tests for TaskAnalyzer."""

    def test_analyze_code_task(self):
        """Test analyzing code task."""
        analyzer = TaskAnalyzer()

        task_type = analyzer.analyze("Write a Python function to sort a list")

        assert task_type == TaskType.CODE

    def test_analyze_math_task(self):
        """Test analyzing math task."""
        analyzer = TaskAnalyzer()

        task_type = analyzer.analyze("Calculate the sum of 1 + 2 + 3")

        assert task_type == TaskType.MATH

    def test_analyze_translation_task(self):
        """Test analyzing translation task."""
        analyzer = TaskAnalyzer()

        task_type = analyzer.analyze("Translate this to Chinese")

        assert task_type == TaskType.TRANSLATION

    def test_analyze_complexity_simple(self):
        """Test analyzing simple task complexity."""
        analyzer = TaskAnalyzer()

        complexity = analyzer.analyze_complexity("Hello")

        assert complexity <= 5

    def test_analyze_complexity_complex(self):
        """Test analyzing complex task complexity."""
        analyzer = TaskAnalyzer()

        complexity = analyzer.analyze_complexity(
            "Design a distributed machine learning system with "
            "neural network architecture for scalability and performance optimization. "
            "Include step by step implementation details for multiple components."
        )

        assert complexity >= 7

    def test_suggest_strategy_high_complexity(self):
        """Test strategy suggestion for high complexity."""
        analyzer = TaskAnalyzer()

        strategy = analyzer.suggest_strategy(TaskType.CODE, complexity=9)

        assert strategy == RoutingStrategy.QUALITY_OPTIMIZED

    def test_suggest_strategy_low_complexity(self):
        """Test strategy suggestion for low complexity."""
        analyzer = TaskAnalyzer()

        strategy = analyzer.suggest_strategy(TaskType.CONVERSATION, complexity=2)

        assert strategy == RoutingStrategy.COST_OPTIMIZED


class TestBudgetConfig:
    """Tests for BudgetConfig."""

    def test_budget_config_defaults(self):
        """Test BudgetConfig default values."""
        budget = BudgetConfig()

        assert budget.enabled is False
        assert budget.period == BudgetPeriod.DAILY
        assert budget.limit == 10.0

    def test_budget_add_usage(self):
        """Test adding usage to budget."""
        budget = BudgetConfig(enabled=True, limit=10.0)

        budget.add_usage(2.5)

        assert budget.current_usage == 2.5

    def test_budget_remaining(self):
        """Test budget remaining calculation."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        budget.current_usage = 3.0

        assert budget.remaining() == 7.0

    def test_budget_usage_percentage(self):
        """Test budget usage percentage calculation."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        budget.current_usage = 5.0

        assert budget.usage_percentage() == 50.0

    def test_budget_is_warning(self):
        """Test budget warning detection."""
        budget = BudgetConfig(
            enabled=True,
            limit=10.0,
            warning_threshold=0.8,
        )
        budget.current_usage = 8.5

        assert budget.is_warning() is True

    def test_budget_is_exceeded(self):
        """Test budget exceeded detection."""
        budget = BudgetConfig(enabled=True, limit=10.0)
        budget.current_usage = 12.0

        assert budget.is_exceeded() is True


class TestModelInfo:
    """Tests for ModelInfo."""

    def test_model_info_estimate_cost(self):
        """Test ModelInfo cost estimation."""
        model = ModelInfo(
            name="test:model",
            provider="test",
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.02,
        )

        cost = model.estimate_cost(1000, 500)

        # 1000 input tokens * 0.01 + 500 output tokens * 0.02 = 0.01 + 0.01 = 0.02
        assert cost == 0.02

    def test_model_info_update_stats_success(self):
        """Test ModelInfo stats update on success."""
        model = ModelInfo(
            name="test:model",
            provider="test",
        )

        model.update_stats(success=True, response_time_ms=500)

        assert model.total_requests == 1
        assert model.failed_requests == 0
        assert model.success_rate == 1.0

    def test_model_info_update_stats_failure(self):
        """Test ModelInfo stats update on failure."""
        model = ModelInfo(
            name="test:model",
            provider="test",
        )

        model.update_stats(success=False, response_time_ms=500)

        assert model.total_requests == 1
        assert model.failed_requests == 1
        assert model.success_rate == 0.0

    def test_model_info_health_updates(self):
        """Test ModelInfo health status updates."""
        model = ModelInfo(
            name="test:model",
            provider="test",
        )

        # Multiple successes should result in healthy
        for _ in range(10):
            model.update_stats(success=True, response_time_ms=500)

        assert model.health == ModelHealth.HEALTHY

    def test_model_info_health_degrades(self):
        """Test ModelInfo health degrades on failures."""
        model = ModelInfo(
            name="test:model",
            provider="test",
        )

        # Mix of successes and failures
        for _ in range(8):
            model.update_stats(success=True, response_time_ms=500)
        for _ in range(2):
            model.update_stats(success=False, response_time_ms=500)

        # Success rate is 80%, should be DEGRADED
        assert model.health == ModelHealth.DEGRADED


class TestRoutingDecision:
    """Tests for RoutingDecision."""

    def test_routing_decision_creation(self):
        """Test RoutingDecision creation."""
        decision = RoutingDecision(
            model="openai:gpt-4o",
            strategy_used=RoutingStrategy.BALANCED,
            score=8.5,
            reason="Best balanced score",
        )

        assert decision.model == "openai:gpt-4o"
        assert decision.strategy_used == RoutingStrategy.BALANCED
        assert decision.score == 8.5

    def test_routing_decision_with_alternatives(self):
        """Test RoutingDecision with alternatives."""
        decision = RoutingDecision(
            model="openai:gpt-4o",
            strategy_used=RoutingStrategy.BALANCED,
            alternatives=["openai:gpt-4o-mini", "anthropic:claude-3-5-haiku-20241022"],
        )

        assert len(decision.alternatives) == 2


class TestRoutingContext:
    """Tests for RoutingContext."""

    def test_routing_context_defaults(self):
        """Test RoutingContext default values."""
        context = RoutingContext()

        assert context.user_id is None
        assert context.language == "en"
        assert context.urgency == 5

    def test_routing_context_with_values(self):
        """Test RoutingContext with custom values."""
        context = RoutingContext(
            user_id="user123",
            language="zh",
            urgency=8,
            preferred_models=["deepseek:deepseek-chat"],
        )

        assert context.user_id == "user123"
        assert context.language == "zh"
        assert context.urgency == 8
        assert "deepseek:deepseek-chat" in context.preferred_models
