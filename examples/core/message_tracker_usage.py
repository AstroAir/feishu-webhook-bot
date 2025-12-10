"""Example usage of MessageTracker for message delivery tracking."""

from feishu_webhook_bot.core.message_tracker import MessageTracker, MessageStatus


def basic_usage_example() -> None:
    """Demonstrate basic message tracking."""
    # Create a tracker without persistence
    tracker = MessageTracker(cleanup_interval=0)

    # Track a new message
    msg = tracker.track(
        message_id="msg-001",
        provider="feishu",
        target="https://open.feishu.cn/open-apis/bot/v2/hook/...",
        content="Hello, Feishu!",
    )
    print(f"Tracked message: {msg.message_id}, Status: {msg.status.value}")

    # Update status as the message progresses
    tracker.update_status("msg-001", MessageStatus.SENT)
    msg = tracker.get_message("msg-001")
    print(f"Message sent at: {msg.sent_at}")

    # Mark as delivered
    tracker.update_status("msg-001", MessageStatus.DELIVERED)
    msg = tracker.get_message("msg-001")
    print(f"Message delivered at: {msg.delivered_at}")

    # Check pending messages
    pending = tracker.get_pending_messages()
    print(f"Pending messages: {len(pending)}")

    tracker.stop_cleanup()


def duplicate_detection_example() -> None:
    """Demonstrate duplicate message detection."""
    tracker = MessageTracker(cleanup_interval=0)

    target = "https://open.feishu.cn/open-apis/bot/v2/hook/..."
    content = "Don't send this twice!"

    # Track first message
    msg1 = tracker.track("msg-001", "feishu", target, content)
    tracker.update_status("msg-001", MessageStatus.SENT)

    # Check for duplicate within 60 seconds
    is_duplicate = tracker.is_duplicate(msg1.content_hash, target, within_seconds=60)
    print(f"Is duplicate within 60 seconds: {is_duplicate}")

    # Different content - not a duplicate
    is_duplicate2 = tracker.is_duplicate(
        tracker._calculate_hash("Different content"), target, within_seconds=60
    )
    print(f"Is different content duplicate: {is_duplicate2}")

    tracker.stop_cleanup()


def statistics_example() -> None:
    """Demonstrate getting statistics."""
    tracker = MessageTracker(cleanup_interval=0)

    # Track multiple messages in different states
    tracker.track("msg-001", "feishu", "webhook-1", "content1")
    tracker.track("msg-002", "feishu", "webhook-2", "content2")
    tracker.track("msg-003", "slack", "webhook-3", "content3")
    tracker.track("msg-004", "slack", "webhook-4", "content4")

    # Update statuses
    tracker.update_status("msg-001", MessageStatus.DELIVERED)
    tracker.update_status("msg-002", MessageStatus.SENT)
    tracker.update_status("msg-003", MessageStatus.FAILED, error="Network error")

    # Get statistics
    stats = tracker.get_statistics()
    print("Message Statistics:")
    print(f"  Total messages: {stats['total']}")
    print(f"  By status: {stats['by_status']}")
    print(f"  By provider: {stats['by_provider']}")

    tracker.stop_cleanup()


def persistence_example() -> None:
    """Demonstrate SQLite persistence."""
    db_path = "messages.db"

    # Create tracker with persistence
    tracker = MessageTracker(db_path=db_path, cleanup_interval=0)

    # Track some messages
    tracker.track("msg-001", "feishu", "webhook-1", "Persistent message 1")
    tracker.track("msg-002", "feishu", "webhook-2", "Persistent message 2")
    tracker.update_status("msg-001", MessageStatus.DELIVERED)

    print(f"Saved {len(tracker.messages)} messages to {db_path}")
    tracker.stop_cleanup()

    # Later, load from database in a new tracker instance
    tracker2 = MessageTracker(db_path=db_path, cleanup_interval=0)
    loaded = tracker2.load_from_db(limit=100)
    print(f"Loaded {loaded} messages from database")

    # Check loaded messages
    msg = tracker2.get_message("msg-001")
    if msg:
        print(f"Loaded message status: {msg.status.value}")

    tracker2.stop_cleanup()


def error_handling_example() -> None:
    """Demonstrate error tracking and retry logic."""
    tracker = MessageTracker(cleanup_interval=0)

    msg_id = "msg-001"
    tracker.track(msg_id, "feishu", "webhook-1", "Will retry")

    # First attempt fails
    tracker.update_status(
        msg_id, MessageStatus.FAILED, error="Connection timeout", retry_count=1
    )
    msg = tracker.get_message(msg_id)
    print(f"First attempt failed: {msg.error}, Retry count: {msg.retry_count}")

    # Second attempt also fails
    tracker.update_status(msg_id, MessageStatus.FAILED, error="Still timeout", retry_count=2)
    msg = tracker.get_message(msg_id)
    print(f"Second attempt failed: {msg.error}, Retry count: {msg.retry_count}")

    # Third attempt succeeds
    tracker.update_status(msg_id, MessageStatus.SENT, retry_count=3)
    msg = tracker.get_message(msg_id)
    print(f"Third attempt succeeded, Retry count: {msg.retry_count}")

    # Get all failed messages
    failed = tracker.get_failed_messages()
    print(f"Total failed messages (status FAILED): {len(failed)}")

    tracker.stop_cleanup()


def message_lifecycle_example() -> None:
    """Demonstrate complete message lifecycle."""
    tracker = MessageTracker(cleanup_interval=0)

    msg_id = "msg-001"
    provider = "feishu"
    target = "webhook-1"
    content = {"text": "Hello World", "card": "..."}

    # Step 1: Create message
    tracked = tracker.track(msg_id, provider, target, content)
    print(f"Step 1 - Created: {tracked.status.value}")

    # Step 2: Send to webhook
    tracker.update_status(msg_id, MessageStatus.SENT)
    print(f"Step 2 - Sent: {tracker.get_message(msg_id).status.value}")

    # Step 3: Feishu acknowledges delivery
    tracker.update_status(msg_id, MessageStatus.DELIVERED)
    print(f"Step 3 - Delivered: {tracker.get_message(msg_id).status.value}")

    # Step 4: User reads message
    tracker.update_status(msg_id, MessageStatus.READ)
    print(f"Step 4 - Read: {tracker.get_message(msg_id).status.value}")

    # Get final message state
    final_msg = tracker.get_message(msg_id)
    print(f"\nFinal state: {final_msg.to_dict()}")

    tracker.stop_cleanup()


if __name__ == "__main__":
    print("=== Basic Usage ===")
    basic_usage_example()

    print("\n=== Duplicate Detection ===")
    duplicate_detection_example()

    print("\n=== Statistics ===")
    statistics_example()

    print("\n=== Error Handling ===")
    error_handling_example()

    print("\n=== Message Lifecycle ===")
    message_lifecycle_example()

    print("\n=== Persistence ===")
    persistence_example()

    print("\nAll examples completed!")
