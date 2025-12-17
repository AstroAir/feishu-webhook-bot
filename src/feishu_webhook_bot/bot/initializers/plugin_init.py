"""Plugin initialization mixin for FeishuBot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core import get_logger
from ...plugins import PluginManager

if TYPE_CHECKING:
    from ..base import BotBase

logger = get_logger("bot.init.plugin")


class PluginInitializerMixin:
    """Mixin for plugin system initialization."""

    def _init_plugins(self: BotBase) -> None:
        """Initialize plugin manager and load plugins."""
        plugins_config = getattr(self.config, "plugins", None)
        if plugins_config is None:
            logger.warning("Plugin configuration missing; plugin system disabled")
            return

        if not plugins_config.enabled:
            logger.info("Plugin system is disabled")
            return

        # Check for either legacy client or new providers
        if not self.client and not self.providers:
            logger.warning(
                "No webhook client or providers available; skipping plugin initialization"
            )
            return

        try:
            # Pass both client (backward compat) and providers (new architecture)
            self.plugin_manager = PluginManager(
                self.config,
                self.client or self.default_provider,
                self.scheduler,
                providers=self.providers,
            )
        except Exception as exc:
            logger.error("Failed to initialize plugin manager: %s", exc, exc_info=True)
            raise

        try:
            self.plugin_manager.load_plugins()
            self.plugin_manager.enable_all()
        except Exception as exc:
            logger.error("Failed to load or enable plugins: %s", exc, exc_info=True)
            raise

        # Validate plugin configurations at startup
        self._validate_plugin_configs()

        # Start hot reload if enabled
        if plugins_config.auto_reload:
            try:
                self.plugin_manager.start_hot_reload()
            except Exception as exc:
                logger.error("Failed to start plugin hot reload: %s", exc, exc_info=True)
                raise

        logger.info("Plugin system initialized")

    def _validate_plugin_configs(self: BotBase) -> None:
        """Validate all loaded plugin configurations at startup.

        This method checks each plugin's configuration against its schema
        (if defined) and logs warnings for missing or invalid configurations.
        """
        if not self.plugin_manager:
            return

        try:
            from ...plugins.config_validator import ConfigValidator

            validator = ConfigValidator(self.config)
            plugins = self.plugin_manager.get_all_plugins()

            if not plugins:
                return

            report = validator.generate_startup_report(plugins)

            if report.all_valid:
                logger.info(
                    "All %d plugin(s) have valid configurations",
                    len(report.plugins_ready),
                )
            else:
                # Log warnings for plugins needing configuration
                for plugin_name in report.plugins_need_config:
                    result = next(
                        (r for r in report.results if r.plugin_name == plugin_name),
                        None,
                    )
                    if result:
                        if result.missing_required:
                            logger.warning(
                                "Plugin '%s' missing required configuration: %s. "
                                "Run 'feishu-webhook-bot plugin setup %s' to configure.",
                                plugin_name,
                                ", ".join(result.missing_required[:3]),
                                plugin_name,
                            )
                        for error in result.errors[:2]:
                            logger.warning(
                                "Plugin '%s' configuration error: %s",
                                plugin_name,
                                error,
                            )

                # Print report if Rich is available
                try:
                    validator.print_report(report)
                except Exception:
                    # Fallback: just log the summary
                    logger.warning(
                        "%d plugin(s) need configuration: %s",
                        len(report.plugins_need_config),
                        ", ".join(report.plugins_need_config),
                    )

        except ImportError:
            logger.debug("Plugin configuration validation not available")
        except Exception as exc:
            logger.warning("Plugin configuration validation failed: %s", exc, exc_info=True)
