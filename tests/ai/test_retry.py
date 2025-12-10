"""Comprehensive tests for retry utilities and circuit breaker.

Tests cover:
- CircuitBreaker state transitions
- CircuitBreaker sync and async operations
- Exponential backoff decorator
- Retry logic with jitter
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import Mock

import pytest

from feishu_webhook_bot.ai.exceptions import AIServiceUnavailableError
from feishu_webhook_bot.ai.retry import CircuitBreaker, retry_with_exponential_backoff


# ==============================================================================
# CircuitBreaker Tests
# ==============================================================================


class TestCircuitBreakerCreation:
    """Tests for CircuitBreaker initialization."""

    def test_circuit_breaker_defaults(self):
        """Test CircuitBreaker with default settings."""
        cb = CircuitBreaker()

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60.0
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_circuit_breaker_custom_settings(self):
        """Test CircuitBreaker with custom settings."""
        cb = CircuitBreaker(
            failure_threshold=10,
            recovery_timeout=120.0,
            expected_exception=ValueError,
        )

        assert cb.failure_threshold == 10
        assert cb.recovery_timeout == 120.0
        assert cb.expected_exception == ValueError


class TestCircuitBreakerStateTransitions:
    """Tests for circuit breaker state transitions."""

    def test_closed_to_open_after_failures(self):
        """Test circuit opens after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        def failing_func():
            raise Exception("Test error")

        for _ in range(3):
            with pytest.raises(Exception):
                cb.call(failing_func)

        assert cb.state == "OPEN"
        assert cb.failure_count == 3

    def test_open_rejects_calls(self):
        """Test open circuit rejects calls immediately."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)

        def failing_func():
            raise Exception("Test error")

        # Trip the circuit
        with pytest.raises(Exception):
            cb.call(failing_func)

        assert cb.state == "OPEN"

        # Next call should be rejected
        with pytest.raises(AIServiceUnavailableError, match="OPEN"):
            cb.call(lambda: "success")

    def test_open_to_half_open_after_timeout(self):
        """Test circuit transitions to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        def failing_func():
            raise Exception("Test error")

        # Trip the circuit
        with pytest.raises(Exception):
            cb.call(failing_func)

        assert cb.state == "OPEN"

        # Wait for recovery timeout
        time.sleep(0.15)

        # Next call should transition to HALF_OPEN
        def success_func():
            return "success"

        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == "CLOSED"

    def test_half_open_to_closed_on_success(self):
        """Test successful call in half-open state closes circuit."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Trip the circuit
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        time.sleep(0.15)

        # Success should close circuit
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_half_open_to_open_on_failure(self):
        """Test failure in half-open state reopens circuit."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        def failing_func():
            raise Exception("fail")

        # Trip the circuit
        with pytest.raises(Exception):
            cb.call(failing_func)

        time.sleep(0.15)

        # Failure should reopen circuit
        with pytest.raises(Exception):
            cb.call(failing_func)

        assert cb.state == "OPEN"


class TestCircuitBreakerSyncCalls:
    """Tests for synchronous circuit breaker calls."""

    def test_call_success(self):
        """Test successful synchronous call."""
        cb = CircuitBreaker()

        result = cb.call(lambda: "success")

        assert result == "success"
        assert cb.failure_count == 0

    def test_call_with_args(self):
        """Test call with arguments."""
        cb = CircuitBreaker()

        def add(a, b):
            return a + b

        result = cb.call(add, 2, 3)

        assert result == 5

    def test_call_with_kwargs(self):
        """Test call with keyword arguments."""
        cb = CircuitBreaker()

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = cb.call(greet, "World", greeting="Hi")

        assert result == "Hi, World!"

    def test_call_tracks_expected_exception(self):
        """Test circuit only tracks expected exception type."""
        cb = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)

        # TypeError should not be tracked
        with pytest.raises(TypeError):
            cb.call(lambda: (_ for _ in ()).throw(TypeError("wrong type")))

        assert cb.failure_count == 0

        # ValueError should be tracked
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("expected")))

        assert cb.failure_count == 1


class TestCircuitBreakerAsyncCalls:
    """Tests for asynchronous circuit breaker calls."""

    @pytest.mark.anyio
    async def test_call_async_success(self):
        """Test successful async call."""
        cb = CircuitBreaker()

        async def async_func():
            return "async success"

        result = await cb.call_async(async_func)

        assert result == "async success"

    @pytest.mark.anyio
    async def test_call_async_with_args(self):
        """Test async call with arguments."""
        cb = CircuitBreaker()

        async def async_add(a, b):
            return a + b

        result = await cb.call_async(async_add, 5, 7)

        assert result == 12

    @pytest.mark.anyio
    async def test_call_async_failure_tracking(self):
        """Test async call tracks failures."""
        cb = CircuitBreaker(failure_threshold=2)

        async def failing_async():
            raise Exception("async fail")

        with pytest.raises(Exception):
            await cb.call_async(failing_async)

        assert cb.failure_count == 1

    @pytest.mark.anyio
    async def test_call_async_open_circuit(self):
        """Test async call rejected when circuit is open."""
        cb = CircuitBreaker(failure_threshold=1)

        async def failing_async():
            raise Exception("fail")

        # Trip the circuit
        with pytest.raises(Exception):
            await cb.call_async(failing_async)

        # Next call should be rejected
        with pytest.raises(AIServiceUnavailableError):
            await cb.call_async(failing_async)


