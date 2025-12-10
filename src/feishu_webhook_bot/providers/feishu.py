"""Feishu provider implementation for multi-platform messaging support."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from typing import Any

import httpx
from pydantic import Field

from ..core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ..core.logger import get_logger
from ..core.message_tracker import MessageStatus, MessageTracker
from ..core.provider import BaseProvider, Message, MessageType, ProviderConfig, SendResult
from .base_http import HTTPProviderMixin

logger = get_logger(__name__)


class FeishuProviderConfig(ProviderConfig):
    """Configuration for Feishu provider."""

    provider_type: str = Field(default="feishu", description="Provider type")
    url: str = Field(..., description="Feishu webhook URL")
    secret: str | None = Field(default=None, description="Webhook secret for HMAC-SHA256 signing")
    headers: dict[str, str] = Field(default_factory=dict, description="Additional HTTP headers")


class FeishuProvider(BaseProvider, HTTPProviderMixin):
    """Feishu message provider implementation.

    Supports sending:
    - Text messages
    - Rich text messages (post format)
    - Interactive cards (JSON v2.0)
    - Images
    """

    def __init__(
        self,
        config: FeishuProviderConfig,
        message_tracker: MessageTracker | None = None,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        """Initialize Feishu provider.

        Args:
            config: Feishu provider configuration
            message_tracker: Optional message tracker for delivery tracking
            circuit_breaker_config: Optional circuit breaker configuration
        """
        super().__init__(config)
        self.config: FeishuProviderConfig = config
        self._client: httpx.Client | None = None
        self._message_tracker = message_tracker
        self._circuit_breaker = CircuitBreaker(
            f"feishu_{config.name}",
            circuit_breaker_config or CircuitBreakerConfig(),
        )

    def connect(self) -> None:
        """Connect to Feishu API."""
        if self._connected:
            return

        try:
            headers = {
                "Content-Type": "application/json",
                **(self.config.headers or {}),
            }
            timeout = self.config.timeout or 10.0
            self._client = httpx.Client(
                timeout=timeout,
                headers=headers,
            )
            self._connected = True
            self.logger.info(f"Connected to Feishu webhook: {self.config.name}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Feishu: {e}", exc_info=True)
            raise

    def disconnect(self) -> None:
        """Disconnect from Feishu API."""
        if self._client:
            self._client.close()
        self._connected = False
        self.logger.info(f"Disconnected from Feishu: {self.config.name}")

    def send_message(self, message: Message, target: str) -> SendResult:
        """Send a message with automatic type detection.

        Args:
            message: Message to send
            target: Target webhook URL (overrides config URL if provided)

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
        elif message.type == MessageType.CARD:
            return self.send_card(message.content, target)
        elif message.type == MessageType.IMAGE:
            return self.send_image(message.content, target)
        else:
            return SendResult.fail(f"Unsupported message type: {message.type}")

    def send_text(self, text: str, target: str) -> SendResult:
        """Send a text message.

        Args:
            text: Text content
            target: Target webhook URL or identifier

        Returns:
            SendResult with status and message ID
        """
        message_id = str(uuid.uuid4())
        url = target or self.config.url

        try:
            # Track message if tracker enabled
            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, url, text)

            payload = {
                "msg_type": "text",
                "content": {
                    "text": text,
                },
            }

            result = self._send_request(url, payload)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            self._log_message_send_result(
                success=True,
                message_type="text",
                message_id=message_id,
                target=url,
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
                target=url,
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
        """Send an interactive card message.

        Args:
            card: Card JSON structure (v2.0 format)
            target: Target webhook URL or identifier

        Returns:
            SendResult with status and message ID
        """
        message_id = str(uuid.uuid4())
        url = target or self.config.url

        try:
            # Track message if tracker enabled
            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, url, card)

            payload = {
                "msg_type": "interactive",
                "card": card,
            }

            result = self._send_request(url, payload)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            self._log_message_send_result(
                success=True,
                message_type="card",
                message_id=message_id,
                target=url,
                provider_name=self.name,
                provider_type=self.provider_type,
            )
            return SendResult.ok(message_id, result)

        except Exception as e:
            error_msg = str(e)
            self._log_message_send_result(
                success=False,
                message_type="card",
                message_id=message_id,
                target=url,
                provider_name=self.name,
                provider_type=self.provider_type,
                error=error_msg,
            )

            if self._message_tracker:
                self._message_tracker.update_status(
                    message_id, MessageStatus.FAILED, error=error_msg
                )

            return SendResult.fail(error_msg)

    def send_rich_text(
        self,
        title: str,
        content: list[list[dict[str, Any]]],
        target: str,
        language: str = "zh_cn",
    ) -> SendResult:
        """Send a rich text (post) message.

        Args:
            title: Post title
            content: Post content (list of paragraphs with elements)
            target: Target webhook URL or identifier
            language: Language code (default: zh_cn)

        Returns:
            SendResult with status and message ID
        """
        message_id = str(uuid.uuid4())
        url = target or self.config.url

        try:
            # Track message if tracker enabled
            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, url, content)

            payload = {
                "msg_type": "post",
                "content": {
                    "post": {
                        language: {
                            "title": title,
                            "content": content,
                        }
                    }
                },
            }

            result = self._send_request(url, payload)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            self._log_message_send_result(
                success=True,
                message_type="rich_text",
                message_id=message_id,
                target=url,
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
                target=url,
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
        """Send an image message.

        Args:
            image_key: Feishu image key (from file upload API)
            target: Target webhook URL or identifier

        Returns:
            SendResult with status and message ID
        """
        message_id = str(uuid.uuid4())
        url = target or self.config.url

        try:
            # Track message if tracker enabled
            if self._message_tracker:
                self._message_tracker.track(message_id, self.provider_type, url, image_key)

            payload = {
                "msg_type": "image",
                "content": {
                    "image_key": image_key,
                },
            }

            result = self._send_request(url, payload)

            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            self._log_message_send_result(
                success=True,
                message_type="image",
                message_id=message_id,
                target=url,
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
                target=url,
                provider_name=self.name,
                provider_type=self.provider_type,
                error=error_msg,
            )

            if self._message_tracker:
                self._message_tracker.update_status(
                    message_id, MessageStatus.FAILED, error=error_msg
                )

            return SendResult.fail(error_msg)

    def _send_request(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send HTTP request with circuit breaker and retry logic.

        Args:
            url: Target webhook URL
            payload: Request payload

        Returns:
            Response data

        Raises:
            Exception: If request fails or circuit breaker is open
        """
        if not self._client:
            raise RuntimeError("Provider not connected. Call connect() first.")

        # Add signature if secret is configured
        if self.config.secret:
            timestamp = int(time.time())
            sign = self._generate_sign(timestamp)
            payload["timestamp"] = str(timestamp)
            payload["sign"] = sign

        # Wrap with circuit breaker
        def _make_request() -> dict[str, Any]:
            return self._circuit_breaker.call(self._make_http_request, url, payload)

        return _make_request()

    def _make_http_request(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make actual HTTP request with retry logic.

        Args:
            url: Target URL
            payload: Request payload

        Returns:
            Response data

        Raises:
            Exception: If all retries fail
        """
        if not self._client:
            raise RuntimeError("HTTP client not initialized")

        def _validate_feishu_response(result: dict[str, Any]) -> None:
            """Validate Feishu API response."""
            if result.get("code") != 0:
                raise ValueError(
                    f"Feishu API error: {result.get('msg', 'Unknown error')}"
                )

        return self._http_request_with_retry(
            client=self._client,
            url=url,
            payload=payload,
            retry_policy=self.config.retry,
            provider_name=self.name,
            provider_type=self.provider_type,
            response_validator=_validate_feishu_response,
        )

    def _generate_sign(self, timestamp: int) -> str:
        """Generate HMAC-SHA256 signature for webhook security.

        Args:
            timestamp: Current timestamp in seconds

        Returns:
            Base64-encoded signature string
        """
        if not self.config.secret:
            return ""

        string_to_sign = f"{timestamp}\n{self.config.secret}"
        hmac_code = hmac.new(
            self.config.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        return base64.b64encode(hmac_code).decode("utf-8")

    def get_capabilities(self) -> dict[str, bool]:
        """Get supported message types.

        Returns:
            Dictionary of capability flags
        """
        return {
            "text": True,
            "rich_text": True,
            "card": True,
            "image": True,
            "file": False,
            "audio": False,
            "video": False,
        }
