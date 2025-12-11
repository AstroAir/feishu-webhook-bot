# ruff: noqa: E501
"""Page modules for WebUI tabs."""

from .general import build_general_page
from .scheduler import build_scheduler_page
from .plugins import build_plugins_page
from .logging_page import build_logging_page
from .templates import build_templates_page
from .notifications import build_notifications_page
from .status import build_status_page
from .ai_dashboard import build_ai_dashboard_page
from .tasks import build_tasks_page
from .automation import build_automation_page
from .providers import build_providers_page
from .bridge import build_bridge_page
from .messages import build_messages_page
from .auth import build_auth_page
from .events import build_events_page
from .logs import build_logs_page

__all__ = [
    "build_general_page",
    "build_scheduler_page",
    "build_plugins_page",
    "build_logging_page",
    "build_templates_page",
    "build_notifications_page",
    "build_status_page",
    "build_ai_dashboard_page",
    "build_tasks_page",
    "build_automation_page",
    "build_providers_page",
    "build_bridge_page",
    "build_messages_page",
    "build_auth_page",
    "build_events_page",
    "build_logs_page",
]
