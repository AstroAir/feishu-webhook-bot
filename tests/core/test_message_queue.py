"""Comprehensive tests for message queue module.

Tests cover:
- QueuedMessage dataclass
- MessageQueue initialization
- Message enqueueing
- Queue processing
- Retry logic
- Statistics tracking
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from feishu_webhook_bot.core.message_queue import (
    MessageQueue,
    QueuedMessage,
)
from feishu_webhook_bot.core.provider import MessageType, SendResult

# ==============================================================================
# QueuedMessage Tests
# ==============================================================================


class TestQueuedMessage:
    """Tests for QueuedMessage dataclass."""

    def test_queued_message_creation(self):
        """Test QueuedMessage creation with required fields."""
        msg = QueuedMessage(
            content="Hello",
            target="user123",
        )

        assert msg.content == "Hello"
        assert msg.target == "user123"
        assert msg.provider_name == "default"
        assert msg.retry_count == 0
        assert msg.max_retries == 3

    def test_queued_message_custom_values(self):
        """Test QueuedMessage with custom values."""
        msg = QueuedMessage(
            content="Test",
            target="group456",
            provider_name="feishu",
            max_retries=5,
            message_type=MessageType.CARD,
        )

        assert msg.provider_name == "feishu"
        assert msg.max_retries == 5
        assert msg.message_type == MessageType.CARD

    def test_queued_message_empty_target_raises(self):
        """Test QueuedMessage raises on empty target."""
        with pytest.raises(ValueError, match="target cannot be empty"):
            QueuedMessage(content="Hello", target="")

    def test_queued_message_negative_max_retries_raises(self):
        """Test QueuedMessage raises on negative max_retries."""
        with pytest.raises(ValueError, match="non-negative"):
            QueuedMessage(content="Hello", target="user", max_retries=-1)

    def test_queued_message_has_id(self):
        """Test QueuedMessage has auto-generated ID."""
        msg = QueuedMessage(content="Hello", target="user")

        assert msg.id is not None
        assert len(msg.id) > 0

    def test_queued_message_unique_ids(self):
        """Test each QueuedMessage has unique ID."""
        msg1 = QueuedMessage(content="Hello", target="user")
        msg2 = QueuedMessage(content="Hello", target="user")

        assert msg1.id != msg2.id


class TestQueuedMessageRetry:
    """Tests for QueuedMessage retry functionality."""

    def test_is_retryable_true(self):
        """Test is_retryable returns True when retries available."""
        msg = QueuedMessage(content="Hello", target="user", max_retries=3)

        assert msg.is_retryable() is True

    def test_is_retryable_false(self):
        """Test is_retryable returns False when max retries reached."""
        msg = QueuedMessage(content="Hello", target="user", max_retries=3)
        msg.retry_count = 3

        assert msg.is_retryable() is False

    def test_increment_retry(self):
        """Test increment_retry increases count."""
        msg = QueuedMessage(content="Hello", target="user")

        assert msg.retry_count == 0
        msg.increment_retry()
        assert msg.retry_count == 1

    def test_get_retry_delay_exponential(self):
        """Test get_retry_delay uses exponential backoff."""
        msg = QueuedMessage(content="Hello", target="user")

        # First retry: 1 * 2^0 = 1
        assert msg.get_retry_delay() == 1.0

        msg.retry_count = 1
        # Second retry: 1 * 2^1 = 2
        assert msg.get_retry_delay() == 2.0

        msg.retry_count = 2
        # Third retry: 1 * 2^2 = 4
        assert msg.get_retry_delay() == 4.0


# ==============================================================================
# MessageQueue Initialization Tests
# ==============================================================================


class TestMessageQueueInitialization:
    """Tests for MessageQueue initialization."""

    def test_queue_creation(self):
        """Test MessageQueue creation."""
        providers = {"default": Mock()}
        queue = MessageQueue(providers)

        assert len(queue) == 0
        assert queue.max_batch_size == 10
        assert queue.max_retries == 3

    def test_queue_custom_settings(self):
        """Test MessageQueue with custom settings."""
        providers = {"default": Mock()}
        queue = MessageQueue(
            providers,
            max_batch_size=20,
            retry_delay=10.0,
            max_retries=5,
        )

        assert queue.max_batch_size == 20
        assert queue.retry_delay == 10.0
        assert queue.max_retries == 5

    def test_queue_repr(self):
        """Test MessageQueue string representation."""
        providers = {"default": Mock()}
        queue = MessageQueue(providers)

        repr_str = repr(queue)

        assert "MessageQueue" in repr_str
        assert "size=0" in repr_str


# ==============================================================================
# Message Enqueueing Tests
# ==============================================================================


class TestMessageEnqueueing:
    """Tests for message enqueueing."""

    @pytest.fixture
    def queue(self):
        """Create a message queue with mock provider."""
        providers = {"default": Mock(), "feishu": Mock()}
        return MessageQueue(providers)

    @pytest.mark.anyio
    async def test_enqueue_message(self, queue):
        """Test enqueueing a single message."""
        msg = QueuedMessage(content="Hello", target="user123")

        await queue.enqueue(msg)

        assert len(queue) == 1

    @pytest.mark.anyio
    async def test_enqueue_empty_target_raises(self, queue):
        """Test enqueueing message with empty target raises."""
        msg = QueuedMessage.__new__(QueuedMessage)
        msg.target = ""
        msg.provider_name = "default"

        with pytest.raises(ValueError, match="target cannot be empty"):
            await queue.enqueue(msg)

    @pytest.mark.anyio
    async def test_enqueue_unknown_provider_raises(self, queue):
        """Test enqueueing message with unknown provider raises."""
        msg = QueuedMessage(
            content="Hello",
            target="user123",
            provider_name="unknown",
        )

        with pytest.raises(ValueError, match="Unknown provider"):
            await queue.enqueue(msg)

    @pytest.mark.anyio
    async def test_enqueue_batch(self, queue):
        """Test enqueueing multiple messages."""
        messages = [
            QueuedMessage(content="Hello 1", target="user1"),
            QueuedMessage(content="Hello 2", target="user2"),
            QueuedMessage(content="Hello 3", target="user3"),
        ]

        await queue.enqueue_batch(messages)

        assert len(queue) == 3

    @pytest.mark.anyio
    async def test_enqueue_updates_stats(self, queue):
        """Test enqueueing updates statistics."""
        msg = QueuedMessage(content="Hello", target="user123")

        await queue.enqueue(msg)

        stats = queue.get_queue_stats()
        assert stats["total_enqueued"] == 1
        assert stats["current_size"] == 1


# ==============================================================================
# Queue Processing Tests
# ==============================================================================


class TestQueueProcessing:
    """Tests for queue processing."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider."""
        provider = Mock()
        provider.is_connected = True
        provider.send_text.return_value = SendResult.ok("msg_123")
        return provider

    @pytest.fixture
    def queue(self, mock_provider):
        """Create a message queue with mock provider."""
        return MessageQueue({"default": mock_provider})

    @pytest.mark.anyio
    async def test_process_empty_queue(self, queue):
        """Test processing empty queue."""
        results = await queue.process_queue()

        assert results["sent"] == 0
        assert results["failed"] == 0
        assert results["processed"] == 0

    @pytest.mark.anyio
    async def test_process_single_message(self, queue, mock_provider):
        """Test processing single message."""
        msg = QueuedMessage(content="Hello", target="user123")
        await queue.enqueue(msg)

        results = await queue.process_queue()

        assert results["sent"] == 1
        assert results["failed"] == 0
        mock_provider.send_text.assert_called_once()

    @pytest.mark.anyio
    async def test_process_multiple_messages(self, queue, mock_provider):
        """Test processing multiple messages."""
        for i in range(5):
            msg = QueuedMessage(content=f"Hello {i}", target=f"user{i}")
            await queue.enqueue(msg)

        results = await queue.process_queue()

        assert results["sent"] == 5
        assert mock_provider.send_text.call_count == 5

    @pytest.mark.anyio
    async def test_process_failed_message_retries(self, queue, mock_provider):
        """Test failed messages are retried until exhausted."""
        mock_provider.send_text.return_value = SendResult.fail("Error")

        msg = QueuedMessage(content="Hello", target="user123", max_retries=2)
        await queue.enqueue(msg)

        results = await queue.process_queue()

        # Message retried twice (max_retries=2), then failed permanently
        assert results["retried"] == 2
        assert results["failed"] == 1
        assert len(queue) == 0  # Queue is empty after processing

    @pytest.mark.anyio
    async def test_process_exhausted_retries(self, queue, mock_provider):
        """Test message fails after exhausting retries."""
        mock_provider.send_text.return_value = SendResult.fail("Error")

        msg = QueuedMessage(content="Hello", target="user123", max_retries=0)
        await queue.enqueue(msg)

        results = await queue.process_queue()

        assert results["failed"] == 1
        assert results["retried"] == 0


