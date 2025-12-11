"""Message system CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..base import BotConfig, logger


def cmd_message(args: argparse.Namespace) -> int:
    """Handle message system commands.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    if not args.message_command:
        print("Usage: feishu-webhook-bot message <subcommand>")
        print("Subcommands: stats, queue, tracker, circuit-breaker")
        return 1

    handlers = {
        "stats": _cmd_message_stats,
        "queue": _cmd_message_queue,
        "tracker": _cmd_message_tracker,
        "circuit-breaker": _cmd_message_circuit_breaker,
    }

    handler = handlers.get(args.message_command)
    if handler:
        return handler(args)

    print(f"Unknown message subcommand: {args.message_command}")
    return 1


def _cmd_message_stats(args: argparse.Namespace) -> int:
    """Handle message stats command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Message System Statistics[/]\n")

        # Get message tracking config safely
        message_tracking = getattr(config, "message_tracking", None)
        message_queue = getattr(config, "message_queue", None)

        info_lines = [
            "[bold]Message Queue:[/]",
            f"  Max Batch Size: {getattr(message_queue, 'max_batch_size', 'N/A') if message_queue else 'N/A'}",
            f"  Max Retries: {getattr(message_queue, 'max_retries', 'N/A') if message_queue else 'N/A'}",
            "",
            "[bold]Message Tracker:[/]",
            f"  Max History: {getattr(message_tracking, 'max_history', 'N/A') if message_tracking else 'N/A'}",
            f"  Database: {getattr(message_tracking, 'db_path', 'In-memory') if message_tracking else 'In-memory'}",
        ]

        console.print("\n".join(info_lines))
        console.print(
            "\n[yellow]Note: Detailed runtime statistics available when bot is running.[/]"
        )

        return 0

    except Exception as e:
        logger.error(f"Error getting message stats: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_message_queue(args: argparse.Namespace) -> int:
    """Handle message queue command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Message Queue Status[/]\n")

        if not config.message_queue:
            console.print("[yellow]Message queue not configured.[/]")
            return 0

        table = Table()
        table.add_column("Configuration", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Max Batch Size", str(config.message_queue.max_batch_size))
        table.add_row("Max Retries", str(config.message_queue.max_retries))
        table.add_row("Retry Delay (s)", str(config.message_queue.retry_delay))

        console.print(table)
        console.print(
            "\n[yellow]Note: Queue size and message count available during runtime.[/]"
        )

        return 0

    except Exception as e:
        logger.error(f"Error getting queue status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_message_tracker(args: argparse.Namespace) -> int:
    """Handle message tracker command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Message Tracker Statistics[/]\n")

        if not config.message_tracker:
            console.print("[yellow]Message tracker not configured.[/]")
            return 0

        table = Table()
        table.add_column("Configuration", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Max History", str(config.message_tracker.max_history))
        table.add_row(
            "Cleanup Interval (s)", str(config.message_tracker.cleanup_interval)
        )

        db_status = (
            config.message_tracker.db_path
            if config.message_tracker.db_path
            else "In-memory (no persistence)"
        )
        table.add_row("Storage", db_status)

        console.print(table)
        console.print(
            "\n[yellow]Note: Message counts and status breakdown available during runtime.[/]"
        )

        return 0

    except Exception as e:
        logger.error(f"Error getting tracker stats: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_message_circuit_breaker(args: argparse.Namespace) -> int:
    """Handle circuit breaker status command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Circuit Breaker Status[/]\n")

        # Check if any providers have circuit breaker config
        has_circuit_breakers = any(
            p.retry and p.retry.circuit_breaker
            for p in config.providers
            if hasattr(p, 'retry') and hasattr(p.retry, 'circuit_breaker')
        )

        if not has_circuit_breakers:
            console.print("[yellow]No circuit breakers configured.[/]")
            return 0

        table = Table(title="Circuit Breaker Configuration")
        table.add_column("Provider", style="cyan")
        table.add_column("Failure Threshold", style="magenta")
        table.add_column("Timeout (s)")
        table.add_column("Status")

        for provider in config.providers:
            if hasattr(provider, 'retry') and provider.retry:
                cb_config = getattr(provider.retry, 'circuit_breaker', None)
                if cb_config:
                    table.add_row(
                        provider.name,
                        str(cb_config.failure_threshold),
                        str(cb_config.timeout_seconds),
                        "[yellow]Config[/]",
                    )

        if table.rows:
            console.print(table)

        console.print(
            "\n[yellow]Note: Runtime circuit breaker states available when bot is running.[/]"
        )

        return 0

    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_message"]
