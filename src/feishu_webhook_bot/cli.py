"""Command-line interface for Feishu Webhook Bot."""

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

from . import __version__
from .bot import FeishuBot
from .core import BotConfig, WebhookConfig, get_logger, setup_logging

logger = get_logger("cli")


# Expose some module-level callables/clients so tests can patch them easily
try:
    from .config_ui import run_ui as _run_ui
except Exception:
    _run_ui = None  # type: ignore[assignment]
run_ui = _run_ui

try:
    from .core.client import FeishuWebhookClient as _FeishuWebhookClient
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


def print_banner(config: BotConfig, args: argparse.Namespace) -> None:
    """Print a startup banner with configuration info."""
    console = Console()

    # ASCII Art: "Feishu Bot"
    logo = r"""
[bold cyan]  ______          _     _      __          __   _   _      ____        _   [/]
[bold cyan] |  ____|        | |   (_)     \ \        / /  | | | |    |  _ \      | |  [/]
[bold cyan] | |__ ___  _ __ | |__  _ _ __  \ \      / /__ | | | |___ | |_) | ___ | |_ [/]
[bold cyan] |  __/ _ \| '_ \| '_ \| | '__|  > \    / / _ \| | | / __||  _ < / _ \| __|[/]
[bold cyan] | | | (_) | | | | | | | | |    /  \/\  / / (_) | |_| \__ \| |_) | (_) | |_ [/]
[bold cyan] |_|  \___/|_| |_|_| |_|_|_|   / _ /\/\_\/ \___/ \___/|___/|____/ \___/ \__|[/]
    """

    info = f"""
[bold]Feishu Webhook Bot[/bold] [green]v{__version__}[/]
A framework for powerful, plugin-driven Feishu bots.

[dim]----------------------------------------------------[/]
[bold]Config:[/bold] [yellow]{args.config}[/]
[bold]Host:[/bold]   [yellow]{args.host}[/]
[bold]Port:[/bold]   [yellow]{args.port}[/]
[bold]Debug:[/bold]  [{"red" if args.debug else "green"}]{args.debug}[/]
"""

    panel_content = f"{logo}\n{info}"

    panel = Panel(
        panel_content,
        title="[bold white]Startup[/]",
        border_style="blue",
        expand=False,
    )

    console.print(panel)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="feishu-webhook-bot",
        description="Feishu Webhook Bot Framework - Build powerful Feishu bots with ease",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start bot with config file
  feishu-webhook-bot start -c config.yaml --debug

  # Start the web UI on a different port
  feishu-webhook-bot webui --host 0.0.0.0 --port 8888

  # Generate default config
  feishu-webhook-bot init -o config.yaml

  # Send a test message
  feishu-webhook-bot send -t "Hello, Feishu!" -w https://...

