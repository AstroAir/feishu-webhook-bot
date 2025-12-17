"""QQ event handler for OneBot11 protocol event parsing and processing.

This module handles incoming OneBot11 events from QQ (via Napcat or other implementations),
converting them into unified IncomingMessage format for consistent message handling
across the bot framework.

Key features:
- Parse OneBot11 message events (private and group)
- Parse notice events (group member changes, friend add, poke, etc.)
- Parse request events (friend/group add requests)
- Extract CQ code segments (text, @mentions, images, reply, face, etc.)
- Detect @bot mentions for bot-specific message routing
- Support for message metadata and raw content preservation

Supported OneBot11 Events:
- message: private, group
- notice: group_increase, group_decrease, group_ban, friend_add, poke, etc.
- request: friend, group
- meta_event: lifecycle, heartbeat
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from ..core.logger import get_logger
from ..core.message_handler import IncomingMessage

logger = get_logger(__name__)


class QQEventType(str, Enum):
    """OneBot11 event types."""

    # Message events
    MESSAGE_PRIVATE = "message_private"
    MESSAGE_GROUP = "message_group"

    # Notice events
    NOTICE_GROUP_INCREASE = "notice_group_increase"
    NOTICE_GROUP_DECREASE = "notice_group_decrease"
    NOTICE_GROUP_BAN = "notice_group_ban"
    NOTICE_GROUP_ADMIN = "notice_group_admin"
    NOTICE_GROUP_UPLOAD = "notice_group_upload"
    NOTICE_GROUP_RECALL = "notice_group_recall"
    NOTICE_FRIEND_ADD = "notice_friend_add"
    NOTICE_FRIEND_RECALL = "notice_friend_recall"
    NOTICE_POKE = "notice_poke"
    NOTICE_LUCKY_KING = "notice_lucky_king"
    NOTICE_HONOR = "notice_honor"

    # Request events
    REQUEST_FRIEND = "request_friend"
    REQUEST_GROUP = "request_group"

    # Meta events
    META_LIFECYCLE = "meta_event_lifecycle"
    META_HEARTBEAT = "meta_event_heartbeat"

    # Unknown
    UNKNOWN = "unknown"


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
        event_type: Computed full event type enum.
    """

    post_type: str
    message_type: str | None = None
    notice_type: str | None = None
    request_type: str | None = None
    sub_type: str | None = None
    self_id: int | None = None
    time: int | None = None

    @property
    def event_type(self) -> QQEventType:
        """Get the full event type."""
        if self.post_type == "message":
            if self.message_type == "private":
                return QQEventType.MESSAGE_PRIVATE
            elif self.message_type == "group":
                return QQEventType.MESSAGE_GROUP
        elif self.post_type == "notice":
            type_map = {
                "group_increase": QQEventType.NOTICE_GROUP_INCREASE,
                "group_decrease": QQEventType.NOTICE_GROUP_DECREASE,
                "group_ban": QQEventType.NOTICE_GROUP_BAN,
                "group_admin": QQEventType.NOTICE_GROUP_ADMIN,
                "group_upload": QQEventType.NOTICE_GROUP_UPLOAD,
                "group_recall": QQEventType.NOTICE_GROUP_RECALL,
                "friend_add": QQEventType.NOTICE_FRIEND_ADD,
                "friend_recall": QQEventType.NOTICE_FRIEND_RECALL,
                "notify": QQEventType.NOTICE_POKE,  # poke is under notify
            }
            return type_map.get(self.notice_type or "", QQEventType.UNKNOWN)
        elif self.post_type == "request":
            if self.request_type == "friend":
                return QQEventType.REQUEST_FRIEND
            elif self.request_type == "group":
                return QQEventType.REQUEST_GROUP
        elif self.post_type == "meta_event":
            if self.sub_type == "lifecycle":
                return QQEventType.META_LIFECYCLE
            elif self.sub_type == "heartbeat":
                return QQEventType.META_HEARTBEAT
        return QQEventType.UNKNOWN


@dataclass
class QQNoticeEvent:
    """Parsed notice event data."""

    event_type: QQEventType
    group_id: int | None = None
    user_id: int | None = None
    operator_id: int | None = None
    sub_type: str | None = None
    message_id: int | None = None
    duration: int | None = None  # For ban events
    file: dict[str, Any] | None = None  # For upload events
    target_id: int | None = None  # For poke events
    time: datetime = field(default_factory=datetime.now)
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class QQRequestEvent:
    """Parsed request event data."""

    event_type: QQEventType
    user_id: int
    flag: str  # Used to approve/reject
    comment: str = ""
    group_id: int | None = None
    sub_type: str | None = None  # add, invite for group requests
    time: datetime = field(default_factory=datetime.now)
    raw_data: dict[str, Any] = field(default_factory=dict)


# Type aliases for event callbacks
NoticeCallback = Any  # Callable[[QQNoticeEvent], Awaitable[None]]
RequestCallback = Any  # Callable[[QQRequestEvent], Awaitable[None]]


