"""Command-line interface for Feishu Webhook Bot.

This module is a compatibility layer that re-exports from the cli package.
The actual implementation has been split into the cli/ directory.
"""

from __future__ import annotations

# Re-export everything from the cli package for backward compatibility
from .cli import (
    BotConfig,
    Console,
    FeishuBot,
    FeishuWebhookClient,
    Panel,
    Path,
    Table,
    WebhookConfig,
    __version__,
    _has_valid_logging_config,
    build_parser,
    cmd_ai,
    cmd_auth,
    cmd_automation,
    cmd_bridge,
    cmd_calendar,
    cmd_chat,
    cmd_config,
    cmd_events,
    cmd_image,
    cmd_init,
    cmd_logging,
    cmd_message,
    cmd_plugins,
    cmd_provider,
    cmd_scheduler,
    cmd_send,
    cmd_start,
    cmd_task,
    cmd_webui,
    get_logger,
    logger,
    main,
    print_banner,
    run_ui,
    setup_logging,
)

__all__ = [
    # Main entry point
    "main",
    # Parser
    "build_parser",
    "print_banner",
    # Base utilities
    "BotConfig",
    "Console",
    "FeishuBot",
    "FeishuWebhookClient",
    "Panel",
    "Path",
    "Table",
    "WebhookConfig",
    "__version__",
    "_has_valid_logging_config",
    "get_logger",
    "logger",
    "run_ui",
    "setup_logging",
    # Command handlers
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
