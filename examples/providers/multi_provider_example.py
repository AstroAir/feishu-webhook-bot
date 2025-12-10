#!/usr/bin/env python3
"""Multi-Provider Example.

This example demonstrates multi-provider orchestration:
- Provider registry for managing multiple providers
- Sending to multiple platforms simultaneously
- Provider-specific message formatting
- Failover and fallback strategies
- Load balancing across providers
- Unified message interface

The multi-provider system enables cross-platform messaging from a single bot.
"""

import asyncio
import os
from typing import Any

from feishu_webhook_bot.core import (
    CircuitBreakerConfig,
    LoggingConfig,
    MessageTracker,
    get_logger,
    setup_logging,
)
from feishu_webhook_bot.core.provider import (
    BaseProvider,
    Message,
    MessageType,
    ProviderConfig,
    ProviderRegistry,
    SendResult,
)
from feishu_webhook_bot.providers.feishu import FeishuProvider, FeishuProviderConfig
from feishu_webhook_bot.providers.qq_napcat import NapcatProvider, NapcatProviderConfig

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Provider Registry
# =============================================================================
def demo_provider_registry() -> None:
    """Demonstrate provider registry usage."""
    print("\n" + "=" * 60)
    print("Demo 1: Provider Registry")
    print("=" * 60)

    # Create registry (Note: ProviderRegistry is deprecated, use dict instead)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        registry = ProviderRegistry()
    print("ProviderRegistry created (deprecated, use dict instead)")

    # Register Feishu provider
    feishu_config = FeishuProviderConfig(
        name="feishu_main",
        url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    )
    feishu_provider = FeishuProvider(feishu_config)
    registry.register(feishu_provider)  # API changed: only takes provider
    print("Registered: feishu_main")

    # Register QQ provider
    qq_config = NapcatProviderConfig(
        name="qq_main",
        http_url="http://127.0.0.1:3000",
    )
    qq_provider = NapcatProvider(qq_config)
    registry.register(qq_provider)
    print("Registered: qq_main")

    # List providers using get_all()
    print("\nRegistered providers:")
    for name, provider in registry.get_all().items():
        print(f"  - {name}: {provider.config.provider_type}")

    # Get specific provider
    print("\nGetting provider by name:")
    feishu = registry.get("feishu_main")
    if feishu:
        print(f"  feishu_main: {feishu.name}")

    # Check if provider exists
    print("\nProvider existence check:")
    print(f"  'feishu_main' exists: {'feishu_main' in registry.get_all()}")
    print(f"  'slack' exists: {'slack' in registry.get_all()}")


# =============================================================================
# Demo 2: Multi-Platform Message Sending
# =============================================================================
def demo_multi_platform_sending() -> None:
    """Demonstrate sending to multiple platforms."""
    print("\n" + "=" * 60)
    print("Demo 2: Multi-Platform Message Sending")
    print("=" * 60)

    class MultiPlatformMessenger:
        """Messenger that sends to multiple platforms."""

        def __init__(self):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                self.registry = ProviderRegistry()
            self._setup_providers()

        def _setup_providers(self) -> None:
            """Setup all providers."""
            # Feishu
            feishu_url = os.environ.get(
                "FEISHU_WEBHOOK_URL",
                "https://open.feishu.cn/open-apis/bot/v2/hook/demo",
            )
            feishu_config = FeishuProviderConfig(name="feishu", url=feishu_url)
            self.registry.register(FeishuProvider(feishu_config))

            # QQ
            qq_url = os.environ.get("NAPCAT_HTTP_URL", "http://127.0.0.1:3000")
            qq_config = NapcatProviderConfig(name="qq", http_url=qq_url)
            self.registry.register(NapcatProvider(qq_config))

        def send_to_all(self, message: str) -> dict[str, bool]:
            """Send message to all platforms."""
            results = {}
            for name, provider in self.registry.get_all().items():
                try:
                    provider.connect()
                    # Use default target for demo
                    result = provider.send_text(message, target="default")
                    results[name] = result.success
                except Exception as e:
                    logger.error(f"Failed to send to {name}: {e}")
                    results[name] = False
            return results

        def send_to_specific(
            self, provider_name: str, message: str, target: str
        ) -> SendResult:
            """Send to a specific provider."""
            provider = self.registry.get(provider_name)
            if not provider:
                return SendResult(
                    success=False, error=f"Provider not found: {provider_name}"
                )

            provider.connect()
            return provider.send_text(message, target)

    messenger = MultiPlatformMessenger()

    print("MultiPlatformMessenger created with providers:")
    for name in messenger.registry.get_all().keys():
        print(f"  - {name}")

    print("\nUsage:")
    print("  # Send to all platforms")
    print("  results = messenger.send_to_all('Hello everyone!')")
    print("")
    print("  # Send to specific platform")
    print("  result = messenger.send_to_specific('feishu', 'Hello Feishu!', webhook_url)")


