"""Retry utilities with exponential backoff for AI operations."""

from __future__ import annotations

import asyncio
import functools
import random
from collections.abc import Callable
from typing import Any, TypeVar, cast

from ..core.logger import get_logger
from .exceptions import AIServiceUnavailableError

logger = get_logger("ai.retry")

T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker pattern implementation for preventing cascading failures.

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to track for failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        logger.info(
            "CircuitBreaker initialized (threshold=%d, timeout=%.1fs)",
            failure_threshold,
            recovery_timeout,
        )

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            AIServiceUnavailableError: If circuit is open
        """
        if self.state == "OPEN":
            import time

            try:
                loop = asyncio.get_running_loop()
                current_time = loop.time()
            except RuntimeError:
                # No running loop, use time.time()
                current_time = time.time()

            if (
                self.last_failure_time
                and (current_time - self.last_failure_time) > self.recovery_timeout
            ):
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise AIServiceUnavailableError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as exc:
            self._on_failure()
            raise exc

    async def call_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            AIServiceUnavailableError: If circuit is open
        """
        if self.state == "OPEN":
            import time

            try:
                loop = asyncio.get_running_loop()
                current_time = loop.time()
            except RuntimeError:
                # No running loop, use time.time()
                current_time = time.time()

            if (
                self.last_failure_time
                and (current_time - self.last_failure_time) > self.recovery_timeout
            ):
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise AIServiceUnavailableError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as exc:
            self._on_failure()
            raise exc

    def _on_success(self) -> None:
        """Handle successful execution."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            logger.info("Circuit breaker recovered, state: CLOSED")

    def _on_failure(self) -> None:
        """Handle failed execution."""
        import time

        self.failure_count += 1
        # Use time.time() for sync context, asyncio loop time for async
        try:
            loop = asyncio.get_running_loop()
            self.last_failure_time = loop.time()
        except RuntimeError:
            # No running loop, use time.time()
            self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                "Circuit breaker opened after %d failures",
                self.failure_count,
            )

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        logger.info("Circuit breaker reset")


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retry_on: Tuple of exception types to retry on

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except retry_on as exc:
                    last_exception = exc

                    if attempt == max_retries:
                        logger.error(
                            "Function %s failed after %d attempts: %s",
                            func.__name__,
                            max_retries + 1,
                            exc,
                            exc_info=True,
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        "Function %s failed (attempt %d/%d): %s. Retrying in %.2fs...",
                        func.__name__,
                        attempt + 1,
                        max_retries + 1,
                        exc,
                        delay,
                    )

                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # For sync functions, we can't use asyncio.sleep
            # This is a simplified version without async support
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except retry_on as exc:
                    last_exception = exc

                    if attempt == max_retries:
                        logger.error(
                            "Function %s failed after %d attempts: %s",
                            func.__name__,
                            max_retries + 1,
                            exc,
                            exc_info=True,
                        )
                        raise

                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        "Function %s failed (attempt %d/%d): %s. Retrying in %.2fs...",
                        func.__name__,
                        attempt + 1,
                        max_retries + 1,
                        exc,
                        delay,
                    )

                    import time

                    time.sleep(delay)

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)

    return decorator