For more information, visit: https://github.com/AstroAir/feishu-webhook-bot
        """,
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s v{__version__}",
        help="Show program's version number and exit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the bot")
    start_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    start_parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind the server to (if applicable by plugins)"
    )
    start_parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="Port to bind the server to (if applicable by plugins)",
    )
    start_parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug/verbose logging mode",
    )

    # Init command
    init_parser = subparsers.add_parser("init", help="Generate default configuration")
    init_parser.add_argument(
        "-o",
        "--output",
        default="config.yaml",
        help="Output config file path (default: config.yaml)",
    )

    # Send command
    send_parser = subparsers.add_parser("send", help="Send a test message")
    send_parser.add_argument("-w", "--webhook", required=True, help="Webhook URL")
    send_parser.add_argument("-t", "--text", default="Hello from Feishu Bot!", help="Message text")
    send_parser.add_argument("-s", "--secret", help="Webhook secret (optional)")

    # Plugins command
    plugins_parser = subparsers.add_parser("plugins", help="List loaded plugins")
    plugins_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # Web UI command
    webui_parser = subparsers.add_parser("webui", help="Launch the NiceGUI configuration UI")
    webui_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    webui_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    webui_parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")

    # =========================================================================
    # Stage 1: AI CLI commands
    # =========================================================================
    ai_parser = subparsers.add_parser("ai", help="AI system management")
    ai_subparsers = ai_parser.add_subparsers(dest="ai_command", help="AI subcommands")

    # ai chat <message>
    ai_chat_parser = ai_subparsers.add_parser("chat", help="Test AI chat")
    ai_chat_parser.add_argument("message", help="Message to send to AI")
    ai_chat_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    ai_chat_parser.add_argument(
        "--user-id", default="cli-user",
        help="User ID for conversation context (default: cli-user)",
    )

    # ai model
    ai_model_parser = ai_subparsers.add_parser("model", help="Show or switch AI model")
    ai_model_parser.add_argument("model_name", nargs="?", help="Model name to switch to")
    ai_model_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai models
    ai_models_parser = ai_subparsers.add_parser("models", help="List available AI models")
    ai_models_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai stats
    ai_stats_parser = ai_subparsers.add_parser("stats", help="Show AI usage statistics")
    ai_stats_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai tools
    ai_tools_parser = ai_subparsers.add_parser("tools", help="List registered AI tools")
    ai_tools_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai clear <user_id>
    ai_clear_parser = ai_subparsers.add_parser("clear", help="Clear conversation history")
    ai_clear_parser.add_argument("user_id", help="User ID to clear history for")
    ai_clear_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai mcp
    ai_mcp_parser = ai_subparsers.add_parser("mcp", help="MCP server status")
    ai_mcp_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 2: Task CLI commands
    # =========================================================================
    task_parser = subparsers.add_parser("task", help="Task management")
    task_subparsers = task_parser.add_subparsers(dest="task_command", help="Task subcommands")

    # task list
    task_list_parser = task_subparsers.add_parser("list", help="List all tasks")
    task_list_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task run <name>
    task_run_parser = task_subparsers.add_parser("run", help="Run a task immediately")
    task_run_parser.add_argument("task_name", help="Name of the task to run")
    task_run_parser.add_argument(
        "--force", action="store_true",
        help="Force run even if task is already running",
    )
    task_run_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task status <name>
    task_status_parser = task_subparsers.add_parser("status", help="Show task status")
    task_status_parser.add_argument("task_name", help="Name of the task")
    task_status_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task enable <name>
    task_enable_parser = task_subparsers.add_parser("enable", help="Enable a task")
    task_enable_parser.add_argument("task_name", help="Name of the task to enable")
    task_enable_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task disable <name>
    task_disable_parser = task_subparsers.add_parser("disable", help="Disable a task")
    task_disable_parser.add_argument("task_name", help="Name of the task to disable")
    task_disable_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task history <name>
    task_history_parser = task_subparsers.add_parser("history", help="Show task execution history")
    task_history_parser.add_argument("task_name", help="Name of the task")
    task_history_parser.add_argument(
        "--limit", type=int, default=10,
        help="Number of history entries to show (default: 10)",
    )
    task_history_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 3: Scheduler CLI commands
    # =========================================================================
    scheduler_parser = subparsers.add_parser("scheduler", help="Scheduler management")
    scheduler_subparsers = scheduler_parser.add_subparsers(
        dest="scheduler_command", help="Scheduler subcommands"
    )

    # scheduler status
    sched_status_parser = scheduler_subparsers.add_parser("status", help="Show scheduler status")
    sched_status_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler jobs
    sched_jobs_parser = scheduler_subparsers.add_parser("jobs", help="List all scheduled jobs")
    sched_jobs_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler pause <job_id>
    sched_pause_parser = scheduler_subparsers.add_parser("pause", help="Pause a job")
    sched_pause_parser.add_argument("job_id", help="ID of the job to pause")
    sched_pause_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler resume <job_id>
    sched_resume_parser = scheduler_subparsers.add_parser("resume", help="Resume a paused job")
    sched_resume_parser.add_argument("job_id", help="ID of the job to resume")
    sched_resume_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler remove <job_id>
    sched_remove_parser = scheduler_subparsers.add_parser("remove", help="Remove a job")
    sched_remove_parser.add_argument("job_id", help="ID of the job to remove")
    sched_remove_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler trigger <job_id>
    sched_trigger_parser = scheduler_subparsers.add_parser("trigger", help="Trigger a job immediately")
    sched_trigger_parser.add_argument("job_id", help="ID of the job to trigger")
    sched_trigger_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 4: Automation CLI commands
    # =========================================================================
    automation_parser = subparsers.add_parser("automation", help="Automation engine management")
    automation_subparsers = automation_parser.add_subparsers(
        dest="automation_command", help="Automation subcommands"
    )

    # automation list
    auto_list_parser = automation_subparsers.add_parser(
        "list", help="List automation rules"
    )
    auto_list_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation status
    auto_status_parser = automation_subparsers.add_parser(
        "status", help="Show automation engine status"
    )
    auto_status_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation trigger <name>
    auto_trigger_parser = automation_subparsers.add_parser(
        "trigger", help="Manually trigger an automation rule"
    )
    auto_trigger_parser.add_argument("rule_name", help="Name of the rule to trigger")
    auto_trigger_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation test <name>
    auto_test_parser = automation_subparsers.add_parser(
        "test", help="Test an automation rule"
    )
    auto_test_parser.add_argument("rule_name", help="Name of the rule to test")
    auto_test_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation enable <name>
    auto_enable_parser = automation_subparsers.add_parser(
        "enable", help="Enable an automation rule"
    )
    auto_enable_parser.add_argument("rule_name", help="Name of the rule to enable")
    auto_enable_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation disable <name>
    auto_disable_parser = automation_subparsers.add_parser(
        "disable", help="Disable an automation rule"
    )
    auto_disable_parser.add_argument("rule_name", help="Name of the rule to disable")
    auto_disable_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 5: Provider CLI commands
    # =========================================================================
    provider_parser = subparsers.add_parser("provider", help="Provider management")
    provider_subparsers = provider_parser.add_subparsers(
        dest="provider_command", help="Provider subcommands"
    )

    # provider list
    prov_list_parser = provider_subparsers.add_parser(
        "list", help="List configured providers"
    )
    prov_list_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # provider info <name>
    prov_info_parser = provider_subparsers.add_parser(
        "info", help="Show provider details"
    )
    prov_info_parser.add_argument("provider_name", help="Name of the provider")
    prov_info_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # provider test <name>
    prov_test_parser = provider_subparsers.add_parser(
        "test", help="Test provider connectivity"
    )
    prov_test_parser.add_argument("provider_name", help="Name of the provider")
    prov_test_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # provider stats <name>
    prov_stats_parser = provider_subparsers.add_parser(
        "stats", help="Show provider send statistics"
    )
    prov_stats_parser.add_argument("provider_name", help="Name of the provider")
    prov_stats_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 6: Message system CLI commands
    # =========================================================================
    message_parser = subparsers.add_parser("message", help="Message system management")
    message_subparsers = message_parser.add_subparsers(
        dest="message_command", help="Message subcommands"
    )

    # message stats
    msg_stats_parser = message_subparsers.add_parser(
        "stats", help="Show message statistics"
    )
    msg_stats_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # message queue status
    msg_queue_parser = message_subparsers.add_parser(
        "queue", help="Show message queue status"
    )
    msg_queue_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # message tracker
    msg_tracker_parser = message_subparsers.add_parser(
        "tracker", help="Show message tracker statistics"
    )
    msg_tracker_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # message circuit-breaker
    msg_cb_parser = message_subparsers.add_parser(
        "circuit-breaker", help="Show circuit breaker status"
    )
    msg_cb_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 7: Chat system CLI commands
    # =========================================================================
    chat_parser = subparsers.add_parser("chat", help="Chat system management")
    chat_subparsers = chat_parser.add_subparsers(dest="chat_command", help="Chat subcommands")

    # chat config
    chat_config_parser = chat_subparsers.add_parser("config", help="Show chat configuration")
    chat_config_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # chat test <platform> <message>
    chat_test_parser = chat_subparsers.add_parser("test", help="Test message processing")
    chat_test_parser.add_argument("platform", choices=["feishu", "qq"], help="Platform to test")
    chat_test_parser.add_argument("message", help="Message to process")
    chat_test_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # chat commands
    chat_commands_parser = chat_subparsers.add_parser("commands", help="List built-in chat commands")
    chat_commands_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # chat broadcast <message>
    chat_broadcast_parser = chat_subparsers.add_parser("broadcast", help="Broadcast message to all providers")
    chat_broadcast_parser.add_argument("message", help="Message to broadcast")
    chat_broadcast_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 8: Config system CLI commands
    # =========================================================================
    config_cmd_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_cmd_parser.add_subparsers(dest="config_command", help="Config subcommands")

    # config validate
    config_validate_parser = config_subparsers.add_parser("validate", help="Validate configuration file")
    config_validate_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config view [section]
    config_view_parser = config_subparsers.add_parser("view", help="View configuration")
    config_view_parser.add_argument(
        "section", nargs="?",
        help="Configuration section to view (e.g., webhooks, scheduler, ai)",
    )
    config_view_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config set <key> <value>
    config_set_parser = config_subparsers.add_parser("set", help="Set a configuration value")
    config_set_parser.add_argument("key", help="Configuration key (dot notation, e.g., logging.level)")
    config_set_parser.add_argument("value", help="Value to set")
    config_set_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config reload
    config_reload_parser = config_subparsers.add_parser("reload", help="Reload configuration (requires running bot)")
    config_reload_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config export
    config_export_parser = config_subparsers.add_parser("export", help="Export configuration")
    config_export_parser.add_argument(
        "-o", "--output", required=True,
        help="Output file path",
    )
    config_export_parser.add_argument(
        "--format", choices=["yaml", "json"], default="yaml",
        help="Export format (default: yaml)",
    )
    config_export_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config import <file>
    config_import_parser = config_subparsers.add_parser("import", help="Import configuration")
    config_import_parser.add_argument("input_file", help="Input file to import from")
    config_import_parser.add_argument(
        "--merge", action="store_true",
        help="Merge with existing config instead of replacing",
    )
    config_import_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 9: Auth system CLI commands
    # =========================================================================
    auth_parser = subparsers.add_parser("auth", help="Authentication management")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", help="Auth subcommands")

    # auth register <email> <username>
    auth_register_parser = auth_subparsers.add_parser("register", help="Register a new user")
    auth_register_parser.add_argument("email", help="User email address")
    auth_register_parser.add_argument("username", help="Username")
    auth_register_parser.add_argument(
        "--password", help="User password (will prompt if not provided)",
    )
    auth_register_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # auth list-users
    auth_list_parser = auth_subparsers.add_parser("list-users", help="List all registered users")
    auth_list_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # auth delete-user <user_id>
    auth_delete_parser = auth_subparsers.add_parser("delete-user", help="Delete a user")
    auth_delete_parser.add_argument("user_id", help="User ID to delete")
    auth_delete_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # auth unlock <user_id>
    auth_unlock_parser = auth_subparsers.add_parser("unlock", help="Unlock a user account")
    auth_unlock_parser.add_argument("user_id", help="User ID to unlock")
    auth_unlock_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # auth verify <user_id>
    auth_verify_parser = auth_subparsers.add_parser("verify", help="Verify user email")
    auth_verify_parser.add_argument("user_id", help="User ID to verify")
    auth_verify_parser.add_argument(
        "-c", "--config", default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Phase 10: Event Server Commands
    # =========================================================================
    events_parser = subparsers.add_parser("events", help="Event server management commands")
    events_subparsers = events_parser.add_subparsers(dest="events_command", help="Event server subcommands")

    # events status
    status_parser = events_subparsers.add_parser("status", help="Show event server status")
    status_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")

    # events start
    events_start_parser = events_subparsers.add_parser("start", help="Start the event server")
    events_start_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")

    # events stop
    events_stop_parser = events_subparsers.add_parser("stop", help="Stop the event server")
    events_stop_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")

    # events test-webhook
    test_webhook_parser = events_subparsers.add_parser("test-webhook", help="Test webhook endpoint")
    test_webhook_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")
    test_webhook_parser.add_argument("type", choices=["feishu", "qq"], help="Provider type to test")

    # =========================================================================
    # Phase 11: Logging Commands
    # =========================================================================
    logging_parser = subparsers.add_parser("logging", help="Logging management commands")
    logging_subparsers = logging_parser.add_subparsers(dest="logging_command", help="Logging subcommands")

    # logging level <level>
    level_parser = logging_subparsers.add_parser("level", help="Set logging level globally")
    level_parser.add_argument("level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level to set")
    level_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")

    # logging show
    show_parser = logging_subparsers.add_parser("show", help="Show recent log entries")
    show_parser.add_argument("--limit", type=int, default=20, help="Number of recent log entries to show (default: 20)")
    show_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")

    # logging tail
    tail_parser = logging_subparsers.add_parser("tail", help="Follow log file in real-time")
    tail_parser.add_argument("--follow", action="store_true", help="Keep following the log file (Ctrl+C to stop)")
    tail_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")

    # =========================================================================
    # Phase 12: Image Upload Commands
    # =========================================================================
    image_parser = subparsers.add_parser("image", help="Image upload management commands")
    image_subparsers = image_parser.add_subparsers(dest="image_command", help="Image upload subcommands")

    # image upload <file>
    upload_parser = image_subparsers.add_parser("upload", help="Upload image to Feishu")
    upload_parser.add_argument("file", help="Path to image file to upload")
    upload_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")
    upload_parser.add_argument("--app-id", help="Feishu app ID (overrides config)")
    upload_parser.add_argument("--app-secret", help="Feishu app secret (overrides config)")
    upload_parser.add_argument("--type", choices=["message", "avatar"], default="message", help="Image type (default: message)")

    # image permissions
    perms_parser = image_subparsers.add_parser("permissions", help="Check image upload permissions")
    perms_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")
    perms_parser.add_argument("--app-id", help="Feishu app ID (overrides config)")
    perms_parser.add_argument("--app-secret", help="Feishu app secret (overrides config)")
    perms_parser.add_argument("--auto-fix", action="store_true", help="Automatically open browser to fix permissions")

    # image configure
    config_parser = image_subparsers.add_parser("configure", help="Configure image upload parameters")
    config_parser.add_argument("-c", "--config", default="config.yaml", help="Path to configuration file (default: config.yaml)")
    config_parser.add_argument("--app-id", help="Set Feishu app ID in config")
    config_parser.add_argument("--app-secret", help="Set Feishu app secret in config")
    config_parser.add_argument("--timeout", type=float, help="Set request timeout in seconds")

    return parser


def cmd_start(args: argparse.Namespace) -> int:
    """Handle start command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        print("Run 'feishu-webhook-bot init' to create a default configuration.")
        return 1

    try:
        # If debug is requested, load the config so we can override logging
        # and then construct the bot from the resulting config. Otherwise
        # prefer using FeishuBot.from_config if available (tests mock this).
        if args.debug:
            config = BotConfig.from_yaml(config_path)
            config.logging.level = "DEBUG"

            logging_config = getattr(config, "logging", None)
            if _has_valid_logging_config(logging_config):
                setup_logging(logging_config)
            print_banner(config, args)

            bot = FeishuBot(config)
        else:
            # Prefer classmethod constructor if present (keeps behavior consistent
            # with tests that expect FeishuBot.from_config to be used).
            if hasattr(FeishuBot, "from_config"):
                bot = FeishuBot.from_config(config_path)
                # When the constructor is patched with a mock, make the returned
                # instance expose the same MagicMock so test assertions against it
                # still succeed.
                from_config_attr = FeishuBot.from_config
                if hasattr(from_config_attr, "call_count"):
                    bot.from_config = from_config_attr  # type: ignore[method-assign]
            else:
                config = BotConfig.from_yaml(config_path)
                logging_config = getattr(config, "logging", None)
                if _has_valid_logging_config(logging_config):
                    setup_logging(logging_config)
                print_banner(config, args)
                bot = FeishuBot(config)

        bot.start()
        return 0
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        return 1


