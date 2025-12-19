"""Common utility functions for providers.

This module provides shared utility functions used across provider implementations.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ...core.logger import get_logger

logger = get_logger(__name__)


def validate_response(
    result: dict[str, Any],
    error_field: str = "code",
    success_value: Any = 0,
    message_field: str = "msg",
) -> None:
    """Validate API response and raise ValueError if failed.

    This provides a configurable response validation that works with
    different API response formats.

    Args:
        result: API response dict.
        error_field: Field name containing error/status code.
        success_value: Value indicating success.
        message_field: Field name containing error message.

    Raises:
        ValueError: If response indicates failure.

    Example:
        ```python
        # For Feishu API (code=0 means success)
        validate_response(result, error_field="code", success_value=0)

        # For OneBot API (status="ok" means success)
        validate_response(result, error_field="status", success_value="ok")
        ```
    """
    actual_value = result.get(error_field)
    if actual_value != success_value:
        error_msg = result.get(message_field, "Unknown error")
        raise ValueError(f"API error: {error_msg} ({error_field}={actual_value})")


def create_response_validator(
    error_field: str = "code",
    success_value: Any = 0,
    message_field: str = "msg",
) -> Callable[[dict[str, Any]], None]:
    """Create a response validator function with preconfigured settings.

    This is useful for creating validators that can be passed to HTTP request methods.

    Args:
        error_field: Field name containing error/status code.
        success_value: Value indicating success.
        message_field: Field name containing error message.

    Returns:
        A callable that validates responses.

    Example:
        ```python
        feishu_validator = create_response_validator("code", 0, "msg")
        onebot_validator = create_response_validator("status", "ok", "msg")
        ```
    """

    def validator(result: dict[str, Any]) -> None:
        validate_response(result, error_field, success_value, message_field)

    return validator


def log_message_result(
    success: bool,
    message_type: str,
    message_id: str,
    target: str,
    provider_name: str,
    provider_type: str,
    error: str | None = None,
) -> None:
    """Log message send result with structured fields.

    Provides consistent logging format across all providers.

    Args:
        success: Whether the send was successful.
        message_type: Type of message (text, card, image, etc.).
        message_id: Unique message identifier.
        target: Target destination.
        provider_name: Name of the provider instance.
        provider_type: Type of provider.
        error: Error message if failed.
    """
    extra = {
        "provider": provider_name,
        "provider_type": provider_type,
        "message_type": message_type,
        "message_id": message_id,
        "target": target,
    }

    if success:
        logger.debug("Message sent successfully", extra=extra)
    else:
        extra["error"] = error
        logger.error("Message send failed", extra=extra)


def parse_target(target: str, separator: str = ":") -> tuple[str, str]:
    """Parse target string into type and ID components.

    Args:
        target: Target string in format "type:id" (e.g., "group:123456").
        separator: Separator character.

    Returns:
        Tuple of (target_type, target_id). Both empty if parsing fails.

    Example:
        ```python
        target_type, target_id = parse_target("group:123456")
        # target_type = "group", target_id = "123456"
        ```
    """
    parts = target.split(separator, 1)
    if len(parts) != 2:
        return "", ""
    return parts[0], parts[1]


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int.

    Args:
        value: Value to convert.
        default: Default value if conversion fails.

    Returns:
        Converted int or default.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max length with suffix.

    Args:
        s: String to truncate.
        max_length: Maximum length including suffix.
        suffix: Suffix to append if truncated.

    Returns:
        Truncated string.
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix
