"""Tests for specialized agents.

Tests cover:
- SpecializedAgent base class
- SearchAgent, AnalysisAgent, ResponseAgent
- CodeAgent, SummaryAgent, TranslationAgent
- ReasoningAgent, PlanningAgent, CreativeAgent, MathAgent
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from feishu_webhook_bot.ai.multi_agent import (
    AnalysisAgent,
    ResponseAgent,
    SearchAgent,
    SpecializedAgent,
)
from feishu_webhook_bot.ai.multi_agent.agents import (
    CodeAgent,
    CreativeAgent,
    MathAgent,
    PlanningAgent,
    ReasoningAgent,
    SummaryAgent,
    TranslationAgent,
)
from feishu_webhook_bot.ai.multi_agent.base import AgentCapability

AGENT_MOCK_PATH = "feishu_webhook_bot.ai.multi_agent.agents.Agent"


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

    @patch(AGENT_MOCK_PATH)
    def test_agent_with_very_long_system_prompt(self, mock_agent_class):
        """Test agent with very long system prompt."""
        long_prompt = "You are a helpful assistant. " * 100

        agent = SpecializedAgent(
            name="LongPromptAgent",
            role="test",
            system_prompt=long_prompt,
        )

        assert agent.name == "LongPromptAgent"

    @patch(AGENT_MOCK_PATH)
    def test_agent_update_model(self, mock_agent):
        """Test agent update_model method."""
        agent = SpecializedAgent(
            name="TestAgent",
            role="test",
            system_prompt="Test",
            model="openai:gpt-4o",
        )

        agent.update_model("anthropic:claude-3-5-sonnet-20241022")

        assert agent.model == "anthropic:claude-3-5-sonnet-20241022"


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
# All Specialized Agents Tests
# ==============================================================================


class TestAllSpecializedAgents:
    """Tests for all specialized agent types."""

    @patch(AGENT_MOCK_PATH)
    def test_code_agent_initialization(self, mock_agent):
        """Test CodeAgent initialization."""
        agent = CodeAgent()

        assert agent.name == "CodeAgent"
        assert agent.role == "code"

    @patch(AGENT_MOCK_PATH)
    def test_summary_agent_initialization(self, mock_agent):
        """Test SummaryAgent initialization."""
        agent = SummaryAgent()

        assert agent.name == "SummaryAgent"
        assert agent.role == "summary"

    @patch(AGENT_MOCK_PATH)
    def test_translation_agent_initialization(self, mock_agent):
        """Test TranslationAgent initialization."""
        agent = TranslationAgent()

        assert agent.name == "TranslationAgent"
        assert agent.role == "translation"

    @patch(AGENT_MOCK_PATH)
    def test_reasoning_agent_initialization(self, mock_agent):
        """Test ReasoningAgent initialization."""
        agent = ReasoningAgent()

        assert agent.name == "ReasoningAgent"
        assert agent.role == "reasoning"

    @patch(AGENT_MOCK_PATH)
    def test_planning_agent_initialization(self, mock_agent):
        """Test PlanningAgent initialization."""
        agent = PlanningAgent()

        assert agent.name == "PlanningAgent"
        assert agent.role == "planning"

    @patch(AGENT_MOCK_PATH)
    def test_creative_agent_initialization(self, mock_agent):
        """Test CreativeAgent initialization."""
        agent = CreativeAgent()

        assert agent.name == "CreativeAgent"
        assert agent.role == "creative"

    @patch(AGENT_MOCK_PATH)
    def test_math_agent_initialization(self, mock_agent):
        """Test MathAgent initialization."""
        agent = MathAgent()

        assert agent.name == "MathAgent"
        assert agent.role == "math"

    @patch(AGENT_MOCK_PATH)
    def test_agent_has_capability(self, mock_agent):
        """Test agent has_capability method."""
        agent = CodeAgent()

        assert agent.has_capability(AgentCapability.CODE_GENERATION) is True
        assert agent.has_capability(AgentCapability.SEARCH) is False

    @patch(AGENT_MOCK_PATH)
    def test_agent_get_info(self, mock_agent):
        """Test agent get_info method."""
        agent = AnalysisAgent()

        info = agent.get_info()

        assert info.name == "AnalysisAgent"
        assert info.role == "analysis"
        assert info.enabled is True

    @patch(AGENT_MOCK_PATH)
    def test_agent_get_stats(self, mock_agent):
        """Test agent get_stats method."""
        agent = ResponseAgent()

        stats = agent.get_stats()

        assert stats["name"] == "ResponseAgent"
        assert stats["total_requests"] == 0
        assert stats["success_rate"] == 0
