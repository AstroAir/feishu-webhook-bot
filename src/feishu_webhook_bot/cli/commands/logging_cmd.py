"""Logging CLI commands."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from ..base import BotConfig


def cmd_logging(args: argparse.Namespace) -> int:
    """Handle logging commands."""
    if not args.logging_command:
        print("Usage: feishu-webhook-bot logging <subcommand>")
        return 1

    handlers = {
        "level": _cmd_logging_level,
        "show": _cmd_logging_show,
        "tail": _cmd_logging_tail,
    }

    handler = handlers.get(args.logging_command)
    if handler:
        return handler(args)

    return 1


def _cmd_logging_level(args: argparse.Namespace) -> int:
    """Set logging level."""
    level = args.level
    logging.getLogger().setLevel(getattr(logging, level))
    logging.getLogger("feishu_bot").setLevel(getattr(logging, level))
    print(f"Logging level set to: {level}")
    return 0


def _cmd_logging_show(args: argparse.Namespace) -> int:
    """Show recent log entries."""
    config_path = Path(args.config)
    if not config_path.exists():
        print("Error: Configuration file not found")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        log_file = getattr(config.logging, "log_file", None)

        if not log_file:
            print("Error: No log file configured")
            return 1

        log_path = Path(log_file)
        if not log_path.exists():
            print("Error: Log file not found")
            return 1

        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        display_lines = lines[-args.limit:] if len(lines) > args.limit else lines
        for line in display_lines:
            print(line.rstrip())

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def _cmd_logging_tail(args: argparse.Namespace) -> int:
    """Follow log file in real-time."""
    config_path = Path(args.config)
    if not config_path.exists():
        print("Error: Configuration file not found")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        log_file = getattr(config.logging, "log_file", None)

        if not log_file:
            print("Error: No log file configured")
            return 1

        log_path = Path(log_file)
        if not log_path.exists():
            print("Error: Log file not found")
            return 1

        print(f"Following log file: {log_path}")

        with open(log_path, "r", encoding="utf-8") as f:
            f.seek(0, 2)  # Go to end of file

            try:
                while True:
                    line = f.readline()
                    if line:
                        print(line.rstrip())
                    else:
                        time.sleep(0.1)
            except KeyboardInterrupt:
                return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_logging"]