# ==============================================================================
# Message Type Handling Tests
# ==============================================================================


class TestMessageTypeHandling:
    """Tests for different message type handling."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider with all send methods."""
        provider = Mock()
        provider.is_connected = True
        provider.send_text.return_value = SendResult.ok("msg_123")
        provider.send_card.return_value = SendResult.ok("msg_123")
        provider.send_rich_text.return_value = SendResult.ok("msg_123")
        provider.send_image.return_value = SendResult.ok("msg_123")
        provider.send_message.return_value = SendResult.ok("msg_123")
        return provider

    @pytest.fixture
    def queue(self, mock_provider):
        """Create a message queue with mock provider."""
        return MessageQueue({"default": mock_provider})

    @pytest.mark.anyio
    async def test_send_text_message(self, queue, mock_provider):
        """Test sending text message."""
        msg = QueuedMessage(
            content="Hello",
            target="user123",
            message_type=MessageType.TEXT,
        )
        await queue.enqueue(msg)
        await queue.process_queue()

        mock_provider.send_text.assert_called_once_with("Hello", "user123")

    @pytest.mark.anyio
    async def test_send_card_message(self, queue, mock_provider):
        """Test sending card message."""
        card_content = {"header": {"title": "Test"}}
        msg = QueuedMessage(
            content=card_content,
            target="user123",
            message_type=MessageType.CARD,
        )
        await queue.enqueue(msg)
        await queue.process_queue()

        mock_provider.send_card.assert_called_once_with(card_content, "user123")

    @pytest.mark.anyio
    async def test_send_image_message(self, queue, mock_provider):
        """Test sending image message."""
        msg = QueuedMessage(
            content="img_key_123",
            target="user123",
            message_type=MessageType.IMAGE,
        )
        await queue.enqueue(msg)
        await queue.process_queue()

        mock_provider.send_image.assert_called_once_with("img_key_123", "user123")

    @pytest.mark.anyio
    async def test_send_rich_text_message(self, queue, mock_provider):
        """Test sending rich text message."""
        msg = QueuedMessage(
            content=("Title", [["text content"]], "zh_cn"),
            target="user123",
            message_type=MessageType.RICH_TEXT,
        )
        await queue.enqueue(msg)
        await queue.process_queue()

        mock_provider.send_rich_text.assert_called_once()


