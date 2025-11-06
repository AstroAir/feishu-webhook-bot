"""Feishu Webhook Client for sending messages.

This module implements the Feishu webhook API client with support for:
- Text messages
- Rich text messages
- Interactive cards (JSON v2.0)
- Image messages
- Security signing (HMAC-SHA256)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from datetime import datetime
from typing import Any

import httpx

from .config import WebhookConfig
from .logger import get_logger

logger = get_logger("client")


class MessageType:
    """Feishu message types."""

    TEXT = "text"
    POST = "post"
    INTERACTIVE = "interactive"
    IMAGE = "image"
    SHARE_CHAT = "share_chat"


class FeishuWebhookClient:
    """Client for sending messages via Feishu webhook.

    This client supports all major Feishu message types and implements
    security signing for protected webhooks.

    Example:
        ```python
        from feishu_webhook_bot.core import FeishuWebhookClient, WebhookConfig

        config = WebhookConfig(
            url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
            secret="your-secret"
        )
        client = FeishuWebhookClient(config)

        # Send text message
        client.send_text("Hello, Feishu!")

        # Send interactive card
        card = {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": "Title"}},
            "elements": [...]
        }
        client.send_card(card)
        ```
    """

    def __init__(self, config: WebhookConfig, timeout: float = 10.0):
        """Initialize the webhook client.

        Args:
            config: Webhook configuration
            timeout: Request timeout in seconds
        """
        self.config = config
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> FeishuWebhookClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _generate_sign(self, timestamp: int) -> str:
        """Generate HMAC-SHA256 signature for webhook security.

        Args:
            timestamp: Current timestamp in seconds

        Returns:
            Base64-encoded signature string

        Raises:
            ValueError: If secret is not configured
        """
        if not self.config.secret:
            raise ValueError("Webhook secret is required for signing")

        # Concatenate timestamp and secret
        string_to_sign = f"{timestamp}\n{self.config.secret}"

        # Generate HMAC-SHA256 signature
        hmac_code = hmac.new(
            self.config.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        # Base64 encode
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign

    def _send_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a message to the webhook.

        Args:
            payload: Message payload

        Returns:
            Response from Feishu API

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If response indicates error
        """
        # Add timestamp and signature if secret is configured
        if self.config.secret:
            timestamp = int(time.time())
            sign = self._generate_sign(timestamp)
            payload["timestamp"] = str(timestamp)
            payload["sign"] = sign

        logger.debug(f"Sending message to webhook: {self.config.name}")

        try:
            response = self._client.post(
                self.config.url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()

            # Check Feishu API response
            if result.get("code") != 0:
                error_msg = result.get("msg", "Unknown error")
                logger.error(f"Feishu API error: {error_msg}")
                raise ValueError(f"Feishu API error: {error_msg}")

            logger.info(f"Message sent successfully via webhook: {self.config.name}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending message: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    def send_text(self, text: str) -> dict[str, Any]:
        """Send a simple text message.

        Args:
            text: Text content to send

        Returns:
            Response from Feishu API

        Example:
            ```python
            client.send_text("Hello, world!")
            ```
        """
        payload = {"msg_type": MessageType.TEXT, "content": {"text": text}}
        return self._send_message(payload)

    def send_rich_text(
        self,
        title: str,
        content: list[list[dict[str, Any]]],
        language: str = "zh_cn",
    ) -> dict[str, Any]:
        """Send a rich text message with formatting.

        Rich text supports multiple elements like text, links, @mentions, and images.

        Args:
            title: Message title
            content: Rich text content as nested lists
            language: Language code (zh_cn, en_us, ja_jp, etc.)

        Returns:
            Response from Feishu API

        Example:
            ```python
            content = [
                [
                    {"tag": "text", "text": "Hello "},
                    {"tag": "a", "text": "link", "href": "https://example.com"},
                ]
            ]
            client.send_rich_text("Title", content)
            ```
        """
        payload = {
            "msg_type": MessageType.POST,
            "content": {"post": {language: {"title": title, "content": content}}},
        }
        return self._send_message(payload)

    def send_card(self, card: dict[str, Any] | str) -> dict[str, Any]:
        """Send an interactive card message.

        Supports both Card JSON v1.0 and v2.0 formats.

        Args:
            card: Card JSON structure (dict or JSON string)

        Returns:
            Response from Feishu API

        Example:
            ```python
            card = {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "Card Title"
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "plain_text",
                            "content": "This is card content"
                        }
                    }
                ]
            }
            client.send_card(card)
            ```
        """
        if isinstance(card, str):
            import json

            card = json.loads(card)

        payload = {"msg_type": MessageType.INTERACTIVE, "card": card}
        return self._send_message(payload)

    def send_card_v2(
        self,
        header: dict[str, Any] | None = None,
        elements: list[dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a Card JSON v2.0 message with structured parameters.

        This is a convenience method for building Card v2.0 messages.

        Args:
            header: Card header configuration
            elements: List of card elements
            config: Card configuration (optional)

        Returns:
            Response from Feishu API

        Example:
            ```python
            header = {
                "title": {
                    "tag": "plain_text",
                    "content": "Notification"
                },
                "template": "blue"
            }
            elements = [
                {
                    "tag": "markdown",
                    "content": "**Bold text** and *italic*"
                }
            ]
            client.send_card_v2(header=header, elements=elements)
            ```
        """
        card: dict[str, Any] = {"schema": "2.0"}

        if config:
            card["config"] = config
        if header:
            card["header"] = header
        if elements:
            card["elements"] = elements

        return self.send_card(card)

    def send_image(self, image_key: str) -> dict[str, Any]:
        """Send an image message.

        Note: The image must be uploaded to Feishu first to get an image_key.

        Args:
            image_key: Feishu image key

        Returns:
            Response from Feishu API

        Example:
            ```python
            # After uploading image to Feishu
            client.send_image("img_v2_xxxxx")
            ```
        """
        payload = {"msg_type": MessageType.IMAGE, "content": {"image_key": image_key}}
        return self._send_message(payload)


class CardBuilder:
    """Helper class for building Feishu interactive cards.

    This builder provides a fluent interface for constructing Card JSON v2.0
    structures without manually creating nested dictionaries.

    Example:
        ```python
        card = (
            CardBuilder()
            .set_header("Title", template="blue")
            .add_markdown("**Bold** content")
            .add_divider()
            .add_button("Click Me", url="https://example.com")
            .build()
        )
        client.send_card(card)
        ```
    """

    def __init__(self):
        """Initialize card builder."""
        self.card: dict[str, Any] = {"schema": "2.0", "elements": []}

    def set_config(self, **kwargs: Any) -> CardBuilder:
        """Set card configuration.

        Args:
            **kwargs: Configuration options (wide_screen_mode, enable_forward, etc.)

        Returns:
            Self for chaining
        """
        if "config" not in self.card:
            self.card["config"] = {}
        self.card["config"].update(kwargs)
        return self

    def set_header(
        self, title: str, template: str = "blue", subtitle: str | None = None
    ) -> CardBuilder:
        """Set card header.

        Args:
            title: Header title
            template: Color template (blue, red, green, etc.)
            subtitle: Optional subtitle

        Returns:
            Self for chaining
        """
        header: dict[str, Any] = {
            "title": {"tag": "plain_text", "content": title},
            "template": template,
        }
        if subtitle:
            header["subtitle"] = {"tag": "plain_text", "content": subtitle}

        self.card["header"] = header
        return self

    def add_markdown(self, content: str) -> CardBuilder:
        """Add a markdown text element.

        Args:
            content: Markdown content

        Returns:
            Self for chaining
        """
        self.card["elements"].append({"tag": "markdown", "content": content})
        return self

    def add_text(self, content: str, text_tag: str = "plain_text") -> CardBuilder:
        """Add a plain text element.

        Args:
            content: Text content
            text_tag: Text tag type (plain_text or lark_md)

        Returns:
            Self for chaining
        """
        self.card["elements"].append(
            {"tag": "div", "text": {"tag": text_tag, "content": content}}
        )
        return self

    def add_divider(self) -> CardBuilder:
        """Add a divider line.

        Returns:
            Self for chaining
        """
        self.card["elements"].append({"tag": "hr"})
        return self

    def add_button(
        self,
        text: str,
        url: str | None = None,
        button_type: str = "default",
    ) -> CardBuilder:
        """Add a button element.

        Args:
            text: Button text
            url: Button URL (optional)
            button_type: Button type (default, primary, danger)

        Returns:
            Self for chaining
        """
        button: dict[str, Any] = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": text},
            "type": button_type,
        }
        if url:
            button["url"] = url

        self.card["elements"].append({"tag": "action", "actions": [button]})
        return self

    def add_image(self, img_key: str, alt: str = "") -> CardBuilder:
        """Add an image element.

        Args:
            img_key: Feishu image key
            alt: Alternative text

        Returns:
            Self for chaining
        """
        self.card["elements"].append(
            {"tag": "img", "img_key": img_key, "alt": {"tag": "plain_text", "content": alt}}
        )
        return self

    def add_note(self, content: str) -> CardBuilder:
        """Add a note element (small gray text).

        Args:
            content: Note content

        Returns:
            Self for chaining
        """
        self.card["elements"].append(
            {"tag": "note", "elements": [{"tag": "plain_text", "content": content}]}
        )
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the card structure.

        Returns:
            Complete card JSON structure
        """
        return self.card
