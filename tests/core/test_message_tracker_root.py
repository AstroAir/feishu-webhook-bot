"""Tests for message tracking and delivery confirmation system."""

from __future__ import annotations

import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from feishu_webhook_bot.core.message_tracker import (
    MessageStatus,
    MessageTracker,
    TrackedMessage,
)


class TestMessageStatus:
    """Tests for MessageStatus enumeration."""

    def test_status_values(self) -> None:
        """Test all status enum values."""
        assert MessageStatus.PENDING.value == "pending"
        assert MessageStatus.SENT.value == "sent"
        assert MessageStatus.DELIVERED.value == "delivered"
        assert MessageStatus.READ.value == "read"
        assert MessageStatus.FAILED.value == "failed"
        assert MessageStatus.EXPIRED.value == "expired"

    def test_status_creation_from_value(self) -> None:
        """Test creating status from string value."""
        status = MessageStatus("pending")
        assert status == MessageStatus.PENDING


class TestTrackedMessage:
    """Tests for TrackedMessage dataclass."""

    def test_message_creation(self) -> None:
        """Test creating a tracked message."""
        now = datetime.now()
        msg = TrackedMessage(
            message_id="msg-1",
            provider="feishu",
            target="webhook-1",
            content_hash="abc123",
            status=MessageStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        assert msg.message_id == "msg-1"
        assert msg.provider == "feishu"
        assert msg.target == "webhook-1"
        assert msg.status == MessageStatus.PENDING
        assert msg.retry_count == 0
        assert msg.metadata == {}

    def test_message_to_dict(self) -> None:
        """Test converting message to dictionary."""
        now = datetime.now()
        msg = TrackedMessage(
            message_id="msg-1",
            provider="feishu",
            target="webhook-1",
            content_hash="abc123",
            status=MessageStatus.SENT,
            created_at=now,
            updated_at=now,
            sent_at=now,
            error=None,
            retry_count=1,
            metadata={"custom": "value"},
        )

        msg_dict = msg.to_dict()
        assert msg_dict["message_id"] == "msg-1"
        assert msg_dict["status"] == "sent"
        assert msg_dict["retry_count"] == 1
        assert msg_dict["metadata"] == {"custom": "value"}

    def test_message_from_dict(self) -> None:
        """Test creating message from dictionary."""
        now = datetime.now()
        data = {
            "message_id": "msg-1",
            "provider": "feishu",
            "target": "webhook-1",
            "content_hash": "abc123",
            "status": "delivered",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "sent_at": now.isoformat(),
            "delivered_at": now.isoformat(),
            "error": None,
            "retry_count": 2,
            "metadata": {"key": "value"},
        }

        msg = TrackedMessage.from_dict(data)
        assert msg.message_id == "msg-1"
        assert msg.status == MessageStatus.DELIVERED
        assert msg.retry_count == 2
        assert msg.metadata == {"key": "value"}


class TestMessageTracker:
    """Tests for MessageTracker class."""

    @pytest.fixture
    def tracker(self) -> MessageTracker:
        """Create a tracker for testing."""
        return MessageTracker(max_history=1000, cleanup_interval=0)

    def test_tracker_creation(self) -> None:
        """Test creating a message tracker."""
        tracker = MessageTracker()
        assert tracker.max_history == 10000
        assert len(tracker.messages) == 0
        tracker.stop_cleanup()

    def test_track_message(self, tracker: MessageTracker) -> None:
        """Test tracking a new message."""
        msg = tracker.track("msg-1", "feishu", "webhook-1", "Hello World")

        assert msg.message_id == "msg-1"
        assert msg.provider == "feishu"
        assert msg.status == MessageStatus.PENDING
        assert len(tracker.messages) == 1

    def test_get_message(self, tracker: MessageTracker) -> None:
        """Test retrieving a tracked message."""
        tracker.track("msg-1", "feishu", "webhook-1", "content")
        msg = tracker.get_message("msg-1")

        assert msg is not None
        assert msg.message_id == "msg-1"

    def test_get_message_not_found(self, tracker: MessageTracker) -> None:
        """Test getting non-existent message."""
        msg = tracker.get_message("msg-999")
        assert msg is None

    def test_update_status(self, tracker: MessageTracker) -> None:
        """Test updating message status."""
        tracker.track("msg-1", "feishu", "webhook-1", "content")

        success = tracker.update_status("msg-1", MessageStatus.SENT)
        assert success is True

        msg = tracker.get_message("msg-1")
        assert msg.status == MessageStatus.SENT
        assert msg.sent_at is not None

    def test_update_status_with_error(self, tracker: MessageTracker) -> None:
        """Test updating status with error message."""
        tracker.track("msg-1", "feishu", "webhook-1", "content")
        success = tracker.update_status("msg-1", MessageStatus.FAILED, error="Network timeout")

        assert success is True
        msg = tracker.get_message("msg-1")
        assert msg.status == MessageStatus.FAILED
        assert msg.error == "Network timeout"

    def test_update_status_not_found(self, tracker: MessageTracker) -> None:
        """Test updating status of non-existent message."""
        success = tracker.update_status("msg-999", MessageStatus.SENT)
        assert success is False

    def test_get_pending_messages(self, tracker: MessageTracker) -> None:
        """Test retrieving pending messages."""
        tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "feishu", "webhook-2", "content2")
        tracker.track("msg-3", "feishu", "webhook-3", "content3")

        tracker.update_status("msg-2", MessageStatus.SENT)

        pending = tracker.get_pending_messages()
        assert len(pending) == 2
        assert all(msg.status == MessageStatus.PENDING for msg in pending)

    def test_get_failed_messages(self, tracker: MessageTracker) -> None:
        """Test retrieving failed messages."""
        tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "feishu", "webhook-2", "content2")

        tracker.update_status("msg-1", MessageStatus.FAILED, error="Error 1")
        tracker.update_status("msg-2", MessageStatus.FAILED, error="Error 2")

        failed = tracker.get_failed_messages()
        assert len(failed) == 2
        assert all(msg.status == MessageStatus.FAILED for msg in failed)

    def test_get_messages_by_status(self, tracker: MessageTracker) -> None:
        """Test retrieving messages by status."""
        tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "feishu", "webhook-2", "content2")
        tracker.track("msg-3", "feishu", "webhook-3", "content3")

        tracker.update_status("msg-1", MessageStatus.DELIVERED)
        tracker.update_status("msg-2", MessageStatus.DELIVERED)

        delivered = tracker.get_messages_by_status(MessageStatus.DELIVERED)
        assert len(delivered) == 2
        assert all(msg.status == MessageStatus.DELIVERED for msg in delivered)

    def test_get_messages_by_provider(self, tracker: MessageTracker) -> None:
        """Test retrieving messages by provider."""
        tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "slack", "webhook-2", "content2")
        tracker.track("msg-3", "feishu", "webhook-3", "content3")

        feishu_msgs = tracker.get_messages_by_provider("feishu")
        assert len(feishu_msgs) == 2
        assert all(msg.provider == "feishu" for msg in feishu_msgs)

        slack_msgs = tracker.get_messages_by_provider("slack")
        assert len(slack_msgs) == 1
        assert slack_msgs[0].provider == "slack"

    def test_cleanup_old_messages(self, tracker: MessageTracker) -> None:
        """Test cleanup of old messages."""
        # Track messages
        msg1 = tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "feishu", "webhook-2", "content2")

        # Manually set one message to be old
        old_time = datetime.now() - timedelta(seconds=100000)
        msg1.created_at = old_time

        # Cleanup messages older than 1 hour
        removed = tracker.cleanup_old_messages(max_age_seconds=3600)

        assert removed == 1
        assert len(tracker.messages) == 1
        assert tracker.get_message("msg-2") is not None
        assert tracker.get_message("msg-1") is None

    def test_get_statistics(self, tracker: MessageTracker) -> None:
        """Test getting message statistics."""
        tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "feishu", "webhook-2", "content2")
        tracker.track("msg-3", "slack", "webhook-3", "content3")

        tracker.update_status("msg-1", MessageStatus.SENT)
        tracker.update_status("msg-2", MessageStatus.DELIVERED)

        stats = tracker.get_statistics()

        assert stats["total"] == 3
        assert stats["by_status"]["pending"] == 1
        assert stats["by_status"]["sent"] == 1
        assert stats["by_status"]["delivered"] == 1
        assert stats["by_provider"]["feishu"] == 2
        assert stats["by_provider"]["slack"] == 1
        assert "oldest_message" in stats
        assert "newest_message" in stats

    def test_is_duplicate(self, tracker: MessageTracker) -> None:
        """Test duplicate detection."""
        content = "Hello World"
        target = "webhook-1"

        msg1 = tracker.track("msg-1", "feishu", target, content)
        tracker.update_status("msg-1", MessageStatus.SENT)

        # Should detect duplicate within time window
        is_dup = tracker.is_duplicate(msg1.content_hash, target, within_seconds=60)
        assert is_dup is True

        # Should not detect duplicate after time window
        is_dup_expired = tracker.is_duplicate(msg1.content_hash, target, within_seconds=1)
        time.sleep(1.1)
        is_dup_expired = tracker.is_duplicate(msg1.content_hash, target, within_seconds=1)
        assert is_dup_expired is False

    def test_is_duplicate_different_target(self, tracker: MessageTracker) -> None:
        """Test duplicate detection with different target."""
        content = "Hello World"

        msg1 = tracker.track("msg-1", "feishu", "webhook-1", content)
        tracker.update_status("msg-1", MessageStatus.SENT)

        # Should not detect duplicate for different target
        is_dup = tracker.is_duplicate(msg1.content_hash, "webhook-2", within_seconds=60)
        assert is_dup is False

    def test_is_duplicate_failed_message(self, tracker: MessageTracker) -> None:
        """Test duplicate detection with failed messages."""
        content = "Hello World"
        target = "webhook-1"

        msg1 = tracker.track("msg-1", "feishu", target, content)
        tracker.update_status("msg-1", MessageStatus.FAILED, error="Network error")

        # Should not detect duplicate for failed messages
        is_dup = tracker.is_duplicate(msg1.content_hash, target, within_seconds=60)
        assert is_dup is False

    def test_export_messages(self, tracker: MessageTracker) -> None:
        """Test exporting messages."""
        tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "feishu", "webhook-2", "content2")

        tracker.update_status("msg-1", MessageStatus.DELIVERED)

        # Export all messages
        all_msgs = tracker.export_messages()
        assert len(all_msgs) == 2

        # Export only delivered
        delivered_msgs = tracker.export_messages(status=MessageStatus.DELIVERED)
        assert len(delivered_msgs) == 1
        assert delivered_msgs[0]["status"] == "delivered"

    def test_clear_all_messages(self, tracker: MessageTracker) -> None:
        """Test clearing all messages."""
        tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "feishu", "webhook-2", "content2")

        assert len(tracker.messages) == 2

        cleared = tracker.clear()
        assert cleared == 2
        assert len(tracker.messages) == 0

    def test_max_history_enforcement(self) -> None:
        """Test that max_history limit is enforced."""
        tracker = MessageTracker(max_history=5, cleanup_interval=0)

        for i in range(10):
            tracker.track(f"msg-{i}", "feishu", "webhook-1", f"content-{i}")

        assert len(tracker.messages) <= 5
        tracker.stop_cleanup()

    def test_thread_safety(self) -> None:
        """Test thread-safe operations."""
        tracker = MessageTracker(max_history=10000, cleanup_interval=0)
        errors = []

        def add_messages(start: int, count: int) -> None:
            try:
                for i in range(start, start + count):
                    tracker.track(f"msg-{i}", "feishu", "webhook-1", f"content-{i}")
                    if i % 3 == 0:
                        tracker.update_status(f"msg-{i}", MessageStatus.SENT)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_messages, args=(i * 100, 100)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(tracker.messages) == 500
        tracker.stop_cleanup()

    def test_hash_calculation(self, tracker: MessageTracker) -> None:
        """Test content hash calculation."""
        # String content
        hash1 = tracker._calculate_hash("Hello World")
        hash2 = tracker._calculate_hash("Hello World")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

        # Different content
        hash3 = tracker._calculate_hash("Different")
        assert hash3 != hash1

        # Dict content
        dict_hash1 = tracker._calculate_hash({"key": "value"})
        dict_hash2 = tracker._calculate_hash({"key": "value"})
        assert dict_hash1 == dict_hash2


