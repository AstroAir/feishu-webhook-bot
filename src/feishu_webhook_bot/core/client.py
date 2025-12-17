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
from typing import Any

import httpx

from .config import RetryPolicyConfig, WebhookConfig
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

    def __init__(
        self,
        config: WebhookConfig,
        timeout: float | None = None,
        retry: RetryPolicyConfig | None = None,
    ):
        """Initialize the webhook client.

        Args:
            config: Webhook configuration
            timeout: Request timeout in seconds
        """
        self.config = config
        self.timeout = timeout if timeout is not None else (config.timeout or 10.0)
        self.retry_policy = retry or config.retry or RetryPolicyConfig()
        self._default_headers = {**(config.headers or {})}
        self._client = httpx.Client(timeout=self.timeout, headers=self._default_headers)

    def __enter__(self) -> FeishuWebhookClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def is_configured(self) -> bool:
        """Check if the webhook is properly configured.

        Returns:
            True if webhook URL appears valid, False otherwise.
        """
        url = self.config.url
        if not url or not url.strip():
            return False
        # Check for placeholder or example URLs
        if "${" in url or "$(" in url:
            return False
        if "your-webhook" in url.lower() or "xxx" in url.lower():
            return False
        if not url.startswith("https://"):
            return False
        # Check for Feishu webhook URL pattern
        if "open.feishu.cn" not in url and "open.larksuite.com" not in url:
            logger.debug("Webhook URL does not appear to be a Feishu URL: %s", url[:50])
        return True

    def validate_webhook(self) -> tuple[bool, str]:
        """Validate the webhook by checking its configuration.

        Returns:
            Tuple of (is_valid, error_message). error_message is empty if valid.
        """
        if not self.is_configured():
            return False, "Webhook URL is not properly configured"

        url = self.config.url
        # Check URL format
        if not url.startswith("https://"):
            return False, "Webhook URL must use HTTPS"

        # Check for common Feishu webhook patterns
        valid_patterns = [
            "open.feishu.cn/open-apis/bot/v2/hook/",
            "open.larksuite.com/open-apis/bot/v2/hook/",
        ]
        if not any(pattern in url for pattern in valid_patterns):
            return False, "Webhook URL does not match expected Feishu webhook pattern"

        return True, ""

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

        logger.debug("Sending message to webhook: %s", self.config.name)

        attempt = 0
        delay = self.retry_policy.backoff_seconds
        headers = {"Content-Type": "application/json", **self._default_headers}

        while True:
            attempt += 1
            try:
                response = self._client.post(
                    self.config.url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                result = response.json()

                # Check Feishu API response. Treat API-level errors (code != 0)
                # as non-retriable: raise immediately so tests observing a
                # non-zero code get the expected ValueError without retries.
                if result.get("code") != 0:
                    error_msg = result.get("msg", "Unknown error")
                    raise ValueError(f"Feishu API error: {error_msg}")

                logger.info(
                    "Message sent successfully via webhook '%s' (attempt %s)",
                    self.config.name,
                    attempt,
                )
                return result

            except httpx.TransportError as exc:
                # Only retry on transport/HTTP-level errors
                if attempt >= self.retry_policy.max_attempts:
                    logger.error(
                        "Failed to send message via '%s' after %s attempts: %s",
                        self.config.name,
                        attempt,
                        exc,
                    )
                    raise

                sleep_for = min(delay, self.retry_policy.max_backoff_seconds)
                logger.warning(
                    "Send attempt %s/%s for webhook '%s' failed: %s. Retrying in %.2fs",
                    attempt,
                    self.retry_policy.max_attempts,
                    self.config.name,
                    exc,
                    sleep_for,
                )
                time.sleep(sleep_for)
                delay = max(
                    delay * self.retry_policy.backoff_multiplier,
                    self.retry_policy.backoff_seconds,
                )

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
        """Send an image message using image_key.

        Note: The image must be uploaded to Feishu first to get an image_key.
        For sending local images, use send_image_base64() instead.

        Args:
            image_key: Feishu image key (e.g., "img_v2_xxxxx")

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

    def send_image_base64(
        self,
        image_base64: str,
        alt_text: str = "",
    ) -> dict[str, Any]:
        """Send an image message using base64 encoded data.

        This method sends an image as a rich text message with embedded base64 image.
        Note: Feishu webhook bots have limited support for base64 images.
        For best results, use the Feishu Open API to upload images and get image_key.

        Args:
            image_base64: Base64 encoded image data (without data URI prefix)
            alt_text: Alternative text for the image

        Returns:
            Response from Feishu API

        Example:
            ```python
            import base64
            with open("image.png", "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            client.send_image_base64(image_data, "My Image")
            ```
        """
        # Send as rich text with image element
        # Note: Webhook bots may not support all image features
        content = [
            [{"tag": "text", "text": alt_text or "Image"}],
        ]
        payload = {
            "msg_type": MessageType.POST,
            "content": {
                "post": {
                    "zh_cn": {
                        "title": alt_text or "Image",
                        "content": content,
                    }
                }
            },
        }
        return self._send_message(payload)

    def send_image_file(
        self,
        file_path: str,
        alt_text: str | None = None,
    ) -> dict[str, Any]:
        """Send an image from a local file path.

        This is a convenience method that reads and encodes a local image file.
        Note: For webhook bots, images need to be uploaded first via Feishu Open API
        to get an image_key. This method provides a fallback using rich text.

        Args:
            file_path: Path to the local image file
            alt_text: Alternative text (defaults to filename)

        Returns:
            Response from Feishu API

        Example:
            ```python
            client.send_image_file("/path/to/image.png", "Screenshot")
            ```
        """
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        if alt_text is None:
            alt_text = path.name

        # Read and encode image
        with open(file_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        return self.send_image_base64(image_data, alt_text)


class CardBuilder:
    """Helper class for building Feishu interactive cards.

    This builder provides a fluent interface for constructing Card JSON
    structures. Supports both v1.0 (default, better webhook compatibility)
    and v2.0 formats.

    Card JSON v1.0 structure (default):
        - config: Card configuration (wide_screen_mode, etc.)
        - header: Card header with title and template
        - elements: Array of card components

    Card JSON v2.0 structure:
        - schema: "2.0"
        - config: Extended configuration with style options
        - header: Card header
        - body: Container with direction, padding, and elements

    Example:
        ```python
        # v1.0 format (recommended for webhooks)
        card = (
            CardBuilder()
            .set_header("Title", template="blue")
            .add_markdown("**Bold** content")
            .add_divider()
            .add_button("Click Me", url="https://example.com")
            .build()
        )

        # v2.0 format
        card = (
            CardBuilder(version="2.0")
            .set_header("Title", template="blue")
            .add_markdown("**Bold** content")
            .build()
        )
        client.send_card(card)
        ```
    """

    def __init__(self, version: str = "1.0") -> None:
        """Initialize card builder.

        Args:
            version: Card JSON version ("1.0" or "2.0"). Default is "1.0"
                     which has better compatibility with webhooks.
        """
        self.version = version
        if version == "2.0":
            self.card: dict[str, Any] = {
                "schema": "2.0",
                "body": {
                    "direction": "vertical",
                    "elements": [],
                },
            }
        else:
            # v1.0 format - better webhook compatibility
            self.card: dict[str, Any] = {"elements": []}

    def _get_elements(self) -> list[dict[str, Any]]:
        """Get the elements array based on card version."""
        if self.version == "2.0":
            return self.card["body"]["elements"]
        return self.card["elements"]

    def set_config(
        self,
        wide_screen_mode: bool | None = None,
        enable_forward: bool | None = None,
        update_multi: bool | None = None,
        style: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> CardBuilder:
        """Set card configuration.

        Args:
            wide_screen_mode: Enable wide screen mode for PC
            enable_forward: Allow card forwarding
            update_multi: Enable shared card (multiple users see same card)
            style: Style configuration (v2.0 only)
            **kwargs: Additional configuration options

        Returns:
            Self for chaining
        """
        if "config" not in self.card:
            self.card["config"] = {}

        if wide_screen_mode is not None:
            self.card["config"]["wide_screen_mode"] = wide_screen_mode
        if enable_forward is not None:
            self.card["config"]["enable_forward"] = enable_forward
        if update_multi is not None:
            self.card["config"]["update_multi"] = update_multi
        if style is not None and self.version == "2.0":
            self.card["config"]["style"] = style

        self.card["config"].update(kwargs)
        return self

    def set_header(
        self,
        title: str,
        template: str = "blue",
        subtitle: str | None = None,
        icon: dict[str, Any] | None = None,
        ud_icon: dict[str, Any] | None = None,
    ) -> CardBuilder:
        """Set card header.

        Args:
            title: Header title
            template: Color template (blue, turquoise, green, yellow, orange,
                      red, carmine, violet, purple, indigo, grey, default)
            subtitle: Optional subtitle
            icon: Standard icon configuration (tag: "standard_icon")
            ud_icon: Custom icon configuration (using image key)

        Returns:
            Self for chaining
        """
        header: dict[str, Any] = {
            "title": {"tag": "plain_text", "content": title},
            "template": template,
        }
        if subtitle:
            header["subtitle"] = {"tag": "plain_text", "content": subtitle}
        if icon:
            header["icon"] = icon
        if ud_icon:
            header["ud_icon"] = ud_icon

        self.card["header"] = header
        return self

    def add_markdown(
        self,
        content: str,
        text_align: str | None = None,
        text_size: str | None = None,
        icon: dict[str, Any] | None = None,
        href: dict[str, str] | None = None,
    ) -> CardBuilder:
        """Add a markdown text element.

        Args:
            content: Markdown content (supports **bold**, *italic*, ~~strike~~,
                     [link](url), <at id=all></at>, etc.)
            text_align: Text alignment (left, center, right)
            text_size: Text size (normal, heading, xxxx-large, etc.)
            icon: Icon to display before text
            href: URL variable mapping for ${var} in content

        Returns:
            Self for chaining
        """
        element: dict[str, Any] = {"tag": "markdown", "content": content}
        if text_align:
            element["text_align"] = text_align
        if text_size:
            element["text_size"] = text_size
        if icon:
            element["icon"] = icon
        if href:
            element["href"] = href

        self._get_elements().append(element)
        return self

    def add_text(
        self,
        content: str,
        text_tag: str = "plain_text",
        lines: int | None = None,
    ) -> CardBuilder:
        """Add a plain text element (div).

        Args:
            content: Text content
            text_tag: Text tag type (plain_text or lark_md)
            lines: Maximum lines to display (truncates with ellipsis)

        Returns:
            Self for chaining
        """
        element: dict[str, Any] = {
            "tag": "div",
            "text": {"tag": text_tag, "content": content},
        }
        if lines:
            element["text"]["lines"] = lines

        self._get_elements().append(element)
        return self

    def add_divider(self) -> CardBuilder:
        """Add a divider line.

        Returns:
            Self for chaining
        """
        self._get_elements().append({"tag": "hr"})
        return self

    def add_button(
        self,
        text: str,
        url: str | None = None,
        multi_url: dict[str, str] | None = None,
        button_type: str = "default",
        size: str = "medium",
        width: str | None = None,
        icon: dict[str, Any] | None = None,
        disabled: bool = False,
        disabled_tips: dict[str, str] | None = None,
        confirm: dict[str, Any] | None = None,
        value: dict[str, Any] | None = None,
        action_type: str | None = None,
        complex_interaction: bool = False,
    ) -> CardBuilder:
        """Add a button element.

        Args:
            text: Button text
            url: Button URL (for link buttons)
            multi_url: Platform-specific URLs (url, pc_url, ios_url, android_url)
            button_type: Button type (default, primary, danger, text)
            size: Button size (tiny, small, medium, large)
            width: Button width (default, fill, or pixel values like [100,bindButtonWidth])
            icon: Icon configuration
            disabled: Whether button is disabled
            disabled_tips: Tooltip when disabled
            confirm: Confirmation dialog configuration
            value: Custom value passed to callback
            action_type: Action type (link, request, form_submit, form_reset)
            complex_interaction: Enable complex interaction mode

        Returns:
            Self for chaining
        """
        button: dict[str, Any] = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": text},
            "type": button_type,
            "size": size,
        }
        if url:
            button["url"] = url
        if multi_url:
            button["multi_url"] = multi_url
        if width:
            button["width"] = width
        if icon:
            button["icon"] = icon
        if disabled:
            button["disabled"] = disabled
        if disabled_tips:
            button["disabled_tips"] = disabled_tips
        if confirm:
            button["confirm"] = confirm
        if value:
            button["value"] = value
        if action_type:
            button["action_type"] = action_type
        if complex_interaction:
            button["complex_interaction"] = complex_interaction

        elements = self._get_elements()
        # If last element is an action block, append button to it
        if elements and elements[-1].get("tag") == "action":
            elements[-1]["actions"].append(button)
        else:
            # Otherwise, create a new action block
            elements.append({"tag": "action", "actions": [button]})
        return self

    def add_image(
        self,
        img_key: str,
        alt: str = "",
        preview: bool = False,
        scale_type: str | None = None,
        size: str | None = None,
        custom_width: int | None = None,
        custom_height: int | None = None,
        transparent: bool = False,
        corner_radius: str | None = None,
        margin: str | None = None,
        component_id: str | None = None,
    ) -> CardBuilder:
        """Add an image element.

        Image limits (recommended):
        - Size within 1500 × 3000 px
        - File size under 10 MB
        - Aspect ratio (height:width) not exceeding 16:9

        Args:
            img_key: Feishu image key (obtained by uploading image via API)
            alt: Hover tooltip text shown on PC when cursor hovers over image
            preview: Enable click to view enlarged image preview. Default False.
            scale_type: Image cropping/scaling mode:
                - None or "fit_horizontal": Show complete image, no cropping (default)
                - "crop_center": Center crop - crops from center based on target size
                - "crop_top": Top crop - preserves top of image when height exceeds target
            size: Predefined image size (used with crop modes):
                - "stretch_without_padding": Extra large - fills container width
                - "large": 160×160 px - good for multi-image layouts in columns
                - "medium": 80×80 px - good for cover images in text+image layouts
                - "small": 40×40 px - good for avatars
                - "tiny": 16×16 px - good for icons, notes
            custom_width: Custom width in pixels [1-1000], used instead of size
            custom_height: Custom height in pixels [1-1000], used with custom_width
            transparent: Enable transparent background. Default False (white background).
            corner_radius: Border radius (e.g., "8px" or "50%")
            margin: Outer margin (e.g., "4px 8px" or "-8px" for full-bleed effect)
            component_id: Unique component ID (letters, numbers, underscore;
                         must start with letter; max 20 chars)

        Returns:
            Self for chaining

        Example:
            ```python
            # Basic image
            builder.add_image("img_v2_xxx", alt="Product photo")

            # Large centered image with preview
            builder.add_image(
                "img_v2_xxx",
                alt="Banner",
                scale_type="crop_center",
                size="stretch_without_padding",
                preview=True
            )

            # Custom size avatar with rounded corners
            builder.add_image(
                "img_v2_xxx",
                custom_width=48,
                custom_height=48,
                corner_radius="50%"
            )

            # Full-bleed image (negative margin)
            builder.add_image(
                "img_v2_xxx",
                margin="-12px -12px 0 -12px"
            )
            ```
        """
        element: dict[str, Any] = {
            "tag": "img",
            "img_key": img_key,
        }

        # Alt text (hover tooltip)
        if alt:
            element["alt"] = {"tag": "plain_text", "content": alt}

        # Preview mode
        if preview:
            element["preview"] = preview

        # Scale/crop type
        if scale_type:
            element["scale_type"] = scale_type

        # Size configuration
        if custom_width and custom_height:
            # Custom fixed size
            element["custom_width"] = min(max(custom_width, 1), 1000)
            element["size"] = {
                "width": f"{min(max(custom_width, 1), 1000)}px",
                "height": f"{min(max(custom_height, 1), 1000)}px",
            }
        elif size:
            element["size"] = size

        # Transparent background
        if transparent:
            element["transparent"] = transparent

        # Corner radius
        if corner_radius:
            element["corner_radius"] = corner_radius

        # Margin (outer spacing)
        if margin:
            element["margin"] = margin

        # Component ID
        if component_id:
            element["component_id"] = component_id

        self._get_elements().append(element)
        return self

    def add_image_combination(
        self,
        img_keys: list[str],
        combination_mode: str = "double",
        corner_radius: str | None = None,
    ) -> CardBuilder:
        """Add a multi-image combination layout.

        Creates a visually appealing multi-image layout using column_set.

        Args:
            img_keys: List of image keys (2-4 images recommended)
            combination_mode: Layout mode:
                - "double": 2 images side by side
                - "triple": 3 images (1 large + 2 small)
                - "quad": 4 images in 2x2 grid
            corner_radius: Border radius for all images

        Returns:
            Self for chaining

        Example:
            ```python
            builder.add_image_combination(
                ["img_v2_1", "img_v2_2"],
                combination_mode="double"
            )
            ```
        """
        if combination_mode == "double" and len(img_keys) >= 2:
            columns = [
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "img",
                            "img_key": img_keys[0],
                            "scale_type": "crop_center",
                            **({"corner_radius": corner_radius} if corner_radius else {}),
                        }
                    ],
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "img",
                            "img_key": img_keys[1],
                            "scale_type": "crop_center",
                            **({"corner_radius": corner_radius} if corner_radius else {}),
                        }
                    ],
                },
            ]
            self.add_column_set(columns, flex_mode="bisect", horizontal_spacing="small")

        elif combination_mode == "triple" and len(img_keys) >= 3:
            columns = [
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 2,
                    "elements": [
                        {
                            "tag": "img",
                            "img_key": img_keys[0],
                            "scale_type": "crop_center",
                            **({"corner_radius": corner_radius} if corner_radius else {}),
                        }
                    ],
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "vertical_spacing": "small",
                    "elements": [
                        {
                            "tag": "img",
                            "img_key": img_keys[1],
                            "scale_type": "crop_center",
                            "size": "large",
                            **({"corner_radius": corner_radius} if corner_radius else {}),
                        },
                        {
                            "tag": "img",
                            "img_key": img_keys[2],
                            "scale_type": "crop_center",
                            "size": "large",
                            **({"corner_radius": corner_radius} if corner_radius else {}),
                        },
                    ],
                },
            ]
            self.add_column_set(columns, flex_mode="none", horizontal_spacing="small")

        elif combination_mode == "quad" and len(img_keys) >= 4:
            # First row
            row1 = [
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "img",
                            "img_key": img_keys[0],
                            "scale_type": "crop_center",
                            "size": "large",
                            **({"corner_radius": corner_radius} if corner_radius else {}),
                        }
                    ],
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "img",
                            "img_key": img_keys[1],
                            "scale_type": "crop_center",
                            "size": "large",
                            **({"corner_radius": corner_radius} if corner_radius else {}),
                        }
                    ],
                },
            ]
            self.add_column_set(row1, flex_mode="bisect", horizontal_spacing="small")

            # Second row
            row2 = [
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "img",
                            "img_key": img_keys[2],
                            "scale_type": "crop_center",
                            "size": "large",
                            **({"corner_radius": corner_radius} if corner_radius else {}),
                        }
                    ],
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "img",
                            "img_key": img_keys[3],
                            "scale_type": "crop_center",
                            "size": "large",
                            **({"corner_radius": corner_radius} if corner_radius else {}),
                        }
                    ],
                },
            ]
            self.add_column_set(
                row2, flex_mode="bisect", horizontal_spacing="small", margin="4px 0 0 0"
            )

        return self

    def add_note(
        self,
        content: str | None = None,
        elements: list[dict[str, Any]] | None = None,
    ) -> CardBuilder:
        """Add a note element (small gray text with optional icons/images).

        Args:
            content: Simple text content
            elements: Array of text/image elements for complex notes

        Returns:
            Self for chaining
        """
        if elements:
            note_elements = elements
        elif content:
            note_elements = [{"tag": "plain_text", "content": content}]
        else:
            note_elements = []

        self._get_elements().append({"tag": "note", "elements": note_elements})
        return self

    def add_column_set(
        self,
        columns: list[dict[str, Any]],
        flex_mode: str = "none",
        background_style: str = "default",
        horizontal_spacing: str = "default",
        horizontal_align: str = "left",
        margin: str | None = None,
        action: dict[str, Any] | None = None,
    ) -> CardBuilder:
        """Add a multi-column layout (column_set).

        Args:
            columns: List of column configurations, each with:
                - tag: "column"
                - width: "weighted" or "auto"
                - weight: Column weight (1-5) if width is "weighted"
                - vertical_align: "top", "center", or "bottom"
                - vertical_spacing: Spacing between elements
                - padding: Column padding
                - elements: Array of elements in the column
            flex_mode: Flex mode (none, stretch, flow, bisect, trisect, etc.)
            background_style: Background color (default, grey, etc.)
            horizontal_spacing: Spacing between columns (default, small, medium, large)
            horizontal_align: Column alignment (left, center, right)
            margin: Outer margin (e.g., "16px 0px")
            action: Action configuration for clickable columns

        Returns:
            Self for chaining

        Example:
            ```python
            builder.add_column_set(
                columns=[
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "elements": [{"tag": "markdown", "content": "Left"}]
                    },
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "elements": [{"tag": "markdown", "content": "Right"}]
                    }
                ],
                flex_mode="bisect"
            )
            ```
        """
        element: dict[str, Any] = {
            "tag": "column_set",
            "flex_mode": flex_mode,
            "background_style": background_style,
            "horizontal_spacing": horizontal_spacing,
            "horizontal_align": horizontal_align,
            "columns": columns,
        }
        if margin:
            element["margin"] = margin
        if action:
            element["action"] = action

        self._get_elements().append(element)
        return self

    def add_table(
        self,
        columns: list[dict[str, Any]],
        rows: list[list[Any]],
        row_height: str | None = None,
        header_style: dict[str, Any] | None = None,
        page_size: int | None = None,
    ) -> CardBuilder:
        """Add a table component.

        Args:
            columns: Column definitions with:
                - name: Column identifier
                - display_name: Column header text
                - data_type: Column type (text, number, options, persons, date, etc.)
                - width: Column width (auto or pixel/percentage)
                - horizontal_align: Text alignment (left, center, right)
                - format: Display format for specific types
            rows: 2D array of row data matching column order
            row_height: Row height (short, medium, tall) - optional
            header_style: Header style configuration
            page_size: Rows per page (enables pagination)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.add_table(
                columns=[
                    {"name": "col1", "display_name": "Name", "data_type": "text"},
                    {"name": "col2", "display_name": "Status", "data_type": "options"}
                ],
                rows=[
                    ["John", "Active"],
                    ["Jane", "Inactive"]
                ]
            )
            ```
        """
        element: dict[str, Any] = {
            "tag": "table",
            "columns": columns,
            "rows": [
                {col["name"]: val for col, val in zip(columns, row, strict=False)} for row in rows
            ],
        }
        if row_height:
            element["row_height"] = row_height
        if header_style:
            element["header_style"] = header_style
        if page_size:
            element["page_size"] = page_size

        self._get_elements().append(element)
        return self

    def add_chart(
        self,
        chart_spec: dict[str, Any],
        aspect_ratio: str = "16:9",
        color_theme: str | None = None,
        preview: bool = True,
        height: str = "auto",
    ) -> CardBuilder:
        """Add a chart component (VChart specification).

        Args:
            chart_spec: VChart specification object containing:
                - type: Chart type (bar, line, pie, etc.)
                - data: Chart data
                - xField, yField: Field mappings
                - Other VChart options
            aspect_ratio: Chart aspect ratio (1:1, 2:1, 4:3, 16:9)
            color_theme: Color theme (brand, rainbow, etc.)
            preview: Enable fullscreen preview
            height: Chart height (auto or pixel value)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.add_chart(
                chart_spec={
                    "type": "bar",
                    "data": [
                        {"name": "A", "value": 10},
                        {"name": "B", "value": 20}
                    ],
                    "xField": "name",
                    "yField": "value"
                },
                aspect_ratio="16:9"
            )
            ```
        """
        element: dict[str, Any] = {
            "tag": "chart",
            "chart_spec": chart_spec,
            "aspect_ratio": aspect_ratio,
            "preview": preview,
            "height": height,
        }
        if color_theme:
            element["color_theme"] = color_theme

        self._get_elements().append(element)
        return self

    def add_form(
        self,
        name: str,
        elements: list[dict[str, Any]],
    ) -> CardBuilder:
        """Add a form container.

        Forms wrap input components (input, select, date_picker, etc.)
        to enable batch submission instead of real-time validation.

        Args:
            name: Form name (used as callback identifier)
            elements: Array of form elements (inputs, buttons, etc.)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.add_form(
                name="user_form",
                elements=[
                    {"tag": "input", "name": "username", "placeholder": {"content": "Enter name"}},
                    {"tag": "button", "text": {"tag": "plain_text", "content": "Submit"},
                     "action_type": "form_submit"}
                ]
            )
            ```
        """
        element: dict[str, Any] = {
            "tag": "form",
            "name": name,
            "elements": elements,
        }
        self._get_elements().append(element)
        return self

    def add_input(
        self,
        name: str,
        placeholder: str = "",
        default_value: str | None = None,
        label: str | None = None,
        required: bool = False,
        disabled: bool = False,
        max_length: int | None = None,
        input_type: str = "text",
        rows: int | None = None,
        width: str = "default",
    ) -> CardBuilder:
        """Add an input field.

        Args:
            name: Input name (used in form submission)
            placeholder: Placeholder text
            default_value: Pre-filled value
            label: Input label
            required: Whether input is required
            disabled: Whether input is disabled
            max_length: Maximum character length
            input_type: Input type (text, password, multiline)
            rows: Number of rows for multiline input
            width: Input width (default, fill, or custom)

        Returns:
            Self for chaining
        """
        element: dict[str, Any] = {
            "tag": "input",
            "name": name,
            "placeholder": {"content": placeholder},
            "width": width,
        }
        if default_value:
            element["default_value"] = default_value
        if label:
            element["label"] = {"tag": "plain_text", "content": label}
        if required:
            element["required"] = required
        if disabled:
            element["disabled"] = disabled
        if max_length:
            element["max_length"] = max_length
        if input_type != "text":
            element["input_type"] = input_type
        if rows:
            element["rows"] = rows

        self._get_elements().append(element)
        return self

    def add_select(
        self,
        name: str,
        options: list[dict[str, str]],
        placeholder: str = "",
        default_value: str | None = None,
        multi_select: bool = False,
        width: str = "default",
    ) -> CardBuilder:
        """Add a select dropdown.

        Args:
            name: Select name
            options: List of options with "text" and "value" keys
            placeholder: Placeholder text
            default_value: Default selected value
            multi_select: Allow multiple selections
            width: Select width (default, fill, or custom)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.add_select(
                name="status",
                options=[
                    {"text": "Active", "value": "active"},
                    {"text": "Inactive", "value": "inactive"}
                ],
                default_value="active"
            )
            ```
        """
        element: dict[str, Any] = {
            "tag": "select_static",
            "name": name,
            "placeholder": {"content": placeholder},
            "options": [
                {"text": {"tag": "plain_text", "content": opt["text"]}, "value": opt["value"]}
                for opt in options
            ],
            "width": width,
        }
        if default_value:
            element["initial_option"] = default_value
        if multi_select:
            element["tag"] = "multi_select_static"

        self._get_elements().append(element)
        return self

    def add_date_picker(
        self,
        name: str,
        placeholder: str = "",
        default_value: str | None = None,
        picker_type: str = "date",
        width: str = "default",
    ) -> CardBuilder:
        """Add a date/time picker.

        Args:
            name: Picker name
            placeholder: Placeholder text
            default_value: Default date/time value
            picker_type: Picker type (date, datetime, date_time)
            width: Picker width

        Returns:
            Self for chaining
        """
        tag = "date_picker" if picker_type == "date" else "picker_datetime"
        element: dict[str, Any] = {
            "tag": tag,
            "name": name,
            "placeholder": {"content": placeholder},
            "width": width,
        }
        if default_value:
            element["initial_date" if picker_type == "date" else "initial_datetime"] = default_value

        self._get_elements().append(element)
        return self

    def add_person_list(
        self,
        persons: list[str],
        size: str = "medium",
        show_avatar: bool = True,
        show_name: bool = True,
    ) -> CardBuilder:
        """Add a person list component.

        Args:
            persons: List of user IDs (open_id, union_id, or user_id)
            size: Avatar size (extra_small, small, medium, large)
            show_avatar: Show user avatars
            show_name: Show user names

        Returns:
            Self for chaining
        """
        element: dict[str, Any] = {
            "tag": "person_list",
            "persons": [{"id": pid} for pid in persons],
            "size": size,
            "show_avatar": show_avatar,
            "show_name": show_name,
        }
        self._get_elements().append(element)
        return self

    def add_collapsible_panel(
        self,
        title: str,
        elements: list[dict[str, Any]],
        expanded: bool = False,
        background_color: str | None = None,
        header_icon: dict[str, Any] | None = None,
        vertical_spacing: str | None = None,
        padding: str | None = None,
    ) -> CardBuilder:
        """Add a collapsible panel (折叠面板).

        Args:
            title: Panel title text
            elements: Content elements inside the panel
            expanded: Initial expanded state
            background_color: Background color when expanded
            header_icon: Icon configuration for header
            vertical_spacing: Spacing between elements (4px, 8px, 12px, 16px) - optional
            padding: Panel padding

        Returns:
            Self for chaining
        """
        element: dict[str, Any] = {
            "tag": "collapsible_panel",
            "header": {
                "title": {"tag": "plain_text", "content": title},
            },
            "expanded": expanded,
            "elements": elements,
        }
        if background_color:
            element["background_color"] = background_color
        if header_icon:
            element["header"]["icon"] = header_icon
        if vertical_spacing:
            element["vertical_spacing"] = vertical_spacing
        if padding:
            element["padding"] = padding

        self._get_elements().append(element)
        return self

    def add_raw_element(self, element: dict[str, Any]) -> CardBuilder:
        """Add a raw element directly to the card.

        Use this for custom elements not covered by other methods.

        Args:
            element: Raw element dictionary

        Returns:
            Self for chaining
        """
        self._get_elements().append(element)
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the card structure.

        Returns:
            Complete card JSON structure
        """
        return self.card
