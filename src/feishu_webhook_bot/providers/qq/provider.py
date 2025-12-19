"""QQ Napcat provider implementation based on OneBot11 protocol.

This module provides the main NapcatProvider class that combines
all API functionality through mixins.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from ...core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ...core.logger import get_logger
from ...core.message_tracker import MessageStatus, MessageTracker
from ...core.provider import BaseProvider, Message, MessageType, SendResult
from ..common.http import HTTPProviderMixin
from ..common.utils import create_response_validator, log_message_result
from .api import (
    OneBotGroupAdminMixin,
    OneBotGroupInfoMixin,
    OneBotMessageMixin,
    OneBotRequestMixin,
    OneBotSystemMixin,
    OneBotUserMixin,
)
from .async_provider import AsyncNapcatMixin
from .config import NapcatProviderConfig
from .napcat import (
    NapcatAIVoiceMixin,
    NapcatFileMixin,
    NapcatGroupExtMixin,
    NapcatMessageExtMixin,
    NapcatPokeMixin,
)

logger = get_logger(__name__)


class NapcatProvider(
    BaseProvider,
    HTTPProviderMixin,
    # OneBot11 Standard APIs
    OneBotMessageMixin,
    OneBotUserMixin,
    OneBotGroupInfoMixin,
    OneBotGroupAdminMixin,
    OneBotRequestMixin,
    OneBotSystemMixin,
    # NapCat Extended APIs
    NapcatPokeMixin,
    NapcatAIVoiceMixin,
    NapcatMessageExtMixin,
    NapcatGroupExtMixin,
    NapcatFileMixin,
    # Async Support
    AsyncNapcatMixin,
):
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
            name="my_qq_bot",
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
            config: Napcat provider configuration.
            message_tracker: Optional message tracker for delivery tracking.
            circuit_breaker_config: Optional circuit breaker configuration.
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
            message: Message to send.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status and message ID.
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
            text: Text content.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status and message ID.
        """
        message_id = str(uuid.uuid4())

        try:
            user_id, group_id = self._parse_target(target)

            if not user_id and not group_id:
                return SendResult.fail("Invalid target format. Use 'private:QQ号' or 'group:群号'")

            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, target, text)

            message_segments = [{"type": "text", "data": {"text": text}}]
            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            log_message_result(
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
            log_message_result(
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
            card: Card data.
            target: Target identifier.

        Returns:
            SendResult with failure status.
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
            title: Text title/header.
            content: Content structure (converted to formatted text).
            target: Target in format "private:QQ号" or "group:群号".
            language: Language code (ignored for OneBot11).

        Returns:
            SendResult with status and message ID.
        """
        message_id = str(uuid.uuid4())

        try:
            user_id, group_id = self._parse_target(target)

            if not user_id and not group_id:
                return SendResult.fail("Invalid target format. Use 'private:QQ号' or 'group:群号'")

            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, target, content)

            message_segments = self._convert_rich_text_to_segments(title, content)
            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            log_message_result(
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
            log_message_result(
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
            image_key: Image URL or file path.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status and message ID.
        """
        message_id = str(uuid.uuid4())

        try:
            user_id, group_id = self._parse_target(target)

            if not user_id and not group_id:
                return SendResult.fail("Invalid target format. Use 'private:QQ号' or 'group:群号'")

            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, target, image_key)

            message_segments = [{"type": "image", "data": {"file": image_key}}]
            result = self._send_onebot_message(message_id, user_id, group_id, message_segments)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            log_message_result(
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
            log_message_result(
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

    # Additional message types

    def send_file(self, file_path: str, target: str) -> SendResult:
        """Send a file message.

        Args:
            file_path: File path or URL.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status.
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
            audio_key: Audio file path or URL.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status.
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
            video_key: Video file path or URL.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status.
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
            user_id: QQ number to mention (0 for @all).
            target: Target group.
            text: Additional text after @mention.

        Returns:
            SendResult with status.
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
            reply_to_id: Message ID to reply to.
            text: Reply text.
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            SendResult with status.
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

    # Internal methods

    def _parse_target(self, target: str) -> tuple[int | None, int | None]:
        """Parse target format to extract user_id and group_id.

        Args:
            target: Target in format "private:QQ号" or "group:群号".

        Returns:
            Tuple of (user_id, group_id) - one will be None.
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
            title: Text title.
            content: Content structure.

        Returns:
            List of OneBot message segments.
        """
        segments: list[dict[str, Any]] = []

        if title:
            segments.append({"type": "text", "data": {"text": f"{title}\n"}})

        for paragraph in content:
            paragraph_text = ""

            for element in paragraph:
                if isinstance(element, dict):
                    if element.get("type") == "text":
                        paragraph_text += element.get("text", "")
                    elif element.get("type") == "at":
                        user_id = element.get("user_id")
                        if user_id:
                            paragraph_text += f"[CQ:at,qq={user_id}]"
                    elif element.get("type") == "link":
                        text = element.get("text", "")
                        href = element.get("href", "")
                        paragraph_text += f"{text}({href})"

            if paragraph_text:
                segments.append({"type": "text", "data": {"text": paragraph_text + "\n"}})

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
            message_id: Unique message identifier.
            user_id: QQ user ID for private messages.
            group_id: QQ group ID for group messages.
            message_segments: OneBot message segments.

        Returns:
            API response data.

        Raises:
            Exception: If request fails.
        """
        if not self._client:
            raise RuntimeError("Provider not connected. Call connect() first.")

        if user_id:
            endpoint = "/send_private_msg"
            payload = {"user_id": user_id, "message": message_segments}
        elif group_id:
            endpoint = "/send_group_msg"
            payload = {"group_id": group_id, "message": message_segments}
        else:
            raise ValueError("Either user_id or group_id must be specified")

        def _make_request() -> dict[str, Any]:
            return self._circuit_breaker.call(self._make_http_request, endpoint, payload)

        return _make_request()

    def _make_http_request(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make actual HTTP request with retry logic.

        Args:
            endpoint: API endpoint path.
            payload: Request payload.

        Returns:
            Response data.

        Raises:
            Exception: If all retries fail.
        """
        if not self._client:
            raise RuntimeError("HTTP client not initialized")

        validator = create_response_validator("status", "ok", "msg")

        return self._http_request_with_retry(
            client=self._client,
            url=endpoint,
            payload=payload,
            retry_policy=self.config.retry,
            provider_name=self.name,
            provider_type=self.provider_type,
            response_validator=validator,
        )

    def _call_api(self, endpoint: str, payload: dict[str, Any]) -> Any:
        """Call OneBot API endpoint.

        Args:
            endpoint: API endpoint path.
            payload: Request payload.

        Returns:
            Response data field.

        Raises:
            Exception: If request fails.
        """
        result = self._make_http_request(endpoint, payload)
        return result.get("data") if result else None

    def get_capabilities(self) -> dict[str, bool]:
        """Get supported message types.

        Returns:
            Dictionary of capability flags.
        """
        return {
            "text": True,
            "rich_text": True,
            "card": False,
            "image": True,
            "file": True,
            "audio": True,
            "video": True,
            "forward": True,
            "poke": True,
        }
