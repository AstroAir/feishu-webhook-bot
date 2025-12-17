"""Comprehensive tests for message tracking module.

Tests cover:
- MessageStatus enum
- TrackedMessage dataclass
- MessageTracker initialization
- Message tracking operations
- Status updates
- Duplicate detection
- Statistics
- Cleanup operations
- Database persistence
"""

from __future__ import annotations

import platform
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from feishu_webhook_bot.core.message_tracker import (
    MessageStatus,
    MessageTracker,
    TrackedMessage,
)

# ==============================================================================
# MessageStatus Tests
# ==============================================================================


class TestMessageStatus:
    """Tests for MessageStatus enum."""

    def test_status_values(self):
        """Test MessageStatus enum values."""
        assert MessageStatus.PENDING.value == "pending"
        assert MessageStatus.SENT.value == "sent"
        assert MessageStatus.DELIVERED.value == "delivered"
        assert MessageStatus.READ.value == "read"
        assert MessageStatus.FAILED.value == "failed"
        assert MessageStatus.EXPIRED.value == "expired"

    def test_status_is_string_enum(self):
        """Test MessageStatus is a string enum."""
        assert isinstance(MessageStatus.PENDING, str)
        assert MessageStatus.PENDING == "pending"


# ==============================================================================
# TrackedMessage Tests
# ==============================================================================


