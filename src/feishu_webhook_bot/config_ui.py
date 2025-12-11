# ruff: noqa: E501

"""NiceGUI-based configuration and control panel for Feishu Webhook Bot.

This module provides a local web UI to:
- View and edit bot configuration (YAML)
- Start / Stop / Restart the bot
- Show current status and recent logs

Usage (CLI will wire this as `feishu-webhook-bot webui`):
    python -m feishu_webhook_bot.config_ui --config config.yaml --host 127.0.0.1 --port 8080

The UI has been refactored into the webui submodule with a dashboard layout.
This module re-exports the main entry points for backward compatibility.
"""

from __future__ import annotations

from .webui import BotController, UIMemoryLogHandler, build_ui, run_ui

__all__ = [
    "BotController",
    "UIMemoryLogHandler",
    "build_ui",
    "run_ui",
]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", default="config.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    run_ui(args.config, args.host, args.port)
