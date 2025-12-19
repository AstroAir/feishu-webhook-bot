"""QQ Napcat provider implementation based on OneBot11 protocol.

This module provides a comprehensive QQ bot implementation using the OneBot11 protocol,
compatible with NapCatQQ, LLOneBot, Lagrange, and other OneBot11 implementations.

Features:
- Full OneBot11 API support (send/receive messages, group management, user info)
- NapCat extended APIs (AI voice, poke, emoji reactions)
- Async and sync message sending
- Message forwarding and history retrieval
- Group and friend management
- Circuit breaker and retry support
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field

from ..core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ..core.logger import get_logger
from ..core.message_tracker import MessageStatus, MessageTracker
from ..core.provider import BaseProvider, Message, MessageType, ProviderConfig, SendResult
from .base_http import HTTPProviderMixin

logger = get_logger(__name__)


# ==============================================================================
# Data Models
# ==============================================================================


class OnlineStatus(int, Enum):
    """QQ online status codes."""

    ONLINE = 11  # 在线
    AWAY = 31  # 离开
    INVISIBLE = 41  # 隐身
    BUSY = 50  # 忙碌
    Q_ME = 60  # Q我吧
    DO_NOT_DISTURB = 70  # 请勿打扰


@dataclass
class QQUserInfo:
    """QQ user information."""

    user_id: int
    nickname: str
    sex: str = "unknown"  # male, female, unknown
    age: int = 0
    remark: str = ""  # Friend remark name


@dataclass
class QQGroupInfo:
    """QQ group information."""

    group_id: int
    group_name: str
    member_count: int = 0
    max_member_count: int = 0


@dataclass
class QQGroupMember:
    """QQ group member information."""

    group_id: int
    user_id: int
    nickname: str
    card: str = ""  # Group card/nickname
    sex: str = "unknown"
    age: int = 0
    role: str = "member"  # owner, admin, member
    title: str = ""  # Special title
    join_time: int = 0
    last_sent_time: int = 0


@dataclass
class QQMessage:
    """QQ message information."""

    message_id: int
    message_type: str  # private, group
    sender_id: int
    sender_nickname: str
    content: list[dict[str, Any]]
    time: int
    group_id: int | None = None


class OneBotResponse(BaseModel):
    """OneBot API response model."""

    status: str  # ok, failed, async
    retcode: int = 0
    data: Any = None
    msg: str = ""
    wording: str = ""


class NapcatProviderConfig(ProviderConfig):
    """Configuration for QQ Napcat provider (OneBot11 protocol)."""

    provider_type: str = Field(default="napcat", description="Provider type")
    http_url: str = Field(
        ...,
        description="Napcat HTTP API base URL (e.g., http://127.0.0.1:3000)",
    )
    access_token: str | None = Field(
        default=None,
        description="Optional Napcat API access token for authentication",
    )
    bot_qq: str | None = Field(
        default=None,
        description="Bot's QQ number for @mention detection",
    )
    enable_ai_voice: bool = Field(
        default=False,
        description="Enable NapCat AI voice features",
    )


class NapcatProvider(BaseProvider, HTTPProviderMixin):
    """QQ Napcat message provider implementation.

    Supports OneBot11 protocol for:
    - Text messages (private and group)
    - Rich text messages (converted to CQ code format)
    - Image, audio, video messages
    - Forward messages and message history
    - Group management (kick, ban, admin)
    - User and group information queries
    - NapCat extended APIs (AI voice, poke, emoji reactions)

    Target format:
    - Private message: "private:QQ号" (e.g., "private:123456789")
    - Group message: "group:群号" (e.g., "group:987654321")

    Example:
        ```python
        from feishu_webhook_bot.providers import NapcatProvider, NapcatProviderConfig

        config = NapcatProviderConfig(
            http_url="http://127.0.0.1:3000",
            access_token="your_token",
            bot_qq="123456789",
        )
        provider = NapcatProvider(config)
        provider.connect()

        # Send message
        result = provider.send_text("Hello!", "group:987654321")

        # Get user info
        user = provider.get_stranger_info(123456789)

        # Group management
        provider.set_group_ban(987654321, 123456789, duration=60)
        ```
    """

    def __init__(
        self,
        config: NapcatProviderConfig,
        message_tracker: MessageTracker | None = None,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        """Initialize Napcat provider.

        Args:
            config: Napcat provider configuration
            message_tracker: Optional message tracker for delivery tracking
            circuit_breaker_config: Optional circuit breaker configuration
        """
        super().__init__(config)
        self.config: NapcatProviderConfig = config
        self._client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        self._message_tracker = message_tracker
        self._circuit_breaker = CircuitBreaker(
            f"napcat_{config.name}",
            circuit_breaker_config or CircuitBreakerConfig(),
        )
        self._login_info: dict[str, Any] | None = None

    def connect(self) -> None:
        """Connect to Napcat API."""
        if self._connected:
            return

        try:
            headers = {"Content-Type": "application/json"}
            if self.config.access_token:
                headers["Authorization"] = f"Bearer {self.config.access_token}"

            timeout = self.config.timeout or 10.0
            self._client = httpx.Client(
                timeout=timeout,
                headers=headers,
                base_url=self.config.http_url,
            )
            self._connected = True
            self.logger.info(f"Connected to Napcat: {self.config.name}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Napcat: {e}", exc_info=True)
            raise

    def disconnect(self) -> None:
        """Disconnect from Napcat API."""
        if self._client:
            self._client.close()
        self._connected = False
        self.logger.info(f"Disconnected from Napcat: {self.config.name}")

    def send_message(self, message: Message, target: str) -> SendResult:
        """Send a message with automatic type detection.

        Args:
            message: Message to send
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status and message ID
        """
        if message.type == MessageType.TEXT:
            return self.send_text(message.content, target)
        elif message.type == MessageType.RICH_TEXT:
            return self.send_rich_text(
                message.content.get("title", ""),
                message.content.get("content", []),
                target,
                message.content.get("language", "zh_cn"),
            )
        elif message.type == MessageType.IMAGE:
            return self.send_image(message.content, target)
        elif message.type == MessageType.CARD:
            return SendResult.fail("Card messages not supported by Napcat (OneBot11)")
        else:
            return SendResult.fail(f"Unsupported message type: {message.type}")

    def send_text(self, text: str, target: str) -> SendResult:
        """Send a text message.

        Args:
            text: Text content
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status and message ID
        """
        message_id = str(uuid.uuid4())

        try:
            # Parse target format
            user_id, group_id = self._parse_target(target)

            if not user_id and not group_id:
                return SendResult.fail("Invalid target format. Use 'private:QQ号' or 'group:群号'")

            # Track message if tracker enabled
            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, target, text)

            # Prepare CQ message segments
            message_segments = [
                {
                    "type": "text",
                    "data": {
                        "text": text,
                    },
                }
            ]

            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            self._log_message_send_result(
                success=True,
                message_type="text",
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
            )
            return SendResult.ok(message_id, result)

        except Exception as e:
            error_msg = str(e)
            self._log_message_send_result(
                success=False,
                message_type="text",
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
                error=error_msg,
            )

            if self._message_tracker:
                self._message_tracker.update_status(
                    message_id, MessageStatus.FAILED, error=error_msg
                )

            return SendResult.fail(error_msg)

    def send_card(self, card: dict[str, Any], target: str) -> SendResult:
        """Card messages are not supported by OneBot11.

        Args:
            card: Card data
            target: Target identifier

        Returns:
            SendResult with failure status
        """
        return SendResult.fail("Card messages not supported by OneBot11/Napcat protocol")

    def send_rich_text(
        self,
        title: str,
        content: list[list[dict[str, Any]]],
        target: str,
        language: str = "zh_cn",
    ) -> SendResult:
        """Send rich text message converted to text with formatting.

        Args:
            title: Text title/header
            content: Content structure (converted to formatted text)
            target: Target in format "private:QQ号" or "group:群号"
            language: Language code (ignored for OneBot11)

        Returns:
            SendResult with status and message ID
        """
        message_id = str(uuid.uuid4())

        try:
            # Parse target format
            user_id, group_id = self._parse_target(target)

            if not user_id and not group_id:
                return SendResult.fail("Invalid target format. Use 'private:QQ号' or 'group:群号'")

            # Track message if tracker enabled
            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, target, content)

            # Convert rich text to OneBot message format
            message_segments = self._convert_rich_text_to_segments(title, content)

            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            self._log_message_send_result(
                success=True,
                message_type="rich_text",
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
            )
            return SendResult.ok(message_id, result)

        except Exception as e:
            error_msg = str(e)
            self._log_message_send_result(
                success=False,
                message_type="rich_text",
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
                error=error_msg,
            )

            if self._message_tracker:
                self._message_tracker.update_status(
                    message_id, MessageStatus.FAILED, error=error_msg
                )

            return SendResult.fail(error_msg)

    def send_image(self, image_key: str, target: str) -> SendResult:
        """Send an image message using CQ code format.

        Args:
            image_key: Image URL or file path
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status and message ID
        """
        message_id = str(uuid.uuid4())

        try:
            # Parse target format
            user_id, group_id = self._parse_target(target)

            if not user_id and not group_id:
                return SendResult.fail("Invalid target format. Use 'private:QQ号' or 'group:群号'")

            # Track message if tracker enabled
            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, target, image_key)

            # Prepare CQ image message segment
            message_segments = [
                {
                    "type": "image",
                    "data": {
                        "file": image_key,
                    },
                }
            ]

            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            self._log_message_send_result(
                success=True,
                message_type="image",
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
            )
            return SendResult.ok(message_id, result)

        except Exception as e:
            error_msg = str(e)
            self._log_message_send_result(
                success=False,
                message_type="image",
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
                error=error_msg,
            )

            if self._message_tracker:
                self._message_tracker.update_status(
                    message_id, MessageStatus.FAILED, error=error_msg
                )

            return SendResult.fail(error_msg)

    def _parse_target(self, target: str) -> tuple[int | None, int | None]:
        """Parse target format to extract user_id and group_id.

        Args:
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            Tuple of (user_id, group_id) - one will be None
        """
        parts = target.split(":")
        if len(parts) != 2:
            return None, None

        target_type, target_id = parts[0], parts[1]

        try:
            if target_type == "private":
                return int(target_id), None
            elif target_type == "group":
                return None, int(target_id)
        except ValueError:
            self.logger.warning(f"Invalid target ID in '{target}'")

        return None, None

    def _convert_rich_text_to_segments(
        self, title: str, content: list[list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """Convert rich text format to OneBot message segments.

        Args:
            title: Text title
            content: Content structure

        Returns:
            List of OneBot message segments
        """
        segments: list[dict[str, Any]] = []

        # Add title if provided
        if title:
            segments.append(
                {
                    "type": "text",
                    "data": {
                        "text": f"{title}\n",
                    },
                }
            )

        # Process content paragraphs
        for paragraph in content:
            paragraph_text = ""

            for element in paragraph:
                if isinstance(element, dict):
                    if element.get("type") == "text":
                        paragraph_text += element.get("text", "")
                    elif element.get("type") == "at":
                        # Convert @mention to CQ code
                        user_id = element.get("user_id")
                        if user_id:
                            paragraph_text += f"[CQ:at,qq={user_id}]"
                    elif element.get("type") == "link":
                        # Convert link to text format
                        text = element.get("text", "")
                        href = element.get("href", "")
                        paragraph_text += f"{text}({href})"

            if paragraph_text:
                segments.append(
                    {
                        "type": "text",
                        "data": {
                            "text": paragraph_text + "\n",
                        },
                    }
                )

        return segments

    def _send_onebot_message(
        self,
        message_id: str,
        user_id: int | None,
        group_id: int | None,
        message_segments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Send message via OneBot11 API with circuit breaker and retry logic.

        Args:
            message_id: Unique message identifier
            user_id: QQ user ID for private messages
            group_id: QQ group ID for group messages
            message_segments: OneBot message segments

        Returns:
            API response data

        Raises:
            Exception: If request fails
        """
        if not self._client:
            raise RuntimeError("Provider not connected. Call connect() first.")

        # Determine endpoint based on target type
        if user_id:
            endpoint = "/send_private_msg"
            payload = {
                "user_id": user_id,
                "message": message_segments,
            }
        elif group_id:
            endpoint = "/send_group_msg"
            payload = {
                "group_id": group_id,
                "message": message_segments,
            }
        else:
            raise ValueError("Either user_id or group_id must be specified")

        # Wrap with circuit breaker
        def _make_request() -> dict[str, Any]:
            return self._circuit_breaker.call(self._make_http_request, endpoint, payload)

        return _make_request()

    def _make_http_request(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make actual HTTP request with retry logic.

        Args:
            endpoint: API endpoint path
            payload: Request payload

        Returns:
            Response data

        Raises:
            Exception: If all retries fail
        """
        if not self._client:
            raise RuntimeError("HTTP client not initialized")

        def _validate_onebot_response(result: dict[str, Any]) -> None:
            """Validate OneBot API response."""
            if result.get("status") != "ok":
                raise ValueError(f"OneBot API error: {result.get('msg', 'Unknown error')}")

        return self._http_request_with_retry(
            client=self._client,
            url=endpoint,
            payload=payload,
            retry_policy=self.config.retry,
            provider_name=self.name,
            provider_type=self.provider_type,
            response_validator=_validate_onebot_response,
        )

    def get_capabilities(self) -> dict[str, bool]:
        """Get supported message types.

        Returns:
            Dictionary of capability flags
        """
        return {
            "text": True,
            "rich_text": True,
            "card": False,  # Not supported by OneBot11
            "image": True,
            "file": True,
            "audio": True,
            "video": True,
            "forward": True,
            "poke": True,
        }

    # ==========================================================================
    # OneBot11 Standard APIs - Message Operations
    # ==========================================================================

    def delete_msg(self, message_id: int) -> bool:
        """Recall/delete a message.

        Args:
            message_id: Message ID to delete

        Returns:
            True if successful
        """
        try:
            self._call_api("/delete_msg", {"message_id": message_id})
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete message {message_id}: {e}")
            return False

    def get_msg(self, message_id: int) -> QQMessage | None:
        """Get message details by ID.

        Args:
            message_id: Message ID

        Returns:
            QQMessage object or None if not found
        """
        try:
            data = self._call_api("/get_msg", {"message_id": message_id})
            if data:
                return QQMessage(
                    message_id=data.get("message_id", message_id),
                    message_type=data.get("message_type", ""),
                    sender_id=data.get("sender", {}).get("user_id", 0),
                    sender_nickname=data.get("sender", {}).get("nickname", ""),
                    content=data.get("message", []),
                    time=data.get("time", 0),
                    group_id=data.get("group_id"),
                )
        except Exception as e:
            self.logger.error(f"Failed to get message {message_id}: {e}")
        return None

    def send_like(self, user_id: int, times: int = 1) -> bool:
        """Send likes to a user's profile.

        Args:
            user_id: Target QQ number
            times: Number of likes (max 10 per day per user)

        Returns:
            True if successful
        """
        try:
            self._call_api("/send_like", {"user_id": user_id, "times": min(times, 10)})
            return True
        except Exception as e:
            self.logger.error(f"Failed to send like to {user_id}: {e}")
            return False

    def send_forward_msg(
        self,
        target: str,
        messages: list[dict[str, Any]],
    ) -> SendResult:
        """Send a forward message (合并转发).

        Args:
            target: Target in format "private:QQ号" or "group:群号"
            messages: List of message nodes

        Returns:
            SendResult with message ID
        """
        message_id = str(uuid.uuid4())
        try:
            user_id, group_id = self._parse_target(target)

            payload: dict[str, Any] = {"messages": messages}
            if user_id:
                payload["message_type"] = "private"
                payload["user_id"] = user_id
            elif group_id:
                payload["message_type"] = "group"
                payload["group_id"] = group_id
            else:
                return SendResult.fail("Invalid target format")

            result = self._call_api("/send_forward_msg", payload)
            return SendResult.ok(str(result.get("message_id", message_id)), result)
        except Exception as e:
            return SendResult.fail(str(e))

    def get_forward_msg(self, forward_id: str) -> list[dict[str, Any]]:
        """Get forward message content.

        Args:
            forward_id: Forward message ID

        Returns:
            List of message nodes
        """
        try:
            data = self._call_api("/get_forward_msg", {"id": forward_id})
            return data.get("message", []) if data else []
        except Exception as e:
            self.logger.error(f"Failed to get forward message: {e}")
            return []

    # ==========================================================================
    # OneBot11 Standard APIs - User Information
    # ==========================================================================

    def get_login_info(self) -> dict[str, Any]:
        """Get bot's login information.

        Returns:
            Dict with user_id and nickname
        """
        if self._login_info:
            return self._login_info

        try:
            data = self._call_api("/get_login_info", {})
            self._login_info = data or {}
            return self._login_info
        except Exception as e:
            self.logger.error(f"Failed to get login info: {e}")
            return {}

    def get_stranger_info(self, user_id: int, no_cache: bool = False) -> QQUserInfo | None:
        """Get stranger/user information.

        Args:
            user_id: QQ number
            no_cache: Whether to bypass cache

        Returns:
            QQUserInfo object or None
        """
        try:
            data = self._call_api(
                "/get_stranger_info",
                {"user_id": user_id, "no_cache": no_cache},
            )
            if data:
                return QQUserInfo(
                    user_id=data.get("user_id", user_id),
                    nickname=data.get("nickname", ""),
                    sex=data.get("sex", "unknown"),
                    age=data.get("age", 0),
                )
        except Exception as e:
            self.logger.error(f"Failed to get stranger info for {user_id}: {e}")
        return None

    def get_friend_list(self) -> list[QQUserInfo]:
        """Get bot's friend list.

        Returns:
            List of QQUserInfo objects
        """
        try:
            data = self._call_api("/get_friend_list", {})
            if data and isinstance(data, list):
                return [
                    QQUserInfo(
                        user_id=f.get("user_id", 0),
                        nickname=f.get("nickname", ""),
                        remark=f.get("remark", ""),
                    )
                    for f in data
                ]
        except Exception as e:
            self.logger.error(f"Failed to get friend list: {e}")
        return []

    # ==========================================================================
    # OneBot11 Standard APIs - Group Information
    # ==========================================================================

    def get_group_info(self, group_id: int, no_cache: bool = False) -> QQGroupInfo | None:
        """Get group information.

        Args:
            group_id: Group number
            no_cache: Whether to bypass cache

        Returns:
            QQGroupInfo object or None
        """
        try:
            data = self._call_api(
                "/get_group_info",
                {"group_id": group_id, "no_cache": no_cache},
            )
            if data:
                return QQGroupInfo(
                    group_id=data.get("group_id", group_id),
                    group_name=data.get("group_name", ""),
                    member_count=data.get("member_count", 0),
                    max_member_count=data.get("max_member_count", 0),
                )
        except Exception as e:
            self.logger.error(f"Failed to get group info for {group_id}: {e}")
        return None

    def get_group_list(self) -> list[QQGroupInfo]:
        """Get bot's group list.

        Returns:
            List of QQGroupInfo objects
        """
        try:
            data = self._call_api("/get_group_list", {})
            if data and isinstance(data, list):
                return [
                    QQGroupInfo(
                        group_id=g.get("group_id", 0),
                        group_name=g.get("group_name", ""),
                        member_count=g.get("member_count", 0),
                        max_member_count=g.get("max_member_count", 0),
                    )
                    for g in data
                ]
        except Exception as e:
            self.logger.error(f"Failed to get group list: {e}")
        return []

    def get_group_member_info(
        self,
        group_id: int,
        user_id: int,
        no_cache: bool = False,
    ) -> QQGroupMember | None:
        """Get group member information.

        Args:
            group_id: Group number
            user_id: Member's QQ number
            no_cache: Whether to bypass cache

        Returns:
            QQGroupMember object or None
        """
        try:
            data = self._call_api(
                "/get_group_member_info",
                {"group_id": group_id, "user_id": user_id, "no_cache": no_cache},
            )
            if data:
                return QQGroupMember(
                    group_id=data.get("group_id", group_id),
                    user_id=data.get("user_id", user_id),
                    nickname=data.get("nickname", ""),
                    card=data.get("card", ""),
                    sex=data.get("sex", "unknown"),
                    age=data.get("age", 0),
                    role=data.get("role", "member"),
                    title=data.get("title", ""),
                    join_time=data.get("join_time", 0),
                    last_sent_time=data.get("last_sent_time", 0),
                )
        except Exception as e:
            self.logger.error(f"Failed to get member info: {e}")
        return None

    def get_group_member_list(self, group_id: int) -> list[QQGroupMember]:
        """Get all members of a group.

        Args:
            group_id: Group number

        Returns:
            List of QQGroupMember objects
        """
        try:
            data = self._call_api("/get_group_member_list", {"group_id": group_id})
            if data and isinstance(data, list):
                return [
                    QQGroupMember(
                        group_id=group_id,
                        user_id=m.get("user_id", 0),
                        nickname=m.get("nickname", ""),
                        card=m.get("card", ""),
                        role=m.get("role", "member"),
                    )
                    for m in data
                ]
        except Exception as e:
            self.logger.error(f"Failed to get group member list: {e}")
        return []

    # ==========================================================================
    # OneBot11 Standard APIs - Group Management
    # ==========================================================================

    def set_group_kick(
        self,
        group_id: int,
        user_id: int,
        reject_add_request: bool = False,
    ) -> bool:
        """Kick a member from group.

        Args:
            group_id: Group number
            user_id: Member to kick
            reject_add_request: Whether to reject future join requests

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_kick",
                {
                    "group_id": group_id,
                    "user_id": user_id,
                    "reject_add_request": reject_add_request,
                },
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to kick user {user_id} from group {group_id}: {e}")
            return False

    def set_group_ban(
        self,
        group_id: int,
        user_id: int,
        duration: int = 1800,
    ) -> bool:
        """Ban/mute a group member.

        Args:
            group_id: Group number
            user_id: Member to ban
            duration: Ban duration in seconds (0 to unban)

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_ban",
                {"group_id": group_id, "user_id": user_id, "duration": duration},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to ban user {user_id}: {e}")
            return False

    def set_group_whole_ban(self, group_id: int, enable: bool = True) -> bool:
        """Enable/disable whole group mute.

        Args:
            group_id: Group number
            enable: Whether to enable mute

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_whole_ban",
                {"group_id": group_id, "enable": enable},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set whole ban for group {group_id}: {e}")
            return False

    def set_group_admin(
        self,
        group_id: int,
        user_id: int,
        enable: bool = True,
    ) -> bool:
        """Set/unset group admin.

        Args:
            group_id: Group number
            user_id: Member to set as admin
            enable: Whether to set as admin

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_admin",
                {"group_id": group_id, "user_id": user_id, "enable": enable},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set admin for user {user_id}: {e}")
            return False

    def set_group_card(self, group_id: int, user_id: int, card: str = "") -> bool:
        """Set group member's card/nickname.

        Args:
            group_id: Group number
            user_id: Member's QQ number
            card: New card name (empty to clear)

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_card",
                {"group_id": group_id, "user_id": user_id, "card": card},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set card for user {user_id}: {e}")
            return False

    def set_group_name(self, group_id: int, group_name: str) -> bool:
        """Set group name.

        Args:
            group_id: Group number
            group_name: New group name

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_name",
                {"group_id": group_id, "group_name": group_name},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set group name: {e}")
            return False

    def set_group_leave(self, group_id: int, is_dismiss: bool = False) -> bool:
        """Leave a group.

        Args:
            group_id: Group number
            is_dismiss: Whether to dismiss group (if owner)

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_leave",
                {"group_id": group_id, "is_dismiss": is_dismiss},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to leave group {group_id}: {e}")
            return False

    def set_group_special_title(
        self,
        group_id: int,
        user_id: int,
        special_title: str = "",
        duration: int = -1,
    ) -> bool:
        """Set member's special title.

        Args:
            group_id: Group number
            user_id: Member's QQ number
            special_title: Special title (empty to clear)
            duration: Duration in seconds (-1 for permanent)

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_special_title",
                {
                    "group_id": group_id,
                    "user_id": user_id,
                    "special_title": special_title,
                    "duration": duration,
                },
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set special title: {e}")
            return False

    # ==========================================================================
    # OneBot11 Standard APIs - Request Handling
    # ==========================================================================

    def set_friend_add_request(
        self,
        flag: str,
        approve: bool = True,
        remark: str = "",
    ) -> bool:
        """Handle friend add request.

        Args:
            flag: Request flag from event
            approve: Whether to approve
            remark: Friend remark (if approved)

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_friend_add_request",
                {"flag": flag, "approve": approve, "remark": remark},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to handle friend request: {e}")
            return False

    def set_group_add_request(
        self,
        flag: str,
        sub_type: str,
        approve: bool = True,
        reason: str = "",
    ) -> bool:
        """Handle group add/invite request.

        Args:
            flag: Request flag from event
            sub_type: "add" or "invite"
            approve: Whether to approve
            reason: Rejection reason (if not approved)

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_add_request",
                {
                    "flag": flag,
                    "sub_type": sub_type,
                    "approve": approve,
                    "reason": reason,
                },
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to handle group request: {e}")
            return False

    # ==========================================================================
    # OneBot11 Standard APIs - System
    # ==========================================================================

    def get_status(self) -> dict[str, Any]:
        """Get bot running status.

        Returns:
            Status dict with online and good fields
        """
        try:
            return self._call_api("/get_status", {}) or {}
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return {"online": False, "good": False}

    def get_version_info(self) -> dict[str, Any]:
        """Get OneBot implementation version info.

        Returns:
            Version info dict
        """
        try:
            return self._call_api("/get_version_info", {}) or {}
        except Exception as e:
            self.logger.error(f"Failed to get version info: {e}")
            return {}

    def can_send_image(self) -> bool:
        """Check if bot can send images.

        Returns:
            True if can send images
        """
        try:
            data = self._call_api("/can_send_image", {})
            return data.get("yes", False) if data else False
        except Exception:
            return False

    def can_send_record(self) -> bool:
        """Check if bot can send voice messages.

        Returns:
            True if can send voice
        """
        try:
            data = self._call_api("/can_send_record", {})
            return data.get("yes", False) if data else False
        except Exception:
            return False

    # ==========================================================================
    # NapCat Extended APIs
    # ==========================================================================

    def send_poke(self, user_id: int, group_id: int | None = None) -> bool:
        """Send poke (戳一戳).

        Args:
            user_id: Target QQ number
            group_id: Group ID (None for private poke)

        Returns:
            True if successful
        """
        try:
            payload: dict[str, Any] = {"user_id": user_id}
            if group_id:
                payload["group_id"] = group_id
            self._call_api("/send_poke", payload)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send poke: {e}")
            return False

    def group_poke(self, group_id: int, user_id: int) -> bool:
        """Send group poke (群聊戳一戳).

        Args:
            group_id: Group number
            user_id: Target QQ number

        Returns:
            True if successful
        """
        try:
            self._call_api("/group_poke", {"group_id": group_id, "user_id": user_id})
            return True
        except Exception as e:
            self.logger.error(f"Failed to send group poke: {e}")
            return False

    def friend_poke(self, user_id: int) -> bool:
        """Send friend poke (私聊戳一戳).

        Args:
            user_id: Target QQ number

        Returns:
            True if successful
        """
        try:
            self._call_api("/friend_poke", {"user_id": user_id})
            return True
        except Exception as e:
            self.logger.error(f"Failed to send friend poke: {e}")
            return False

    def set_msg_emoji_like(self, message_id: int, emoji_id: str) -> bool:
        """React to a message with emoji.

        Args:
            message_id: Message ID
            emoji_id: Emoji ID

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_msg_emoji_like",
                {"message_id": message_id, "emoji_id": emoji_id},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set emoji reaction: {e}")
            return False

    def mark_msg_as_read(self, target: str) -> bool:
        """Mark messages as read.

        Args:
            target: "private:QQ号" or "group:群号"

        Returns:
            True if successful
        """
        try:
            user_id, group_id = self._parse_target(target)
            if user_id:
                self._call_api("/mark_private_msg_as_read", {"user_id": user_id})
            elif group_id:
                self._call_api("/mark_group_msg_as_read", {"group_id": group_id})
            else:
                return False
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark as read: {e}")
            return False

    def get_group_msg_history(
        self,
        group_id: int,
        message_seq: int = 0,
        count: int = 20,
    ) -> list[dict[str, Any]]:
        """Get group message history.

        Args:
            group_id: Group number
            message_seq: Starting message sequence (0 for latest)
            count: Number of messages to retrieve

        Returns:
            List of message dicts
        """
        try:
            data = self._call_api(
                "/get_group_msg_history",
                {"group_id": group_id, "message_seq": message_seq, "count": count},
            )
            return data.get("messages", []) if data else []
        except Exception as e:
            self.logger.error(f"Failed to get group history: {e}")
            return []

    def get_friend_msg_history(
        self,
        user_id: int,
        message_seq: int = 0,
        count: int = 20,
    ) -> list[dict[str, Any]]:
        """Get private message history.

        Args:
            user_id: Friend's QQ number
            message_seq: Starting message sequence (0 for latest)
            count: Number of messages to retrieve

        Returns:
            List of message dicts
        """
        try:
            data = self._call_api(
                "/get_friend_msg_history",
                {"user_id": user_id, "message_seq": message_seq, "count": count},
            )
            return data.get("messages", []) if data else []
        except Exception as e:
            self.logger.error(f"Failed to get friend history: {e}")
            return []

    def set_group_sign(self, group_id: int) -> bool:
        """Sign in to group (群签到).

        Args:
            group_id: Group number

        Returns:
            True if successful
        """
        try:
            self._call_api("/set_group_sign", {"group_id": str(group_id)})
            return True
        except Exception as e:
            self.logger.error(f"Failed to sign in group: {e}")
            return False

    def set_online_status(
        self,
        status: OnlineStatus | int,
        ext_status: int = 0,
        battery_status: int = 0,
    ) -> bool:
        """Set bot's online status.

        Args:
            status: Online status code
            ext_status: Extended status
            battery_status: Battery level

        Returns:
            True if successful
        """
        try:
            status_val = status.value if isinstance(status, OnlineStatus) else status
            self._call_api(
                "/set_online_status",
                {
                    "status": status_val,
                    "ext_status": ext_status,
                    "battery_status": battery_status,
                },
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set online status: {e}")
            return False

    def set_qq_avatar(self, file: str) -> bool:
        """Set bot's QQ avatar.

        Args:
            file: Image file path or URL

        Returns:
            True if successful
        """
        try:
            self._call_api("/set_qq_avatar", {"file": file})
            return True
        except Exception as e:
            self.logger.error(f"Failed to set avatar: {e}")
            return False

    def get_file(self, file_id: str) -> dict[str, Any]:
        """Get file information.

        Args:
            file_id: File ID

        Returns:
            File info dict with file, url, file_size, file_name
        """
        try:
            return self._call_api("/get_file", {"file_id": file_id}) or {}
        except Exception as e:
            self.logger.error(f"Failed to get file: {e}")
            return {}

    def translate_en2zh(self, words: list[str]) -> list[str]:
        """Translate English to Chinese (NapCat feature).

        Args:
            words: List of English words/phrases

        Returns:
            List of Chinese translations
        """
        try:
            data = self._call_api("/translate_en2zh", {"words": words})
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Failed to translate: {e}")
            return []

    # ==========================================================================
    # NapCat AI Voice APIs
    # ==========================================================================

    def get_ai_characters(self, group_id: int) -> list[dict[str, Any]]:
        """Get available AI voice characters.

        Args:
            group_id: Group number (required for API)

        Returns:
            List of character info dicts
        """
        if not self.config.enable_ai_voice:
            return []

        try:
            data = self._call_api("/get_ai_characters", {"group_id": group_id})
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Failed to get AI characters: {e}")
            return []

    def get_ai_record(
        self,
        character: str,
        group_id: int,
        text: str,
    ) -> str:
        """Convert text to AI voice.

        Args:
            character: AI character ID
            group_id: Group number
            text: Text to convert

        Returns:
            Voice file URL or empty string
        """
        if not self.config.enable_ai_voice:
            return ""

        try:
            data = self._call_api(
                "/get_ai_record",
                {"character": character, "group_id": group_id, "text": text},
            )
            return data.get("data", "") if data else ""
        except Exception as e:
            self.logger.error(f"Failed to get AI record: {e}")
            return ""

    def send_group_ai_record(
        self,
        group_id: int,
        character: str,
        text: str,
    ) -> SendResult:
        """Send AI voice message to group.

        Args:
            group_id: Group number
            character: AI character ID
            text: Text to convert to voice

        Returns:
            SendResult with message ID
        """
        if not self.config.enable_ai_voice:
            return SendResult.fail("AI voice not enabled")

        try:
            data = self._call_api(
                "/send_group_ai_record",
                {"group_id": group_id, "character": character, "text": text},
            )
            msg_id = data.get("message_id", "") if data else ""
            return SendResult.ok(str(msg_id), data)
        except Exception as e:
            return SendResult.fail(str(e))

    # ==========================================================================
    # Additional Message Types
    # ==========================================================================

    def send_file(self, file_path: str, target: str) -> SendResult:
        """Send a file message.

        Args:
            file_path: File path or URL
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status
        """
        message_id = str(uuid.uuid4())
        try:
            user_id, group_id = self._parse_target(target)
            if not user_id and not group_id:
                return SendResult.fail("Invalid target format")

            message_segments = [{"type": "file", "data": {"file": file_path}}]
            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)
            return SendResult.ok(message_id, result)
        except Exception as e:
            return SendResult.fail(str(e))

    def send_audio(self, audio_key: str, target: str) -> SendResult:
        """Send an audio/voice message.

        Args:
            audio_key: Audio file path or URL
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status
        """
        message_id = str(uuid.uuid4())
        try:
            user_id, group_id = self._parse_target(target)
            if not user_id and not group_id:
                return SendResult.fail("Invalid target format")

            message_segments = [{"type": "record", "data": {"file": audio_key}}]
            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)
            return SendResult.ok(message_id, result)
        except Exception as e:
            return SendResult.fail(str(e))

    def send_video(self, video_key: str, target: str) -> SendResult:
        """Send a video message.

        Args:
            video_key: Video file path or URL
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status
        """
        message_id = str(uuid.uuid4())
        try:
            user_id, group_id = self._parse_target(target)
            if not user_id and not group_id:
                return SendResult.fail("Invalid target format")

            message_segments = [{"type": "video", "data": {"file": video_key}}]
            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)
            return SendResult.ok(message_id, result)
        except Exception as e:
            return SendResult.fail(str(e))

    def send_at(self, user_id: int, target: str, text: str = "") -> SendResult:
        """Send an @mention message.

        Args:
            user_id: QQ number to mention (0 for @all)
            target: Target group
            text: Additional text after @mention

        Returns:
            SendResult with status
        """
        message_id = str(uuid.uuid4())
        try:
            _, group_id = self._parse_target(target)
            if not group_id:
                return SendResult.fail("@mention only works in groups")

            message_segments = [{"type": "at", "data": {"qq": str(user_id) if user_id else "all"}}]
            if text:
                message_segments.append({"type": "text", "data": {"text": f" {text}"}})

            result = self._send_onebot_message(message_id, None, group_id, message_segments)
            return SendResult.ok(message_id, result)
        except Exception as e:
            return SendResult.fail(str(e))

    def send_reply(
        self,
        reply_to_id: int,
        text: str,
        target: str,
    ) -> SendResult:
        """Send a reply message.

        Args:
            reply_to_id: Message ID to reply to
            text: Reply text
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status
        """
        message_id = str(uuid.uuid4())
        try:
            user_id, group_id = self._parse_target(target)
            if not user_id and not group_id:
                return SendResult.fail("Invalid target format")

            message_segments = [
                {"type": "reply", "data": {"id": str(reply_to_id)}},
                {"type": "text", "data": {"text": text}},
            ]
            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)
            return SendResult.ok(message_id, result)
        except Exception as e:
            return SendResult.fail(str(e))

    # ==========================================================================
    # NapCat Extended APIs - Group Announcements
    # ==========================================================================

    def get_group_notice(self, group_id: int) -> list[dict[str, Any]]:
        """Get group announcements.

        Args:
            group_id: Group number

        Returns:
            List of announcement dicts with sender_id, publish_time, content
        """
        try:
            data = self._call_api("/get_group_notice", {"group_id": group_id})
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Failed to get group notice: {e}")
            return []

    def send_group_notice(
        self,
        group_id: int,
        content: str,
        image: str = "",
    ) -> bool:
        """Send a group announcement.

        Args:
            group_id: Group number
            content: Announcement content
            image: Optional image URL or file path

        Returns:
            True if successful
        """
        try:
            payload: dict[str, Any] = {"group_id": group_id, "content": content}
            if image:
                payload["image"] = image
            self._call_api("/_send_group_notice", payload)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send group notice: {e}")
            return False

    def del_group_notice(self, group_id: int, notice_id: str) -> bool:
        """Delete a group announcement.

        Args:
            group_id: Group number
            notice_id: Announcement ID to delete

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/_del_group_notice",
                {"group_id": group_id, "notice_id": notice_id},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete group notice: {e}")
            return False

    # ==========================================================================
    # NapCat Extended APIs - Essence Messages
    # ==========================================================================

    def get_essence_msg_list(self, group_id: int) -> list[dict[str, Any]]:
        """Get essence/pinned messages in a group.

        Args:
            group_id: Group number

        Returns:
            List of essence message dicts
        """
        try:
            data = self._call_api("/get_essence_msg_list", {"group_id": group_id})
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Failed to get essence messages: {e}")
            return []

    def set_essence_msg(self, message_id: int) -> bool:
        """Set a message as essence/pinned.

        Args:
            message_id: Message ID to set as essence

        Returns:
            True if successful
        """
        try:
            self._call_api("/set_essence_msg", {"message_id": message_id})
            return True
        except Exception as e:
            self.logger.error(f"Failed to set essence message: {e}")
            return False

    def delete_essence_msg(self, message_id: int) -> bool:
        """Remove a message from essence/pinned.

        Args:
            message_id: Message ID to remove from essence

        Returns:
            True if successful
        """
        try:
            self._call_api("/delete_essence_msg", {"message_id": message_id})
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete essence message: {e}")
            return False

    # ==========================================================================
    # NapCat Extended APIs - Message Forwarding
    # ==========================================================================

    def forward_friend_single_msg(
        self,
        message_id: int,
        user_id: int,
    ) -> SendResult:
        """Forward a single message to a friend.

        Args:
            message_id: Message ID to forward
            user_id: Target friend QQ number

        Returns:
            SendResult with new message ID
        """
        try:
            data = self._call_api(
                "/forward_friend_single_msg",
                {"message_id": message_id, "user_id": user_id},
            )
            new_id = data.get("message_id", "") if data else ""
            return SendResult.ok(str(new_id), data)
        except Exception as e:
            return SendResult.fail(str(e))

    def forward_group_single_msg(
        self,
        message_id: int,
        group_id: int,
    ) -> SendResult:
        """Forward a single message to a group.

        Args:
            message_id: Message ID to forward
            group_id: Target group number

        Returns:
            SendResult with new message ID
        """
        try:
            data = self._call_api(
                "/forward_group_single_msg",
                {"message_id": message_id, "group_id": group_id},
            )
            new_id = data.get("message_id", "") if data else ""
            return SendResult.ok(str(new_id), data)
        except Exception as e:
            return SendResult.fail(str(e))

    # ==========================================================================
    # NapCat Extended APIs - File Operations
    # ==========================================================================

    def get_private_file_url(self, file_id: str) -> str:
        """Get private file download URL.

        Args:
            file_id: File ID from message

        Returns:
            File download URL or empty string
        """
        try:
            data = self._call_api("/get_private_file_url", {"file_id": file_id})
            return data.get("url", "") if data else ""
        except Exception as e:
            self.logger.error(f"Failed to get private file URL: {e}")
            return ""

    def move_group_file(
        self,
        group_id: int,
        file_id: str,
        parent_dir_id: str,
    ) -> bool:
        """Move a file within group files.

        Args:
            group_id: Group number
            file_id: File ID to move
            parent_dir_id: Target directory ID

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/move_group_file",
                {
                    "group_id": group_id,
                    "file_id": file_id,
                    "parent_dir_id": parent_dir_id,
                },
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to move group file: {e}")
            return False

    def rename_group_file(
        self,
        group_id: int,
        file_id: str,
        new_name: str,
    ) -> bool:
        """Rename a group file.

        Args:
            group_id: Group number
            file_id: File ID to rename
            new_name: New file name

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/rename_group_file",
                {
                    "group_id": group_id,
                    "file_id": file_id,
                    "new_name": new_name,
                },
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to rename group file: {e}")
            return False

    def trans_group_file(
        self,
        group_id: int,
        file_id: str,
    ) -> str:
        """Transfer group file to personal storage.

        Args:
            group_id: Group number
            file_id: File ID to transfer

        Returns:
            New file ID in personal storage or empty string
        """
        try:
            data = self._call_api(
                "/trans_group_file",
                {"group_id": group_id, "file_id": file_id},
            )
            return data.get("file_id", "") if data else ""
        except Exception as e:
            self.logger.error(f"Failed to transfer group file: {e}")
            return ""

    # ==========================================================================
    # NapCat Extended APIs - OCR & Image
    # ==========================================================================

    def ocr_image(self, image: str) -> list[dict[str, Any]]:
        """Perform OCR on an image.

        Args:
            image: Image URL or file path

        Returns:
            List of OCR result dicts with text and coordinates
        """
        try:
            data = self._call_api("/ocr_image", {"image": image})
            if data:
                return data.get("texts", []) if isinstance(data, dict) else data
            return []
        except Exception as e:
            self.logger.error(f"Failed to OCR image: {e}")
            return []

    def fetch_custom_face(self, count: int = 48) -> list[dict[str, Any]]:
        """Fetch custom face/emoji list.

        Args:
            count: Number of faces to fetch (max 48)

        Returns:
            List of custom face info dicts
        """
        try:
            data = self._call_api("/fetch_custom_face", {"count": min(count, 48)})
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Failed to fetch custom face: {e}")
            return []

    # ==========================================================================
    # NapCat Extended APIs - Profile & Status
    # ==========================================================================

    def get_profile_like(self) -> dict[str, Any]:
        """Get profile likes information.

        Returns:
            Profile like info dict
        """
        try:
            return self._call_api("/get_profile_like", {}) or {}
        except Exception as e:
            self.logger.error(f"Failed to get profile like: {e}")
            return {}

    def fetch_emoji_like(
        self,
        message_id: int,
        emoji_id: str,
        emoji_type: str = "1",
    ) -> list[dict[str, Any]]:
        """Fetch users who reacted with an emoji.

        Args:
            message_id: Message ID
            emoji_id: Emoji ID
            emoji_type: Emoji type

        Returns:
            List of user info dicts
        """
        try:
            data = self._call_api(
                "/fetch_emoji_like",
                {
                    "message_id": message_id,
                    "emoji_id": emoji_id,
                    "emoji_type": emoji_type,
                },
            )
            return data if isinstance(data, list) else []
        except Exception as e:
            self.logger.error(f"Failed to fetch emoji like: {e}")
            return []

    def set_input_status(self, user_id: int, event_type: int = 1) -> bool:
        """Set input status (typing indicator).

        Args:
            user_id: Target user QQ number
            event_type: Status type (1=typing, 0=stop)

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_input_status",
                {"user_id": user_id, "event_type": event_type},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set input status: {e}")
            return False

    def get_cookies(self, domain: str = "") -> str:
        """Get QQ cookies for a domain.

        Args:
            domain: Target domain (empty for default)

        Returns:
            Cookie string
        """
        try:
            data = self._call_api("/get_cookies", {"domain": domain})
            return data.get("cookies", "") if data else ""
        except Exception as e:
            self.logger.error(f"Failed to get cookies: {e}")
            return ""

    def get_clientkey(self) -> str:
        """Get client key.

        Returns:
            Client key string
        """
        try:
            data = self._call_api("/.get_clientkey", {})
            return data.get("clientkey", "") if data else ""
        except Exception as e:
            self.logger.error(f"Failed to get clientkey: {e}")
            return ""

    # ==========================================================================
    # NapCat Extended APIs - Extended Group Info
    # ==========================================================================

    def get_group_info_ex(self, group_id: int) -> dict[str, Any]:
        """Get extended group information.

        Args:
            group_id: Group number

        Returns:
            Extended group info dict
        """
        try:
            return self._call_api("/get_group_info_ex", {"group_id": group_id}) or {}
        except Exception as e:
            self.logger.error(f"Failed to get extended group info: {e}")
            return {}

    def set_group_portrait(self, group_id: int, file: str) -> bool:
        """Set group avatar/portrait.

        Args:
            group_id: Group number
            file: Image file path or URL

        Returns:
            True if successful
        """
        try:
            self._call_api(
                "/set_group_portrait",
                {"group_id": group_id, "file": file},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to set group portrait: {e}")
            return False

    def get_group_honor_info(
        self,
        group_id: int,
        honor_type: str = "all",
    ) -> dict[str, Any]:
        """Get group honor information.

        Args:
            group_id: Group number
            honor_type: Honor type (talkative, performer, legend, strong_newbie, emotion, all)

        Returns:
            Group honor info dict
        """
        try:
            return (
                self._call_api(
                    "/get_group_honor_info",
                    {"group_id": group_id, "type": honor_type},
                )
                or {}
            )
        except Exception as e:
            self.logger.error(f"Failed to get group honor info: {e}")
            return {}

    def get_group_at_all_remain(self, group_id: int) -> dict[str, Any]:
        """Get remaining @all count for today.

        Args:
            group_id: Group number

        Returns:
            Dict with can_at_all, remain_at_all_count_for_group, remain_at_all_count_for_uin
        """
        try:
            return self._call_api("/get_group_at_all_remain", {"group_id": group_id}) or {}
        except Exception as e:
            self.logger.error(f"Failed to get @all remain: {e}")
            return {}

    # ==========================================================================
    # Internal Helper Methods
    # ==========================================================================

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API endpoint.

        Args:
            endpoint: API endpoint path
            payload: Request payload

        Returns:
            Response data field

        Raises:
            Exception: If request fails
        """
        result = self._make_http_request(endpoint, payload)
        return result.get("data") if result else None

    # ==========================================================================
    # Async Support
    # ==========================================================================

    async def async_connect(self) -> None:
        """Connect async client to Napcat API."""
        if self._async_client is not None:
            return

        try:
            headers = {"Content-Type": "application/json"}
            if self.config.access_token:
                headers["Authorization"] = f"Bearer {self.config.access_token}"

            timeout = self.config.timeout or 10.0
            self._async_client = httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                base_url=self.config.http_url,
            )
            self.logger.info(f"Async connected to Napcat: {self.config.name}")
        except Exception as e:
            self.logger.error(f"Failed to async connect to Napcat: {e}", exc_info=True)
            raise

    async def async_disconnect(self) -> None:
        """Disconnect async client from Napcat API."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
        self.logger.info(f"Async disconnected from Napcat: {self.config.name}")

    async def __aenter__(self) -> NapcatProvider:
        """Async context manager entry."""
        await self.async_connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.async_disconnect()

    async def _async_call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API endpoint asynchronously.

        Args:
            endpoint: API endpoint path
            payload: Request payload

        Returns:
            Response data field

        Raises:
            Exception: If request fails
        """
        if not self._async_client:
            await self.async_connect()

        response = await self._async_client.post(endpoint, json=payload)
        response.raise_for_status()
        result = response.json()

        if result.get("status") != "ok":
            raise ValueError(f"OneBot API error: {result.get('msg', 'Unknown error')}")

        return result.get("data")

    async def async_send_text(self, text: str, target: str) -> SendResult:
        """Send a text message asynchronously.

        Args:
            text: Text content
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status and message ID
        """
        message_id = str(uuid.uuid4())

        try:
            user_id, group_id = self._parse_target(target)

            if not user_id and not group_id:
                return SendResult.fail("Invalid target format. Use 'private:QQ号' or 'group:群号'")

            message_segments = [{"type": "text", "data": {"text": text}}]

            if user_id:
                endpoint = "/send_private_msg"
                payload = {"user_id": user_id, "message": message_segments}
            else:
                endpoint = "/send_group_msg"
                payload = {"group_id": group_id, "message": message_segments}

            result = await self._async_call_api(endpoint, payload)

            self._log_message_send_result(
                success=True,
                message_type="text",
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
            )
            return SendResult.ok(message_id, result)

        except Exception as e:
            error_msg = str(e)
            self._log_message_send_result(
                success=False,
                message_type="text",
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
                error=error_msg,
            )
            return SendResult.fail(error_msg)

    async def async_send_image(self, image_key: str, target: str) -> SendResult:
        """Send an image message asynchronously.

        Args:
            image_key: Image URL or file path
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status and message ID
        """
        message_id = str(uuid.uuid4())

        try:
            user_id, group_id = self._parse_target(target)

            if not user_id and not group_id:
                return SendResult.fail("Invalid target format")

            message_segments = [{"type": "image", "data": {"file": image_key}}]

            if user_id:
                endpoint = "/send_private_msg"
                payload = {"user_id": user_id, "message": message_segments}
            else:
                endpoint = "/send_group_msg"
                payload = {"group_id": group_id, "message": message_segments}

            result = await self._async_call_api(endpoint, payload)
            return SendResult.ok(message_id, result)

        except Exception as e:
            return SendResult.fail(str(e))

    async def async_send_reply(
        self,
        reply_to_id: int,
        text: str,
        target: str,
    ) -> SendResult:
        """Send a reply message asynchronously.

        Args:
            reply_to_id: Message ID to reply to
            text: Reply text
            target: Target in format "private:QQ号" or "group:群号"

        Returns:
            SendResult with status
        """
        message_id = str(uuid.uuid4())

        try:
            user_id, group_id = self._parse_target(target)

            if not user_id and not group_id:
                return SendResult.fail("Invalid target format")

            message_segments = [
                {"type": "reply", "data": {"id": str(reply_to_id)}},
                {"type": "text", "data": {"text": text}},
            ]

            if user_id:
                endpoint = "/send_private_msg"
                payload = {"user_id": user_id, "message": message_segments}
            else:
                endpoint = "/send_group_msg"
                payload = {"group_id": group_id, "message": message_segments}

            result = await self._async_call_api(endpoint, payload)
            return SendResult.ok(message_id, result)

        except Exception as e:
            return SendResult.fail(str(e))

    async def async_delete_msg(self, message_id: int) -> bool:
        """Recall/delete a message asynchronously.

        Args:
            message_id: Message ID to delete

        Returns:
            True if successful
        """
        try:
            await self._async_call_api("/delete_msg", {"message_id": message_id})
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete message {message_id}: {e}")
            return False

    async def async_get_msg(self, message_id: int) -> QQMessage | None:
        """Get message details asynchronously.

        Args:
            message_id: Message ID

        Returns:
            QQMessage object or None if not found
        """
        try:
            data = await self._async_call_api("/get_msg", {"message_id": message_id})
            if data:
                return QQMessage(
                    message_id=data.get("message_id", message_id),
                    message_type=data.get("message_type", ""),
                    sender_id=data.get("sender", {}).get("user_id", 0),
                    sender_nickname=data.get("sender", {}).get("nickname", ""),
                    content=data.get("message", []),
                    time=data.get("time", 0),
                    group_id=data.get("group_id"),
                )
        except Exception as e:
            self.logger.error(f"Failed to get message {message_id}: {e}")
        return None

    async def async_get_group_info(
        self,
        group_id: int,
        no_cache: bool = False,
    ) -> QQGroupInfo | None:
        """Get group information asynchronously.

        Args:
            group_id: Group number
            no_cache: Whether to bypass cache

        Returns:
            QQGroupInfo object or None
        """
        try:
            data = await self._async_call_api(
                "/get_group_info",
                {"group_id": group_id, "no_cache": no_cache},
            )
            if data:
                return QQGroupInfo(
                    group_id=data.get("group_id", group_id),
                    group_name=data.get("group_name", ""),
                    member_count=data.get("member_count", 0),
                    max_member_count=data.get("max_member_count", 0),
                )
        except Exception as e:
            self.logger.error(f"Failed to get group info: {e}")
        return None

    async def async_get_group_member_list(
        self,
        group_id: int,
    ) -> list[QQGroupMember]:
        """Get all members of a group asynchronously.

        Args:
            group_id: Group number

        Returns:
            List of QQGroupMember objects
        """
        try:
            data = await self._async_call_api(
                "/get_group_member_list",
                {"group_id": group_id},
            )
            if data and isinstance(data, list):
                return [
                    QQGroupMember(
                        group_id=group_id,
                        user_id=m.get("user_id", 0),
                        nickname=m.get("nickname", ""),
                        card=m.get("card", ""),
                        role=m.get("role", "member"),
                    )
                    for m in data
                ]
        except Exception as e:
            self.logger.error(f"Failed to get group member list: {e}")
        return []

    async def async_set_group_ban(
        self,
        group_id: int,
        user_id: int,
        duration: int = 1800,
    ) -> bool:
        """Ban/mute a group member asynchronously.

        Args:
            group_id: Group number
            user_id: Member to ban
            duration: Ban duration in seconds (0 to unban)

        Returns:
            True if successful
        """
        try:
            await self._async_call_api(
                "/set_group_ban",
                {"group_id": group_id, "user_id": user_id, "duration": duration},
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to ban user {user_id}: {e}")
            return False

    async def async_set_group_kick(
        self,
        group_id: int,
        user_id: int,
        reject_add_request: bool = False,
    ) -> bool:
        """Kick a member from group asynchronously.

        Args:
            group_id: Group number
            user_id: Member to kick
            reject_add_request: Whether to reject future join requests

        Returns:
            True if successful
        """
        try:
            await self._async_call_api(
                "/set_group_kick",
                {
                    "group_id": group_id,
                    "user_id": user_id,
                    "reject_add_request": reject_add_request,
                },
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to kick user {user_id}: {e}")
            return False

    async def async_send_poke(
        self,
        user_id: int,
        group_id: int | None = None,
    ) -> bool:
        """Send poke asynchronously.

        Args:
            user_id: Target QQ number
            group_id: Group ID (None for private poke)

        Returns:
            True if successful
        """
        try:
            payload: dict[str, Any] = {"user_id": user_id}
            if group_id:
                payload["group_id"] = group_id
            await self._async_call_api("/send_poke", payload)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send poke: {e}")
            return False

    async def async_get_group_msg_history(
        self,
        group_id: int,
        message_seq: int = 0,
        count: int = 20,
    ) -> list[dict[str, Any]]:
        """Get group message history asynchronously.

        Args:
            group_id: Group number
            message_seq: Starting message sequence (0 for latest)
            count: Number of messages to retrieve

        Returns:
            List of message dicts
        """
        try:
            data = await self._async_call_api(
                "/get_group_msg_history",
                {"group_id": group_id, "message_seq": message_seq, "count": count},
            )
            return data.get("messages", []) if data else []
        except Exception as e:
            self.logger.error(f"Failed to get group history: {e}")
            return []

    async def async_ocr_image(self, image: str) -> list[dict[str, Any]]:
        """Perform OCR on an image asynchronously.

        Args:
            image: Image URL or file path

        Returns:
            List of OCR result dicts with text and coordinates
        """
        try:
            data = await self._async_call_api("/ocr_image", {"image": image})
            if data:
                return data.get("texts", []) if isinstance(data, dict) else data
            return []
        except Exception as e:
            self.logger.error(f"Failed to OCR image: {e}")
            return []
