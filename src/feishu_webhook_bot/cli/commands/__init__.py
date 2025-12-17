"""CLI command handlers package."""

from .ai import cmd_ai
from .auth import cmd_auth
from .automation import cmd_automation
from .basic import cmd_init, cmd_send, cmd_start, cmd_webui
from .bridge import cmd_bridge
from .calendar import cmd_calendar
from .chat import cmd_chat
from .config_cmd import cmd_config
from .events import cmd_events
from .image import cmd_image
from .logging_cmd import cmd_logging
from .message import cmd_message
from .plugins import cmd_plugins
from .provider import cmd_provider
from .scheduler import cmd_scheduler
from .task import cmd_task

__all__ = [
    "cmd_ai",
    "cmd_auth",
    "cmd_automation",
    "cmd_bridge",
    "cmd_calendar",
    "cmd_chat",
    "cmd_config",
    "cmd_events",
    "cmd_image",
    "cmd_init",
    "cmd_logging",
    "cmd_message",
    "cmd_plugins",
    "cmd_provider",
    "cmd_scheduler",
    "cmd_send",
    "cmd_start",
    "cmd_task",
    "cmd_webui",
]
