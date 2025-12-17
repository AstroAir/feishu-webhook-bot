#!/usr/bin/env python3
"""Feishu Provider Example.

This example demonstrates the Feishu provider for sending messages:
- Provider configuration and setup
- Sending text messages
- Sending rich text (post) messages
- Sending interactive cards
- Sending images
- HMAC-SHA256 signature for secure webhooks
- Circuit breaker integration
- Message tracking

The Feishu provider implements the BaseProvider interface for
consistent multi-platform messaging.
"""

import os
from typing import Any

from feishu_webhook_bot.core import (
    CircuitBreakerConfig,
    LoggingConfig,
    MessageStatus,
    MessageTracker,
    get_logger,
    setup_logging,
)
from feishu_webhook_bot.core.provider import Message, MessageType, SendResult
from feishu_webhook_bot.providers.feishu import FeishuProvider, FeishuProviderConfig

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Basic Provider Setup
# =============================================================================
def demo_basic_setup() -> None:
    """Demonstrate basic Feishu provider setup."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Provider Setup")
    print("=" * 60)

    # Get webhook URL from environment or use placeholder
    webhook_url = os.environ.get(
        "FEISHU_WEBHOOK_URL",
        "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id",
    )

    # Create provider configuration
    config = FeishuProviderConfig(
        name="default",
        url=webhook_url,
        timeout=10.0,
    )

    print("FeishuProviderConfig:")
    print(f"  name: {config.name}")
    print(f"  provider_type: {config.provider_type}")
    print(f"  url: {config.url[:50]}...")
    print(f"  timeout: {config.timeout}")

    # Create provider
    provider = FeishuProvider(config)
    print(f"\nProvider created: {provider.name}")
    print(f"Connected: {provider.is_connected}")

    # Connect
    print("\nConnecting...")
    provider.connect()
    print(f"Connected: {provider.is_connected}")

    # Disconnect
    provider.disconnect()
    print(f"Disconnected: {not provider.is_connected}")


# =============================================================================
# Demo 2: Provider with Secret (Signed Webhooks)
# =============================================================================
def demo_signed_webhooks() -> None:
    """Demonstrate signed webhook configuration."""
    print("\n" + "=" * 60)
    print("Demo 2: Provider with Secret (Signed Webhooks)")
    print("=" * 60)

    webhook_url = os.environ.get(
        "FEISHU_WEBHOOK_URL",
        "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id",
    )
    webhook_secret = os.environ.get("FEISHU_WEBHOOK_SECRET", "your-webhook-secret")

    # Create configuration with secret
    config = FeishuProviderConfig(
        name="signed_webhook",
        url=webhook_url,
        secret=webhook_secret,
        timeout=15.0,
    )

    print("Signed webhook configuration:")
    print(f"  URL: {config.url[:50]}...")
    print(f"  Secret: {'*' * len(config.secret) if config.secret else 'None'}")

    # Create provider
    FeishuProvider(config)

    print("\nNote: When a secret is configured, the provider will:")
    print("  1. Generate a timestamp")
    print("  2. Create HMAC-SHA256 signature")
    print("  3. Include signature in request payload")


# =============================================================================
# Demo 3: Sending Text Messages
# =============================================================================
def demo_send_text() -> None:
    """Demonstrate sending text messages."""
    print("\n" + "=" * 60)
    print("Demo 3: Sending Text Messages")
    print("=" * 60)

    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")

    if not webhook_url:
        print("FEISHU_WEBHOOK_URL not set. Showing message structure only.")
        print("\nText message payload structure:")
        payload = {"msg_type": "text", "content": {"text": "Hello, Feishu!"}}
        print_json(payload)
        return

    config = FeishuProviderConfig(name="text_demo", url=webhook_url)
    provider = FeishuProvider(config)
    provider.connect()

    # Send text message
    print("Sending text message...")
    result = provider.send_text("Hello from Feishu Provider Example!", target=webhook_url)

    print("\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Message ID: {result.message_id}")
    if result.error:
        print(f"  Error: {result.error}")

    provider.disconnect()


# =============================================================================
# Demo 4: Sending Rich Text Messages
# =============================================================================
def demo_send_rich_text() -> None:
    """Demonstrate sending rich text (post) messages."""
    print("\n" + "=" * 60)
    print("Demo 4: Sending Rich Text Messages")
    print("=" * 60)

    # Rich text content structure
    title = "Daily Report"
    content = [
        [
            {"tag": "text", "text": "Project Status: "},
            {"tag": "text", "text": "On Track", "style": ["bold"]},
        ],
        [
            {"tag": "text", "text": "Tasks completed: "},
            {"tag": "text", "text": "15/20"},
        ],
        [
            {"tag": "a", "text": "View Dashboard", "href": "https://example.com/dashboard"},
        ],
        [
            {"tag": "at", "user_id": "all", "user_name": "All"},
        ],
    ]

    print("Rich text structure:")
    print(f"  Title: {title}")
    print(f"  Content paragraphs: {len(content)}")

    # Show payload structure
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": content,
                }
            }
        },
    }
    print("\nPayload structure:")
    print_json(payload)

    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
    if webhook_url:
        config = FeishuProviderConfig(name="rich_text_demo", url=webhook_url)
        provider = FeishuProvider(config)
        provider.connect()

        result = provider.send_rich_text(title, content, target=webhook_url)
        print(f"\nSend result: {result.success}")

        provider.disconnect()


# =============================================================================
# Demo 5: Sending Interactive Cards
# =============================================================================
def demo_send_card() -> None:
    """Demonstrate sending interactive cards."""
    print("\n" + "=" * 60)
    print("Demo 5: Sending Interactive Cards")
    print("=" * 60)

    # Card structure
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "System Alert"},
            "template": "red",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**Alert:** High CPU usage detected on server-01",
                },
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": "**Server:** server-01"},
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": "**CPU:** 95%"},
                    },
                ],
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "View Details"},
                        "type": "primary",
                        "url": "https://example.com/alerts/123",
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "Acknowledge"},
                        "type": "default",
                    },
                ],
            },
        ],
    }

    print("Interactive card structure:")
    print_json(card)

    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
    if webhook_url:
        config = FeishuProviderConfig(name="card_demo", url=webhook_url)
        provider = FeishuProvider(config)
        provider.connect()

        result = provider.send_card(card, target=webhook_url)
        print(f"\nSend result: {result.success}")

        provider.disconnect()


# =============================================================================
# Demo 6: Provider with Circuit Breaker
# =============================================================================
def demo_circuit_breaker_integration() -> None:
    """Demonstrate circuit breaker integration."""
    print("\n" + "=" * 60)
    print("Demo 6: Provider with Circuit Breaker")
    print("=" * 60)

    webhook_url = os.environ.get(
        "FEISHU_WEBHOOK_URL",
        "https://open.feishu.cn/open-apis/bot/v2/hook/invalid",
    )

    # Create circuit breaker configuration
    cb_config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=30.0,
    )

    print("Circuit breaker configuration:")
    print(f"  Failure threshold: {cb_config.failure_threshold}")
    print(f"  Success threshold: {cb_config.success_threshold}")
    print(f"  Timeout: {cb_config.timeout_seconds}s")

    # Create provider with circuit breaker
    config = FeishuProviderConfig(name="cb_demo", url=webhook_url)
    FeishuProvider(config, circuit_breaker_config=cb_config)

    print("\nProvider created with circuit breaker protection")
    print("The circuit breaker will:")
    print("  - Open after 3 consecutive failures")
    print("  - Block requests for 30 seconds when open")
    print("  - Allow test requests in half-open state")
    print("  - Close after 2 consecutive successes")


# =============================================================================
# Demo 7: Provider with Message Tracking
# =============================================================================
def demo_message_tracking() -> None:
    """Demonstrate message tracking integration."""
    print("\n" + "=" * 60)
    print("Demo 7: Provider with Message Tracking")
    print("=" * 60)

    webhook_url = os.environ.get(
        "FEISHU_WEBHOOK_URL",
        "https://open.feishu.cn/open-apis/bot/v2/hook/demo",
    )

    # Create message tracker
    tracker = MessageTracker(max_history=1000)

    # Create provider with tracker
    config = FeishuProviderConfig(name="tracked_demo", url=webhook_url)
    FeishuProvider(config, message_tracker=tracker)

    print("Provider created with message tracking")
    print("\nMessage tracking provides:")
    print("  - Delivery status tracking")
    print("  - Duplicate detection")
    print("  - Retry counting")
    print("  - Statistics and monitoring")

    # Simulate tracking (without actual sending)
    print("\n--- Simulating message tracking ---")
    import uuid

    msg_id = str(uuid.uuid4())
    tracker.track(
        message_id=msg_id,
        provider="feishu",
        target=webhook_url,
        content="Test message",
    )
    print(f"Tracked message: {msg_id[:16]}...")

    tracker.update_status(msg_id, MessageStatus.SENT)
    tracker.update_status(msg_id, MessageStatus.DELIVERED)

    msg = tracker.get_message(msg_id)
    if msg:
        print(f"Status: {msg.status.value}")

    # Get statistics
    stats = tracker.get_statistics()
    print(f"\nStatistics: {stats}")


# =============================================================================
# Demo 8: Generic Message Sending
# =============================================================================
def demo_generic_message() -> None:
    """Demonstrate generic message sending."""
    print("\n" + "=" * 60)
    print("Demo 8: Generic Message Sending")
    print("=" * 60)

    webhook_url = os.environ.get(
        "FEISHU_WEBHOOK_URL",
        "https://open.feishu.cn/open-apis/bot/v2/hook/demo",
    )

    config = FeishuProviderConfig(name="generic_demo", url=webhook_url)
    FeishuProvider(config)

    # Create different message types
    messages = [
        Message(type=MessageType.TEXT, content="Text message"),
        Message(
            type=MessageType.RICH_TEXT,
            content={
                "title": "Rich Text",
                "content": [[{"tag": "text", "text": "Content"}]],
            },
        ),
        Message(
            type=MessageType.CARD,
            content={
                "elements": [{"tag": "div", "text": {"tag": "plain_text", "content": "Card"}}]
            },
        ),
        Message(type=MessageType.IMAGE, content="img_v2_xxx"),
    ]

    print("Message types supported:")
    for msg in messages:
        print(f"  - {msg.type.value}: {type(msg.content).__name__}")

    print("\nUsage:")
    print("  result = provider.send_message(message, target)")


# =============================================================================
# Demo 9: Error Handling
# =============================================================================
def demo_error_handling() -> None:
    """Demonstrate error handling patterns."""
    print("\n" + "=" * 60)
    print("Demo 9: Error Handling")
    print("=" * 60)

    # Invalid URL
    print("--- Handling invalid webhook URL ---")
    config = FeishuProviderConfig(
        name="error_demo",
        url="https://invalid.example.com/webhook",
    )
    provider = FeishuProvider(config)
    provider.connect()

    result = provider.send_text("Test", target=config.url)
    print(f"Success: {result.success}")
    print(f"Error: {result.error}")

    provider.disconnect()

    # Error handling pattern
    print("\n--- Recommended error handling pattern ---")
    print(
        """
