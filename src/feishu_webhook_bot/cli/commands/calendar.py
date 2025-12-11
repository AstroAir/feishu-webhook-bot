"""Calendar CLI commands."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from ..base import BotConfig, FeishuWebhookClient


def cmd_calendar(args: argparse.Namespace) -> int:
    """Handle calendar management commands."""
    if not args.calendar_command:
        print("Usage: feishu-webhook-bot calendar <subcommand>")
        print("Subcommands: setup, test, list, events, today, status, permissions, send-summary")
        return 1

    handlers = {
        "setup": _cmd_calendar_setup,
        "test": _cmd_calendar_test,
        "list": _cmd_calendar_list,
        "events": _cmd_calendar_events,
        "today": _cmd_calendar_today,
        "status": _cmd_calendar_status,
        "permissions": _cmd_calendar_permissions,
        "send-summary": _cmd_calendar_send_summary,
    }

    handler = handlers.get(args.calendar_command)
    if handler:
        return handler(args)

    print(f"Unknown calendar subcommand: {args.calendar_command}")
    return 1


def _get_calendar_plugin(config_path: Path) -> Any:
    """Helper to get the calendar plugin instance."""
    from ...plugins.feishu_calendar import FeishuCalendarPlugin

    if not config_path.exists():
        return None

    config = BotConfig.from_yaml(config_path)

    # Find calendar plugin settings
    plugin_settings = {}
    if config.plugins and hasattr(config.plugins, "plugin_settings"):
        for ps in config.plugins.plugin_settings:
            if ps.plugin_name == "feishu-calendar":
                plugin_settings = ps.settings or {}
                break

    # Create plugin instance with settings
    plugin = FeishuCalendarPlugin()
    plugin._settings = plugin_settings
    plugin.on_load()
    return plugin


def _cmd_calendar_setup(args: argparse.Namespace) -> int:
    """Handle calendar setup wizard."""
    console = Console()
    console.print("\n[bold cyan]飞书日历插件配置向导[/]\n")

    try:
        from ...plugins.feishu_calendar import CalendarSetupGuide, FeishuCalendarPlugin

        # Show setup steps
        console.print("[bold]配置步骤:[/]\n")
        for step in CalendarSetupGuide.get_setup_steps():
            console.print(f"  [cyan]{step['step']}.[/] [bold]{step['title']}[/]")
            console.print(f"     {step['description']}\n")

        # Ask if user wants interactive setup
        response = input("\n是否进行交互式配置? (y/N): ").strip().lower()
        if response == "y":
            config_data = FeishuCalendarPlugin.interactive_setup()

            # Show generated config
            console.print("\n[bold green]生成的配置:[/]\n")
            import yaml

            config_yaml = yaml.dump(
                {"feishu-calendar": {"settings": config_data}},
                allow_unicode=True,
                default_flow_style=False,
            )
            console.print(config_yaml)

            # Ask to save
            save_response = input("\n是否将配置保存到文件? (y/N): ").strip().lower()
            if save_response == "y":
                config_path = Path(args.config)
                if config_path.exists():
                    console.print(f"\n[yellow]请手动将以上配置添加到 {config_path}[/]")
                else:
                    console.print(f"\n[yellow]配置文件不存在: {config_path}[/]")
                    console.print("请先运行 'feishu-webhook-bot init' 创建配置文件")
        else:
            # Show templates
            console.print("\n[bold]配置模板:[/]")
            console.print(CalendarSetupGuide.get_config_template())

            console.print("\n[bold]环境变量模板:[/]")
            console.print(CalendarSetupGuide.get_env_template())

        return 0

    except Exception as e:
        console.print(f"[red]配置向导错误:[/] {e}")
        return 1


def _cmd_calendar_test(args: argparse.Namespace) -> int:
    """Handle calendar connection test."""
    console = Console()
    console.print("\n[bold]测试飞书日历API连接...[/]\n")

    try:
        config_path = Path(args.config)
        plugin = _get_calendar_plugin(config_path)

        if not plugin:
            console.print("[red]无法加载日历插件配置[/]")
            console.print(f"请确保配置文件存在: {config_path}")
            return 1

        # Override credentials if provided
        if args.app_id:
            plugin._app_id = args.app_id
        if args.app_secret:
            plugin._app_secret = args.app_secret

        # Run connection test
        result = plugin.test_connection()

        if result["success"]:
            console.print("[bold green]✓ 连接测试成功![/]\n")
            console.print(f"  App ID: {result.get('app_id', 'N/A')}")
            console.print("  令牌有效: [green]是[/]")
            console.print("  日历访问: [green]是[/]")
            console.print(f"  可用日历数: {result.get('calendar_count', 0)}")

            if result.get("calendars"):
                console.print("\n[bold]可用日历:[/]")
                for cal in result["calendars"]:
                    cal_type = cal.get("type", "unknown")
                    console.print(f"  - {cal.get('name', 'N/A')} ({cal_type})")
                    console.print(f"    ID: {cal.get('id', 'N/A')}")
        else:
            console.print("[bold red]✗ 连接测试失败[/]\n")
            console.print(f"  错误: {result.get('error', '未知错误')}")
            console.print(f"  令牌有效: {'是' if result.get('token_valid') else '否'}")
            console.print(
                f"  日历访问: {'是' if result.get('calendars_accessible') else '否'}"
            )

            # Show guidance
            console.print("\n[yellow]请检查以下配置:[/]")
            console.print("  1. App ID 和 App Secret 是否正确")
            console.print("  2. 应用是否已发布并获得日历权限")
            console.print(
                "  3. 运行 'feishu-webhook-bot calendar permissions' 查看所需权限"
            )

            return 1

        return 0

    except Exception as e:
        console.print(f"[red]测试失败:[/] {e}")
        return 1


def _cmd_calendar_list(args: argparse.Namespace) -> int:
    """Handle calendar list command."""
    console = Console()
    console.print("\n[bold]获取日历列表...[/]\n")

    try:
        config_path = Path(args.config)
        plugin = _get_calendar_plugin(config_path)

        if not plugin:
            console.print("[red]无法加载日历插件[/]")
            return 1

        calendars = plugin.get_calendar_list()

        if not calendars:
            console.print("[yellow]未找到可用日历[/]")
            console.print("请检查应用权限配置")
            return 0

        table = Table(title=f"可用日历 (共 {len(calendars)} 个)")
        table.add_column("日历名称", style="cyan")
        table.add_column("日历ID", style="dim")
        table.add_column("类型", style="magenta")
        table.add_column("角色", style="green")

        role_icons = {"owner": "👑", "writer": "✏️", "reader": "👁️"}

        for cal in calendars:
            role_icon = role_icons.get(cal.role, "📅")
            cal_id = cal.calendar_id
            if len(cal_id) > 20:
                cal_id = cal_id[:20] + "..."
            table.add_row(
                cal.summary or "(无名称)",
                cal_id,
                cal.type or "unknown",
                f"{role_icon} {cal.role}",
            )

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]获取日历列表失败:[/] {e}")
        return 1


def _cmd_calendar_events(args: argparse.Namespace) -> int:
    """Handle calendar events command."""
    console = Console()
    calendar_id = args.calendar_id
    days = args.days

    console.print(f"\n[bold]获取日历 '{calendar_id}' 未来 {days} 天的日程...[/]\n")

    try:
        config_path = Path(args.config)
        plugin = _get_calendar_plugin(config_path)

        if not plugin:
            console.print("[red]无法加载日历插件[/]")
            return 1

        events = plugin.get_events(calendar_id=calendar_id, days_ahead=days)

        if not events:
            console.print("[yellow]未找到日程[/]")
            return 0

        table = Table(title=f"日程列表 (共 {len(events)} 个)")
        table.add_column("时间", style="cyan", width=20)
        table.add_column("标题", style="bold")
        table.add_column("状态", width=8)
        table.add_column("地点/会议", style="dim")

        status_icons = {"confirmed": "✅", "tentative": "⏳", "cancelled": "❌"}

        for event in events:
            time_str = event.get_time_range_str(plugin._timezone)
            status_icon = status_icons.get(event.status.value, "")

            location_info = ""
            if event.location.name:
                location_info = f"📍 {event.location.name}"
            elif event.vchat.meeting_url:
                location_info = "💻 有会议链接"

            table.add_row(
                time_str,
                event.summary or "(无标题)",
                status_icon,
                location_info,
            )

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]获取日程失败:[/] {e}")
        return 1


def _cmd_calendar_today(args: argparse.Namespace) -> int:
    """Handle calendar today command."""
    console = Console()
    calendar_id = args.calendar_id

    console.print(f"\n[bold]获取日历 '{calendar_id}' 今日日程...[/]\n")

    try:
        config_path = Path(args.config)
        plugin = _get_calendar_plugin(config_path)

        if not plugin:
            console.print("[red]无法加载日历插件[/]")
            return 1

        events = plugin.get_today_events(calendar_id=calendar_id)

        if not events:
            console.print("[green]今天没有日程安排，享受美好的一天！[/]")
            return 0

        # Summary stats
        total = len(events)
        meetings = sum(1 for e in events if e.vchat.meeting_url)
        all_day = sum(1 for e in events if e.is_all_day)

        console.print(
            f"[bold]今日统计:[/] 共 {total} 个日程, {meetings} 个会议, {all_day} 个全天日程\n"
        )

        table = Table(title="今日日程")
        table.add_column("时间", style="cyan", width=16)
        table.add_column("标题", style="bold")
        table.add_column("详情", style="dim")

        for event in events:
            if event.is_all_day:
                time_str = "全天"
            elif event.start_time:
                start = event.start_time.astimezone(plugin._timezone)
                if event.end_time:
                    end = event.end_time.astimezone(plugin._timezone)
                    time_str = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
                else:
                    time_str = start.strftime("%H:%M")
            else:
                time_str = "--:--"

            details = []
            if event.location.name:
                details.append(f"📍 {event.location.name}")
            if event.vchat.meeting_url:
                details.append("💻 有会议")
            if event.attendees:
                details.append(f"👥 {len(event.attendees)}人")

            table.add_row(time_str, event.summary or "(无标题)", " | ".join(details))

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]获取今日日程失败:[/] {e}")
        return 1


def _cmd_calendar_status(args: argparse.Namespace) -> int:
    """Handle calendar status command."""
    console = Console()
    console.print("\n[bold]飞书日历插件状态[/]\n")

    try:
        config_path = Path(args.config)
        plugin = _get_calendar_plugin(config_path)

        if not plugin:
            console.print("[red]无法加载日历插件[/]")
            console.print("请运行 'feishu-webhook-bot calendar setup' 进行配置")
            return 1

        status = plugin.get_setup_status()

        configured = status.get("configured", False)
        ready = status.get("ready", False)
        console.print(
            f"配置状态: {'[green]已配置[/]' if configured else '[red]未配置[/]'}"
        )
        console.print(f"就绪状态: {'[green]就绪[/]' if ready else '[yellow]未就绪[/]'}")

        if status.get("missing_config"):
            console.print(
                f"\n[yellow]缺少配置项:[/] {', '.join(status['missing_config'])}"
            )

        if status.get("error"):
            console.print(f"\n[red]错误:[/] {status['error']}")

        if status.get("calendar_count"):
            console.print(f"\n可用日历数: {status['calendar_count']}")

        if status.get("next_steps"):
            console.print("\n[bold]下一步操作:[/]")
            for step in status["next_steps"]:
                console.print(f"  {step['step']}. {step['title']}")
                console.print(f"     {step['description'][:80]}...")

        return 0

    except Exception as e:
        console.print(f"[red]获取状态失败:[/] {e}")
        return 1


def _cmd_calendar_permissions(args: argparse.Namespace) -> int:
    """Handle calendar permissions command."""
    console = Console()

    try:
        from ...plugins.feishu_calendar import CalendarSetupGuide

        console.print("\n[bold cyan]飞书日历插件权限指南[/]\n")
        console.print(CalendarSetupGuide.get_permission_guide())
        return 0

    except Exception as e:
        console.print(f"[red]获取权限指南失败:[/] {e}")
        return 1


def _cmd_calendar_send_summary(args: argparse.Namespace) -> int:
    """Handle calendar send-summary command."""
    console = Console()
    console.print("\n[bold]发送今日日程摘要...[/]\n")

    try:
        config_path = Path(args.config)

        if not config_path.exists():
            console.print(f"[red]配置文件不存在: {config_path}[/]")
            return 1

        config = BotConfig.from_yaml(config_path)

        # Get webhook
        webhook = config.get_webhook(args.webhook) or (
            config.webhooks[0] if config.webhooks else None
        )
        if not webhook:
            console.print("[red]未找到 Webhook 配置[/]")
            return 1

        # Get calendar plugin
        plugin = _get_calendar_plugin(config_path)
        if not plugin:
            console.print("[red]无法加载日历插件[/]")
            return 1

        # Get today's events
        all_events = []
        calendar_ids = plugin._calendar_ids or ["primary"]
        for cal_id in calendar_ids:
            events = plugin.get_today_events(cal_id)
            all_events.extend(events)

        # Sort by start time
        all_events.sort(key=lambda e: e.start_time or datetime.min.replace(tzinfo=UTC))

        # Build summary card
        card = plugin.build_daily_summary_card(all_events)

        # Send via webhook client
        client_cls = FeishuWebhookClient
        if client_cls is None:
            from ...core.client import FeishuWebhookClient as client_cls

        with client_cls(webhook) as client:
            client.send_card(card)

        console.print("[green]✓ 日程摘要已发送![/]")
        console.print(f"  发送到: {args.webhook}")
        console.print(f"  日程数: {len(all_events)}")
        return 0

    except Exception as e:
        console.print(f"[red]发送摘要失败:[/] {e}")
        return 1


__all__ = ["cmd_calendar"]
