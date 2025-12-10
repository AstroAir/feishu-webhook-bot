"""Tests for AI task integration.

This module tests the integration of AI capabilities with the automated task system.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from feishu_webhook_bot.ai.task_integration import (
    AITaskExecutor,
    AITaskResult,
    execute_ai_task_action,
)
from feishu_webhook_bot.core.config import TaskActionConfig

# Use anyio for async tests with asyncio backend only
pytestmark = pytest.mark.anyio(backends=["asyncio"])


class TestAITaskResult:
    """Tests for AITaskResult model."""

    def test_successful_result(self):
        """Test creating a successful AI task result."""
        result = AITaskResult(
            success=True,
            response="Test response",
            confidence=0.95,
            sources_used=["source1", "source2"],
            tools_called=["tool1"],
            error=None,
            metadata={"key": "value"},
        )

        assert result.success is True
        assert result.response == "Test response"
        assert result.confidence == 0.95
        assert len(result.sources_used) == 2
        assert len(result.tools_called) == 1
        assert result.error is None
        assert result.metadata == {"key": "value"}

    def test_failed_result(self):
        """Test creating a failed AI task result."""
        result = AITaskResult(
            success=False,
            response="",
            confidence=None,
            sources_used=[],
            tools_called=[],
            error="Test error",
            metadata={},
        )

        assert result.success is False
        assert result.response == ""
        assert result.confidence is None
        assert result.error == "Test error"

    def test_default_values(self):
        """Test default values in AITaskResult."""
        result = AITaskResult(
            success=True,
            response="Test",
            confidence=None,
            sources_used=[],
            tools_called=[],
            error=None,
            metadata={},
        )

        assert result.sources_used == []
        assert result.tools_called == []
        assert result.metadata == {}


class TestAITaskExecutor:
    """Tests for AITaskExecutor class."""

    @pytest.fixture
    def mock_ai_agent(self):
        """Create a mock AI agent."""
        agent = MagicMock()
        agent.chat = AsyncMock(return_value="AI response")
        return agent

    @pytest.fixture
    def ai_executor(self, mock_ai_agent):
        """Create an AITaskExecutor with mock agent."""
        return AITaskExecutor(mock_ai_agent)

    async def test_execute_ai_chat_action(self, ai_executor, mock_ai_agent):
        """Test executing an ai_chat action."""
        action = TaskActionConfig(
            type="ai_chat",
            ai_prompt="Test prompt",
            ai_user_id="test_user",
        )
        context = {}

        result = await ai_executor.execute_ai_action(action, context)

        assert result.success is True
        assert result.response == "AI response"
        mock_ai_agent.chat.assert_called_once()

    async def test_execute_ai_query_action(self, ai_executor, mock_ai_agent):
        """Test executing an ai_query action."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test query",
            ai_user_id="test_user",
        )
        context = {}

        result = await ai_executor.execute_ai_action(action, context)

        assert result.success is True
        assert result.response == "AI response"
        mock_ai_agent.chat.assert_called()

    async def test_context_variable_substitution(self, ai_executor, mock_ai_agent):
        """Test variable substitution in prompts."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Hello ${name}, today is ${date}",
            ai_user_id="test_user",
        )
        context = {
            "name": "Alice",
            "date": "2024-01-01",
        }

        await ai_executor.execute_ai_action(action, context)

        # Check that the prompt was substituted
        call_args = mock_ai_agent.chat.call_args
        assert "Alice" in str(call_args)
        assert "2024-01-01" in str(call_args)

    async def test_save_response_to_context(self, ai_executor, mock_ai_agent):
        """Test saving AI response to context."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test",
            ai_user_id="test_user",
            ai_save_response_as="ai_result",
        )
        context = {}

        result = await ai_executor.execute_ai_action(action, context)

        assert result.success is True
        assert context["ai_result"] == "AI response"

    async def test_config_override_temperature(self, ai_executor, mock_ai_agent):
        """Test overriding temperature in action."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test",
            ai_user_id="test_user",
            ai_temperature=0.9,
        )
        context = {}

        result = await ai_executor.execute_ai_action(action, context)

        assert result.success is True
        # Temperature override should be passed to agent

    async def test_config_override_max_tokens(self, ai_executor, mock_ai_agent):
        """Test overriding max_tokens in action."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test",
            ai_user_id="test_user",
            ai_max_tokens=100,
        )
        context = {}

        result = await ai_executor.execute_ai_action(action, context)

        assert result.success is True

    async def test_config_override_system_prompt(self, ai_executor, mock_ai_agent):
        """Test overriding system prompt in action."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test",
            ai_user_id="test_user",
            ai_system_prompt="Custom system prompt",
        )
        context = {}

        result = await ai_executor.execute_ai_action(action, context)

        assert result.success is True

    async def test_error_handling(self, ai_executor, mock_ai_agent):
        """Test error handling in AI action execution."""
        mock_ai_agent.chat.side_effect = Exception("Test error")

        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test",
            ai_user_id="test_user",
        )
        context = {}

        result = await ai_executor.execute_ai_action(action, context)

        assert result.success is False
        assert "Test error" in result.error

    async def test_missing_prompt(self, ai_executor):
        """Test handling of missing prompt."""
        action = TaskActionConfig(
            type="ai_query",
            ai_user_id="test_user",
        )
        context = {}

        result = await ai_executor.execute_ai_action(action, context)

        assert result.success is False
        assert result.error is not None

    async def test_default_user_id(self, ai_executor, mock_ai_agent):
        """Test default user_id when not specified."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test",
        )
        context = {}

        result = await ai_executor.execute_ai_action(action, context)

        assert result.success is True
        # Should use default user_id


