"""Configuration file watcher for hot-reloading."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

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
        event_path = Path(event.src_path).resolve()
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
        self._observer: Observer | None = None
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
        self._observer = Observer()
        
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
        """Callback to reload bot configuration."""
        try:
            # Apply environment overrides if configured
            if new_config.active_environment:
                new_config = new_config.apply_environment_overrides()

            # Update bot configuration
            bot_instance.config = new_config

            # Reload components that support hot-reload
            if hasattr(bot_instance, "plugin_manager") and bot_instance.plugin_manager:
                logger.info("Reloading plugins...")
                bot_instance.plugin_manager.reload_plugins()

            if hasattr(bot_instance, "task_manager") and bot_instance.task_manager:
                logger.info("Reloading tasks...")
                bot_instance.task_manager.reload_tasks()

            if hasattr(bot_instance, "automation_engine") and bot_instance.automation_engine:
                logger.info("Reloading automations...")
                # Stop old automations
                bot_instance.automation_engine.shutdown()
                # Recreate automation engine with new config
                # Note: This would need to be implemented in the bot class

            logger.info("Bot configuration reloaded successfully")

        except Exception as e:
            logger.error(f"Failed to apply new configuration to bot: {e}", exc_info=True)

    return ConfigWatcher(config_path, reload_callback, reload_delay)

