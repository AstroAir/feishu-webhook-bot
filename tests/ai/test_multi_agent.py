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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_agent_default_model(self, mock_agent_class):
        """Test SpecializedAgent with default model."""
        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="Test prompt",
        )

        assert agent.model == "openai:gpt-4o"

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_search_agent_initialization(self, mock_agent_class):
        """Test SearchAgent initialization."""
        agent = SearchAgent()

        assert agent.name == "SearchAgent"
        assert agent.role == "search"

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_search_agent_custom_model(self, mock_agent_class):
        """Test SearchAgent with custom model."""
        agent = SearchAgent(model="anthropic:claude-3")

        assert agent.model == "anthropic:claude-3"

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_analysis_agent_initialization(self, mock_agent_class):
        """Test AnalysisAgent initialization."""
        agent = AnalysisAgent()

        assert agent.name == "AnalysisAgent"
        assert agent.role == "analysis"

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_orchestrator_disabled(self, mock_agent_class):
        """Test orchestrator when disabled."""
        config = MultiAgentConfig(enabled=False)

        orchestrator = AgentOrchestrator(config)

        assert orchestrator.config.enabled is False
        assert len(orchestrator._agents) == 0

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_orchestrator_enabled(self, mock_agent_class):
        """Test orchestrator when enabled."""
        config = MultiAgentConfig(enabled=True)

        orchestrator = AgentOrchestrator(config)

        assert orchestrator.config.enabled is True
        assert len(orchestrator._agents) == 3  # search, analysis, response

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_orchestrator_custom_model(self, mock_agent_class):
        """Test orchestrator with custom model."""
        config = MultiAgentConfig(enabled=True)

        orchestrator = AgentOrchestrator(config, model="anthropic:claude-3")

        assert orchestrator.model == "anthropic:claude-3"

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_orchestrator_default_agents(self, mock_agent_class):
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_register_custom_agent(self, mock_agent_class):
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_register_replaces_existing(self, mock_agent_class):
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_orchestrate_disabled(self, mock_agent_class):
        """Test orchestration when disabled."""
        config = MultiAgentConfig(enabled=False)
        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message")

        assert result == ""

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_orchestrate_invalid_mode(self, mock_agent_class):
        """Test orchestration with invalid mode."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")
        orchestrator = AgentOrchestrator(config)

        with pytest.raises(ValueError, match="Unknown orchestration mode"):
            await orchestrator.orchestrate("Test", mode="invalid")  # type: ignore

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_orchestrate_uses_config_mode(self, mock_agent_class):
        """Test orchestration uses config mode by default."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        # Setup mock for all agents
        mock_result = MagicMock()
        mock_result.output = "Test output"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message")

        # Should complete without error
        assert isinstance(result, str)


# ==============================================================================
# AgentOrchestrator Sequential Mode Tests
# ==============================================================================


class TestAgentOrchestratorSequential:
    """Tests for sequential orchestration mode."""

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_sequential_success(self, mock_agent_class):
        """Test successful sequential orchestration."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        # Setup mock
        mock_result = MagicMock()
        mock_result.output = "Final response"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="sequential")

        assert result == "Final response"

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_sequential_search_failure(self, mock_agent_class):
        """Test sequential orchestration when search fails."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        # Setup mock to fail on first call
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(side_effect=Exception("Search error"))
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="sequential")

        assert "Search failed" in result


# ==============================================================================
# AgentOrchestrator Concurrent Mode Tests
# ==============================================================================


class TestAgentOrchestratorConcurrent:
    """Tests for concurrent orchestration mode."""

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_concurrent_success(self, mock_agent_class):
        """Test successful concurrent orchestration."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="concurrent")

        # Setup mock
        mock_result = MagicMock()
        mock_result.output = "Agent output"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="concurrent")

        # Should contain outputs from multiple agents
        assert "Agent output" in result


# ==============================================================================
# AgentOrchestrator Hierarchical Mode Tests
# ==============================================================================


class TestAgentOrchestratorHierarchical:
    """Tests for hierarchical orchestration mode."""

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_hierarchical_success(self, mock_agent_class):
        """Test successful hierarchical orchestration."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="hierarchical")

        # Setup mock
        mock_result = MagicMock()
        mock_result.output = "Coordinator plan"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="hierarchical")

        # Should complete (falls back to sequential)
        assert isinstance(result, str)


# ==============================================================================
# AgentOrchestrator Statistics Tests
# ==============================================================================


class TestAgentOrchestratorStats:
    """Tests for orchestrator statistics."""

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_get_stats_disabled(self, mock_agent_class):
        """Test get_stats when disabled."""
        config = MultiAgentConfig(enabled=False)
        orchestrator = AgentOrchestrator(config)

        stats = orchestrator.get_stats()

        assert stats["enabled"] is False
        assert stats["agent_count"] == 0
        assert stats["agents"] == []

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_get_stats_enabled(self, mock_agent_class):
        """Test get_stats when enabled."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")
        orchestrator = AgentOrchestrator(config)

        stats = orchestrator.get_stats()

        assert stats["enabled"] is True
        assert stats["mode"] == "sequential"
        assert stats["agent_count"] == 3
        assert len(stats["agents"]) == 3

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_get_stats_agent_info(self, mock_agent_class):
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_sequential_all_steps_called(self, mock_agent_class):
        """Test sequential orchestration calls all agents in order."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        # Track call order
        call_order = []

        def create_mock_result(name):
            mock_result = MagicMock()
            mock_result.output = f"{name} output"
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
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="sequential")

        # All three agents should be called
        assert len(call_order) == 3
        assert result is not None

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_concurrent_all_agents_run(self, mock_agent_class):
        """Test concurrent orchestration runs all agents."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="concurrent")

        mock_result = MagicMock()
        mock_result.output = "Concurrent output"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="concurrent")

        # Result should contain outputs from multiple agents
        assert "Concurrent output" in result

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_concurrent_handles_partial_failures(self, mock_agent_class):
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
            return mock_result

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(side_effect=mock_run)
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="concurrent")

        # Should still have some output despite one failure
        assert result is not None

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_hierarchical_creates_coordinator(self, mock_agent_class):
        """Test hierarchical orchestration creates coordinator agent."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="hierarchical")

        mock_result = MagicMock()
        mock_result.output = "Coordinator plan"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="hierarchical")

        # Should complete without error
        assert result is not None

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_orchestrate_with_long_message(self, mock_agent_class):
        """Test orchestration with very long message."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        mock_result = MagicMock()
        mock_result.output = "Response"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_orchestrator_with_all_modes(self, mock_agent_class):
        """Test orchestrator supports all orchestration modes."""
        for mode in ["sequential", "concurrent", "hierarchical"]:
            config = MultiAgentConfig(enabled=True, orchestration_mode=mode)
            orchestrator = AgentOrchestrator(config)

            assert orchestrator.config.orchestration_mode == mode

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_register_multiple_custom_agents(self, mock_agent_class):
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

        # Should have 3 default + 5 custom = 8 agents
        assert len(orchestrator._agents) == 8

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    @pytest.mark.anyio
    async def test_orchestrate_empty_message(self, mock_agent_class):
        """Test orchestration with empty message."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

        mock_result = MagicMock()
        mock_result.output = "Response to empty"
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("")

        assert result is not None

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
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

    @patch("feishu_webhook_bot.ai.multi_agent.Agent")
    def test_stats_after_agent_registration(self, mock_agent_class):
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
