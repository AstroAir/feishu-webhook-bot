"""Configuration file watcher for hot-reloading."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from watchdog.observers import Observer

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer as ObserverClass

from .config import BotConfig
from .logger import get_logger
from .validation import validate_yaml_config

logger = get_logger("config.watcher")


class ConfigFileHandler(FileSystemEventHandler):
    """Handler for configuration file changes."""

    def __init__(
        self,
        config_path: Path,
        reload_callback: Callable[[BotConfig], None],
        reload_delay: float = 1.0,
    ):
        """Initialize config file handler.

        Args:
            config_path: Path to the configuration file
            reload_callback: Callback function to call when config is reloaded
            reload_delay: Delay in seconds before reloading after change detected
        """
        self.config_path = config_path.resolve()
        self.reload_callback = reload_callback
        self.reload_delay = reload_delay
        self._last_reload_time = 0.0
        self._pending_reload = False

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        # Check if the modified file is our config file
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path_str = src_path.decode("utf-8")
        elif isinstance(src_path, (bytearray, memoryview)):
            src_path_str = bytes(src_path).decode("utf-8")
        else:
            src_path_str = str(src_path)
        event_path = Path(src_path_str).resolve()
        if event_path != self.config_path:
            return

        # Debounce: ignore if we just reloaded
        current_time = time.time()
        if current_time - self._last_reload_time < self.reload_delay:
            return

        logger.info(f"Configuration file changed: {self.config_path}")
        self._schedule_reload()

    def _schedule_reload(self) -> None:
        """Schedule a configuration reload."""
        if self._pending_reload:
            return

        self._pending_reload = True

        # Wait for the delay period
        time.sleep(self.reload_delay)

        try:
            self._reload_config()
        finally:
            self._pending_reload = False
            self._last_reload_time = time.time()

    def _reload_config(self) -> None:
        """Reload the configuration file."""
        logger.info("Reloading configuration...")

        # Validate first
        is_valid, errors = validate_yaml_config(self.config_path)
        if not is_valid:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            logger.error("Configuration not reloaded due to validation errors")
            return

        # Load new configuration
        try:
            new_config = BotConfig.from_yaml(self.config_path)
            logger.info("Configuration loaded successfully")

            # Call reload callback
            self.reload_callback(new_config)
            logger.info("Configuration reloaded successfully")

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}", exc_info=True)


class ConfigWatcher:
    """Watches configuration file for changes and triggers reloads."""

    def __init__(
        self,
        config_path: str | Path,
        reload_callback: Callable[[BotConfig], None],
        reload_delay: float = 1.0,
    ):
        """Initialize configuration watcher.

        Args:
            config_path: Path to the configuration file
            reload_callback: Callback function to call when config is reloaded
            reload_delay: Delay in seconds before reloading after change detected

        Example:
            ```python
            def on_config_reload(new_config: BotConfig):
                print("Config reloaded!")
                # Update bot with new config

            watcher = ConfigWatcher("config.yaml", on_config_reload)
            watcher.start()

            # Later...
            watcher.stop()
            ```
        """
        self.config_path = Path(config_path).resolve()
        self.reload_callback = reload_callback
        self.reload_delay = reload_delay
        self._observer: Observer | None = None  # type: ignore[valid-type]
        self._handler: ConfigFileHandler | None = None

    def start(self) -> None:
        """Start watching the configuration file."""
        if self._observer is not None:
            logger.warning("Config watcher already started")
            return

        if not self.config_path.exists():
            logger.error(f"Configuration file not found: {self.config_path}")
            return

        logger.info(f"Starting config watcher for {self.config_path}")

        # Create handler
        self._handler = ConfigFileHandler(
            self.config_path,
            self.reload_callback,
            self.reload_delay,
        )

        # Create observer
        self._observer = ObserverClass()

        # Watch the directory containing the config file
        watch_dir = self.config_path.parent
        self._observer.schedule(self._handler, str(watch_dir), recursive=False)

        # Start observer
        self._observer.start()
        logger.info("Config watcher started")

    def stop(self) -> None:
        """Stop watching the configuration file."""
        if self._observer is None:
            return

        logger.info("Stopping config watcher...")
        self._observer.stop()
        self._observer.join()
        self._observer = None
        self._handler = None
        logger.info("Config watcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is running.

        Returns:
            True if watcher is running, False otherwise
        """
        return self._observer is not None and self._observer.is_alive()


