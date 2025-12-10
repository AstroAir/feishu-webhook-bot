#!/usr/bin/env python3
"""QQ Napcat Provider Example.

This example demonstrates the QQ Napcat provider (OneBot11 protocol):
- Provider configuration and setup
- Sending private messages
- Sending group messages
- Message types (text, image, rich text)
- CQ code format
- Circuit breaker integration
- Message tracking

The Napcat provider implements the OneBot11 protocol for QQ messaging.
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
from feishu_webhook_bot.core.provider import Message, MessageType
from feishu_webhook_bot.providers.qq_napcat import NapcatProvider, NapcatProviderConfig

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Basic Provider Setup
# =============================================================================
def demo_basic_setup() -> None:
    """Demonstrate basic Napcat provider setup."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Provider Setup")
    print("=" * 60)

    # Get HTTP URL from environment or use placeholder
    http_url = os.environ.get("NAPCAT_HTTP_URL", "http://127.0.0.1:3000")

    # Create provider configuration
    config = NapcatProviderConfig(
        name="qq_bot",
        http_url=http_url,
        timeout=10.0,
    )

    print("NapcatProviderConfig:")
    print(f"  name: {config.name}")
    print(f"  provider_type: {config.provider_type}")
    print(f"  http_url: {config.http_url}")
    print(f"  timeout: {config.timeout}")

    # Create provider
    provider = NapcatProvider(config)
    print(f"\nProvider created: {provider.name}")
    print(f"Connected: {provider.is_connected}")


# =============================================================================
# Demo 2: Provider with Access Token
# =============================================================================
def demo_with_access_token() -> None:
    """Demonstrate provider with access token authentication."""
    print("\n" + "=" * 60)
    print("Demo 2: Provider with Access Token")
    print("=" * 60)

    http_url = os.environ.get("NAPCAT_HTTP_URL", "http://127.0.0.1:3000")
    access_token = os.environ.get("NAPCAT_ACCESS_TOKEN", "your-access-token")

    # Create configuration with access token
    config = NapcatProviderConfig(
        name="qq_bot_auth",
        http_url=http_url,
        access_token=access_token,
        timeout=15.0,
    )

    print("Authenticated configuration:")
    print(f"  HTTP URL: {config.http_url}")
    print(f"  Access Token: {'*' * 10 if config.access_token else 'None'}")

    # Create provider
    provider = NapcatProvider(config)

    print("\nNote: When access_token is configured, the provider will:")
    print("  - Include 'Authorization: Bearer <token>' header")
    print("  - Authenticate all API requests")


# =============================================================================
# Demo 3: Target Format
# =============================================================================
def demo_target_format() -> None:
    """Demonstrate target format for private and group messages."""
    print("\n" + "=" * 60)
    print("Demo 3: Target Format")
    print("=" * 60)

    print("Napcat provider uses the following target format:")
    print("\nPrivate messages:")
    print("  Format: 'private:<QQ号>'")
    print("  Example: 'private:123456789'")

    print("\nGroup messages:")
    print("  Format: 'group:<群号>'")
    print("  Example: 'group:987654321'")

    # Parse target examples
    targets = [
        "private:123456789",
        "group:987654321",
        "private:111222333",
        "group:444555666",
    ]

    print("\nParsing examples:")
    for target in targets:
        msg_type, target_id = target.split(":")
        print(f"  {target}")
        print(f"    Type: {msg_type}")
        print(f"    ID: {target_id}")


# =============================================================================
# Demo 4: Sending Text Messages
# =============================================================================
def demo_send_text() -> None:
    """Demonstrate sending text messages."""
    print("\n" + "=" * 60)
    print("Demo 4: Sending Text Messages")
    print("=" * 60)

    http_url = os.environ.get("NAPCAT_HTTP_URL")

    if not http_url:
        print("NAPCAT_HTTP_URL not set. Showing API structure only.")

        print("\nPrivate message API:")
        print("  POST /send_private_msg")
        print("  Body:")
        print_json({"user_id": 123456789, "message": "Hello!"})

        print("\nGroup message API:")
        print("  POST /send_group_msg")
        print("  Body:")
        print_json({"group_id": 987654321, "message": "Hello group!"})
        return

    config = NapcatProviderConfig(name="text_demo", http_url=http_url)
    provider = NapcatProvider(config)
    provider.connect()

    # Send private message
    print("Sending private message...")
    result = provider.send_text("Hello from Napcat Provider!", target="private:123456789")
    print(f"Result: {result.success}")

    # Send group message
    print("\nSending group message...")
    result = provider.send_text("Hello group!", target="group:987654321")
    print(f"Result: {result.success}")

    provider.disconnect()