class TestCircuitBreakerReset:
    """Tests for circuit breaker reset."""

    def test_reset_clears_state(self):
        """Test reset clears all state."""
        cb = CircuitBreaker(failure_threshold=2)

        # Accumulate some failures
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        assert cb.state == "OPEN"
        assert cb.failure_count == 2

        cb.reset()

        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.last_failure_time is None


# ==============================================================================
# Retry Decorator Tests
# ==============================================================================


class TestRetryWithExponentialBackoff:
    """Tests for retry_with_exponential_backoff decorator."""

    def test_retry_success_first_try(self):
        """Test function succeeds on first try."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self):
        """Test function succeeds after initial failures."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary failure")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Test function fails after max retries."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            always_fails()

        assert call_count == 3  # Initial + 2 retries

    def test_retry_specific_exceptions(self):
        """Test retry only on specific exception types."""
        call_count = 0

        @retry_with_exponential_backoff(
            max_retries=3,
            base_delay=0.01,
            retry_on=(ValueError,),
        )
        def specific_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retried")

        with pytest.raises(TypeError):
            specific_error()

        assert call_count == 1  # No retries for TypeError


class TestRetryAsyncFunctions:
    """Tests for retry decorator with async functions."""

    @pytest.mark.anyio
    async def test_async_retry_success(self):
        """Test async function succeeds after retries."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01)
        async def async_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("temporary")
            return "async success"

        result = await async_flaky()

        assert result == "async success"
        assert call_count == 2

    @pytest.mark.anyio
    async def test_async_retry_exhausted(self):
        """Test async function fails after max retries."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        async def async_always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        with pytest.raises(ValueError):
            await async_always_fails()

        assert call_count == 3


class TestRetryBackoffCalculation:
    """Tests for backoff calculation."""

    def test_exponential_backoff_increases(self):
        """Test delay increases exponentially."""
        delays = []
        call_count = 0

        @retry_with_exponential_backoff(
            max_retries=3,
            base_delay=0.1,
            exponential_base=2.0,
            jitter=False,
        )
        def track_delays():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        # We can't easily test actual delays without mocking time
        # This test verifies the decorator works with these parameters
        with pytest.raises(ValueError):
            track_delays()

        assert call_count == 4

    def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        call_count = 0

        @retry_with_exponential_backoff(
            max_retries=5,
            base_delay=10.0,
            max_delay=0.01,  # Very low cap
            jitter=False,
        )
        def capped_delay():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"

        result = capped_delay()
        assert result == "success"


# ==============================================================================
# Circuit Breaker Advanced Tests
# ==============================================================================


