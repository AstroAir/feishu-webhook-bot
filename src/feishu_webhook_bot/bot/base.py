"""Base class definition for FeishuBot with type annotations."""

from __future__ import annotations

import asyncio
import signal
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..ai.agent import AIAgent
    from ..automation import AutomationEngine
    from ..chat.controller import ChatController
    from ..core import BotConfig, FeishuWebhookClient
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


class BotBase:
    """Base class defining all FeishuBot attributes for type checking.

    This class serves as a type stub for mixin classes to reference
    bot attributes without circular imports.
    """

    # Configuration
    config: BotConfig

    # Webhook clients (legacy)
    clients: dict[str, FeishuWebhookClient]
    client: FeishuWebhookClient | None

    # Providers (new architecture)
    providers: dict[str, BaseProvider]
    default_provider: BaseProvider | None

    # Core components
    scheduler: TaskScheduler | None
    plugin_manager: PluginManager | None
    template_registry: TemplateRegistry | None
    automation_engine: AutomationEngine | None
    task_manager: TaskManager | None
    event_server: EventServer | None
    config_watcher: ConfigWatcher | None

    # AI components
    ai_agent: AIAgent | None
    chat_controller: ChatController | None

    # Messaging components
    message_tracker: MessageTracker | None
    message_queue: MessageQueue | None
    message_bridge: MessageBridgeEngine | None
    _message_queue_task: asyncio.Task[None] | None

    # Runtime state
    _running: bool
    _shutdown_event: threading.Event
    _signal_handlers: dict[int, signal.Handlers]
    _signal_handlers_installed: bool

    # Methods that mixins may call on each other
    def send_message(self, text: str, webhook_name: str | list[str] = "default") -> None:
        """Send a text message via specified webhook or provider."""
        ...

    def _send_rendered_template(self, rendered: Any, webhook_names: list[str]) -> None:
        """Send a rendered template to specified webhooks."""
        ...

    def _handle_incoming_event(self, payload: dict[str, Any]) -> None:
        """Handle inbound events from the event server."""
        ...

    def _parse_incoming_message(self, payload: dict[str, Any]) -> Any:
        """Parse event payload into a unified IncomingMessage."""
        ...

    def _is_chat_message(self, payload: dict[str, Any]) -> bool:
        """Check if the payload is a chat message."""
        ...

    async def _handle_ai_chat(self, payload: dict[str, Any]) -> None:
        """Handle AI chat message."""
        ...

    def start(self) -> None:
        """Start the bot."""
        ...

    def stop(self) -> None:
        """Stop the bot and clean up resources."""
        ...
