"""Unified message handling interface for multi-platform messaging support.

This module provides a standardized message representation and handling protocol
for incoming messages from different platforms (Feishu, QQ, etc.).

Key components:
- IncomingMessage: Universal incoming message data class
- MessageHandler: Protocol for message handlers
- MessageParser: Protocol for platform-specific message parsers
- Utility functions: User/chat key generation for conversation tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from .logger import get_logger
from .provider import SendResult

logger = get_logger(__name__)


@dataclass
class IncomingMessage:
    """Universal incoming message representation across platforms.

    This class provides a unified interface for messages from different
    platforms (Feishu, QQ, etc.), enabling consistent message handling
    across the bot framework.

    Attributes:
        id: Platform-specific message ID or unique identifier.
        platform: Source platform identifier (e.g., "feishu", "qq").
        chat_type: Type of chat (private DM, group, or channel).
        chat_id: Group/channel ID. Empty string for private chats.
        sender_id: User ID on the platform.
        sender_name: Display name or username of the sender.
        content: Text content of the message.
        mentions: List of @mentioned user IDs on this platform.
        is_at_bot: Whether the bot itself is @mentioned in this message.
        reply_to: Message ID being replied to (None for top-level messages).
        thread_id: Thread or topic ID for threaded conversations (None if not threaded).
        timestamp: When the message was created. Defaults to current time.
        raw_content: Platform-specific raw content (JSON, dict, etc.) for advanced use.
        metadata: Additional platform-specific metadata.

    Example:
        ```python
        # From a Feishu group message mentioning the bot
        msg = IncomingMessage(
            id="om_xxxxx",
            platform="feishu",
            chat_type="group",
            chat_id="oc_xxxxx",
            sender_id="ou_xxxxx",
            sender_name="Alice",
            content="@bot help",
            is_at_bot=True,
            mentions=["bot_id"],
        )

        # From a QQ private message with reply
        msg = IncomingMessage(
            id="12345",
            platform="qq",
            chat_type="private",
            chat_id="",
            sender_id="123456789",
            sender_name="Bob",
            content="Are you there?",
            reply_to="11111",
        )
        ```
    """

    id: str
    """Platform-specific message ID."""

    platform: Literal["feishu", "qq"]
    """Message platform identifier."""

    chat_type: Literal["private", "group", "channel"]
    """Chat type: DM, group chat, or channel/topic."""

    chat_id: str
    """Group/channel ID. Empty for private chats."""

    sender_id: str
    """User ID on the platform."""

    sender_name: str
    """Display name or username."""

    content: str
    """Text content of the message."""

    mentions: list[str] = field(default_factory=list)
    """List of @mentioned user IDs."""

    is_at_bot: bool = False
    """Whether the bot is @mentioned."""

    reply_to: str | None = None
    """Message ID being replied to."""

    thread_id: str | None = None
    """Thread or topic ID for threaded conversations."""

    timestamp: datetime = field(default_factory=datetime.now)
    """Message creation timestamp."""

    raw_content: Any = None
    """Platform-specific raw content (JSON, dict, etc.)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Extra platform-specific data."""

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for serialization.

        This method converts all fields to JSON-serializable types,
        converting datetime objects to ISO format strings.

        Returns:
            Dictionary representation of the message.

        Example:
            ```python
            msg = IncomingMessage(...)
            data = msg.to_dict()
            json_str = json.dumps(data)
            ```
        """
        return {
            "id": self.id,
            "platform": self.platform,
            "chat_type": self.chat_type,
            "chat_id": self.chat_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "mentions": self.mentions,
            "is_at_bot": self.is_at_bot,
            "reply_to": self.reply_to,
            "thread_id": self.thread_id,
            "timestamp": self.timestamp.isoformat(),
            "raw_content": self.raw_content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IncomingMessage:
        """Create message from dictionary.

        This method reconstructs a message from a dictionary, converting
        ISO format timestamp strings back to datetime objects.

        Args:
            data: Dictionary representation of the message.

        Returns:
            Reconstructed IncomingMessage instance.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If field values are invalid.

        Example:
            ```python
            data = {"id": "123", "platform": "feishu", ...}
            msg = IncomingMessage.from_dict(data)
            ```
        """
        # Parse timestamp if it's a string
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            id=data["id"],
            platform=data["platform"],
            chat_type=data["chat_type"],
            chat_id=data["chat_id"],
            sender_id=data["sender_id"],
            sender_name=data["sender_name"],
            content=data["content"],
            mentions=data.get("mentions", []),
            is_at_bot=data.get("is_at_bot", False),
            reply_to=data.get("reply_to"),
            thread_id=data.get("thread_id"),
            timestamp=timestamp,
            raw_content=data.get("raw_content"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<IncomingMessage id={self.id} platform={self.platform} "
            f"from {self.sender_name} ({self.sender_id})>"
        )


@runtime_checkable
class MessageHandler(Protocol):
    """Protocol for message handlers.

    Implementations should handle incoming messages and optionally send
    replies. This protocol can be used for type checking and duck typing.

    Example:
        ```python
        class MyHandler:
            async def handle_message(self, message: IncomingMessage) -> str | None:
                if "hello" in message.content.lower():
                    return "Hello! How can I help?"
                return None

            async def send_reply(
                self,
                message: IncomingMessage,
                reply: str,
                reply_in_thread: bool = True
            ) -> SendResult:
                # Send the reply to the original message
                return SendResult.ok(message_id="reply_id")

        handler: MessageHandler = MyHandler()
        ```
    """

    async def handle_message(self, message: IncomingMessage) -> str | None:
        """Handle incoming message and return optional response.

        This method should process an incoming message and optionally
        return a text response. Returning None indicates no automatic
        reply should be sent.

        Args:
            message: The incoming message to handle.

        Returns:
            Response text to send, or None to skip automatic reply.

        Raises:
            Exception: Handler implementation may raise exceptions for
                error handling by the caller.

        Example:
            ```python
            async def handle_message(self, message: IncomingMessage) -> str | None:
                logger.info(f"Received: {message.content}")
                if message.is_at_bot:
                    return f"You said: {message.content}"
                return None
            ```
        """
        ...

    async def send_reply(
        self,
        message: IncomingMessage,
        reply: str,
        reply_in_thread: bool = True,
    ) -> SendResult:
        """Send reply to the original message.

        This method sends a reply to the original message, optionally
        in a thread/topic if the platform supports it.

        Args:
            message: The original message being replied to.
            reply: The reply text to send.
            reply_in_thread: If True, send in thread if available.

        Returns:
            SendResult indicating success/failure of the send operation.

        Raises:
            Exception: Handler implementation may raise exceptions for
                error handling by the caller.

        Example:
            ```python
            async def send_reply(
                self,
                message: IncomingMessage,
                reply: str,
                reply_in_thread: bool = True,
            ) -> SendResult:
                # Send reply to the message's chat
                target = message.chat_id or message.sender_id
                return self.client.send_text(reply, target)
            ```
        """
        ...


@runtime_checkable
class MessageParser(Protocol):
    """Protocol for platform-specific message parsers.

    Implementations parse platform-specific event payloads into a
    unified IncomingMessage representation.

    Example:
        ```python
        class FeishuMessageParser:
            def can_parse(self, payload: dict[str, Any]) -> bool:
                return payload.get("type") == "message"

            def parse(self, payload: dict[str, Any]) -> IncomingMessage | None:
                if not self.can_parse(payload):
                    return None
                # Parse Feishu event structure...
                return IncomingMessage(...)

        parser: MessageParser = FeishuMessageParser()
        if parser.can_parse(webhook_payload):
            message = parser.parse(webhook_payload)
        ```
    """

    def parse(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse platform event payload into IncomingMessage.

        This method should extract relevant information from a
        platform-specific event payload and convert it to the
        unified IncomingMessage format. Return None if the payload
        doesn't represent a message event.

        Args:
            payload: Platform-specific event payload (typically from webhook).

        Returns:
            Parsed IncomingMessage, or None if not a message event.

        Raises:
            ValueError: If payload is malformed.
            KeyError: If required fields are missing.

        Example:
            ```python
            def parse(self, payload: dict[str, Any]) -> IncomingMessage | None:
                if payload.get("type") != "message":
                    return None

                msg_data = payload["event"]["message"]
                return IncomingMessage(
                    id=msg_data["message_id"],
                    platform="feishu",
                    chat_type="group",
                    chat_id=payload["event"]["chat_id"],
                    sender_id=msg_data["sender_id"],
                    sender_name=msg_data.get("sender_name", "Unknown"),
                    content=msg_data.get("text", ""),
                )
            ```
        """
        ...

    def can_parse(self, payload: dict[str, Any]) -> bool:
        """Check if this parser can handle the payload.

        This method is called before parse() to determine if this parser
        should attempt to parse the payload. Useful for routing payloads
        to the correct parser in a multi-parser setup.

        Args:
            payload: Platform-specific event payload.

        Returns:
            True if this parser can handle the payload, False otherwise.

        Example:
            ```python
            def can_parse(self, payload: dict[str, Any]) -> bool:
                return payload.get("type") == "message"
            ```
        """
        ...


def get_user_key(message: IncomingMessage) -> str:
    """Generate unique user key for conversation tracking.

    This key combines platform, chat type, and sender ID to create a
    unique identifier for user-level conversation state. Useful for
    maintaining per-user conversation context across messages.

    Format: `{platform}:{chat_type}:{sender_id}`

    Args:
        message: The message to generate key for.

    Returns:
        Unique user key string.

    Example:
        ```python
        msg = IncomingMessage(
            platform="feishu",
            chat_type="group",
            sender_id="ou_xxxxx",
            ...
        )
        key = get_user_key(msg)
        # Returns: "feishu:group:ou_xxxxx"

        # Track user context
        user_contexts[key] = {"last_command": "help", ...}
        ```
    """
    return f"{message.platform}:{message.chat_type}:{message.sender_id}"


def get_chat_key(message: IncomingMessage) -> str:
    """Generate unique chat key for chat-level tracking.

    This key combines platform and chat identifier to create a unique
    identifier for chat-level state. For private chats, uses sender ID
    as the identifier. Useful for maintaining per-chat configuration
    and state.

    Format: `{platform}:{chat_id or sender_id}`

    Args:
        message: The message to generate key for.

    Returns:
        Unique chat key string.

    Example:
        ```python
        # Group message
        msg = IncomingMessage(
            platform="feishu",
            chat_id="oc_xxxxx",
            sender_id="ou_xxxxx",
            ...
        )
        key = get_chat_key(msg)
        # Returns: "feishu:oc_xxxxx"

        # Private message
        msg = IncomingMessage(
            platform="qq",
            chat_id="",
            sender_id="123456789",
            ...
        )
        key = get_chat_key(msg)
        # Returns: "qq:123456789"

        # Track per-chat state
        chat_settings[key] = {"language": "zh", "timezone": "UTC+8"}
        ```
    """
    chat_identifier = message.chat_id or message.sender_id
    return f"{message.platform}:{chat_identifier}"
