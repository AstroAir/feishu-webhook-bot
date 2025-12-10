"""Comprehensive tests for circuit breaker pattern implementation.

Tests cover:
- CircuitState enum
- CircuitBreakerConfig validation
- CircuitBreakerOpen exception
- CircuitBreaker state transitions
- CircuitBreaker call method
- CircuitBreaker decorator
- CircuitBreakerRegistry singleton
"""

from __future__ import annotations

import threading
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


# ==============================================================================
# CircuitState Tests
# ==============================================================================


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_circuit_state_values(self):
        """Test CircuitState enum values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_circuit_state_is_string_enum(self):
        """Test CircuitState is a string enum."""
        assert isinstance(CircuitState.CLOSED, str)
        assert CircuitState.CLOSED == "closed"


# ==============================================================================
# CircuitBreakerConfig Tests
# ==============================================================================


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout_seconds == 30.0
        assert config.excluded_exceptions == []

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=5,
            timeout_seconds=60.0,
            excluded_exceptions=["ValueError", "KeyError"],
        )

        assert config.failure_threshold == 10
        assert config.success_threshold == 5
        assert config.timeout_seconds == 60.0
        assert config.excluded_exceptions == ["ValueError", "KeyError"]

    def test_config_validation_failure_threshold(self):
        """Test failure_threshold must be >= 1."""
        with pytest.raises(ValueError):
            CircuitBreakerConfig(failure_threshold=0)

    def test_config_validation_success_threshold(self):
        """Test success_threshold must be >= 1."""
        with pytest.raises(ValueError):
            CircuitBreakerConfig(success_threshold=0)

    def test_config_validation_timeout(self):
        """Test timeout_seconds must be >= 0."""
        with pytest.raises(ValueError):
            CircuitBreakerConfig(timeout_seconds=-1.0)


# ==============================================================================
# CircuitBreakerOpen Exception Tests
# ==============================================================================


class TestCircuitBreakerOpen:
    """Tests for CircuitBreakerOpen exception."""

    def test_exception_attributes(self):
        """Test exception has correct attributes."""
        exc = CircuitBreakerOpen("test_circuit", 15.5)

        assert exc.name == "test_circuit"
        assert exc.remaining_seconds == 15.5

    def test_exception_message(self):
        """Test exception message format."""
        exc = CircuitBreakerOpen("my_circuit", 10.0)

        message = str(exc)

        assert "my_circuit" in message
        assert "10.0" in message
        assert "open" in message.lower()


# ==============================================================================
# CircuitBreaker State Transition Tests
# ==============================================================================


class TestCircuitBreakerStateTransitions:
    """Tests for CircuitBreaker state transitions."""

    def test_initial_state_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker("test")

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_closed_to_open_after_failures(self):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    def test_open_blocks_requests(self):
        """Test open circuit blocks requests."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=60.0)
        cb = CircuitBreaker("test", config)

        cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.should_allow_request() is False

    def test_open_to_half_open_after_timeout(self):
        """Test circuit transitions to half-open after timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.1)
        cb = CircuitBreaker("test", config)

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)

        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_after_successes(self):
        """Test circuit closes after success threshold in half-open."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,  # Need 2 successes to close
            timeout_seconds=0.1,
        )
        cb = CircuitBreaker("test", config)

        # Open the circuit
        cb.record_failure()
        time.sleep(0.15)

        # Verify we're in half-open state
        assert cb.state == CircuitState.HALF_OPEN

        # Record successes to close the circuit
        # Note: Don't check state between successes as it resets success_count
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self):
        """Test circuit reopens on failure in half-open."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.1)
        cb = CircuitBreaker("test", config)

        # Open the circuit
        cb.record_failure()
        time.sleep(0.15)

        assert cb.state == CircuitState.HALF_OPEN

        # Failure in half-open reopens
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


# ==============================================================================
# CircuitBreaker Call Method Tests
# ==============================================================================


class TestCircuitBreakerCall:
    """Tests for CircuitBreaker.call method."""

    def test_call_success(self):
        """Test successful call through circuit breaker."""
        cb = CircuitBreaker("test")

        def success_func():
            return "success"

        result = cb.call(success_func)

        assert result == "success"

    def test_call_with_args(self):
        """Test call with arguments."""
        cb = CircuitBreaker("test")

        def add(a, b):
            return a + b

        result = cb.call(add, 2, 3)

        assert result == 5

    def test_call_with_kwargs(self):
        """Test call with keyword arguments."""
        cb = CircuitBreaker("test")

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = cb.call(greet, "World", greeting="Hi")

        assert result == "Hi, World!"

    def test_call_failure_propagates(self):
        """Test exceptions propagate through circuit breaker."""
        cb = CircuitBreaker("test")

        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            cb.call(failing_func)

    def test_call_records_failure(self):
        """Test call records failure on exception."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config)

        def failing_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            cb.call(failing_func)

        assert cb.failure_count == 1

    def test_call_blocked_when_open(self):
        """Test call raises CircuitBreakerOpen when circuit is open."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=60.0)
        cb = CircuitBreaker("test", config)

        cb.record_failure()

        with pytest.raises(CircuitBreakerOpen) as exc_info:
            cb.call(lambda: "success")

        assert exc_info.value.name == "test"


# ==============================================================================
# CircuitBreaker Excluded Exceptions Tests
# ==============================================================================


class TestCircuitBreakerExcludedExceptions:
    """Tests for excluded exceptions."""

    def test_excluded_exception_not_counted(self):
        """Test excluded exceptions don't count as failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            excluded_exceptions=["ValueError"],
        )
        cb = CircuitBreaker("test", config)

        # Record excluded exception
        cb.record_failure(ValueError("excluded"))

        assert cb.failure_count == 0

    def test_non_excluded_exception_counted(self):
        """Test non-excluded exceptions count as failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            excluded_exceptions=["ValueError"],
        )
        cb = CircuitBreaker("test", config)

        # Record non-excluded exception
        cb.record_failure(TypeError("not excluded"))

        assert cb.failure_count == 1


# ==============================================================================
# CircuitBreaker Reset Tests
# ==============================================================================


class TestCircuitBreakerReset:
    """Tests for CircuitBreaker.reset method."""

    def test_reset_clears_state(self):
        """Test reset clears all state."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0


