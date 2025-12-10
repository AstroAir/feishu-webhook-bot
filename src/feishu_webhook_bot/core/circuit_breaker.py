"""Circuit breaker pattern implementation for fault tolerance."""

from __future__ import annotations

import threading
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, Field

from .logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker."""
    failure_threshold: int = Field(default=5, ge=1, description="Failures before opening")
    success_threshold: int = Field(default=3, ge=1, description="Successes to close from half-open")
    timeout_seconds: float = Field(default=30.0, ge=0.0, description="Wait time before half-open")
    excluded_exceptions: list[str] = Field(default_factory=list, description="Exception class names to ignore")


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    def __init__(self, name: str, remaining_seconds: float):
        self.name = name
        self.remaining_seconds = remaining_seconds
        super().__init__(f"Circuit breaker '{name}' is open. Retry in {remaining_seconds:.1f}s")


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._check_state_transition()
            return self._state

    def get_state(self) -> CircuitState:
        """Get current circuit state (alias for state property)."""
        return self.state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def success_count(self) -> int:
        return self._success_count

    def _check_state_transition(self) -> None:
        """Check and perform state transitions based on timeout."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.config.timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"Circuit '{self.name}' transitioned to HALF_OPEN")

    def should_allow_request(self) -> bool:
        """Check if request should be allowed through."""
        with self._lock:
            self._check_state_transition()
            return self._state != CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful operation."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(f"Circuit '{self.name}' closed after {self.config.success_threshold} successes")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self, exception: Exception | None = None) -> None:
        """Record a failed operation."""
        if exception and self._is_excluded(exception):
            return

        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._last_failure_time = time.time()
                logger.warning(f"Circuit '{self.name}' re-opened from HALF_OPEN")
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._last_failure_time = time.time()
                    logger.warning(f"Circuit '{self.name}' opened after {self._failure_count} failures")

    def _is_excluded(self, exception: Exception) -> bool:
        """Check if exception type is excluded."""
        exc_name = type(exception).__name__
        return exc_name in self.config.excluded_exceptions

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function through circuit breaker."""
        if not self.should_allow_request():
            remaining = self.config.timeout_seconds
            if self._last_failure_time:
                remaining = max(0, self.config.timeout_seconds - (time.time() - self._last_failure_time))
            raise CircuitBreakerOpen(self.name, remaining)

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit '{self.name}' reset")

    def get_state_info(self) -> dict[str, Any]:
        """Get current state information."""
        with self._lock:
            self._check_state_transition()
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time,
            }

    def get_status(self) -> dict[str, Any]:
        """Get current status (alias for get_state_info)."""
        return self.get_state_info()


def circuit_breaker(
    name: str | None = None, config: CircuitBreakerConfig | None = None
) -> Callable[[F], F]:
    """Decorator to wrap function with circuit breaker.

    Args:
        name: Circuit breaker name. If None, uses function name.
        config: Circuit breaker configuration.

    Returns:
        Decorated function.
    """
    def decorator(func: F) -> F:
        breaker_name = name or func.__name__
        cb = CircuitBreakerRegistry().get_or_create(breaker_name, config or CircuitBreakerConfig())

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return cb.call(func, *args, **kwargs)

        # Attach circuit breaker reference to wrapper
        wrapper._circuit_breaker = cb  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]
    return decorator


class CircuitBreakerRegistry:
    """Registry for managing circuit breaker instances."""
    _instance: CircuitBreakerRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> CircuitBreakerRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers = {}
        return cls._instance

    @property
    def _breakers(self) -> dict[str, CircuitBreaker]:
        return self.__dict__.get("_breakers", {})

    @_breakers.setter
    def _breakers(self, value: dict[str, CircuitBreaker]) -> None:
        self.__dict__["_breakers"] = value

    def get_or_create(self, name: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        return self._breakers.get(name)

    def remove(self, name: str) -> None:
        self._breakers.pop(name, None)

    def get_all_states(self) -> dict[str, CircuitState]:
        return {name: cb.state for name, cb in self._breakers.items()}

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """Get status information for all circuit breakers."""
        return {name: cb.get_state_info() for name, cb in self._breakers.items()}

    def reset_all(self) -> None:
        for cb in self._breakers.values():
            cb.reset()

    def clear(self) -> None:
        """Clear all circuit breakers from the registry."""
        self._breakers.clear()

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None
