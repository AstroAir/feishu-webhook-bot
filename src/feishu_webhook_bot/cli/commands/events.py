"""Events CLI commands."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..base import BotConfig


def cmd_events(args: argparse.Namespace) -> int:
    """Handle event server commands."""
    if not args.events_command:
        print("Usage: feishu-webhook-bot events <subcommand>")
        return 1

    handlers = {
        "status": _cmd_events_status,
        "start": _cmd_events_start,
        "stop": _cmd_events_stop,
        "test-webhook": _cmd_events_test_webhook,
    }

    handler = handlers.get(args.events_command)
    if handler:
        return handler(args)

    return 1


def _cmd_events_status(args: argparse.Namespace) -> int:
    """Show event server status."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()
        event_config = config.event_server

        table = Table(title="Event Server Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Enabled", "Yes" if event_config.enabled else "No")
        table.add_row("Host", event_config.host)
        table.add_row("Port", str(event_config.port))
        table.add_row("Path", event_config.path)
        table.add_row("Auto Start", "Yes" if event_config.auto_start else "No")
        table.add_row(
            "Verification Token",
            "Configured" if event_config.verification_token else "Not set",
        )
        table.add_row(
            "Signature Secret",
            "Configured" if event_config.signature_secret else "Not set",
        )

        console.print(table)
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def _cmd_events_start(args: argparse.Namespace) -> int:
    """Start the event server."""
    config_path = Path(args.config)
    if not config_path.exists():
        print("Error: Configuration file not found")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        if not config.event_server.enabled:
            print("Error: Event server is disabled in configuration")
            return 1

        from ...core.event_server import EventServer

        def dummy_handler(payload):
            pass

        server = EventServer(config.event_server, dummy_handler)
        server.start()

        if server.is_running:
            host = config.event_server.host
            port = config.event_server.port
            path = config.event_server.path
            print(f"Event server started on http://{host}:{port}{path}")
            print("Press Ctrl+C to stop")

            try:
                while server.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                server.stop()

            return 0

        return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


def _cmd_events_stop(args: argparse.Namespace) -> int:
    """Stop the event server."""
    print("To stop the event server, press Ctrl+C in the running process")
    return 0


def _cmd_events_test_webhook(args: argparse.Namespace) -> int:
    """Test webhook endpoint."""
    if args.type == "feishu":
        url = "http://localhost:8000/feishu/events"
    else:
        url = "http://localhost:8000/qq/events"

    print(f"Webhook URL: {url}")
    print("\nTo test, send a POST request:")
    print(f"curl -X POST {url} -H 'Content-Type: application/json' -d '{{}}'")
    return 0


__all__ = ["cmd_events"]