# ==============================================================================
# CircuitBreaker State Info Tests
# ==============================================================================


class TestCircuitBreakerStateInfo:
    """Tests for CircuitBreaker state info methods."""

    def test_get_state_info(self):
        """Test get_state_info returns correct info."""
        cb = CircuitBreaker("test_circuit")
        cb.record_failure()

        info = cb.get_state_info()

        assert info["name"] == "test_circuit"
        assert info["state"] == "closed"
        assert info["failure_count"] == 1
        assert info["success_count"] == 0

    def test_get_status_alias(self):
        """Test get_status is alias for get_state_info."""
        cb = CircuitBreaker("test")

        info = cb.get_state_info()
        status = cb.get_status()

        assert info == status


# ==============================================================================
# CircuitBreaker Decorator Tests
# ==============================================================================


class TestCircuitBreakerDecorator:
    """Tests for circuit_breaker decorator."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before and after each test."""
        CircuitBreakerRegistry.reset_instance()
        yield
        CircuitBreakerRegistry.reset_instance()

    def test_decorator_wraps_function(self):
        """Test decorator wraps function."""
        @circuit_breaker(name="test_func")
        def my_func():
            return "result"

        result = my_func()

        assert result == "result"

    def test_decorator_uses_function_name(self):
        """Test decorator uses function name when name not provided."""
        @circuit_breaker()
        def named_function():
            return "result"

        # Should have circuit breaker attached
        assert hasattr(named_function, "_circuit_breaker")
        assert named_function._circuit_breaker.name == "named_function"

    def test_decorator_with_config(self):
        """Test decorator with custom config."""
        config = CircuitBreakerConfig(failure_threshold=10)

        @circuit_breaker(name="custom", config=config)
        def custom_func():
            return "result"

        cb = custom_func._circuit_breaker
        assert cb.config.failure_threshold == 10


# ==============================================================================
# CircuitBreakerRegistry Tests
# ==============================================================================


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before and after each test."""
        CircuitBreakerRegistry.reset_instance()
        yield
        CircuitBreakerRegistry.reset_instance()

    def test_registry_singleton(self):
        """Test registry is singleton."""
        reg1 = CircuitBreakerRegistry()
        reg2 = CircuitBreakerRegistry()

        assert reg1 is reg2

    def test_get_or_create(self):
        """Test get_or_create creates new circuit breaker."""
        registry = CircuitBreakerRegistry()

        cb = registry.get_or_create("test")

        assert cb is not None
        assert cb.name == "test"

    def test_get_or_create_returns_existing(self):
        """Test get_or_create returns existing circuit breaker."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("test")
        cb2 = registry.get_or_create("test")

        assert cb1 is cb2

    def test_get_existing(self):
        """Test get returns existing circuit breaker."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("test")

        cb = registry.get("test")

        assert cb is not None
        assert cb.name == "test"

    def test_get_nonexistent(self):
        """Test get returns None for nonexistent."""
        registry = CircuitBreakerRegistry()

        cb = registry.get("nonexistent")

        assert cb is None

    def test_remove(self):
        """Test remove removes circuit breaker."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("test")

        registry.remove("test")

        assert registry.get("test") is None

    def test_get_all_states(self):
        """Test get_all_states returns all states."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("cb1")
        registry.get_or_create("cb2")

        states = registry.get_all_states()

        assert "cb1" in states
        assert "cb2" in states
        assert states["cb1"] == CircuitState.CLOSED

    def test_get_all_status(self):
        """Test get_all_status returns all status info."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("cb1")

        status = registry.get_all_status()

        assert "cb1" in status
        assert "state" in status["cb1"]

    def test_reset_all(self):
        """Test reset_all resets all circuit breakers."""
        registry = CircuitBreakerRegistry()
        cb = registry.get_or_create("test", CircuitBreakerConfig(failure_threshold=1))
        cb.record_failure()

        assert cb.state == CircuitState.OPEN

        registry.reset_all()

        assert cb.state == CircuitState.CLOSED

    def test_clear(self):
        """Test clear removes all circuit breakers."""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("cb1")
        registry.get_or_create("cb2")

        registry.clear()

        assert registry.get("cb1") is None
        assert registry.get("cb2") is None


# ==============================================================================
# Thread Safety Tests
# ==============================================================================


class TestCircuitBreakerThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_failures(self):
        """Test concurrent failure recording."""
        # Set threshold high enough that we can record many failures
        # before the circuit opens
        config = CircuitBreakerConfig(failure_threshold=1000)
        cb = CircuitBreaker("test", config)

        def record_failures():
            for _ in range(50):
                cb.record_failure()

        threads = [threading.Thread(target=record_failures) for _ in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have recorded all failures (4 threads * 50 = 200)
        assert cb.failure_count == 200

    def test_concurrent_calls(self):
        """Test concurrent calls through circuit breaker."""
        cb = CircuitBreaker("test")
        results = []

        def make_call():
            result = cb.call(lambda: "success")
            results.append(result)

        threads = [threading.Thread(target=make_call) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert all(r == "success" for r in results)
