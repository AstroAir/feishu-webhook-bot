#!/usr/bin/env python3
"""Circuit Breaker Pattern Example.

This example demonstrates the circuit breaker pattern for fault tolerance:
- Basic circuit breaker usage
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Decorator-based circuit breaker
- Circuit breaker registry for managing multiple breakers
- Configuration options
- Error handling and recovery

The circuit breaker prevents cascading failures by temporarily blocking
requests to failing services.
"""

import random
import time
from typing import Any

from feishu_webhook_bot.core import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitBreakerRegistry,
    CircuitState,
    LoggingConfig,
    circuit_breaker,
    get_logger,
    setup_logging,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Basic Circuit Breaker Usage
# =============================================================================
def demo_basic_circuit_breaker() -> None:
    """Demonstrate basic circuit breaker functionality."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Circuit Breaker Usage")
    print("=" * 60)

    # Create a circuit breaker with custom configuration
    config = CircuitBreakerConfig(
        failure_threshold=3,  # Open after 3 failures
        success_threshold=2,  # Close after 2 successes in half-open
        timeout_seconds=5.0,  # Wait 5 seconds before half-open
    )
    cb = CircuitBreaker("demo_service", config)

    print(f"Initial state: {cb.state}")
    print(f"Failure threshold: {config.failure_threshold}")
    print(f"Success threshold: {config.success_threshold}")
    print(f"Timeout: {config.timeout_seconds}s")

    # Simulate successful operations
    print("\n--- Simulating successful operations ---")
    for i in range(3):
        cb.record_success()
        print(f"Success {i + 1}: State = {cb.state}, Failures = {cb.failure_count}")

    # Simulate failures to trigger circuit open
    print("\n--- Simulating failures ---")
    for i in range(4):
        cb.record_failure()
        print(f"Failure {i + 1}: State = {cb.state}, Failures = {cb.failure_count}")

    # Try to make a request when circuit is open
    print("\n--- Attempting request with open circuit ---")
    if not cb.should_allow_request():
        print("Request blocked - circuit is OPEN")

    # Get state information
    print("\n--- Circuit breaker state info ---")
    state_info = cb.get_state_info()
    for key, value in state_info.items():
        print(f"  {key}: {value}")


# =============================================================================
# Demo 2: Circuit Breaker with Function Calls
# =============================================================================
def demo_circuit_breaker_call() -> None:
    """Demonstrate circuit breaker wrapping function calls."""
    print("\n" + "=" * 60)
    print("Demo 2: Circuit Breaker with Function Calls")
    print("=" * 60)

    config = CircuitBreakerConfig(
        failure_threshold=2,
        timeout_seconds=3.0,
    )
    cb = CircuitBreaker("api_service", config)

    # Simulated API call that may fail
    def unreliable_api_call(should_fail: bool = False) -> dict[str, Any]:
        if should_fail:
            raise ConnectionError("API connection failed")
        return {"status": "success", "data": "Hello from API"}

    # Successful calls
    print("\n--- Making successful API calls ---")
    for i in range(2):
        try:
            result = cb.call(unreliable_api_call, should_fail=False)
            print(f"Call {i + 1}: {result}")
        except Exception as e:
            print(f"Call {i + 1} failed: {e}")

    # Failing calls to trigger circuit open
    print("\n--- Making failing API calls ---")
    for i in range(3):
        try:
            result = cb.call(unreliable_api_call, should_fail=True)
            print(f"Call {i + 1}: {result}")
        except CircuitBreakerOpen as e:
            print(f"Call {i + 1}: Circuit breaker open - {e}")
        except ConnectionError as e:
            print(f"Call {i + 1}: API error - {e}")

    print(f"\nFinal state: {cb.state}")


# =============================================================================
# Demo 3: Decorator-Based Circuit Breaker
# =============================================================================
def demo_decorator_circuit_breaker() -> None:
    """Demonstrate decorator-based circuit breaker."""
    print("\n" + "=" * 60)
    print("Demo 3: Decorator-Based Circuit Breaker")
    print("=" * 60)

    # Clear registry for clean demo
    CircuitBreakerRegistry.reset_instance()

    @circuit_breaker(
        name="external_service",
        config=CircuitBreakerConfig(failure_threshold=2, timeout_seconds=2.0),
    )
    def call_external_service(value: int) -> str:
        """Simulated external service call."""
        if value < 0:
            raise ValueError("Negative values not allowed")
        return f"Processed: {value}"

    # Successful calls
    print("\n--- Successful calls ---")
    for i in range(3):
        try:
            result = call_external_service(i * 10)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")

    # Failing calls
    print("\n--- Failing calls (negative values) ---")
    for i in range(3):
        try:
            result = call_external_service(-i - 1)
            print(f"Result: {result}")
        except CircuitBreakerOpen as e:
            print(f"Circuit breaker open: {e}")
        except ValueError as e:
            print(f"Value error: {e}")

    # Access the circuit breaker attached to the function
    if hasattr(call_external_service, "_circuit_breaker"):
        cb = call_external_service._circuit_breaker
        print(f"\nCircuit state: {cb.state}")
        print(f"Failure count: {cb.failure_count}")


# =============================================================================
# Demo 4: Circuit Breaker Registry
# =============================================================================
def demo_circuit_breaker_registry() -> None:
    """Demonstrate circuit breaker registry for managing multiple breakers."""
    print("\n" + "=" * 60)
    print("Demo 4: Circuit Breaker Registry")
    print("=" * 60)

    # Reset and get registry instance
    CircuitBreakerRegistry.reset_instance()
    registry = CircuitBreakerRegistry()

    # Create multiple circuit breakers
    services = ["database", "cache", "api", "storage"]
    for service in services:
        config = CircuitBreakerConfig(
            failure_threshold=random.randint(2, 5),
            timeout_seconds=random.uniform(5.0, 15.0),
        )
        registry.get_or_create(service, config)
        print(f"Created circuit breaker for: {service}")

    # Simulate some failures
    print("\n--- Simulating failures ---")
    registry.get("database").record_failure()
    registry.get("database").record_failure()
    registry.get("database").record_failure()
    registry.get("cache").record_failure()

    # Get all states
    print("\n--- All circuit breaker states ---")
    states = registry.get_all_states()
    for name, state in states.items():
        print(f"  {name}: {state.value}")

    # Get detailed status
    print("\n--- Detailed status ---")
    all_status = registry.get_all_status()
    for name, status in all_status.items():
        print(f"  {name}:")
        print(f"    State: {status['state']}")
        print(f"    Failures: {status['failure_count']}")

    # Reset all circuit breakers
    print("\n--- Resetting all circuit breakers ---")
    registry.reset_all()
    states = registry.get_all_states()
    for name, state in states.items():
        print(f"  {name}: {state.value}")


# =============================================================================
# Demo 5: State Transitions
# =============================================================================
def demo_state_transitions() -> None:
    """Demonstrate circuit breaker state transitions."""
    print("\n" + "=" * 60)
    print("Demo 5: State Transitions")
    print("=" * 60)

    config = CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=2,
        timeout_seconds=2.0,
    )
    cb = CircuitBreaker("transition_demo", config)

    print("State transition flow:")
    print("CLOSED -> (failures) -> OPEN -> (timeout) -> HALF_OPEN -> (successes) -> CLOSED")

    # Step 1: Start in CLOSED state
    print(f"\n1. Initial state: {cb.state}")

    # Step 2: Trigger failures to OPEN
    print("\n2. Recording failures...")
    cb.record_failure()
    print(f"   After 1 failure: {cb.state}")
    cb.record_failure()
    print(f"   After 2 failures: {cb.state} (threshold reached)")

    # Step 3: Wait for timeout to transition to HALF_OPEN
    print(f"\n3. Waiting {config.timeout_seconds}s for timeout...")
    time.sleep(config.timeout_seconds + 0.5)
    print(f"   After timeout: {cb.state}")

    # Step 4: Record successes to close
    print("\n4. Recording successes in HALF_OPEN...")
    cb.record_success()
    print(f"   After 1 success: {cb.state}")
    cb.record_success()
    print(f"   After 2 successes: {cb.state} (threshold reached)")


# =============================================================================
# Demo 6: Excluded Exceptions
# =============================================================================
def demo_excluded_exceptions() -> None:
    """Demonstrate excluding certain exceptions from circuit breaker."""
    print("\n" + "=" * 60)
    print("Demo 6: Excluded Exceptions")
    print("=" * 60)

    # Create circuit breaker that ignores ValueError
    config = CircuitBreakerConfig(
        failure_threshold=2,
        excluded_exceptions=["ValueError", "KeyError"],
    )
    cb = CircuitBreaker("excluded_demo", config)

    print("Excluded exceptions: ValueError, KeyError")
    print(f"Initial state: {cb.state}")

    # Record excluded exceptions - should not count as failures
    print("\n--- Recording excluded exceptions ---")
    cb.record_failure(ValueError("This is excluded"))
    print(f"After ValueError: State = {cb.state}, Failures = {cb.failure_count}")

    cb.record_failure(KeyError("This is also excluded"))
    print(f"After KeyError: State = {cb.state}, Failures = {cb.failure_count}")

    # Record non-excluded exception - should count
    print("\n--- Recording non-excluded exceptions ---")
    cb.record_failure(RuntimeError("This counts"))
    print(f"After RuntimeError: State = {cb.state}, Failures = {cb.failure_count}")

    cb.record_failure(ConnectionError("This also counts"))
    print(f"After ConnectionError: State = {cb.state}, Failures = {cb.failure_count}")


# =============================================================================
# Demo 7: Real-World Usage Pattern
# =============================================================================
def demo_real_world_pattern() -> None:
    """Demonstrate a real-world usage pattern with circuit breaker."""
    print("\n" + "=" * 60)
    print("Demo 7: Real-World Usage Pattern")
    print("=" * 60)

    class ExternalServiceClient:
        """Example client with circuit breaker protection."""

        def __init__(self, service_name: str):
            self.service_name = service_name
            self._circuit_breaker = CircuitBreaker(
                service_name,
                CircuitBreakerConfig(
                    failure_threshold=3,
                    success_threshold=2,
                    timeout_seconds=10.0,
                ),
            )
            self._failure_rate = 0.3  # 30% failure rate for demo

        def call_api(self, endpoint: str) -> dict[str, Any]:
            """Make an API call with circuit breaker protection."""
            # Check if circuit allows request
            if not self._circuit_breaker.should_allow_request():
                state_info = self._circuit_breaker.get_state_info()
                raise CircuitBreakerOpen(
                    self.service_name,
                    state_info.get("last_failure_time", 0),
                )

            try:
                # Simulate API call with random failures
                if random.random() < self._failure_rate:
                    raise ConnectionError(f"Failed to connect to {endpoint}")

                result = {"endpoint": endpoint, "status": "success"}
                self._circuit_breaker.record_success()
                return result

            except Exception as e:
                self._circuit_breaker.record_failure(e)
                raise

        def get_health(self) -> dict[str, Any]:
            """Get service health status."""
            return {
                "service": self.service_name,
                "circuit_state": self._circuit_breaker.state.value,
                "failure_count": self._circuit_breaker.failure_count,
                "is_healthy": self._circuit_breaker.state == CircuitState.CLOSED,
            }

    # Create client and make calls
    client = ExternalServiceClient("payment_service")

    print("Making API calls with 30% failure rate...")
    print(f"Initial health: {client.get_health()}")

    successful = 0
    failed = 0
    blocked = 0

    for i in range(15):
        try:
            result = client.call_api(f"/api/v1/endpoint_{i}")
            successful += 1
            print(f"Call {i + 1}: SUCCESS - {result['endpoint']}")
        except CircuitBreakerOpen:
            blocked += 1
            print(f"Call {i + 1}: BLOCKED - Circuit breaker open")
        except ConnectionError as e:
            failed += 1
            print(f"Call {i + 1}: FAILED - {e}")

    print(f"\n--- Summary ---")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Blocked: {blocked}")
    print(f"Final health: {client.get_health()}")


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all circuit breaker demonstrations."""
    print("=" * 60)
    print("Circuit Breaker Pattern Examples")
    print("=" * 60)

    demos = [
        ("Basic Circuit Breaker", demo_basic_circuit_breaker),
        ("Circuit Breaker with Function Calls", demo_circuit_breaker_call),
        ("Decorator-Based Circuit Breaker", demo_decorator_circuit_breaker),
        ("Circuit Breaker Registry", demo_circuit_breaker_registry),
        ("State Transitions", demo_state_transitions),
        ("Excluded Exceptions", demo_excluded_exceptions),
        ("Real-World Usage Pattern", demo_real_world_pattern),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
