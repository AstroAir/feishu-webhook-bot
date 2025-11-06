"""Main bot class that orchestrates all components."""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import Any

from .core import BotConfig, FeishuWebhookClient, get_logger, setup_logging
from .core.config import WebhookConfig
from .plugins import PluginManager
from .scheduler import TaskScheduler

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
        self.config = config
        self._setup_logging()

        # Initialize components
        self.client: FeishuWebhookClient | None = None
        self.scheduler: TaskScheduler | None = None
        self.plugin_manager: PluginManager | None = None
        self._running = False

        # Eagerly initialize core components so they are available immediately
        # without requiring an explicit start() call. This aligns with tests and
        # provides a ready-to-use bot instance.
        try:
            self._init_client()
            self._init_scheduler()
            self._init_plugins()
        except Exception as e:
            # Log but don't raise here to allow construction to succeed for
            # environments where optional components may fail.
            logger.warning(f"Initialization warning: {e}")

        logger.info("Feishu Bot initialized")

    def _setup_logging(self) -> None:
        """Setup logging based on configuration."""
        setup_logging(self.config.logging)

    def _init_client(self) -> None:
        """Initialize webhook client with default webhook."""
        default_webhook = self.config.get_webhook("default")
        if not default_webhook:
            if self.config.webhooks:
                default_webhook = self.config.webhooks[0]
            else:
                logger.warning("No webhook configured, using placeholder")
                default_webhook = WebhookConfig(
                    url="https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL"
                )

        self.client = FeishuWebhookClient(default_webhook)
        logger.info(f"Webhook client initialized: {default_webhook.name}")

    def _init_scheduler(self) -> None:
        """Initialize task scheduler if enabled."""
        if not self.config.scheduler.enabled:
            logger.info("Scheduler is disabled")
            return

        self.scheduler = TaskScheduler(self.config.scheduler)
        logger.info("Scheduler initialized")

    def _init_plugins(self) -> None:
        """Initialize plugin manager and load plugins."""
        if not self.config.plugins.enabled:
            logger.info("Plugin system is disabled")
            return

        if not self.client:
            raise RuntimeError("Client must be initialized before plugins")

        self.plugin_manager = PluginManager(
            self.config, self.client, self.scheduler
        )
        self.plugin_manager.load_plugins()

        # Enable all plugins
        self.plugin_manager.enable_all()

        # Start hot reload if enabled
        if self.config.plugins.auto_reload:
            self.plugin_manager.start_hot_reload()

        logger.info("Plugin system initialized")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(sig: int, frame: Any) -> None:
            logger.info(f"Received signal {sig}, shutting down...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start(self) -> None:
        """Start the bot.

        This initializes all components and starts the scheduler.
        The bot will run until interrupted.
        """
        if self._running:
            logger.warning("Bot is already running")
            return

        logger.info("Starting Feishu Bot...")

        try:
            # Initialize components
            self._init_client()
            self._init_scheduler()
            self._init_plugins()

            # Start scheduler
            if self.scheduler:
                self.scheduler.start()
                logger.info("Scheduler started")

            self._running = True
            self._setup_signal_handlers()

            logger.info("🚀 Feishu Bot is running!")

            # Send startup notification
            if self.client:
                try:
                    self.client.send_text("🤖 Feishu Bot started successfully!")
                except Exception as e:
                    logger.warning(f"Failed to send startup notification: {e}")

            # Keep the main thread alive
            if self.scheduler and self.scheduler._scheduler:
                # Block until scheduler is stopped
                while self._running and self.scheduler._scheduler.running:
                    import time
                    time.sleep(1)

        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            self.stop()
            raise

    def stop(self) -> None:
        """Stop the bot and clean up resources."""
        if not self._running:
            return

        logger.info("Stopping Feishu Bot...")

        try:
            # Send shutdown notification
            if self.client:
                try:
                    self.client.send_text("🛑 Feishu Bot is shutting down...")
                except Exception:
                    pass  # Ignore errors during shutdown

            # Stop hot reload
            if self.plugin_manager:
                self.plugin_manager.stop_hot_reload()

            # Disable all plugins
            if self.plugin_manager:
                self.plugin_manager.disable_all()

            # Stop scheduler
            if self.scheduler:
                self.scheduler.shutdown()

            # Close client
            if self.client:
                self.client.close()

            self._running = False
            logger.info("Feishu Bot stopped")

        except Exception as e:
            logger.error(f"Error stopping bot: {e}", exc_info=True)

    def send_message(self, text: str, webhook_name: str = "default") -> None:
        """Send a text message via specified webhook.

        Args:
            text: Message text
            webhook_name: Webhook name (default: "default")
        """
        webhook = self.config.get_webhook(webhook_name)
        if not webhook:
            raise ValueError(f"Webhook not found: {webhook_name}")

        with FeishuWebhookClient(webhook) as client:
            client.send_text(text)

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
        config_path = Path(config_path)

        if config_path.suffix in [".yaml", ".yml"]:
            config = BotConfig.from_yaml(config_path)
        elif config_path.suffix == ".json":
            config = BotConfig.from_json(config_path)
        else:
            raise ValueError(f"Unsupported config file format: {config_path.suffix}")

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
        config = BotConfig()
        return cls(config)
