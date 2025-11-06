"""Plugin manager for loading, managing, and hot-reloading plugins."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
import time
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ..core.client import FeishuWebhookClient
from ..core.config import BotConfig, PluginConfig
from ..core.logger import get_logger
from .base import BasePlugin

logger = get_logger("plugin_manager")


class PluginFileHandler(FileSystemEventHandler):
    """File system event handler for plugin hot-reload."""

    def __init__(self, manager: PluginManager, delay: float = 1.0):
        """Initialize the handler.

        Args:
            manager: Plugin manager instance
            delay: Delay before reloading (to debounce multiple events)
        """
        self.manager = manager
        self.delay = delay
        self._pending_reload = False
        self._last_event_time = 0.0

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        # Only watch Python files
        if not event.src_path.endswith(".py"):
            return

        current_time = time.time()
        if current_time - self._last_event_time < self.delay:
            return

        self._last_event_time = current_time
        logger.info(f"Plugin file changed: {event.src_path}")

        # Reload plugins after delay
        self.manager.reload_plugins()


class PluginManager:
    """Manager for loading and managing plugins.

    The plugin manager handles:
    - Plugin discovery and loading
    - Plugin lifecycle management
    - Hot-reloading of plugins
    - Job registration for plugins

    Example:
        ```python
        from feishu_webhook_bot.plugins import PluginManager

        manager = PluginManager(config, client, scheduler)
        manager.load_plugins()
        manager.enable_all()

        # Later, when shutting down
        manager.disable_all()
        ```
    """

    def __init__(
        self,
        config: BotConfig,
        client: FeishuWebhookClient,
        scheduler: Any = None,
    ):
        """Initialize the plugin manager.

        Args:
            config: Bot configuration
            client: Feishu webhook client
            scheduler: Task scheduler instance (optional)
        """
        self.config = config
        self.client = client
        self.scheduler = scheduler
        self.plugins: dict[str, BasePlugin] = {}
        self._observer: Observer | None = None

    def _discover_plugins(self, plugin_dir: Path) -> list[Path]:
        """Discover plugin files in the plugin directory.

        Args:
            plugin_dir: Directory to search for plugins

        Returns:
            List of plugin file paths
        """
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return []

        plugin_files = []
        for path in plugin_dir.glob("*.py"):
            if path.name.startswith("_"):
                continue
            plugin_files.append(path)

        logger.info(f"Discovered {len(plugin_files)} plugin files")
        return plugin_files

    def _load_plugin_from_file(self, file_path: Path) -> BasePlugin | None:
        """Load a plugin from a Python file.

        Args:
            file_path: Path to plugin file

        Returns:
            Plugin instance or None if loading failed
        """
        try:
            # Generate module name
            module_name = f"feishu_bot_plugin_{file_path.stem}"

            # If module already loaded, reload it
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                # Load module from file
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    logger.error(f"Failed to load spec for plugin: {file_path}")
                    return None

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            # Find plugin class (subclass of BasePlugin)
            plugin_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BasePlugin)
                    and obj is not BasePlugin
                    and obj.__module__ == module_name
                ):
                    plugin_class = obj
                    break

            if plugin_class is None:
                logger.error(f"No plugin class found in: {file_path}")
                return None

            # Instantiate plugin
            plugin = plugin_class(self.config, self.client)
            logger.info(f"Loaded plugin: {plugin.metadata().name} from {file_path.name}")
            return plugin

        except Exception as e:
            logger.error(f"Error loading plugin from {file_path}: {e}", exc_info=True)
            return None

    def load_plugins(self) -> None:
        """Discover and load all plugins from the plugin directory."""
        if not self.config.plugins.enabled:
            logger.info("Plugin system is disabled")
            return

        plugin_dir = Path(self.config.plugins.plugin_dir)
        plugin_files = self._discover_plugins(plugin_dir)

        for file_path in plugin_files:
            plugin = self._load_plugin_from_file(file_path)
            if plugin:
                metadata = plugin.metadata()
                self.plugins[metadata.name] = plugin
                plugin.on_load()

        logger.info(f"Loaded {len(self.plugins)} plugins")

    def reload_plugins(self) -> None:
        """Reload all plugins (for hot-reload)."""
        logger.info("Reloading plugins...")

        # Disable and unload existing plugins
        for plugin in self.plugins.values():
            try:
                plugin.on_disable()
                plugin.on_unload()
                plugin.cleanup_jobs()
            except Exception as e:
                logger.error(f"Error unloading plugin {plugin.metadata().name}: {e}")

        # Clear plugin dict
        self.plugins.clear()

        # Reload plugins
        self.load_plugins()

        # Re-enable plugins
        self.enable_all()

        logger.info("Plugin reload complete")

    def enable_plugin(self, name: str) -> bool:
        """Enable a specific plugin.

        Args:
            name: Plugin name

        Returns:
            True if plugin was enabled, False otherwise
        """
        plugin = self.plugins.get(name)
        if not plugin:
            logger.warning(f"Plugin not found: {name}")
            return False

        try:
            # Patch register_job to actually register with scheduler
            if self.scheduler:
                original_register = plugin.register_job

                def patched_register(
                    func: Any,
                    trigger: str = "interval",
                    job_id: str | None = None,
                    **trigger_args: Any,
                ) -> str:
                    if job_id is None:
                        job_id = f"plugin.{name}.{func.__name__}"
                    actual_job_id = self.scheduler.add_job(
                        func, trigger=trigger, job_id=job_id, **trigger_args
                    )
                    plugin._job_ids.append(actual_job_id)
                    return actual_job_id

                plugin.register_job = patched_register  # type: ignore

            plugin.on_enable()
            logger.info(f"Plugin enabled: {name}")
            return True

        except Exception as e:
            logger.error(f"Error enabling plugin {name}: {e}", exc_info=True)
            return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a specific plugin.

        Args:
            name: Plugin name

        Returns:
            True if plugin was disabled, False otherwise
        """
        plugin = self.plugins.get(name)
        if not plugin:
            logger.warning(f"Plugin not found: {name}")
            return False

        try:
            # Remove all jobs registered by this plugin
            if self.scheduler:
                for job_id in plugin._job_ids:
                    try:
                        self.scheduler.remove_job(job_id)
                    except Exception as e:
                        logger.warning(f"Error removing job {job_id}: {e}")

            plugin.on_disable()
            plugin.cleanup_jobs()
            logger.info(f"Plugin disabled: {name}")
            return True

        except Exception as e:
            logger.error(f"Error disabling plugin {name}: {e}", exc_info=True)
            return False

    def enable_all(self) -> None:
        """Enable all loaded plugins."""
        for name in self.plugins:
            self.enable_plugin(name)

    def disable_all(self) -> None:
        """Disable all loaded plugins."""
        for name in self.plugins:
            self.disable_plugin(name)

    def get_plugin(self, name: str) -> BasePlugin | None:
        """Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None
        """
        return self.plugins.get(name)

    def list_plugins(self) -> list[str]:
        """Get list of loaded plugin names.

        Returns:
            List of plugin names
        """
        return list(self.plugins.keys())

    def start_hot_reload(self) -> None:
        """Start watching for plugin file changes."""
        if not self.config.plugins.auto_reload:
            logger.info("Hot reload is disabled")
            return

        plugin_dir = Path(self.config.plugins.plugin_dir)
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return

        event_handler = PluginFileHandler(self, delay=self.config.plugins.reload_delay)
        self._observer = Observer()
        self._observer.schedule(event_handler, str(plugin_dir), recursive=False)
        self._observer.start()

        logger.info(f"Hot reload enabled for: {plugin_dir}")

    def stop_hot_reload(self) -> None:
        """Stop watching for plugin file changes."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Hot reload stopped")