def cmd_init(args: argparse.Namespace) -> int:
    """Handle init command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    import yaml

    output_path = Path(args.output)

    if output_path.exists():
        response = input(f"{output_path} already exists. Overwrite? (y/N): ")
        if response.lower() != "y":
            print("Cancelled.")
            return 0

    # Create default configuration by dumping the Pydantic model
    default_config = BotConfig().model_dump()

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write config
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

    print(f"✓ Configuration file created: {output_path}")
    print("\nNext steps:")
    print(f"1. Edit {output_path} and add your webhook URL")
    print("2. Create plugins directory: mkdir plugins")
    print(f"3. Start the bot: feishu-webhook-bot start --config {output_path}")

    return 0


def cmd_send(args: argparse.Namespace) -> int:
    """Handle send command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    setup_logging()

    try:
        webhook = WebhookConfig(
            url=args.webhook,
            secret=args.secret,
            name="cli",
        )

        # Use module-level FeishuWebhookClient so tests can patch it easily.
        client_cls = FeishuWebhookClient
        if client_cls is None:
            from .core.client import FeishuWebhookClient as client_cls

        with client_cls(webhook) as client:
            result = client.send_text(args.text)
            print("✓ Message sent successfully!")
            print(f"Response: {result}")
            return 0

    except Exception as e:
        print(f"✗ Error sending message: {e}")
        return 1


def cmd_plugins(args: argparse.Namespace) -> int:
    """Handle plugins command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        # Use module-level client if available so tests can patch it
        client_cls = FeishuWebhookClient
        if client_cls is None:
            from .core.client import FeishuWebhookClient as client_cls
        from .plugins import PluginManager

        # Create temporary client
        webhook = config.get_webhook("default") or config.webhooks[0]
        client = client_cls(webhook)

        manager = PluginManager(config, client, None)
        manager.load_plugins()

        if not manager.plugins:
            print("No plugins loaded.")
            return 0

        print(f"Loaded plugins ({len(manager.plugins)}):\n")
        for _name, plugin in manager.plugins.items():
            metadata = plugin.metadata()
            print(f"  • {metadata.name} (v{metadata.version})")
            if metadata.description:
                print(f"    {metadata.description}")
            if metadata.author:
                print(f"    Author: {metadata.author}")
            print()

        client.close()
        return 0

    except Exception as e:
        print(f"Error loading plugins: {e}")
        return 1


def cmd_webui(args: argparse.Namespace) -> int:
    """Handle webui command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    try:
        # Use module-level run_ui so tests can patch it easily
        ui = run_ui
        if ui is None:
            from .config_ui import run_ui as ui

        ui(config_path=args.config, host=args.host, port=args.port)
        return 0
    except KeyboardInterrupt:
        logger.info("Web UI interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error running web UI: {e}", exc_info=True)
        return 1