# ==============================================================================
# Statistics Tests
# ==============================================================================


class TestQueueStatistics:
    """Tests for queue statistics."""

    @pytest.fixture
    def queue(self):
        """Create a message queue with mock provider."""
        provider = Mock()
        provider.is_connected = True
        provider.send_text.return_value = SendResult.ok("msg_123")
        return MessageQueue({"default": provider})

    @pytest.mark.anyio
    async def test_get_queue_stats(self, queue):
        """Test getting queue statistics."""
        stats = queue.get_queue_stats()

        assert "current_size" in stats
        assert "total_enqueued" in stats
        assert "total_sent" in stats
        assert "total_failed" in stats
        assert "total_retried" in stats

    @pytest.mark.anyio
    async def test_stats_update_on_enqueue(self, queue):
        """Test stats update on enqueue."""
        msg = QueuedMessage(content="Hello", target="user123")
        await queue.enqueue(msg)

        stats = queue.get_queue_stats()
        assert stats["total_enqueued"] == 1

    @pytest.mark.anyio
    async def test_stats_update_on_send(self, queue):
        """Test stats update on successful send."""
        msg = QueuedMessage(content="Hello", target="user123")
        await queue.enqueue(msg)
        await queue.process_queue()

        stats = queue.get_queue_stats()
        assert stats["total_sent"] == 1


# ==============================================================================
# Queue Management Tests
# ==============================================================================


class TestQueueManagement:
    """Tests for queue management operations."""

    @pytest.fixture
    def queue(self):
        """Create a message queue with mock provider."""
        return MessageQueue({"default": Mock()})

    @pytest.mark.anyio
    async def test_clear_queue(self, queue):
        """Test clearing the queue."""
        for i in range(5):
            msg = QueuedMessage(content=f"Hello {i}", target=f"user{i}")
            await queue.enqueue(msg)

        assert len(queue) == 5

        cleared = queue.clear_queue()

        assert cleared == 5
        assert len(queue) == 0

    @pytest.mark.anyio
    async def test_queue_len(self, queue):
        """Test queue length."""
        assert len(queue) == 0

        msg = QueuedMessage(content="Hello", target="user123")
        await queue.enqueue(msg)

        assert len(queue) == 1


# ==============================================================================
# Error Handling Tests
# ==============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.anyio
    async def test_provider_not_connected(self):
        """Test handling disconnected provider."""
        provider = Mock()
        provider.is_connected = False

        queue = MessageQueue({"default": provider})
        msg = QueuedMessage(content="Hello", target="user123", max_retries=0)
        await queue.enqueue(msg)

        results = await queue.process_queue()

        assert results["failed"] == 1

    @pytest.mark.anyio
    async def test_provider_exception(self):
        """Test handling provider exception."""
        provider = Mock()
        provider.is_connected = True
        provider.send_text.side_effect = Exception("Network error")

        queue = MessageQueue({"default": provider})
        msg = QueuedMessage(content="Hello", target="user123", max_retries=0)
        await queue.enqueue(msg)

        results = await queue.process_queue()

        assert results["failed"] == 1
        assert msg.error is not None
