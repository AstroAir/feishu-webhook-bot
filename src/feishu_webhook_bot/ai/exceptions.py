"""Custom exceptions for AI module."""

from __future__ import annotations


class AIError(Exception):
    """Base exception for AI-related errors."""

    pass


class AIServiceUnavailableError(AIError):
    """Raised when AI service is unavailable."""

    def __init__(
        self, message: str = "AI service is currently unavailable", service: str | None = None
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            service: Name of the unavailable service
        """
        self.service = service
        super().__init__(message)


class ToolExecutionError(AIError):
    """Raised when a tool execution fails."""

    def __init__(
        self, message: str, tool_name: str, original_error: Exception | None = None
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            tool_name: Name of the tool that failed
            original_error: Original exception that caused the failure
        """
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(message)


class ConversationNotFoundError(AIError):
    """Raised when a conversation is not found."""

    def __init__(self, user_id: str) -> None:
        """Initialize the exception.

        Args:
            user_id: User ID of the missing conversation
        """
        self.user_id = user_id
        super().__init__(f"Conversation not found for user: {user_id}")


class ModelResponseError(AIError):
    """Raised when model response is invalid or unexpected."""

    def __init__(self, message: str, response: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            response: The invalid response from the model
        """
        self.response = response
        super().__init__(message)


class TokenLimitExceededError(AIError):
    """Raised when token limit is exceeded."""

    def __init__(self, message: str, tokens_used: int, token_limit: int) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            tokens_used: Number of tokens used
            token_limit: Maximum allowed tokens
        """
        self.tokens_used = tokens_used
        self.token_limit = token_limit
        super().__init__(message)


class RateLimitError(AIError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: float | None = None
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
        """
        self.retry_after = retry_after
        super().__init__(message)


class ConfigurationError(AIError):
    """Raised when AI configuration is invalid."""

    def __init__(self, message: str, config_key: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            config_key: Configuration key that is invalid
        """
        self.config_key = config_key
        super().__init__(message)
