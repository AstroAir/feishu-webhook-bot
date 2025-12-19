"""Scheduler CLI commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..base import BotConfig, logger


def cmd_scheduler(args: argparse.Namespace) -> int:
    """Handle scheduler management commands."""
    if not args.scheduler_command:
        print("Usage: feishu-webhook-bot scheduler <subcommand>")
        print("Subcommands: status, jobs, health, stats, pause, resume, remove, trigger")
        return 1

    handlers = {
        "status": _cmd_scheduler_status,
        "jobs": _cmd_scheduler_jobs,
        "health": _cmd_scheduler_health,
        "stats": _cmd_scheduler_stats,
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


def _cmd_scheduler_health(args: argparse.Namespace) -> int:
    """Handle scheduler health command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Scheduler Health Configuration[/]\n")

        sched_config = config.scheduler
        if not sched_config:
            console.print("[yellow]Scheduler not configured.[/]")
            return 0

        health_enabled = getattr(sched_config, "health_check_enabled", True)
        history_enabled = getattr(sched_config, "history_enabled", True)

        table = Table(title="Health Monitoring Settings")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Health Check Enabled", str(health_enabled))
        table.add_row(
            "Health Check Interval", f"{getattr(sched_config, 'health_check_interval', 60)}s"
        )
        table.add_row("Failure Threshold", str(getattr(sched_config, "failure_threshold", 3)))
        table.add_row(
            "Stale Job Threshold", f"{getattr(sched_config, 'stale_job_threshold', 3600)}s"
        )
        table.add_row("History Enabled", str(history_enabled))
        table.add_row(
            "History Retention Days", str(getattr(sched_config, "history_retention_days", 30))
        )

        console.print(table)
        console.print("\n[yellow]Note: Live health metrics require bot runtime.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error getting scheduler health: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _cmd_scheduler_stats(args: argparse.Namespace) -> int:
    """Handle scheduler statistics command."""
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    try:
        config = BotConfig.from_yaml(config_path)
        console = Console()

        console.print("\n[bold]Scheduler Statistics[/]\n")

        sched_config = config.scheduler
        if not sched_config:
            console.print("[yellow]Scheduler not configured.[/]")
            return 0

        table = Table(title="Scheduler Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Enabled", str(sched_config.enabled))
        table.add_row("Timezone", sched_config.timezone or "System default")
        table.add_row("Job Store Type", sched_config.job_store_type)
        table.add_row("Max Workers", str(getattr(sched_config, "max_workers", 10)))
        table.add_row("Job Coalesce", str(getattr(sched_config, "job_coalesce", True)))
        table.add_row("Max Instances", str(getattr(sched_config, "max_instances", 1)))
        table.add_row("Misfire Grace Time", f"{getattr(sched_config, 'misfire_grace_time', 60)}s")

        console.print(table)

        # Hooks configuration
        console.print("\n[bold]Hooks Configuration[/]")
        hooks_table = Table()
        hooks_table.add_column("Hook", style="cyan")
        hooks_table.add_column("Enabled", style="green")

        hooks_table.add_row(
            "Logging Hook", str(getattr(sched_config, "logging_hook_enabled", True))
        )
        hooks_table.add_row(
            "Metrics Hook", str(getattr(sched_config, "metrics_hook_enabled", True))
        )
        hooks_table.add_row("Alert Hook", str(getattr(sched_config, "alert_hook_enabled", False)))

        console.print(hooks_table)
        console.print("\n[yellow]Note: Live statistics require bot runtime.[/]")

        return 0

    except Exception as e:
        logger.error(f"Error getting scheduler stats: {e}", exc_info=True)
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
                trigger = "interval"
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
    console.print(
        f"\nTo pause task '{args.job_id}', use: feishu-webhook-bot task disable <task_name>"
    )

    return 0


def _cmd_scheduler_resume(args: argparse.Namespace) -> int:
    """Handle scheduler job resume command."""
    console = Console()

    console.print(f"\n[bold]Resuming Job: {args.job_id}[/]\n")
    console.print("[yellow]Note: Job control requires bot runtime context.[/]")
    console.print("The bot scheduler manages job states during execution.")
    console.print(
        f"\nTo resume task '{args.job_id}', use: feishu-webhook-bot task enable <task_name>"
    )

    return 0


def _cmd_scheduler_remove(args: argparse.Namespace) -> int:
    """Handle scheduler job remove command."""
    console = Console()

    console.print(f"\n[bold]Removing Job: {args.job_id}[/]\n")
    console.print(
        "[yellow]Note: To permanently remove a job, remove the task from configuration.[/]"
    )
    console.print("Edit your config.yaml and remove the task definition.")

    return 0


def _cmd_scheduler_trigger(args: argparse.Namespace) -> int:
    """Handle scheduler job trigger command."""
    console = Console()

    console.print(f"\n[bold]Triggering Job: {args.job_id}[/]\n")
    console.print("[yellow]Note: Job triggering requires bot runtime context.[/]")
    console.print("The scheduler can trigger jobs when the bot is running.")
    console.print(
        "\nTo run a task immediately, use: feishu-webhook-bot task run <task_name> --force"
    )

    return 0


__all__ = ["cmd_scheduler"]