# =============================================================================
# Demo 3: Provider-Specific Formatting
# =============================================================================
def demo_provider_formatting() -> None:
    """Demonstrate provider-specific message formatting."""
    print("\n" + "=" * 60)
    print("Demo 3: Provider-Specific Formatting")
    print("=" * 60)

    class MessageFormatter:
        """Format messages for different providers."""

        @staticmethod
        def format_alert(
            provider_type: str,
            title: str,
            content: str,
            severity: str = "info",
        ) -> dict[str, Any] | str:
            """Format alert message for specific provider."""
            if provider_type == "feishu":
                # Feishu card format
                colors = {
                    "info": "blue",
                    "warning": "orange",
                    "error": "red",
                }
                return {
                    "header": {
                        "title": {"tag": "plain_text", "content": title},
                        "template": colors.get(severity, "blue"),
                    },
                    "elements": [
                        {"tag": "div", "text": {"tag": "lark_md", "content": content}}
                    ],
                }
            elif provider_type == "qq_napcat":
                # QQ CQ code format
                emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}
                return f"{emoji.get(severity, 'ℹ️')} 【{title}】\n{content}"
            else:
                # Plain text fallback
                return f"[{severity.upper()}] {title}\n{content}"

        @staticmethod
        def format_notification(
            provider_type: str,
            message: str,
            mentions: list[str] | None = None,
        ) -> dict[str, Any] | str:
            """Format notification with mentions."""
            if provider_type == "feishu":
                content = [[{"tag": "text", "text": message}]]
                if mentions:
                    content.append(
                        [{"tag": "at", "user_id": uid} for uid in mentions]
                    )
                return {
                    "title": "Notification",
                    "content": content,
                }
            elif provider_type == "qq_napcat":
                text = message
                if mentions:
                    at_codes = " ".join(f"[CQ:at,qq={uid}]" for uid in mentions)
                    text = f"{at_codes} {message}"
                return text
            else:
                return message

    formatter = MessageFormatter()

    # Format alert for different providers
    print("Alert formatting for different providers:")

    for provider_type in ["feishu", "qq_napcat", "unknown"]:
        print(f"\n--- {provider_type} ---")
        formatted = formatter.format_alert(
            provider_type=provider_type,
            title="Server Alert",
            content="CPU usage exceeded 90%",
            severity="warning",
        )
        if isinstance(formatted, dict):
            print_json(formatted)
        else:
            print(f"  {formatted}")


# =============================================================================
# Demo 4: Failover Strategy
# =============================================================================
def demo_failover_strategy() -> None:
    """Demonstrate failover between providers."""
    print("\n" + "=" * 60)
    print("Demo 4: Failover Strategy")
    print("=" * 60)

    class FailoverMessenger:
        """Messenger with failover support."""

        def __init__(self, providers: list[tuple[str, BaseProvider]]):
            self.providers = providers
            self._primary_index = 0

        def send_with_failover(self, message: str, target: str) -> SendResult:
            """Send message with automatic failover."""
            errors = []

            # Try each provider in order
            for i, (name, provider) in enumerate(self.providers):
                try:
                    provider.connect()
                    result = provider.send_text(message, target)

                    if result.success:
                        if i != self._primary_index:
                            logger.info(f"Failover to {name} successful")
                        return result
                    else:
                        errors.append(f"{name}: {result.error}")

                except Exception as e:
                    errors.append(f"{name}: {str(e)}")
                    logger.warning(f"Provider {name} failed: {e}")

            # All providers failed
            return SendResult(
                success=False,
                error=f"All providers failed: {'; '.join(errors)}",
            )

        def get_healthy_providers(self) -> list[str]:
            """Get list of healthy providers."""
            healthy = []
            for name, provider in self.providers:
                try:
                    provider.connect()
                    healthy.append(name)
                except Exception:
                    pass
            return healthy

    print("FailoverMessenger provides automatic failover:")
    print("  1. Try primary provider")
    print("  2. If failed, try next provider")
    print("  3. Continue until success or all fail")

    print("\nUsage:")
    print(
        """
providers = [
    ("feishu", feishu_provider),
    ("qq", qq_provider),
    ("slack", slack_provider),
]
messenger = FailoverMessenger(providers)
result = messenger.send_with_failover("Hello!", target)
"""
    )


