"""CLI argument parser and banner display."""

from __future__ import annotations

import argparse

from rich.console import Console
from rich.panel import Panel

from .. import __version__
from ..core import BotConfig


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

    # Plugins command with subcommands
    plugins_parser = subparsers.add_parser("plugins", help="Plugin management")
    plugins_subparsers = plugins_parser.add_subparsers(
        dest="plugins_command", help="Plugin subcommands"
    )

    # plugins list (default)
    plugins_list_parser = plugins_subparsers.add_parser("list", help="List all plugins")
    plugins_list_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # plugins info <name>
    plugins_info_parser = plugins_subparsers.add_parser("info", help="Show plugin details")
    plugins_info_parser.add_argument("plugin_name", help="Plugin name")
    plugins_info_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # plugins enable <name>
    plugins_enable_parser = plugins_subparsers.add_parser("enable", help="Enable a plugin")
    plugins_enable_parser.add_argument("plugin_name", help="Plugin name to enable")
    plugins_enable_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    plugins_enable_parser.add_argument(
        "--save",
        action="store_true",
        help="Save enabled state to config file",
    )

    # plugins disable <name>
    plugins_disable_parser = plugins_subparsers.add_parser("disable", help="Disable a plugin")
    plugins_disable_parser.add_argument("plugin_name", help="Plugin name to disable")
    plugins_disable_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    plugins_disable_parser.add_argument(
        "--save",
        action="store_true",
        help="Save disabled state to config file",
    )

    # plugins reload [name]
    plugins_reload_parser = plugins_subparsers.add_parser("reload", help="Reload plugin(s)")
    plugins_reload_parser.add_argument(
        "plugin_name", nargs="?", help="Plugin name (omit to reload all)"
    )
    plugins_reload_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # plugins config <name>
    plugins_config_parser = plugins_subparsers.add_parser(
        "config", help="View or update plugin configuration"
    )
    plugins_config_parser.add_argument("plugin_name", help="Plugin name")
    plugins_config_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    plugins_config_parser.add_argument(
        "--get", metavar="KEY", help="Get a specific configuration value"
    )
    plugins_config_parser.add_argument(
        "--set",
        metavar="KEY=VALUE",
        action="append",
        help="Set configuration value(s). Can be used multiple times.",
    )
    plugins_config_parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload plugin after updating configuration",
    )

    # plugins priority <name> <priority>
    plugins_priority_parser = plugins_subparsers.add_parser(
        "priority", help="Set plugin loading priority"
    )
    plugins_priority_parser.add_argument("plugin_name", help="Plugin name")
    plugins_priority_parser.add_argument(
        "priority", type=int, help="Priority value (lower loads first)"
    )
    plugins_priority_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # plugins permissions [name]
    plugins_perms_parser = plugins_subparsers.add_parser(
        "permissions", help="View or manage plugin permissions"
    )
    plugins_perms_parser.add_argument(
        "plugin_name", nargs="?", help="Plugin name (omit to list all permissions)"
    )
    plugins_perms_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    plugins_perms_parser.add_argument(
        "--grant", metavar="PERMISSION", help="Grant a permission to the plugin"
    )
    plugins_perms_parser.add_argument(
        "--revoke", metavar="PERMISSION", help="Revoke a permission from the plugin"
    )
    plugins_perms_parser.add_argument(
        "--approve",
        metavar="PERMISSION",
        help="Approve a dangerous permission for the plugin",
    )

    # Also add -c to main plugins parser for backward compatibility
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
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    ai_chat_parser.add_argument(
        "--user-id",
        default="cli-user",
        help="User ID for conversation context (default: cli-user)",
    )

    # ai model
    ai_model_parser = ai_subparsers.add_parser("model", help="Show or switch AI model")
    ai_model_parser.add_argument("model_name", nargs="?", help="Model name to switch to")
    ai_model_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai models
    ai_models_parser = ai_subparsers.add_parser("models", help="List available AI models")
    ai_models_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai stats
    ai_stats_parser = ai_subparsers.add_parser("stats", help="Show AI usage statistics")
    ai_stats_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai tools
    ai_tools_parser = ai_subparsers.add_parser("tools", help="List registered AI tools")
    ai_tools_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai clear <user_id>
    ai_clear_parser = ai_subparsers.add_parser("clear", help="Clear conversation history")
    ai_clear_parser.add_argument("user_id", help="User ID to clear history for")
    ai_clear_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai mcp
    ai_mcp_parser = ai_subparsers.add_parser("mcp", help="MCP server status")
    ai_mcp_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai test
    ai_test_parser = ai_subparsers.add_parser("test", help="Test AI configuration and connection")
    ai_test_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    ai_test_parser.add_argument(
        "--message",
        default="Hello, this is a test message.",
        help="Test message to send (default: 'Hello, this is a test message.')",
    )

    # ai stream <message>
    ai_stream_parser = ai_subparsers.add_parser("stream", help="Test AI streaming response")
    ai_stream_parser.add_argument("message", help="Message to send to AI")
    ai_stream_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    ai_stream_parser.add_argument(
        "--user-id",
        default="cli-user",
        help="User ID for conversation context (default: cli-user)",
    )

    # ai conversation - conversation management subcommands
    ai_conv_parser = ai_subparsers.add_parser("conversation", help="Conversation management")
    ai_conv_subparsers = ai_conv_parser.add_subparsers(
        dest="conv_command", help="Conversation subcommands"
    )

    # ai conversation list
    ai_conv_list_parser = ai_conv_subparsers.add_parser("list", help="List active conversations")
    ai_conv_list_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai conversation export <user_id>
    ai_conv_export_parser = ai_conv_subparsers.add_parser("export", help="Export a conversation")
    ai_conv_export_parser.add_argument("user_id", help="User ID of the conversation")
    ai_conv_export_parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout)",
    )
    ai_conv_export_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai conversation import <file>
    ai_conv_import_parser = ai_conv_subparsers.add_parser("import", help="Import a conversation")
    ai_conv_import_parser.add_argument("file", help="JSON file to import from")
    ai_conv_import_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai conversation delete <user_id>
    ai_conv_delete_parser = ai_conv_subparsers.add_parser("delete", help="Delete a conversation")
    ai_conv_delete_parser.add_argument("user_id", help="User ID of the conversation")
    ai_conv_delete_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai conversation details <user_id>
    ai_conv_details_parser = ai_conv_subparsers.add_parser(
        "details", help="Show conversation details"
    )
    ai_conv_details_parser.add_argument("user_id", help="User ID of the conversation")
    ai_conv_details_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai multi-agent - multi-agent management subcommands
    ai_ma_parser = ai_subparsers.add_parser("multi-agent", help="Multi-agent orchestration")
    ai_ma_subparsers = ai_ma_parser.add_subparsers(
        dest="ma_command", help="Multi-agent subcommands"
    )

    # ai multi-agent status
    ai_ma_status_parser = ai_ma_subparsers.add_parser("status", help="Show multi-agent status")
    ai_ma_status_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # ai multi-agent test <message>
    ai_ma_test_parser = ai_ma_subparsers.add_parser("test", help="Test multi-agent orchestration")
    ai_ma_test_parser.add_argument("message", help="Message to process")
    ai_ma_test_parser.add_argument(
        "--mode",
        choices=["sequential", "concurrent", "hierarchical"],
        help="Orchestration mode (default: use config)",
    )
    ai_ma_test_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
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
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task run <name>
    task_run_parser = task_subparsers.add_parser("run", help="Run a task immediately")
    task_run_parser.add_argument("task_name", help="Name of the task to run")
    task_run_parser.add_argument(
        "--force",
        action="store_true",
        help="Force run even if task is already running",
    )
    task_run_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task status <name>
    task_status_parser = task_subparsers.add_parser("status", help="Show task status")
    task_status_parser.add_argument("task_name", help="Name of the task")
    task_status_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task enable <name>
    task_enable_parser = task_subparsers.add_parser("enable", help="Enable a task")
    task_enable_parser.add_argument("task_name", help="Name of the task to enable")
    task_enable_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task disable <name>
    task_disable_parser = task_subparsers.add_parser("disable", help="Disable a task")
    task_disable_parser.add_argument("task_name", help="Name of the task to disable")
    task_disable_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task history <name>
    task_history_parser = task_subparsers.add_parser("history", help="Show task execution history")
    task_history_parser.add_argument("task_name", help="Name of the task")
    task_history_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of history entries to show (default: 10)",
    )
    task_history_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task pause <name>
    task_pause_parser = task_subparsers.add_parser("pause", help="Pause a task")
    task_pause_parser.add_argument("task_name", help="Name of the task to pause")
    task_pause_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task resume <name>
    task_resume_parser = task_subparsers.add_parser("resume", help="Resume a paused task")
    task_resume_parser.add_argument("task_name", help="Name of the task to resume")
    task_resume_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task details <name>
    task_details_parser = task_subparsers.add_parser(
        "details", help="Show detailed task information"
    )
    task_details_parser.add_argument("task_name", help="Name of the task")
    task_details_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task stats - Show task statistics
    task_stats_parser = task_subparsers.add_parser("stats", help="Show task statistics summary")
    task_stats_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task templates - List available task templates
    task_templates_parser = task_subparsers.add_parser(
        "templates", help="List available task templates"
    )
    task_templates_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task create-from-template <template_name> <task_name>
    task_create_tpl_parser = task_subparsers.add_parser(
        "create-from-template", help="Create a new task from a template"
    )
    task_create_tpl_parser.add_argument("template_name", help="Name of the template to use")
    task_create_tpl_parser.add_argument("task_name", help="Name for the new task")
    task_create_tpl_parser.add_argument(
        "--params",
        type=str,
        default="{}",
        help="JSON string of parameters to pass to the template (default: {})",
    )
    task_create_tpl_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task update <name> - Update task configuration
    task_update_parser = task_subparsers.add_parser("update", help="Update task configuration")
    task_update_parser.add_argument("task_name", help="Name of the task to update")
    task_update_parser.add_argument("--timeout", type=int, help="Set task timeout in seconds")
    task_update_parser.add_argument(
        "--max-concurrent", type=int, help="Set maximum concurrent executions"
    )
    task_update_parser.add_argument("--priority", type=int, help="Set task priority")
    task_update_parser.add_argument("--description", type=str, help="Set task description")
    task_update_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task reload - Reload all tasks from configuration
    task_reload_parser = task_subparsers.add_parser(
        "reload", help="Reload all tasks from configuration"
    )
    task_reload_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # task delete <name> - Delete a task
    task_delete_parser = task_subparsers.add_parser(
        "delete", help="Delete a task from configuration"
    )
    task_delete_parser.add_argument("task_name", help="Name of the task to delete")
    task_delete_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    task_delete_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
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
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler jobs
    sched_jobs_parser = scheduler_subparsers.add_parser("jobs", help="List all scheduled jobs")
    sched_jobs_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler pause <job_id>
    sched_pause_parser = scheduler_subparsers.add_parser("pause", help="Pause a job")
    sched_pause_parser.add_argument("job_id", help="ID of the job to pause")
    sched_pause_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler resume <job_id>
    sched_resume_parser = scheduler_subparsers.add_parser("resume", help="Resume a paused job")
    sched_resume_parser.add_argument("job_id", help="ID of the job to resume")
    sched_resume_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler remove <job_id>
    sched_remove_parser = scheduler_subparsers.add_parser("remove", help="Remove a job")
    sched_remove_parser.add_argument("job_id", help="ID of the job to remove")
    sched_remove_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler trigger <job_id>
    sched_trigger_parser = scheduler_subparsers.add_parser(
        "trigger", help="Trigger a job immediately"
    )
    sched_trigger_parser.add_argument("job_id", help="ID of the job to trigger")
    sched_trigger_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler health
    sched_health_parser = scheduler_subparsers.add_parser(
        "health", help="Show scheduler health configuration"
    )
    sched_health_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # scheduler stats
    sched_stats_parser = scheduler_subparsers.add_parser(
        "stats", help="Show scheduler statistics and configuration"
    )
    sched_stats_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
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
    auto_list_parser = automation_subparsers.add_parser("list", help="List automation rules")
    auto_list_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation status
    auto_status_parser = automation_subparsers.add_parser(
        "status", help="Show automation engine status"
    )
    auto_status_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation trigger <name>
    auto_trigger_parser = automation_subparsers.add_parser(
        "trigger", help="Manually trigger an automation rule"
    )
    auto_trigger_parser.add_argument("rule_name", help="Name of the rule to trigger")
    auto_trigger_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation test <name>
    auto_test_parser = automation_subparsers.add_parser("test", help="Test an automation rule")
    auto_test_parser.add_argument("rule_name", help="Name of the rule to test")
    auto_test_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation enable <name>
    auto_enable_parser = automation_subparsers.add_parser(
        "enable", help="Enable an automation rule"
    )
    auto_enable_parser.add_argument("rule_name", help="Name of the rule to enable")
    auto_enable_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation disable <name>
    auto_disable_parser = automation_subparsers.add_parser(
        "disable", help="Disable an automation rule"
    )
    auto_disable_parser.add_argument("rule_name", help="Name of the rule to disable")
    auto_disable_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation history <name>
    auto_history_parser = automation_subparsers.add_parser(
        "history", help="Show automation execution history"
    )
    auto_history_parser.add_argument("rule_name", help="Name of the rule")
    auto_history_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of history entries to show (default: 10)",
    )
    auto_history_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation details <name>
    auto_details_parser = automation_subparsers.add_parser(
        "details", help="Show detailed automation rule information"
    )
    auto_details_parser.add_argument("rule_name", help="Name of the rule")
    auto_details_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation create
    auto_create_parser = automation_subparsers.add_parser(
        "create", help="Create a new automation rule (interactive)"
    )
    auto_create_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation edit <name>
    auto_edit_parser = automation_subparsers.add_parser(
        "edit", help="Edit an existing automation rule"
    )
    auto_edit_parser.add_argument("rule_name", help="Name of the rule to edit")
    auto_edit_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation delete <name>
    auto_delete_parser = automation_subparsers.add_parser(
        "delete", help="Delete an automation rule"
    )
    auto_delete_parser.add_argument("rule_name", help="Name of the rule to delete")
    auto_delete_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation run <name> [params...]
    auto_run_parser = automation_subparsers.add_parser(
        "run", help="Run an automation rule with parameters"
    )
    auto_run_parser.add_argument("rule_name", help="Name of the rule to run")
    auto_run_parser.add_argument("params", nargs="*", help="Parameters in key=value format")
    auto_run_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation validate
    auto_validate_parser = automation_subparsers.add_parser(
        "validate", help="Validate automation rules configuration"
    )
    auto_validate_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation import <file>
    auto_import_parser = automation_subparsers.add_parser(
        "import", help="Import automation rules from file"
    )
    auto_import_parser.add_argument("import_file", help="Path to import file (YAML/JSON)")
    auto_import_parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing rules with same name"
    )
    auto_import_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation export <file>
    auto_export_parser = automation_subparsers.add_parser(
        "export", help="Export automation rules to file"
    )
    auto_export_parser.add_argument("export_file", help="Path to export file (YAML/JSON)")
    auto_export_parser.add_argument(
        "--rules",
        nargs="*",
        dest="rule_names",
        help="Specific rules to export (exports all if not specified)",
    )
    auto_export_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # automation templates
    auto_templates_parser = automation_subparsers.add_parser(
        "templates", help="List available workflow templates"
    )
    auto_templates_parser.add_argument(
        "--show-actions", action="store_true", help="Also show available action types"
    )

    # =========================================================================
    # Stage 5: Provider CLI commands
    # =========================================================================
    provider_parser = subparsers.add_parser("provider", help="Provider management")
    provider_subparsers = provider_parser.add_subparsers(
        dest="provider_command", help="Provider subcommands"
    )

    # provider list
    prov_list_parser = provider_subparsers.add_parser("list", help="List configured providers")
    prov_list_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # provider info <name>
    prov_info_parser = provider_subparsers.add_parser("info", help="Show provider details")
    prov_info_parser.add_argument("provider_name", help="Name of the provider")
    prov_info_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # provider test <name>
    prov_test_parser = provider_subparsers.add_parser("test", help="Test provider connectivity")
    prov_test_parser.add_argument("provider_name", help="Name of the provider")
    prov_test_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # provider stats <name>
    prov_stats_parser = provider_subparsers.add_parser(
        "stats", help="Show provider send statistics"
    )
    prov_stats_parser.add_argument("provider_name", help="Name of the provider")
    prov_stats_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # provider send <name> <target> <message>
    prov_send_parser = provider_subparsers.add_parser("send", help="Send a message via provider")
    prov_send_parser.add_argument("provider_name", help="Name of the provider")
    prov_send_parser.add_argument(
        "target",
        help="Target identifier (e.g., 'group:123456' for QQ, webhook URL for Feishu)",
    )
    prov_send_parser.add_argument("message", help="Message text to send")
    prov_send_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # provider status
    prov_status_parser = provider_subparsers.add_parser("status", help="Show all providers status")
    prov_status_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 5.5: Bridge CLI commands
    # =========================================================================
    bridge_parser = subparsers.add_parser("bridge", help="Message bridge management")
    bridge_subparsers = bridge_parser.add_subparsers(
        dest="bridge_command", help="Bridge subcommands"
    )

    # bridge status
    bridge_status_parser = bridge_subparsers.add_parser(
        "status", help="Show bridge status and statistics"
    )
    bridge_status_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # bridge list
    bridge_list_parser = bridge_subparsers.add_parser("list", help="List bridge rules")
    bridge_list_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # bridge enable <rule_name>
    bridge_enable_parser = bridge_subparsers.add_parser("enable", help="Enable a bridge rule")
    bridge_enable_parser.add_argument("rule_name", help="Name of the rule to enable")
    bridge_enable_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # bridge disable <rule_name>
    bridge_disable_parser = bridge_subparsers.add_parser("disable", help="Disable a bridge rule")
    bridge_disable_parser.add_argument("rule_name", help="Name of the rule to disable")
    bridge_disable_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # bridge test <rule_name>
    bridge_test_parser = bridge_subparsers.add_parser(
        "test", help="Test a bridge rule with a sample message"
    )
    bridge_test_parser.add_argument("rule_name", help="Name of the rule to test")
    bridge_test_parser.add_argument(
        "-m",
        "--message",
        default="Test message from CLI",
        help="Test message content",
    )
    bridge_test_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
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
    msg_stats_parser = message_subparsers.add_parser("stats", help="Show message statistics")
    msg_stats_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # message queue status
    msg_queue_parser = message_subparsers.add_parser("queue", help="Show message queue status")
    msg_queue_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # message tracker
    msg_tracker_parser = message_subparsers.add_parser(
        "tracker", help="Show message tracker statistics"
    )
    msg_tracker_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # message circuit-breaker
    msg_cb_parser = message_subparsers.add_parser(
        "circuit-breaker", help="Show circuit breaker status"
    )
    msg_cb_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
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
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # chat test <platform> <message>
    chat_test_parser = chat_subparsers.add_parser("test", help="Test message processing")
    chat_test_parser.add_argument("platform", choices=["feishu", "qq"], help="Platform to test")
    chat_test_parser.add_argument("message", help="Message to process")
    chat_test_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # chat commands
    chat_commands_parser = chat_subparsers.add_parser(
        "commands", help="List built-in chat commands"
    )
    chat_commands_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # chat broadcast <message>
    chat_broadcast_parser = chat_subparsers.add_parser(
        "broadcast", help="Broadcast message to all providers"
    )
    chat_broadcast_parser.add_argument("message", help="Message to broadcast")
    chat_broadcast_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Stage 8: Config system CLI commands
    # =========================================================================
    config_cmd_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_cmd_parser.add_subparsers(
        dest="config_command", help="Config subcommands"
    )

    # config validate
    config_validate_parser = config_subparsers.add_parser(
        "validate", help="Validate configuration file"
    )
    config_validate_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config view [section]
    config_view_parser = config_subparsers.add_parser("view", help="View configuration")
    config_view_parser.add_argument(
        "section",
        nargs="?",
        help="Configuration section to view (e.g., webhooks, scheduler, ai)",
    )
    config_view_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config set <key> <value>
    config_set_parser = config_subparsers.add_parser("set", help="Set a configuration value")
    config_set_parser.add_argument(
        "key", help="Configuration key (dot notation, e.g., logging.level)"
    )
    config_set_parser.add_argument("value", help="Value to set")
    config_set_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config reload
    config_reload_parser = config_subparsers.add_parser(
        "reload", help="Reload configuration (requires running bot)"
    )
    config_reload_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config export
    config_export_parser = config_subparsers.add_parser("export", help="Export configuration")
    config_export_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output file path",
    )
    config_export_parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Export format (default: yaml)",
    )
    config_export_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # config import <file>
    config_import_parser = config_subparsers.add_parser("import", help="Import configuration")
    config_import_parser.add_argument("input_file", help="Input file to import from")
    config_import_parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge with existing config instead of replacing",
    )
    config_import_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
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
        "--password",
        help="User password (will prompt if not provided)",
    )
    auth_register_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # auth list-users
    auth_list_parser = auth_subparsers.add_parser("list-users", help="List all registered users")
    auth_list_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # auth delete-user <user_id>
    auth_delete_parser = auth_subparsers.add_parser("delete-user", help="Delete a user")
    auth_delete_parser.add_argument("user_id", help="User ID to delete")
    auth_delete_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # auth unlock <user_id>
    auth_unlock_parser = auth_subparsers.add_parser("unlock", help="Unlock a user account")
    auth_unlock_parser.add_argument("user_id", help="User ID to unlock")
    auth_unlock_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # auth verify <user_id>
    auth_verify_parser = auth_subparsers.add_parser("verify", help="Verify user email")
    auth_verify_parser.add_argument("user_id", help="User ID to verify")
    auth_verify_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Phase 10: Event Server Commands
    # =========================================================================
    events_parser = subparsers.add_parser("events", help="Event server management commands")
    events_subparsers = events_parser.add_subparsers(
        dest="events_command", help="Event server subcommands"
    )

    # events status
    status_parser = events_subparsers.add_parser("status", help="Show event server status")
    status_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # events start
    events_start_parser = events_subparsers.add_parser("start", help="Start the event server")
    events_start_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # events stop
    events_stop_parser = events_subparsers.add_parser("stop", help="Stop the event server")
    events_stop_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # events test-webhook
    test_webhook_parser = events_subparsers.add_parser("test-webhook", help="Test webhook endpoint")
    test_webhook_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    test_webhook_parser.add_argument("type", choices=["feishu", "qq"], help="Provider type to test")

    # =========================================================================
    # Phase 11: Logging Commands
    # =========================================================================
    logging_parser = subparsers.add_parser("logging", help="Logging management commands")
    logging_subparsers = logging_parser.add_subparsers(
        dest="logging_command", help="Logging subcommands"
    )

    # logging level <level>
    level_parser = logging_subparsers.add_parser("level", help="Set logging level globally")
    level_parser.add_argument(
        "level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level to set",
    )
    level_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # logging show
    show_parser = logging_subparsers.add_parser("show", help="Show recent log entries")
    show_parser.add_argument(
        "--limit", type=int, default=20, help="Number of recent log entries to show (default: 20)"
    )
    show_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # logging tail
    tail_parser = logging_subparsers.add_parser("tail", help="Follow log file in real-time")
    tail_parser.add_argument(
        "--follow", action="store_true", help="Keep following the log file (Ctrl+C to stop)"
    )
    tail_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    # =========================================================================
    # Phase 12: Calendar Commands
    # =========================================================================
    calendar_parser = subparsers.add_parser(
        "calendar", help="Feishu calendar subscription management"
    )
    calendar_subparsers = calendar_parser.add_subparsers(
        dest="calendar_command", help="Calendar subcommands"
    )

    # calendar setup
    cal_setup_parser = calendar_subparsers.add_parser(
        "setup", help="Interactive calendar setup wizard"
    )
    cal_setup_parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to configuration file"
    )

    # calendar test
    cal_test_parser = calendar_subparsers.add_parser("test", help="Test calendar API connection")
    cal_test_parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to configuration file"
    )
    cal_test_parser.add_argument("--app-id", help="Override app_id from config")
    cal_test_parser.add_argument("--app-secret", help="Override app_secret from config")

    # calendar list
    cal_list_parser = calendar_subparsers.add_parser("list", help="List available calendars")
    cal_list_parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to configuration file"
    )

    # calendar events [calendar_id]
    cal_events_parser = calendar_subparsers.add_parser("events", help="Show upcoming events")
    cal_events_parser.add_argument(
        "calendar_id", nargs="?", default="primary", help="Calendar ID (default: primary)"
    )
    cal_events_parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to configuration file"
    )
    cal_events_parser.add_argument(
        "--days", type=int, default=7, help="Days ahead to show (default: 7)"
    )

    # calendar today [calendar_id]
    cal_today_parser = calendar_subparsers.add_parser("today", help="Show today's events")
    cal_today_parser.add_argument(
        "calendar_id", nargs="?", default="primary", help="Calendar ID (default: primary)"
    )
    cal_today_parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to configuration file"
    )

    # calendar status
    cal_status_parser = calendar_subparsers.add_parser("status", help="Show calendar plugin status")
    cal_status_parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to configuration file"
    )

    # calendar permissions
    calendar_subparsers.add_parser("permissions", help="Show required permissions guide")

    # calendar send-summary
    cal_summary_parser = calendar_subparsers.add_parser(
        "send-summary", help="Send daily summary now"
    )
    cal_summary_parser.add_argument(
        "-c", "--config", default="config.yaml", help="Path to configuration file"
    )
    cal_summary_parser.add_argument("--webhook", default="default", help="Webhook name to use")

    # =========================================================================
    # Phase 13: Image Upload Commands
    # =========================================================================
    image_parser = subparsers.add_parser("image", help="Image upload management commands")
    image_subparsers = image_parser.add_subparsers(
        dest="image_command", help="Image upload subcommands"
    )

    # image upload <file>
    upload_parser = image_subparsers.add_parser("upload", help="Upload image to Feishu")
    upload_parser.add_argument("file", help="Path to image file to upload")
    upload_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    upload_parser.add_argument("--app-id", help="Feishu app ID (overrides config)")
    upload_parser.add_argument("--app-secret", help="Feishu app secret (overrides config)")
    upload_parser.add_argument(
        "--type",
        choices=["message", "avatar"],
        default="message",
        help="Image type (default: message)",
    )

    # image permissions
    perms_parser = image_subparsers.add_parser("permissions", help="Check image upload permissions")
    perms_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    perms_parser.add_argument("--app-id", help="Feishu app ID (overrides config)")
    perms_parser.add_argument("--app-secret", help="Feishu app secret (overrides config)")
    perms_parser.add_argument(
        "--auto-fix", action="store_true", help="Automatically open browser to fix permissions"
    )

    # image configure
    config_parser = image_subparsers.add_parser(
        "configure", help="Configure image upload parameters"
    )
    config_parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    config_parser.add_argument("--app-id", help="Set Feishu app ID in config")
    config_parser.add_argument("--app-secret", help="Set Feishu app secret in config")
    config_parser.add_argument("--timeout", type=float, help="Set request timeout in seconds")

    return parser


__all__ = ["build_parser", "print_banner"]
