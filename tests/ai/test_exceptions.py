"""Comprehensive tests for AI module exceptions.

Tests cover:
- AIError base exception
- AIServiceUnavailableError
- ToolExecutionError
- ConversationNotFoundError
- ModelResponseError
- TokenLimitExceededError
- RateLimitError
- ConfigurationError
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.ai.exceptions import (
    AIError,
    AIServiceUnavailableError,
    ConfigurationError,
    ConversationNotFoundError,
    ModelResponseError,
    RateLimitError,
    TokenLimitExceededError,
    ToolExecutionError,
)


# ==============================================================================
# AIError Tests
# ==============================================================================


class TestAIError:
    """Tests for base AIError exception."""

    def test_ai_error_creation(self):
        """Test AIError can be created with message."""
        error = AIError("Test error message")
        assert str(error) == "Test error message"

    def test_ai_error_is_exception(self):
        """Test AIError is an Exception."""
        error = AIError("test")
        assert isinstance(error, Exception)

    def test_ai_error_can_be_raised(self):
        """Test AIError can be raised and caught."""
        with pytest.raises(AIError, match="test error"):
            raise AIError("test error")


# ==============================================================================
# AIServiceUnavailableError Tests
# ==============================================================================


class TestAIServiceUnavailableError:
    """Tests for AIServiceUnavailableError."""

    def test_default_message(self):
        """Test default error message."""
        error = AIServiceUnavailableError()
        assert "unavailable" in str(error).lower()

    def test_custom_message(self):
        """Test custom error message."""
        error = AIServiceUnavailableError("Custom unavailable message")
        assert str(error) == "Custom unavailable message"

    def test_with_service_name(self):
        """Test error with service name."""
        error = AIServiceUnavailableError("OpenAI is down", service="openai")
        assert error.service == "openai"
        assert "OpenAI is down" in str(error)

    def test_inherits_from_ai_error(self):
        """Test inherits from AIError."""
        error = AIServiceUnavailableError()
        assert isinstance(error, AIError)


# ==============================================================================
# ToolExecutionError Tests
# ==============================================================================


class TestToolExecutionError:
    """Tests for ToolExecutionError."""

    def test_creation_with_required_args(self):
        """Test creation with required arguments."""
        error = ToolExecutionError("Tool failed", tool_name="web_search")
        assert str(error) == "Tool failed"
        assert error.tool_name == "web_search"
        assert error.original_error is None

    def test_creation_with_original_error(self):
        """Test creation with original error."""
        original = ValueError("Original cause")
        error = ToolExecutionError(
            "Tool failed",
            tool_name="calculator",
            original_error=original,
        )
        assert error.tool_name == "calculator"
        assert error.original_error is original

    def test_inherits_from_ai_error(self):
        """Test inherits from AIError."""
        error = ToolExecutionError("fail", tool_name="test")
        assert isinstance(error, AIError)


# ==============================================================================
# ConversationNotFoundError Tests
# ==============================================================================


class TestConversationNotFoundError:
    """Tests for ConversationNotFoundError."""

    def test_creation_with_user_id(self):
        """Test creation with user_id."""
        error = ConversationNotFoundError("user123")
        assert error.user_id == "user123"
        assert "user123" in str(error)

    def test_message_format(self):
        """Test error message format."""
        error = ConversationNotFoundError("test_user")
        assert "not found" in str(error).lower()
        assert "test_user" in str(error)

    def test_inherits_from_ai_error(self):
        """Test inherits from AIError."""
        error = ConversationNotFoundError("user")
        assert isinstance(error, AIError)


# ==============================================================================
# ModelResponseError Tests
# ==============================================================================


class TestModelResponseError:
    """Tests for ModelResponseError."""

    def test_creation_with_message(self):
        """Test creation with message only."""
        error = ModelResponseError("Invalid response format")
        assert str(error) == "Invalid response format"
        assert error.response is None

    def test_creation_with_response(self):
        """Test creation with response data."""
        error = ModelResponseError(
            "Unexpected response",
            response='{"error": "invalid"}',
        )
        assert error.response == '{"error": "invalid"}'

    def test_inherits_from_ai_error(self):
        """Test inherits from AIError."""
        error = ModelResponseError("test")
        assert isinstance(error, AIError)


# ==============================================================================
# TokenLimitExceededError Tests
# ==============================================================================


class TestTokenLimitExceededError:
    """Tests for TokenLimitExceededError."""

    def test_creation_with_all_args(self):
        """Test creation with all arguments."""
        error = TokenLimitExceededError(
            "Token limit exceeded",
            tokens_used=5000,
            token_limit=4096,
        )
        assert str(error) == "Token limit exceeded"
        assert error.tokens_used == 5000
        assert error.token_limit == 4096

    def test_token_values_accessible(self):
        """Test token values are accessible."""
        error = TokenLimitExceededError(
            "Exceeded",
            tokens_used=10000,
            token_limit=8192,
        )
        assert error.tokens_used > error.token_limit

    def test_inherits_from_ai_error(self):
        """Test inherits from AIError."""
        error = TokenLimitExceededError("test", tokens_used=0, token_limit=0)
        assert isinstance(error, AIError)


# ==============================================================================
# RateLimitError Tests
# ==============================================================================


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_default_message(self):
        """Test default error message."""
        error = RateLimitError()
        assert "rate limit" in str(error).lower()

    def test_custom_message(self):
        """Test custom error message."""
        error = RateLimitError("Too many requests to OpenAI")
        assert str(error) == "Too many requests to OpenAI"

    def test_with_retry_after(self):
        """Test error with retry_after value."""
        error = RateLimitError("Rate limited", retry_after=30.0)
        assert error.retry_after == 30.0

    def test_retry_after_none(self):
        """Test retry_after defaults to None."""
        error = RateLimitError()
        assert error.retry_after is None

    def test_inherits_from_ai_error(self):
        """Test inherits from AIError."""
        error = RateLimitError()
        assert isinstance(error, AIError)


# ==============================================================================
# ConfigurationError Tests
# ==============================================================================


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_creation_with_message(self):
        """Test creation with message only."""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
        assert error.config_key is None

    def test_creation_with_config_key(self):
        """Test creation with config_key."""
        error = ConfigurationError(
            "Missing API key",
            config_key="openai_api_key",
        )
        assert error.config_key == "openai_api_key"

    def test_inherits_from_ai_error(self):
        """Test inherits from AIError."""
        error = ConfigurationError("test")
        assert isinstance(error, AIError)


# ==============================================================================
# Exception Hierarchy Tests
# ==============================================================================


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_all_exceptions_inherit_from_ai_error(self):
        """Test all custom exceptions inherit from AIError."""
        exceptions = [
            AIServiceUnavailableError(),
            ToolExecutionError("test", tool_name="test"),
            ConversationNotFoundError("user"),
            ModelResponseError("test"),
            TokenLimitExceededError("test", tokens_used=0, token_limit=0),
            RateLimitError(),
            ConfigurationError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, AIError), f"{type(exc).__name__} should inherit from AIError"

    def test_can_catch_all_with_ai_error(self):
        """Test all exceptions can be caught with AIError."""
        def raise_service_unavailable():
            raise AIServiceUnavailableError()

        def raise_tool_execution():
            raise ToolExecutionError("fail", tool_name="test")

        def raise_rate_limit():
            raise RateLimitError()

        for func in [raise_service_unavailable, raise_tool_execution, raise_rate_limit]:
            with pytest.raises(AIError):
                func()
