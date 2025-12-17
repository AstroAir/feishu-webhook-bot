"""Tests for message queue module with retry support."""

from __future__ import annotations

import asyncio

import pytest

from feishu_webhook_bot.core.message_queue import MessageQueue, QueuedMessage
from feishu_webhook_bot.core.provider import (
    BaseProvider,
    MessageType,
    ProviderConfig,
    SendResult,
)

# Use anyio for async tests with asyncio backend only
pytestmark = pytest.mark.anyio(backends=["asyncio"])


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    def __init__(self, name: str = "mock", succeed: bool = True):
        """Initialize mock provider."""
        config = ProviderConfig(provider_type="mock", name=name)
        super().__init__(config)
        self.succeed = succeed
        self.sent_messages = []
        self._connected = True

    def connect(self) -> None:
        """Connect provider."""
        self._connected = True

    def disconnect(self) -> None:
        """Disconnect provider."""
        self._connected = False

    def send_message(self, message, target: str) -> SendResult:
        """Send generic message."""
        if self.succeed:
            self.sent_messages.append(("message", target, message))
            return SendResult.ok(f"msg-{len(self.sent_messages)}")
        return SendResult.fail("Mock error")

    def send_text(self, text: str, target: str) -> SendResult:
        """Send text message."""
        if self.succeed:
            self.sent_messages.append(("text", target, text))
            return SendResult.ok(f"msg-{len(self.sent_messages)}")
        return SendResult.fail("Mock error")

    def send_card(self, card: dict, target: str) -> SendResult:
        """Send card message."""
        if self.succeed:
            self.sent_messages.append(("card", target, card))
            return SendResult.ok(f"msg-{len(self.sent_messages)}")
        return SendResult.fail("Mock error")

    def send_rich_text(
        self,
        title: str,
        content: list[list[dict]],
        target: str,
        language: str = "zh_cn",
    ) -> SendResult:
        """Send rich text message."""
        if self.succeed:
            self.sent_messages.append(("rich_text", target, (title, content, language)))
            return SendResult.ok(f"msg-{len(self.sent_messages)}")
        return SendResult.fail("Mock error")

    def send_image(self, image_key: str, target: str) -> SendResult:
        """Send image message."""
        if self.succeed:
            self.sent_messages.append(("image", target, image_key))
            return SendResult.ok(f"msg-{len(self.sent_messages)}")
        return SendResult.fail("Mock error")


