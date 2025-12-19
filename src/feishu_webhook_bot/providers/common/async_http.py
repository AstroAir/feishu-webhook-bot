"""Async HTTP provider mixin with common retry and error handling logic.

This module provides asynchronous HTTP request functionality with:
- Exponential backoff retry logic
- Structured logging with provider context
- Consistent error handling
- Response validation
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import httpx

from ...core.logger import get_logger
from .models import RetryConfig

if TYPE_CHECKING:
    from ...core.config import RetryPolicyConfig

logger = get_logger(__name__)


class AsyncHTTPProviderMixin:
    """Mixin providing asynchronous HTTP request functionality with retry logic.

    This mixin provides standardized async HTTP request handling with:
    - Exponential backoff retry logic
    - Structured logging with provider context
    - Consistent error handling

    Usage:
        class MyAsyncProvider(AsyncHTTPProviderMixin):
            async def _make_async_request(self, url: str, payload: dict) -> dict:
                return await self._async_http_request_with_retry(
                    client=self._async_client,
                    url=url,
                    payload=payload,
                    retry_policy=self.config.retry,
                    provider_name=self.name,
                    provider_type=self.provider_type,
                )
    """

    async def _async_http_request_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        payload: dict[str, Any],
        retry_policy: RetryPolicyConfig | None,
        provider_name: str,
        provider_type: str,
        *,
        response_validator: Callable[[dict[str, Any]], None] | None = None,
        method: str = "POST",
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make async HTTP request with exponential backoff retry.

        Args:
            client: httpx AsyncClient instance.
            url: Target URL.
            payload: Request JSON payload.
            retry_policy: Retry configuration (optional).
            provider_name: Provider instance name for logging.
            provider_type: Provider type for logging.
            response_validator: Optional callable to validate response.
                Should raise ValueError if response is invalid.
            method: HTTP method (default: POST).
            headers: Additional headers for the request.

        Returns:
            Response JSON data.

        Raises:
            RuntimeError: If client is not initialized.
            httpx.HTTPStatusError: If all retries fail with HTTP error.
            ValueError: If response validation fails.
            Exception: If all retries fail with other errors.
        """
        if not client:
            raise RuntimeError("Async HTTP client not initialized")

        # Extract retry configuration
        config = RetryConfig.from_policy(retry_policy)

        delay = config.backoff_seconds
        last_error: Exception | None = None

        for attempt in range(config.max_attempts):
            try:
                if method.upper() == "POST":
                    response = await client.post(url, json=payload, headers=headers)
                elif method.upper() == "GET":
                    response = await client.get(url, params=payload, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=payload, headers=headers)
                elif method.upper() == "PATCH":
                    response = await client.patch(url, json=payload, headers=headers)
                else:
                    response = await client.request(method, url, json=payload, headers=headers)

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
                        "Async HTTP request failed, retrying",
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
                    await asyncio.sleep(delay)
                    delay = min(delay * config.backoff_multiplier, config.max_backoff_seconds)
                else:
                    logger.error(
                        "Async HTTP request failed after all retries",
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
                    "Async response validation failed",
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
                        "Async request failed, retrying",
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
                    await asyncio.sleep(delay)
                    delay = min(delay * config.backoff_multiplier, config.max_backoff_seconds)
                else:
                    logger.error(
                        "Async request failed after all retries",
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
        raise RuntimeError("Unknown error during async HTTP request")

    async def _async_request_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make a simple async HTTP request without retry.

        Args:
            client: httpx AsyncClient instance.
            method: HTTP method.
            url: Target URL.
            json: JSON body (for POST/PUT/PATCH).
            params: Query parameters.
            headers: Request headers.

        Returns:
            httpx Response object.

        Raises:
            RuntimeError: If client is not initialized.
        """
        if not client:
            raise RuntimeError("Async HTTP client not initialized")

        return await client.request(
            method,
            url,
            json=json,
            params=params,
            headers=headers,
        )
