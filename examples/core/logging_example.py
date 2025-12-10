#!/usr/bin/env python3
"""Logging System Example.

This example demonstrates the logging system:
- Setting up logging with different levels
- Using the get_logger function
- Structured logging with context
- Log formatting options
- File and console handlers
- Log rotation
- Performance logging

The logging system provides consistent logging across all bot components.
"""

import logging
import sys
import tempfile
import time
from pathlib import Path

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging

# =============================================================================
# Demo 1: Basic Logging Setup
# =============================================================================
def demo_basic_logging() -> None:
    """Demonstrate basic logging setup."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Logging Setup")
    print("=" * 60)

    # Setup logging with INFO level
    setup_logging(LoggingConfig(level="INFO"))

    # Get a logger
    logger = get_logger(__name__)

    print("Logging at different levels:")
    print("-" * 40)

    logger.debug("This is a DEBUG message (won't show at INFO level)")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")

    print("-" * 40)
    print("Note: DEBUG message not shown because level is INFO")


# =============================================================================
# Demo 2: Different Log Levels
# =============================================================================
def demo_log_levels() -> None:
    """Demonstrate different log levels."""
    print("\n" + "=" * 60)
    print("Demo 2: Different Log Levels")
    print("=" * 60)

    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    for level in levels:
        print(f"\n--- Level: {level} ---")
        setup_logging(LoggingConfig(level=level))
        logger = get_logger(f"demo.{level.lower()}")

        logger.debug("DEBUG: Detailed information for debugging")
        logger.info("INFO: General information about program execution")
        logger.warning("WARNING: Something unexpected but not critical")
        logger.error("ERROR: A significant problem occurred")
        logger.critical("CRITICAL: A very serious error")


# =============================================================================
# Demo 3: Named Loggers
# =============================================================================
def demo_named_loggers() -> None:
    """Demonstrate using named loggers."""
    print("\n" + "=" * 60)
    print("Demo 3: Named Loggers")
    print("=" * 60)

    setup_logging(LoggingConfig(level="INFO"))

    # Create loggers for different components
    bot_logger = get_logger("bot")
    plugin_logger = get_logger("plugin.calendar")
    ai_logger = get_logger("ai.agent")
    scheduler_logger = get_logger("scheduler")

    print("Logging from different components:")
    print("-" * 40)

    bot_logger.info("Bot started successfully")
    plugin_logger.info("Calendar plugin loaded")
    ai_logger.info("AI agent initialized with GPT-4")
    scheduler_logger.info("Scheduler started with 5 jobs")

    print("-" * 40)
    print("Each logger shows its component name in the output")


# =============================================================================
# Demo 4: Logging with Context
# =============================================================================
def demo_logging_with_context() -> None:
    """Demonstrate logging with contextual information."""
    print("\n" + "=" * 60)
    print("Demo 4: Logging with Context")
    print("=" * 60)

    setup_logging(LoggingConfig(level="INFO"))
    logger = get_logger("context_demo")

    # Log with extra context
    print("Logging with contextual information:")
    print("-" * 40)

    # Using string formatting
    user_id = "user_123"
    action = "send_message"
    logger.info("User %s performed action: %s", user_id, action)

    # Using f-strings (common pattern)
    message_id = "msg_456"
    target = "group_789"
    logger.info(f"Message {message_id} sent to {target}")

    # Logging exceptions
    try:
        result = 1 / 0
    except ZeroDivisionError:
        logger.exception("An error occurred during calculation")

    print("-" * 40)


# =============================================================================
# Demo 5: Custom Log Format
# =============================================================================
def demo_custom_format() -> None:
    """Demonstrate custom log formatting."""
    print("\n" + "=" * 60)
    print("Demo 5: Custom Log Format")
    print("=" * 60)

    # Different format options
    formats = [
        ("Simple", "%(levelname)s: %(message)s"),
        ("With time", "%(asctime)s - %(levelname)s - %(message)s"),
        ("Full", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        (
            "Detailed",
            "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
        ),
    ]

    for name, fmt in formats:
        print(f"\n--- Format: {name} ---")
        setup_logging(LoggingConfig(level="INFO", format=fmt))
        logger = get_logger("format_demo")
        logger.info("This is a test message")


# =============================================================================
# Demo 6: File Logging
# =============================================================================
def demo_file_logging() -> None:
    """Demonstrate logging to files."""
    print("\n" + "=" * 60)
    print("Demo 6: File Logging")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "bot.log"

        # Setup file handler manually
        setup_logging(LoggingConfig(level="DEBUG"))
        logger = get_logger("file_demo")

        # Add file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

        # Log some messages
        print("Writing logs to file...")
        logger.debug("Debug message to file")
        logger.info("Info message to file")
        logger.warning("Warning message to file")
        logger.error("Error message to file")

        # Read and display file contents
        print(f"\nLog file: {log_file}")
        print(f"File size: {log_file.stat().st_size} bytes")
        print("\nFile contents:")
        print("-" * 40)
        with open(log_file) as f:
            print(f.read())
        print("-" * 40)


# =============================================================================
# Demo 7: Performance Logging
# =============================================================================
def demo_performance_logging() -> None:
    """Demonstrate performance logging patterns."""
    print("\n" + "=" * 60)
    print("Demo 7: Performance Logging")
    print("=" * 60)

    setup_logging(LoggingConfig(level="INFO"))
    logger = get_logger("performance")

    # Simple timing
    print("\n--- Simple timing ---")
    start = time.time()
    time.sleep(0.1)  # Simulate work
    elapsed = time.time() - start
    logger.info(f"Operation completed in {elapsed:.3f}s")

    # Context manager for timing
    print("\n--- Context manager timing ---")

    class Timer:
        def __init__(self, name: str, log: logging.Logger):
            self.name = name
            self.logger = log
            self.start = 0.0

        def __enter__(self):
            self.start = time.time()
            self.logger.debug(f"Starting {self.name}")
            return self

        def __exit__(self, *args):
            elapsed = time.time() - self.start
            self.logger.info(f"{self.name} completed in {elapsed:.3f}s")

    with Timer("database_query", logger):
        time.sleep(0.05)

    with Timer("api_call", logger):
        time.sleep(0.08)

    with Timer("data_processing", logger):
        time.sleep(0.03)


# =============================================================================
# Demo 8: Structured Logging Pattern
# =============================================================================
def demo_structured_logging() -> None:
    """Demonstrate structured logging patterns."""
    print("\n" + "=" * 60)
    print("Demo 8: Structured Logging Pattern")
    print("=" * 60)

    setup_logging(LoggingConfig(level="INFO"))
    logger = get_logger("structured")

    # Log events with structured data
    print("Structured logging examples:")
    print("-" * 40)

    # Request logging
    logger.info(
        "HTTP Request",
        extra={
            "method": "POST",
            "path": "/api/messages",
            "status": 200,
            "duration_ms": 45,
        },
    )

    # Message event
    logger.info(
        "Message sent",
        extra={
            "message_id": "msg_123",
            "provider": "feishu",
            "target": "group_456",
            "type": "card",
        },
    )

    # Error event
    logger.error(
        "API call failed",
        extra={
            "endpoint": "/open-apis/bot/v2/hook",
            "error_code": 500,
            "retry_count": 3,
        },
    )

    print("-" * 40)
    print("Note: Extra fields may not show with default formatter")
    print("Use a JSON formatter for full structured logging")


# =============================================================================
# Demo 9: Logger Hierarchy
# =============================================================================
def demo_logger_hierarchy() -> None:
    """Demonstrate logger hierarchy and propagation."""
    print("\n" + "=" * 60)
    print("Demo 9: Logger Hierarchy")
    print("=" * 60)

    setup_logging(LoggingConfig(level="INFO"))

    # Create hierarchical loggers
    root = get_logger("app")
    plugins = get_logger("app.plugins")
    calendar = get_logger("app.plugins.calendar")
    ai = get_logger("app.ai")
    agent = get_logger("app.ai.agent")

    print("Logger hierarchy:")
    print("  app")
    print("  ├── app.plugins")
    print("  │   └── app.plugins.calendar")
    print("  └── app.ai")
    print("      └── app.ai.agent")

    print("\nLogging from each level:")
    print("-" * 40)

    root.info("Root logger message")
    plugins.info("Plugins logger message")
    calendar.info("Calendar plugin message")
    ai.info("AI module message")
    agent.info("AI agent message")

    print("-" * 40)


# =============================================================================
# Demo 10: Real-World Logging Pattern
# =============================================================================
def demo_real_world_pattern() -> None:
    """Demonstrate a real-world logging pattern."""
    print("\n" + "=" * 60)
    print("Demo 10: Real-World Logging Pattern")
    print("=" * 60)

    setup_logging(LoggingConfig(level="INFO"))

    class MessageService:
        """Example service with comprehensive logging."""

        def __init__(self):
            self.logger = get_logger("service.message")
            self.logger.info("MessageService initialized")

        def send_message(self, target: str, content: str) -> bool:
            """Send a message with logging."""
            self.logger.debug(f"Preparing to send message to {target}")

            try:
                # Validate
                if not target:
                    self.logger.error("Invalid target: empty string")
                    return False

                if not content:
                    self.logger.warning("Empty content, sending anyway")

                # Simulate sending
                start = time.time()
                time.sleep(0.05)  # Simulate network call
                elapsed = time.time() - start

                self.logger.info(
                    f"Message sent to {target} in {elapsed:.3f}s",
                )
                return True

            except Exception as e:
                self.logger.exception(f"Failed to send message to {target}")
                return False

        def process_batch(self, messages: list) -> dict:
            """Process a batch of messages."""
            self.logger.info(f"Processing batch of {len(messages)} messages")

            results = {"sent": 0, "failed": 0}

            for i, msg in enumerate(messages):
                self.logger.debug(f"Processing message {i + 1}/{len(messages)}")
                if self.send_message(msg.get("target", ""), msg.get("content", "")):
                    results["sent"] += 1
                else:
                    results["failed"] += 1

            self.logger.info(
                f"Batch complete: {results['sent']} sent, {results['failed']} failed"
            )
            return results

    # Use the service
    service = MessageService()

    print("\n--- Sending single message ---")
    service.send_message("user_123", "Hello!")

    print("\n--- Processing batch ---")
    messages = [
        {"target": "user_1", "content": "Message 1"},
        {"target": "user_2", "content": "Message 2"},
        {"target": "", "content": "Invalid"},  # Will fail
        {"target": "user_3", "content": "Message 3"},
    ]
    results = service.process_batch(messages)
    print(f"Results: {results}")


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all logging demonstrations."""
    print("=" * 60)
    print("Logging System Examples")
    print("=" * 60)

    demos = [
        ("Basic Logging Setup", demo_basic_logging),
        ("Different Log Levels", demo_log_levels),
        ("Named Loggers", demo_named_loggers),
        ("Logging with Context", demo_logging_with_context),
        ("Custom Log Format", demo_custom_format),
        ("File Logging", demo_file_logging),
        ("Performance Logging", demo_performance_logging),
        ("Structured Logging Pattern", demo_structured_logging),
        ("Logger Hierarchy", demo_logger_hierarchy),
        ("Real-World Logging Pattern", demo_real_world_pattern),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
