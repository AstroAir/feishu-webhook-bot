#!/usr/bin/env python3
"""Message Queue Example.

This example demonstrates the message queue for reliable message delivery:
- Basic queue operations (enqueue, process)
- Batch message processing
- Retry mechanism with exponential backoff
- Queue statistics and monitoring
- Integration with providers
- Error handling and recovery

The message queue ensures reliable delivery with automatic retries
for failed messages.
"""

import asyncio
from datetime import datetime
from typing import Any

from feishu_webhook_bot.core import (
    LoggingConfig,
    MessageQueue,
    QueuedMessage,
    get_logger,
    setup_logging,
)
from feishu_webhook_bot.core.provider import (
    BaseProvider,
    Message,
    MessageType,
    ProviderConfig,
    SendResult,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Mock Provider for Testing
# =============================================================================
class MockProviderConfig(ProviderConfig):
    """Configuration for mock provider."""

    provider_type: str = "mock"
    failure_rate: float = 0.0  # Probability of failure (0.0 to 1.0)


class MockProvider(BaseProvider):
    """Mock provider for testing message queue."""

    def __init__(self, config: MockProviderConfig):
        super().__init__(config)
        self.config: MockProviderConfig = config
        self._sent_messages: list[dict[str, Any]] = []
        self._failure_count = 0
        import random

        self._random = random

    def connect(self) -> None:
        self._connected = True
        self.logger.info(f"MockProvider '{self.config.name}' connected")

    def disconnect(self) -> None:
        self._connected = False
        self.logger.info(f"MockProvider '{self.config.name}' disconnected")

    def send_message(self, message: Message, target: str) -> SendResult:
        """Send a message (mock implementation)."""
        # Simulate random failures
        if self._random.random() < self.config.failure_rate:
            self._failure_count += 1
            return SendResult(
                success=False,
                message_id=None,
                error="Simulated failure",
            )

        msg_id = f"msg_{len(self._sent_messages) + 1}"
        self._sent_messages.append(
            {
                "id": msg_id,
                "type": message.type.value,
                "content": message.content,
                "target": target,
                "timestamp": datetime.now().isoformat(),
            }
        )
        return SendResult(success=True, message_id=msg_id)

    def send_text(self, text: str, target: str) -> SendResult:
        """Send a text message."""
        return self.send_message(Message(type=MessageType.TEXT, content=text), target)

    def send_card(self, card: dict[str, Any], target: str) -> SendResult:
        """Send a card message."""
        return self.send_message(Message(type=MessageType.CARD, content=card), target)

    def send_rich_text(
        self, title: str, content: list[list[dict[str, Any]]], target: str, language: str = "zh_cn"
    ) -> SendResult:
        """Send a rich text message."""
        return self.send_message(
            Message(type=MessageType.RICH_TEXT, content={"title": title, "content": content}),
            target,
        )

    def send_image(self, image_key: str, target: str) -> SendResult:
        """Send an image message."""
        return self.send_message(Message(type=MessageType.IMAGE, content=image_key), target)

    def get_sent_messages(self) -> list[dict[str, Any]]:
        """Get all sent messages."""
        return self._sent_messages.copy()

    def get_failure_count(self) -> int:
        """Get number of simulated failures."""
        return self._failure_count


# =============================================================================
# Demo 1: Basic Queue Operations
# =============================================================================
async def demo_basic_queue_operations() -> None:
    """Demonstrate basic queue operations."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Queue Operations")
    print("=" * 60)

    # Create mock provider
    provider_config = MockProviderConfig(name="test_provider")
    provider = MockProvider(provider_config)
    provider.connect()

    # Create message queue
    queue = MessageQueue(
        providers={"default": provider},
        max_batch_size=5,
        max_retries=3,
    )

    print("Queue created with batch size: 5, max retries: 3")
    print(f"Initial queue size: {len(queue)}")

    # Enqueue messages
    print("\n--- Enqueueing messages ---")
    for i in range(5):
        msg = QueuedMessage(
            content=f"Hello, message {i + 1}!",
            target="webhook_url",
            provider_name="default",
            message_type=MessageType.TEXT,
        )
        await queue.enqueue(msg)
        print(f"Enqueued message {i + 1}: {msg.id[:8]}...")

    print(f"\nQueue size after enqueueing: {len(queue)}")

    # Process queue
    print("\n--- Processing queue ---")
    results = await queue.process_queue()

    print("\nProcessing results:")
    print(f"  Sent: {results['sent']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Retried: {results['retried']}")
    print(f"  Batches processed: {results['batch_count']}")

    # Check sent messages
    sent = provider.get_sent_messages()
    print(f"\nMessages sent by provider: {len(sent)}")

    # Get queue statistics
    stats = queue.get_queue_stats()
    print("\nQueue statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


# =============================================================================
# Demo 2: Batch Message Processing
# =============================================================================
async def demo_batch_processing() -> None:
    """Demonstrate batch message processing."""
    print("\n" + "=" * 60)
    print("Demo 2: Batch Message Processing")
    print("=" * 60)

    # Create provider
    provider_config = MockProviderConfig(name="batch_provider")
    provider = MockProvider(provider_config)
    provider.connect()

    # Create queue with small batch size
    queue = MessageQueue(
        providers={"default": provider},
        max_batch_size=3,  # Process 3 messages per batch
    )

    # Create batch of messages
    messages = [
        QueuedMessage(
            content=f"Batch message {i + 1}",
            target="webhook_url",
            provider_name="default",
        )
        for i in range(10)
    ]

    # Enqueue all at once
    print(f"Enqueueing {len(messages)} messages as batch...")
    await queue.enqueue_batch(messages)
    print(f"Queue size: {len(queue)}")

    # Process queue
    print("\n--- Processing queue in batches ---")
    results = await queue.process_queue()

    print("\nResults:")
    print(f"  Total processed: {results['processed']}")
    print(f"  Batches: {results['batch_count']}")
    print(f"  Expected batches: {(len(messages) + 2) // 3}")  # Ceiling division


# =============================================================================
# Demo 3: Retry Mechanism
# =============================================================================
async def demo_retry_mechanism() -> None:
    """Demonstrate retry mechanism with exponential backoff."""
    print("\n" + "=" * 60)
    print("Demo 3: Retry Mechanism")
    print("=" * 60)

    # Create provider with 50% failure rate
    provider_config = MockProviderConfig(name="flaky_provider", failure_rate=0.5)
    provider = MockProvider(provider_config)
    provider.connect()

    # Create queue
    queue = MessageQueue(
        providers={"default": provider},
        max_batch_size=10,
        max_retries=3,
    )

    # Enqueue messages
    print("Enqueueing 5 messages with 50% failure rate provider...")
    for i in range(5):
        msg = QueuedMessage(
            content=f"Retry test message {i + 1}",
            target="webhook_url",
            provider_name="default",
            max_retries=3,
        )
        await queue.enqueue(msg)

    # Process multiple times to handle retries
    print("\n--- Processing with retries ---")
    total_sent = 0
    total_failed = 0
    total_retried = 0

    for round_num in range(4):  # Multiple rounds to process retries
        if len(queue) == 0:
            break

        print(f"\nRound {round_num + 1}: Queue size = {len(queue)}")
        results = await queue.process_queue()
        total_sent += results["sent"]
        total_failed += results["failed"]
        total_retried += results["retried"]
        print(
            f"  Sent: {results['sent']}, Failed: {results['failed']}, Retried: {results['retried']}"
        )

    print("\n--- Final Summary ---")
    print(f"Total sent: {total_sent}")
    print(f"Total failed (exceeded retries): {total_failed}")
    print(f"Total retry attempts: {total_retried}")
    print(f"Provider failure count: {provider.get_failure_count()}")


# =============================================================================
# Demo 4: QueuedMessage Features
# =============================================================================
async def demo_queued_message_features() -> None:
    """Demonstrate QueuedMessage features."""
    print("\n" + "=" * 60)
    print("Demo 4: QueuedMessage Features")
    print("=" * 60)

    # Create a message
    msg = QueuedMessage(
        content="Test message content",
        target="https://webhook.example.com",
        provider_name="default",
        max_retries=5,
        message_type=MessageType.TEXT,
    )

    print("QueuedMessage properties:")
    print(f"  ID: {msg.id}")
    print(f"  Content: {msg.content}")
    print(f"  Target: {msg.target}")
    print(f"  Provider: {msg.provider_name}")
    print(f"  Created at: {msg.created_at}")
    print(f"  Retry count: {msg.retry_count}")
    print(f"  Max retries: {msg.max_retries}")
    print(f"  Message type: {msg.message_type}")

    # Test retry logic
    print("\n--- Retry backoff calculation ---")
    for _i in range(5):
        delay = msg.get_retry_delay()
        is_retryable = msg.is_retryable()
        print(f"  Retry {msg.retry_count}: delay = {delay}s, retryable = {is_retryable}")
        msg.increment_retry()

    print("\nAfter max retries:")
    print(f"  Retry count: {msg.retry_count}")
    print(f"  Is retryable: {msg.is_retryable()}")


# =============================================================================
# Demo 5: Different Message Types
# =============================================================================
async def demo_message_types() -> None:
    """Demonstrate different message types in queue."""
    print("\n" + "=" * 60)
    print("Demo 5: Different Message Types")
    print("=" * 60)

    # Create provider
    provider_config = MockProviderConfig(name="multi_type_provider")
    provider = MockProvider(provider_config)
    provider.connect()

    # Create queue
    queue = MessageQueue(providers={"default": provider})

    # Enqueue different message types
    print("Enqueueing different message types...")

    # Text message
    await queue.enqueue(
        QueuedMessage(
            content="Hello, this is a text message!",
            target="webhook_url",
            provider_name="default",
            message_type=MessageType.TEXT,
        )
    )
    print("  - Text message enqueued")

    # Card message
    card_content = {
        "config": {"wide_screen_mode": True},
        "elements": [{"tag": "div", "text": {"content": "Card content", "tag": "plain_text"}}],
    }
    await queue.enqueue(
        QueuedMessage(
            content=card_content,
            target="webhook_url",
            provider_name="default",
            message_type=MessageType.CARD,
        )
    )
    print("  - Card message enqueued")

    # Rich text message (tuple format: title, content, language)
    rich_text_content = (
        "Rich Text Title",
        [[{"tag": "text", "text": "Rich text content"}]],
        "zh_cn",
    )
    await queue.enqueue(
        QueuedMessage(
            content=rich_text_content,
            target="webhook_url",
            provider_name="default",
            message_type=MessageType.RICH_TEXT,
        )
    )
    print("  - Rich text message enqueued")

    # Image message
    await queue.enqueue(
        QueuedMessage(
            content="img_v2_xxx",
            target="webhook_url",
            provider_name="default",
            message_type=MessageType.IMAGE,
        )
    )
    print("  - Image message enqueued")

    # Process queue
    print("\n--- Processing queue ---")
    results = await queue.process_queue()
    print(f"Sent: {results['sent']}")

    # Check sent messages
    sent = provider.get_sent_messages()
    print("\nSent messages:")
    for msg in sent:
        print(f"  - Type: {msg['type']}, Target: {msg['target']}")


# =============================================================================
# Demo 6: Queue Statistics and Monitoring
# =============================================================================
async def demo_queue_monitoring() -> None:
    """Demonstrate queue statistics and monitoring."""
    print("\n" + "=" * 60)
    print("Demo 6: Queue Statistics and Monitoring")
    print("=" * 60)

    # Create provider with some failures
    provider_config = MockProviderConfig(name="monitored_provider", failure_rate=0.3)
    provider = MockProvider(provider_config)
    provider.connect()

    # Create queue
    queue = MessageQueue(
        providers={"default": provider},
        max_batch_size=5,
        max_retries=2,
    )

    # Initial stats
    print("Initial queue statistics:")
    stats = queue.get_queue_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Enqueue messages
    print("\n--- Enqueueing 20 messages ---")
    for i in range(20):
        await queue.enqueue(
            QueuedMessage(
                content=f"Monitored message {i + 1}",
                target="webhook_url",
                provider_name="default",
                max_retries=2,
            )
        )

    # Stats after enqueueing
    print("\nAfter enqueueing:")
    stats = queue.get_queue_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Process in multiple rounds
    print("\n--- Processing queue ---")
    for round_num in range(3):
        if len(queue) == 0:
            break
        results = await queue.process_queue()
        print(
            f"Round {round_num + 1}: sent={results['sent']}, failed={results['failed']}, retried={results['retried']}"
        )

    # Final stats
    print("\nFinal queue statistics:")
    stats = queue.get_queue_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Queue representation
    print(f"\nQueue repr: {queue}")


# =============================================================================
# Demo 7: Queue Clear Operation
# =============================================================================
async def demo_queue_clear() -> None:
    """Demonstrate queue clear operation."""
    print("\n" + "=" * 60)
    print("Demo 7: Queue Clear Operation")
    print("=" * 60)

    # Create provider
    provider_config = MockProviderConfig(name="clear_provider")
    provider = MockProvider(provider_config)
    provider.connect()

    # Create queue
    queue = MessageQueue(providers={"default": provider})

    # Enqueue messages
    print("Enqueueing 10 messages...")
    for i in range(10):
        await queue.enqueue(
            QueuedMessage(
                content=f"Message {i + 1}",
                target="webhook_url",
                provider_name="default",
            )
        )

    print(f"Queue size: {len(queue)}")

    # Clear queue
    print("\n--- Clearing queue ---")
    cleared = queue.clear_queue()
    print(f"Cleared {cleared} messages")
    print(f"Queue size after clear: {len(queue)}")

    # Stats after clear
    stats = queue.get_queue_stats()
    print("\nStatistics after clear:")
    print(f"  current_size: {stats['current_size']}")
    print(f"  total_enqueued: {stats['total_enqueued']}")


# =============================================================================
# Demo 8: Multi-Provider Queue
# =============================================================================
async def demo_multi_provider_queue() -> None:
    """Demonstrate queue with multiple providers."""
    print("\n" + "=" * 60)
    print("Demo 8: Multi-Provider Queue")
    print("=" * 60)

    # Create multiple providers
    feishu_config = MockProviderConfig(name="feishu")
    feishu_provider = MockProvider(feishu_config)
    feishu_provider.connect()

    qq_config = MockProviderConfig(name="qq")
    qq_provider = MockProvider(qq_config)
    qq_provider.connect()

    slack_config = MockProviderConfig(name="slack")
    slack_provider = MockProvider(slack_config)
    slack_provider.connect()

    # Create queue with multiple providers
    queue = MessageQueue(
        providers={
            "feishu": feishu_provider,
            "qq": qq_provider,
            "slack": slack_provider,
        }
    )

    print("Queue created with providers: feishu, qq, slack")

    # Enqueue messages for different providers
    print("\n--- Enqueueing messages for different providers ---")

    await queue.enqueue(
        QueuedMessage(
            content="Hello Feishu!",
            target="feishu_webhook",
            provider_name="feishu",
        )
    )
    print("  - Message for Feishu enqueued")

    await queue.enqueue(
        QueuedMessage(
            content="Hello QQ!",
            target="group:123456",
            provider_name="qq",
        )
    )
    print("  - Message for QQ enqueued")

    await queue.enqueue(
        QueuedMessage(
            content="Hello Slack!",
            target="slack_webhook",
            provider_name="slack",
        )
    )
    print("  - Message for Slack enqueued")

    # Process queue
    print("\n--- Processing queue ---")
    results = await queue.process_queue()
    print(f"Sent: {results['sent']}")

    # Check each provider
    print("\nMessages sent per provider:")
    print(f"  Feishu: {len(feishu_provider.get_sent_messages())}")
    print(f"  QQ: {len(qq_provider.get_sent_messages())}")
    print(f"  Slack: {len(slack_provider.get_sent_messages())}")


# =============================================================================
# Main Entry Point
# =============================================================================
async def main() -> None:
    """Run all message queue demonstrations."""
    print("=" * 60)
    print("Message Queue Examples")
    print("=" * 60)

    demos = [
        ("Basic Queue Operations", demo_basic_queue_operations),
        ("Batch Message Processing", demo_batch_processing),
        ("Retry Mechanism", demo_retry_mechanism),
        ("QueuedMessage Features", demo_queued_message_features),
        ("Different Message Types", demo_message_types),
        ("Queue Statistics and Monitoring", demo_queue_monitoring),
        ("Queue Clear Operation", demo_queue_clear),
        ("Multi-Provider Queue", demo_multi_provider_queue),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            await demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