def create_config_watcher(
    config_path: str | Path,
    bot_instance: Any,
    reload_delay: float = 1.0,
) -> ConfigWatcher:
    """Create a configuration watcher for a bot instance.

    This is a convenience function that creates a watcher with a callback
    that updates the bot instance with the new configuration.

    Args:
        config_path: Path to the configuration file
        bot_instance: Bot instance to update on config reload
        reload_delay: Delay in seconds before reloading

    Returns:
        ConfigWatcher instance

    Example:
        ```python
        bot = FeishuBot.from_yaml("config.yaml")
        watcher = create_config_watcher("config.yaml", bot)
        watcher.start()
        ```
    """

    def reload_callback(new_config: BotConfig) -> None:
        """Callback to reload bot configuration with comprehensive component updates."""
        old_config = getattr(bot_instance, "config", None)
        components_reloaded: list[str] = []

        try:
            # Apply environment overrides if configured
            if new_config.active_environment:
                new_config = new_config.apply_environment_overrides()

            # Validate configuration changes
            warnings = _validate_config_changes(old_config, new_config)
            for warning in warnings:
                logger.warning(f"Config change warning: {warning}")

            # Update bot configuration
            bot_instance.config = new_config

            # Reload plugins
            if hasattr(bot_instance, "plugin_manager") and bot_instance.plugin_manager:
                logger.info("Reloading plugins...")
                try:
                    bot_instance.plugin_manager.reload_plugins()
                    components_reloaded.append("plugins")
                except Exception as e:
                    logger.error(f"Failed to reload plugins: {e}")

            # Reload task manager
            if hasattr(bot_instance, "task_manager") and bot_instance.task_manager:
                logger.info("Reloading tasks...")
                try:
                    bot_instance.task_manager.config = new_config
                    if hasattr(bot_instance.task_manager, "reload_tasks"):
                        bot_instance.task_manager.reload_tasks()
                    components_reloaded.append("tasks")
                except Exception as e:
                    logger.error(f"Failed to reload tasks: {e}")

            # Reload automation engine
            if hasattr(bot_instance, "automation_engine") and bot_instance.automation_engine:
                logger.info("Reloading automations...")
                try:
                    # Update automation rules
                    if hasattr(bot_instance.automation_engine, "_rules"):
                        bot_instance.automation_engine._rules = new_config.automations
                    # Restart automation engine
                    bot_instance.automation_engine.shutdown()
                    bot_instance.automation_engine.start()
                    components_reloaded.append("automations")
                except Exception as e:
                    logger.error(f"Failed to reload automations: {e}")

            # Reload template registry
            if hasattr(bot_instance, "template_registry"):
                logger.info("Reloading templates...")
                try:
                    from .templates import TemplateRegistry

                    bot_instance.template_registry = TemplateRegistry(new_config.templates or [])
                    # Update template_registry reference in task_manager
                    if hasattr(bot_instance, "task_manager") and bot_instance.task_manager:
                        bot_instance.task_manager.template_registry = bot_instance.template_registry
                    components_reloaded.append("templates")
                except Exception as e:
                    logger.error(f"Failed to reload templates: {e}")

            # Reload AI agent configuration (if AI config changed)
            if hasattr(bot_instance, "ai_agent") and bot_instance.ai_agent:
                ai_config = getattr(new_config, "ai", None)
                old_ai_config = getattr(old_config, "ai", None) if old_config else None

                if ai_config and ai_config != old_ai_config:
                    logger.info("AI configuration changed, updating agent...")
                    try:
                        # Update AI agent config
                        bot_instance.ai_agent.config = ai_config
                        components_reloaded.append("ai_agent")
                    except Exception as e:
                        logger.error(f"Failed to update AI agent: {e}")

            # Reload event server configuration
            if hasattr(bot_instance, "event_server") and bot_instance.event_server:
                event_config = getattr(new_config, "event_server", None)
                if event_config:
                    logger.info("Updating event server configuration...")
                    try:
                        # Event server may need restart for port changes
                        # For now, just update config reference
                        bot_instance.event_server.config = event_config
                        components_reloaded.append("event_server")
                    except Exception as e:
                        logger.error(f"Failed to update event server: {e}")

            logger.info(
                "Bot configuration reloaded successfully. Components: %s",
                ", ".join(components_reloaded) if components_reloaded else "none",
            )

        except Exception as e:
            logger.error(f"Failed to apply new configuration to bot: {e}", exc_info=True)
            # Attempt to rollback to old config
            if old_config:
                logger.info("Attempting to rollback to previous configuration...")
                try:
                    bot_instance.config = old_config
                    logger.info("Rollback successful")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")

    return ConfigWatcher(config_path, reload_callback, reload_delay)


def _validate_config_changes(old_config: BotConfig | None, new_config: BotConfig) -> list[str]:
    """Validate configuration changes and return warnings.

    Args:
        old_config: Previous configuration (None if first load)
        new_config: New configuration

    Returns:
        List of warning messages about potentially breaking changes
    """
    warnings: list[str] = []

    if old_config is None:
        return warnings

    # Check for removed webhooks
    old_webhooks = {w.name for w in (old_config.webhooks or [])}
    new_webhooks = {w.name for w in (new_config.webhooks or [])}
    removed_webhooks = old_webhooks - new_webhooks
    if removed_webhooks:
        warnings.append(
            f"Webhooks removed: {', '.join(removed_webhooks)} - tasks using these webhooks may fail"
        )

    # Check if all webhooks were removed
    if old_webhooks and not new_webhooks:
        warnings.append("All webhooks removed - message sending will be unavailable")

    # Check scheduler status change
    old_scheduler = getattr(old_config, "scheduler", None)
    new_scheduler = getattr(new_config, "scheduler", None)
    if old_scheduler and new_scheduler and old_scheduler.enabled and not new_scheduler.enabled:
        warnings.append("Scheduler disabled - scheduled tasks will stop running")

    # Check AI status change
    old_ai = getattr(old_config, "ai", None)
    new_ai = getattr(new_config, "ai", None)
    if old_ai and new_ai:
        if old_ai.enabled and not new_ai.enabled:
            warnings.append("AI disabled - AI-powered tasks will fail")
        elif old_ai.model != new_ai.model:
            warnings.append(f"AI model changed from {old_ai.model} to {new_ai.model}")

    return warnings