class TestTrackedMessage:
    """Tests for TrackedMessage dataclass."""

    def test_tracked_message_creation(self):
        """Test TrackedMessage creation."""
        now = datetime.now()
        msg = TrackedMessage(
            message_id="msg123",
            provider="feishu",
            target="user456",
            content_hash="abc123",
            status=MessageStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        assert msg.message_id == "msg123"
        assert msg.provider == "feishu"
        assert msg.target == "user456"
        assert msg.content_hash == "abc123"
        assert msg.status == MessageStatus.PENDING

    def test_tracked_message_defaults(self):
        """Test TrackedMessage default values."""
        now = datetime.now()
        msg = TrackedMessage(
            message_id="msg123",
            provider="feishu",
            target="user456",
            content_hash="abc123",
            status=MessageStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        assert msg.sent_at is None
        assert msg.delivered_at is None
        assert msg.error is None
        assert msg.retry_count == 0
        assert msg.metadata == {}

    def test_tracked_message_to_dict(self):
        """Test TrackedMessage to_dict method."""
        now = datetime.now()
        msg = TrackedMessage(
            message_id="msg123",
            provider="feishu",
            target="user456",
            content_hash="abc123",
            status=MessageStatus.SENT,
            created_at=now,
            updated_at=now,
            sent_at=now,
        )

        data = msg.to_dict()

        assert data["message_id"] == "msg123"
        assert data["provider"] == "feishu"
        assert data["status"] == "sent"
        assert data["sent_at"] == now.isoformat()

    def test_tracked_message_from_dict(self):
        """Test TrackedMessage from_dict method."""
        now = datetime.now()
        data = {
            "message_id": "msg123",
            "provider": "feishu",
            "target": "user456",
            "content_hash": "abc123",
            "status": "pending",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "sent_at": None,
            "delivered_at": None,
            "error": None,
            "retry_count": 0,
            "metadata": {},
        }

        msg = TrackedMessage.from_dict(data)

        assert msg.message_id == "msg123"
        assert msg.status == MessageStatus.PENDING


# ==============================================================================
# MessageTracker Initialization Tests
# ==============================================================================


class TestMessageTrackerInitialization:
    """Tests for MessageTracker initialization."""

    def test_tracker_creation(self):
        """Test MessageTracker creation."""
        tracker = MessageTracker(cleanup_interval=0)

        assert len(tracker.messages) == 0
        assert tracker.max_history == 10000

    def test_tracker_custom_settings(self):
        """Test MessageTracker with custom settings."""
        tracker = MessageTracker(
            max_history=100,
            cleanup_interval=0,
        )

        assert tracker.max_history == 100

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Windows file locking prevents cleanup of temp db files",
    )
    def test_tracker_with_database(self):
        """Test MessageTracker with database persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "messages.db")
            tracker = MessageTracker(db_path=db_path, cleanup_interval=0)

            assert tracker.db_path == db_path
            assert Path(db_path).exists()


# ==============================================================================
# Message Tracking Tests
# ==============================================================================


class TestMessageTracking:
    """Tests for message tracking operations."""

    @pytest.fixture
    def tracker(self):
        """Create a message tracker."""
        return MessageTracker(cleanup_interval=0)

    def test_track_message(self, tracker):
        """Test tracking a new message."""
        msg = tracker.track(
            message_id="msg123",
            provider="feishu",
            target="user456",
            content="Hello World",
        )

        assert msg.message_id == "msg123"
        assert msg.provider == "feishu"
        assert msg.target == "user456"
        assert msg.status == MessageStatus.PENDING

    def test_track_message_generates_hash(self, tracker):
        """Test tracking generates content hash."""
        msg = tracker.track(
            message_id="msg123",
            provider="feishu",
            target="user456",
            content="Hello World",
        )

        assert msg.content_hash is not None
        assert len(msg.content_hash) == 64  # SHA256 hex length

    def test_track_same_content_same_hash(self, tracker):
        """Test same content produces same hash."""
        msg1 = tracker.track("msg1", "feishu", "user1", "Hello")
        msg2 = tracker.track("msg2", "feishu", "user2", "Hello")

        assert msg1.content_hash == msg2.content_hash

    def test_track_different_content_different_hash(self, tracker):
        """Test different content produces different hash."""
        msg1 = tracker.track("msg1", "feishu", "user1", "Hello")
        msg2 = tracker.track("msg2", "feishu", "user2", "World")

        assert msg1.content_hash != msg2.content_hash

    def test_get_message(self, tracker):
        """Test getting a tracked message."""
        tracker.track("msg123", "feishu", "user456", "Hello")

        msg = tracker.get_message("msg123")

        assert msg is not None
        assert msg.message_id == "msg123"

    def test_get_message_not_found(self, tracker):
        """Test getting nonexistent message."""
        msg = tracker.get_message("nonexistent")
        assert msg is None


# ==============================================================================
# Status Update Tests
# ==============================================================================


class TestStatusUpdates:
    """Tests for status update operations."""

    @pytest.fixture
    def tracker(self):
        """Create a message tracker with a tracked message."""
        tracker = MessageTracker(cleanup_interval=0)
        tracker.track("msg123", "feishu", "user456", "Hello")
        return tracker

    def test_update_status(self, tracker):
        """Test updating message status."""
        result = tracker.update_status("msg123", MessageStatus.SENT)

        assert result is True
        msg = tracker.get_message("msg123")
        assert msg.status == MessageStatus.SENT

    def test_update_status_sets_sent_at(self, tracker):
        """Test updating to SENT sets sent_at timestamp."""
        tracker.update_status("msg123", MessageStatus.SENT)

        msg = tracker.get_message("msg123")
        assert msg.sent_at is not None

    def test_update_status_sets_delivered_at(self, tracker):
        """Test updating to DELIVERED sets delivered_at timestamp."""
        tracker.update_status("msg123", MessageStatus.DELIVERED)

        msg = tracker.get_message("msg123")
        assert msg.delivered_at is not None

    def test_update_status_with_error(self, tracker):
        """Test updating status with error message."""
        tracker.update_status("msg123", MessageStatus.FAILED, error="Network error")

        msg = tracker.get_message("msg123")
        assert msg.status == MessageStatus.FAILED
        assert msg.error == "Network error"

    def test_update_status_with_retry_count(self, tracker):
        """Test updating status with retry count."""
        tracker.update_status("msg123", MessageStatus.PENDING, retry_count=3)

        msg = tracker.get_message("msg123")
        assert msg.retry_count == 3

    def test_update_status_with_metadata(self, tracker):
        """Test updating status with metadata."""
        tracker.update_status(
            "msg123",
            MessageStatus.SENT,
            metadata={"response_id": "resp123"},
        )

        msg = tracker.get_message("msg123")
        assert msg.metadata["response_id"] == "resp123"

    def test_update_status_not_found(self, tracker):
        """Test updating nonexistent message."""
        result = tracker.update_status("nonexistent", MessageStatus.SENT)
        assert result is False


# ==============================================================================
# Query Tests
# ==============================================================================


class TestMessageQueries:
    """Tests for message query operations."""

    @pytest.fixture
    def tracker(self):
        """Create a message tracker with multiple messages."""
        tracker = MessageTracker(cleanup_interval=0)

        # Track messages with different statuses
        tracker.track("msg1", "feishu", "user1", "Hello 1")
        tracker.track("msg2", "feishu", "user2", "Hello 2")
        tracker.track("msg3", "slack", "user3", "Hello 3")

        tracker.update_status("msg1", MessageStatus.SENT)
        tracker.update_status("msg2", MessageStatus.FAILED, error="Error")

        return tracker

    def test_get_pending_messages(self, tracker):
        """Test getting pending messages."""
        pending = tracker.get_pending_messages()

        assert len(pending) == 1
        assert pending[0].message_id == "msg3"

    def test_get_failed_messages(self, tracker):
        """Test getting failed messages."""
        failed = tracker.get_failed_messages()

        assert len(failed) == 1
        assert failed[0].message_id == "msg2"

    def test_get_messages_by_status(self, tracker):
        """Test getting messages by status."""
        sent = tracker.get_messages_by_status(MessageStatus.SENT)

        assert len(sent) == 1
        assert sent[0].message_id == "msg1"

    def test_get_messages_by_provider(self, tracker):
        """Test getting messages by provider."""
        feishu_msgs = tracker.get_messages_by_provider("feishu")
        slack_msgs = tracker.get_messages_by_provider("slack")

        assert len(feishu_msgs) == 2
        assert len(slack_msgs) == 1


# ==============================================================================
# Duplicate Detection Tests
# ==============================================================================


class TestDuplicateDetection:
    """Tests for duplicate detection."""

    @pytest.fixture
    def tracker(self):
        """Create a message tracker."""
        return MessageTracker(cleanup_interval=0)

    def test_is_duplicate_true(self, tracker):
        """Test duplicate detection returns True."""
        msg = tracker.track("msg1", "feishu", "user1", "Hello")

        is_dup = tracker.is_duplicate(msg.content_hash, "user1", within_seconds=60)

        assert is_dup is True

    def test_is_duplicate_false_different_target(self, tracker):
        """Test duplicate detection with different target."""
        msg = tracker.track("msg1", "feishu", "user1", "Hello")

        is_dup = tracker.is_duplicate(msg.content_hash, "user2", within_seconds=60)

        assert is_dup is False

    def test_is_duplicate_false_different_hash(self, tracker):
        """Test duplicate detection with different hash."""
        tracker.track("msg1", "feishu", "user1", "Hello")

        is_dup = tracker.is_duplicate("different_hash", "user1", within_seconds=60)

        assert is_dup is False

    def test_is_duplicate_ignores_failed(self, tracker):
        """Test duplicate detection ignores failed messages."""
        msg = tracker.track("msg1", "feishu", "user1", "Hello")
        tracker.update_status("msg1", MessageStatus.FAILED)

        is_dup = tracker.is_duplicate(msg.content_hash, "user1", within_seconds=60)

        assert is_dup is False


# ==============================================================================
# Statistics Tests
# ==============================================================================


class TestStatistics:
    """Tests for statistics operations."""

    @pytest.fixture
    def tracker(self):
        """Create a message tracker with messages."""
        tracker = MessageTracker(cleanup_interval=0)

        tracker.track("msg1", "feishu", "user1", "Hello 1")
        tracker.track("msg2", "feishu", "user2", "Hello 2")
        tracker.track("msg3", "slack", "user3", "Hello 3")

        tracker.update_status("msg1", MessageStatus.SENT)

        return tracker

    def test_get_statistics(self, tracker):
        """Test getting statistics."""
        stats = tracker.get_statistics()

        assert stats["total"] == 3
        assert "by_status" in stats
        assert "by_provider" in stats

    def test_statistics_by_status(self, tracker):
        """Test statistics by status."""
        stats = tracker.get_statistics()

        assert stats["by_status"]["sent"] == 1
        assert stats["by_status"]["pending"] == 2

    def test_statistics_by_provider(self, tracker):
        """Test statistics by provider."""
        stats = tracker.get_statistics()

        assert stats["by_provider"]["feishu"] == 2
        assert stats["by_provider"]["slack"] == 1


# ==============================================================================
# Cleanup Tests
# ==============================================================================


class TestCleanup:
    """Tests for cleanup operations."""

    @pytest.fixture
    def tracker(self):
        """Create a message tracker."""
        return MessageTracker(cleanup_interval=0)

    def test_cleanup_old_messages(self, tracker):
        """Test cleaning up old messages."""
        # Track a message
        tracker.track("msg1", "feishu", "user1", "Hello")

        # Manually age the message
        tracker.messages["msg1"].created_at = datetime.now() - timedelta(hours=25)

        removed = tracker.cleanup_old_messages(max_age_seconds=86400)

        assert removed == 1
        assert len(tracker.messages) == 0

    def test_cleanup_keeps_recent_messages(self, tracker):
        """Test cleanup keeps recent messages."""
        tracker.track("msg1", "feishu", "user1", "Hello")

        removed = tracker.cleanup_old_messages(max_age_seconds=86400)

        assert removed == 0
        assert len(tracker.messages) == 1

    def test_clear_all_messages(self, tracker):
        """Test clearing all messages."""
        tracker.track("msg1", "feishu", "user1", "Hello 1")
        tracker.track("msg2", "feishu", "user2", "Hello 2")

        cleared = tracker.clear()

        assert cleared == 2
        assert len(tracker.messages) == 0


# ==============================================================================
# Max History Tests
# ==============================================================================


class TestMaxHistory:
    """Tests for max history enforcement."""

    def test_evicts_oldest_when_full(self):
        """Test oldest message is evicted when max history reached."""
        tracker = MessageTracker(max_history=3, cleanup_interval=0)

        tracker.track("msg1", "feishu", "user1", "Hello 1")
        time.sleep(0.01)
        tracker.track("msg2", "feishu", "user2", "Hello 2")
        time.sleep(0.01)
        tracker.track("msg3", "feishu", "user3", "Hello 3")
        time.sleep(0.01)
        tracker.track("msg4", "feishu", "user4", "Hello 4")

        assert len(tracker.messages) == 3
        assert tracker.get_message("msg1") is None  # Oldest evicted
        assert tracker.get_message("msg4") is not None


# ==============================================================================
# Export Tests
# ==============================================================================


class TestExport:
    """Tests for export operations."""

    @pytest.fixture
    def tracker(self):
        """Create a message tracker with messages."""
        tracker = MessageTracker(cleanup_interval=0)

        tracker.track("msg1", "feishu", "user1", "Hello 1")
        tracker.track("msg2", "feishu", "user2", "Hello 2")

        tracker.update_status("msg1", MessageStatus.SENT)

        return tracker

    def test_export_all_messages(self, tracker):
        """Test exporting all messages."""
        exported = tracker.export_messages()

        assert len(exported) == 2
        assert all(isinstance(m, dict) for m in exported)

    def test_export_by_status(self, tracker):
        """Test exporting messages by status."""
        exported = tracker.export_messages(status=MessageStatus.SENT)

        assert len(exported) == 1
        assert exported[0]["message_id"] == "msg1"


# ==============================================================================
# Database Persistence Tests
# ==============================================================================


class TestDatabasePersistence:
    """Tests for database persistence."""

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Windows file locking prevents cleanup of temp db files",
    )
    def test_save_and_load(self):
        """Test saving and loading messages from database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "messages.db")

            # Create tracker and track messages
            tracker1 = MessageTracker(db_path=db_path, cleanup_interval=0)
            tracker1.track("msg1", "feishu", "user1", "Hello")
            tracker1.update_status("msg1", MessageStatus.SENT)

            # Create new tracker and load from database
            tracker2 = MessageTracker(db_path=db_path, cleanup_interval=0)
            loaded = tracker2.load_from_db()

            assert loaded == 1
            msg = tracker2.get_message("msg1")
            assert msg is not None
            assert msg.status == MessageStatus.SENT

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Windows file locking prevents cleanup of temp db files",
    )
    def test_load_with_limit(self):
        """Test loading with limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "messages.db")

            tracker1 = MessageTracker(db_path=db_path, cleanup_interval=0)
            for i in range(10):
                tracker1.track(f"msg{i}", "feishu", f"user{i}", f"Hello {i}")

            tracker2 = MessageTracker(db_path=db_path, cleanup_interval=0)
            loaded = tracker2.load_from_db(limit=5)

            assert loaded == 5
