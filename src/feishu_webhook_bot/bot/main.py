"""Main FeishuBot class that combines all mixins."""

from __future__ import annotations

import asyncio
import signal
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..core import BotConfig, get_logger
from .event_handler import EventHandlerMixin
from .initializers import (
    AIInitializerMixin,
    ClientInitializerMixin,
    MessagingInitializerMixin,
    MiscInitializerMixin,
    PluginInitializerMixin,
    ProviderInitializerMixin,
    SchedulerInitializerMixin,
)
from .lifecycle import LifecycleMixin
from .messaging import MessagingMixin

if TYPE_CHECKING:
    from ..ai.agent import AIAgent
    from ..automation import AutomationEngine
    from ..chat.controller import ChatController
    from ..core import FeishuWebhookClient
    from ..core.config_watcher import ConfigWatcher
    from ..core.event_server import EventServer
    from ..core.message_bridge import MessageBridgeEngine
    from ..core.message_queue import MessageQueue
    from ..core.message_tracker import MessageTracker
    from ..core.provider import BaseProvider
    from ..core.templates import TemplateRegistry
    from ..plugins import PluginManager
    from ..scheduler import TaskScheduler
    from ..tasks import TaskManager

logger = get_logger("bot")


class FeishuBot(
    ClientInitializerMixin,
    ProviderInitializerMixin,
    MessagingInitializerMixin,
    SchedulerInitializerMixin,
    PluginInitializerMixin,
    AIInitializerMixin,
    MiscInitializerMixin,
    LifecycleMixin,
    EventHandlerMixin,
    MessagingMixin,
):
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

    # Type annotations for all attributes
    config: BotConfig
    clients: dict[str, FeishuWebhookClient]
    client: FeishuWebhookClient | None
    providers: dict[str, BaseProvider]
    default_provider: BaseProvider | None
    scheduler: TaskScheduler | None
    plugin_manager: PluginManager | None
    template_registry: TemplateRegistry | None
    automation_engine: AutomationEngine | None
    task_manager: TaskManager | None
    event_server: EventServer | None
    config_watcher: ConfigWatcher | None
    ai_agent: AIAgent | None
    chat_controller: ChatController | None
    message_tracker: MessageTracker | None
    message_queue: MessageQueue | None
    message_bridge: MessageBridgeEngine | None
    _message_queue_task: asyncio.Task[None] | None
    _running: bool
    _shutdown_event: threading.Event
    _signal_handlers: dict[int, signal.Handlers]
    _signal_handlers_installed: bool

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
        self.clients: dict[str, Any] = {}
        self.client: Any = None  # for backward compatibility
        self.providers: dict[str, Any] = {}  # New multi-provider support
        self.default_provider: Any = None
        self.scheduler: Any = None
        self.plugin_manager: Any = None
        self.template_registry: Any = None
        self.automation_engine: Any = None
        self.task_manager: Any = None
        self.event_server: Any = None
        self.config_watcher: Any = None
        self.ai_agent: Any = None
        self.chat_controller: Any = None
        self.message_tracker: Any = None
        self.message_queue: Any = None
        self.message_bridge: Any = None
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
                "Message tracker initialization failed, continuing without tracking: %s",
                exc,
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
            logger.warning("Message queue initialization failed, continuing without queue: %s", exc)

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
            self._init_message_bridge()  # Initialize message bridge after providers
            self._init_tasks()
            self._init_event_server()
            self._init_config_watcher()
        except Exception as exc:
            logger.error("Failed to initialize optional components: %s", exc, exc_info=True)
            raise

        logger.info("Feishu Bot initialized")

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
