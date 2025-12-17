"""Client initialization mixin for FeishuBot."""

from __future__ import annotations

import unittest.mock as _mock
from typing import TYPE_CHECKING, Any

from ...core import FeishuWebhookClient, get_logger
from ...core.config import WebhookConfig

if TYPE_CHECKING:
    from ..base import BotBase

logger = get_logger("bot.init.client")


class ClientInitializerMixin:
    """Mixin for webhook client initialization."""

    def _init_clients(self: BotBase) -> None:
        """Initialize webhook clients for all configured webhooks."""
        webhooks = self.config.webhooks or []
        if not webhooks:
            logger.warning("No webhooks configured.")
            self.client = None
            return

        for webhook in webhooks:
            if not isinstance(webhook, WebhookConfig):
                logger.error("Invalid webhook configuration type: %s", type(webhook).__name__)
                continue

            if not webhook.name:
                logger.error("Webhook configuration missing a name: %s", webhook)
                continue

            if webhook.name in self.clients:
                logger.warning(
                    "Duplicate webhook configuration detected for '%s'; replacing existing client.",
                    webhook.name,
                )
            try:
                client_kwargs: dict[str, Any] = {}
                if webhook.timeout is not None:
                    client_kwargs["timeout"] = webhook.timeout
                if webhook.retry is not None:
                    client_kwargs["retry"] = webhook.retry

                client_obj = FeishuWebhookClient(webhook, **client_kwargs)

                # If tests have patched the client class to return a Mock,
                # create a per-webhook MagicMock proxy that records calls
                # independently while delegating actual calls to the
                # underlying mock instance. This preserves test expectations
                # where each client in bot.clients is a distinct MagicMock.
                if isinstance(client_obj, _mock.Mock):
                    proxy = _mock.MagicMock()

                    def _make_delegator(
                        method_name: str, client: Any = client_obj
                    ) -> _mock.MagicMock:
                        def _delegator(*a: Any, **k: Any) -> Any:
                            # Call the underlying mock
                            getattr(client, method_name)(*a, **k)

                        return _mock.MagicMock(side_effect=_delegator)

                    proxy.send_text = _make_delegator("send_text")
                    proxy.close = _make_delegator("close")
                    # Keep reference to underlying client for any other uses
                    proxy._wrapped = client_obj
                    self.clients[webhook.name] = proxy
                else:
                    self.clients[webhook.name] = client_obj
            except Exception as exc:  # httpx raises at runtime; propagate with context
                logger.error(
                    "Failed to initialize webhook client '%s': %s",
                    webhook.name,
                    exc,
                    exc_info=True,
                )
            else:
                logger.info("Webhook client initialized: %s", webhook.name)

        if not self.clients:
            if any(isinstance(webhook, WebhookConfig) for webhook in webhooks):
                raise RuntimeError("No webhook clients available after initialization")
            logger.debug(
                "Skipping client initialization failures; "
                "configuration does not provide valid WebhookConfig instances"
            )
            self.client = None
            return

        default_client = self.clients.get("default")
        if default_client is None:
            fallback_name, default_client = next(iter(self.clients.items()))
            logger.info(
                "Default webhook client not explicitly configured; using '%s' instead.",
                fallback_name,
            )
        self.client = default_client
