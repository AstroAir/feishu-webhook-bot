"""Miscellaneous component initialization mixin for FeishuBot."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from ...automation import AutomationEngine
from ...core import get_logger
from ...core.config_watcher import create_config_watcher
from ...core.event_server import EventServer
from ...core.templates import RenderedTemplate, TemplateRegistry

if TYPE_CHECKING:
    from ..base import BotBase

logger = get_logger("bot.init.misc")


class MiscInitializerMixin:
    """Mixin for miscellaneous component initialization."""

    def _setup_logging(self: BotBase) -> None:
        """Setup logging based on configuration."""
        from ...core import setup_logging

        logging_config = getattr(self.config, "logging", None)
        level_value = getattr(logging_config, "level", None) if logging_config else None
        if not isinstance(level_value, str):
            logger.debug("Skipping logging configuration setup; invalid logging level provided")
            return
        setup_logging(logging_config)

    def _init_templates(self: BotBase) -> None:
        """Initialize template registry from configuration."""
        templates = getattr(self.config, "templates", []) or []
        self.template_registry = TemplateRegistry(templates)
        if templates:
            logger.info("Loaded %s configured templates", len(templates))

    def _init_automation(self: BotBase) -> None:
        """Initialize automation engine for declarative workflows."""
        rules = getattr(self.config, "automations", []) or []
        template_registry = self.template_registry or TemplateRegistry([])
        self.automation_engine = AutomationEngine(
            rules=rules,
            scheduler=self.scheduler,
            clients=self.clients,
            template_registry=template_registry,
            http_defaults=self.config.http,
            send_text=self._automation_send_text,
            send_rendered=self._automation_send_rendered,
            providers=self.providers,
        )
        if rules:
            logger.info("Automation engine configured with %s rule(s)", len(rules))

    def _automation_send_text(self: BotBase, text: str, webhook_name: str) -> None:
        """Send text message for automation engine."""
        self.send_message(text, webhook_name)

    def _automation_send_rendered(
        self: BotBase, rendered: RenderedTemplate, webhook_names: Sequence[str]
    ) -> None:
        """Send rendered template for automation engine."""
        self._send_rendered_template(rendered, webhook_names)

    def _init_config_watcher(self: BotBase) -> None:
        """Initialize configuration file watcher for hot-reload."""
        if not self.config.config_hot_reload:
            logger.info("Configuration hot-reload is disabled")
            return

        # Get config file path from environment or use default
        config_path = os.environ.get("FEISHU_BOT_CONFIG", "config.yaml")
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found: {config_path}, hot-reload disabled")
            return

        try:
            self.config_watcher = create_config_watcher(config_path, self)
            logger.info("Configuration watcher initialized for %s", config_path)
        except Exception as exc:
            logger.error("Failed to initialize config watcher: %s", exc, exc_info=True)

    def _init_event_server(self: BotBase) -> None:
        """Initialize inbound event server if configured."""
        event_config = getattr(self.config, "event_server", None)
        if not event_config:
            logger.info("Event server disabled")
            return

        enabled_flag = getattr(event_config, "enabled", None)
        if not isinstance(enabled_flag, bool) or not enabled_flag:
            logger.info("Event server disabled")
            return

        path_value = getattr(event_config, "path", None)
        if not isinstance(path_value, str):
            logger.debug("Skipping event server initialization; configuration path is not a string")
            return

        # Pass providers config for QQ access token verification
        providers_config = getattr(self.config, "providers", None)
        self.event_server = EventServer(
            event_config, self._handle_incoming_event, providers_config=providers_config
        )

        # Connect chat controller to event server if available
        if self.chat_controller:
            try:
                # Create async wrapper for chat controller message handling
                async def _handle_message_wrapper(payload: dict[str, Any]) -> None:
                    """Async wrapper to handle messages through chat controller."""
                    try:
                        # For now, we'll keep the event handling separate from chat controller
                        # Chat controller will be called from _handle_incoming_event
                        pass
                    except Exception as exc:
                        logger.error(
                            "Chat controller message handling failed: %s", exc, exc_info=True
                        )

                logger.info("Chat controller connected to event server")
            except Exception as exc:
                logger.error(
                    "Failed to connect chat controller to event server: %s", exc, exc_info=True
                )

        logger.info(
            "Event server configured on %s:%s%s",
            event_config.host,
            event_config.port,
            event_config.path,
        )
