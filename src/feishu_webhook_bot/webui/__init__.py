# ruff: noqa: E501
"""WebUI module for Feishu Webhook Bot configuration and control panel.

This module provides a NiceGUI-based web interface organized as a dashboard.
"""

from .controller import BotController, UIMemoryLogHandler
from .i18n import get_lang, set_lang, t
from .layout import build_ui, run_ui

__all__ = [
    "BotController",
    "UIMemoryLogHandler",
    "build_ui",
    "run_ui",
    "t",
    "get_lang",
    "set_lang",
]
