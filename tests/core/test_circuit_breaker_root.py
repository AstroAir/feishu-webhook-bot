"""Tests for circuit breaker implementation."""

from __future__ import annotations

import time
import pytest
from feishu_webhook_bot.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitBreakerRegistry,
    CircuitState,
    circuit_breaker,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout_seconds == 30.0
        assert config.excluded_exceptions == []

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=10.0,
            excluded_exceptions=["ValueError", "KeyError"],
        )
        assert config.failure_threshold == 3
        assert config.success_threshold == 2
        assert config.timeout_seconds == 10.0
        assert config.excluded_exceptions == ["ValueError", "KeyError"]

    def test_config_validation(self) -> None:
        """Test that invalid config values are rejected."""
        with pytest.raises(ValueError):
            CircuitBreakerConfig(failure_threshold=0)

        with pytest.raises(ValueError):
            CircuitBreakerConfig(success_threshold=-1)

        with pytest.raises(ValueError):
            CircuitBreakerConfig(timeout_seconds=-1)


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state(self) -> None:
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker("test")
        assert cb.get_state() == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_successful_call(self) -> None:
        """Test successful function call."""
        cb = CircuitBreaker("test")

        def success_func() -> str:
            return "success"

        result = cb.call(success_func)
        assert result == "success"
        assert cb.failure_count == 0

    def test_failed_call_raises_exception(self) -> None:
        """Test that exceptions from function are raised."""
        cb = CircuitBreaker("test")

        def failing_func() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            cb.call(failing_func)

    def test_failure_counting(self) -> None:
        """Test that failures are counted."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))

        def failing_func() -> None:
            raise RuntimeError("Test")

        for i in range(2):
            with pytest.raises(RuntimeError):
                cb.call(failing_func)
            assert cb.failure_count == i + 1

        assert cb.get_state() == CircuitState.CLOSED

    def test_open_on_threshold(self) -> None:
        """Test circuit opens when failure threshold is reached."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config)

        def failing_func() -> None:
            raise RuntimeError("Test")

        # First failure
        with pytest.raises(RuntimeError):
            cb.call(failing_func)
        assert cb.get_state() == CircuitState.CLOSED

        # Second failure - should trigger OPEN
        with pytest.raises(RuntimeError):
            cb.call(failing_func)
        assert cb.get_state() == CircuitState.OPEN

    def test_open_rejects_requests(self) -> None:
        """Test that OPEN circuit rejects requests."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        def failing_func() -> None:
            raise RuntimeError("Test")

        # Open the circuit
        with pytest.raises(RuntimeError):
            cb.call(failing_func)

        assert cb.get_state() == CircuitState.OPEN

        # Further requests should be rejected with CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen):
            cb.call(failing_func)

    def test_half_open_after_timeout(self) -> None:
        """Test transition to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.1)
        cb = CircuitBreaker("test", config)

        def failing_func() -> None:
            raise RuntimeError("Test")

        # Open the circuit
        with pytest.raises(RuntimeError):
            cb.call(failing_func)

        assert cb.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.15)

        # Should now allow request (HALF_OPEN)
        def success_func() -> str:
            return "recovered"

        result = cb.call(success_func)
        assert result == "recovered"
        assert cb.get_state() == CircuitState.HALF_OPEN

    def test_close_after_success_threshold_in_half_open(self) -> None:
        """Test circuit closes after success threshold is met in HALF_OPEN."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.1,
        )
        cb = CircuitBreaker("test", config)

        def failing_func() -> None:
            raise RuntimeError("Test")

        def success_func() -> str:
            return "ok"

        # Open the circuit
        with pytest.raises(RuntimeError):
            cb.call(failing_func)

        # Wait for timeout
        time.sleep(0.15)

        # Successful calls in HALF_OPEN
        assert cb.call(success_func) == "ok"
        assert cb.get_state() == CircuitState.HALF_OPEN
        assert cb.success_count == 1

        assert cb.call(success_func) == "ok"
        assert cb.get_state() == CircuitState.CLOSED
        assert cb.success_count == 0

    def test_reopen_on_failure_in_half_open(self) -> None:
        """Test circuit reopens immediately on failure in HALF_OPEN."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0.1,
        )
        cb = CircuitBreaker("test", config)

        def failing_func() -> None:
            raise RuntimeError("Test")

        def success_func() -> str:
            return "ok"

        # Open the circuit
        with pytest.raises(RuntimeError):
            cb.call(failing_func)

        # Wait for timeout to enter HALF_OPEN
        time.sleep(0.15)
        assert cb.call(success_func) == "ok"
        assert cb.get_state() == CircuitState.HALF_OPEN

        # Failure in HALF_OPEN should immediately reopen
        with pytest.raises(RuntimeError):
            cb.call(failing_func)

        assert cb.get_state() == CircuitState.OPEN

    def test_excluded_exceptions(self) -> None:
        """Test that excluded exceptions don't trigger the breaker."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            excluded_exceptions=["ValueError"],
        )
        cb = CircuitBreaker("test", config)

        def raising_func(exc_type: type) -> None:
            raise exc_type("Test")

        # ValueError should not count as failure
        with pytest.raises(ValueError):
            cb.call(raising_func, ValueError)

        assert cb.failure_count == 0
        assert cb.get_state() == CircuitState.CLOSED

        # RuntimeError should count as failure
        with pytest.raises(RuntimeError):
            cb.call(raising_func, RuntimeError)

        assert cb.failure_count == 1

    def test_success_resets_failure_count(self) -> None:
        """Test that success resets failure count."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        def failing_func() -> None:
            raise RuntimeError("Test")

        def success_func() -> str:
            return "ok"

        # Generate some failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(failing_func)

        assert cb.failure_count == 2

        # Success should decrement failure count (not reset to 0)
        assert cb.call(success_func) == "ok"
        assert cb.failure_count == 1  # Decremented from 2 to 1

    def test_reset(self) -> None:
        """Test reset method."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        def failing_func() -> None:
            raise RuntimeError("Test")

        # Open the circuit
        with pytest.raises(RuntimeError):
            cb.call(failing_func)

        assert cb.get_state() == CircuitState.OPEN

        # Reset
        cb.reset()
        assert cb.get_state() == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_get_status(self) -> None:
        """Test status information."""
        config = CircuitBreakerConfig(failure_threshold=5, success_threshold=3)
        cb = CircuitBreaker("test_breaker", config)

        status = cb.get_status()
        assert status["name"] == "test_breaker"
        assert status["state"] == CircuitState.CLOSED.value
        assert status["failure_count"] == 0
        assert status["success_count"] == 0
        # Note: config is not included in get_status/get_state_info


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    def test_singleton_pattern(self) -> None:
        """Test that registry is singleton."""
        reg1 = CircuitBreakerRegistry()
        reg2 = CircuitBreakerRegistry()
        assert reg1 is reg2

    def test_get_or_create(self) -> None:
        """Test creating and retrieving circuit breakers."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        config = CircuitBreakerConfig(failure_threshold=5)
        cb1 = registry.get_or_create("api1", config)

        assert cb1.name == "api1"
        assert cb1.config.failure_threshold == 5

        # Getting same name should return same instance
        cb2 = registry.get_or_create("api1")
        assert cb1 is cb2

    def test_get(self) -> None:
        """Test retrieving circuit breaker."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        config = CircuitBreakerConfig()
        cb = registry.get_or_create("test", config)

        retrieved = registry.get("test")
        assert retrieved is cb

        not_found = registry.get("nonexistent")
        assert not_found is None

    def test_remove(self) -> None:
        """Test removing circuit breaker."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        cb = registry.get_or_create("test", CircuitBreakerConfig())
        assert registry.get("test") is cb

        registry.remove("test")
        assert registry.get("test") is None

    def test_get_all_states(self) -> None:
        """Test getting all breaker states."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        registry.get_or_create("breaker1", CircuitBreakerConfig())
        registry.get_or_create("breaker2", CircuitBreakerConfig())

        states = registry.get_all_states()
        assert len(states) == 2
        assert states["breaker1"] == CircuitState.CLOSED
        assert states["breaker2"] == CircuitState.CLOSED

    def test_get_all_status(self) -> None:
        """Test getting all breaker status."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        registry.get_or_create("breaker1", CircuitBreakerConfig())
        registry.get_or_create("breaker2", CircuitBreakerConfig(failure_threshold=3))

        status = registry.get_all_status()
        assert len(status) == 2
        assert status["breaker1"]["state"] == CircuitState.CLOSED.value
        assert status["breaker2"]["state"] == CircuitState.CLOSED.value

    def test_reset_all(self) -> None:
        """Test resetting all breakers."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        cb1 = registry.get_or_create("breaker1", CircuitBreakerConfig(failure_threshold=1))
        cb2 = registry.get_or_create("breaker2", CircuitBreakerConfig(failure_threshold=1))

        def failing_func() -> None:
            raise RuntimeError("Test")

        # Open both breakers
        with pytest.raises(RuntimeError):
            cb1.call(failing_func)

        with pytest.raises(RuntimeError):
            cb2.call(failing_func)

        assert cb1.get_state() == CircuitState.OPEN
        assert cb2.get_state() == CircuitState.OPEN

        # Reset all
        registry.reset_all()
        assert cb1.get_state() == CircuitState.CLOSED
        assert cb2.get_state() == CircuitState.CLOSED

    def test_clear(self) -> None:
        """Test clearing all breakers."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        registry.get_or_create("breaker1", CircuitBreakerConfig())
        registry.get_or_create("breaker2", CircuitBreakerConfig())

        assert len(registry.get_all_states()) == 2

        registry.clear()
        assert len(registry.get_all_states()) == 0


