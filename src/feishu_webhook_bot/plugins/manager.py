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
from ..core.config import BotConfig
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
        if not str(event.src_path).endswith(".py"):
            return

        current_time = time.time()
        if current_time - self._last_event_time < self.delay:
            return

        self._last_event_time = current_time
        logger.info(f"Plugin file changed: {event.src_path}")

        # Reload plugins after delay
        self.manager.reload_plugins()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory or not str(event.src_path).endswith(".py"):
            return
        current_time = time.time()
        # Debounce creation events to avoid duplicate reloads (create -> mod)
        if current_time - self._last_event_time < self.delay:
            return
        self._last_event_time = current_time
        logger.info(f"New plugin file detected: {event.src_path}")
        self.manager.reload_plugins()

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if event.is_directory or not str(event.src_path).endswith(".py"):
            return
        logger.info(f"Plugin file deleted: {event.src_path}")
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

            # If module already loaded, try to reload it. If the existing
            # module has no spec (can happen for modules loaded from a
            # previous dynamic import), remove it and load fresh.
            if module_name in sys.modules:
                # Always drop the previous module to avoid reload issues when
                # specs are missing (common with dynamically loaded modules
                # under test environments).
                del sys.modules[module_name]

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
            for _name, obj in inspect.getmembers(module, inspect.isclass):
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

        # Sort plugins by priority if configured
        plugin_priorities: dict[str, int] = {}
        for plugin_setting in self.config.plugins.plugin_settings:
            plugin_priorities[plugin_setting.plugin_name] = plugin_setting.priority

        # Load plugins
        loaded_plugins: list[tuple[str, BasePlugin, int]] = []
        for file_path in plugin_files:
            plugin = self._load_plugin_from_file(file_path)
            if plugin:
                metadata = plugin.metadata()

                # Check if plugin is disabled in configuration
                plugin_enabled = True
                for plugin_setting in self.config.plugins.plugin_settings:
                    if plugin_setting.plugin_name == metadata.name:
                        plugin_enabled = plugin_setting.enabled
                        break

                if not plugin_enabled:
                    logger.info(f"Plugin {metadata.name} is disabled in configuration")
                    continue

                priority = plugin_priorities.get(metadata.name, 100)
                loaded_plugins.append((metadata.name, plugin, priority))

        # Sort by priority (lower numbers first)
        loaded_plugins.sort(key=lambda x: x[2])

        # Register plugins in priority order
        for name, plugin, _ in loaded_plugins:
            self.plugins[name] = plugin
            plugin.on_load()
            logger.info(f"Loaded plugin: {name}")

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

                # Patch cleanup to remove jobs from the scheduler when the
                # plugin is disabled.
                def patched_cleanup() -> None:
                    try:
                        for jid in list(plugin._job_ids):
                            try:
                                self.scheduler.remove_job(jid)
                            except Exception:
                                logger.exception("Failed to remove job %s", jid)
                        plugin._job_ids.clear()
                    except Exception as e:
                        logger.error("Error during plugin cleanup: %s", e)

                plugin.cleanup_jobs = patched_cleanup  # type: ignore

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
        observer = Observer()
        observer.schedule(event_handler, str(plugin_dir), recursive=False)
        observer.start()
        self._observer = observer

        logger.info(f"Hot reload enabled for: {plugin_dir}")

    def stop_hot_reload(self) -> None:
        """Stop watching for plugin file changes."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Hot reload stopped")

    def dispatch_event(self, event: dict[str, Any], context: dict[str, Any] | None = None) -> None:
        """Forward an inbound event to all loaded plugins."""

        for plugin in self.plugins.values():
            handler = getattr(plugin, "handle_event", None)
            if not handler:
                continue
            try:
                handler(event, context or {})
            except Exception as exc:
                metadata = plugin.metadata()
                logger.error(
                    "Plugin '%s' failed to handle event: %s",
                    metadata.name,
                    exc,
                    exc_info=True,
                )
