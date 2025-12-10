"""Message parsers for multi-platform event parsing.

This module provides platform-specific parsers that convert raw webhook event
payloads into unified IncomingMessage format.

Key parsers:
- FeishuMessageParser: Parse Feishu event callbacks
- QQMessageParser: Parse OneBot11 events from QQ/Napcat

Each parser implements the MessageParser protocol from message_handler.py.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from .logger import get_logger
from .message_handler import IncomingMessage, MessageParser

logger = get_logger("message_parsers")


class FeishuMessageParser:
    """Parse Feishu event callbacks into IncomingMessage.

    Handles Feishu Open Platform webhook event structure, extracting message
    content, sender information, mentions, and thread context.

    Feishu message event structure:
    ```json
    {
        "schema": "2.0",
        "header": {
            "event_id": "xxx",
            "event_type": "im.message.receive_v1",
            "create_time": "1234567890000"
        },
        "event": {
            "sender": {
                "sender_id": {"open_id": "ou_xxx", "user_id": "xxx"},
                "sender_type": "user"
            },
            "message": {
                "message_id": "om_xxx",
                "root_id": "om_yyy",
                "parent_id": "om_zzz",
                "chat_id": "oc_xxx",
                "chat_type": "group",
                "message_type": "text",
                "content": "{\\"text\\":\\"Hello @bot\\"}",
                "mentions": [{"key": "@_user_1", "id": {"open_id": "ou_bot"}}]
            }
        }
    }
    ```

    Example:
        ```python
        parser = FeishuMessageParser(bot_open_id="ou_bot_xxx")

        if parser.can_parse(payload):
            message = parser.parse(payload)
            if message:
                print(f"Message from {message.sender_name}: {message.content}")
        ```
    """

    # Event types that represent messages
    MESSAGE_EVENT_TYPES = {
        "im.message.receive_v1",
        "im.message.message_read_v1",  # Read receipt (not a chat message)
    }

    def __init__(self, bot_open_id: str | None = None):
        """Initialize Feishu message parser.

        Args:
            bot_open_id: Bot's open_id for @mention detection.
                Can be obtained from Feishu Open Platform dashboard.
        """
        self.bot_open_id = bot_open_id

    def can_parse(self, payload: dict[str, Any]) -> bool:
        """Check if this parser can handle the payload.

        Identifies Feishu message events by checking header.event_type.

        Args:
            payload: Event payload from Feishu webhook.

        Returns:
            True if this is a parseable Feishu message event.
        """
        # Check for v2.0 schema
        header = payload.get("header", {})
        event_type = header.get("event_type", "")

        if event_type == "im.message.receive_v1":
            return True

        # Check for legacy v1.0 schema
        if payload.get("type") == "message":
            return True

        return False

    def parse(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse Feishu event payload into IncomingMessage.

        Extracts message content, sender info, mentions, and thread context
        from Feishu event structure.

        Args:
            payload: Feishu event payload.

        Returns:
            IncomingMessage if parsing succeeds, None if not a message event.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If payload structure is invalid.
        """
        if not self.can_parse(payload):
            return None

        try:
            # Determine schema version
            if "header" in payload:
                return self._parse_v2(payload)
            else:
                return self._parse_v1(payload)
        except Exception as e:
            logger.error("Failed to parse Feishu message: %s", e, exc_info=True)
            return None

    def _parse_v2(self, payload: dict[str, Any]) -> IncomingMessage:
        """Parse v2.0 schema Feishu event.

        Args:
            payload: Feishu v2.0 event payload.

        Returns:
            Parsed IncomingMessage.
        """
        header = payload["header"]
        event = payload.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})

        # Extract IDs
        message_id = message.get("message_id", "")
        chat_id = message.get("chat_id", "")
        chat_type = message.get("chat_type", "p2p")  # p2p, group, topic

        # Map Feishu chat_type to our unified type
        unified_chat_type = self._map_chat_type(chat_type)

        # Extract sender info
        sender_id_obj = sender.get("sender_id", {})
        sender_id = sender_id_obj.get("open_id") or sender_id_obj.get("user_id", "")
        sender_name = self._get_sender_name(event)

        # Parse message content
        content = self._extract_content(message)

        # Extract mentions
        mentions = self._extract_mentions(message)
        is_at_bot = self._is_at_bot(message)

        # Thread info
        root_id = message.get("root_id")
        parent_id = message.get("parent_id")
        thread_id = root_id if root_id else None
        reply_to = parent_id if parent_id and parent_id != root_id else None

        # Timestamp
        create_time = header.get("create_time", "")
        timestamp = self._parse_timestamp(create_time)

        return IncomingMessage(
            id=message_id,
            platform="feishu",
            chat_type=unified_chat_type,
            chat_id=chat_id if unified_chat_type != "private" else "",
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            mentions=mentions,
            is_at_bot=is_at_bot,
            reply_to=reply_to,
            thread_id=thread_id,
            timestamp=timestamp,
            raw_content=message.get("content"),
            metadata={
                "event_id": header.get("event_id"),
                "event_type": header.get("event_type"),
                "message_type": message.get("message_type"),
                "sender_type": sender.get("sender_type"),
            },
        )

    def _parse_v1(self, payload: dict[str, Any]) -> IncomingMessage:
        """Parse legacy v1.0 schema Feishu event.

        Args:
            payload: Feishu v1.0 event payload.

        Returns:
            Parsed IncomingMessage.
        """
        event = payload.get("event", payload)

        message_id = event.get("message_id", event.get("msg_id", ""))
        chat_id = event.get("chat_id", event.get("open_chat_id", ""))
        chat_type = event.get("chat_type", "private")

        unified_chat_type = self._map_chat_type(chat_type)

        # Sender info
        sender_id = event.get("open_id", event.get("user_id", ""))
        sender_name = event.get("user_name", sender_id)

        # Content
        content = event.get("text", event.get("text_without_at_bot", ""))

        # Mentions
        mentions = []
        is_at_bot = event.get("is_mention", False)

        timestamp = datetime.now()
        if "create_time" in event:
            timestamp = self._parse_timestamp(str(event["create_time"]))

        return IncomingMessage(
            id=message_id,
            platform="feishu",
            chat_type=unified_chat_type,
            chat_id=chat_id if unified_chat_type != "private" else "",
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            mentions=mentions,
            is_at_bot=is_at_bot,
            reply_to=event.get("parent_id"),
            thread_id=event.get("root_id"),
            timestamp=timestamp,
            raw_content=event.get("content"),
            metadata={
                "msg_type": event.get("msg_type"),
            },
        )

    def _map_chat_type(self, feishu_type: str) -> str:
        """Map Feishu chat_type to unified type.

        Args:
            feishu_type: Feishu-specific chat type.

        Returns:
            One of "private", "group", "channel".
        """
        mapping = {
            "p2p": "private",
            "private": "private",
            "group": "group",
            "topic": "channel",
        }
        return mapping.get(feishu_type.lower(), "group")

    def _get_sender_name(self, event: dict[str, Any]) -> str:
        """Extract sender display name from event.

        Args:
            event: Feishu event object.

        Returns:
            Sender's display name or ID as fallback.
        """
        sender = event.get("sender", {})

        # Try to get name from sender object
        sender_id = sender.get("sender_id", {})
        name = sender_id.get("name") or sender_id.get("open_id") or ""

        # Fallback to event-level user info
        if not name:
            name = event.get("user_name", event.get("open_id", "unknown"))

        return name

    def _extract_content(self, message: dict[str, Any]) -> str:
        """Extract text content from message.

        Handles different message types (text, post, etc.) and parses
        JSON content format.

        Args:
            message: Feishu message object.

        Returns:
            Plain text content.
        """
        content_str = message.get("content", "")
        message_type = message.get("message_type", "text")

        if not content_str:
            return ""

        try:
            content_obj = json.loads(content_str)
        except (json.JSONDecodeError, TypeError):
            # Not JSON, return as-is
            return str(content_str)

        if message_type == "text":
            return content_obj.get("text", "")

        elif message_type == "post":
            # Rich text: extract all text elements
            return self._extract_post_text(content_obj)

        elif message_type == "interactive":
            # Card message: try to get title or first text
            return content_obj.get("header", {}).get("title", {}).get("content", "")

        else:
            # Other types (image, file, etc.): return type indicator
            return f"[{message_type}]"

    def _extract_post_text(self, content: dict[str, Any]) -> str:
        """Extract text from rich text (post) content.

        Args:
            content: Parsed post content object.

        Returns:
            Concatenated text from all text elements.
        """
        texts = []

        # Post has localized content
        for lang, post_content in content.items():
            if isinstance(post_content, dict):
                # Process paragraphs
                for paragraph in post_content.get("content", []):
                    if isinstance(paragraph, list):
                        for element in paragraph:
                            if isinstance(element, dict):
                                if element.get("tag") == "text":
                                    texts.append(element.get("text", ""))
                                elif element.get("tag") == "at":
                                    texts.append(f"@{element.get('user_name', '')}")

        return "".join(texts)

    def _extract_mentions(self, message: dict[str, Any]) -> list[str]:
        """Extract @mentioned user IDs from message.

        Args:
            message: Feishu message object.

        Returns:
            List of mentioned user open_ids.
        """
        mentions = []
        mention_list = message.get("mentions", [])

        for mention in mention_list:
            mention_id = mention.get("id", {})
            open_id = mention_id.get("open_id")
            if open_id:
                mentions.append(open_id)

        return mentions

    def _is_at_bot(self, message: dict[str, Any]) -> bool:
        """Check if bot is @mentioned.

        Args:
            message: Feishu message object.

        Returns:
            True if bot is mentioned.
        """
        if not self.bot_open_id:
            return False

        mentions = self._extract_mentions(message)
        return self.bot_open_id in mentions

    def _parse_timestamp(self, time_str: str) -> datetime:
        """Parse Feishu timestamp string.

        Args:
            time_str: Timestamp string (milliseconds or ISO format).

        Returns:
            Parsed datetime object.
        """
        if not time_str:
            return datetime.now()

        try:
            # Try milliseconds format first
            timestamp_ms = int(time_str)
            return datetime.fromtimestamp(timestamp_ms / 1000)
        except ValueError:
            pass

        try:
            # Try ISO format
            return datetime.fromisoformat(time_str)
        except ValueError:
            pass

        return datetime.now()


