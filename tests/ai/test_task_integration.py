"""Comprehensive tests for AI task integration module.

Tests cover:
- AITaskResult model validation
- AITaskExecutor initialization
- AI action execution
- Prompt building with context substitution
- Config override and restoration
- Error handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from feishu_webhook_bot.ai.task_integration import (
    AITaskExecutor,
    AITaskResult,
    execute_ai_task_action,
)


# ==============================================================================
# AITaskResult Tests
# ==============================================================================


class TestAITaskResult:
    """Tests for AITaskResult model."""

    def test_result_success(self):
        """Test successful AITaskResult."""
        result = AITaskResult(
            success=True,
            response="AI generated response",
        )

        assert result.success is True
        assert result.response == "AI generated response"
        assert result.confidence is None
        assert result.sources_used == []
        assert result.tools_called == []
        assert result.error is None
        assert result.metadata == {}

    def test_result_failure(self):
        """Test failed AITaskResult."""
        result = AITaskResult(
            success=False,
            response="",
            error="AI service unavailable",
        )

        assert result.success is False
        assert result.response == ""
        assert result.error == "AI service unavailable"

    def test_result_with_confidence(self):
        """Test AITaskResult with confidence."""
        result = AITaskResult(
            success=True,
            response="Response",
            confidence=0.95,
        )

        assert result.confidence == 0.95

    def test_result_confidence_bounds(self):
        """Test AITaskResult confidence must be between 0 and 1."""
        # Valid bounds
        result_low = AITaskResult(success=True, response="", confidence=0.0)
        result_high = AITaskResult(success=True, response="", confidence=1.0)

        assert result_low.confidence == 0.0
        assert result_high.confidence == 1.0

        # Invalid bounds
        with pytest.raises(ValueError):
            AITaskResult(success=True, response="", confidence=-0.1)

        with pytest.raises(ValueError):
            AITaskResult(success=True, response="", confidence=1.1)

    def test_result_with_sources_and_tools(self):
        """Test AITaskResult with sources and tools."""
        result = AITaskResult(
            success=True,
            response="Response",
            sources_used=["web_search", "database"],
            tools_called=["calculator", "weather"],
        )

        assert len(result.sources_used) == 2
        assert len(result.tools_called) == 2
        assert "web_search" in result.sources_used
        assert "calculator" in result.tools_called

    def test_result_with_metadata(self):
        """Test AITaskResult with metadata."""
        result = AITaskResult(
            success=True,
            response="Response",
            metadata={"tokens": 150, "model": "gpt-4"},
        )

        assert result.metadata["tokens"] == 150
        assert result.metadata["model"] == "gpt-4"

    def test_result_serialization(self):
        """Test AITaskResult serialization."""
        result = AITaskResult(
            success=True,
            response="Test",
            confidence=0.9,
        )

        data = result.model_dump()

        assert data["success"] is True
        assert data["response"] == "Test"
        assert data["confidence"] == 0.9


# ==============================================================================
# AITaskExecutor Initialization Tests
# ==============================================================================


class TestAITaskExecutorInitialization:
    """Tests for AITaskExecutor initialization."""

    def test_executor_without_agent(self):
        """Test executor initialization without AI agent."""
        executor = AITaskExecutor()

        assert executor.ai_agent is None

    def test_executor_with_agent(self):
        """Test executor initialization with AI agent."""
        mock_agent = MagicMock()

        executor = AITaskExecutor(ai_agent=mock_agent)

        assert executor.ai_agent == mock_agent


# ==============================================================================
# AITaskExecutor Prompt Building Tests
# ==============================================================================


class TestAITaskExecutorPromptBuilding:
    """Tests for prompt building with context substitution."""

    def test_build_prompt_no_variables(self):
        """Test building prompt without variables."""
        executor = AITaskExecutor()

        prompt = executor._build_prompt("Hello, world!", {})

        assert prompt == "Hello, world!"

    def test_build_prompt_with_variables(self):
        """Test building prompt with variable substitution."""
        executor = AITaskExecutor()

        prompt = executor._build_prompt(
            "Hello, ${name}! Today is ${day}.",
            {"name": "Alice", "day": "Monday"},
        )

        assert prompt == "Hello, Alice! Today is Monday."

    def test_build_prompt_missing_variable(self):
        """Test building prompt with missing variable."""
        executor = AITaskExecutor()

        prompt = executor._build_prompt(
            "Hello, ${name}! Your ID is ${id}.",
            {"name": "Bob"},
        )

        # Missing variable is left as-is
        assert prompt == "Hello, Bob! Your ID is ${id}."

    def test_build_prompt_numeric_variable(self):
        """Test building prompt with numeric variable."""
        executor = AITaskExecutor()

        prompt = executor._build_prompt(
            "You have ${count} messages.",
            {"count": 42},
        )

        assert prompt == "You have 42 messages."


# ==============================================================================
# AITaskExecutor Execution Tests
# ==============================================================================


class TestAITaskExecutorExecution:
    """Tests for AI action execution."""

    @pytest.mark.anyio
    async def test_execute_without_agent(self):
        """Test execution fails without AI agent."""
        executor = AITaskExecutor()

        mock_action = MagicMock()
        mock_action.ai_prompt = "Test prompt"

        result = await executor.execute_ai_action(mock_action, {})

        assert result.success is False
        assert "not available" in result.error

    @pytest.mark.anyio
    async def test_execute_without_prompt(self):
        """Test execution fails without ai_prompt."""
        mock_agent = MagicMock()
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_prompt = None

        result = await executor.execute_ai_action(mock_action, {})

        assert result.success is False
        assert "ai_prompt is required" in result.error

    @pytest.mark.anyio
    async def test_execute_success(self):
        """Test successful AI action execution."""
        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value="AI response")
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_prompt = "Test prompt"
        mock_action.ai_user_id = None
        mock_action.ai_structured_output = False
        mock_action.ai_save_response_as = None
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = None

        result = await executor.execute_ai_action(mock_action, {})

        assert result.success is True
        assert result.response == "AI response"

    @pytest.mark.anyio
    async def test_execute_with_user_id(self):
        """Test execution with custom user ID."""
        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value="Response")
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_prompt = "Test"
        mock_action.ai_user_id = "custom_user"
        mock_action.ai_structured_output = False
        mock_action.ai_save_response_as = None
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = None

        await executor.execute_ai_action(mock_action, {})

        mock_agent.chat.assert_called_once_with("custom_user", "Test")

    @pytest.mark.anyio
    async def test_execute_with_context_user_id(self):
        """Test execution uses user_id from context."""
        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value="Response")
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_prompt = "Test"
        mock_action.ai_user_id = None
        mock_action.ai_structured_output = False
        mock_action.ai_save_response_as = None
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = None

        await executor.execute_ai_action(mock_action, {"user_id": "context_user"})

        mock_agent.chat.assert_called_once_with("context_user", "Test")

    @pytest.mark.anyio
    async def test_execute_saves_response(self):
        """Test execution saves response to context."""
        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value="AI response")
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_prompt = "Test"
        mock_action.ai_user_id = None
        mock_action.ai_structured_output = False
        mock_action.ai_save_response_as = "ai_result"
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = None

        context = {}
        await executor.execute_ai_action(mock_action, context)

        assert context["ai_result"] == "AI response"

    @pytest.mark.anyio
    async def test_execute_with_prompt_substitution(self):
        """Test execution with prompt variable substitution."""
        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value="Response")
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_prompt = "Hello ${name}, summarize ${topic}"
        mock_action.ai_user_id = None
        mock_action.ai_structured_output = False
        mock_action.ai_save_response_as = None
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = None

        await executor.execute_ai_action(
            mock_action,
            {"name": "Alice", "topic": "AI"},
        )

        mock_agent.chat.assert_called_once_with(
            "task_system",
            "Hello Alice, summarize AI",
        )

    @pytest.mark.anyio
    async def test_execute_handles_exception(self):
        """Test execution handles exceptions gracefully."""
        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(side_effect=Exception("API error"))
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_prompt = "Test"
        mock_action.ai_user_id = None
        mock_action.ai_structured_output = False
        mock_action.ai_save_response_as = None
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = None

        result = await executor.execute_ai_action(mock_action, {})

        assert result.success is False
        assert "API error" in result.error


# ==============================================================================
# AITaskExecutor Structured Output Tests
# ==============================================================================


class TestAITaskExecutorStructuredOutput:
    """Tests for structured output handling."""

    @pytest.mark.anyio
    async def test_execute_structured_output(self):
        """Test execution with structured output."""
        mock_response = MagicMock()
        mock_response.message = "Structured response"
        mock_response.confidence = 0.95
        mock_response.sources_used = ["web"]
        mock_response.tools_called = ["search"]

        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value=mock_response)
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_prompt = "Test"
        mock_action.ai_user_id = None
        mock_action.ai_structured_output = True
        mock_action.ai_save_response_as = None
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = None

        result = await executor.execute_ai_action(mock_action, {})

        assert result.success is True
        assert result.response == "Structured response"
        assert result.confidence == 0.95
        assert result.sources_used == ["web"]
        assert result.tools_called == ["search"]

    @pytest.mark.anyio
    async def test_execute_structured_output_no_message_attr(self):
        """Test structured output when response has no message attribute."""
        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value="Plain string response")
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_prompt = "Test"
        mock_action.ai_user_id = None
        mock_action.ai_structured_output = True
        mock_action.ai_save_response_as = None
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = None

        result = await executor.execute_ai_action(mock_action, {})

        assert result.success is True
        assert result.response == "Plain string response"


# ==============================================================================
# AITaskExecutor Config Override Tests
# ==============================================================================


class TestAITaskExecutorConfigOverride:
    """Tests for config override and restoration."""

    def test_save_and_override_config_no_agent(self):
        """Test config override without agent."""
        executor = AITaskExecutor()

        mock_action = MagicMock()
        mock_action.ai_system_prompt = "New prompt"

        result = executor._save_and_override_config(mock_action)

        assert result == {}

    def test_save_and_override_temperature(self):
        """Test temperature override."""
        mock_agent = MagicMock()
        mock_agent.config.temperature = 0.7
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = 0.9
        mock_action.ai_max_tokens = None

        original = executor._save_and_override_config(mock_action)

        assert original["temperature"] == 0.7
        assert mock_agent.config.temperature == 0.9

    def test_save_and_override_max_tokens(self):
        """Test max_tokens override."""
        mock_agent = MagicMock()
        mock_agent.config.max_tokens = 1000
        executor = AITaskExecutor(ai_agent=mock_agent)

        mock_action = MagicMock()
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = 2000

        original = executor._save_and_override_config(mock_action)

        assert original["max_tokens"] == 1000
        assert mock_agent.config.max_tokens == 2000

    def test_restore_config(self):
        """Test config restoration."""
        mock_agent = MagicMock()
        mock_agent.config.temperature = 0.9
        mock_agent.config.max_tokens = 2000
        executor = AITaskExecutor(ai_agent=mock_agent)

        original = {"temperature": 0.7, "max_tokens": 1000}

        executor._restore_config(original)

        assert mock_agent.config.temperature == 0.7
        assert mock_agent.config.max_tokens == 1000

    def test_restore_config_no_agent(self):
        """Test config restoration without agent."""
        executor = AITaskExecutor()

        # Should not raise
        executor._restore_config({"temperature": 0.7})


# ==============================================================================
# Convenience Function Tests
# ==============================================================================


class TestExecuteAITaskAction:
    """Tests for execute_ai_task_action convenience function."""

    @pytest.mark.anyio
    async def test_execute_without_agent(self):
        """Test convenience function without agent."""
        mock_action = MagicMock()
        mock_action.ai_prompt = "Test"

        result = await execute_ai_task_action(mock_action, {})

        assert result.success is False
        assert "not available" in result.error

    @pytest.mark.anyio
    async def test_execute_with_agent(self):
        """Test convenience function with agent."""
        mock_agent = MagicMock()
        mock_agent.chat = AsyncMock(return_value="Response")

        mock_action = MagicMock()
        mock_action.ai_prompt = "Test"
        mock_action.ai_user_id = None
        mock_action.ai_structured_output = False
        mock_action.ai_save_response_as = None
        mock_action.ai_system_prompt = None
        mock_action.ai_temperature = None
        mock_action.ai_max_tokens = None

        result = await execute_ai_task_action(mock_action, {}, ai_agent=mock_agent)

        assert result.success is True
        assert result.response == "Response"