# =============================================================================
# Demo 5: CQ Code Format
# =============================================================================
def demo_cq_code() -> None:
    """Demonstrate CQ code format for rich messages."""
    print("\n" + "=" * 60)
    print("Demo 5: CQ Code Format")
    print("=" * 60)

    print("CQ codes are used for rich content in OneBot11 protocol:")

    cq_codes = [
        ("[CQ:face,id=178]", "QQ表情"),
        ("[CQ:image,file=xxx.jpg]", "图片"),
        ("[CQ:at,qq=123456]", "@某人"),
        ("[CQ:at,qq=all]", "@全体成员"),
        ("[CQ:reply,id=12345]", "回复消息"),
        ("[CQ:record,file=xxx.amr]", "语音"),
        ("[CQ:video,file=xxx.mp4]", "视频"),
        ("[CQ:share,url=xxx,title=xxx]", "链接分享"),
    ]

    print("\nCommon CQ codes:")
    for code, desc in cq_codes:
        print(f"  {desc}: {code}")

    # Example message with CQ codes
    print("\nExample message with CQ codes:")
    message = "Hello [CQ:at,qq=123456] ! Check this out [CQ:image,file=photo.jpg]"
    print(f"  {message}")


# =============================================================================
# Demo 6: Sending Images
# =============================================================================
def demo_send_image() -> None:
    """Demonstrate sending image messages."""
    print("\n" + "=" * 60)
    print("Demo 6: Sending Images")
    print("=" * 60)

    print("Image sending methods:")

    print("\n1. Local file:")
    print("   [CQ:image,file=file:///path/to/image.jpg]")

    print("\n2. URL:")
    print("   [CQ:image,file=https://example.com/image.jpg]")

    print("\n3. Base64:")
    print("   [CQ:image,file=base64://iVBORw0KGgo...]")

    # Show API structure
    print("\nAPI structure for image message:")
    print_json(
        {
            "user_id": 123456789,
            "message": "[CQ:image,file=https://example.com/image.jpg]",
        }
    )


# =============================================================================
# Demo 7: Rich Text Conversion
# =============================================================================
def demo_rich_text_conversion() -> None:
    """Demonstrate rich text to CQ code conversion."""
    print("\n" + "=" * 60)
    print("Demo 7: Rich Text Conversion")
    print("=" * 60)

    print("The Napcat provider converts rich text to CQ code format:")

    # Example rich text structure
    rich_text = {
        "title": "Report Title",
        "content": [
            [{"tag": "text", "text": "Hello "}],
            [{"tag": "at", "user_id": "123456"}],
            [{"tag": "text", "text": " Check this: "}],
            [{"tag": "a", "text": "Link", "href": "https://example.com"}],
        ],
    }

    print("\nInput rich text:")
    print_json(rich_text)

    # Converted output
    converted = "Report Title\n\nHello \n[CQ:at,qq=123456]\n Check this: \nLink (https://example.com)"
    print("\nConverted to CQ code format:")
    print(f"  {converted}")


# =============================================================================
# Demo 8: Provider with Circuit Breaker
# =============================================================================
def demo_circuit_breaker() -> None:
    """Demonstrate circuit breaker integration."""
    print("\n" + "=" * 60)
    print("Demo 8: Provider with Circuit Breaker")
    print("=" * 60)

    http_url = os.environ.get("NAPCAT_HTTP_URL", "http://127.0.0.1:3000")

    # Create circuit breaker configuration
    cb_config = CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout_seconds=60.0,
    )

    print("Circuit breaker configuration:")
    print(f"  Failure threshold: {cb_config.failure_threshold}")
    print(f"  Success threshold: {cb_config.success_threshold}")
    print(f"  Timeout: {cb_config.timeout_seconds}s")

    # Create provider with circuit breaker
    config = NapcatProviderConfig(name="cb_demo", http_url=http_url)
    provider = NapcatProvider(config, circuit_breaker_config=cb_config)

    print(f"\nProvider created: {provider.name}")
    print("Circuit breaker will protect against cascading failures")


