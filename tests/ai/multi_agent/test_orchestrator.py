"""Tests for AgentOrchestrator.

Tests cover:
- AgentOrchestrator initialization
- Agent registration
- Orchestration modes (sequential, concurrent, hierarchical)
- Statistics
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from feishu_webhook_bot.ai.config import MultiAgentConfig
from feishu_webhook_bot.ai.multi_agent import (
    AgentOrchestrator,
    SpecializedAgent,
)

AGENT_MOCK_PATH = "feishu_webhook_bot.ai.multi_agent.agents.Agent"
ORCHESTRATOR_AGENT_MOCK_PATH = "feishu_webhook_bot.ai.multi_agent.orchestrator.Agent"
PLANNER_AGENT_MOCK_PATH = "feishu_webhook_bot.ai.multi_agent.planner.Agent"


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

        new_search = SpecializedAgent(
            name="NewSearchAgent",
            role="search",
            system_prompt="New search prompt",
        )

        orchestrator.register_agent(new_search)

        assert orchestrator._agents["search"].name == "NewSearchAgent"

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_register_multiple_custom_agents(self, mock_agent, mock_orch, mock_plan):
        """Test registering multiple custom agents."""
        config = MultiAgentConfig(enabled=True)
        orchestrator = AgentOrchestrator(config)

        for i in range(5):
            agent = SpecializedAgent(
                name=f"CustomAgent{i}",
                role=f"custom{i}",
                system_prompt=f"Custom prompt {i}",
            )
            orchestrator.register_agent(agent)

        # Should have 10 default + 5 custom = 15 agents
        assert len(orchestrator._agents) == 15


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

        mock_result = MagicMock()
        mock_result.output = "Test output"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message")

        assert isinstance(result, str)

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

        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(side_effect=Exception("Search error"))
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="sequential")

        assert "Search failed" in result

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    @pytest.mark.anyio
    async def test_sequential_all_steps_called(self, mock_agent, mock_orch, mock_plan):
        """Test sequential orchestration calls all agents in order."""
        config = MultiAgentConfig(enabled=True, orchestration_mode="sequential")

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

        assert len(call_order) == 3
        assert result is not None


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

        mock_result = MagicMock()
        mock_result.output = "Agent output"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="concurrent")

        assert "Agent output" in result

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

        assert result is not None


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

        mock_result = MagicMock()
        mock_result.output = "Coordinator plan"
        mock_result.usage = MagicMock(return_value=None)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent.return_value = mock_agent_instance
        mock_orch.return_value = mock_agent_instance

        orchestrator = AgentOrchestrator(config)

        result = await orchestrator.orchestrate("Test message", mode="hierarchical")

        assert isinstance(result, str)

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

        assert result is not None


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

    @patch(PLANNER_AGENT_MOCK_PATH)
    @patch(ORCHESTRATOR_AGENT_MOCK_PATH)
    @patch(AGENT_MOCK_PATH)
    def test_stats_after_agent_registration(self, mock_agent, mock_orch, mock_plan):
        """Test stats update after agent registration."""
        config = MultiAgentConfig(enabled=True)
        orchestrator = AgentOrchestrator(config)

        initial_count = orchestrator.get_stats()["agent_count"]

        agent = SpecializedAgent(
            name="NewAgent",
            role="new",
            system_prompt="New prompt",
        )
        orchestrator.register_agent(agent)

        new_count = orchestrator.get_stats()["agent_count"]

        assert new_count == initial_count + 1


# ==============================================================================
# Advanced Orchestration Tests
# ==============================================================================


class TestAgentOrchestratorAdvanced:
    """Advanced tests for AgentOrchestrator."""

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

        long_message = "Test " * 1000
        result = await orchestrator.orchestrate(long_message)

        assert result is not None


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
