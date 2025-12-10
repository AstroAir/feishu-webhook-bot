"""QQ event handler for OneBot11 protocol event parsing and processing.

This module handles incoming OneBot11 events from QQ (via Napcat or other implementations),
converting them into unified IncomingMessage format for consistent message handling
across the bot framework.

Key features:
- Parse OneBot11 message events (private and group)
- Extract CQ code segments (text, @mentions, images)
- Detect @bot mentions for bot-specific message routing
- Support for message metadata and raw content preservation
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from ..core.logger import get_logger
from ..core.message_handler import IncomingMessage

logger = get_logger(__name__)


@dataclass
class QQEventMeta:
    """Metadata for QQ events.

    Attributes:
        post_type: Event type (message, notice, request, meta_event).
        message_type: Message type for message events (private, group).
        notice_type: Notice type for notice events.
        request_type: Request type for request events.
        sub_type: Sub-type of event (e.g., friend, normal, anonymous).
        self_id: Bot's QQ number.
        time: Event timestamp (Unix timestamp).
    """

    post_type: str
    message_type: str | None = None
    notice_type: str | None = None
    request_type: str | None = None
    sub_type: str | None = None
    self_id: int | None = None
    time: int | None = None


class QQEventHandler:
    """Handle incoming OneBot11 events from QQ.

    Converts OneBot11 event payloads to unified IncomingMessage format
    and provides utilities for message parsing, CQ code extraction,
    and @mention detection.

    Supports:
    - Private and group message events
    - CQ code parsing (text, @mentions, images)
    - Bot @mention detection for command routing
    - Metadata preservation for advanced use cases

    Example:
        ```python
        handler = QQEventHandler(bot_qq="123456789")

        # Handle incoming event
        message = await handler.handle_event(event_payload)
        if message:
            # Process as chat message
            response = await ai_chat(message)
            await provider.send_reply(message, response)
        ```
    """

    # Supported event types
    MESSAGE_EVENTS = ["message_private", "message_group"]
    NOTICE_EVENTS = ["notice_group_increase", "notice_group_decrease", "notice_friend_add"]

    def __init__(
        self,
        bot_qq: str | None = None,
    ):
        """Initialize QQ event handler.

        Args:
            bot_qq: Bot's QQ number for @mention detection and filtering.
                If provided, enables detection of @bot mentions.
        """
        self.bot_qq = bot_qq

    def parse_event_meta(self, payload: dict[str, Any]) -> QQEventMeta:
        """Parse event metadata from payload.

        Extracts basic event type information from OneBot11 payload.

        Args:
            payload: OneBot11 event payload.

        Returns:
            QQEventMeta with parsed metadata.
        """
        return QQEventMeta(
            post_type=payload.get("post_type", ""),
            message_type=payload.get("message_type"),
            notice_type=payload.get("notice_type"),
            request_type=payload.get("request_type"),
            sub_type=payload.get("sub_type"),
            self_id=payload.get("self_id"),
            time=payload.get("time"),
        )

    async def handle_event(
        self,
        payload: dict[str, Any],
    ) -> IncomingMessage | None:
        """Handle incoming OneBot11 event.

        Routes different event types appropriately. Only message events
        are converted to IncomingMessage; other event types return None.

        Args:
            payload: OneBot11 event payload from Napcat or other OneBot11 implementation.

        Returns:
            IncomingMessage if this is a message event, None for other event types.
        """
        meta = self.parse_event_meta(payload)

        # Handle different event types
        if meta.post_type == "message":
            return self._parse_message_event(payload, meta)
        elif meta.post_type == "notice":
            logger.debug("Received notice event: %s", meta.notice_type)
            return None
        elif meta.post_type == "request":
            logger.debug("Received request event: %s", meta.request_type)
            return None
        elif meta.post_type == "meta_event":
            # Heartbeat, lifecycle events - silently ignored
            return None

        logger.warning("Unknown post_type: %s", meta.post_type)
        return None

    def _parse_message_event(
        self,
        payload: dict[str, Any],
        meta: QQEventMeta,
    ) -> IncomingMessage:
        """Parse message event into IncomingMessage.

        Extracts message content, sender info, mentions, and metadata from
        a OneBot11 message event payload.

        Args:
            payload: OneBot11 message event payload.
            meta: Pre-parsed event metadata.

        Returns:
            IncomingMessage with unified format.
        """
        # Extract basic info
        message_id = str(payload.get("message_id", ""))
        user_id = str(payload.get("user_id", ""))
        group_id = str(payload.get("group_id", "")) if meta.message_type == "group" else ""

        # Get sender info
        sender = payload.get("sender", {})
        sender_name = sender.get("card") or sender.get("nickname") or user_id

        # Parse message content
        message_data = payload.get("message", [])
        text_content = self._extract_text(message_data)
        mentions = self._extract_mentions(message_data)
        is_at_bot = self._is_at_bot(message_data)

        # Determine chat type
        chat_type: Literal["private", "group"] = (
            "group" if meta.message_type == "group" else "private"
        )

        # Build timestamp
        timestamp = datetime.fromtimestamp(meta.time) if meta.time else datetime.now()

        return IncomingMessage(
            id=message_id,
            platform="qq",
            chat_type=chat_type,
            chat_id=group_id,
            sender_id=user_id,
            sender_name=sender_name,
            content=text_content,
            mentions=mentions,
            is_at_bot=is_at_bot,
            reply_to=None,  # OneBot11 doesn't provide reply info directly
            thread_id=None,
            timestamp=timestamp,
            raw_content=message_data,
            metadata={
                "sub_type": meta.sub_type,
                "self_id": meta.self_id,
                "raw_message": payload.get("raw_message", ""),
                "sender": sender,
            },
        )

    def _extract_text(self, message: list[dict[str, Any]] | str) -> str:
        """Extract plain text content from message segments.

        Handles both structured message array format and raw CQ string format.
        For CQ strings, removes CQ codes while preserving text content.

        Args:
            message: Message segments array or raw CQ string.

        Returns:
            Extracted text content, empty string if no text found.
        """
        if isinstance(message, str):
            # Raw CQ string, extract text portions by removing CQ codes
            text = re.sub(r"\[CQ:[^\]]+\]", "", message)
            return text.strip()

        if not isinstance(message, list):
            return str(message).strip()

        text_parts = []
        for segment in message:
            if not isinstance(segment, dict):
                continue
            if segment.get("type") == "text":
                text_content = segment.get("data", {}).get("text", "")
                if text_content:
                    text_parts.append(text_content)

        return "".join(text_parts).strip()

    def _extract_mentions(self, message: list[dict[str, Any]] | str) -> list[str]:
        """Extract @mentioned QQ numbers from message.

        Supports both structured message format and raw CQ string format.
        Parses [CQ:at,qq=123456] patterns in CQ strings. Handles both numeric
        QQ numbers and special "all" for group @all mentions.

        Args:
            message: Message segments or raw CQ string.

        Returns:
            List of mentioned QQ numbers (as strings) or ["all"] for group mentions.
        """
        mentions = []

        if isinstance(message, str):
            # Parse CQ codes: [CQ:at,qq=123456] or [CQ:at,qq=all]
            # Handle both numeric QQ and "all" keyword
            for match in re.finditer(r"\[CQ:at,qq=(\w+)\]", message):
                qq_value = match.group(1)
                if qq_value and qq_value not in mentions:
                    mentions.append(qq_value)
            return mentions

        if not isinstance(message, list):
            return mentions

        for segment in message:
            if not isinstance(segment, dict):
                continue
            if segment.get("type") == "at":
                qq = segment.get("data", {}).get("qq")
                if qq:
                    qq_str = str(qq)
                    if qq_str not in mentions:
                        mentions.append(qq_str)

        return mentions

    def _is_at_bot(self, message: list[dict[str, Any]] | str) -> bool:
        """Check if the bot is @mentioned in the message.

        Detects specific @bot or @all (group mentions) patterns.

        Args:
            message: Message segments or raw CQ string.

        Returns:
            True if bot is @mentioned, False otherwise.
        """
        if not self.bot_qq:
            return False

        mentions = self._extract_mentions(message)

        # Check for specific @bot or @all mentions
        return self.bot_qq in mentions or "all" in mentions

    def _extract_images(
        self, message: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Extract image information from message.

        Args:
            message: Message segments (must be array format).

        Returns:
            List of image info dicts with file and url keys.
        """
        images = []

        if not isinstance(message, list):
            return images

        for segment in message:
            if not isinstance(segment, dict):
                continue
            if segment.get("type") == "image":
                data = segment.get("data", {})
                image_info = {
                    "file": data.get("file", ""),
                    "url": data.get("url", ""),
                }
                if image_info["file"] or image_info["url"]:
                    images.append(image_info)

        return images

    def strip_at_prefix(self, content: str) -> str:
        """Remove @bot prefix from message content.

        Removes @bot mention at the beginning of message for cleaner
        command processing. Also handles @all mentions.

        Args:
            content: Message content that may start with @bot.

        Returns:
            Content with @bot/@all prefix removed and trimmed.
        """
        if not self.bot_qq:
            return content

        # Remove @bot and @all from beginning
        pattern = rf"^\s*@{self.bot_qq}\s*|^\s*@all\s*"
        return re.sub(pattern, "", content).strip()


def create_qq_event_handler(
    bot_qq: str | None = None,
) -> QQEventHandler:
    """Factory function to create configured QQ event handler.

    Args:
        bot_qq: Bot's QQ number for @mention detection.

    Returns:
        Configured QQEventHandler instance ready for event processing.
    """
    return QQEventHandler(bot_qq=bot_qq)
