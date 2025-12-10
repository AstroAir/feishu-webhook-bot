#!/usr/bin/env python3
"""AI Retry Mechanism Example.

This example demonstrates retry mechanisms for AI operations:
- Exponential backoff retry
- Circuit breaker pattern for AI calls
- Rate limit handling
- Timeout management
- Error classification and handling
- Retry policies and strategies

The retry mechanisms ensure reliable AI interactions despite transient failures.
"""

import asyncio
import random
import time
from typing import Any

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)

# Check for AI dependencies
try:
    from feishu_webhook_bot.ai import CircuitBreaker, retry_with_exponential_backoff
    from feishu_webhook_bot.ai.exceptions import (
        AIError,
        AIServiceUnavailableError,
        RateLimitError,
        TokenLimitExceededError,
    )

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("AI dependencies not available. Install with: pip install pydantic-ai")


# =============================================================================
# Demo 1: Basic Exponential Backoff
# =============================================================================
async def demo_basic_exponential_backoff() -> None:
    """Demonstrate basic exponential backoff retry."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Exponential Backoff")
    print("=" * 60)

    print("Exponential backoff increases delay between retries:")
    print("  Attempt 1: Wait 1s")
    print("  Attempt 2: Wait 2s")
    print("  Attempt 3: Wait 4s")
    print("  Attempt 4: Wait 8s")
    print("  ...")

    # Simulate exponential backoff
    base_delay = 1.0
    max_retries = 5

    print(f"\nSimulating {max_retries} retry attempts:")
    for attempt in range(max_retries):
        delay = base_delay * (2**attempt)
        jitter = random.uniform(0, 0.1 * delay)  # Add jitter
        total_delay = delay + jitter
        print(f"  Attempt {attempt + 1}: delay = {total_delay:.2f}s")


# =============================================================================
# Demo 2: Retry Decorator
# =============================================================================
async def demo_retry_decorator() -> None:
    """Demonstrate retry decorator usage."""
    print("\n" + "=" * 60)
    print("Demo 2: Retry Decorator")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    # Counter for tracking attempts
    attempt_count = [0]

    @retry_with_exponential_backoff(max_retries=3, base_delay=0.1)
    async def unreliable_operation() -> str:
        """Operation that fails sometimes."""
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ConnectionError(f"Attempt {attempt_count[0]} failed")
        return "Success!"

    print("Executing unreliable operation with retry decorator...")
    try:
        result = await unreliable_operation()
        print(f"Result: {result}")
        print(f"Total attempts: {attempt_count[0]}")
    except Exception as e:
        print(f"Failed after all retries: {e}")


# =============================================================================
# Demo 3: Circuit Breaker for AI
# =============================================================================
async def demo_ai_circuit_breaker() -> None:
    """Demonstrate circuit breaker for AI operations."""
    print("\n" + "=" * 60)
    print("Demo 3: Circuit Breaker for AI")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    # Create circuit breaker (AI module version)
    cb = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=5.0,
        expected_exception=AIServiceUnavailableError,
    )

    print("Circuit Breaker Configuration:")
    print(f"  Failure threshold: {cb.failure_threshold}")
    print(f"  Recovery timeout: {cb.recovery_timeout}s")
    print(f"  Expected exception: {cb.expected_exception.__name__}")

    # Simulate operations
    async def ai_call(should_fail: bool = False) -> str:
        if should_fail:
            raise AIServiceUnavailableError("AI service unavailable")
        return "AI response"

    print("\n--- Simulating circuit breaker behavior ---")

    # Normal operation using call_async
    print("\n1. Normal operation (circuit CLOSED):")
    for i in range(2):
        try:
            result = await cb.call_async(ai_call, should_fail=False)
            print(f"   Call {i + 1}: Success - {result}")
        except AIServiceUnavailableError as e:
            print(f"   Call {i + 1}: Failed - {e}")

    print(f"   Circuit state: {cb.state}")

    # Failing operations to open circuit
    print("\n2. Failing operations (opening circuit):")
    for i in range(4):
        try:
            await cb.call_async(ai_call, should_fail=True)
            print(f"   Call {i + 1}: Success")
        except AIServiceUnavailableError as e:
            print(f"   Call {i + 1}: Failed - {type(e).__name__}")

    print(f"   Circuit state: {cb.state}")


# =============================================================================
# Demo 4: Rate Limit Handling
# =============================================================================
async def demo_rate_limit_handling() -> None:
    """Demonstrate rate limit handling."""
    print("\n" + "=" * 60)
    print("Demo 4: Rate Limit Handling")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    class RateLimitedClient:
        """Client with rate limit handling."""

        def __init__(self, requests_per_minute: int = 60):
            self.requests_per_minute = requests_per_minute
            self.request_times: list[float] = []

        async def call_with_rate_limit(self, func, *args, **kwargs) -> Any:
            """Execute function with rate limiting."""
            # Clean old requests
            current_time = time.time()
            self.request_times = [
                t for t in self.request_times if current_time - t < 60
            ]

            # Check rate limit
            if len(self.request_times) >= self.requests_per_minute:
                wait_time = 60 - (current_time - self.request_times[0])
                print(f"    Rate limited, waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)

            # Record request
            self.request_times.append(time.time())

            # Execute
            return await func(*args, **kwargs)

    client = RateLimitedClient(requests_per_minute=5)

    async def mock_ai_call(prompt: str) -> str:
        await asyncio.sleep(0.1)
        return f"Response to: {prompt[:20]}..."

    print("Rate limited client (5 requests/minute):")
    print("\nMaking 7 requests:")

    for i in range(7):
        result = await client.call_with_rate_limit(mock_ai_call, f"Prompt {i + 1}")
        print(f"  Request {i + 1}: {result}")


# =============================================================================
# Demo 5: Timeout Management
# =============================================================================
async def demo_timeout_management() -> None:
    """Demonstrate timeout management for AI calls."""
    print("\n" + "=" * 60)
    print("Demo 5: Timeout Management")
    print("=" * 60)

    async def slow_ai_call(delay: float) -> str:
        """Simulated slow AI call."""
        await asyncio.sleep(delay)
        return "Response"

    async def call_with_timeout(timeout: float, delay: float) -> str | None:
        """Call with timeout."""
        try:
            result = await asyncio.wait_for(slow_ai_call(delay), timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return None

    print("Testing timeout behavior:")

    test_cases = [
        (2.0, 0.5, "Should succeed"),
        (0.5, 2.0, "Should timeout"),
        (1.0, 0.8, "Should succeed (close)"),
    ]

    for timeout, delay, description in test_cases:
        print(f"\n  {description}:")
        print(f"    Timeout: {timeout}s, Delay: {delay}s")
        result = await call_with_timeout(timeout, delay)
        if result:
            print(f"    Result: {result}")
        else:
            print("    Result: TIMEOUT")


# =============================================================================
# Demo 6: Error Classification
# =============================================================================
def demo_error_classification() -> None:
    """Demonstrate AI error classification."""
    print("\n" + "=" * 60)
    print("Demo 6: Error Classification")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    print("AI Error Hierarchy:")
    print("""
    AIError (base)
    ├── AIServiceUnavailableError (retryable)
    │   - Service temporarily unavailable
    │   - Network issues
    │
    ├── RateLimitError (retryable with backoff)
    │   - Too many requests
    │   - Quota exceeded
    │
    ├── TokenLimitExceededError (not retryable)
    │   - Input too long
    │   - Context window exceeded
    │
    ├── ModelResponseError (may be retryable)
    │   - Invalid response format
    │   - Parsing errors
    │
    └── ConfigurationError (not retryable)
        - Invalid API key
        - Missing configuration
    """)

    # Error handling pattern
    print("Error handling pattern:")
    print("""
    async def call_ai_with_error_handling(prompt: str) -> str:
        try:
            return await ai_agent.run(prompt)
        
        except RateLimitError as e:
            # Wait and retry
            await asyncio.sleep(e.retry_after or 60)
            return await call_ai_with_error_handling(prompt)
        
        except AIServiceUnavailableError:
            # Retry with exponential backoff
            raise  # Let retry decorator handle
        
        except TokenLimitExceededError:
            # Truncate input and retry
            truncated = prompt[:len(prompt) // 2]
            return await call_ai_with_error_handling(truncated)
        
        except ConfigurationError:
            # Cannot recover, re-raise
            raise
    """)


# =============================================================================
# Demo 7: Retry Policies
# =============================================================================
async def demo_retry_policies() -> None:
    """Demonstrate different retry policies."""
    print("\n" + "=" * 60)
    print("Demo 7: Retry Policies")
    print("=" * 60)

    class RetryPolicy:
        """Base retry policy."""

        def should_retry(self, attempt: int, error: Exception) -> bool:
            raise NotImplementedError

        def get_delay(self, attempt: int) -> float:
            raise NotImplementedError

    class ExponentialBackoffPolicy(RetryPolicy):
        """Exponential backoff with jitter."""

        def __init__(
            self,
            max_retries: int = 3,
            base_delay: float = 1.0,
            max_delay: float = 60.0,
        ):
            self.max_retries = max_retries
            self.base_delay = base_delay
            self.max_delay = max_delay

        def should_retry(self, attempt: int, error: Exception) -> bool:
            return attempt < self.max_retries

        def get_delay(self, attempt: int) -> float:
            delay = self.base_delay * (2**attempt)
            jitter = random.uniform(0, 0.1 * delay)
            return min(delay + jitter, self.max_delay)

    class LinearBackoffPolicy(RetryPolicy):
        """Linear backoff."""

        def __init__(self, max_retries: int = 3, delay_increment: float = 2.0):
            self.max_retries = max_retries
            self.delay_increment = delay_increment

        def should_retry(self, attempt: int, error: Exception) -> bool:
            return attempt < self.max_retries

        def get_delay(self, attempt: int) -> float:
            return self.delay_increment * (attempt + 1)

    class NoRetryPolicy(RetryPolicy):
        """No retry - fail immediately."""

        def should_retry(self, attempt: int, error: Exception) -> bool:
            return False

        def get_delay(self, attempt: int) -> float:
            return 0

    # Compare policies
    policies = [
        ("Exponential Backoff", ExponentialBackoffPolicy()),
        ("Linear Backoff", LinearBackoffPolicy()),
        ("No Retry", NoRetryPolicy()),
    ]

    print("Retry policy comparison (5 attempts):")
    for name, policy in policies:
        print(f"\n  {name}:")
        for attempt in range(5):
            should_retry = policy.should_retry(attempt, Exception())
            delay = policy.get_delay(attempt)
            status = "retry" if should_retry else "stop"
            print(f"    Attempt {attempt + 1}: {status}, delay = {delay:.2f}s")


# =============================================================================
# Demo 8: Adaptive Retry
# =============================================================================
async def demo_adaptive_retry() -> None:
    """Demonstrate adaptive retry based on error type."""
    print("\n" + "=" * 60)
    print("Demo 8: Adaptive Retry")
    print("=" * 60)

    if not AI_AVAILABLE:
        print("Skipping - AI dependencies not available")
        return

    class AdaptiveRetryHandler:
        """Retry handler that adapts based on error type."""

        def __init__(self):
            self.error_counts: dict[str, int] = {}

        def get_retry_config(self, error: Exception) -> dict[str, Any]:
            """Get retry configuration based on error type."""
            error_type = type(error).__name__

            if isinstance(error, RateLimitError):
                return {
                    "should_retry": True,
                    "max_retries": 5,
                    "base_delay": 60.0,  # Longer delay for rate limits
                    "strategy": "fixed",
                }
            elif isinstance(error, AIServiceUnavailableError):
                return {
                    "should_retry": True,
                    "max_retries": 3,
                    "base_delay": 1.0,
                    "strategy": "exponential",
                }
            elif isinstance(error, TokenLimitExceededError):
                return {
                    "should_retry": False,
                    "reason": "Input too long, cannot retry",
                }
            else:
                return {
                    "should_retry": True,
                    "max_retries": 2,
                    "base_delay": 0.5,
                    "strategy": "exponential",
                }

        def record_error(self, error: Exception) -> None:
            """Record error for tracking."""
            error_type = type(error).__name__
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        def get_error_stats(self) -> dict[str, int]:
            """Get error statistics."""
            return dict(self.error_counts)

    handler = AdaptiveRetryHandler()

    # Test different error types
    errors = [
        RateLimitError("Rate limit exceeded"),
        AIServiceUnavailableError("Service unavailable"),
        TokenLimitExceededError("Token limit exceeded", tokens_used=5000, token_limit=4096),
        AIError("Generic AI error"),
    ]

    print("Adaptive retry configurations:")
    for error in errors:
        config = handler.get_retry_config(error)
        handler.record_error(error)
        print(f"\n  {type(error).__name__}:")
        for key, value in config.items():
            print(f"    {key}: {value}")

    print(f"\nError statistics: {handler.get_error_stats()}")


# =============================================================================
# Demo 9: Real-World Retry Pattern
# =============================================================================
async def demo_real_world_pattern() -> None:
    """Demonstrate a real-world retry pattern."""
    print("\n" + "=" * 60)
    print("Demo 9: Real-World Retry Pattern")
    print("=" * 60)

    class AIClientWithRetry:
        """AI client with comprehensive retry handling."""

        def __init__(
            self,
            max_retries: int = 3,
            base_delay: float = 1.0,
            timeout: float = 30.0,
        ):
            self.max_retries = max_retries
            self.base_delay = base_delay
            self.timeout = timeout
            self._request_count = 0
            self._error_count = 0
            self._success_count = 0

        async def call(self, prompt: str) -> str:
            """Make AI call with retry handling."""
            last_error = None

            for attempt in range(self.max_retries + 1):
                self._request_count += 1

                try:
                    # Simulate AI call
                    result = await self._make_request(prompt, attempt)
                    self._success_count += 1
                    return result

                except Exception as e:
                    last_error = e
                    self._error_count += 1

                    if attempt < self.max_retries:
                        delay = self._calculate_delay(attempt, e)
                        print(f"    Attempt {attempt + 1} failed, retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                    else:
                        print(f"    All {self.max_retries + 1} attempts failed")

            raise last_error or Exception("Unknown error")

        async def _make_request(self, prompt: str, attempt: int) -> str:
            """Simulate AI request."""
            # Simulate failures for first few attempts
            if attempt < 2 and random.random() < 0.7:
                raise ConnectionError("Simulated connection error")
            await asyncio.sleep(0.1)
            return f"Response to: {prompt[:30]}..."

        def _calculate_delay(self, attempt: int, error: Exception) -> float:
            """Calculate retry delay."""
            delay = self.base_delay * (2**attempt)
            jitter = random.uniform(0, 0.1 * delay)
            return delay + jitter

        def get_stats(self) -> dict[str, Any]:
            """Get client statistics."""
            return {
                "total_requests": self._request_count,
                "successes": self._success_count,
                "errors": self._error_count,
                "success_rate": (
                    self._success_count / self._request_count * 100
                    if self._request_count > 0
                    else 0
                ),
            }

    # Use the client
    client = AIClientWithRetry(max_retries=3, base_delay=0.2)

    print("Making AI calls with retry handling:")
    for i in range(3):
        print(f"\n  Call {i + 1}:")
        try:
            result = await client.call(f"Test prompt {i + 1}")
            print(f"    Result: {result}")
        except Exception as e:
            print(f"    Failed: {e}")

    print(f"\n--- Client Statistics ---")
    stats = client.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.1f}%")
        else:
            print(f"  {key}: {value}")


# =============================================================================
# Main Entry Point
# =============================================================================
async def main() -> None:
    """Run all retry mechanism demonstrations."""
    print("=" * 60)
    print("AI Retry Mechanism Examples")
    print("=" * 60)

    demos = [
        ("Basic Exponential Backoff", demo_basic_exponential_backoff),
        ("Retry Decorator", demo_retry_decorator),
        ("Circuit Breaker for AI", demo_ai_circuit_breaker),
        ("Rate Limit Handling", demo_rate_limit_handling),
        ("Timeout Management", demo_timeout_management),
        ("Error Classification", demo_error_classification),
        ("Retry Policies", demo_retry_policies),
        ("Adaptive Retry", demo_adaptive_retry),
        ("Real-World Retry Pattern", demo_real_world_pattern),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            if asyncio.iscoroutinefunction(demo_func):
                await demo_func()
            else:
                demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