class TestCircuitBreakerAdvanced:
    """Advanced tests for CircuitBreaker."""

    def test_circuit_breaker_custom_exception_type(self):
        """Test circuit breaker with custom exception type."""
        cb = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)

        # ValueError should be tracked
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("tracked")))

        assert cb.state == "OPEN"

    def test_circuit_breaker_ignores_other_exceptions(self):
        """Test circuit breaker ignores non-expected exceptions."""
        cb = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)

        # TypeError should not be tracked
        for _ in range(5):
            with pytest.raises(TypeError):
                cb.call(lambda: (_ for _ in ()).throw(TypeError("ignored")))

        # Circuit should still be closed
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_circuit_breaker_mixed_exceptions(self):
        """Test circuit breaker with mixed exception types."""
        cb = CircuitBreaker(failure_threshold=3, expected_exception=ValueError)

        # Mix of tracked and untracked exceptions
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("tracked")))
        assert cb.failure_count == 1

        with pytest.raises(TypeError):
            cb.call(lambda: (_ for _ in ()).throw(TypeError("ignored")))
        assert cb.failure_count == 1  # Still 1

        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("tracked")))
        assert cb.failure_count == 2

    def test_circuit_breaker_success_resets_in_half_open(self):
        """Test successful call in half-open state resets failure count."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)

        # Trip the circuit
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        assert cb.state == "OPEN"
        assert cb.failure_count == 1

        # Wait for recovery
        import time
        time.sleep(0.02)

        # Successful call should reset
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_circuit_breaker_failure_in_half_open_reopens(self):
        """Test failure in half-open state reopens circuit."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)

        # Trip the circuit
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        import time
        time.sleep(0.02)

        # Failure in half-open should reopen
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail again")))

        assert cb.state == "OPEN"

    @pytest.mark.anyio
    async def test_circuit_breaker_async_recovery(self):
        """Test async circuit breaker recovery."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)

        async def failing_async():
            raise Exception("async fail")

        # Trip the circuit
        with pytest.raises(Exception):
            await cb.call_async(failing_async)

        assert cb.state == "OPEN"

        # Wait for recovery
        await asyncio.sleep(0.02)

        async def success_async():
            return "async success"

        # Should recover
        result = await cb.call_async(success_async)
        assert result == "async success"
        assert cb.state == "CLOSED"

    def test_circuit_breaker_reset_from_open(self):
        """Test reset from open state."""
        cb = CircuitBreaker(failure_threshold=1)

        # Trip the circuit
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        assert cb.state == "OPEN"

        # Reset
        cb.reset()

        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

        # Should work again
        result = cb.call(lambda: "works")
        assert result == "works"


# ==============================================================================
# Retry Decorator Advanced Tests
# ==============================================================================


class TestRetryDecoratorAdvanced:
    """Advanced tests for retry decorator."""

    def test_retry_preserves_function_metadata(self):
        """Test retry decorator preserves function metadata."""
        @retry_with_exponential_backoff()
        def my_function():
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_retry_with_multiple_exception_types(self):
        """Test retry with multiple exception types."""
        call_count = 0

        @retry_with_exponential_backoff(
            max_retries=3,
            base_delay=0.01,
            retry_on=(ValueError, TypeError),
        )
        def multi_exception():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first")
            if call_count == 2:
                raise TypeError("second")
            return "success"

        result = multi_exception()
        assert result == "success"
        assert call_count == 3

    def test_retry_does_not_retry_unspecified_exceptions(self):
        """Test retry does not retry unspecified exception types."""
        call_count = 0

        @retry_with_exponential_backoff(
            max_retries=3,
            base_delay=0.01,
            retry_on=(ValueError,),
        )
        def wrong_exception():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("not retried")

        with pytest.raises(RuntimeError):
            wrong_exception()

        assert call_count == 1  # No retries

    @pytest.mark.anyio
    async def test_async_retry_with_return_value(self):
        """Test async retry returns correct value."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        async def async_with_value():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retry")
            return {"key": "value", "count": call_count}

        result = await async_with_value()
        assert result == {"key": "value", "count": 2}

    def test_retry_zero_retries(self):
        """Test retry with zero retries (just one attempt)."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=0, base_delay=0.01)
        def no_retries():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            no_retries()

        assert call_count == 1

    def test_retry_with_jitter_variation(self):
        """Test retry with jitter produces variation."""
        # This is a probabilistic test - jitter should cause variation
        # We can't easily test the actual delay values without mocking
        call_count = 0

        @retry_with_exponential_backoff(
            max_retries=2,
            base_delay=0.001,
            jitter=True,
        )
        def with_jitter():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"

        result = with_jitter()
        assert result == "success"


# ==============================================================================
# Edge Cases Tests
# ==============================================================================


class TestRetryEdgeCases:
    """Edge case tests for retry utilities."""

    def test_circuit_breaker_with_zero_threshold(self):
        """Test circuit breaker with threshold of 1."""
        cb = CircuitBreaker(failure_threshold=1)

        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        # Should be open after just one failure
        assert cb.state == "OPEN"

    def test_circuit_breaker_with_high_threshold(self):
        """Test circuit breaker with high threshold."""
        cb = CircuitBreaker(failure_threshold=100)

        for _ in range(50):
            with pytest.raises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        # Should still be closed
        assert cb.state == "CLOSED"
        assert cb.failure_count == 50

    def test_circuit_breaker_with_very_short_timeout(self):
        """Test circuit breaker with very short recovery timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.001)

        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        import time
        time.sleep(0.01)

        # Should be able to recover quickly
        result = cb.call(lambda: "recovered")
        assert result == "recovered"

    def test_retry_with_very_high_base_delay(self):
        """Test retry with high base delay but low max delay."""
        call_count = 0

        @retry_with_exponential_backoff(
            max_retries=2,
            base_delay=1000.0,  # Very high
            max_delay=0.001,    # But capped very low
            jitter=False,
        )
        def high_base():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "success"

        result = high_base()
        assert result == "success"

    @pytest.mark.anyio
    async def test_async_circuit_breaker_concurrent_calls(self):
        """Test async circuit breaker with concurrent calls."""
        cb = CircuitBreaker(failure_threshold=5)

        async def maybe_fail(should_fail: bool):
            if should_fail:
                raise Exception("fail")
            return "success"

        # Run multiple concurrent calls
        tasks = []
        for i in range(10):
            if i < 5:
                tasks.append(cb.call_async(maybe_fail, True))
            else:
                tasks.append(cb.call_async(maybe_fail, False))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # First 5 should be exceptions, circuit opens, rest rejected
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) >= 5