# =============================================================================
# Demo 9: Message Tracking
# =============================================================================
def demo_message_tracking() -> None:
    """Demonstrate message tracking integration."""
    print("\n" + "=" * 60)
    print("Demo 9: Message Tracking")
    print("=" * 60)

    http_url = os.environ.get("NAPCAT_HTTP_URL", "http://127.0.0.1:3000")

    # Create message tracker
    tracker = MessageTracker(max_history=1000)

    # Create provider with tracker
    config = NapcatProviderConfig(name="tracked_demo", http_url=http_url)
    provider = NapcatProvider(config, message_tracker=tracker)

    print(f"Provider created: {provider.name}")
    print("Message tracking enabled")

    # Simulate tracking
    print("\n--- Simulating message tracking ---")
    import uuid
    msg_id = str(uuid.uuid4())
    tracker.track(
        message_id=msg_id,
        provider="qq_napcat",
        target="group:123456",
        content="Test message",
    )
    print(f"Tracked message: {msg_id[:16]}...")

    tracker.update_status(msg_id, MessageStatus.SENT)
    tracker.update_status(msg_id, MessageStatus.DELIVERED)

    msg = tracker.get_message(msg_id)
    if msg:
        print(f"Status: {msg.status.value}")


# =============================================================================
# Demo 10: Real-World Usage Pattern
# =============================================================================
def demo_real_world_pattern() -> None:
    """Demonstrate a real-world usage pattern."""
    print("\n" + "=" * 60)
    print("Demo 10: Real-World Usage Pattern")
    print("=" * 60)

    class QQNotificationService:
        """Notification service using Napcat provider."""

        def __init__(self, http_url: str, access_token: str | None = None):
            self.config = NapcatProviderConfig(
                name="qq_notification",
                http_url=http_url,
                access_token=access_token,
            )
            self.provider = NapcatProvider(
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

        def send_to_user(self, user_id: int, message: str) -> bool:
            """Send message to a user."""
            self.connect()
            target = f"private:{user_id}"
            result = self.provider.send_text(message, target)
            return result.success

        def send_to_group(self, group_id: int, message: str) -> bool:
            """Send message to a group."""
            self.connect()
            target = f"group:{group_id}"
            result = self.provider.send_text(message, target)
            return result.success

        def send_alert(
            self,
            group_id: int,
            title: str,
            content: str,
            mention_all: bool = False,
        ) -> bool:
            """Send alert to a group."""
            self.connect()

            message = f"【{title}】\n{content}"
            if mention_all:
                message = "[CQ:at,qq=all] " + message

            target = f"group:{group_id}"
            result = self.provider.send_text(message, target)
            return result.success

    # Usage example
    http_url = os.environ.get("NAPCAT_HTTP_URL", "http://127.0.0.1:3000")

    service = QQNotificationService(http_url)

    print("QQNotificationService created")
    print("\nUsage examples:")
    print(
        """
# Send to user
service.send_to_user(123456789, "Hello!")

# Send to group
service.send_to_group(987654321, "Hello group!")

# Send alert with @all
service.send_alert(
    group_id=987654321,
    title="System Alert",
    content="Server maintenance at 3:00 AM",
    mention_all=True
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
    """Run all Napcat provider demonstrations."""
    print("=" * 60)
    print("QQ Napcat Provider Examples")
    print("=" * 60)

    demos = [
        ("Basic Provider Setup", demo_basic_setup),
        ("Provider with Access Token", demo_with_access_token),
        ("Target Format", demo_target_format),
        ("Sending Text Messages", demo_send_text),
        ("CQ Code Format", demo_cq_code),
        ("Sending Images", demo_send_image),
        ("Rich Text Conversion", demo_rich_text_conversion),
        ("Circuit Breaker Integration", demo_circuit_breaker),
        ("Message Tracking", demo_message_tracking),
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
