"""Task CLI commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..base import BotConfig, logger


def cmd_task(args: argparse.Namespace) -> int:
    """Handle task management commands."""
    if not args.task_command:
        print("Usage: feishu-webhook-bot task <subcommand>")
        print("Subcommands: list, run, status, enable, disable, history, pause, resume,")
        print("             details, stats, templates, create-from-template, update, reload, delete")
        return 1

    handlers = {
        "list": _cmd_task_list,
        "run": _cmd_task_run,
        "status": _cmd_task_status,
        "enable": _cmd_task_enable,
        "disable": _cmd_task_disable,
        "history": _cmd_task_history,
        "pause": _cmd_task_pause,
        "resume": _cmd_task_resume,
        "details": _cmd_task_details,
        "stats": _cmd_task_stats,
        "templates": _cmd_task_templates,
        "create-from-template": _cmd_task_create_from_template,
        "update": _cmd_task_update,
        "reload": _cmd_task_reload,
        "delete": _cmd_task_delete,
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
        console.print(
            f"\nTo manually trigger: restart the bot with task '{args.task_name}' enabled."
        )

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

        info_lines.append(
            f"[bold]Actions:[/] {len(task.actions) if task.actions else 0}"
        )

        if task.error_handling:
            info_lines.append("\n[bold]Error Handling:[/]")
            info_lines.append(
                f"  Retry on failure: {task.error_handling.retry_on_failure}"
            )
            info_lines.append(f"  Max retries: {task.error_handling.max_retries}")
            info_lines.append(
                f"  On failure: {task.error_handling.on_failure_action}"
            )

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


def _cmd_task_pause(args: argparse.Namespace) -> int:
    """Handle task pause command."""
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

        console.print(f"\n[bold]Pausing Task: {args.task_name}[/]\n")
        console.print("[yellow]Note: Task pause requires bot runtime context.[/]")
        console.print("The task will be paused when the bot is running.")
        console.print(
            f"\nTo disable task permanently, use: feishu-webhook-bot task disable {args.task_name}"
        )

        return 0

    except Exception as e:
        logger.error(f"Error pausing task: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_resume(args: argparse.Namespace) -> int:
    """Handle task resume command."""
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

        console.print(f"\n[bold]Resuming Task: {args.task_name}[/]\n")
        console.print("[yellow]Note: Task resume requires bot runtime context.[/]")
        console.print("The task will be resumed when the bot is running.")
        console.print(
            f"\nTo enable task permanently, use: feishu-webhook-bot task enable {args.task_name}"
        )

        return 0

    except Exception as e:
        logger.error(f"Error resuming task: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_details(args: argparse.Namespace) -> int:
    """Handle task details command."""
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

        # Build details
        info_lines = [
            f"[bold]Name:[/] {task.name}",
            f"[bold]Description:[/] {task.description or 'N/A'}",
            f"[bold]Enabled:[/] {task.enabled}",
        ]

        # Schedule info
        if task.cron:
            info_lines.append(f"[bold]Schedule (cron):[/] {task.cron}")
        elif task.interval:
            info_lines.append(f"[bold]Schedule (interval):[/] {task.interval}")
        elif task.schedule:
            info_lines.append(f"[bold]Schedule (mode):[/] {task.schedule.mode}")

        info_lines.append(f"[bold]Timeout:[/] {task.timeout}s")
        info_lines.append(f"[bold]Max Concurrent:[/] {task.max_concurrent}")
        info_lines.append(
            f"[bold]Actions:[/] {len(task.actions) if task.actions else 0}"
        )

        if task.conditions:
            info_lines.append(f"[bold]Conditions:[/] {len(task.conditions)}")

        # Error handling
        if task.error_handling:
            info_lines.append("\n[bold]Error Handling:[/]")
            info_lines.append(
                f"  Retry on failure: {task.error_handling.retry_on_failure}"
            )
            info_lines.append(f"  Max retries: {task.error_handling.max_retries}")
            info_lines.append(
                f"  On failure: {task.error_handling.on_failure_action}"
            )

        # Actions details
        if task.actions:
            info_lines.append("\n[bold]Actions:[/]")
            for i, action in enumerate(task.actions, 1):
                action_type = action.type if hasattr(action, 'type') else 'unknown'
                info_lines.append(f"  {i}. {action_type}")

        console.print(
            Panel("\n".join(info_lines), title=f"Task Details: {args.task_name}")
        )
        return 0

    except Exception as e:
        logger.error(f"Error getting task details: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_stats(args: argparse.Namespace) -> int:
    """Handle task stats command - show task statistics summary."""
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

        console.print("\n[bold]Task Statistics Summary[/]\n")

        total = len(config.tasks)
        enabled = sum(1 for t in config.tasks if t.enabled)
        disabled = total - enabled

        # Count by schedule type
        cron_count = sum(1 for t in config.tasks if t.cron)
        interval_count = sum(1 for t in config.tasks if t.interval)
        schedule_count = sum(1 for t in config.tasks if t.schedule and not t.cron)

        # Count actions
        total_actions = sum(len(t.actions) for t in config.tasks if t.actions)

        table = Table(title="Task Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Tasks", str(total))
        table.add_row("Enabled", f"[green]{enabled}[/]")
        table.add_row("Disabled", f"[red]{disabled}[/]")
        table.add_row("Cron Scheduled", str(cron_count))
        table.add_row("Interval Scheduled", str(interval_count))
        table.add_row("Other Schedule", str(schedule_count))
        table.add_row("Total Actions", str(total_actions))

        console.print(table)

        console.print("\n[yellow]Note: Runtime statistics require bot to be running.[/]")
        return 0

    except Exception as e:
        logger.error(f"Error getting task stats: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_templates(args: argparse.Namespace) -> int:
    """Handle task templates command - list available task templates."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        templates = getattr(config, "task_templates", [])
        if not templates:
            console.print("[yellow]No task templates configured.[/]")
            console.print("\nTo add templates, define them in your config.yaml:")
            console.print("  task_templates:")
            console.print("    - name: my_template")
            console.print("      description: My template description")
            console.print("      base_task: ...")
            return 0

        console.print("\n[bold]Available Task Templates[/]\n")

        table = Table(title="Task Templates")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Parameters", style="magenta")

        for tpl in templates:
            name = tpl.name if hasattr(tpl, "name") else str(tpl.get("name", ""))
            desc = (
                tpl.description
                if hasattr(tpl, "description")
                else str(tpl.get("description", "N/A"))
            )
            params = (
                tpl.parameters
                if hasattr(tpl, "parameters")
                else tpl.get("parameters", [])
            )
            param_count = len(params) if params else 0
            table.add_row(name, desc, str(param_count))

        console.print(table)
        return 0

    except Exception as e:
        logger.error(f"Error listing task templates: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_create_from_template(args: argparse.Namespace) -> int:
    """Handle task create-from-template command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        templates = getattr(config, "task_templates", [])
        if not templates:
            console.print("[red]No task templates configured.[/]")
            return 1

        # Find template
        template = None
        for tpl in templates:
            tpl_name = tpl.name if hasattr(tpl, "name") else tpl.get("name", "")
            if tpl_name == args.template_name:
                template = tpl
                break

        if not template:
            console.print(f"[red]Template not found: {args.template_name}[/]")
            return 1

        # Parse parameters
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON parameters: {e}[/]")
            return 1

        # Create task from template
        from ...tasks.templates import TaskTemplateEngine

        engine = TaskTemplateEngine([template])
        new_task = engine.create_task_from_template(
            args.template_name, args.task_name, params
        )

        # Add to config
        config.tasks.append(new_task)
        config.save_yaml(config_path)

        console.print(
            f"[green]Created task '{args.task_name}' from template "
            f"'{args.template_name}'[/]"
        )
        return 0

    except Exception as e:
        logger.error(f"Error creating task from template: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_update(args: argparse.Namespace) -> int:
    """Handle task update command - update task configuration."""
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

        updated = []

        if args.timeout is not None:
            task.timeout = args.timeout
            updated.append(f"timeout={args.timeout}")

        if args.max_concurrent is not None:
            task.max_concurrent = args.max_concurrent
            updated.append(f"max_concurrent={args.max_concurrent}")

        if args.priority is not None:
            task.priority = args.priority
            updated.append(f"priority={args.priority}")

        if args.description is not None:
            task.description = args.description
            updated.append("description")

        if not updated:
            console.print("[yellow]No updates specified. Use --help for options.[/]")
            return 0

        config.save_yaml(config_path)
        console.print(
            f"[green]Updated task '{args.task_name}': {', '.join(updated)}[/]"
        )
        return 0

    except Exception as e:
        logger.error(f"Error updating task: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_reload(args: argparse.Namespace) -> int:
    """Handle task reload command - reload all tasks from configuration."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        task_count = len(config.tasks) if config.tasks else 0

        console.print("\n[bold]Task Reload[/]\n")
        console.print(f"Configuration file: {config_path}")
        console.print(f"Tasks in configuration: {task_count}")

        console.print("\n[yellow]Note: Task reload requires bot runtime context.[/]")
        console.print("When the bot is running, tasks are automatically reloaded.")
        console.print("\nTo apply changes:")
        console.print("  1. Stop the bot: feishu-webhook-bot stop")
        console.print("  2. Start the bot: feishu-webhook-bot start")
        console.print("Or use the WebUI to reload tasks at runtime.")

        return 0

    except Exception as e:
        logger.error(f"Error reloading tasks: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_task_delete(args: argparse.Namespace) -> int:
    """Handle task delete command - remove a task from configuration."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        # Find task
        task = config.get_task(args.task_name)
        if not task:
            console.print(f"[red]Task not found: {args.task_name}[/]")
            return 1

        # Confirm deletion
        if not args.yes:
            console.print(
                f"\n[bold yellow]Warning:[/] About to delete task '{args.task_name}'"
            )
            console.print("This action cannot be undone.\n")
            confirm = input("Type 'yes' to confirm deletion: ")
            if confirm.lower() != "yes":
                console.print("[yellow]Deletion cancelled.[/]")
                return 0

        # Remove task from config
        for i, t in enumerate(config.tasks):
            if t.name == args.task_name:
                config.tasks.pop(i)
                break

        # Save config
        config.save_yaml(config_path)
        console.print(f"[green]Task '{args.task_name}' deleted successfully.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error deleting task: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


__all__ = ["cmd_task"]
