"""CLI command handlers package."""

from .basic import cmd_start, cmd_init, cmd_send, cmd_plugins, cmd_webui
from .ai import cmd_ai
from .task import cmd_task
from .scheduler import cmd_scheduler
from .automation import cmd_automation
from .provider import cmd_provider
from .bridge import cmd_bridge
from .message import cmd_message
from .chat import cmd_chat
from .config_cmd import cmd_config
from .auth import cmd_auth
from .events import cmd_events
from .logging_cmd import cmd_logging
from .calendar import cmd_calendar
from .image import cmd_image

__all__ = [
    "cmd_start",
    "cmd_init",
    "cmd_send",
    "cmd_plugins",
    "cmd_webui",
    "cmd_ai",
    "cmd_task",
    "cmd_scheduler",
    "cmd_automation",
    "cmd_provider",
    "cmd_bridge",
    "cmd_message",
    "cmd_chat",
    "cmd_config",
    "cmd_auth",
    "cmd_events",
    "cmd_logging",
    "cmd_calendar",
    "cmd_image",
]