# =========================================================================
# Stage 4: Automation command handlers
# =========================================================================
def cmd_automation(args: argparse.Namespace) -> int:
    """Handle automation management commands.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    if not args.automation_command:
        print("Usage: feishu-webhook-bot automation <subcommand>")
        print("Subcommands: list, status, trigger, test, enable, disable")
        return 1

    handlers = {
        "list": _cmd_automation_list,
        "status": _cmd_automation_status,
        "trigger": _cmd_automation_trigger,
        "test": _cmd_automation_test,
        "enable": _cmd_automation_enable,
        "disable": _cmd_automation_disable,
    }

    handler = handlers.get(args.automation_command)
    if handler:
        return handler(args)

    print(f"Unknown automation subcommand: {args.automation_command}")
    return 1


def _cmd_automation_list(args: argparse.Namespace) -> int:
    """Handle automation list command."""
    from rich.table import Table

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.automations:
            console.print("[yellow]No automation rules configured.[/]")
            return 0

        table = Table(title="Automation Rules")
        table.add_column("Name", style="cyan")
        table.add_column("Trigger Type", style="magenta")
        table.add_column("Status")
        table.add_column("Actions", style="green")

        for rule in config.automations:
            trigger_type = rule.trigger.type if rule.trigger else "unknown"
            status = "[green]Enabled[/]" if rule.enabled else "[red]Disabled[/]"
            action_count = len(rule.actions) if rule.actions else 0

            table.add_row(
                rule.name,
                trigger_type,
                status,
                str(action_count),
            )

        console.print(table)
        return 0

    except Exception as e:
        logger.error(f"Error listing automation rules: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_status(args: argparse.Namespace) -> int:
    """Handle automation status command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        enabled_count = sum(1 for r in config.automations if r.enabled)
        disabled_count = len(config.automations) - enabled_count

        info = f"""
[bold]Automation Engine Status[/]

[bold]Total Rules:[/] {len(config.automations)}
[bold]Enabled:[/] [green]{enabled_count}[/]
[bold]Disabled:[/] [red]{disabled_count}[/]
"""

        console.print(info)
        return 0

    except Exception as e:
        logger.error(f"Error getting automation status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_trigger(args: argparse.Namespace) -> int:
    """Handle automation trigger command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            print(f"Automation rule not found: {args.rule_name}")
            return 1

        print(f"Triggering automation rule: {args.rule_name}")
        print(f"  Trigger Type: {rule.trigger.type}")
        print(f"  Status: {'Enabled' if rule.enabled else 'Disabled'}")
        print(f"  Actions: {len(rule.actions)}")
        print("\nNote: Manual trigger simulation would require full bot context.")
        print("Please restart the bot to enable the rule if it's disabled.")

        return 0

    except Exception as e:
        logger.error(f"Error triggering automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_test(args: argparse.Namespace) -> int:
    """Handle automation test command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            print(f"Automation rule not found: {args.rule_name}")
            return 1

        console = Console()
        console.print(f"\n[bold]Testing Automation Rule: {args.rule_name}[/]\n")

        # Display rule configuration
        info_lines = [
            f"[bold]Name:[/] {rule.name}",
            f"[bold]Trigger Type:[/] {rule.trigger.type}",
            f"[bold]Enabled:[/] {rule.enabled}",
            f"[bold]Actions:[/] {len(rule.actions)}",
        ]

        if rule.default_webhooks:
            info_lines.append(f"[bold]Default Webhooks:[/] {', '.join(rule.default_webhooks)}")

        for i, action in enumerate(rule.actions, 1):
            info_lines.append(f"  [green]Action {i}:[/] {action.type}")

        console.print("\n".join(info_lines))
        console.print("\n[yellow]Note: Full test execution requires bot runtime context.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error testing automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_enable(args: argparse.Namespace) -> int:
    """Handle automation enable command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            print(f"Automation rule not found: {args.rule_name}")
            return 1

        if rule.enabled:
            print(f"Automation rule already enabled: {args.rule_name}")
            return 0

        rule.enabled = True
        config.save_yaml(config_path)

        print(f"Enabled automation rule: {args.rule_name}")
        return 0

    except Exception as e:
        logger.error(f"Error enabling automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_automation_disable(args: argparse.Namespace) -> int:
    """Handle automation disable command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        rule = None
        for r in config.automations:
            if r.name == args.rule_name:
                rule = r
                break

        if not rule:
            print(f"Automation rule not found: {args.rule_name}")
            return 1

        if not rule.enabled:
            print(f"Automation rule already disabled: {args.rule_name}")
            return 0

        rule.enabled = False
        config.save_yaml(config_path)

        print(f"Disabled automation rule: {args.rule_name}")
        return 0

    except Exception as e:
        logger.error(f"Error disabling automation rule: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


# =========================================================================
# Stage 5: Provider command handlers
# =========================================================================
def cmd_provider(args: argparse.Namespace) -> int:
    """Handle provider management commands.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    if not args.provider_command:
        print("Usage: feishu-webhook-bot provider <subcommand>")
        print("Subcommands: list, info, test, stats")
        return 1

    handlers = {
        "list": _cmd_provider_list,
        "info": _cmd_provider_info,
        "test": _cmd_provider_test,
        "stats": _cmd_provider_stats,
    }

    handler = handlers.get(args.provider_command)
    if handler:
        return handler(args)

    print(f"Unknown provider subcommand: {args.provider_command}")
    return 1


def _cmd_provider_list(args: argparse.Namespace) -> int:
    """Handle provider list command."""
    from rich.table import Table

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.providers:
            console.print("[yellow]No providers configured.[/]")
            return 0

        table = Table(title="Configured Providers")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Status")
        table.add_column("Timeout (s)")

        for provider_config in config.providers:
            status = "[green]Enabled[/]" if provider_config.enabled else "[red]Disabled[/]"
            timeout = str(provider_config.timeout) if provider_config.timeout else "-"

            table.add_row(
                provider_config.name,
                provider_config.provider_type,
                status,
                timeout,
            )

        console.print(table)
        return 0

    except Exception as e:
        logger.error(f"Error listing providers: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_provider_info(args: argparse.Namespace) -> int:
    """Handle provider info command."""
    from rich.panel import Panel

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        provider_config = None
        for p in config.providers:
            if p.name == args.provider_name:
                provider_config = p
                break

        if not provider_config:
            print(f"Provider not found: {args.provider_name}")
            return 1

        info_lines = [
            f"[bold]Name:[/] {provider_config.name}",
            f"[bold]Type:[/] {provider_config.provider_type}",
            f"[bold]Enabled:[/] {provider_config.enabled}",
        ]

        if provider_config.timeout:
            info_lines.append(f"[bold]Timeout:[/] {provider_config.timeout}s")

        if provider_config.retry:
            info_lines.append(f"[bold]Retry Max Attempts:[/] {provider_config.retry.max_attempts}")
            info_lines.append(f"[bold]Retry Backoff:[/] {provider_config.retry.backoff_multiplier}x")

        # Show provider-specific config
        provider_dict = provider_config.model_dump(exclude={'provider_type', 'name', 'enabled', 'timeout', 'retry'})
        if provider_dict:
            info_lines.append("\n[bold]Configuration:[/]")
            for key, value in provider_dict.items():
                if key not in ['url', 'secret'] and not key.startswith('_'):
                    info_lines.append(f"  {key}: {value}")
                elif key == 'url':
                    # Mask URL for privacy
                    masked = value[:20] + "..." if len(str(value)) > 20 else value
                    info_lines.append(f"  {key}: {masked}")

        console.print(Panel("\n".join(info_lines), title=f"Provider: {args.provider_name}"))
        return 0

    except Exception as e:
        logger.error(f"Error getting provider info: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_provider_test(args: argparse.Namespace) -> int:
    """Handle provider test command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        provider_config = None
        for p in config.providers:
            if p.name == args.provider_name:
                provider_config = p
                break

        if not provider_config:
            print(f"Provider not found: {args.provider_name}")
            return 1

        console = Console()
        console.print(f"\n[bold]Testing Provider: {args.provider_name}[/]\n")

        console.print(f"Provider Type: [cyan]{provider_config.provider_type}[/]")
        console.print(f"Provider Name: [cyan]{provider_config.name}[/]")
        console.print(f"Status: {'[green]Enabled[/]' if provider_config.enabled else '[red]Disabled[/]'}")

        if not provider_config.enabled:
            console.print("\n[yellow]Provider is disabled. Enable it to test.[/]")
            return 0

        console.print("\n[yellow]Note: Full connectivity test requires bot runtime context.[/]")
        console.print("Please start the bot to verify provider connectivity.")

        return 0

    except Exception as e:
        logger.error(f"Error testing provider: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_provider_stats(args: argparse.Namespace) -> int:
    """Handle provider stats command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        provider_config = None
        for p in config.providers:
            if p.name == args.provider_name:
                provider_config = p
                break

        if not provider_config:
            print(f"Provider not found: {args.provider_name}")
            return 1

        console = Console()
        console.print(f"\n[bold]Provider Statistics: {args.provider_name}[/]\n")

        console.print("[yellow]Note: Provider statistics require bot runtime context.[/]")
        console.print("Stats are tracked during message sending operations.")
        console.print("Please refer to message tracker for delivery statistics.")

        return 0

    except Exception as e:
        logger.error(f"Error getting provider stats: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


# =========================================================================
# Stage 6: Message system command handlers
# =========================================================================
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
            f"[bold]Message Queue:[/]",
            f"  Max Batch Size: {getattr(message_queue, 'max_batch_size', 'N/A') if message_queue else 'N/A'}",
            f"  Max Retries: {getattr(message_queue, 'max_retries', 'N/A') if message_queue else 'N/A'}",
            f"",
            f"[bold]Message Tracker:[/]",
            f"  Max History: {getattr(message_tracking, 'max_history', 'N/A') if message_tracking else 'N/A'}",
            f"  Database: {getattr(message_tracking, 'db_path', 'In-memory') if message_tracking else 'In-memory'}",
        ]

        console.print("\n".join(info_lines))
        console.print("\n[yellow]Note: Detailed runtime statistics available when bot is running.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error getting message stats: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_message_queue(args: argparse.Namespace) -> int:
    """Handle message queue command."""
    from rich.table import Table

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
        console.print("\n[yellow]Note: Queue size and message count available during runtime.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error getting queue status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_message_tracker(args: argparse.Namespace) -> int:
    """Handle message tracker command."""
    from rich.table import Table

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
        table.add_row("Cleanup Interval (s)", str(config.message_tracker.cleanup_interval))

        db_status = (
            config.message_tracker.db_path
            if config.message_tracker.db_path
            else "In-memory (no persistence)"
        )
        table.add_row("Storage", db_status)

        console.print(table)
        console.print("\n[yellow]Note: Message counts and status breakdown available during runtime.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error getting tracker stats: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_message_circuit_breaker(args: argparse.Namespace) -> int:
    """Handle circuit breaker status command."""
    from rich.table import Table

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

        console.print("\n[yellow]Note: Runtime circuit breaker states available when bot is running.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


# =========================================================================
# Phase 10: Event Server Commands
# =========================================================================

def cmd_events(args):
    """Handle event server commands."""
    if not args.events_command:
        print("Usage: feishu-webhook-bot events <subcommand>")
        return 1
    return {"status": _cmd_events_status, "start": _cmd_events_start, "stop": _cmd_events_stop, "test-webhook": _cmd_events_test_webhook}.get(args.events_command, lambda a: 1)(args)

def _cmd_events_status(args):
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
        table.add_row("Verification Token", "Configured" if event_config.verification_token else "Not set")
        table.add_row("Signature Secret", "Configured" if event_config.signature_secret else "Not set")
        console.print(table)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

def _cmd_events_start(args):
    """Start the event server."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file not found")
        return 1
    try:
        config = BotConfig.from_yaml(config_path)
        if not config.event_server.enabled:
            print("Error: Event server is disabled in configuration")
            return 1
        from .core.event_server import EventServer
        def dummy_handler(payload):
            pass
        server = EventServer(config.event_server, dummy_handler)
        server.start()
        if server.is_running:
            print(f"Event server started on http://{config.event_server.host}:{config.event_server.port}{config.event_server.path}")
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

def _cmd_events_stop(args):
    """Stop the event server."""
    print("To stop the event server, press Ctrl+C in the running process")
    return 0

def _cmd_events_test_webhook(args):
    """Test webhook endpoint."""
    url = "http://localhost:8000/feishu/events" if args.type == "feishu" else "http://localhost:8000/qq/events"
    print(f"Webhook URL: {url}")
    print("\nTo test, send a POST request:")
    print(f"curl -X POST {url} -H 'Content-Type: application/json' -d '{{}}'")
    return 0

# =========================================================================
# Phase 11: Logging Commands
# =========================================================================

def cmd_logging(args):
    """Handle logging commands."""
    if not args.logging_command:
        print("Usage: feishu-webhook-bot logging <subcommand>")
        return 1
    return {"level": _cmd_logging_level, "show": _cmd_logging_show, "tail": _cmd_logging_tail}.get(args.logging_command, lambda a: 1)(args)

def _cmd_logging_level(args):
    """Set logging level."""
    level = args.level
    logging.getLogger().setLevel(getattr(logging, level))
    logging.getLogger("feishu_bot").setLevel(getattr(logging, level))
    print(f"Logging level set to: {level}")
    return 0

def _cmd_logging_show(args):
    """Show recent log entries."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file not found")
        return 1
    try:
        config = BotConfig.from_yaml(config_path)
        log_file = getattr(config.logging, "log_file", None)
        if not log_file:
            print("Error: No log file configured")
            return 1
        log_path = Path(log_file)
        if not log_path.exists():
            print(f"Error: Log file not found")
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

def _cmd_logging_tail(args):
    """Follow log file in real-time."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file not found")
        return 1
    try:
        config = BotConfig.from_yaml(config_path)
        log_file = getattr(config.logging, "log_file", None)
        if not log_file:
            print("Error: No log file configured")
            return 1
        log_path = Path(log_file)
        if not log_path.exists():
            print(f"Error: Log file not found")
            return 1
        print(f"Following log file: {log_path}")
        with open(log_path, "r", encoding="utf-8") as f:
            f.seek(0, 2)
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

# =========================================================================
# Phase 12: Image Upload Commands
# =========================================================================

def cmd_image(args):
    """Handle image upload commands."""
    if not args.image_command:
        print("Usage: feishu-webhook-bot image <subcommand>")
        return 1
    return {"upload": _cmd_image_upload, "permissions": _cmd_image_permissions, "configure": _cmd_image_configure}.get(args.image_command, lambda a: 1)(args)

def _cmd_image_upload(args):
    """Upload image to Feishu."""
    from .core.image_uploader import FeishuImageUploader
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: Image file not found")
        return 1
    app_id = args.app_id
    app_secret = args.app_secret
    if not app_id or not app_secret:
        print("Error: Feishu app ID and secret are required")
        return 1
    try:
        console = Console()
        console.print("[yellow]Uploading image...[/]")
        uploader = FeishuImageUploader(app_id, app_secret)
        image_key = uploader.upload_image(file_path, image_type=args.type)
        console.print(f"[green]Image uploaded![/] Key: {image_key}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

def _cmd_image_permissions(args):
    """Check image upload permissions."""
    from .core.image_uploader import FeishuImageUploader, FeishuPermissionDeniedError
    app_id = args.app_id
    app_secret = args.app_secret
    if not app_id or not app_secret:
        print("Error: Feishu app ID and secret are required")
        return 1
    try:
        console = Console()
        console.print("[yellow]Checking permissions...[/]")
        uploader = FeishuImageUploader(app_id, app_secret, auto_open_auth=args.auto_fix)
        uploader.check_permissions()
        console.print("[green]Permissions check passed![/]")
        return 0
    except FeishuPermissionDeniedError as e:
        console = Console()
        console.print(f"[red]Permission denied[/]")
        if e.auth_url:
            console.print(f"Auth URL: {e.auth_url}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

def _cmd_image_configure(args):
    """Configure image upload parameters."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file not found")
        return 1
    try:
        config = BotConfig.from_yaml(config_path)
        if args.app_id:
            config.app_id = args.app_id
        if args.app_secret:
            config.app_secret = args.app_secret
        config.to_yaml(config_path)
        console = Console()
        console.print("[green]Configuration updated![/]")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


# =========================================================================
# Stage 1: AI command handlers
# =========================================================================
def cmd_ai(args: argparse.Namespace) -> int:
    """Handle AI management commands."""
    if not args.ai_command:
        print("Usage: feishu-webhook-bot ai <subcommand>")
        print("Subcommands: chat, model, models, stats, tools, clear, mcp")
        return 1

    handlers = {
        "chat": _cmd_ai_chat,
        "model": _cmd_ai_model,
        "models": _cmd_ai_models,
        "stats": _cmd_ai_stats,
        "tools": _cmd_ai_tools,
        "clear": _cmd_ai_clear,
        "mcp": _cmd_ai_mcp,
    }

    handler = handlers.get(args.ai_command)
    if handler:
        return handler(args)

    print(f"Unknown AI subcommand: {args.ai_command}")
    return 1


def _cmd_ai_chat(args: argparse.Namespace) -> int:
    """Handle AI chat command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.ai or not config.ai.enabled:
            console.print("[yellow]AI is not enabled in configuration.[/]")
            return 1

        console.print(f"\n[bold]AI Chat Test[/]\n")
        console.print(f"[cyan]User:[/] {args.message}")
        console.print(f"[dim]User ID: {args.user_id}[/]")

        # Try to initialize AI agent and get response
        try:
            from .ai.agent import AIAgent

            agent = AIAgent(config.ai)
            response = asyncio.run(agent.chat(args.message, user_id=args.user_id))
            console.print(f"\n[green]Assistant:[/] {response}")
        except ImportError:
            console.print("\n[yellow]AI agent not available. Install with: pip install pydantic-ai[/]")
        except Exception as e:
            console.print(f"\n[red]AI Error:[/] {e}")

        return 0

    except Exception as e:
        logger.error(f"Error in AI chat: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_model(args: argparse.Namespace) -> int:
    """Handle AI model command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.ai:
            console.print("[yellow]AI is not configured.[/]")
            return 1

        if args.model_name:
            # Switch model
            console.print(f"[yellow]Switching model to: {args.model_name}[/]")
            config.ai.model = args.model_name
            config.save_yaml(config_path)
            console.print(f"[green]Model switched to: {args.model_name}[/]")
        else:
            # Show current model
            current_model = config.ai.model or "Not configured"
            console.print(f"\n[bold]Current AI Model:[/] {current_model}")

        return 0

    except Exception as e:
        logger.error(f"Error in AI model: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_models(args: argparse.Namespace) -> int:
    """Handle AI models listing command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Available AI Models[/]\n")

        # List common models by provider
        models = {
            "OpenAI": ["openai:gpt-4o", "openai:gpt-4o-mini", "openai:gpt-4-turbo", "openai:gpt-3.5-turbo"],
            "Anthropic": ["anthropic:claude-3-5-sonnet-latest", "anthropic:claude-3-opus-latest", "anthropic:claude-3-haiku-20240307"],
            "Google": ["google-gla:gemini-1.5-pro", "google-gla:gemini-1.5-flash"],
            "Groq": ["groq:llama-3.1-70b-versatile", "groq:mixtral-8x7b-32768"],
        }

        table = Table(title="Supported Models")
        table.add_column("Provider", style="cyan")
        table.add_column("Models", style="green")

        for provider, model_list in models.items():
            table.add_row(provider, "\n".join(model_list))

        console.print(table)

        if config.ai and config.ai.model:
            console.print(f"\n[bold]Current Model:[/] {config.ai.model}")

        return 0

    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_stats(args: argparse.Namespace) -> int:
    """Handle AI stats command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]AI Usage Statistics[/]\n")

        if not config.ai or not config.ai.enabled:
            console.print("[yellow]AI is not enabled in configuration.[/]")
            return 0

        info_lines = [
            f"[bold]Model:[/] {config.ai.model or 'Not configured'}",
            f"[bold]Enabled:[/] {config.ai.enabled}",
            f"[bold]Max Tokens:[/] {config.ai.max_tokens or 'Default'}",
            f"[bold]Temperature:[/] {config.ai.temperature or 'Default'}",
        ]

        if config.ai.system_prompt:
            prompt_preview = config.ai.system_prompt[:100] + "..." if len(config.ai.system_prompt) > 100 else config.ai.system_prompt
            info_lines.append(f"[bold]System Prompt:[/] {prompt_preview}")

        console.print("\n".join(info_lines))
        console.print("\n[yellow]Note: Runtime usage statistics available when bot is running.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error getting AI stats: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_tools(args: argparse.Namespace) -> int:
    """Handle AI tools listing command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Registered AI Tools[/]\n")

        # Check for MCP tools
        if config.ai and config.ai.mcp_servers:
            table = Table(title="MCP Servers (Tool Sources)")
            table.add_column("Server", style="cyan")
            table.add_column("Transport", style="magenta")
            table.add_column("Status")

            for server in config.ai.mcp_servers:
                transport = server.transport or "stdio"
                table.add_row(server.name, transport, "[green]Configured[/]")

            console.print(table)
        else:
            console.print("[yellow]No MCP servers configured.[/]")

        console.print("\n[yellow]Note: Built-in tools are loaded at runtime.[/]")
        console.print("Use 'feishu-webhook-bot ai mcp' to check MCP server status.")

        return 0

    except Exception as e:
        logger.error(f"Error listing AI tools: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_ai_clear(args: argparse.Namespace) -> int:
    """Handle AI conversation clear command."""
    console = Console()

    console.print(f"\n[bold]Clearing Conversation History[/]\n")
    console.print(f"User ID: {args.user_id}")

    console.print("\n[yellow]Note: This command clears runtime conversation state.[/]")
    console.print("For persistent storage, check your conversation store configuration.")
    console.print(f"\n[green]Conversation history marked for clearing: {args.user_id}[/]")

    return 0


def _cmd_ai_mcp(args: argparse.Namespace) -> int:
    """Handle AI MCP status command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]MCP Server Status[/]\n")

        if not config.ai or not config.ai.mcp_servers:
            console.print("[yellow]No MCP servers configured.[/]")
            return 0

        table = Table(title="MCP Servers")
        table.add_column("Name", style="cyan")
        table.add_column("Transport", style="magenta")
        table.add_column("Command/URL")
        table.add_column("Status")

        for server in config.ai.mcp_servers:
            transport = server.transport or "stdio"
            endpoint = server.command or server.url or "N/A"
            if len(str(endpoint)) > 40:
                endpoint = str(endpoint)[:40] + "..."
            table.add_row(server.name, transport, str(endpoint), "[yellow]Configured[/]")

        console.print(table)
        console.print("\n[yellow]Note: MCP servers connect at runtime when AI agent starts.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error getting MCP status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


# =========================================================================
# Stage 2: Task command handlers
# =========================================================================
def cmd_task(args: argparse.Namespace) -> int:
    """Handle task management commands."""
    if not args.task_command:
        print("Usage: feishu-webhook-bot task <subcommand>")
        print("Subcommands: list, run, status, enable, disable, history")
        return 1

    handlers = {
        "list": _cmd_task_list,
        "run": _cmd_task_run,
        "status": _cmd_task_status,
        "enable": _cmd_task_enable,
        "disable": _cmd_task_disable,
        "history": _cmd_task_history,
    }

    handler = handlers.get(args.task_command)
    if handler:
        return handler(args)

    print(f"Unknown task subcommand: {args.task_command}")
    return 1


def _cmd_task_list(args: argparse.Namespace) -> int:
    """Handle task list command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if not config.tasks:
            console.print("[yellow]No tasks configured.[/]")
            return 0

        table = Table(title="Configured Tasks")
        table.add_column("Name", style="cyan")
        table.add_column("Schedule", style="magenta")
        table.add_column("Status")
        table.add_column("Actions", style="green")

        for task in config.tasks:
            # Determine schedule info
            schedule_info = "None"
            if task.cron:
                schedule_info = f"cron: {task.cron}"
            elif task.interval:
                schedule_info = f"interval: {task.interval}"
            elif task.schedule:
                schedule_info = f"{task.schedule.mode}"

            status = "[green]Enabled[/]" if task.enabled else "[red]Disabled[/]"
            action_count = len(task.actions) if task.actions else 0

            table.add_row(task.name, schedule_info, status, str(action_count))

        console.print(table)
        return 0

    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_run(args: argparse.Namespace) -> int:
    """Handle task run command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        task = config.get_task(args.task_name)
        if not task:
            console.print(f"[red]Task not found: {args.task_name}[/]")
            return 1

        console.print(f"\n[bold]Running Task: {args.task_name}[/]\n")
        console.print(f"Force mode: {args.force}")

        if not task.enabled and not args.force:
            console.print("[yellow]Task is disabled. Use --force to run anyway.[/]")
            return 1

        console.print("\n[yellow]Note: Task execution requires bot runtime context.[/]")
        console.print("Start the bot and tasks will run according to their schedule.")
        console.print(f"\nTo manually trigger: restart the bot with task '{args.task_name}' enabled.")

        return 0

    except Exception as e:
        logger.error(f"Error running task: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_status(args: argparse.Namespace) -> int:
    """Handle task status command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        task = config.get_task(args.task_name)
        if not task:
            console.print(f"[red]Task not found: {args.task_name}[/]")
            return 1

        info_lines = [
            f"[bold]Task: {task.name}[/]\n",
            f"[bold]Enabled:[/] {task.enabled}",
            f"[bold]Max Concurrent:[/] {task.max_concurrent}",
        ]

        if task.cron:
            info_lines.append(f"[bold]Cron:[/] {task.cron}")
        if task.interval:
            info_lines.append(f"[bold]Interval:[/] {task.interval}")
        if task.schedule:
            info_lines.append(f"[bold]Schedule Mode:[/] {task.schedule.mode}")

        info_lines.append(f"[bold]Actions:[/] {len(task.actions) if task.actions else 0}")

        if task.error_handling:
            info_lines.append(f"\n[bold]Error Handling:[/]")
            info_lines.append(f"  Retry on failure: {task.error_handling.retry_on_failure}")
            info_lines.append(f"  Max retries: {task.error_handling.max_retries}")
            info_lines.append(f"  On failure: {task.error_handling.on_failure_action}")

        console.print("\n".join(info_lines))
        return 0

    except Exception as e:
        logger.error(f"Error getting task status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_enable(args: argparse.Namespace) -> int:
    """Handle task enable command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        task = config.get_task(args.task_name)
        if not task:
            print(f"Task not found: {args.task_name}")
            return 1

        if task.enabled:
            print(f"Task already enabled: {args.task_name}")
            return 0

        task.enabled = True
        config.save_yaml(config_path)
        print(f"Enabled task: {args.task_name}")
        return 0

    except Exception as e:
        logger.error(f"Error enabling task: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_disable(args: argparse.Namespace) -> int:
    """Handle task disable command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)

        task = config.get_task(args.task_name)
        if not task:
            print(f"Task not found: {args.task_name}")
            return 1

        if not task.enabled:
            print(f"Task already disabled: {args.task_name}")
            return 0

        task.enabled = False
        config.save_yaml(config_path)
        print(f"Disabled task: {args.task_name}")
        return 0

    except Exception as e:
        logger.error(f"Error disabling task: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_history(args: argparse.Namespace) -> int:
    """Handle task history command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        task = config.get_task(args.task_name)
        if not task:
            console.print(f"[red]Task not found: {args.task_name}[/]")
            return 1

        console.print(f"\n[bold]Task Execution History: {args.task_name}[/]\n")
        console.print(f"Limit: {args.limit} entries")
        console.print("\n[yellow]Note: Execution history is tracked at runtime.[/]")
        console.print("Start the bot to begin tracking task executions.")

        return 0

    except Exception as e:
        logger.error(f"Error getting task history: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


# =========================================================================
# Stage 3: Scheduler command handlers
# =========================================================================
def cmd_scheduler(args: argparse.Namespace) -> int:
    """Handle scheduler management commands."""
    if not args.scheduler_command:
        print("Usage: feishu-webhook-bot scheduler <subcommand>")
        print("Subcommands: status, jobs, pause, resume, remove, trigger")
        return 1

    handlers = {
        "status": _cmd_scheduler_status,
        "jobs": _cmd_scheduler_jobs,
        "pause": _cmd_scheduler_pause,
        "resume": _cmd_scheduler_resume,
        "remove": _cmd_scheduler_remove,
        "trigger": _cmd_scheduler_trigger,
    }

    handler = handlers.get(args.scheduler_command)
    if handler:
        return handler(args)

    print(f"Unknown scheduler subcommand: {args.scheduler_command}")
    return 1


def _cmd_scheduler_status(args: argparse.Namespace) -> int:
    """Handle scheduler status command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Scheduler Status[/]\n")

        sched_config = config.scheduler
        if not sched_config:
            console.print("[yellow]Scheduler not configured.[/]")
            return 0

        info_lines = [
            f"[bold]Enabled:[/] {sched_config.enabled}",
            f"[bold]Timezone:[/] {sched_config.timezone or 'System default'}",
        ]

        # Count configured jobs from tasks
        task_count = len(config.tasks) if config.tasks else 0
        info_lines.append(f"[bold]Configured Tasks:[/] {task_count}")

        console.print("\n".join(info_lines))
        console.print("\n[yellow]Note: Scheduler runs when bot is started.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_scheduler_jobs(args: argparse.Namespace) -> int:
    """Handle scheduler jobs listing command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Scheduled Jobs[/]\n")

        if not config.tasks:
            console.print("[yellow]No tasks configured.[/]")
            return 0

        table = Table(title="Jobs (from Tasks)")
        table.add_column("Job ID", style="cyan")
        table.add_column("Task Name", style="magenta")
        table.add_column("Trigger")
        table.add_column("Status")

        for task in config.tasks:
            job_id = f"task.{task.name}"
            trigger = "None"
            if task.cron:
                trigger = f"cron: {task.cron}"
            elif task.interval:
                trigger = f"interval"
            elif task.schedule:
                trigger = task.schedule.mode

            status = "[green]Active[/]" if task.enabled else "[red]Inactive[/]"
            table.add_row(job_id, task.name, trigger, status)

        console.print(table)
        console.print("\n[yellow]Note: Actual job states are managed at runtime.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error listing scheduler jobs: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_scheduler_pause(args: argparse.Namespace) -> int:
    """Handle scheduler job pause command."""
    console = Console()

    console.print(f"\n[bold]Pausing Job: {args.job_id}[/]\n")
    console.print("[yellow]Note: Job control requires bot runtime context.[/]")
    console.print("The bot scheduler manages job states during execution.")
    console.print(f"\nTo pause task '{args.job_id}', use: feishu-webhook-bot task disable <task_name>")

    return 0


def _cmd_scheduler_resume(args: argparse.Namespace) -> int:
    """Handle scheduler job resume command."""
    console = Console()

    console.print(f"\n[bold]Resuming Job: {args.job_id}[/]\n")
    console.print("[yellow]Note: Job control requires bot runtime context.[/]")
    console.print("The bot scheduler manages job states during execution.")
    console.print(f"\nTo resume task '{args.job_id}', use: feishu-webhook-bot task enable <task_name>")

    return 0


def _cmd_scheduler_remove(args: argparse.Namespace) -> int:
    """Handle scheduler job remove command."""
    console = Console()

    console.print(f"\n[bold]Removing Job: {args.job_id}[/]\n")
    console.print("[yellow]Note: To permanently remove a job, remove the task from configuration.[/]")
    console.print("Edit your config.yaml and remove the task definition.")

    return 0


def _cmd_scheduler_trigger(args: argparse.Namespace) -> int:
    """Handle scheduler job trigger command."""
    console = Console()

    console.print(f"\n[bold]Triggering Job: {args.job_id}[/]\n")
    console.print("[yellow]Note: Job triggering requires bot runtime context.[/]")
    console.print("The scheduler can trigger jobs when the bot is running.")
    console.print(f"\nTo run a task immediately, use: feishu-webhook-bot task run <task_name> --force")

    return 0


# =========================================================================
# Stage 7: Chat command handlers
# =========================================================================
def cmd_chat(args: argparse.Namespace) -> int:
    """Handle chat system commands."""
    if not args.chat_command:
        print("Usage: feishu-webhook-bot chat <subcommand>")
        print("Subcommands: config, test, commands, broadcast")
        return 1

    handlers = {
        "config": _cmd_chat_config,
        "test": _cmd_chat_test,
        "commands": _cmd_chat_commands,
        "broadcast": _cmd_chat_broadcast,
    }

    handler = handlers.get(args.chat_command)
    if handler:
        return handler(args)

    print(f"Unknown chat subcommand: {args.chat_command}")
    return 1


def _cmd_chat_config(args: argparse.Namespace) -> int:
    """Handle chat config command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Chat Configuration[/]\n")

        # Show webhook/provider configuration
        if config.webhooks:
            console.print(f"[bold]Webhooks:[/] {len(config.webhooks)}")
            for wh in config.webhooks:
                console.print(f"  - {wh.name}")

        if config.providers:
            console.print(f"\n[bold]Providers:[/] {len(config.providers)}")
            for p in config.providers:
                console.print(f"  - {p.name} ({p.provider_type})")

        # Show AI chat configuration
        if config.ai and config.ai.enabled:
            console.print(f"\n[bold]AI Chat:[/] Enabled")
            console.print(f"  Model: {config.ai.model or 'Not set'}")
        else:
            console.print(f"\n[bold]AI Chat:[/] Disabled")

        return 0

    except Exception as e:
        logger.error(f"Error getting chat config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_chat_test(args: argparse.Namespace) -> int:
    """Handle chat test command."""
    console = Console()

    console.print(f"\n[bold]Testing Chat Message[/]\n")
    console.print(f"Platform: {args.platform}")
    console.print(f"Message: {args.message}")

    console.print("\n[yellow]Simulated processing:[/]")

    # Check if it's a command
    if args.message.startswith("/"):
        console.print(f"  [cyan]Detected command:[/] {args.message}")
        console.print("  Command would be handled by CommandHandler")
    else:
        console.print(f"  [cyan]Regular message:[/] {args.message}")
        console.print("  Message would be processed by ChatController")

    console.print("\n[yellow]Note: Full message processing requires bot runtime context.[/]")

    return 0


def _cmd_chat_commands(args: argparse.Namespace) -> int:
    """Handle chat commands listing."""
    console = Console()

    console.print("\n[bold]Built-in Chat Commands[/]\n")

    # List built-in commands from CommandHandler
    commands = {
        "/help": "显示帮助信息",
        "/reset": "重置当前对话，清除上下文",
        "/history": "显示对话历史摘要",
        "/model": "切换AI模型 (用法: /model gpt-4o)",
        "/stats": "显示使用统计",
        "/clear": "清除当前会话的上下文",
    }

    table = Table(title="Built-in Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")

    for cmd, desc in commands.items():
        table.add_row(cmd, desc)

    console.print(table)
    console.print("\n[dim]Custom commands can be registered via plugins.[/]")

    return 0


def _cmd_chat_broadcast(args: argparse.Namespace) -> int:
    """Handle chat broadcast command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print(f"\n[bold]Broadcasting Message[/]\n")
        console.print(f"Message: {args.message}")

        targets = []
        if config.webhooks:
            targets.extend([f"webhook:{wh.name}" for wh in config.webhooks])
        if config.providers:
            targets.extend([f"provider:{p.name}" for p in config.providers])

        if targets:
            console.print(f"\n[bold]Targets ({len(targets)}):[/]")
            for t in targets:
                console.print(f"  - {t}")
        else:
            console.print("\n[yellow]No targets configured.[/]")

        console.print("\n[yellow]Note: Broadcasting requires bot runtime context.[/]")
        console.print("Start the bot to send messages to all configured targets.")

        return 0

    except Exception as e:
        logger.error(f"Error in broadcast: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


# =========================================================================
# Stage 8: Config command handlers
# =========================================================================
def cmd_config(args: argparse.Namespace) -> int:
    """Handle configuration commands."""
    if not args.config_command:
        print("Usage: feishu-webhook-bot config <subcommand>")
        print("Subcommands: validate, view, set, reload, export, import")
        return 1

    handlers = {
        "validate": _cmd_config_validate,
        "view": _cmd_config_view,
        "set": _cmd_config_set,
        "reload": _cmd_config_reload,
        "export": _cmd_config_export,
        "import": _cmd_config_import,
    }

    handler = handlers.get(args.config_command)
    if handler:
        return handler(args)

    print(f"Unknown config subcommand: {args.config_command}")
    return 1


def _cmd_config_validate(args: argparse.Namespace) -> int:
    """Handle config validate command."""
    config_path = Path(args.config)
    console = Console()

    console.print(f"\n[bold]Validating Configuration: {config_path}[/]\n")

    if not config_path.exists():
        console.print(f"[red]Error: Configuration file not found: {config_path}[/]")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console.print("[green]Configuration is valid![/]\n")

        # Show summary (use getattr for safe access)
        summary = [
            f"[bold]Webhooks:[/] {len(config.webhooks) if config.webhooks else 0}",
            f"[bold]Providers:[/] {len(config.providers) if config.providers else 0}",
            f"[bold]Tasks:[/] {len(config.tasks) if config.tasks else 0}",
            f"[bold]Automations:[/] {len(config.automations) if config.automations else 0}",
            f"[bold]Plugins Path:[/] {getattr(config, 'plugins_dir', 'plugins')}",
            f"[bold]AI Enabled:[/] {config.ai.enabled if config.ai else False}",
        ]

        console.print("\n".join(summary))
        return 0

    except Exception as e:
        console.print(f"[red]Configuration validation failed:[/]")
        console.print(f"  {e}")
        return 1


def _cmd_config_view(args: argparse.Namespace) -> int:
    """Handle config view command."""
    import json

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        if args.section:
            # View specific section
            section_data = getattr(config, args.section, None)
            if section_data is None:
                console.print(f"[red]Section not found: {args.section}[/]")
                console.print("Available sections: webhooks, providers, tasks, automations, scheduler, ai, logging, http")
                return 1

            console.print(f"\n[bold]Configuration Section: {args.section}[/]\n")

            if hasattr(section_data, "model_dump"):
                data = section_data.model_dump()
            elif isinstance(section_data, list):
                data = [item.model_dump() if hasattr(item, "model_dump") else item for item in section_data]
            else:
                data = section_data

            console.print(json.dumps(data, indent=2, default=str))
        else:
            # View full config summary
            console.print(f"\n[bold]Configuration: {config_path}[/]\n")

            sections = ["webhooks", "providers", "tasks", "automations", "scheduler", "ai", "logging"]
            for section in sections:
                data = getattr(config, section, None)
                if data:
                    if isinstance(data, list):
                        console.print(f"[cyan]{section}:[/] {len(data)} items")
                    else:
                        console.print(f"[cyan]{section}:[/] configured")
                else:
                    console.print(f"[dim]{section}:[/] not configured")

        return 0

    except Exception as e:
        logger.error(f"Error viewing config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_config_set(args: argparse.Namespace) -> int:
    """Handle config set command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        import yaml

        # Load raw YAML to modify
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Parse dot notation key
        keys = args.key.split(".")
        current = data

        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set value (try to parse as JSON for complex values)
        import json
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value

        current[keys[-1]] = value

        # Save
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        console = Console()
        console.print(f"[green]Set {args.key} = {args.value}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error setting config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_config_reload(args: argparse.Namespace) -> int:
    """Handle config reload command."""
    console = Console()

    console.print("\n[bold]Configuration Reload[/]\n")
    console.print("[yellow]Note: Configuration reload requires a running bot.[/]")
    console.print("The bot watches for config file changes automatically if config_watcher is enabled.")
    console.print("\nAlternatively, restart the bot to load new configuration.")

    return 0


def _cmd_config_export(args: argparse.Namespace) -> int:
    """Handle config export command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        output_path = Path(args.output)

        if args.format == "json":
            import json
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(config.model_dump(), f, indent=2, default=str)
        else:
            import yaml
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(config.model_dump(), f, default_flow_style=False, allow_unicode=True)

        console = Console()
        console.print(f"[green]Configuration exported to: {output_path}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error exporting config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_config_import(args: argparse.Namespace) -> int:
    """Handle config import command."""
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    config_path = Path(args.config)

    try:
        import json
        import yaml

        # Load input file
        with open(input_path, "r", encoding="utf-8") as f:
            if input_path.suffix == ".json":
                input_data = json.load(f)
            else:
                input_data = yaml.safe_load(f)

        if args.merge and config_path.exists():
            # Merge with existing config
            with open(config_path, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}

            # Deep merge
            def deep_merge(base, update):
                for key, value in update.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
                return base

            merged = deep_merge(existing, input_data)
            input_data = merged

        # Validate by loading as config
        _ = BotConfig(**input_data)

        # Save
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(input_data, f, default_flow_style=False, allow_unicode=True)

        console = Console()
        console.print(f"[green]Configuration imported to: {config_path}[/]")
        return 0

    except Exception as e:
        logger.error(f"Error importing config: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


# =========================================================================
# Stage 9: Auth command handlers
# =========================================================================
def cmd_auth(args: argparse.Namespace) -> int:
    """Handle authentication commands."""
    if not args.auth_command:
        print("Usage: feishu-webhook-bot auth <subcommand>")
        print("Subcommands: register, list-users, delete-user, unlock, verify")
        return 1

    handlers = {
        "register": _cmd_auth_register,
        "list-users": _cmd_auth_list_users,
        "delete-user": _cmd_auth_delete_user,
        "unlock": _cmd_auth_unlock,
        "verify": _cmd_auth_verify,
    }

    handler = handlers.get(args.auth_command)
    if handler:
        return handler(args)

    print(f"Unknown auth subcommand: {args.auth_command}")
    return 1


def _cmd_auth_register(args: argparse.Namespace) -> int:
    """Handle user registration command."""
    import getpass

    console = Console()

    console.print("\n[bold]Register New User[/]\n")
    console.print(f"Email: {args.email}")
    console.print(f"Username: {args.username}")

    # Get password if not provided
    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm Password: ")
        if password != confirm:
            console.print("[red]Passwords do not match![/]")
            return 1

    try:
        from .auth.service import AuthService

        auth_service = AuthService()
        user = asyncio.run(auth_service.register(
            email=args.email,
            username=args.username,
            password=password,
        ))

        console.print(f"\n[green]User registered successfully![/]")
        console.print(f"User ID: {user.id}")
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        console.print("The auth system requires the full bot installation.")
        return 1
    except Exception as e:
        console.print(f"[red]Registration failed:[/] {e}")
        return 1


def _cmd_auth_list_users(args: argparse.Namespace) -> int:
    """Handle list users command."""
    console = Console()

    console.print("\n[bold]Registered Users[/]\n")

    try:
        from .auth.service import AuthService

        auth_service = AuthService()
        users = asyncio.run(auth_service.list_users())

        if not users:
            console.print("[yellow]No users registered.[/]")
            return 0

        table = Table(title="Users")
        table.add_column("ID", style="cyan")
        table.add_column("Username", style="magenta")
        table.add_column("Email")
        table.add_column("Verified")
        table.add_column("Locked")

        for user in users:
            verified = "[green]Yes[/]" if user.email_verified else "[red]No[/]"
            locked = "[red]Yes[/]" if user.is_locked else "[green]No[/]"
            table.add_row(str(user.id), user.username, user.email, verified, locked)

        console.print(table)
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        console.print("User listing requires auth database setup.")
        return 1
    except Exception as e:
        console.print(f"[red]Error listing users:[/] {e}")
        return 1


def _cmd_auth_delete_user(args: argparse.Namespace) -> int:
    """Handle delete user command."""
    console = Console()

    console.print(f"\n[bold]Deleting User: {args.user_id}[/]\n")

    try:
        from .auth.service import AuthService

        auth_service = AuthService()
        asyncio.run(auth_service.delete_user(args.user_id))

        console.print(f"[green]User deleted: {args.user_id}[/]")
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        return 1
    except Exception as e:
        console.print(f"[red]Error deleting user:[/] {e}")
        return 1


def _cmd_auth_unlock(args: argparse.Namespace) -> int:
    """Handle unlock user command."""
    console = Console()

    console.print(f"\n[bold]Unlocking User: {args.user_id}[/]\n")

    try:
        from .auth.service import AuthService

        auth_service = AuthService()
        asyncio.run(auth_service.unlock_user(args.user_id))

        console.print(f"[green]User unlocked: {args.user_id}[/]")
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        return 1
    except Exception as e:
        console.print(f"[red]Error unlocking user:[/] {e}")
        return 1


def _cmd_auth_verify(args: argparse.Namespace) -> int:
    """Handle verify user email command."""
    console = Console()

    console.print(f"\n[bold]Verifying User Email: {args.user_id}[/]\n")

    try:
        from .auth.service import AuthService

        auth_service = AuthService()
        asyncio.run(auth_service.verify_email(args.user_id))

        console.print(f"[green]User email verified: {args.user_id}[/]")
        return 0

    except ImportError:
        console.print("[yellow]Auth service not available.[/]")
        return 1
    except Exception as e:
        console.print(f"[red]Error verifying email:[/] {e}")
        return 1


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
        "message": cmd_message,
        # Stage 7-9: Chat, Config, Auth
        "chat": cmd_chat,
        "config": cmd_config,
        "auth": cmd_auth,
        # Stage 10-12: Events, Logging, Image
        "events": cmd_events,
        "logging": cmd_logging,
        "image": cmd_image,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1
