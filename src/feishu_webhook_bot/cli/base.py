"""Base utilities and shared imports for CLI module."""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .. import __version__
from ..bot import FeishuBot
from ..core import BotConfig, WebhookConfig, get_logger, setup_logging

logger = get_logger("cli")


# Expose some module-level callables/clients so tests can patch them easily
try:
    from ..config_ui import run_ui as _run_ui
except Exception:
    _run_ui = None  # type: ignore[assignment]
run_ui = _run_ui

try:
    from ..core.client import FeishuWebhookClient as _FeishuWebhookClient
except Exception:
    _FeishuWebhookClient = None  # type: ignore[assignment,misc]
FeishuWebhookClient = _FeishuWebhookClient


def _has_valid_logging_config(logging_config: Any) -> bool:
    """Return True when logging config looks like a real LoggingConfig."""

    if logging_config is None:
        return False
    level = getattr(logging_config, "level", None)
    log_format = getattr(logging_config, "format", None)
    return isinstance(level, str) and isinstance(log_format, str)


__all__ = [
    "argparse",
    "asyncio",
    "logging",
    "time",
    "Sequence",
    "Path",
    "Any",
    "Console",
    "Panel",
    "Table",
    "__version__",
    "FeishuBot",
    "BotConfig",
    "WebhookConfig",
    "get_logger",
    "setup_logging",
    "logger",
    "run_ui",
    "FeishuWebhookClient",
    "_has_valid_logging_config",
]