class TestExecuteAITaskAction:
    """Tests for execute_ai_task_action helper function."""

    @pytest.fixture
    def mock_ai_agent(self):
        """Create a mock AI agent."""
        agent = MagicMock()
        agent.chat = AsyncMock(return_value="AI response")
        return agent

    async def test_execute_ai_task_action(self, mock_ai_agent):
        """Test the execute_ai_task_action helper function."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test prompt",
            ai_user_id="test_user",
        )
        context = {}

        result = await execute_ai_task_action(action, context, mock_ai_agent)

        assert isinstance(result, AITaskResult)
        assert result.success is True
        assert result.response == "AI response"

    async def test_execute_with_context_substitution(self, mock_ai_agent):
        """Test execute_ai_task_action with context substitution."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Process ${data}",
            ai_user_id="test_user",
            ai_save_response_as="result",
        )
        context = {"data": "test data"}

        result = await execute_ai_task_action(action, context, mock_ai_agent)

        assert result.success is True
        assert context["result"] == "AI response"


class TestTaskActionConfig:
    """Tests for TaskActionConfig with AI fields."""

    def test_ai_chat_action_config(self):
        """Test creating an ai_chat action configuration."""
        action = TaskActionConfig(
            type="ai_chat",
            ai_prompt="Test prompt",
            ai_user_id="user1",
            ai_temperature=0.8,
            ai_max_tokens=500,
        )

        assert action.type == "ai_chat"
        assert action.ai_prompt == "Test prompt"
        assert action.ai_user_id == "user1"
        assert action.ai_temperature == 0.8
        assert action.ai_max_tokens == 500

    def test_ai_query_action_config(self):
        """Test creating an ai_query action configuration."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test query",
            ai_user_id="user1",
            ai_save_response_as="result",
        )

        assert action.type == "ai_query"
        assert action.ai_prompt == "Test query"
        assert action.ai_save_response_as == "result"

    def test_ai_action_with_system_prompt(self):
        """Test AI action with custom system prompt."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test",
            ai_system_prompt="Custom system prompt",
        )

        assert action.ai_system_prompt == "Custom system prompt"

    def test_ai_action_with_structured_output(self):
        """Test AI action with structured output enabled."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test",
            ai_structured_output=True,
        )

        assert action.ai_structured_output is True

    def test_ai_action_defaults(self):
        """Test default values for AI action fields."""
        action = TaskActionConfig(
            type="ai_query",
            ai_prompt="Test",
        )

        assert action.ai_user_id is None
        assert action.ai_system_prompt is None
        assert action.ai_temperature is None
        assert action.ai_max_tokens is None
        assert action.ai_save_response_as is None
        assert action.ai_structured_output is False
