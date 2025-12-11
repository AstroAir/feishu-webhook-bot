"""CLI module for Feishu Webhook Bot.

This module provides the command-line interface for the bot.
"""

from __future__ import annotations

from collections.abc import Sequence

from .base import (
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
    get_logger,
    logger,
    run_ui,
    setup_logging,
)
from .commands import (
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
)
from .parser import build_parser, print_banner


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional sequence of CLI arguments (without the program name).

    Returns:
        Process exit code. 0 for success.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle no command: print help and exit (raise SystemExit to match
    # tests that expect argparse-like behavior)
    if not args.command:
        parser.print_help()
        raise SystemExit(0)

    # Dispatch to command handler
    handlers = {
        "start": cmd_start,
        "init": cmd_init,
        "send": cmd_send,
        "plugins": cmd_plugins,
        "webui": cmd_webui,
        # Stage 1-3: AI, Task, Scheduler
        "ai": cmd_ai,
        "task": cmd_task,
        "scheduler": cmd_scheduler,
        # Stage 4-6: Automation, Provider, Message
        "automation": cmd_automation,
        "provider": cmd_provider,
        "bridge": cmd_bridge,
        "message": cmd_message,
        # Stage 7-9: Chat, Config, Auth
        "chat": cmd_chat,
        "config": cmd_config,
        "auth": cmd_auth,
        # Stage 10-13: Events, Logging, Calendar, Image
        "events": cmd_events,
        "logging": cmd_logging,
        "calendar": cmd_calendar,
        "image": cmd_image,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1


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
