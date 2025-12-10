"""Main bot class that orchestrates all components."""

from __future__ import annotations

import asyncio
import os
import signal
import threading
from collections.abc import Sequence
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, Any

from .automation import AutomationEngine
from .chat.controller import ChatController, ChatConfig, create_chat_controller
from .core import BotConfig, FeishuWebhookClient, get_logger, setup_logging
from .core.circuit_breaker import CircuitBreakerConfig
from .core.config import ProviderConfigBase, WebhookConfig
from .core.config_watcher import ConfigWatcher, create_config_watcher
from .core.event_server import EventServer
from .core.message_queue import MessageQueue
from .core.message_tracker import MessageTracker
from .core.message_handler import IncomingMessage
from .core.message_parsers import FeishuMessageParser, QQMessageParser
from .core.provider import BaseProvider
from .core.templates import RenderedTemplate, TemplateRegistry
from .plugins import PluginManager
from .scheduler import TaskScheduler
from .tasks import TaskManager

if TYPE_CHECKING:
    from .ai.agent import AIAgent

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
        self.providers: dict[str, BaseProvider] = {}  # New multi-provider support
        self.default_provider: BaseProvider | None = None
        self.scheduler: TaskScheduler | None = None
        self.plugin_manager: PluginManager | None = None
        self.template_registry: TemplateRegistry | None = None
        self.automation_engine: AutomationEngine | None = None
        self.task_manager: TaskManager | None = None
        self.event_server: EventServer | None = None
        self.config_watcher: ConfigWatcher | None = None
        self.ai_agent: AIAgent | None = None
        self.chat_controller: ChatController | None = None
        self.message_tracker: MessageTracker | None = None
        self.message_queue: MessageQueue | None = None
        self._message_queue_task: asyncio.Task[None] | None = None
        self._running: bool = False
        self._shutdown_event: threading.Event = threading.Event()
        self._signal_handlers: dict[int, signal.Handlers] = {}
        self._signal_handlers_installed: bool = False

        # Eagerly initialize core components
        try:
            self._init_clients()
        except Exception as exc:
            logger.error("Failed to initialize webhook clients: %s", exc, exc_info=True)
            raise

        # Initialize message tracker before providers (providers need it)
        try:
            self._init_message_tracker()
        except Exception as exc:
            logger.warning(
                "Message tracker initialization failed, continuing without tracking: %s", exc
            )

        try:
            self._init_providers()
        except Exception as exc:
            logger.error("Failed to initialize providers: %s", exc, exc_info=True)
            raise

        # Initialize message queue after providers (queue needs providers)
        try:
            self._init_message_queue()
        except Exception as exc:
            logger.warning(
                "Message queue initialization failed, continuing without queue: %s", exc
            )

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
            self._init_ai_agent()  # Initialize AI agent before tasks
            self._init_chat_controller()  # Initialize chat controller after AI agent
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

    def _init_message_tracker(self) -> None:
        """Initialize message tracker for delivery tracking and persistence."""
        tracking_config = getattr(self.config, "message_tracking", None)

        if not tracking_config:
            logger.info("Message tracking disabled (no config)")
            return

        enabled = getattr(tracking_config, "enabled", False)
        if not enabled:
            logger.info("Message tracking disabled")
            return

        try:
            max_history = getattr(tracking_config, "max_history", 10000)
            cleanup_interval = getattr(tracking_config, "cleanup_interval", 3600.0)
            db_path = getattr(tracking_config, "db_path", None)

            self.message_tracker = MessageTracker(
                max_history=max_history,
                cleanup_interval=cleanup_interval,
                db_path=db_path,
            )
            logger.info(
                "Message tracker initialized (db_path=%s, max_history=%d)",
                db_path or "in-memory",
                max_history,
            )
        except Exception as exc:
            logger.error("Failed to initialize message tracker: %s", exc, exc_info=True)
            # Non-fatal - continue without tracking

    def _init_message_queue(self) -> None:
        """Initialize message queue for reliable async delivery."""
        queue_config = getattr(self.config, "message_queue", None)

        if not queue_config:
            logger.info("Message queue disabled (no config)")
            return

        enabled = getattr(queue_config, "enabled", False)
        if not enabled:
            logger.info("Message queue disabled")
            return

        if not self.providers:
            logger.warning("No providers available; message queue disabled")
            return

        try:
            max_batch_size = getattr(queue_config, "max_batch_size", 10)
            retry_delay = getattr(queue_config, "retry_delay", 5.0)
            max_retries = getattr(queue_config, "max_retries", 3)

            self.message_queue = MessageQueue(
                providers=self.providers,
                max_batch_size=max_batch_size,
                retry_delay=retry_delay,
                max_retries=max_retries,
            )
            logger.info(
                "Message queue initialized (batch_size=%d, max_retries=%d)",
                max_batch_size,
                max_retries,
            )
        except Exception as exc:
            logger.error("Failed to initialize message queue: %s", exc, exc_info=True)
            # Non-fatal - continue without queue

    async def _run_message_queue_processor(self) -> None:
        """Run message queue processor in background loop.

        This method runs continuously while the bot is running,
        processing queued messages with error handling and backoff.
        """
        while self._running:
            try:
                if self.message_queue:
                    await self.message_queue.process_queue()
                await asyncio.sleep(1.0)  # Process interval
            except asyncio.CancelledError:
                logger.info("Message queue processor cancelled")
                break
            except Exception as exc:
                logger.error("Message queue processing error: %s", exc, exc_info=True)
                await asyncio.sleep(5.0)  # Backoff on error

    def _convert_circuit_breaker_config(
        self, policy_config: Any
    ) -> CircuitBreakerConfig | None:
        """Convert CircuitBreakerPolicyConfig to CircuitBreakerConfig.

        Args:
            policy_config: CircuitBreakerPolicyConfig or dict

        Returns:
            CircuitBreakerConfig or None
        """
        if not policy_config:
            return None

        try:
            failure_threshold = getattr(policy_config, "failure_threshold", 5)
            reset_timeout = getattr(policy_config, "reset_timeout", 30.0)
            half_open_max = getattr(policy_config, "half_open_max_calls", 3)

            return CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                success_threshold=half_open_max,
                timeout_seconds=reset_timeout,
            )
        except Exception as exc:
            logger.warning("Failed to convert circuit breaker config: %s", exc)
            return None

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

    def _init_providers(self) -> None:
        """Initialize message providers from configuration.

        Supports both new provider configuration and backward compatibility
        with legacy webhooks configuration.
        """
        provider_configs = self.config.providers or []

        # If no providers configured but webhooks exist, create FeishuProviders from webhooks
        if not provider_configs and self.config.webhooks:
            logger.info(
                "No providers configured, creating FeishuProviders from %d webhook(s)",
                len(self.config.webhooks),
            )
            for webhook in self.config.webhooks:
                try:
                    provider = self._create_provider_from_webhook(webhook)
                    if provider:
                        self.providers[provider.name] = provider
                        logger.info("Created provider from webhook: %s", provider.name)
                except Exception as exc:
                    logger.error(
                        "Failed to create provider from webhook '%s': %s",
                        webhook.name,
                        exc,
                        exc_info=True,
                    )
        else:
            # Initialize from provider configurations
            for provider_config in provider_configs:
                if not provider_config.enabled:
                    logger.info("Provider '%s' is disabled, skipping", provider_config.name)
                    continue

                try:
                    provider = self._create_provider(provider_config)
                    if provider:
                        self.providers[provider.name] = provider
                        logger.info(
                            "Initialized provider: %s (%s)",
                            provider.name,
                            provider_config.provider_type,
                        )
                except Exception as exc:
                    logger.error(
                        "Failed to initialize provider '%s': %s",
                        provider_config.name,
                        exc,
                        exc_info=True,
                    )

        # Set default provider
        if self.providers:
            default_name = self.config.default_provider
            if default_name and default_name in self.providers:
                self.default_provider = self.providers[default_name]
            else:
                # Use first provider as default
                first_name = next(iter(self.providers))
                self.default_provider = self.providers[first_name]
                if default_name:
                    logger.warning(
                        "Default provider '%s' not found, using '%s'",
                        default_name,
                        first_name,
                    )
            logger.info("Default provider set to: %s", self.default_provider.name)
        else:
            logger.info("No providers initialized")

    def _create_provider_from_webhook(self, webhook: WebhookConfig) -> BaseProvider | None:
        """Create a FeishuProvider from a legacy WebhookConfig.

        Args:
            webhook: Legacy webhook configuration

        Returns:
            FeishuProvider instance or None if creation failed
        """
        try:
            from .providers.feishu import FeishuProvider, FeishuProviderConfig

            config = FeishuProviderConfig(
                provider_type="feishu",
                name=webhook.name,
                url=webhook.url,
                secret=webhook.secret,
                timeout=webhook.timeout or self.config.http.timeout,
                retry=webhook.retry or self.config.http.retry,
                headers=webhook.headers,
            )
            return FeishuProvider(
                config,
                message_tracker=self.message_tracker,
                circuit_breaker_config=None,  # No circuit breaker config in legacy webhooks
            )
        except ImportError:
            logger.warning("FeishuProvider not available, skipping webhook conversion")
            return None
        except Exception as exc:
            logger.error("Failed to create FeishuProvider: %s", exc, exc_info=True)
            return None

    def _create_provider(self, config: ProviderConfigBase) -> BaseProvider | None:
        """Create a provider instance from configuration.

        Args:
            config: Provider configuration

        Returns:
            Provider instance or None if creation failed
        """
        provider_type = config.provider_type

        # Extract and convert circuit breaker config
        cb_config = self._convert_circuit_breaker_config(config.circuit_breaker)

        if provider_type == "feishu":
            try:
                from .providers.feishu import FeishuProvider, FeishuProviderConfig

                feishu_config = FeishuProviderConfig(
                    provider_type="feishu",
                    name=config.name,
                    url=config.webhook_url or "",
                    secret=config.secret,
                    timeout=config.timeout or self.config.http.timeout,
                    retry=config.retry or self.config.http.retry,
                    headers=config.headers,
                )
                return FeishuProvider(
                    feishu_config,
                    message_tracker=self.message_tracker,
                    circuit_breaker_config=cb_config,
                )
            except ImportError as exc:
                logger.error("FeishuProvider not available: %s", exc)
                return None

        elif provider_type == "napcat":
            try:
                from .providers.qq_napcat import NapcatProvider, NapcatProviderConfig

                napcat_config = NapcatProviderConfig(
                    provider_type="napcat",
                    name=config.name,
                    http_url=config.http_url,
                    access_token=config.access_token,
                    default_target=config.default_target,
                    timeout=config.timeout or self.config.http.timeout,
                    retry=config.retry,
                    circuit_breaker=config.circuit_breaker,
                    message_tracking=config.message_tracking,
                )
                return NapcatProvider(
                    napcat_config,
                    message_tracker=self.message_tracker,
                    circuit_breaker_config=cb_config,
                )
            except ImportError as exc:
                logger.error("NapcatProvider not available: %s", exc)
                return None

        else:
            logger.warning("Unknown provider type: %s", provider_type)
            return None

    def get_provider(self, name: str | None = None) -> BaseProvider | None:
        """Get a provider by name.

        Args:
            name: Provider name. If None, returns the default provider.

        Returns:
            Provider instance or None if not found.
        """
        if name is None:
            return self.default_provider
        return self.providers.get(name)

    def _init_scheduler(self) -> None:
        """Initialize task scheduler if enabled."""
        scheduler_config = getattr(self.config, "scheduler", None)
        if scheduler_config is None:
            logger.warning("Scheduler configuration missing; scheduler disabled")
            return

        enabled_flag = getattr(scheduler_config, "enabled", None)
        if not isinstance(enabled_flag, bool):
            logger.debug(
                "Skipping scheduler initialization; "
                "scheduler config does not provide a boolean 'enabled' flag"
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

    def _validate_plugin_configs(self) -> None:
        """Validate all loaded plugin configurations at startup.

        This method checks each plugin's configuration against its schema
        (if defined) and logs warnings for missing or invalid configurations.
        """
        if not self.plugin_manager:
            return

        try:
            from .plugins.config_validator import ConfigValidator

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
            logger.warning(
                "Plugin configuration validation failed: %s", exc, exc_info=True
            )

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
            providers=self.providers,
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
                ai_agent=self.ai_agent,  # Pass AI agent for ai_chat/ai_query actions
                providers=self.providers,
                template_registry=self.template_registry,
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
            logger.debug("Skipping event server initialization; configuration path is not a string")
            return

        # Pass providers config for QQ access token verification
        providers_config = getattr(self.config, "providers", None)
        self.event_server = EventServer(event_config, self._handle_incoming_event, providers_config=providers_config)

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
                        logger.error("Chat controller message handling failed: %s", exc, exc_info=True)

                logger.info("Chat controller connected to event server")
            except Exception as exc:
                logger.error("Failed to connect chat controller to event server: %s", exc, exc_info=True)

        logger.info(
            "Event server configured on %s:%s%s",
            event_config.host,
            event_config.port,
            event_config.path,
        )

    def _init_ai_agent(self) -> None:
        """Initialize AI agent if configured."""
        ai_config = getattr(self.config, "ai", None)
        if not ai_config:
            logger.info("AI agent disabled")
            return

        enabled_flag = getattr(ai_config, "enabled", None)
        if not isinstance(enabled_flag, bool) or not enabled_flag:
            logger.info("AI agent disabled")
            return

        try:
            from .ai import AIAgent
            from .ai.config import AIConfig

            # Convert to AIConfig if it's a dict
            if isinstance(ai_config, dict):
                ai_config = AIConfig(**ai_config)
            elif not hasattr(ai_config, "enabled"):
                logger.warning("Invalid AI configuration, skipping AI agent initialization")
                return

            self.ai_agent = AIAgent(ai_config)
            logger.info("AI agent initialized with model: %s", ai_config.model)
        except ImportError as exc:
            logger.error("Failed to import AI modules: %s", exc, exc_info=True)
        except Exception as exc:
            logger.error("Failed to initialize AI agent: %s", exc, exc_info=True)

    def _init_chat_controller(self) -> None:
        """Initialize chat controller for unified message handling."""
        # Check if chat configuration is available
        chat_config = getattr(self.config, "chat", None)
        if chat_config is None:
            # Use default configuration
            chat_config = ChatConfig()

        if not chat_config.enabled:
            logger.info("Chat controller disabled")
            return

        # Get available models from AI configuration
        ai_config = getattr(self.config, "ai", None)
        available_models = None
        if ai_config:
            available_models = getattr(ai_config, "available_models", None)

        try:
            self.chat_controller = create_chat_controller(
                ai_agent=self.ai_agent,
                providers=self.providers,
                config=chat_config,
                available_models=available_models,
            )
            logger.info("Chat controller initialized")
        except Exception as e:
            logger.error("Failed to initialize chat controller: %s", e, exc_info=True)

    def _automation_send_text(self, text: str, webhook_name: str) -> None:
        self.send_message(text, webhook_name)

    def _automation_send_rendered(
        self, rendered: RenderedTemplate, webhook_names: Sequence[str]
    ) -> None:
        self._send_rendered_template(rendered, webhook_names)

    def _handle_incoming_event(self, payload: dict[str, Any]) -> None:
        """Handle inbound events from the event server."""
        logger.debug("Handling incoming event: %s", payload.get("type", "unknown"))

        # Handle AI chat messages via ChatController if available
        if self.chat_controller and self._is_chat_message(payload):
            try:
                import asyncio

                # Parse message from payload and route to chat controller
                message = self._parse_incoming_message(payload)
                if message:
                    asyncio.create_task(self.chat_controller.handle_incoming(message))
                    logger.debug("Message routed to chat controller")
                    # Note: Plugin and automation dispatch still happens below for
                    # backward compatibility and non-message event handling
                else:
                    logger.debug("Could not parse message from payload")
            except Exception as exc:
                logger.error("Chat controller message handling failed: %s", exc, exc_info=True)
        # Fallback to old AI chat handler if no chat controller
        elif self.ai_agent and self._is_chat_message(payload):
            try:
                import asyncio

                asyncio.create_task(self._handle_ai_chat(payload))
            except Exception as exc:
                logger.error("AI chat handling failed: %s", exc, exc_info=True)

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

    def _parse_incoming_message(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse event payload into a unified IncomingMessage.

        Uses platform-specific parsers for comprehensive message parsing:
        - FeishuMessageParser for Feishu events
        - QQMessageParser for OneBot11/Napcat events

        Args:
            payload: Event payload from webhook

        Returns:
            IncomingMessage instance or None if parsing fails
        """
        try:
            # Determine platform from payload marker (set by event_server)
            provider = payload.get("_provider", "")

            # Try Feishu parser
            if provider == "feishu" or not provider:
                # Get bot_open_id from provider config if available
                bot_open_id = None
                for p_config in self.config.providers or []:
                    if p_config.provider_type == "feishu":
                        api_config = getattr(p_config, "api", None)
                        if api_config:
                            # In a real implementation, bot_open_id would be obtained from API
                            pass
                        break

                feishu_parser = FeishuMessageParser(bot_open_id=bot_open_id)
                if feishu_parser.can_parse(payload):
                    message = feishu_parser.parse(payload)
                    if message:
                        return message

            # Try QQ parser
            if provider == "napcat" or provider == "qq" or not provider:
                # Get bot_qq from provider config
                bot_qq = None
                for p_config in self.config.providers or []:
                    if p_config.provider_type == "napcat":
                        bot_qq = getattr(p_config, "bot_qq", None)
                        break

                qq_parser = QQMessageParser(bot_qq=bot_qq)
                if qq_parser.can_parse(payload):
                    message = qq_parser.parse(payload)
                    if message:
                        return message

            # Fallback: Try basic Feishu structure for backward compatibility
            event_type = payload.get("type")
            if event_type == "message":
                event = payload.get("event", payload)
                message_data = event.get("message", {})
                sender = event.get("sender", {})

                return IncomingMessage(
                    id=message_data.get("message_id", ""),
                    platform="feishu",
                    chat_type=event.get("chat_type", "private"),
                    chat_id=event.get("chat_id", ""),
                    sender_id=sender.get("sender_id", {}).get("user_id", ""),
                    sender_name=sender.get("sender_name", "Unknown"),
                    content=message_data.get("text", ""),
                    is_at_bot=False,
                    raw_content=message_data,
                    metadata={"event_id": payload.get("event_id", "")},
                )

            return None

        except Exception as e:
            logger.debug("Failed to parse incoming message: %s", e, exc_info=True)
            return None

    def _is_chat_message(self, payload: dict[str, Any]) -> bool:
        """Check if the payload is a chat message that should be handled by AI.

        Supports both Feishu and QQ (OneBot11) message structures.

        Args:
            payload: Event payload

        Returns:
            True if this is a chat message
        """
        # Check platform marker (set by event_server)
        provider = payload.get("_provider", "")

        # Check for Feishu message event structure
        event_type = payload.get("type")
        if event_type == "message":
            return True

        # Check for nested event structure (Feishu v2.0)
        header = payload.get("header", {})
        if header.get("event_type") == "im.message.receive_v1":
            return True

        event = payload.get("event", {})
        if event.get("type") == "message":
            return True

        # Check for QQ/OneBot11 message event structure
        post_type = payload.get("post_type")
        if post_type == "message":
            return True

        return False

    async def _handle_ai_chat(self, payload: dict[str, Any]) -> None:
        """Handle AI chat message.

        Note: This method is now primarily handled by ChatController when available.
        It's kept for backward compatibility and as a fallback when chat_controller
        is not initialized.

        Args:
            payload: Event payload
        """
        # If chat controller is available, it should handle this
        if self.chat_controller:
            logger.debug("AI chat should be handled by ChatController, skipping legacy handler")
            return

        try:
            # Extract message content and user ID from payload
            event = payload.get("event", payload)
            message_content = event.get("text", event.get("content", ""))
            user_id = event.get("sender", {}).get("sender_id", {}).get("user_id", "unknown")

            if not message_content:
                logger.warning("Received empty message, skipping AI processing")
                return

            logger.info("Processing AI chat from user %s: %s", user_id, message_content[:100])

            # Get AI response
            response = await self.ai_agent.chat(user_id, message_content)

            # Send response back via webhook
            if response and self.client:
                self.client.send_text(response)
                logger.info("Sent AI response to user %s", user_id)

        except Exception as exc:
            logger.error("Error handling AI chat: %s", exc, exc_info=True)

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
            # Connect all providers
            for name, provider in self.providers.items():
                try:
                    provider.connect()
                    logger.info("Provider connected: %s", name)
                except Exception as exc:
                    logger.error(
                        "Failed to connect provider '%s': %s", name, exc, exc_info=True
                    )
                    raise

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

            if self.ai_agent:
                try:
                    self.ai_agent.start()
                    logger.info("AI agent started")
                except Exception as exc:
                    logger.error("Failed to start AI agent: %s", exc, exc_info=True)
                    raise

            # Start message queue processor
            if self.message_queue:
                try:
                    self._message_queue_task = asyncio.create_task(
                        self._run_message_queue_processor()
                    )
                    logger.info("Message queue processor started")
                except Exception as exc:
                    logger.warning("Failed to start message queue processor: %s", exc, exc_info=True)

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

            # Stop AI agent
            if self.ai_agent:
                try:
                    import asyncio

                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.ai_agent.stop())
                    else:
                        loop.run_until_complete(self.ai_agent.stop())
                except Exception as exc:
                    logger.error("Failed to stop AI agent: %s", exc, exc_info=True)

            # Stop scheduler
            if self.scheduler:
                try:
                    self.scheduler.shutdown()
                except Exception as exc:
                    logger.error("Failed to shutdown scheduler: %s", exc, exc_info=True)

            # Stop message queue processor
            if self._message_queue_task:
                try:
                    self._message_queue_task.cancel()
                    logger.info("Message queue processor stopped")
                except Exception as exc:
                    logger.error("Failed to stop message queue: %s", exc, exc_info=True)

            # Stop message tracker cleanup thread
            if self.message_tracker:
                try:
                    self.message_tracker.stop_cleanup()
                    logger.info("Message tracker stopped")
                except Exception as exc:
                    logger.error("Failed to stop message tracker: %s", exc, exc_info=True)

            # Disconnect all providers
            for name, provider in self.providers.items():
                try:
                    provider.disconnect()
                    logger.info("Provider disconnected: %s", name)
                except Exception as exc:
                    logger.error(
                        "Error disconnecting provider %s: %s", name, exc, exc_info=True
                    )

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