def send_with_retry(provider, message, target, max_retries=3):
    for attempt in range(max_retries):
        result = provider.send_text(message, target)

        if result.success:
            return result

        if "rate limit" in (result.error or "").lower():
            time.sleep(2 ** attempt)  # Exponential backoff
            continue

        # Non-retryable error
        break

    return result
"""
    )


# =============================================================================
# Demo 10: Real-World Usage Pattern
# =============================================================================
def demo_real_world_pattern() -> None:
    """Demonstrate a real-world usage pattern."""
    print("\n" + "=" * 60)
    print("Demo 10: Real-World Usage Pattern")
    print("=" * 60)

    class FeishuNotificationService:
        """Notification service using Feishu provider."""

        def __init__(self, webhook_url: str, secret: str | None = None):
            self.config = FeishuProviderConfig(
                name="notification_service",
                url=webhook_url,
                secret=secret,
            )
            self.provider = FeishuProvider(
                self.config,
                message_tracker=MessageTracker(),
                circuit_breaker_config=CircuitBreakerConfig(
                    failure_threshold=5,
                    timeout_seconds=60.0,
                ),
            )
            self._connected = False

        def connect(self) -> None:
            if not self._connected:
                self.provider.connect()
                self._connected = True

        def disconnect(self) -> None:
            if self._connected:
                self.provider.disconnect()
                self._connected = False

        def send_alert(
            self,
            title: str,
            message: str,
            severity: str = "info",
        ) -> SendResult:
            """Send an alert notification."""
            self.connect()

            colors = {
                "info": "blue",
                "warning": "orange",
                "error": "red",
                "success": "green",
            }

            card = {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": colors.get(severity, "blue"),
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": message},
                    }
                ],
            }

            return self.provider.send_card(card, target=self.config.url)

        def send_report(
            self,
            title: str,
            sections: list[dict[str, Any]],
        ) -> SendResult:
            """Send a report notification."""
            self.connect()

            elements = []
            for section in sections:
                elements.append(
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**{section['title']}**\n{section['content']}",
                        },
                    }
                )
                elements.append({"tag": "hr"})

            card = {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue",
                },
                "elements": elements[:-1],  # Remove last hr
            }

            return self.provider.send_card(card, target=self.config.url)

    # Usage example
    webhook_url = os.environ.get(
        "FEISHU_WEBHOOK_URL",
        "https://open.feishu.cn/open-apis/bot/v2/hook/demo",
    )

    FeishuNotificationService(webhook_url)

    print("FeishuNotificationService created")
    print("\nUsage examples:")
    print(
        """