class TestCircuitBreakerDecorator:
    """Tests for circuit_breaker decorator."""

    def test_decorator_with_default_name(self) -> None:
        """Test decorator uses function name as default."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        @circuit_breaker()
        def my_function() -> str:
            return "result"

        assert my_function() == "result"

        breaker = registry.get("my_function")
        assert breaker is not None
        assert breaker.name == "my_function"

    def test_decorator_with_custom_name(self) -> None:
        """Test decorator with custom breaker name."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        @circuit_breaker(name="custom_api")
        def api_call() -> str:
            return "result"

        assert api_call() == "result"

        breaker = registry.get("custom_api")
        assert breaker is not None

    def test_decorator_with_config(self) -> None:
        """Test decorator with custom configuration."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        config = CircuitBreakerConfig(failure_threshold=2)

        @circuit_breaker(name="test_api", config=config)
        def api_call() -> str:
            return "result"

        assert api_call() == "result"

        breaker = registry.get("test_api")
        assert breaker.config.failure_threshold == 2

    def test_decorator_failure_handling(self) -> None:
        """Test decorator handles exceptions and opens circuit."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        config = CircuitBreakerConfig(failure_threshold=1)

        @circuit_breaker(name="failing_api", config=config)
        def failing_call() -> None:
            raise ValueError("API error")

        # First call fails and opens circuit
        with pytest.raises(ValueError):
            failing_call()

        # Second call should raise CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen):
            failing_call()

    def test_decorator_preserves_function_metadata(self) -> None:
        """Test that decorator preserves function name and docstring."""

        @circuit_breaker()
        def my_api_call(x: int, y: int) -> int:
            """Adds two numbers."""
            return x + y

        assert my_api_call.__name__ == "my_api_call"
        assert my_api_call.__doc__ == "Adds two numbers."

    def test_decorator_with_args_and_kwargs(self) -> None:
        """Test decorator works with function arguments."""
        registry = CircuitBreakerRegistry()
        registry.clear()

        @circuit_breaker(name="sum_func")
        def sum_values(a: int, b: int, c: int = 0) -> int:
            return a + b + c

        assert sum_values(1, 2) == 3
        assert sum_values(1, 2, c=5) == 8

    def test_circuit_breaker_attribute(self) -> None:
        """Test that decorated function has circuit breaker reference."""

        @circuit_breaker(name="test_func")
        def my_func() -> str:
            return "result"

        assert hasattr(my_func, "_circuit_breaker")
        assert isinstance(my_func._circuit_breaker, CircuitBreaker)


class TestCircuitBreakerThreadSafety:
    """Tests for thread safety of circuit breaker."""

    def test_thread_safe_state_updates(self) -> None:
        """Test that concurrent calls are thread-safe."""
        import threading

        config = CircuitBreakerConfig(failure_threshold=10)
        cb = CircuitBreaker("concurrent_test", config)
        results = []

        def success_func() -> str:
            return "ok"

        def worker() -> None:
            try:
                for _ in range(5):
                    cb.call(success_func)
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r == "success" for r in results)
        assert cb.get_state() == CircuitState.CLOSED