class TestMessageTrackerWithDatabase:
    """Tests for MessageTracker with SQLite persistence."""

    @pytest.fixture
    def temp_db_path(self) -> str:
        """Create temporary database path."""
        tmpdir = tempfile.mkdtemp()
        db_path = str(Path(tmpdir) / "test_messages.db")
        yield db_path

        # Cleanup
        try:
            Path(db_path).unlink(missing_ok=True)
            Path(tmpdir).rmdir()
        except Exception:
            pass  # Ignore cleanup errors on Windows

    def test_database_initialization(self, temp_db_path: str) -> None:
        """Test database initialization."""
        tracker = MessageTracker(db_path=temp_db_path, cleanup_interval=0)

        db_file = Path(temp_db_path)
        assert db_file.exists()

        # Verify tables exist
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
            )
            assert cursor.fetchone() is not None

        tracker.stop_cleanup()

    def test_save_and_load_from_db(self, temp_db_path: str) -> None:
        """Test saving and loading messages from database."""
        tracker = MessageTracker(db_path=temp_db_path, cleanup_interval=0)

        # Track messages
        tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "feishu", "webhook-2", "content2")

        tracker.update_status("msg-1", MessageStatus.DELIVERED)

        # Create new tracker and load from database
        tracker2 = MessageTracker(db_path=temp_db_path, cleanup_interval=0)
        loaded = tracker2.load_from_db()

        assert loaded == 2
        assert tracker2.get_message("msg-1").status == MessageStatus.DELIVERED
        assert tracker2.get_message("msg-2").status == MessageStatus.PENDING

        tracker.stop_cleanup()
        tracker2.stop_cleanup()

    def test_cleanup_removes_from_db(self, temp_db_path: str) -> None:
        """Test that cleanup removes messages from database."""
        tracker = MessageTracker(db_path=temp_db_path, cleanup_interval=0)

        msg = tracker.track("msg-1", "feishu", "webhook-1", "content1")
        old_time = datetime.now() - timedelta(seconds=100000)
        msg.created_at = old_time

        tracker.cleanup_old_messages(max_age_seconds=3600)

        # Verify message is gone from database
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
            assert count == 0

        tracker.stop_cleanup()

    def test_clear_removes_from_db(self, temp_db_path: str) -> None:
        """Test that clear removes messages from database."""
        tracker = MessageTracker(db_path=temp_db_path, cleanup_interval=0)

        tracker.track("msg-1", "feishu", "webhook-1", "content1")
        tracker.track("msg-2", "feishu", "webhook-2", "content2")

        tracker.clear()

        # Verify database is empty
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
            assert count == 0

        tracker.stop_cleanup()


