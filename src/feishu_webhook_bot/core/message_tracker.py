"""Message delivery tracking and confirmation for Feishu Webhook Bot.

This module provides message tracking functionality including:
- Message status tracking (pending, sent, delivered, read, failed, expired)
- Duplicate detection based on content hash
- Automatic cleanup of old messages
- Statistics and monitoring
- SQLite persistence (optional)
- Thread-safe operations
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger(__name__)


class MessageStatus(str, Enum):
    """Message delivery status enumeration."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class TrackedMessage:
    """Represents a tracked message with delivery status and metadata."""

    message_id: str
    provider: str
    target: str
    content_hash: str
    status: MessageStatus
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    error: str | None = None
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for storage."""
        return {
            "message_id": self.message_id,
            "provider": self.provider,
            "target": self.target,
            "content_hash": self.content_hash,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "error": self.error,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrackedMessage:
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            provider=data["provider"],
            target=data["target"],
            content_hash=data["content_hash"],
            status=MessageStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            sent_at=datetime.fromisoformat(data["sent_at"]) if data.get("sent_at") else None,
            delivered_at=datetime.fromisoformat(data["delivered_at"])
            if data.get("delivered_at")
            else None,
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            metadata=data.get("metadata", {}),
        )


class MessageTracker:
    """Thread-safe message tracking system with persistence support."""

    def __init__(
        self,
        max_history: int = 10000,
        cleanup_interval: float = 3600.0,
        db_path: str | None = None,
    ):
        """Initialize message tracker.

        Args:
            max_history: Maximum number of messages to keep in memory
            cleanup_interval: Interval in seconds for automatic cleanup (0 to disable)
            db_path: Optional SQLite database path for persistence
        """
        self.messages: dict[str, TrackedMessage] = {}
        self.max_history = max_history
        self.cleanup_interval = cleanup_interval
        self.db_path = db_path
        self._lock = threading.RLock()
        self._cleanup_thread: threading.Thread | None = None
        self._stop_cleanup = threading.Event()

        if db_path:
            self._init_db(db_path)

        if cleanup_interval > 0:
            self._start_cleanup_thread()

    def _init_db(self, db_path: str) -> None:
        """Initialize SQLite database for persistence."""
        try:
            path = Path(db_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        target TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        sent_at TEXT,
                        delivered_at TEXT,
                        error TEXT,
                        retry_count INTEGER DEFAULT 0,
                        metadata TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_provider
                    ON messages(provider)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_status
                    ON messages(status)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_created_at
                    ON messages(created_at)
                    """
                )
                conn.commit()
            logger.info(f"Initialized message database at {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)

    def _start_cleanup_thread(self) -> None:
        """Start background cleanup thread."""
        if self.cleanup_interval <= 0:
            return

        self._stop_cleanup.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker, daemon=True, name="MessageTrackerCleanup"
        )
        self._cleanup_thread.start()
        logger.debug(f"Started cleanup thread with interval {self.cleanup_interval}s")

    def _cleanup_worker(self) -> None:
        """Background worker for periodic cleanup."""
        while not self._stop_cleanup.wait(self.cleanup_interval):
            try:
                old_count = len(self.messages)
                removed = self.cleanup_old_messages()
                if removed > 0:
                    logger.debug(
                        f"Cleanup removed {removed} old messages "
                        f"({old_count} -> {len(self.messages)})"
                    )
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}", exc_info=True)

    def stop_cleanup(self) -> None:
        """Stop the cleanup background thread."""
        if self._cleanup_thread:
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5.0)
            logger.debug("Stopped cleanup thread")

    def track(
        self, message_id: str, provider: str, target: str, content: Any
    ) -> TrackedMessage:
        """Track a new message.

        Args:
            message_id: Unique message identifier
            provider: Provider name (e.g., 'feishu', 'slack')
            target: Target identifier (e.g., webhook URL, user ID)
            content: Message content to hash for duplicate detection

        Returns:
            TrackedMessage instance
        """
        content_hash = self._calculate_hash(content)
        now = datetime.now()

        message = TrackedMessage(
            message_id=message_id,
            provider=provider,
            target=target,
            content_hash=content_hash,
            status=MessageStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        with self._lock:
            self.messages[message_id] = message

            # Enforce max history
            if len(self.messages) > self.max_history:
                self._evict_oldest()

            # Persist if database enabled
            if self.db_path:
                self._save_to_db(message)

        logger.debug(f"Tracked message {message_id} for {provider}:{target}")
        return message

    def update_status(
        self,
        message_id: str,
        status: MessageStatus,
        error: str | None = None,
        retry_count: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update message status.

        Args:
            message_id: Message identifier
            status: New status
            error: Error message if status is FAILED
            retry_count: Update retry count
            metadata: Additional metadata to merge

        Returns:
            True if message was found and updated, False otherwise
        """
        with self._lock:
            message = self.messages.get(message_id)
            if not message:
                logger.warning(f"Message {message_id} not found for status update")
                return False

            message.status = status
            message.updated_at = datetime.now()

            if error:
                message.error = error
            if retry_count is not None:
                message.retry_count = retry_count

            if metadata:
                message.metadata.update(metadata)

            # Update timestamp based on status
            if status == MessageStatus.SENT and not message.sent_at:
                message.sent_at = datetime.now()
            elif status == MessageStatus.DELIVERED and not message.delivered_at:
                message.delivered_at = datetime.now()

            # Persist if database enabled
            if self.db_path:
                self._update_db(message)

            logger.debug(
                f"Updated message {message_id} status to {status.value}"
                + (f" (error: {error})" if error else "")
            )
            return True

    def get_message(self, message_id: str) -> TrackedMessage | None:
        """Get a tracked message by ID.

        Args:
            message_id: Message identifier

        Returns:
            TrackedMessage or None if not found
        """
        with self._lock:
            return self.messages.get(message_id)

    def get_pending_messages(self) -> list[TrackedMessage]:
        """Get all pending messages.

        Returns:
            List of messages with PENDING status
        """
        return self.get_messages_by_status(MessageStatus.PENDING)

    def get_failed_messages(self) -> list[TrackedMessage]:
        """Get all failed messages.

        Returns:
            List of messages with FAILED status
        """
        return self.get_messages_by_status(MessageStatus.FAILED)

    def get_messages_by_status(self, status: MessageStatus) -> list[TrackedMessage]:
        """Get all messages with specific status.

        Args:
            status: MessageStatus to filter by

        Returns:
            List of matching messages sorted by creation time (newest first)
        """
        with self._lock:
            messages = [msg for msg in self.messages.values() if msg.status == status]
            return sorted(messages, key=lambda m: m.created_at, reverse=True)

    def get_messages_by_provider(self, provider: str) -> list[TrackedMessage]:
        """Get all messages for a specific provider.

        Args:
            provider: Provider name to filter by

        Returns:
            List of matching messages sorted by creation time (newest first)
        """
        with self._lock:
            messages = [msg for msg in self.messages.values() if msg.provider == provider]
            return sorted(messages, key=lambda m: m.created_at, reverse=True)

    def cleanup_old_messages(self, max_age_seconds: float = 86400) -> int:
        """Remove messages older than specified age.

        Args:
            max_age_seconds: Maximum age in seconds (default: 24 hours)

        Returns:
            Number of messages removed
        """
        cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)
        removed = 0

        with self._lock:
            to_remove = [
                msg_id
                for msg_id, msg in self.messages.items()
                if msg.created_at < cutoff_time
            ]

            for msg_id in to_remove:
                del self.messages[msg_id]
                removed += 1

                # Also remove from database if enabled
                if self.db_path:
                    self._delete_from_db(msg_id)

        if removed > 0:
            logger.info(f"Cleaned up {removed} messages older than {max_age_seconds}s")

        return removed

    def get_statistics(self) -> dict[str, Any]:
        """Get message statistics.

        Returns:
            Dictionary with counts by status and other statistics
        """
        with self._lock:
            stats = {
                "total": len(self.messages),
                "by_status": {},
                "by_provider": {},
            }

            by_status: dict[str, int] = {}
            by_provider: dict[str, int] = {}

            for msg_status in MessageStatus:
                count = sum(1 for msg in self.messages.values() if msg.status == msg_status)
                by_status[msg_status.value] = count

            providers = set(msg.provider for msg in self.messages.values())
            for provider in providers:
                count = sum(1 for msg in self.messages.values() if msg.provider == provider)
                by_provider[provider] = count

            stats["by_status"] = by_status
            stats["by_provider"] = by_provider

            if self.messages:
                messages_list = list(self.messages.values())
                oldest = min(msg.created_at for msg in messages_list)
                newest = max(msg.created_at for msg in messages_list)
                stats["oldest_message"] = oldest.isoformat()
                stats["newest_message"] = newest.isoformat()

            return stats

    def is_duplicate(
        self, content_hash: str, target: str, within_seconds: float = 60.0
    ) -> bool:
        """Check if a message with the same content hash was recently sent to the same target.

        Args:
            content_hash: Content hash to check
            target: Target identifier
            within_seconds: Time window to check (default: 60 seconds)

        Returns:
            True if duplicate found, False otherwise
        """
        cutoff_time = datetime.now() - timedelta(seconds=within_seconds)

        with self._lock:
            for msg in self.messages.values():
                if (
                    msg.content_hash == content_hash
                    and msg.target == target
                    and msg.created_at > cutoff_time
                    and msg.status != MessageStatus.FAILED
                ):
                    logger.debug(
                        f"Duplicate detected: hash={content_hash}, target={target}, "
                        f"original_id={msg.message_id}"
                    )
                    return True

        return False

    def _calculate_hash(self, content: Any) -> str:
        """Calculate SHA256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hex-encoded SHA256 hash
        """
        if isinstance(content, str):
            data = content.encode("utf-8")
        elif isinstance(content, bytes):
            data = content
        else:
            data = json.dumps(content, sort_keys=True, default=str).encode("utf-8")

        return hashlib.sha256(data).hexdigest()

    def _evict_oldest(self) -> None:
        """Evict oldest message when max history is exceeded.

        Must be called with lock held.
        """
        if not self.messages:
            return

        oldest_id = min(self.messages.keys(), key=lambda k: self.messages[k].created_at)
        self.messages.pop(oldest_id)

        if self.db_path:
            self._delete_from_db(oldest_id)

        logger.debug(f"Evicted oldest message {oldest_id} due to max_history limit")

    def _save_to_db(self, message: TrackedMessage) -> None:
        """Save message to database.

        Must be called with lock held.
        """
        if not self.db_path:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO messages
                    (message_id, provider, target, content_hash, status, created_at,
                     updated_at, sent_at, delivered_at, error, retry_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.message_id,
                        message.provider,
                        message.target,
                        message.content_hash,
                        message.status.value,
                        message.created_at.isoformat(),
                        message.updated_at.isoformat(),
                        message.sent_at.isoformat() if message.sent_at else None,
                        message.delivered_at.isoformat() if message.delivered_at else None,
                        message.error,
                        message.retry_count,
                        json.dumps(message.metadata),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save message to database: {e}", exc_info=True)

    def _update_db(self, message: TrackedMessage) -> None:
        """Update message in database.

        Must be called with lock held.
        """
        # Same as save for SQLite UPSERT behavior
        self._save_to_db(message)

    def _delete_from_db(self, message_id: str) -> None:
        """Delete message from database.

        Must be called with lock held.
        """
        if not self.db_path:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM messages WHERE message_id = ?", (message_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to delete message from database: {e}", exc_info=True)

    def load_from_db(self, limit: int | None = None) -> int:
        """Load messages from database into memory.

        Args:
            limit: Maximum number of messages to load (None for all)

        Returns:
            Number of messages loaded
        """
        if not self.db_path:
            logger.warning("Database not configured for loading")
            return 0

        loaded = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM messages ORDER BY created_at DESC"
                if limit:
                    query += f" LIMIT {limit}"

                cursor = conn.execute(query)
                for row in cursor.fetchall():
                    try:
                        message = TrackedMessage(
                            message_id=row[0],
                            provider=row[1],
                            target=row[2],
                            content_hash=row[3],
                            status=MessageStatus(row[4]),
                            created_at=datetime.fromisoformat(row[5]),
                            updated_at=datetime.fromisoformat(row[6]),
                            sent_at=datetime.fromisoformat(row[7]) if row[7] else None,
                            delivered_at=datetime.fromisoformat(row[8]) if row[8] else None,
                            error=row[9],
                            retry_count=row[10],
                            metadata=json.loads(row[11]) if row[11] else {},
                        )

                        with self._lock:
                            self.messages[message.message_id] = message
                            loaded += 1

                            # Enforce max history during load
                            if len(self.messages) > self.max_history:
                                self._evict_oldest()

                    except Exception as e:
                        logger.error(f"Failed to load message from database: {e}")

            logger.info(f"Loaded {loaded} messages from database")
        except Exception as e:
            logger.error(f"Failed to load from database: {e}", exc_info=True)

        return loaded

    def export_messages(self, status: MessageStatus | None = None) -> list[dict[str, Any]]:
        """Export messages as dictionaries.

        Args:
            status: Optional status to filter by

        Returns:
            List of message dictionaries
        """
        with self._lock:
            messages = (
                [msg for msg in self.messages.values() if msg.status == status]
                if status
                else list(self.messages.values())
            )
            return [msg.to_dict() for msg in messages]

    def clear(self) -> int:
        """Clear all tracked messages from memory and database.

        Returns:
            Number of messages cleared
        """
        with self._lock:
            count = len(self.messages)
            self.messages.clear()

            if self.db_path:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("DELETE FROM messages")
                        conn.commit()
                except Exception as e:
                    logger.error(f"Failed to clear database: {e}", exc_info=True)

        logger.info(f"Cleared {count} tracked messages")
        return count
