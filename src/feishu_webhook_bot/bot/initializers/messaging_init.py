"""Messaging component initialization mixin for FeishuBot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core import get_logger
from ...core.message_bridge import MessageBridgeEngine
from ...core.message_queue import MessageQueue
from ...core.message_tracker import MessageTracker

if TYPE_CHECKING:
    from ..base import BotBase

logger = get_logger("bot.init.messaging")


class MessagingInitializerMixin:
    """Mixin for messaging component initialization."""

    def _init_message_tracker(self: BotBase) -> None:
        """Initialize message tracker for delivery tracking and persistence."""
        tracking_config = getattr(self.config, "message_tracking", None)

        if not tracking_config:
            logger.info("Message tracking disabled (no config)")
            return

        enabled = getattr(tracking_config, "enabled", False)
        if not enabled:
            logger.info("Message tracking disabled")
            return

        try:
            max_history = getattr(tracking_config, "max_history", 10000)
            cleanup_interval = getattr(tracking_config, "cleanup_interval", 3600.0)
            db_path = getattr(tracking_config, "db_path", None)

            self.message_tracker = MessageTracker(
                max_history=max_history,
                cleanup_interval=cleanup_interval,
                db_path=db_path,
            )
            logger.info(
                "Message tracker initialized (db_path=%s, max_history=%d)",
                db_path or "in-memory",
                max_history,
            )
        except Exception as exc:
            logger.error("Failed to initialize message tracker: %s", exc, exc_info=True)
            # Non-fatal - continue without tracking

    def _init_message_queue(self: BotBase) -> None:
        """Initialize message queue for reliable async delivery."""
        queue_config = getattr(self.config, "message_queue", None)

        if not queue_config:
            logger.info("Message queue disabled (no config)")
            return

        enabled = getattr(queue_config, "enabled", False)
        if not enabled:
            logger.info("Message queue disabled")
            return

        if not self.providers:
            logger.warning("No providers available; message queue disabled")
            return

        try:
            max_batch_size = getattr(queue_config, "max_batch_size", 10)
            retry_delay = getattr(queue_config, "retry_delay", 5.0)
            max_retries = getattr(queue_config, "max_retries", 3)

            self.message_queue = MessageQueue(
                providers=self.providers,
                max_batch_size=max_batch_size,
                retry_delay=retry_delay,
                max_retries=max_retries,
            )
            logger.info(
                "Message queue initialized (batch_size=%d, max_retries=%d)",
                max_batch_size,
                max_retries,
            )
        except Exception as exc:
            logger.error("Failed to initialize message queue: %s", exc, exc_info=True)
            # Non-fatal - continue without queue

    def _init_message_bridge(self: BotBase) -> None:
        """Initialize message bridge for cross-platform message forwarding."""
        bridge_config = getattr(self.config, "message_bridge", None)
        if bridge_config is None:
            logger.info("Message bridge disabled (no config)")
            return

        if not bridge_config.enabled:
            logger.info("Message bridge disabled")
            return

        try:
            self.message_bridge = MessageBridgeEngine(
                config=bridge_config,
                providers=self.providers,
            )
            logger.info(
                "Message bridge initialized with %d rules",
                len(bridge_config.rules),
            )
        except Exception as e:
            logger.error("Failed to initialize message bridge: %s", e, exc_info=True)