class TestMessageTrackerCleanupThread:
    """Tests for background cleanup thread."""

    def test_cleanup_thread_runs(self) -> None:
        """Test that cleanup thread runs automatically."""
        tracker = MessageTracker(cleanup_interval=0.5)

        # Track a message and make it old
        msg = tracker.track("msg-1", "feishu", "webhook-1", "content1")
        old_time = datetime.now() - timedelta(seconds=100000)
        msg.created_at = old_time

        # Wait for cleanup thread to run
        time.sleep(1.5)

        # Message should be cleaned up
        assert len(tracker.messages) == 0

        tracker.stop_cleanup()

    def test_stop_cleanup_thread(self) -> None:
        """Test stopping cleanup thread."""
        tracker = MessageTracker(cleanup_interval=1.0)
        tracker.stop_cleanup()

        # Thread should be stopped
        assert tracker._cleanup_thread is None or not tracker._cleanup_thread.is_alive()


class TestTrackedMessageIntegration:
    """Integration tests for tracked messages."""

    def test_message_lifecycle(self) -> None:
        """Test complete message lifecycle."""
        tracker = MessageTracker(cleanup_interval=0)

        # Create message
        msg = tracker.track("msg-1", "feishu", "webhook-1", "Hello World")
        assert msg.status == MessageStatus.PENDING

        # Send message
        tracker.update_status("msg-1", MessageStatus.SENT)
        msg = tracker.get_message("msg-1")
        assert msg.status == MessageStatus.SENT
        assert msg.sent_at is not None

        # Message delivered
        tracker.update_status("msg-1", MessageStatus.DELIVERED)
        msg = tracker.get_message("msg-1")
        assert msg.status == MessageStatus.DELIVERED
        assert msg.delivered_at is not None

        # Message read
        tracker.update_status("msg-1", MessageStatus.READ)
        msg = tracker.get_message("msg-1")
        assert msg.status == MessageStatus.READ

        tracker.stop_cleanup()

    def test_message_failure_recovery(self) -> None:
        """Test message with failure and retry."""
        tracker = MessageTracker(cleanup_interval=0)

        msg = tracker.track("msg-1", "feishu", "webhook-1", "Hello")

        # First attempt fails
        tracker.update_status("msg-1", MessageStatus.FAILED, error="Timeout", retry_count=1)
        msg = tracker.get_message("msg-1")
        assert msg.retry_count == 1
        assert msg.error == "Timeout"

        # Retry succeeds
        tracker.update_status("msg-1", MessageStatus.SENT, retry_count=2)
        msg = tracker.get_message("msg-1")
        assert msg.retry_count == 2
        assert msg.error == "Timeout"  # Error not cleared

        tracker.stop_cleanup()
