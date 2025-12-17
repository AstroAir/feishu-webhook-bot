"""Message sending mixin for FeishuBot."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..core import FeishuWebhookClient, get_logger
from ..core.templates import RenderedTemplate

if TYPE_CHECKING:
    from .base import BotBase

logger = get_logger("bot.messaging")


class MessagingMixin:
    """Mixin for message sending functionality."""

    def send_message(
        self: BotBase, text: str, webhook_name: str | Sequence[str] = "default"
    ) -> None:
        """Send a text message via specified webhook or provider.

        Args:
            text: Message text
            webhook_name: Webhook or provider name (default: "default")
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Message text must be a non-empty string")

        targets: Sequence[str]
        if isinstance(webhook_name, str):
            if not webhook_name.strip():
                raise ValueError("Webhook name must be a non-empty string")
            targets = [webhook_name]
        else:
            targets = list(webhook_name)
            if not targets:
                raise ValueError("At least one webhook name must be provided")

        for name in targets:
            # Try clients first (backward compatibility)
            if name in self.clients:
                client = self.clients[name]
                try:
                    client.send_text(text)
                except Exception as exc:
                    logger.error(
                        "Failed to send message via client '%s': %s",
                        name,
                        exc,
                        exc_info=True,
                    )
                    raise
            # Then try providers
            elif name in self.providers:
                provider = self.providers[name]
                try:
                    result = provider.send_text(text, "")  # Empty target uses provider's config URL
                    if not result.success:
                        raise RuntimeError(f"Provider send failed: {result.error}")
                except Exception as exc:
                    logger.error(
                        "Failed to send message via provider '%s': %s",
                        name,
                        exc,
                        exc_info=True,
                    )
                    raise
            else:
                available_clients = ", ".join(sorted(self.clients)) or "none"
                available_providers = ", ".join(sorted(self.providers)) or "none"
                raise ValueError(
                    f"Webhook/provider not found: {name}. "
                    f"Available clients: {available_clients}. "
                    f"Available providers: {available_providers}"
                )

    def _send_rendered_template(
        self: BotBase, rendered: RenderedTemplate, webhook_names: Sequence[str]
    ) -> None:
        """Send a rendered template to specified webhooks.

        Args:
            rendered: Rendered template content
            webhook_names: List of webhook names to send to
        """
        if not webhook_names:
            raise ValueError("No webhook names provided for rendered template")

        missing = [name for name in webhook_names if name not in self.clients]
        if missing:
            available = ", ".join(sorted(self.clients)) or "none"
            raise ValueError(
                f"Webhook client(s) not found: {', '.join(missing)}. Available: {available}"
            )

        for name in webhook_names:
            client = self.clients[name]
            try:
                self._dispatch_rendered(client, rendered)
            except Exception as exc:
                logger.error(
                    "Failed to send rendered template via '%s': %s",
                    name,
                    exc,
                    exc_info=True,
                )
                raise

    def _dispatch_rendered(
        self: BotBase, client: FeishuWebhookClient, rendered: RenderedTemplate
    ) -> None:
        """Dispatch a rendered template to a specific client.

        Args:
            client: Webhook client to send through
            rendered: Rendered template content
        """
        message_type = rendered.type.lower()
        content = rendered.content

        if message_type == "text":
            text_value = content if isinstance(content, str) else str(content)
            client.send_text(text_value)
            return

        if message_type in {"card", "interactive"}:
            client.send_card(content)
            return

        if message_type == "post":
            if not isinstance(content, dict):
                raise ValueError("Post template must render to a dictionary")
            title = content.get("title", "")
            rich_content = content.get("content", [])
            language = content.get("language", "zh_cn")
            client.send_rich_text(title, rich_content, language=language)
            return

        # Fallback to sending a text representation
        client.send_text(str(content))
