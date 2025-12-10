"""Message queue module for reliable message delivery with retry support."""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .logger import get_logger
from .provider import BaseProvider, Message, MessageType, SendResult

logger = get_logger(__name__)


@dataclass
class QueuedMessage:
    """Representation of a queued message with retry information."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = field(default=None)
    target: str = field(default="")
    provider_name: str = field(default="default")
    created_at: datetime = field(default_factory=datetime.now)
    retry_count: int = field(default=0)
    max_retries: int = field(default=3)
    error: str | None = field(default=None)
    message_type: MessageType = field(default=MessageType.TEXT)

    def __post_init__(self) -> None:
        """Validate message data after initialization."""
        if not self.target:
            raise ValueError("Message target cannot be empty")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")

    def is_retryable(self) -> bool:
        """Check if the message can be retried."""
        return self.retry_count < self.max_retries

    def get_retry_delay(self) -> float:
        """Calculate delay for next retry using exponential backoff."""
        # Base delay with exponential backoff: 1s, 2s, 4s, 8s...
        base_delay = 1.0
        return base_delay * (2 ** self.retry_count)

    def increment_retry(self) -> None:
        """Increment the retry count."""
        self.retry_count += 1


class MessageQueue:
    """Queue for reliable message delivery with retry support."""

    def __init__(
        self,
        providers: dict[str, BaseProvider],
        max_batch_size: int = 10,
        retry_delay: float = 5.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize message queue.

        Args:
            providers: Dictionary mapping provider names to BaseProvider instances
            max_batch_size: Maximum messages to process in one batch
            retry_delay: Base delay for retry attempts (seconds)
            max_retries: Default maximum retry attempts per message
        """
        self.providers = providers
        self.max_batch_size = max_batch_size
        self.retry_delay = retry_delay
        self.max_retries = max_retries

        # Thread-safe queue operations
        self._queue: deque[QueuedMessage] = deque()
        self._lock = asyncio.Lock()

        # Statistics tracking
        self._stats = {
            "total_enqueued": 0,
            "total_sent": 0,
            "total_failed": 0,
            "total_retried": 0,
            "current_size": 0,
        }

        logger.info(
            f"MessageQueue initialized with {len(providers)} providers, "
            f"batch_size={max_batch_size}, max_retries={max_retries}"
        )

    async def enqueue(self, message: QueuedMessage) -> None:
        """Add a message to the queue.

        Args:
            message: QueuedMessage to enqueue

        Raises:
            ValueError: If message validation fails
        """
        if not message.target:
            raise ValueError("Message target cannot be empty")
        if message.provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {message.provider_name}")

        async with self._lock:
            self._queue.append(message)
            self._stats["total_enqueued"] += 1
            self._stats["current_size"] = len(self._queue)
            logger.debug(
                f"Message enqueued: id={message.id}, target={message.target}, "
                f"provider={message.provider_name}, queue_size={len(self._queue)}"
            )

    async def enqueue_batch(self, messages: list[QueuedMessage]) -> None:
        """Add multiple messages to the queue.

        Args:
            messages: List of QueuedMessage objects to enqueue

        Raises:
            ValueError: If any message validation fails
        """
        for message in messages:
            if not message.target:
                raise ValueError("Message target cannot be empty")
            if message.provider_name not in self.providers:
                raise ValueError(f"Unknown provider: {message.provider_name}")

        async with self._lock:
            self._queue.extend(messages)
            self._stats["total_enqueued"] += len(messages)
            self._stats["current_size"] = len(self._queue)
            logger.info(
                f"Batch of {len(messages)} messages enqueued, "
                f"queue_size={len(self._queue)}"
            )

    async def process_queue(self) -> dict[str, Any]:
        """Process queued messages in batches.

        Processes messages with exponential backoff retry strategy. Messages
        that exceed max_retries are marked as failed.

        Returns:
            Dictionary with keys:
            - sent: Number of successfully sent messages
            - failed: Number of messages that exceeded max retries
            - retried: Number of messages requeued for retry
            - batch_count: Number of batches processed
            - processed: Total messages processed
        """
        results = {
            "sent": 0,
            "failed": 0,
            "retried": 0,
            "batch_count": 0,
            "processed": 0,
        }

        while True:
            # Get next batch of messages
            batch = await self._get_next_batch()
            if not batch:
                break

            results["batch_count"] += 1
            logger.debug(f"Processing batch {results['batch_count']} with {len(batch)} messages")

            # Process each message in the batch
            for message in batch:
                success = await self._send_message(message)

                if success:
                    results["sent"] += 1
                    self._stats["total_sent"] += 1
                    logger.info(
                        f"Message sent successfully: id={message.id}, "
                        f"target={message.target}"
                    )
                elif message.is_retryable():
                    # Re-queue for retry with exponential backoff
                    message.increment_retry()
                    retry_delay = message.get_retry_delay()

                    async with self._lock:
                        self._queue.append(message)

                    results["retried"] += 1
                    self._stats["total_retried"] += 1
                    logger.warning(
                        f"Message will be retried: id={message.id}, "
                        f"attempt={message.retry_count}/{message.max_retries}, "
                        f"delay={retry_delay}s, error={message.error}"
                    )
                else:
                    # Message exceeded max retries
                    results["failed"] += 1
                    self._stats["total_failed"] += 1
                    logger.error(
                        f"Message failed permanently: id={message.id}, "
                        f"target={message.target}, attempts={message.retry_count}, "
                        f"error={message.error}"
                    )

            results["processed"] += len(batch)

        async with self._lock:
            self._stats["current_size"] = len(self._queue)

        logger.info(
            f"Queue processing complete: sent={results['sent']}, "
            f"failed={results['failed']}, retried={results['retried']}, "
            f"batches={results['batch_count']}"
        )

        return results

    async def _get_next_batch(self) -> list[QueuedMessage]:
        """Get next batch of messages from queue.

        Returns:
            List of messages up to max_batch_size
        """
        async with self._lock:
            batch = []
            for _ in range(min(self.max_batch_size, len(self._queue))):
                batch.append(self._queue.popleft())
            return batch

    async def _send_message(self, msg: QueuedMessage) -> bool:
        """Send a single message.

        Attempts to send a message using the specified provider. Sets error
        message on failure.

        Args:
            msg: QueuedMessage to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            provider = self.providers.get(msg.provider_name)
            if not provider:
                msg.error = f"Provider not found: {msg.provider_name}"
                return False

            if not provider.is_connected:
                msg.error = f"Provider not connected: {msg.provider_name}"
                return False

            # Send message based on type
            result: SendResult | None = None

            if msg.message_type == MessageType.TEXT:
                result = provider.send_text(str(msg.content), msg.target)
            elif msg.message_type == MessageType.CARD:
                result = provider.send_card(msg.content, msg.target)
            elif msg.message_type == MessageType.RICH_TEXT:
                # For rich text, content should be tuple of (title, content_list)
                if isinstance(msg.content, tuple) and len(msg.content) >= 2:
                    title, content = msg.content[0], msg.content[1]
                    language = msg.content[2] if len(msg.content) > 2 else "zh_cn"
                    result = provider.send_rich_text(title, content, msg.target, language)
                else:
                    msg.error = "Rich text content must be tuple of (title, content_list)"
                    return False
            elif msg.message_type == MessageType.IMAGE:
                result = provider.send_image(str(msg.content), msg.target)
            else:
                # Fallback to generic message
                message_obj = Message(type=msg.message_type, content=msg.content)
                result = provider.send_message(message_obj, msg.target)

            if result and result.success:
                return True
            else:
                msg.error = result.error if result else "Unknown error"
                return False

        except Exception as exc:
            msg.error = f"Exception: {str(exc)}"
            logger.exception(f"Error sending message {msg.id}", exc_info=exc)
            return False

    def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics.

        Returns:
            Dictionary with statistics:
            - current_size: Number of messages currently in queue
            - total_enqueued: Total messages ever enqueued
            - total_sent: Total messages successfully sent
            - total_failed: Total messages permanently failed
            - total_retried: Total retry attempts made
        """
        stats = dict(self._stats)
        stats["current_size"] = len(self._queue)
        return stats

    def clear_queue(self) -> int:
        """Clear all queued messages.

        Returns:
            Number of messages cleared
        """
        count = len(self._queue)
        self._queue.clear()
        self._stats["current_size"] = 0
        logger.warning(f"Queue cleared: {count} messages removed")
        return count

    def __len__(self) -> int:
        """Return current queue size."""
        return len(self._queue)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<MessageQueue size={len(self._queue)}, "
            f"providers={len(self.providers)}, "
            f"sent={self._stats['total_sent']}, "
            f"failed={self._stats['total_failed']}>"
        )