class TestQueuedMessage:
    """Tests for QueuedMessage dataclass."""

    def test_queued_message_creation(self) -> None:
        """Test creating a queued message."""
        msg = QueuedMessage(
            content="Hello",
            target="webhook-1",
            provider_name="feishu",
        )
        assert msg.content == "Hello"
        assert msg.target == "webhook-1"
        assert msg.provider_name == "feishu"
        assert msg.retry_count == 0
        assert msg.max_retries == 3
        assert msg.error is None
        assert msg.message_type == MessageType.TEXT

    def test_queued_message_with_custom_id(self) -> None:
        """Test creating a message with custom ID."""
        msg = QueuedMessage(
            id="custom-123",
            content="Hello",
            target="webhook-1",
            provider_name="feishu",
        )
        assert msg.id == "custom-123"

    def test_queued_message_auto_id(self) -> None:
        """Test that auto-generated IDs are unique."""
        msg1 = QueuedMessage(content="Hello", target="webhook-1", provider_name="feishu")
        msg2 = QueuedMessage(content="Hello", target="webhook-1", provider_name="feishu")
        assert msg1.id != msg2.id

    def test_queued_message_validation_empty_target(self) -> None:
        """Test validation rejects empty target."""
        with pytest.raises(ValueError, match="target cannot be empty"):
            QueuedMessage(content="Hello", target="", provider_name="feishu")

    def test_queued_message_validation_negative_retries(self) -> None:
        """Test validation rejects negative max_retries."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            QueuedMessage(
                content="Hello",
                target="webhook-1",
                provider_name="feishu",
                max_retries=-1,
            )

    def test_is_retryable(self) -> None:
        """Test retry status checking."""
        msg = QueuedMessage(
            content="Hello",
            target="webhook-1",
            provider_name="feishu",
            max_retries=3,
        )
        assert msg.is_retryable() is True
        msg.retry_count = 2
        assert msg.is_retryable() is True
        msg.retry_count = 3
        assert msg.is_retryable() is False

    def test_get_retry_delay_exponential_backoff(self) -> None:
        """Test exponential backoff calculation."""
        msg = QueuedMessage(
            content="Hello",
            target="webhook-1",
            provider_name="feishu",
        )
        # First retry: 2^0 = 1 second
        assert msg.get_retry_delay() == 1.0
        msg.retry_count = 1
        # Second retry: 2^1 = 2 seconds
        assert msg.get_retry_delay() == 2.0
        msg.retry_count = 2
        # Third retry: 2^2 = 4 seconds
        assert msg.get_retry_delay() == 4.0
        msg.retry_count = 3
        # Fourth retry: 2^3 = 8 seconds
        assert msg.get_retry_delay() == 8.0

    def test_increment_retry(self) -> None:
        """Test incrementing retry counter."""
        msg = QueuedMessage(
            content="Hello",
            target="webhook-1",
            provider_name="feishu",
        )
        assert msg.retry_count == 0
        msg.increment_retry()
        assert msg.retry_count == 1
        msg.increment_retry()
        assert msg.retry_count == 2


class TestMessageQueue:
    """Tests for MessageQueue class."""

    @pytest.fixture
    def mock_provider(self) -> MockProvider:
        """Create a mock provider."""
        return MockProvider("feishu", succeed=True)

    @pytest.fixture
    def message_queue(self, mock_provider: MockProvider) -> MessageQueue:
        """Create a message queue with mock provider."""
        return MessageQueue(
            providers={"feishu": mock_provider},
            max_batch_size=5,
            max_retries=3,
        )

    async def test_enqueue_single_message(self, message_queue: MessageQueue) -> None:
        """Test enqueuing a single message."""
        msg = QueuedMessage(
            content="Hello",
            target="webhook-1",
            provider_name="feishu",
        )
        await message_queue.enqueue(msg)
        assert len(message_queue) == 1
        assert message_queue._stats["total_enqueued"] == 1

    async def test_enqueue_multiple_messages(self, message_queue: MessageQueue) -> None:
        """Test enqueuing multiple messages."""
        messages = [
            QueuedMessage(content=f"Message {i}", target="webhook-1", provider_name="feishu")
            for i in range(5)
        ]
        await message_queue.enqueue_batch(messages)
        assert len(message_queue) == 5
        assert message_queue._stats["total_enqueued"] == 5

    async def test_enqueue_invalid_target(self, message_queue: MessageQueue) -> None:
        """Test enqueuing message with invalid target."""
        with pytest.raises(ValueError, match="target cannot be empty"):
            QueuedMessage(content="Hello", target="", provider_name="feishu")

    async def test_enqueue_unknown_provider(self, message_queue: MessageQueue) -> None:
        """Test enqueuing message with unknown provider."""
        msg = QueuedMessage(
            content="Hello",
            target="webhook-1",
            provider_name="unknown",
        )
        with pytest.raises(ValueError, match="Unknown provider"):
            await message_queue.enqueue(msg)

    async def test_process_queue_success(self, message_queue: MessageQueue) -> None:
        """Test processing queue with successful sends."""
        messages = [
            QueuedMessage(content=f"Message {i}", target="webhook-1", provider_name="feishu")
            for i in range(3)
        ]
        await message_queue.enqueue_batch(messages)

        results = await message_queue.process_queue()

        assert results["sent"] == 3
        assert results["failed"] == 0
        assert results["retried"] == 0
        assert results["batch_count"] == 1
        assert results["processed"] == 3
        assert len(message_queue) == 0

    async def test_process_queue_with_failures(self) -> None:
        """Test processing queue with failed sends and retries."""
        failing_provider = MockProvider("feishu", succeed=False)
        queue = MessageQueue(
            providers={"feishu": failing_provider},
            max_batch_size=5,
            max_retries=1,
        )

        messages = [
            QueuedMessage(
                content=f"Message {i}",
                target="webhook-1",
                provider_name="feishu",
                max_retries=1,
            )
            for i in range(2)
        ]
        await queue.enqueue_batch(messages)

        # First process_queue call tries and retries messages
        results = await queue.process_queue()

        # Both messages failed on first attempt and are retried
        # process_queue processes all retries in one call
        assert results["sent"] == 0
        assert results["failed"] == 2  # Both messages exhausted retries in one call
        assert results["retried"] == 2  # Both retried once

    async def test_process_queue_batching(self) -> None:
        """Test that messages are processed in batches."""
        mock_provider = MockProvider("feishu", succeed=True)
        queue = MessageQueue(
            providers={"feishu": mock_provider},
            max_batch_size=3,
            max_retries=3,
        )

        messages = [
            QueuedMessage(content=f"Message {i}", target="webhook-1", provider_name="feishu")
            for i in range(7)
        ]
        await queue.enqueue_batch(messages)

        results = await queue.process_queue()

        # 7 messages with batch size 3 = 3 batches
        assert results["batch_count"] == 3
        assert results["sent"] == 7
        assert results["processed"] == 7

    async def test_send_text_message(self, message_queue: MessageQueue) -> None:
        """Test sending text message."""
        msg = QueuedMessage(
            content="Hello World",
            target="webhook-1",
            provider_name="feishu",
            message_type=MessageType.TEXT,
        )
        await message_queue.enqueue(msg)
        results = await message_queue.process_queue()

        assert results["sent"] == 1
        provider = message_queue.providers["feishu"]
        assert len(provider.sent_messages) == 1
        assert provider.sent_messages[0] == ("text", "webhook-1", "Hello World")

    async def test_send_card_message(self, message_queue: MessageQueue) -> None:
        """Test sending card message."""
        card = {"title": "Test Card", "elements": []}
        msg = QueuedMessage(
            content=card,
            target="webhook-1",
            provider_name="feishu",
            message_type=MessageType.CARD,
        )
        await message_queue.enqueue(msg)
        results = await message_queue.process_queue()

        assert results["sent"] == 1
        provider = message_queue.providers["feishu"]
        assert len(provider.sent_messages) == 1
        assert provider.sent_messages[0][0] == "card"

    async def test_send_image_message(self, message_queue: MessageQueue) -> None:
        """Test sending image message."""
        msg = QueuedMessage(
            content="img_abc123",
            target="webhook-1",
            provider_name="feishu",
            message_type=MessageType.IMAGE,
        )
        await message_queue.enqueue(msg)
        results = await message_queue.process_queue()

        assert results["sent"] == 1
        provider = message_queue.providers["feishu"]
        assert provider.sent_messages[0][0] == "image"

    async def test_send_rich_text_message(self, message_queue: MessageQueue) -> None:
        """Test sending rich text message."""
        content = (
            "Title",
            [
                [{"type": "text", "text": "Hello"}],
                [{"type": "text", "text": "World"}],
            ],
            "zh_cn",
        )
        msg = QueuedMessage(
            content=content,
            target="webhook-1",
            provider_name="feishu",
            message_type=MessageType.RICH_TEXT,
        )
        await message_queue.enqueue(msg)
        results = await message_queue.process_queue()

        assert results["sent"] == 1
        provider = message_queue.providers["feishu"]
        assert provider.sent_messages[0][0] == "rich_text"

    async def test_rich_text_invalid_content(self, message_queue: MessageQueue) -> None:
        """Test sending rich text with invalid content format."""
        msg = QueuedMessage(
            content="Invalid format",
            target="webhook-1",
            provider_name="feishu",
            message_type=MessageType.RICH_TEXT,
        )
        await message_queue.enqueue(msg)
        results = await message_queue.process_queue()

        assert results["failed"] == 1
        assert msg.error is not None

    async def test_disconnected_provider(self) -> None:
        """Test handling disconnected provider."""
        provider = MockProvider("feishu", succeed=True)
        provider._connected = False
        queue = MessageQueue(providers={"feishu": provider}, max_retries=1)

        msg = QueuedMessage(
            content="Hello",
            target="webhook-1",
            provider_name="feishu",
            max_retries=1,
        )
        await queue.enqueue(msg)
        results = await queue.process_queue()

        assert results["retried"] == 1
        assert msg.error == "Provider not connected: feishu"

    async def test_get_queue_stats(self, message_queue: MessageQueue) -> None:
        """Test getting queue statistics."""
        messages = [
            QueuedMessage(content=f"Message {i}", target="webhook-1", provider_name="feishu")
            for i in range(3)
        ]
        await message_queue.enqueue_batch(messages)

        stats = message_queue.get_queue_stats()
        assert stats["current_size"] == 3
        assert stats["total_enqueued"] == 3
        assert stats["total_sent"] == 0

        await message_queue.process_queue()
        stats = message_queue.get_queue_stats()
        assert stats["current_size"] == 0
        assert stats["total_sent"] == 3

    async def test_clear_queue(self, message_queue: MessageQueue) -> None:
        """Test clearing the queue."""
        messages = [
            QueuedMessage(content=f"Message {i}", target="webhook-1", provider_name="feishu")
            for i in range(5)
        ]
        await message_queue.enqueue_batch(messages)
        assert len(message_queue) == 5

        cleared = message_queue.clear_queue()
        assert cleared == 5
        assert len(message_queue) == 0

    def test_queue_repr(self, message_queue: MessageQueue) -> None:
        """Test queue string representation."""
        repr_str = repr(message_queue)
        assert "MessageQueue" in repr_str
        assert "size=0" in repr_str

    async def test_queue_thread_safety(self, message_queue: MessageQueue) -> None:
        """Test concurrent enqueue/dequeue operations."""

        async def enqueue_task(count: int) -> None:
            for i in range(count):
                msg = QueuedMessage(
                    content=f"Message {i}",
                    target="webhook-1",
                    provider_name="feishu",
                )
                await message_queue.enqueue(msg)

        # Enqueue from multiple tasks
        await asyncio.gather(
            enqueue_task(5),
            enqueue_task(5),
        )

        assert len(message_queue) == 10
        results = await message_queue.process_queue()
        assert results["sent"] == 10

    async def test_exponential_backoff_retry(self) -> None:
        """Test that exponential backoff delays are calculated correctly."""
        msg = QueuedMessage(
            content="Hello",
            target="webhook-1",
            provider_name="feishu",
            max_retries=2,
        )

        # Test retry delay calculation before any attempts
        assert msg.retry_count == 0
        assert msg.get_retry_delay() == 1.0  # 2^0 = 1

        msg.increment_retry()
        assert msg.retry_count == 1
        assert msg.get_retry_delay() == 2.0  # 2^1 = 2

        msg.increment_retry()
        assert msg.retry_count == 2
        assert msg.get_retry_delay() == 4.0  # 2^2 = 4

    async def test_message_with_provider_error(self, message_queue: MessageQueue) -> None:
        """Test handling provider send errors."""
        # Use async mock for provider that raises exception
        provider = message_queue.providers["feishu"]
        original_send_text = provider.send_text

        def mock_send_text(text: str, target: str) -> SendResult:
            raise RuntimeError("Network error")

        provider.send_text = mock_send_text

        msg = QueuedMessage(
            content="Hello",
            target="webhook-1",
            provider_name="feishu",
            max_retries=0,
        )
        await message_queue.enqueue(msg)
        results = await message_queue.process_queue()

        assert results["failed"] == 1
        assert "Exception:" in msg.error

        # Restore original method
        provider.send_text = original_send_text

    async def test_multiple_providers(self) -> None:
        """Test queue with multiple providers."""
        provider1 = MockProvider("feishu", succeed=True)
        provider2 = MockProvider("qq", succeed=True)
        queue = MessageQueue(
            providers={"feishu": provider1, "qq": provider2},
            max_batch_size=5,
        )

        msgs = [
            QueuedMessage(
                content="Feishu msg",
                target="webhook-1",
                provider_name="feishu",
            ),
            QueuedMessage(
                content="QQ msg",
                target="group-1",
                provider_name="qq",
            ),
        ]
        await queue.enqueue_batch(msgs)

        results = await queue.process_queue()
        assert results["sent"] == 2
        assert len(provider1.sent_messages) == 1
        assert len(provider2.sent_messages) == 1