# =============================================================================
# Demo 5: Load Balancing
# =============================================================================
def demo_load_balancing() -> None:
    """Demonstrate load balancing across providers."""
    print("\n" + "=" * 60)
    print("Demo 5: Load Balancing")
    print("=" * 60)

    class LoadBalancedMessenger:
        """Messenger with load balancing."""

        def __init__(self, providers: list[tuple[str, BaseProvider]]):
            self.providers = providers
            self._current_index = 0
            self._send_counts: dict[str, int] = {name: 0 for name, _ in providers}

        def send_round_robin(self, message: str, target: str) -> SendResult:
            """Send using round-robin load balancing."""
            if not self.providers:
                return SendResult(success=False, error="No providers available")

            name, provider = self.providers[self._current_index]
            self._current_index = (self._current_index + 1) % len(self.providers)

            try:
                provider.connect()
                result = provider.send_text(message, target)
                if result.success:
                    self._send_counts[name] += 1
                return result
            except Exception as e:
                return SendResult(success=False, error=str(e))

        def get_statistics(self) -> dict[str, int]:
            """Get send statistics per provider."""
            return dict(self._send_counts)

    print("LoadBalancedMessenger distributes load across providers:")
    print("  - Round-robin: Rotate through providers")
    print("  - Tracks send counts per provider")

    print("\nUsage:")
    print(
        """
messenger = LoadBalancedMessenger(providers)

# Messages are distributed across providers
for i in range(10):
    messenger.send_round_robin(f"Message {i}", target)

# Check distribution
stats = messenger.get_statistics()
# {'feishu': 4, 'qq': 3, 'slack': 3}
"""
    )


# =============================================================================
# Demo 6: Unified Message Interface
# =============================================================================
def demo_unified_interface() -> None:
    """Demonstrate unified message interface."""
    print("\n" + "=" * 60)
    print("Demo 6: Unified Message Interface")
    print("=" * 60)

    class UnifiedMessenger:
        """Unified interface for all providers."""

        def __init__(self):
            self.registry = ProviderRegistry()
            self.tracker = MessageTracker()

        def register_provider(
            self, name: str, provider: BaseProvider
        ) -> None:
            """Register a provider."""
            self.registry.register(name, provider)

        def send(
            self,
            provider: str,
            target: str,
            message: Message,
        ) -> SendResult:
            """Send message through unified interface."""
            p = self.registry.get(provider)
            if not p:
                return SendResult(success=False, error=f"Unknown provider: {provider}")

            p.connect()

            # Track message
            import uuid
            msg_id = str(uuid.uuid4())
            self.tracker.track(
                message_id=msg_id,
                provider=provider,
                target=target,
                content=str(message.content),
            )

            # Send based on message type
            if message.type == MessageType.TEXT:
                result = p.send_text(str(message.content), target)
            elif message.type == MessageType.CARD:
                result = p.send_card(message.content, target)
            elif message.type == MessageType.RICH_TEXT:
                content = message.content
                if isinstance(content, dict):
                    result = p.send_rich_text(
                        content.get("title", ""),
                        content.get("content", []),
                        target,
                    )
                else:
                    result = SendResult(success=False, error="Invalid rich text format")
            elif message.type == MessageType.IMAGE:
                result = p.send_image(str(message.content), target)
            else:
                result = p.send_message(message, target)

            # Update tracking
            from feishu_webhook_bot.core import MessageStatus

            if result.success:
                self.tracker.update_status(msg_id, MessageStatus.DELIVERED)
            else:
                self.tracker.update_status(
                    msg_id, MessageStatus.FAILED, error=result.error
                )

            return result

        def broadcast(
            self,
            targets: dict[str, str],
            message: Message,
        ) -> dict[str, SendResult]:
            """Broadcast message to multiple providers."""
            results = {}
            for provider, target in targets.items():
                results[provider] = self.send(provider, target, message)
            return results

    print("UnifiedMessenger provides a single interface for all providers:")
    print("  - Automatic message type handling")
    print("  - Built-in message tracking")
    print("  - Broadcast to multiple providers")

    print("\nUsage:")
    print(
        """
messenger = UnifiedMessenger()
messenger.register_provider("feishu", feishu_provider)
messenger.register_provider("qq", qq_provider)

# Send text message
message = Message(type=MessageType.TEXT, content="Hello!")
result = messenger.send("feishu", webhook_url, message)

# Broadcast to all
targets = {
    "feishu": "webhook_url",
    "qq": "group:123456",
}
results = messenger.broadcast(targets, message)
"""
    )


