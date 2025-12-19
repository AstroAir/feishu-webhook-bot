"""Enhanced base provider with integrated tracking and circuit breaker.

This module provides an enhanced base class that combines common functionality
used across all provider implementations.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from ...core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ...core.logger import get_logger
from ...core.message_tracker import MessageStatus, MessageTracker
from ...core.provider import BaseProvider, Message, MessageType, ProviderConfig, SendResult
from .http import HTTPProviderMixin
from .utils import log_message_result

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


class EnhancedBaseProvider(BaseProvider, HTTPProviderMixin):
    """Enhanced base provider with integrated tracking and circuit breaker.

    This class extends BaseProvider with:
    - Message tracking integration
    - Circuit breaker pattern
    - Unified message sending template
    - Consistent logging

    Subclasses should implement:
    - connect(): Establish connection
    - disconnect(): Clean up connection
    - _do_send_message(): Actual message sending logic
    - get_capabilities(): Return supported features

    Example:
        class MyProvider(EnhancedBaseProvider):
            def __init__(self, config: MyProviderConfig):
                super().__init__(config)

            def _do_send_message(
                self,
                message_type: str,
                content: Any,
                target: str,
            ) -> dict[str, Any]:
                # Implement actual sending
                return self._call_api(endpoint, payload)
    """

    def __init__(
        self,
        config: ProviderConfig,
        message_tracker: MessageTracker | None = None,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        """Initialize enhanced provider.

        Args:
            config: Provider configuration.
            message_tracker: Optional message tracker for delivery tracking.
            circuit_breaker_config: Optional circuit breaker configuration.
        """
        super().__init__(config)
        self._message_tracker = message_tracker
        self._circuit_breaker = CircuitBreaker(
            f"{config.provider_type}_{config.name}",
            circuit_breaker_config or CircuitBreakerConfig(),
        )

    def _generate_message_id(self) -> str:
        """Generate a unique message ID.

        Returns:
            UUID string.
        """
        return str(uuid.uuid4())

    def _send_with_tracking(
        self,
        message_type: str,
        content: Any,
        target: str,
        send_func: Callable[[], dict[str, Any]],
    ) -> SendResult:
        """Send message with tracking, logging, and error handling.

        This is a template method that handles common send logic:
        1. Generate message ID
        2. Track message (if tracker enabled)
        3. Execute send function
        4. Update tracking status
        5. Log result

        Args:
            message_type: Type of message (text, image, etc.).
            content: Message content for tracking.
            target: Target destination.
            send_func: Function that performs actual sending.
                Should return API response dict.

        Returns:
            SendResult with status and message ID.
        """
        message_id = self._generate_message_id()

        try:
            # Track message if tracker enabled
            if self._message_tracker:
                self._message_tracker.track(
                    message_id,
                    self.provider_type,
                    target,
                    content,
                )

            # Execute send with circuit breaker
            result = self._circuit_breaker.call(send_func)

            # Update tracking status
            if self._message_tracker:
                self._message_tracker.update_status(message_id, MessageStatus.SENT)

            # Log success
            log_message_result(
                success=True,
                message_type=message_type,
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
            )

            return SendResult.ok(message_id, result)

        except Exception as e:
            error_msg = str(e)

            # Log failure
            log_message_result(
                success=False,
                message_type=message_type,
                message_id=message_id,
                target=target,
                provider_name=self.name,
                provider_type=self.provider_type,
                error=error_msg,
            )

            # Update tracking status
            if self._message_tracker:
                self._message_tracker.update_status(
                    message_id,
                    MessageStatus.FAILED,
                    error=error_msg,
                )

            return SendResult.fail(error_msg)

    def send_message(self, message: Message, target: str) -> SendResult:
        """Send a message with automatic type detection.

        Override this method to handle message type routing.

        Args:
            message: Message to send.
            target: Target destination.

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
        elif message.type == MessageType.CARD:
            return self.send_card(message.content, target)
        elif message.type == MessageType.IMAGE:
            return self.send_image(message.content, target)
        else:
            return SendResult.fail(f"Unsupported message type: {message.type}")

    def send_text(self, text: str, target: str) -> SendResult:
        """Send a text message.

        Subclasses should override this method.

        Args:
            text: Text content.
            target: Target destination.

        Returns:
            SendResult with status and message ID.
        """
        raise NotImplementedError("Subclasses must implement send_text")

    def send_card(self, card: dict[str, Any], target: str) -> SendResult:
        """Send a card message.

        Subclasses should override this method.

        Args:
            card: Card content.
            target: Target destination.

        Returns:
            SendResult with status and message ID.
        """
        raise NotImplementedError("Subclasses must implement send_card")

    def send_rich_text(
        self,
        title: str,
        content: list[list[dict[str, Any]]],
        target: str,
        language: str = "zh_cn",
    ) -> SendResult:
        """Send a rich text message.

        Subclasses should override this method.

        Args:
            title: Message title.
            content: Rich text content structure.
            target: Target destination.
            language: Language code.

        Returns:
            SendResult with status and message ID.
        """
        raise NotImplementedError("Subclasses must implement send_rich_text")

    def send_image(self, image_key: str, target: str) -> SendResult:
        """Send an image message.

        Subclasses should override this method.

        Args:
            image_key: Image key/URL/path.
            target: Target destination.

        Returns:
            SendResult with status and message ID.
        """
        raise NotImplementedError("Subclasses must implement send_image")
