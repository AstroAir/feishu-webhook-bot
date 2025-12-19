"""Common data models shared across providers.

This module contains unified data models used by multiple provider implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


class ProviderResponse(BaseModel):
    """Unified API response model for provider operations.

    This model standardizes response handling across different platforms,
    making it easier to handle success/failure cases consistently.

    Attributes:
        success: Whether the operation succeeded.
        data: Response data (if successful).
        error_code: Error code (if failed).
        error_msg: Error message (if failed).
        raw_response: Original response data for debugging.
    """

    success: bool
    data: Any = None
    error_code: int = 0
    error_msg: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any = None, raw_response: dict[str, Any] | None = None) -> ProviderResponse:
        """Create a successful response.

        Args:
            data: Response data.
            raw_response: Original response dict.

        Returns:
            ProviderResponse with success=True.
        """
        return cls(
            success=True,
            data=data,
            raw_response=raw_response or {},
        )

    @classmethod
    def fail(
        cls,
        error_msg: str,
        error_code: int = -1,
        raw_response: dict[str, Any] | None = None,
    ) -> ProviderResponse:
        """Create a failed response.

        Args:
            error_msg: Error message.
            error_code: Error code.
            raw_response: Original response dict.

        Returns:
            ProviderResponse with success=False.
        """
        return cls(
            success=False,
            error_code=error_code,
            error_msg=error_msg,
            raw_response=raw_response or {},
        )


@dataclass
class MessageContext:
    """Context for message sending operations.

    Provides consistent context information for logging and tracking.

    Attributes:
        message_id: Unique message identifier.
        message_type: Type of message (text, image, etc.).
        target: Target destination.
        provider_name: Name of the provider instance.
        provider_type: Type of provider (feishu, qq, etc.).
    """

    message_id: str
    message_type: str
    target: str
    provider_name: str
    provider_type: str


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts.
        backoff_seconds: Initial backoff delay in seconds.
        backoff_multiplier: Multiplier for exponential backoff.
        max_backoff_seconds: Maximum backoff delay.
    """

    max_attempts: int = 3
    backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 30.0

    @classmethod
    def from_policy(cls, policy: Any) -> RetryConfig:
        """Create RetryConfig from a RetryPolicyConfig.

        Args:
            policy: RetryPolicyConfig instance or None.

        Returns:
            RetryConfig with values from policy or defaults.
        """
        if policy is None:
            return cls()
        return cls(
            max_attempts=getattr(policy, "max_attempts", 3),
            backoff_seconds=getattr(policy, "backoff_seconds", 1.0),
            backoff_multiplier=getattr(policy, "backoff_multiplier", 2.0),
            max_backoff_seconds=getattr(policy, "max_backoff_seconds", 30.0),
        )
