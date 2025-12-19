"""HTTP provider mixin with common retry and error handling logic.

This module provides synchronous HTTP request functionality with:
- Exponential backoff retry logic
- Structured logging with provider context
- Consistent error handling
- Response validation
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import httpx

from ...core.logger import get_logger
from .models import RetryConfig
from .utils import log_message_result

if TYPE_CHECKING:
    from ...core.config import RetryPolicyConfig

logger = get_logger(__name__)


class HTTPProviderMixin:
    """Mixin providing common HTTP request functionality with retry logic.

    This mixin provides standardized HTTP request handling with:
    - Exponential backoff retry logic
    - Structured logging with provider context
    - Consistent error handling

    Usage:
        class MyProvider(BaseProvider, HTTPProviderMixin):
            def _make_http_request(self, url: str, payload: dict) -> dict:
                return self._http_request_with_retry(
                    client=self._client,
                    url=url,
                    payload=payload,
                    retry_policy=self.config.retry,
                    provider_name=self.name,
                    provider_type=self.provider_type,
                )
    """

    def _http_request_with_retry(
        self,
        client: httpx.Client,
        url: str,
        payload: dict[str, Any],
        retry_policy: RetryPolicyConfig | None,
        provider_name: str,
        provider_type: str,
        *,
        response_validator: Callable[[dict[str, Any]], None] | None = None,
        method: str = "POST",
    ) -> dict[str, Any]:
        """Make HTTP request with exponential backoff retry.

        Args:
            client: httpx Client instance.
            url: Target URL.
            payload: Request JSON payload.
            retry_policy: Retry configuration (optional).
            provider_name: Provider instance name for logging.
            provider_type: Provider type for logging.
            response_validator: Optional callable to validate response.
                Should raise ValueError if response is invalid.
            method: HTTP method (default: POST).

        Returns:
            Response JSON data.

        Raises:
            RuntimeError: If client is not initialized.
            httpx.HTTPStatusError: If all retries fail with HTTP error.
            ValueError: If response validation fails.
            Exception: If all retries fail with other errors.
        """
        if not client:
            raise RuntimeError("HTTP client not initialized")

        # Extract retry configuration
        config = RetryConfig.from_policy(retry_policy)

        delay = config.backoff_seconds
        last_error: Exception | None = None

        for attempt in range(config.max_attempts):
            try:
                if method.upper() == "POST":
                    response = client.post(url, json=payload)
                elif method.upper() == "GET":
                    response = client.get(url, params=payload)
                else:
                    response = client.request(method, url, json=payload)

                response.raise_for_status()
                result = response.json()

                # Validate response if validator provided
                if response_validator:
                    response_validator(result)

                return result

            except httpx.HTTPStatusError as e:
                last_error = e
                if attempt < config.max_attempts - 1:
                    logger.warning(
                        "HTTP request failed, retrying",
                        extra={
                            "provider": provider_name,
                            "provider_type": provider_type,
                            "url": url,
                            "attempt": attempt + 1,
                            "max_attempts": config.max_attempts,
                            "status_code": e.response.status_code,
                            "retry_delay": delay,
                        },
                    )
                    time.sleep(delay)
                    delay = min(delay * config.backoff_multiplier, config.max_backoff_seconds)
                else:
                    logger.error(
                        "HTTP request failed after all retries",
                        extra={
                            "provider": provider_name,
                            "provider_type": provider_type,
                            "url": url,
                            "attempts": config.max_attempts,
                            "status_code": e.response.status_code,
                        },
                    )

            except ValueError as e:
                # Response validation error - don't retry
                last_error = e
                logger.error(
                    "Response validation failed",
                    extra={
                        "provider": provider_name,
                        "provider_type": provider_type,
                        "url": url,
                        "error": str(e),
                    },
                )
                raise

            except Exception as e:
                last_error = e
                if attempt < config.max_attempts - 1:
                    logger.warning(
                        "Request failed, retrying",
                        extra={
                            "provider": provider_name,
                            "provider_type": provider_type,
                            "url": url,
                            "attempt": attempt + 1,
                            "max_attempts": config.max_attempts,
                            "error": str(e),
                            "retry_delay": delay,
                        },
                    )
                    time.sleep(delay)
                    delay = min(delay * config.backoff_multiplier, config.max_backoff_seconds)
                else:
                    logger.error(
                        "Request failed after all retries",
                        extra={
                            "provider": provider_name,
                            "provider_type": provider_type,
                            "url": url,
                            "attempts": config.max_attempts,
                            "error": str(e),
                        },
                    )

        if last_error:
            raise last_error
        raise RuntimeError("Unknown error during HTTP request")

    def _log_message_send_result(
        self,
        success: bool,
        message_type: str,
        message_id: str,
        target: str,
        provider_name: str,
        provider_type: str,
        error: str | None = None,
    ) -> None:
        """Log message send result with structured fields.

        This is a convenience method that wraps the utility function.

        Args:
            success: Whether the send was successful.
            message_type: Type of message (text, card, rich_text, image).
            message_id: Unique message identifier.
            target: Target URL or identifier.
            provider_name: Provider instance name.
            provider_type: Provider type.
            error: Error message if failed.
        """
        log_message_result(
            success=success,
            message_type=message_type,
            message_id=message_id,
            target=target,
            provider_name=provider_name,
            provider_type=provider_type,
            error=error,
        )