# Send alert
service.send_alert(
    title="Server Alert",
    message="CPU usage exceeded 90%",
    severity="warning"
)

# Send report
service.send_report(
    title="Daily Summary",
    sections=[
        {"title": "Users", "content": "Active: 1,234"},
        {"title": "Revenue", "content": "$12,345"},
    ]
)
"""
    )


# =============================================================================
# Helper Functions
# =============================================================================
def print_json(obj: Any, indent: int = 2) -> None:
    """Pretty print a JSON-serializable object."""
    import json

    print(json.dumps(obj, indent=indent, ensure_ascii=False))


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all Feishu provider demonstrations."""
    print("=" * 60)
    print("Feishu Provider Examples")
    print("=" * 60)

    demos = [
        ("Basic Provider Setup", demo_basic_setup),
        ("Signed Webhooks", demo_signed_webhooks),
        ("Sending Text Messages", demo_send_text),
        ("Sending Rich Text Messages", demo_send_rich_text),
        ("Sending Interactive Cards", demo_send_card),
        ("Circuit Breaker Integration", demo_circuit_breaker_integration),
        ("Message Tracking", demo_message_tracking),
        ("Generic Message Sending", demo_generic_message),
        ("Error Handling", demo_error_handling),
        ("Real-World Usage Pattern", demo_real_world_pattern),
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
