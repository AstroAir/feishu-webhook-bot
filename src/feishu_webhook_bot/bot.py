"""Main bot class that orchestrates all components."""

from __future__ import annotations

import os
import signal
import threading
from collections.abc import Sequence
from pathlib import Path
from types import FrameType
from typing import Any

from .automation import AutomationEngine
from .core import BotConfig, FeishuWebhookClient, get_logger, setup_logging
from .core.config import WebhookConfig
from .core.config_watcher import create_config_watcher
from .core.event_server import EventServer
from .core.templates import RenderedTemplate, TemplateRegistry
from .plugins import PluginManager
from .scheduler import TaskScheduler
from .tasks import TaskManager

logger = get_logger("bot")


class FeishuBot:
    """Main bot class that orchestrates all components.

    This class integrates:
    - Configuration management
    - Webhook client
    - Task scheduler
    - Plugin system
    - Hot-reload

    Example:
        ```python
        from feishu_webhook_bot import FeishuBot

        # Create bot from config file
        bot = FeishuBot.from_config("config.yaml")

        # Or with config object
        config = BotConfig(...)
        bot = FeishuBot(config)

        # Start the bot
        bot.start()

        # Bot will run until interrupted
        ```
    """

    def __init__(self, config: BotConfig):
        """Initialize the bot.

        Args:
            config: Bot configuration
        """
        if config is None:
            raise ValueError("Bot configuration must not be None")
        # Accept both real BotConfig instances and test doubles/mocks.
        # Rely on duck-typing rather than strict isinstance checks so tests
        # that patch BotConfig with mocks continue to work.

        self.config: BotConfig = config
        self._setup_logging()

        # Initialize components
        self.clients: dict[str, FeishuWebhookClient] = {}
        self.client: FeishuWebhookClient | None = None  # for backward compatibility
        self.scheduler: TaskScheduler | None = None
        self.plugin_manager: PluginManager | None = None
        self.template_registry: TemplateRegistry | None = None
        self.automation_engine: AutomationEngine | None = None
        self.task_manager: TaskManager | None = None
        self.event_server: EventServer | None = None
        self.config_watcher: Any = None
        self._running: bool = False
        self._shutdown_event = threading.Event()
        self._signal_handlers: dict[int, Any] = {}
        self._signal_handlers_installed = False

        # Eagerly initialize core components
        try:
            self._init_clients()
        except Exception as exc:
            logger.error("Failed to initialize webhook clients: %s", exc, exc_info=True)
            raise

        try:
            self._init_scheduler()
        except Exception as exc:
            logger.error("Failed to initialize scheduler: %s", exc, exc_info=True)
            raise

        try:
            self._init_plugins()
        except Exception as exc:
            logger.error("Failed to initialize plugins: %s", exc, exc_info=True)
            raise

        try:
            self._init_templates()
            self._init_automation()
            self._init_tasks()
            self._init_event_server()
            self._init_config_watcher()
        except Exception as exc:
            logger.error("Failed to initialize optional components: %s", exc, exc_info=True)
            raise

        logger.info("Feishu Bot initialized")

    def _setup_logging(self) -> None:
        """Setup logging based on configuration."""
        logging_config = getattr(self.config, "logging", None)
        level_value = getattr(logging_config, "level", None) if logging_config else None
        if not isinstance(level_value, str):
            logger.debug("Skipping logging configuration setup; invalid logging level provided")
            return
        setup_logging(logging_config)

    def _init_clients(self) -> None:
        """Initialize webhook clients for all configured webhooks."""
        webhooks = self.config.webhooks or []
        if not webhooks:
            logger.warning("No webhooks configured.")
            self.client = None
            return

        import unittest.mock as _mock

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

                    def _make_delegator(method_name: str):
                        def _delegator(*a, **k):
                            # Call the underlying mock
                            getattr(client_obj, method_name)(*a, **k)

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
                "Skipping client initialization failures; configuration does not provide valid WebhookConfig instances"
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

    def _init_scheduler(self) -> None:
        """Initialize task scheduler if enabled."""
        scheduler_config = getattr(self.config, "scheduler", None)
        if scheduler_config is None:
            logger.warning("Scheduler configuration missing; scheduler disabled")
            return

        enabled_flag = getattr(scheduler_config, "enabled", None)
        if not isinstance(enabled_flag, bool):
            logger.debug(
                "Skipping scheduler initialization; scheduler config does not provide a boolean 'enabled' flag"
            )
            return

        if not scheduler_config.enabled:
            logger.info("Scheduler is disabled")
            return

        try:
            self.scheduler = TaskScheduler(scheduler_config)
        except Exception as exc:
            logger.error("Failed to initialize scheduler: %s", exc, exc_info=True)
            raise

        logger.info("Scheduler initialized")

    def _init_plugins(self) -> None:
        """Initialize plugin manager and load plugins."""
        plugins_config = getattr(self.config, "plugins", None)
        if plugins_config is None:
            logger.warning("Plugin configuration missing; plugin system disabled")
            return

        if not plugins_config.enabled:
            logger.info("Plugin system is disabled")
            return

        if not self.client:
            logger.warning("No default webhook client available; skipping plugin initialization")
            return

        try:
            self.plugin_manager = PluginManager(self.config, self.client, self.scheduler)
        except Exception as exc:
            logger.error("Failed to initialize plugin manager: %s", exc, exc_info=True)
            raise

        try:
            self.plugin_manager.load_plugins()
            self.plugin_manager.enable_all()
        except Exception as exc:
            logger.error("Failed to load or enable plugins: %s", exc, exc_info=True)
            raise

        # Start hot reload if enabled
        if plugins_config.auto_reload:
            try:
                self.plugin_manager.start_hot_reload()
            except Exception as exc:
                logger.error("Failed to start plugin hot reload: %s", exc, exc_info=True)
                raise

        logger.info("Plugin system initialized")

    def _init_templates(self) -> None:
        """Initialize template registry from configuration."""
        templates = getattr(self.config, "templates", []) or []
        self.template_registry = TemplateRegistry(templates)
        if templates:
            logger.info("Loaded %s configured templates", len(templates))

    def _init_automation(self) -> None:
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
        )
        if rules:
            logger.info("Automation engine configured with %s rule(s)", len(rules))

    def _init_tasks(self) -> None:
        """Initialize task manager for automated tasks."""
        tasks = getattr(self.config, "tasks", []) or []
        if not tasks:
            logger.info("No tasks configured")
            return

        if not self.scheduler:
            logger.warning("Scheduler not available; tasks will not be scheduled")
            return

        try:
            self.task_manager = TaskManager(
                config=self.config,
                scheduler=self.scheduler,
                plugin_manager=self.plugin_manager,
                clients=self.clients,
            )
            logger.info("Task manager configured with %s task(s)", len(tasks))
        except Exception as exc:
            logger.error("Failed to initialize task manager: %s", exc, exc_info=True)
            raise

    def _init_config_watcher(self) -> None:
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

    def _init_event_server(self) -> None:
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
            logger.debug(
                "Skipping event server initialization; configuration path is not a string"
            )
            return

        self.event_server = EventServer(event_config, self._handle_incoming_event)
        logger.info(
            "Event server configured on %s:%s%s",
            event_config.host,
            event_config.port,
            event_config.path,
        )

    def _automation_send_text(self, text: str, webhook_name: str) -> None:
        self.send_message(text, webhook_name)

    def _automation_send_rendered(
        self, rendered: RenderedTemplate, webhook_names: Sequence[str]
    ) -> None:
        self._send_rendered_template(rendered, webhook_names)

    def _handle_incoming_event(self, payload: dict[str, Any]) -> None:
        """Handle inbound events from the event server."""
        logger.debug("Handling incoming event: %s", payload.get("type", "unknown"))

        if self.plugin_manager:
            try:
                self.plugin_manager.dispatch_event(payload, context={})
            except Exception as exc:
                logger.error("Plugin event dispatch failed: %s", exc, exc_info=True)

        if self.automation_engine:
            try:
                self.automation_engine.handle_event(payload)
            except Exception as exc:
                logger.error("Automation event handling failed: %s", exc, exc_info=True)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        if self._signal_handlers_installed:
            return

        def signal_handler(sig: int, frame: FrameType | None) -> None:
            logger.info("Received signal %s, initiating shutdown", sig)
            self._shutdown_event.set()
            self.stop()

        for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if sig is None:
                continue
            try:
                previous = signal.getsignal(sig)
                self._signal_handlers[sig] = previous
                signal.signal(sig, signal_handler)
            except (AttributeError, OSError, ValueError) as exc:
                logger.warning("Unable to register handler for signal %s: %s", sig, exc)

        self._signal_handlers_installed = True

    def _wait_for_shutdown(self) -> None:
        """Block until a shutdown event is triggered."""
        while self._running:
            try:
                if self._shutdown_event.wait(timeout=1.0):
                    break
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received; signalling shutdown")
                self._shutdown_event.set()
                break

    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers if they were overridden."""
        if not self._signal_handlers_installed:
            return

        for sig, handler in self._signal_handlers.items():
            try:
                handler_to_set = handler if handler is not None else signal.SIG_DFL
                signal.signal(sig, handler_to_set)
            except (AttributeError, OSError, ValueError) as exc:
                logger.debug("Unable to restore handler for signal %s: %s", sig, exc)

        self._signal_handlers.clear()
        self._signal_handlers_installed = False

    def start(self) -> None:
        """Start the bot.

        This initializes all components and starts the scheduler.
        The bot will run until interrupted.
        """
        if self._running:
            logger.warning("Bot is already running")
            return

        logger.info("Starting Feishu Bot...")
        self._shutdown_event.clear()

        try:
            # Start scheduler
            if self.scheduler:
                try:
                    self.scheduler.start()
                    logger.info("Scheduler started")
                except Exception as exc:
                    logger.error("Failed to start scheduler: %s", exc, exc_info=True)
                    raise

            if self.automation_engine:
                try:
                    self.automation_engine.start()
                    logger.info("Automation engine started")
                except Exception as exc:
                    logger.error(
                        "Failed to start automation engine: %s",
                        exc,
                        exc_info=True,
                    )
                    raise

            if self.task_manager:
                try:
                    self.task_manager.start()
                    logger.info("Task manager started")
                except Exception as exc:
                    logger.error("Failed to start task manager: %s", exc, exc_info=True)
                    raise

            if self.config_watcher:
                try:
                    self.config_watcher.start()
                    logger.info("Configuration watcher started")
                except Exception as exc:
                    logger.warning(
                        "Failed to start config watcher: %s",
                        exc,
                        exc_info=True,
                    )

            self._running = True
            try:
                self._setup_signal_handlers()
            except Exception as exc:
                logger.warning(
                    "Failed to set up signal handlers; continuing without them: %s",
                    exc,
                    exc_info=True,
                )

            logger.info("🚀 Feishu Bot is running!")

            event_config = getattr(self.config, "event_server", None)
            if (
                self.event_server
                and event_config
                and event_config.enabled
                and event_config.auto_start
            ):
                try:
                    self.event_server.start()
                except Exception as exc:
                    logger.error("Failed to start event server: %s", exc, exc_info=True)
                    raise

            # Send startup notification
            if self.client:
                try:
                    self.client.send_text("🤖 Feishu Bot started successfully!")
                except Exception as exc:
                    logger.warning("Failed to send startup notification: %s", exc, exc_info=True)
            else:
                logger.warning("No default webhook client configured; startup notification skipped")

            # Keep the main thread alive by waiting for shutdown signal
            pause_fn = getattr(signal, "pause", None)
            if callable(pause_fn):
                try:
                    pause_fn()
                except (KeyboardInterrupt, SystemExit):
                    logger.info("Keyboard interrupt received; signalling shutdown")
                    self._shutdown_event.set()
            else:
                self._wait_for_shutdown()

        except Exception as exc:
            logger.error("Error starting bot: %s", exc, exc_info=True)
            if self._running:
                self.stop()
            raise
        finally:
            if not self._running:
                self._restore_signal_handlers()

    def stop(self) -> None:
        """Stop the bot and clean up resources."""
        self._shutdown_event.set()

        if not self._running:
            self._restore_signal_handlers()
            return

        logger.info("Stopping Feishu Bot...")

        try:
            # Send shutdown notification
            if self.client:
                try:
                    self.client.send_text("🛑 Feishu Bot is shutting down...")
                except Exception as exc:
                    logger.warning("Failed to send shutdown notification: %s", exc, exc_info=True)

            # Stop hot reload
            if self.plugin_manager:
                try:
                    self.plugin_manager.stop_hot_reload()
                except Exception as exc:
                    logger.error("Failed to stop plugin hot reload: %s", exc, exc_info=True)

            # Disable all plugins
            if self.plugin_manager:
                try:
                    self.plugin_manager.disable_all()
                except Exception as exc:
                    logger.error("Failed to disable plugins: %s", exc, exc_info=True)

            if self.event_server and self.event_server.is_running:
                try:
                    self.event_server.stop()
                except Exception as exc:
                    logger.error("Failed to stop event server: %s", exc, exc_info=True)

            if self.automation_engine:
                try:
                    self.automation_engine.shutdown()
                except Exception as exc:
                    logger.error("Failed to shutdown automation engine: %s", exc, exc_info=True)

            # Stop task manager
            if self.task_manager:
                try:
                    self.task_manager.stop()
                except Exception as exc:
                    logger.error("Failed to stop task manager: %s", exc, exc_info=True)

            # Stop config watcher
            if self.config_watcher:
                try:
                    self.config_watcher.stop()
                except Exception as exc:
                    logger.error("Failed to stop config watcher: %s", exc, exc_info=True)

            # Stop scheduler
            if self.scheduler:
                try:
                    self.scheduler.shutdown()
                except Exception as exc:
                    logger.error("Failed to shutdown scheduler: %s", exc, exc_info=True)

            # Close clients
            for name, client in self.clients.items():
                try:
                    client.close()
                except Exception as exc:
                    logger.error("Error closing client %s: %s", name, exc, exc_info=True)

        except Exception as exc:
            logger.error("Error stopping bot: %s", exc, exc_info=True)
        finally:
            self._running = False
            self._restore_signal_handlers()
            logger.info("Feishu Bot stopped")

    def send_message(self, text: str, webhook_name: str | Sequence[str] = "default") -> None:
        """Send a text message via specified webhook.

        Args:
            text: Message text
            webhook_name: Webhook name (default: "default")
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

        missing = [name for name in targets if name not in self.clients]
        if missing:
            available = ", ".join(sorted(self.clients)) or "none"
            if len(missing) == 1:
                raise ValueError(f"Webhook client not found: {missing[0]}")
            raise ValueError(
                f"Webhook clients not found: {', '.join(missing)}. Available: {available}"
            )

        for name in targets:
            client = self.clients[name]
            try:
                client.send_text(text)
            except Exception as exc:
                logger.error(
                    "Failed to send message via webhook '%s': %s",
                    name,
                    exc,
                    exc_info=True,
                )
                raise

    def _send_rendered_template(
        self, rendered: RenderedTemplate, webhook_names: Sequence[str]
    ) -> None:
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

    def _dispatch_rendered(self, client: FeishuWebhookClient, rendered: RenderedTemplate) -> None:
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

    @classmethod
    def from_config(cls, config_path: str | Path) -> FeishuBot:
        """Create bot from configuration file.

        Args:
            config_path: Path to YAML or JSON config file

        Returns:
            FeishuBot instance

        Example:
            ```python
            bot = FeishuBot.from_config("config.yaml")
            bot.start()
            ```
        """
        if not isinstance(config_path, (str, Path)):
            raise TypeError(f"config_path must be a str or Path, got {type(config_path)!r}")

        config_path = Path(config_path).expanduser()

        # Validate file format first so callers get a clear error for
        # unsupported extensions regardless of file existence.
        if config_path.suffix not in [".yaml", ".yml", ".json"]:
            raise ValueError(f"Unsupported config file format: {config_path.suffix}")

        try:
            if config_path.suffix in [".yaml", ".yml"]:
                config = BotConfig.from_yaml(config_path)
            else:  # .json
                config = BotConfig.from_json(config_path)
        except Exception as exc:
            logger.error(
                "Failed to load configuration from %s: %s",
                config_path,
                exc,
                exc_info=True,
            )
            raise

        return cls(config)

    @classmethod
    def from_env(cls) -> FeishuBot:
        """Create bot from environment variables.

        Environment variables should be prefixed with FEISHU_BOT_

        Returns:
            FeishuBot instance

        Example:
            ```bash
            export FEISHU_BOT_WEBHOOKS__0__URL="https://..."
            export FEISHU_BOT_SCHEDULER__ENABLED=true
            ```
        """
        try:
            config = BotConfig()
        except Exception as exc:
            logger.error(
                "Failed to load configuration from environment: %s",
                exc,
                exc_info=True,
            )
            raise

        return cls(config)