class QQMessageParser:
    """Parse OneBot11 events from QQ/Napcat into IncomingMessage.

    Handles OneBot11 protocol message events, extracting text content,
    CQ codes, @mentions, and metadata.

    OneBot11 message event structure:
    ```json
    {
        "post_type": "message",
        "message_type": "group",
        "time": 1234567890,
        "self_id": 123456789,
        "sub_type": "normal",
        "user_id": 987654321,
        "group_id": 123456,
        "message_id": 12345,
        "message": [
            {"type": "text", "data": {"text": "Hello "}},
            {"type": "at", "data": {"qq": "123456789"}},
            {"type": "text", "data": {"text": " world"}}
        ],
        "raw_message": "Hello [CQ:at,qq=123456789] world",
        "sender": {
            "user_id": 987654321,
            "nickname": "Alice",
            "card": "Alice in Wonderland"
        }
    }
    ```

    Example:
        ```python
        parser = QQMessageParser(bot_qq="123456789")

        if parser.can_parse(payload):
            message = parser.parse(payload)
            if message:
                print(f"Message from {message.sender_name}: {message.content}")
        ```
    """

    def __init__(self, bot_qq: str | None = None):
        """Initialize QQ message parser.

        Args:
            bot_qq: Bot's QQ number for @mention detection.
        """
        self.bot_qq = bot_qq

    def can_parse(self, payload: dict[str, Any]) -> bool:
        """Check if this parser can handle the payload.

        Identifies OneBot11 message events by post_type.

        Args:
            payload: Event payload from Napcat/OneBot11.

        Returns:
            True if this is a parseable QQ message event.
        """
        post_type = payload.get("post_type")
        return post_type == "message"

    def parse(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse OneBot11 event payload into IncomingMessage.

        Args:
            payload: OneBot11 event payload.

        Returns:
            IncomingMessage if parsing succeeds, None otherwise.
        """
        if not self.can_parse(payload):
            return None

        try:
            return self._parse_message(payload)
        except Exception as e:
            logger.error("Failed to parse QQ message: %s", e, exc_info=True)
            return None

    def _parse_message(self, payload: dict[str, Any]) -> IncomingMessage:
        """Parse OneBot11 message event.

        Args:
            payload: OneBot11 message event payload.

        Returns:
            Parsed IncomingMessage.
        """
        message_type = payload.get("message_type", "private")
        unified_chat_type = "group" if message_type == "group" else "private"

        # Extract IDs
        message_id = str(payload.get("message_id", ""))
        user_id = str(payload.get("user_id", ""))
        group_id = str(payload.get("group_id", "")) if message_type == "group" else ""

        # Sender info
        sender = payload.get("sender", {})
        sender_name = sender.get("card") or sender.get("nickname") or user_id

        # Parse message content
        message_data = payload.get("message", [])
        content = self._extract_text(message_data)
        mentions = self._extract_mentions(message_data)
        is_at_bot = self._is_at_bot(message_data)

        # Timestamp
        time_val = payload.get("time")
        timestamp = datetime.fromtimestamp(time_val) if time_val else datetime.now()

        return IncomingMessage(
            id=message_id,
            platform="qq",
            chat_type=unified_chat_type,
            chat_id=group_id,
            sender_id=user_id,
            sender_name=sender_name,
            content=content,
            mentions=mentions,
            is_at_bot=is_at_bot,
            reply_to=None,
            thread_id=None,
            timestamp=timestamp,
            raw_content=message_data,
            metadata={
                "sub_type": payload.get("sub_type"),
                "self_id": payload.get("self_id"),
                "raw_message": payload.get("raw_message", ""),
                "sender": sender,
            },
        )

    def _extract_text(self, message: list[dict[str, Any]] | str) -> str:
        """Extract plain text from message segments.

        Args:
            message: Message segments or raw CQ string.

        Returns:
            Plain text content.
        """
        if isinstance(message, str):
            # Raw CQ string, remove CQ codes
            return re.sub(r"\[CQ:[^\]]+\]", "", message).strip()

        if not isinstance(message, list):
            return str(message).strip()

        text_parts = []
        for segment in message:
            if isinstance(segment, dict) and segment.get("type") == "text":
                text = segment.get("data", {}).get("text", "")
                if text:
                    text_parts.append(text)

        return "".join(text_parts).strip()

    def _extract_mentions(self, message: list[dict[str, Any]] | str) -> list[str]:
        """Extract @mentioned QQ numbers from message.

        Args:
            message: Message segments or raw CQ string.

        Returns:
            List of mentioned QQ numbers.
        """
        mentions = []

        if isinstance(message, str):
            # Parse CQ codes: [CQ:at,qq=123456]
            for match in re.finditer(r"\[CQ:at,qq=(\w+)\]", message):
                qq = match.group(1)
                if qq and qq not in mentions:
                    mentions.append(qq)
            return mentions

        if not isinstance(message, list):
            return mentions

        for segment in message:
            if isinstance(segment, dict) and segment.get("type") == "at":
                qq = segment.get("data", {}).get("qq")
                if qq:
                    qq_str = str(qq)
                    if qq_str not in mentions:
                        mentions.append(qq_str)

        return mentions

    def _is_at_bot(self, message: list[dict[str, Any]] | str) -> bool:
        """Check if bot is @mentioned.

        Args:
            message: Message segments or raw CQ string.

        Returns:
            True if bot is mentioned.
        """
        if not self.bot_qq:
            return False

        mentions = self._extract_mentions(message)
        return self.bot_qq in mentions or "all" in mentions


# Factory functions for convenient parser creation

def create_feishu_parser(bot_open_id: str | None = None) -> FeishuMessageParser:
    """Create a configured Feishu message parser.

    Args:
        bot_open_id: Bot's open_id for @mention detection.

    Returns:
        Configured FeishuMessageParser instance.
    """
    return FeishuMessageParser(bot_open_id=bot_open_id)


def create_qq_parser(bot_qq: str | None = None) -> QQMessageParser:
    """Create a configured QQ message parser.

    Args:
        bot_qq: Bot's QQ number for @mention detection.

    Returns:
        Configured QQMessageParser instance.
    """
    return QQMessageParser(bot_qq=bot_qq)


# Type assertion for protocol compliance
_: type[MessageParser] = FeishuMessageParser
_: type[MessageParser] = QQMessageParser
