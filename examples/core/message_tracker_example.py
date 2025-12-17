#!/usr/bin/env python3
"""Message Tracker Example.

This example demonstrates the message tracking system:
- Message status tracking (pending, sent, delivered, read, failed, expired)
- Duplicate detection based on content hash
- Automatic cleanup of old messages
- Statistics and monitoring
- SQLite persistence (optional)
- Thread-safe operations

The message tracker provides visibility into message delivery status
and helps prevent duplicate messages.
"""

import hashlib
import json
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from feishu_webhook_bot.core import (
    LoggingConfig,
    MessageStatus,
    MessageTracker,
    TrackedMessage,
    get_logger,
    setup_logging,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


def generate_message_id() -> str:
    """Generate a unique message ID."""
    return str(uuid.uuid4())


def calculate_content_hash(content: Any) -> str:
    """Calculate SHA256 hash of content."""
    if isinstance(content, str):
        data = content.encode("utf-8")
    elif isinstance(content, bytes):
        data = content
    else:
        data = json.dumps(content, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# =============================================================================
# Demo 1: Basic Message Tracking
# =============================================================================
def demo_basic_tracking() -> None:
    """Demonstrate basic message tracking functionality."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Message Tracking")
    print("=" * 60)

    # Create in-memory tracker
    tracker = MessageTracker(max_history=1000)

    print("Created in-memory message tracker")
    print("Max history: 1000 messages")

    # Track a new message
    print("\n--- Tracking a new message ---")
    message_id = generate_message_id()
    content = "Hello, World!"
    tracked_msg = tracker.track(
        message_id=message_id,
        provider="feishu",
        target="webhook_url",
        content=content,
    )
    print(f"Tracked message ID: {tracked_msg.message_id}")

    # Get message status
    message = tracker.get_message(message_id)
    if message:
        print("\nMessage details:")
        print(f"  Status: {message.status.value}")
        print(f"  Provider: {message.provider}")
        print(f"  Target: {message.target}")
        print(f"  Content hash: {message.content_hash[:16]}...")
        print(f"  Created at: {message.created_at}")

    # Update status to sent
    print("\n--- Updating status to SENT ---")
    tracker.update_status(message_id, MessageStatus.SENT)
    message = tracker.get_message(message_id)
    if message:
        print(f"Status: {message.status.value}")
        print(f"Sent at: {message.sent_at}")

    # Update status to delivered
    print("\n--- Updating status to DELIVERED ---")
    tracker.update_status(message_id, MessageStatus.DELIVERED)
    message = tracker.get_message(message_id)
    if message:
        print(f"Status: {message.status.value}")
        print(f"Delivered at: {message.delivered_at}")


# =============================================================================
# Demo 2: Message Status Transitions
# =============================================================================
def demo_status_transitions() -> None:
    """Demonstrate message status transitions."""
    print("\n" + "=" * 60)
    print("Demo 2: Message Status Transitions")
    print("=" * 60)

    tracker = MessageTracker()

    print("Available message statuses:")
    for status in MessageStatus:
        print(f"  - {status.value}")

    # Track messages with different status flows
    print("\n--- Success flow: PENDING -> SENT -> DELIVERED -> READ ---")
    msg_id = generate_message_id()
    tracker.track(msg_id, "feishu", "target1", "Success message")

    for status in [MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.READ]:
        tracker.update_status(msg_id, status)
        msg = tracker.get_message(msg_id)
        print(f"  Status: {msg.status.value}")
        time.sleep(0.1)

    # Failure flow
    print("\n--- Failure flow: PENDING -> FAILED ---")
    msg_id = generate_message_id()
    tracker.track(msg_id, "feishu", "target2", "Failed message")
    tracker.update_status(msg_id, MessageStatus.FAILED, error="Connection timeout")
    msg = tracker.get_message(msg_id)
    print(f"  Status: {msg.status.value}")
    print(f"  Error: {msg.error}")

    # Expiration flow
    print("\n--- Expiration flow: PENDING -> EXPIRED ---")
    msg_id = generate_message_id()
    tracker.track(msg_id, "feishu", "target3", "Expired message")
    tracker.update_status(msg_id, MessageStatus.EXPIRED)
    msg = tracker.get_message(msg_id)
    print(f"  Status: {msg.status.value}")


# =============================================================================
# Demo 3: Duplicate Detection
# =============================================================================
def demo_duplicate_detection() -> None:
    """Demonstrate duplicate message detection."""
    print("\n" + "=" * 60)
    print("Demo 3: Duplicate Detection")
    print("=" * 60)

    tracker = MessageTracker()

    # Track first message
    content = "This is a unique message"
    content_hash = calculate_content_hash(content)
    print(f"Tracking message: '{content}'")
    msg_id1 = generate_message_id()
    tracker.track(msg_id1, "feishu", "target", content)
    print(f"First message ID: {msg_id1}")

    # Check for duplicate using content hash
    print("\n--- Checking for duplicate ---")
    is_dup = tracker.is_duplicate(content_hash, "target", within_seconds=60.0)
    print(f"Is duplicate: {is_dup}")

    # Track same content again with new ID
    print("\n--- Tracking same content again ---")
    msg_id2 = generate_message_id()
    tracker.track(msg_id2, "feishu", "target", content)
    print(f"Second message ID: {msg_id2}")
    print(f"Same ID: {msg_id1 == msg_id2}")

    # Different content
    print("\n--- Checking different content ---")
    different_content = "This is a different message"
    different_hash = calculate_content_hash(different_content)
    is_dup = tracker.is_duplicate(different_hash, "target", within_seconds=60.0)
    print(f"Is duplicate: {is_dup}")

    # Same content, different target
    print("\n--- Same content, different target ---")
    is_dup = tracker.is_duplicate(content_hash, "different_target", within_seconds=60.0)
    print(f"Is duplicate: {is_dup}")


# =============================================================================
# Demo 4: Retry Tracking
# =============================================================================
def demo_retry_tracking() -> None:
    """Demonstrate retry tracking functionality."""
    print("\n" + "=" * 60)
    print("Demo 4: Retry Tracking")
    print("=" * 60)

    tracker = MessageTracker()

    # Track a message
    msg_id = generate_message_id()
    tracker.track(msg_id, "feishu", "target", "Retry test message")
    print(f"Tracked message: {msg_id}")

    # Simulate retries using update_status with retry_count
    print("\n--- Simulating retries ---")
    for i in range(5):
        tracker.update_status(msg_id, MessageStatus.PENDING, retry_count=i + 1)
        msg = tracker.get_message(msg_id)
        print(f"Retry {i + 1}: count = {msg.retry_count}")

    # Get messages by retry count
    print("\n--- Messages with high retry count ---")
    messages = tracker.get_messages_by_status(MessageStatus.PENDING)
    for msg in messages:
        if msg.retry_count > 0:
            print(f"  {msg.message_id[:8]}...: {msg.retry_count} retries")


# =============================================================================
# Demo 5: Statistics and Monitoring
# =============================================================================
def demo_statistics() -> None:
    """Demonstrate statistics and monitoring."""
    print("\n" + "=" * 60)
    print("Demo 5: Statistics and Monitoring")
    print("=" * 60)

    tracker = MessageTracker()

    # Track multiple messages with different statuses
    print("Tracking messages with various statuses...")

    # Successful messages
    for i in range(5):
        msg_id = generate_message_id()
        tracker.track(msg_id, "feishu", f"target_{i}", f"Success message {i}")
        tracker.update_status(msg_id, MessageStatus.SENT)
        tracker.update_status(msg_id, MessageStatus.DELIVERED)

    # Failed messages
    for i in range(3):
        msg_id = generate_message_id()
        tracker.track(msg_id, "feishu", f"target_fail_{i}", f"Failed message {i}")
        tracker.update_status(msg_id, MessageStatus.FAILED, error="Timeout")

    # Pending messages
    for i in range(2):
        msg_id = generate_message_id()
        tracker.track(msg_id, "feishu", f"target_pending_{i}", f"Pending message {i}")

    # Get statistics
    print("\n--- Message Statistics ---")
    stats = tracker.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Get messages by status
    print("\n--- Messages by Status ---")
    for status in [MessageStatus.DELIVERED, MessageStatus.FAILED, MessageStatus.PENDING]:
        messages = tracker.get_messages_by_status(status)
        print(f"  {status.value}: {len(messages)} messages")


# =============================================================================
# Demo 6: SQLite Persistence
# =============================================================================
def demo_sqlite_persistence() -> None:
    """Demonstrate SQLite persistence."""
    print("\n" + "=" * 60)
    print("Demo 6: SQLite Persistence")
    print("=" * 60)

    # Create temporary database file
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "messages.db"
        print(f"Database path: {db_path}")

        # Create tracker with persistence
        tracker = MessageTracker(db_path=db_path)
        print("Created tracker with SQLite persistence")

        # Track some messages
        print("\n--- Tracking messages ---")
        msg_ids = []
        for i in range(5):
            msg_id = generate_message_id()
            tracker.track(msg_id, "feishu", f"target_{i}", f"Persistent message {i}")
            msg_ids.append(msg_id)
            print(f"Tracked: {msg_id[:8]}...")

        # Update some statuses
        tracker.update_status(msg_ids[0], MessageStatus.SENT)
        tracker.update_status(msg_ids[0], MessageStatus.DELIVERED)
        tracker.update_status(msg_ids[1], MessageStatus.FAILED, error="Test error")

        # Check database file exists
        print(f"\nDatabase file exists: {db_path.exists()}")
        print(f"Database size: {db_path.stat().st_size} bytes")

        # Create new tracker from same database
        print("\n--- Loading from database ---")
        tracker2 = MessageTracker(db_path=db_path)

        # Verify messages are loaded
        for msg_id in msg_ids[:2]:
            msg = tracker2.get_message(msg_id)
            if msg:
                print(f"Loaded: {msg_id[:8]}... - Status: {msg.status.value}")

        # Stop cleanup threads before exiting to release file locks (Windows)
        tracker.stop_cleanup()
        tracker2.stop_cleanup()


# =============================================================================
# Demo 7: Automatic Cleanup
# =============================================================================
def demo_automatic_cleanup() -> None:
    """Demonstrate automatic cleanup of old messages."""
    print("\n" + "=" * 60)
    print("Demo 7: Automatic Cleanup")
    print("=" * 60)

    # Create tracker with small max history
    tracker = MessageTracker(max_history=10)
    print("Created tracker with max_history=10")

    # Track more messages than max history
    print("\n--- Tracking 15 messages ---")
    for i in range(15):
        msg_id = generate_message_id()
        tracker.track(msg_id, "feishu", f"target_{i}", f"Message {i}")

    # Check current count
    stats = tracker.get_statistics()
    print(f"Total messages tracked: {stats.get('total', 0)}")

    # Manual cleanup
    print("\n--- Running manual cleanup ---")
    cleaned = tracker.cleanup_old_messages(max_age_seconds=0)  # Clean all
    print(f"Cleaned up {cleaned} messages")

    stats = tracker.get_statistics()
    print(f"Messages after cleanup: {stats.get('total', 0)}")


# =============================================================================
# Demo 8: TrackedMessage Serialization
# =============================================================================
def demo_message_serialization() -> None:
    """Demonstrate TrackedMessage serialization."""
    print("\n" + "=" * 60)
    print("Demo 8: TrackedMessage Serialization")
    print("=" * 60)

    tracker = MessageTracker()

    # Track a message
    msg_id = generate_message_id()
    tracker.track(
        message_id=msg_id,
        provider="feishu",
        target="webhook_url",
        content="Serialization test",
    )

    # Update status
    tracker.update_status(msg_id, MessageStatus.SENT)
    tracker.update_status(msg_id, MessageStatus.DELIVERED)

    # Get message
    message = tracker.get_message(msg_id)
    if message:
        # Convert to dictionary
        print("--- Message as dictionary ---")
        msg_dict = message.to_dict()
        for key, value in msg_dict.items():
            print(f"  {key}: {value}")

        # Recreate from dictionary
        print("\n--- Recreating from dictionary ---")
        recreated = TrackedMessage.from_dict(msg_dict)
        print(f"Message ID matches: {recreated.message_id == message.message_id}")
        print(f"Status matches: {recreated.status == message.status}")
        print(f"Metadata matches: {recreated.metadata == message.metadata}")


# =============================================================================
# Demo 9: Provider-Specific Tracking
# =============================================================================
def demo_provider_tracking() -> None:
    """Demonstrate provider-specific message tracking."""
    print("\n" + "=" * 60)
    print("Demo 9: Provider-Specific Tracking")
    print("=" * 60)

    tracker = MessageTracker()

    # Track messages for different providers
    providers = ["feishu", "qq", "slack", "telegram"]

    print("Tracking messages for multiple providers...")
    for provider in providers:
        for i in range(3):
            msg_id = generate_message_id()
            tracker.track(
                message_id=msg_id,
                provider=provider,
                target=f"{provider}_target_{i}",
                content=f"Message for {provider} #{i}",
            )
            # Randomly set status
            if i % 2 == 0:
                tracker.update_status(msg_id, MessageStatus.DELIVERED)
            else:
                tracker.update_status(msg_id, MessageStatus.FAILED)

    # Get statistics
    print("\n--- Overall Statistics ---")
    stats = tracker.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Get messages by provider
    print("\n--- Messages by Provider ---")
    for provider in providers:
        messages = tracker.get_messages_by_provider(provider)
        delivered = sum(1 for m in messages if m.status == MessageStatus.DELIVERED)
        failed = sum(1 for m in messages if m.status == MessageStatus.FAILED)
        print(f"  {provider}: {len(messages)} total ({delivered} delivered, {failed} failed)")


# =============================================================================
# Demo 10: Real-World Usage Pattern
# =============================================================================
def demo_real_world_pattern() -> None:
    """Demonstrate a real-world usage pattern."""
    print("\n" + "=" * 60)
    print("Demo 10: Real-World Usage Pattern")
    print("=" * 60)

    class MessageService:
        """Example service using message tracker."""

        def __init__(self, db_path: Path | None = None):
            self.tracker = MessageTracker(db_path=db_path, max_history=10000)
            self._send_count = 0

        def send_message(
            self,
            provider: str,
            target: str,
            content: str,
        ) -> tuple[str, bool]:
            """Send a message with tracking."""
            # Check for duplicate using content hash
            content_hash = calculate_content_hash(content)
            if self.tracker.is_duplicate(content_hash, target, within_seconds=60.0):
                print("  Duplicate detected, skipping")
                return "", False

            # Track the message
            msg_id = generate_message_id()
            self.tracker.track(
                message_id=msg_id,
                provider=provider,
                target=target,
                content=content,
            )

            # Simulate sending (would be actual API call)
            self._send_count += 1
            success = self._send_count % 5 != 0  # Fail every 5th message

            if success:
                self.tracker.update_status(msg_id, MessageStatus.SENT)
                self.tracker.update_status(msg_id, MessageStatus.DELIVERED)
                return msg_id, True
            else:
                self.tracker.update_status(msg_id, MessageStatus.FAILED, error="Simulated failure")
                return msg_id, False

        def retry_failed(self) -> int:
            """Retry all failed messages."""
            failed = self.tracker.get_messages_by_status(MessageStatus.FAILED)
            retried = 0

            for msg in failed:
                if msg.retry_count < 3:
                    # Update retry count using update_status
                    self.tracker.update_status(
                        msg.message_id, MessageStatus.PENDING, retry_count=msg.retry_count + 1
                    )
                    # Simulate retry success
                    self.tracker.update_status(msg.message_id, MessageStatus.DELIVERED)
                    retried += 1

            return retried

        def get_health_report(self) -> dict[str, Any]:
            """Get service health report."""
            stats = self.tracker.get_statistics()
            by_status = stats.get("by_status", {})
            total = stats.get("total", 0)
            delivered = by_status.get("delivered", 0)
            failed = by_status.get("failed", 0)
            pending = by_status.get("pending", 0)
            return {
                "total_messages": total,
                "delivered": delivered,
                "failed": failed,
                "pending": pending,
                "delivery_rate": (delivered / total * 100 if total > 0 else 0),
            }

    # Use the service
    service = MessageService()

    print("Sending messages...")
    for i in range(10):
        msg_id, success = service.send_message(
            provider="feishu",
            target="webhook_url",
            content=f"Message {i + 1}",
        )
        status = "SUCCESS" if success else "FAILED"
        print(f"  Message {i + 1}: {status}")

    # Try sending duplicate
    print("\n--- Attempting duplicate ---")
    service.send_message("feishu", "webhook_url", "Message 1")

    # Retry failed messages
    print("\n--- Retrying failed messages ---")
    retried = service.retry_failed()
    print(f"Retried {retried} messages")

    # Health report
    print("\n--- Health Report ---")
    report = service.get_health_report()
    for key, value in report.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.1f}%")
        else:
            print(f"  {key}: {value}")


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all message tracker demonstrations."""
    print("=" * 60)
    print("Message Tracker Examples")
    print("=" * 60)

    demos = [
        ("Basic Message Tracking", demo_basic_tracking),
        ("Message Status Transitions", demo_status_transitions),
        ("Duplicate Detection", demo_duplicate_detection),
        ("Retry Tracking", demo_retry_tracking),
        ("Statistics and Monitoring", demo_statistics),
        ("SQLite Persistence", demo_sqlite_persistence),
        ("Automatic Cleanup", demo_automatic_cleanup),
        ("TrackedMessage Serialization", demo_message_serialization),
        ("Provider-Specific Tracking", demo_provider_tracking),
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