# =============================================================================
# Demo 7: Real-World Multi-Provider Setup
# =============================================================================
def demo_real_world_setup() -> None:
    """Demonstrate a real-world multi-provider setup."""
    print("\n" + "=" * 60)
    print("Demo 7: Real-World Multi-Provider Setup")
    print("=" * 60)

    class NotificationHub:
        """Central hub for multi-platform notifications."""

        def __init__(self):
            self.registry = ProviderRegistry()
            self.tracker = MessageTracker()
            self._channel_mapping: dict[str, list[tuple[str, str]]] = {}

        def add_provider(
            self,
            name: str,
            provider: BaseProvider,
        ) -> None:
            """Add a provider to the hub."""
            self.registry.register(name, provider)

        def add_channel(
            self,
            channel_name: str,
            destinations: list[tuple[str, str]],
        ) -> None:
            """Add a notification channel with destinations.

            Args:
                channel_name: Name of the channel (e.g., "alerts", "reports")
                destinations: List of (provider_name, target) tuples
            """
            self._channel_mapping[channel_name] = destinations

        def notify(
            self,
            channel: str,
            title: str,
            content: str,
            severity: str = "info",
        ) -> dict[str, bool]:
            """Send notification to a channel."""
            destinations = self._channel_mapping.get(channel, [])
            results = {}

            for provider_name, target in destinations:
                provider = self.registry.get(provider_name)
                if not provider:
                    results[f"{provider_name}:{target}"] = False
                    continue

                try:
                    provider.connect()

                    # Format based on provider type
                    if provider.config.provider_type == "feishu":
                        card = self._format_feishu_alert(title, content, severity)
                        result = provider.send_card(card, target)
                    else:
                        text = f"[{severity.upper()}] {title}\n{content}"
                        result = provider.send_text(text, target)

                    results[f"{provider_name}:{target}"] = result.success

                except Exception as e:
                    logger.error(f"Failed to notify {provider_name}:{target}: {e}")
                    results[f"{provider_name}:{target}"] = False

            return results

        def _format_feishu_alert(
            self, title: str, content: str, severity: str
        ) -> dict[str, Any]:
            """Format alert as Feishu card."""
            colors = {"info": "blue", "warning": "orange", "error": "red"}
            return {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": colors.get(severity, "blue"),
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": content}}
                ],
            }

    print("NotificationHub - Central notification management:")
    print("\nSetup:")
    print(
        """
hub = NotificationHub()

# Add providers
hub.add_provider("feishu", feishu_provider)
hub.add_provider("qq", qq_provider)

# Configure channels
hub.add_channel("alerts", [
    ("feishu", "https://webhook.feishu.cn/xxx"),
    ("qq", "group:123456"),
])

hub.add_channel("reports", [
    ("feishu", "https://webhook.feishu.cn/yyy"),
])

# Send notifications
hub.notify(
    channel="alerts",
    title="Server Alert",
    content="CPU usage exceeded 90%",
    severity="warning"
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
    """Run all multi-provider demonstrations."""
    print("=" * 60)
    print("Multi-Provider Examples")
    print("=" * 60)

    demos = [
        ("Provider Registry", demo_provider_registry),
        ("Multi-Platform Sending", demo_multi_platform_sending),
        ("Provider-Specific Formatting", demo_provider_formatting),
        ("Failover Strategy", demo_failover_strategy),
        ("Load Balancing", demo_load_balancing),
        ("Unified Message Interface", demo_unified_interface),
        ("Real-World Multi-Provider Setup", demo_real_world_setup),
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
