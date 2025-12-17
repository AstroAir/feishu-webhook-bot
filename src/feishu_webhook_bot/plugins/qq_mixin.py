"""QQ Plugin Mixin for enhanced QQ/OneBot11 integration.

This module provides a mixin class and decorators for plugins that need
to handle QQ-specific events and operations.

Example usage:
    ```python
    from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata
    from feishu_webhook_bot.plugins.qq_mixin import QQPluginMixin, on_qq_notice, on_qq_poke

    class MyQQPlugin(QQPluginMixin, BasePlugin):
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(name="my-qq-plugin", version="1.0.0")

        @on_qq_notice("group_increase")
        def on_member_join(self, event: dict):
            group_id = event.get("group_id")
            user_id = event.get("user_id")
            self.send_qq_message(f"欢迎 [CQ:at,qq={user_id}]！", f"group:{group_id}")

        @on_qq_poke
        def on_poke(self, event: dict):
            # Poke back!
            user_id = event.get("user_id")
            group_id = event.get("group_id")
            self.send_qq_poke(user_id, group_id)
    ```
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger

if TYPE_CHECKING:
    from .base import BasePlugin

logger = get_logger(__name__)


class QQNoticeType(str, Enum):
    """QQ notice event types."""

    GROUP_INCREASE = "group_increase"
    GROUP_DECREASE = "group_decrease"
    GROUP_BAN = "group_ban"
    GROUP_ADMIN = "group_admin"
    GROUP_UPLOAD = "group_upload"
    GROUP_RECALL = "group_recall"
    FRIEND_ADD = "friend_add"
    FRIEND_RECALL = "friend_recall"
    POKE = "poke"
    LUCKY_KING = "lucky_king"
    HONOR = "honor"


class QQRequestType(str, Enum):
    """QQ request event types."""

    FRIEND = "friend"
    GROUP = "group"


class QQMessageType(str, Enum):
    """QQ message event types."""

    PRIVATE = "private"
    GROUP = "group"


@dataclass
class QQNoticeEvent:
    """Structured QQ notice event data."""

    notice_type: str
    sub_type: str | None = None
    group_id: int | None = None
    user_id: int | None = None
    operator_id: int | None = None
    target_id: int | None = None  # For poke events
    duration: int | None = None  # For ban events
    message_id: int | None = None  # For recall events
    file: dict[str, Any] | None = None  # For upload events
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> QQNoticeEvent:
        """Create from raw event dict."""
        notice_type = event.get("notice_type", "")
        sub_type = event.get("sub_type")

        # Handle poke which is under "notify" notice_type
        if notice_type == "notify" and sub_type == "poke":
            notice_type = "poke"

        return cls(
            notice_type=notice_type,
            sub_type=sub_type,
            group_id=event.get("group_id"),
            user_id=event.get("user_id"),
            operator_id=event.get("operator_id"),
            target_id=event.get("target_id"),
            duration=event.get("duration"),
            message_id=event.get("message_id"),
            file=event.get("file"),
            raw=event,
        )


@dataclass
class QQRequestEvent:
    """Structured QQ request event data."""

    request_type: str
    sub_type: str | None = None
    user_id: int = 0
    group_id: int | None = None
    flag: str = ""
    comment: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> QQRequestEvent:
        """Create from raw event dict."""
        return cls(
            request_type=event.get("request_type", ""),
            sub_type=event.get("sub_type"),
            user_id=event.get("user_id", 0),
            group_id=event.get("group_id"),
            flag=event.get("flag", ""),
            comment=event.get("comment", ""),
            raw=event,
        )


@dataclass
class QQMessageEvent:
    """Structured QQ message event data."""

    message_type: str
    user_id: int = 0
    group_id: int | None = None
    message_id: int = 0
    raw_message: str = ""
    message: list[dict[str, Any]] = field(default_factory=list)
    sender: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> QQMessageEvent:
        """Create from raw event dict."""
        return cls(
            message_type=event.get("message_type", "private"),
            user_id=event.get("user_id", 0),
            group_id=event.get("group_id"),
            message_id=event.get("message_id", 0),
            raw_message=event.get("raw_message", ""),
            message=event.get("message", []),
            sender=event.get("sender", {}),
            raw=event,
        )

    @property
    def content(self) -> str:
        """Get plain text content from message."""
        if self.raw_message:
            import re

            return re.sub(r"\[CQ:[^\]]+\]", "", self.raw_message).strip()

        text_parts = []
        for segment in self.message:
            if segment.get("type") == "text":
                text_parts.append(segment.get("data", {}).get("text", ""))
        return "".join(text_parts).strip()

    @property
    def sender_name(self) -> str:
        """Get sender display name."""
        return self.sender.get("card") or self.sender.get("nickname") or str(self.user_id)

    @property
    def target(self) -> str:
        """Get target string for replying."""
        if self.message_type == "group" and self.group_id:
            return f"group:{self.group_id}"
        return f"private:{self.user_id}"


# Type for handler functions
NoticeHandler = Callable[["BasePlugin", QQNoticeEvent], None]
RequestHandler = Callable[["BasePlugin", QQRequestEvent], bool | None]
MessageHandler = Callable[["BasePlugin", QQMessageEvent], str | None]


def on_qq_notice(notice_type: str | QQNoticeType) -> Callable[[NoticeHandler], NoticeHandler]:
    """Decorator to register a QQ notice event handler.

    Args:
        notice_type: Type of notice to handle (e.g., "group_increase", "poke")

    Returns:
        Decorator function

    Example:
        ```python
        @on_qq_notice("group_increase")
        def on_member_join(self, event: QQNoticeEvent):
            self.send_qq_message(
                f"欢迎 [CQ:at,qq={event.user_id}]！",
                f"group:{event.group_id}"
            )
        ```
    """
    type_str = notice_type.value if isinstance(notice_type, QQNoticeType) else notice_type

    def decorator(func: NoticeHandler) -> NoticeHandler:
        @wraps(func)
        def wrapper(self: BasePlugin, event: QQNoticeEvent) -> None:
            return func(self, event)

        # Mark the handler with metadata
        wrapper._qq_notice_type = type_str  # type: ignore
        wrapper._qq_handler_type = "notice"  # type: ignore
        return wrapper

    return decorator


def on_qq_poke(func: NoticeHandler) -> NoticeHandler:
    """Decorator for handling poke events.

    Example:
        ```python
        @on_qq_poke
        def handle_poke(self, event: QQNoticeEvent):
            # Poke back!
            self.send_qq_poke(event.user_id, event.group_id)
        ```
    """

    @wraps(func)
    def wrapper(self: BasePlugin, event: QQNoticeEvent) -> None:
        return func(self, event)

    wrapper._qq_notice_type = "poke"  # type: ignore
    wrapper._qq_handler_type = "notice"  # type: ignore
    return wrapper


def on_qq_request(request_type: str | QQRequestType) -> Callable[[RequestHandler], RequestHandler]:
    """Decorator to register a QQ request event handler.

    Args:
        request_type: Type of request to handle ("friend" or "group")

    Returns:
        Decorator function

    Example:
        ```python
        @on_qq_request("friend")
        def on_friend_request(self, event: QQRequestEvent) -> bool | None:
            # Auto-approve if comment contains keyword
            if "验证码123" in event.comment:
                return True
            return None  # Let other handlers decide
        ```
    """
    type_str = request_type.value if isinstance(request_type, QQRequestType) else request_type

    def decorator(func: RequestHandler) -> RequestHandler:
        @wraps(func)
        def wrapper(self: BasePlugin, event: QQRequestEvent) -> bool | None:
            return func(self, event)

        wrapper._qq_request_type = type_str  # type: ignore
        wrapper._qq_handler_type = "request"  # type: ignore
        return wrapper

    return decorator


def on_qq_message(
    message_type: str | QQMessageType | None = None,
    keywords: list[str] | None = None,
    command: str | None = None,
) -> Callable[[MessageHandler], MessageHandler]:
    """Decorator to register a QQ message handler.

    Args:
        message_type: Filter by message type ("private", "group", or None for both)
        keywords: Only trigger if message contains any of these keywords
        command: Only trigger if message starts with this command (e.g., "/help")

    Returns:
        Decorator function

    Example:
        ```python
        @on_qq_message(command="/ping")
        def handle_ping(self, event: QQMessageEvent) -> str | None:
            return "pong!"

        @on_qq_message(keywords=["你好", "hello"])
        def handle_greeting(self, event: QQMessageEvent) -> str | None:
            return f"你好，{event.sender_name}！"
        ```
    """
    type_str = message_type.value if isinstance(message_type, QQMessageType) else message_type

    def decorator(func: MessageHandler) -> MessageHandler:
        @wraps(func)
        def wrapper(self: BasePlugin, event: QQMessageEvent) -> str | None:
            # Check message type filter
            if type_str and event.message_type != type_str:
                return None

            content = event.content

            # Check command filter
            if command and not content.startswith(command):
                return None

            # Check keywords filter
            if keywords and not any(kw in content for kw in keywords):
                return None

            return func(self, event)

        wrapper._qq_message_type = type_str  # type: ignore
        wrapper._qq_keywords = keywords  # type: ignore
        wrapper._qq_command = command  # type: ignore
        wrapper._qq_handler_type = "message"  # type: ignore
        return wrapper

    return decorator


class QQPluginMixin:
    """Mixin class for plugins that need QQ event handling.

    This mixin provides automatic dispatching of QQ events to decorated handlers
    and structured event objects.

    Usage:
        ```python
        class MyPlugin(QQPluginMixin, BasePlugin):
            @on_qq_notice("group_increase")
            def on_member_join(self, event: QQNoticeEvent):
                self.send_qq_message(f"欢迎！", f"group:{event.group_id}")

            @on_qq_poke
            def on_poke(self, event: QQNoticeEvent):
                self.send_qq_poke(event.user_id, event.group_id)

            @on_qq_message(command="/help")
            def on_help(self, event: QQMessageEvent) -> str:
                return "可用命令: /help, /ping, /status"
        ```
    """

    # Cache for discovered handlers
    _qq_notice_handlers: dict[str, list[NoticeHandler]] | None = None
    _qq_request_handlers: dict[str, list[RequestHandler]] | None = None
    _qq_message_handlers: list[MessageHandler] | None = None

    def _discover_qq_handlers(self) -> None:
        """Discover and cache QQ event handlers from decorated methods."""
        if self._qq_notice_handlers is not None:
            return  # Already discovered

        self._qq_notice_handlers = {}
        self._qq_request_handlers = {}
        self._qq_message_handlers = []

        for name in dir(self):
            if name.startswith("_"):
                continue

            try:
                method = getattr(self, name)
                if not callable(method):
                    continue

                handler_type = getattr(method, "_qq_handler_type", None)
                if not handler_type:
                    continue

                if handler_type == "notice":
                    notice_type = getattr(method, "_qq_notice_type", "")
                    if notice_type not in self._qq_notice_handlers:
                        self._qq_notice_handlers[notice_type] = []
                    self._qq_notice_handlers[notice_type].append(method)

                elif handler_type == "request":
                    request_type = getattr(method, "_qq_request_type", "")
                    if request_type not in self._qq_request_handlers:
                        self._qq_request_handlers[request_type] = []
                    self._qq_request_handlers[request_type].append(method)

                elif handler_type == "message":
                    self._qq_message_handlers.append(method)

            except Exception:
                continue

    def handle_qq_notice(self: BasePlugin, notice_type: str, event: dict[str, Any]) -> None:
        """Handle QQ notice events by dispatching to decorated handlers.

        This method is called by the plugin manager for QQ notice events.
        It dispatches to methods decorated with @on_qq_notice.
        """
        self._discover_qq_handlers()

        # Convert to structured event
        notice_event = QQNoticeEvent.from_event(event)

        # Dispatch to handlers
        handlers = self._qq_notice_handlers.get(notice_type, [])
        for handler in handlers:
            try:
                handler(notice_event)
            except Exception as e:
                logger.error(
                    "Error in QQ notice handler %s: %s",
                    handler.__name__,
                    e,
                    exc_info=True,
                )

    def handle_qq_request(
        self: BasePlugin, request_type: str, event: dict[str, Any]
    ) -> bool | None:
        """Handle QQ request events by dispatching to decorated handlers.

        Returns True to approve, False to reject, None to let other handlers decide.
        """
        self._discover_qq_handlers()

        # Convert to structured event
        request_event = QQRequestEvent.from_event(event)

        # Dispatch to handlers
        handlers = self._qq_request_handlers.get(request_type, [])
        for handler in handlers:
            try:
                result = handler(request_event)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(
                    "Error in QQ request handler %s: %s",
                    handler.__name__,
                    e,
                    exc_info=True,
                )

        return None

    def handle_qq_message(self: BasePlugin, event: dict[str, Any]) -> str | None:
        """Handle QQ message events by dispatching to decorated handlers.

        Returns response message or None.
        """
        self._discover_qq_handlers()

        # Convert to structured event
        message_event = QQMessageEvent.from_event(event)

        # Dispatch to handlers
        for handler in self._qq_message_handlers or []:
            try:
                result = handler(message_event)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(
                    "Error in QQ message handler %s: %s",
                    handler.__name__,
                    e,
                    exc_info=True,
                )

        return None


__all__ = [
    "QQPluginMixin",
    "QQNoticeType",
    "QQRequestType",
    "QQMessageType",
    "QQNoticeEvent",
    "QQRequestEvent",
    "QQMessageEvent",
    "on_qq_notice",
    "on_qq_poke",
    "on_qq_request",
    "on_qq_message",
]