class QQEventHandler:
    """Handle incoming OneBot11 events from QQ.

    Converts OneBot11 event payloads to unified IncomingMessage format
    and provides utilities for message parsing, CQ code extraction,
    and @mention detection.

    Supports:
    - Private and group message events
    - Notice events (group changes, poke, recall, etc.)
    - Request events (friend/group add requests)
    - CQ code parsing (text, @mentions, images, reply, face)
    - Bot @mention detection for command routing
    - Metadata preservation for advanced use cases
    - Event callback registration

    Example:
        ```python
        handler = QQEventHandler(bot_qq="123456789")

        # Register notice callback
        @handler.on_notice(QQEventType.NOTICE_POKE)
        async def handle_poke(event: QQNoticeEvent):
            print(f"Got poked by {event.user_id}")

        # Handle incoming event
        message, notice, request = await handler.handle_event(event_payload)
        if message:
            response = await ai_chat(message)
            await provider.send_reply(message, response)
        ```
    """

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
        self._notice_callbacks: dict[QQEventType, list[NoticeCallback]] = {}
        self._request_callbacks: dict[QQEventType, list[RequestCallback]] = {}

    def on_notice(
        self,
        event_type: QQEventType,
    ) -> Any:
        """Decorator to register a notice event callback.

        Args:
            event_type: The notice event type to handle

        Returns:
            Decorator function

        Example:
            ```python
            @handler.on_notice(QQEventType.NOTICE_GROUP_INCREASE)
            async def on_member_join(event: QQNoticeEvent):
                print(f"User {event.user_id} joined group {event.group_id}")
            ```
        """

        def decorator(func: NoticeCallback) -> NoticeCallback:
            if event_type not in self._notice_callbacks:
                self._notice_callbacks[event_type] = []
            self._notice_callbacks[event_type].append(func)
            return func

        return decorator

    def on_request(
        self,
        event_type: QQEventType,
    ) -> Any:
        """Decorator to register a request event callback.

        Args:
            event_type: The request event type to handle

        Returns:
            Decorator function

        Example:
            ```python
            @handler.on_request(QQEventType.REQUEST_FRIEND)
            async def on_friend_request(event: QQRequestEvent):
                print(f"Friend request from {event.user_id}: {event.comment}")
            ```
        """

        def decorator(func: RequestCallback) -> RequestCallback:
            if event_type not in self._request_callbacks:
                self._request_callbacks[event_type] = []
            self._request_callbacks[event_type].append(func)
            return func

        return decorator

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
    ) -> tuple[IncomingMessage | None, QQNoticeEvent | None, QQRequestEvent | None]:
        """Handle incoming OneBot11 event.

        Routes different event types appropriately and triggers registered callbacks.

        Args:
            payload: OneBot11 event payload from Napcat or other OneBot11 implementation.

        Returns:
            Tuple of (IncomingMessage, QQNoticeEvent, QQRequestEvent).
            Only one will be non-None based on event type.
        """
        meta = self.parse_event_meta(payload)

        # Handle different event types
        if meta.post_type == "message":
            message = self._parse_message_event(payload, meta)
            return (message, None, None)

        elif meta.post_type == "notice":
            notice = self._parse_notice_event(payload, meta)
            if notice:
                await self._trigger_notice_callbacks(notice)
            return (None, notice, None)

        elif meta.post_type == "request":
            request = self._parse_request_event(payload, meta)
            if request:
                await self._trigger_request_callbacks(request)
            return (None, None, request)

        elif meta.post_type == "meta_event":
            # Heartbeat, lifecycle events - silently ignored
            return (None, None, None)

        logger.warning("Unknown post_type: %s", meta.post_type)
        return (None, None, None)

    async def handle_message_event(
        self,
        payload: dict[str, Any],
    ) -> IncomingMessage | None:
        """Handle only message events (backward compatible).

        Args:
            payload: OneBot11 event payload.

        Returns:
            IncomingMessage if this is a message event, None otherwise.
        """
        message, _, _ = await self.handle_event(payload)
        return message

    def _parse_notice_event(
        self,
        payload: dict[str, Any],
        meta: QQEventMeta,
    ) -> QQNoticeEvent | None:
        """Parse notice event into QQNoticeEvent.

        Args:
            payload: OneBot11 notice event payload.
            meta: Pre-parsed event metadata.

        Returns:
            QQNoticeEvent with parsed data.
        """
        event_type = meta.event_type
        timestamp = datetime.fromtimestamp(meta.time) if meta.time else datetime.now()

        notice = QQNoticeEvent(
            event_type=event_type,
            group_id=payload.get("group_id"),
            user_id=payload.get("user_id"),
            operator_id=payload.get("operator_id"),
            sub_type=meta.sub_type,
            time=timestamp,
            raw_data=payload,
        )

        # Parse event-specific fields
        if event_type == QQEventType.NOTICE_GROUP_BAN:
            notice.duration = payload.get("duration", 0)

        elif event_type == QQEventType.NOTICE_GROUP_UPLOAD:
            notice.file = payload.get("file", {})

        elif event_type in (
            QQEventType.NOTICE_GROUP_RECALL,
            QQEventType.NOTICE_FRIEND_RECALL,
        ):
            notice.message_id = payload.get("message_id")

        elif event_type == QQEventType.NOTICE_POKE:
            notice.target_id = payload.get("target_id")

        logger.debug(
            "Parsed notice event: type=%s, group=%s, user=%s",
            event_type.value,
            notice.group_id,
            notice.user_id,
        )
        return notice

    def _parse_request_event(
        self,
        payload: dict[str, Any],
        meta: QQEventMeta,
    ) -> QQRequestEvent | None:
        """Parse request event into QQRequestEvent.

        Args:
            payload: OneBot11 request event payload.
            meta: Pre-parsed event metadata.

        Returns:
            QQRequestEvent with parsed data.
        """
        event_type = meta.event_type
        timestamp = datetime.fromtimestamp(meta.time) if meta.time else datetime.now()

        request = QQRequestEvent(
            event_type=event_type,
            user_id=payload.get("user_id", 0),
            flag=payload.get("flag", ""),
            comment=payload.get("comment", ""),
            group_id=payload.get("group_id"),
            sub_type=meta.sub_type,
            time=timestamp,
            raw_data=payload,
        )

        logger.debug(
            "Parsed request event: type=%s, user=%s, flag=%s",
            event_type.value,
            request.user_id,
            request.flag[:20] if request.flag else "",
        )
        return request

    async def _trigger_notice_callbacks(self, event: QQNoticeEvent) -> None:
        """Trigger registered notice callbacks.

        Args:
            event: Parsed notice event
        """
        callbacks = self._notice_callbacks.get(event.event_type, [])
        for callback in callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(
                    "Error in notice callback for %s: %s",
                    event.event_type.value,
                    e,
                    exc_info=True,
                )

    async def _trigger_request_callbacks(self, event: QQRequestEvent) -> None:
        """Trigger registered request callbacks.

        Args:
            event: Parsed request event
        """
        callbacks = self._request_callbacks.get(event.event_type, [])
        for callback in callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(
                    "Error in request callback for %s: %s",
                    event.event_type.value,
                    e,
                    exc_info=True,
                )

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

        # Extract reply info
        reply_to = self._extract_reply(message_data)

        # Extract additional content types
        images = self._extract_images(message_data)
        faces = self._extract_faces(message_data)

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
            reply_to=reply_to,
            thread_id=None,
            timestamp=timestamp,
            raw_content=message_data,
            metadata={
                "sub_type": meta.sub_type,
                "self_id": meta.self_id,
                "raw_message": payload.get("raw_message", ""),
                "sender": sender,
                "images": images,
                "faces": faces,
                "message_seq": payload.get("message_seq"),
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

    def _extract_images(self, message: list[dict[str, Any]] | str) -> list[dict[str, str]]:
        """Extract image information from message.

        Args:
            message: Message segments (array or CQ string format).

        Returns:
            List of image info dicts with file and url keys.
        """
        images = []

        if isinstance(message, str):
            # Parse CQ codes: [CQ:image,file=xxx,url=xxx]
            for match in re.finditer(r"\[CQ:image,([^\]]+)\]", message):
                params = self._parse_cq_params(match.group(1))
                if params.get("file") or params.get("url"):
                    images.append(
                        {
                            "file": params.get("file", ""),
                            "url": params.get("url", ""),
                        }
                    )
            return images

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

    def _extract_reply(self, message: list[dict[str, Any]] | str) -> str | None:
        """Extract reply message ID from message.

        Args:
            message: Message segments or raw CQ string.

        Returns:
            Reply message ID or None if not a reply.
        """
        if isinstance(message, str):
            # Parse CQ code: [CQ:reply,id=xxx]
            match = re.search(r"\[CQ:reply,id=(\d+)\]", message)
            if match:
                return match.group(1)
            return None

        if not isinstance(message, list):
            return None

        for segment in message:
            if not isinstance(segment, dict):
                continue
            if segment.get("type") == "reply":
                reply_id = segment.get("data", {}).get("id")
                if reply_id:
                    return str(reply_id)

        return None

    def _extract_faces(self, message: list[dict[str, Any]] | str) -> list[int]:
        """Extract QQ face/emoji IDs from message.

        Args:
            message: Message segments or raw CQ string.

        Returns:
            List of face IDs.
        """
        faces = []

        if isinstance(message, str):
            # Parse CQ codes: [CQ:face,id=xxx]
            for match in re.finditer(r"\[CQ:face,id=(\d+)\]", message):
                with contextlib.suppress(ValueError):
                    faces.append(int(match.group(1)))
            return faces

        if not isinstance(message, list):
            return faces

        for segment in message:
            if not isinstance(segment, dict):
                continue
            if segment.get("type") == "face":
                face_id = segment.get("data", {}).get("id")
                if face_id is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        faces.append(int(face_id))

        return faces

    def _parse_cq_params(self, params_str: str) -> dict[str, str]:
        """Parse CQ code parameters.

        Args:
            params_str: Parameter string like "file=xxx,url=yyy"

        Returns:
            Dict of parameter key-value pairs.
        """
        params = {}
        for part in params_str.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key.strip()] = value.strip()
        return params

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
