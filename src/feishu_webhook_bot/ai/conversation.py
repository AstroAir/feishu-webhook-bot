"""Conversation state management for multi-turn dialogues."""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic_ai import ModelMessage

from ..core.logger import get_logger

logger = get_logger("ai.conversation")


class ConversationState:
    """State for a single conversation with analytics and summarization.

    Attributes:
        user_id: Unique identifier for the user
        messages: List of messages in the conversation
        context: Additional context data for the conversation
        last_activity: Timestamp of last activity
        created_at: Timestamp when conversation was created
        input_tokens: Total input tokens used
        output_tokens: Total output tokens used
        summary: Optional conversation summary for long conversations
        message_count: Total number of messages
    """

    def __init__(self, user_id: str) -> None:
        """Initialize conversation state.

        Args:
            user_id: Unique identifier for the user
        """
        self.user_id = user_id
        self.messages: list[ModelMessage] = []
        self.context: dict[str, Any] = {}
        self.last_activity = datetime.now(UTC)
        self.created_at = datetime.now(UTC)
        self.input_tokens = 0
        self.output_tokens = 0
        self.summary: str | None = None
        self.message_count = 0

    def add_messages(
        self,
        messages: list[ModelMessage],
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Add messages to the conversation with token tracking.

        Args:
            messages: Messages to add
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
        """
        self.messages.extend(messages)
        self.message_count += len(messages)
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.last_activity = datetime.now(UTC)

        logger.debug(
            "Added %d messages to conversation %s (total: %d, tokens: %d in / %d out)",
            len(messages),
            self.user_id,
            self.message_count,
            self.input_tokens,
            self.output_tokens,
        )

    def get_messages(self, max_turns: int | None = None) -> list[ModelMessage]:
        """Get conversation messages.

        Args:
            max_turns: Maximum number of recent turns to return (None for all)

        Returns:
            List of messages
        """
        if max_turns is None:
            return self.messages.copy()

        # Keep the most recent messages up to max_turns
        # Each turn typically has a request and response
        max_messages = max_turns * 2
        return (
            self.messages[-max_messages:]
            if len(self.messages) > max_messages
            else self.messages.copy()
        )

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages.clear()
        self.context.clear()
        self.summary = None
        self.last_activity = datetime.now(UTC)
        logger.debug("Cleared conversation for user: %s", self.user_id)

    def is_expired(self, timeout_minutes: int) -> bool:
        """Check if conversation has expired.

        Args:
            timeout_minutes: Timeout in minutes

        Returns:
            True if conversation has expired
        """
        timeout = timedelta(minutes=timeout_minutes)
        return datetime.now(UTC) - self.last_activity > timeout

    def set_summary(self, summary: str) -> None:
        """Set a summary for the conversation.

        This is useful for long conversations to maintain context
        without keeping all messages in memory.

        Args:
            summary: Conversation summary
        """
        self.summary = summary
        logger.debug("Set summary for conversation %s (%d chars)", self.user_id, len(summary))

    def get_duration(self) -> timedelta:
        """Get the duration of the conversation.

        Returns:
            Time elapsed since conversation creation
        """
        return datetime.now(UTC) - self.created_at

    def get_analytics(self) -> dict[str, Any]:
        """Get analytics for this conversation.

        Returns:
            Dictionary with conversation analytics
        """
        duration = self.get_duration()
        total_tokens = self.input_tokens + self.output_tokens

        return {
            "user_id": self.user_id,
            "message_count": self.message_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": total_tokens,
            "duration_seconds": duration.total_seconds(),
            "duration_minutes": duration.total_seconds() / 60,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "has_summary": self.summary is not None,
            "context_keys": list(self.context.keys()),
        }

    def export_to_dict(self) -> dict[str, Any]:
        """Export conversation state to a dictionary.

        Returns:
            Dictionary representation of the conversation
        """
        return {
            "user_id": self.user_id,
            "messages": [
                {
                    "role": msg.role if hasattr(msg, "role") else "unknown",
                    "content": str(msg.content) if hasattr(msg, "content") else str(msg),
                    "timestamp": msg.timestamp.isoformat() if hasattr(msg, "timestamp") else None,
                }
                for msg in self.messages
            ],
            "context": self.context,
            "summary": self.summary,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }

    @classmethod
    def import_from_dict(cls, data: dict[str, Any]) -> ConversationState:
        """Import conversation state from a dictionary.

        Args:
            data: Dictionary representation of the conversation

        Returns:
            ConversationState instance
        """
        conv = cls(data["user_id"])
        conv.context = data.get("context", {})
        conv.summary = data.get("summary")
        conv.input_tokens = data.get("input_tokens", 0)
        conv.output_tokens = data.get("output_tokens", 0)
        conv.message_count = data.get("message_count", 0)

        # Parse timestamps
        if "created_at" in data:
            conv.created_at = datetime.fromisoformat(data["created_at"])
        if "last_activity" in data:
            conv.last_activity = datetime.fromisoformat(data["last_activity"])

        # Note: We don't restore messages as ModelMessage objects
        # since they may have complex internal state
        logger.info("Imported conversation for user: %s", conv.user_id)

        return conv


class ConversationManager:
    """Manages conversation states for multiple users.

    This class handles:
    - Creating and retrieving conversation states
    - Automatic cleanup of expired conversations
    - Thread-safe access to conversation data
    """

    def __init__(self, timeout_minutes: int = 30, cleanup_interval_seconds: int = 300) -> None:
        """Initialize conversation manager.

        Args:
            timeout_minutes: Minutes of inactivity before conversation expires
            cleanup_interval_seconds: Seconds between cleanup runs
        """
        self._conversations: dict[str, ConversationState] = {}
        self._timeout_minutes = timeout_minutes
        self._cleanup_interval = cleanup_interval_seconds
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None
        logger.info(
            "ConversationManager initialized (timeout=%dm, cleanup=%ds)",
            timeout_minutes,
            cleanup_interval_seconds,
        )

    async def get_conversation(self, user_id: str) -> ConversationState:
        """Get or create conversation state for a user.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Conversation state
        """
        async with self._lock:
            if user_id not in self._conversations:
                logger.debug("Creating new conversation for user: %s", user_id)
                self._conversations[user_id] = ConversationState(user_id)
            return self._conversations[user_id]

    async def clear_conversation(self, user_id: str) -> None:
        """Clear conversation history for a user.

        Args:
            user_id: Unique identifier for the user
        """
        async with self._lock:
            if user_id in self._conversations:
                logger.debug("Clearing conversation for user: %s", user_id)
                self._conversations[user_id].clear()

    async def delete_conversation(self, user_id: str) -> None:
        """Delete conversation for a user.

        Args:
            user_id: Unique identifier for the user
        """
        async with self._lock:
            if user_id in self._conversations:
                logger.debug("Deleting conversation for user: %s", user_id)
                del self._conversations[user_id]

    async def cleanup_expired(self) -> int:
        """Remove expired conversations.

        Returns:
            Number of conversations removed
        """
        async with self._lock:
            expired_users = [
                user_id
                for user_id, conv in self._conversations.items()
                if conv.is_expired(self._timeout_minutes)
            ]

            for user_id in expired_users:
                logger.debug("Removing expired conversation for user: %s", user_id)
                del self._conversations[user_id]

            if expired_users:
                logger.info("Cleaned up %d expired conversations", len(expired_users))

            return len(expired_users)

    async def _cleanup_loop(self) -> None:
        """Background task to periodically clean up expired conversations."""
        logger.info("Starting conversation cleanup loop")
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_expired()
        except asyncio.CancelledError:
            logger.info("Conversation cleanup loop cancelled")
            raise

    def start_cleanup(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Conversation cleanup task started")

    async def stop_cleanup(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            logger.info("Conversation cleanup task stopped")

    async def export_conversation(self, user_id: str) -> str:
        """Export a conversation to JSON format.

        Args:
            user_id: Unique identifier for the user

        Returns:
            JSON string representation of the conversation

        Raises:
            ValueError: If conversation not found
        """
        async with self._lock:
            if user_id not in self._conversations:
                raise ValueError(f"Conversation not found for user: {user_id}")

            conv = self._conversations[user_id]
            data = conv.export_to_dict()
            logger.info("Exported conversation for user: %s", user_id)
            return json.dumps(data, indent=2)

    async def import_conversation(self, json_data: str) -> str:
        """Import a conversation from JSON format.

        Args:
            json_data: JSON string representation of the conversation

        Returns:
            User ID of the imported conversation

        Raises:
            ValueError: If JSON is invalid
        """
        try:
            data = json.loads(json_data)
            conv = ConversationState.import_from_dict(data)

            async with self._lock:
                self._conversations[conv.user_id] = conv
                logger.info("Imported conversation for user: %s", conv.user_id)
                return conv.user_id

        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Failed to import conversation: %s", exc, exc_info=True)
            raise ValueError(f"Invalid conversation data: {str(exc)}") from exc

    async def get_conversation_analytics(self, user_id: str) -> dict[str, Any]:
        """Get analytics for a specific conversation.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Dictionary with conversation analytics

        Raises:
            ValueError: If conversation not found
        """
        async with self._lock:
            if user_id not in self._conversations:
                raise ValueError(f"Conversation not found for user: {user_id}")

            return self._conversations[user_id].get_analytics()

    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics about active conversations.

        Returns:
            Dictionary with conversation statistics
        """
        async with self._lock:
            total = len(self._conversations)

            if total == 0:
                return {
                    "total_conversations": 0,
                    "total_messages": 0,
                    "total_tokens": 0,
                    "average_messages_per_conversation": 0,
                    "average_tokens_per_conversation": 0,
                    "timeout_minutes": self._timeout_minutes,
                }

            total_messages = sum(conv.message_count for conv in self._conversations.values())
            total_input_tokens = sum(conv.input_tokens for conv in self._conversations.values())
            total_output_tokens = sum(conv.output_tokens for conv in self._conversations.values())
            total_tokens = total_input_tokens + total_output_tokens

            # Calculate averages
            avg_messages = total_messages / total
            avg_tokens = total_tokens / total

            # Find longest conversation
            longest_conv = max(
                self._conversations.values(), key=lambda c: c.message_count, default=None
            )

            # Calculate average duration
            total_duration = sum(
                conv.get_duration().total_seconds() for conv in self._conversations.values()
            )
            avg_duration_minutes = (total_duration / total) / 60 if total > 0 else 0

            return {
                "total_conversations": total,
                "total_messages": total_messages,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_tokens,
                "average_messages_per_conversation": round(avg_messages, 2),
                "average_tokens_per_conversation": round(avg_tokens, 2),
                "average_duration_minutes": round(avg_duration_minutes, 2),
                "longest_conversation_messages": longest_conv.message_count if longest_conv else 0,
                "longest_conversation_user": longest_conv.user_id if longest_conv else None,
                "timeout_minutes": self._timeout_minutes,
                "conversations_with_summary": sum(
                    1 for conv in self._conversations.values() if conv.summary
                ),
            }
