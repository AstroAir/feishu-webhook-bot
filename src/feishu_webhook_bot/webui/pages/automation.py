# ruff: noqa: E501
"""Automation page with visual builder and comprehensive management.

This module provides:
- Visual automation rule builder
- Action type configuration forms
- Trigger configuration
- Workflow templates
- Execution history and monitoring
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t

# Action types with their descriptions and required fields
ACTION_TYPES_INFO = {
    "send_text": {
        "label": "发送文本 / Send Text",
        "icon": "chat",
        "description": "发送文本消息到飞书",
        "fields": ["text", "template"],
    },
    "send_template": {
        "label": "发送模板 / Send Template",
        "icon": "description",
        "description": "使用预定义模板发送消息",
        "fields": ["template"],
    },
    "http_request": {
        "label": "HTTP请求 / HTTP Request",
        "icon": "http",
        "description": "发送HTTP请求到外部API",
        "fields": ["method", "url", "headers", "body"],
    },
    "plugin_method": {
        "label": "插件方法 / Plugin Method",
        "icon": "extension",
        "description": "调用已安装插件的方法",
        "fields": ["plugin_name", "method_name", "parameters"],
    },
    "python_code": {
        "label": "Python代码 / Python Code",
        "icon": "code",
        "description": "执行自定义Python代码",
        "fields": ["code"],
    },
    "ai_chat": {
        "label": "AI对话 / AI Chat",
        "icon": "smart_toy",
        "description": "使用AI进行对话",
        "fields": ["prompt", "ai_user_id"],
    },
    "ai_query": {
        "label": "AI查询 / AI Query",
        "icon": "psychology",
        "description": "执行AI查询并获取结果",
        "fields": ["query", "save_as"],
    },
    "conditional": {
        "label": "条件分支 / Conditional",
        "icon": "call_split",
        "description": "根据条件执行不同动作",
        "fields": ["condition", "then_actions", "else_actions"],
    },
    "loop": {
        "label": "循环 / Loop",
        "icon": "loop",
        "description": "循环执行动作",
        "fields": ["items", "actions", "max_iterations"],
    },
    "set_variable": {
        "label": "设置变量 / Set Variable",
        "icon": "data_object",
        "description": "设置上下文变量",
        "fields": ["name", "value", "expression"],
    },
    "delay": {
        "label": "延迟 / Delay",
        "icon": "schedule",
        "description": "等待指定时间",
        "fields": ["seconds", "milliseconds"],
    },
    "notify": {
        "label": "通知 / Notify",
        "icon": "notifications",
        "description": "发送通知消息",
        "fields": ["channel", "message", "level"],
    },
    "log": {
        "label": "日志 / Log",
        "icon": "article",
        "description": "记录日志信息",
        "fields": ["message", "level"],
    },
    "parallel": {
        "label": "并行执行 / Parallel",
        "icon": "call_split",
        "description": "并行执行多个动作",
        "fields": ["actions", "max_concurrent"],
    },
    "chain_rule": {
        "label": "链式规则 / Chain Rule",
        "icon": "link",
        "description": "触发另一个自动化规则",
        "fields": ["rule_name", "pass_context"],
    },
}

TRIGGER_TYPES_INFO = {
    "schedule": {
        "label": "定时触发 / Schedule",
        "icon": "schedule",
        "description": "按时间间隔或cron表达式触发",
    },
    "event": {
        "label": "事件触发 / Event",
        "icon": "bolt",
        "description": "监听飞书事件触发",
    },
    "webhook": {
        "label": "Webhook触发 / Webhook",
        "icon": "webhook",
        "description": "通过HTTP请求触发",
    },
    "manual": {
        "label": "手动触发 / Manual",
        "icon": "touch_app",
        "description": "手动执行触发",
    },
    "chain": {
        "label": "链式触发 / Chain",
        "icon": "link",
        "description": "由其他规则触发",
    },
}

# Common event types
COMMON_EVENT_TYPES = [
    "im.message.receive_v1",
    "im.message.message_read_v1",
    "im.chat.member.user.added_v1",
    "im.chat.member.user.deleted_v1",
    "contact.user.created_v3",
    "calendar.event.changed_v4",
]


def build_automation_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the Automation page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("automation.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("automation.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    rules = controller.get_automation_rules()

    # Stats cards
    with ui.element("div").classes(
        "grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Total rules
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(rules))).classes("text-xl sm:text-2xl font-bold text-blue-600")
                ui.label(t("automation.total_rules")).classes(
                    "text-xs sm:text-sm text-blue-700 text-center"
                )

        # Active rules
        active_count = len([r for r in rules if r.get("enabled", True)])
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(active_count)).classes("text-xl sm:text-2xl font-bold text-green-600")
                ui.label(t("automation.active")).classes(
                    "text-xs sm:text-sm text-green-700 text-center"
                )

        # Ready rules
        ready_count = len([r for r in rules if r.get("status") == "Ready"])
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(ready_count)).classes("text-xl sm:text-2xl font-bold text-purple-600")
                ui.label(t("automation.ready")).classes(
                    "text-xs sm:text-sm text-purple-700 text-center"
                )

        # Bot status
        bot_running = controller.running
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("check_circle" if bot_running else "cancel", size="md").classes(
                    f"text-{'green' if bot_running else 'gray'}-600"
                )
                ui.label(t("automation.bot_status")).classes(
                    "text-xs sm:text-sm text-orange-700 text-center"
                )

    # Active rules status section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("automation.active_rules")).classes(
            "text-lg sm:text-xl font-semibold text-gray-800"
        )
        ui.label(t("automation.active_rules_desc")).classes(
            "text-sm sm:text-base text-gray-500 mt-1"
        )

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
            ui.label(t("automation.registered_rules")).classes(
                "text-base sm:text-lg font-semibold text-gray-800"
            )
            with ui.row().classes("gap-2"):
                ui.button(
                    icon="add",
                    on_click=lambda: _show_create_rule_dialog(controller, rebuild_automations),
                ).props("flat round dense color=primary").tooltip(t("automation.add_rule"))
                ui.button(icon="refresh", on_click=lambda: rebuild_automations()).props(
                    "flat round dense"
                )
        auto_container = ui.column().classes("gap-2 w-full")

        def rebuild_automations() -> None:
            auto_container.clear()
            with auto_container:
                current_rules = controller.get_automation_rules()
                if not current_rules:
                    with ui.column().classes("items-center py-8"):
                        ui.icon("auto_fix_high", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("automation.no_active_rules")).classes("text-gray-400")
                    return

                for rule in current_rules:
                    _build_automation_card(controller, rule, rebuild_automations)

        rebuild_automations()

    # Execution history section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("automation.history")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("automation.history_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
            ui.label(t("automation.recent_executions")).classes(
                "text-base sm:text-lg font-semibold text-gray-800"
            )
            ui.button(icon="refresh", on_click=lambda: rebuild_history()).props("flat round dense")

        history_container = ui.column().classes("gap-2 w-full")

        def rebuild_history() -> None:
            history_container.clear()
            with history_container:
                history = controller.get_automation_history(limit=10)
                if not history:
                    with ui.column().classes("items-center py-6"):
                        ui.icon("history", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("automation.no_history")).classes("text-gray-400")
                    return

                for entry in history:
                    status_color = "green" if entry.get("success") else "red"
                    status_icon = "check_circle" if entry.get("success") else "error"
                    with ui.row().classes(
                        "w-full items-center justify-between p-3 bg-gray-50 rounded-lg"
                    ):
                        with ui.row().classes("items-center gap-3"):
                            ui.icon(status_icon, size="sm").classes(f"text-{status_color}-500")
                            with ui.column().classes("gap-0"):
                                ui.label(entry.get("rule_name", "Unknown")).classes(
                                    "font-medium text-gray-800"
                                )
                                ui.label(entry.get("triggered_at", "N/A")).classes(
                                    "text-xs text-gray-500"
                                )
                        with ui.row().classes("items-center gap-2"):
                            duration = entry.get("duration", 0)
                            ui.label(f"{duration:.2f}s").classes("text-sm text-gray-600")
                            actions = entry.get("actions_executed", 0)
                            ui.chip(f"{actions} actions", color="blue").props("dense")
                            if entry.get("error"):
                                ui.icon("warning", size="sm").classes("text-orange-500").tooltip(
                                    entry.get("error")
                                )

        rebuild_history()

    # Automation configuration section (if state available for editing)
    if state is not None:
        automation_cfg = state["form"].setdefault("automation", {})

        with ui.column().classes("w-full mb-3 sm:mb-4"):
            ui.label(t("automation.configuration")).classes(
                "text-lg sm:text-xl font-semibold text-gray-800"
            )
            ui.label(t("automation.configuration_desc")).classes(
                "text-sm sm:text-base text-gray-500 mt-1"
            )

        with ui.element("div").classes(
            "grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6 w-full"
        ):
            # Basic settings
            with ui.card().classes(
                "p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"
            ):
                ui.label(t("automation.basic_settings")).classes(
                    "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
                )
                with ui.column().classes("gap-4 w-full"):
                    ui.switch(t("automation.enabled")).bind_value(automation_cfg, "enabled")
                    ui.number(t("automation.max_concurrent"), min=1, max=100).bind_value(
                        automation_cfg, "max_concurrent"
                    ).props("outlined").classes("w-full")
                    ui.number(t("automation.timeout"), min=1, max=3600).bind_value(
                        automation_cfg, "timeout_seconds"
                    ).props("outlined").classes("w-full")

            # Error handling
            with ui.card().classes(
                "p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"
            ):
                ui.label(t("automation.error_handling")).classes(
                    "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
                )
                with ui.column().classes("gap-4 w-full"):
                    ui.switch(t("automation.retry_on_error")).bind_value(
                        automation_cfg, "retry_on_error"
                    )
                    ui.number(t("automation.max_retries"), min=0, max=10).bind_value(
                        automation_cfg, "max_retries"
                    ).props("outlined").classes("w-full")
                    ui.number(t("automation.retry_delay"), min=0, max=300).bind_value(
                        automation_cfg, "retry_delay_seconds"
                    ).props("outlined").classes("w-full")

        # Rules configuration
        with ui.column().classes("w-full mb-3 sm:mb-4"):
            ui.label(t("automation.rules_config")).classes(
                "text-lg sm:text-xl font-semibold text-gray-800"
            )
            ui.label(t("automation.rules_config_desc")).classes(
                "text-sm sm:text-base text-gray-500 mt-1"
            )

        with ui.card().classes(
            "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
        ):
            rules_list = automation_cfg.setdefault("rules", [])
            rules_container = ui.column().classes("gap-3 w-full")

            def rebuild_rules() -> None:
                rules_container.clear()
                with rules_container:
                    if not rules_list:
                        with ui.column().classes("items-center py-8"):
                            ui.icon("auto_fix_high", size="xl").classes("text-gray-300 mb-2")
                            ui.label(t("automation.no_rules")).classes("text-gray-400")
                    else:
                        for idx, rule in enumerate(rules_list):
                            with (
                                ui.card().classes(
                                    "w-full p-4 bg-gray-50 border border-gray-100 rounded-lg"
                                ),
                                ui.row().classes("items-start justify-between gap-4"),
                            ):
                                with ui.column().classes("gap-3 flex-grow"):
                                    with ui.row().classes("gap-3 w-full"):
                                        ui.input(t("automation.rule_name")).bind_value(
                                            rule, "name"
                                        ).props("outlined dense").classes("flex-1")
                                        ui.switch(t("automation.rule_enabled")).bind_value(
                                            rule, "enabled"
                                        )
                                    ui.input(t("automation.trigger_event")).bind_value(
                                        rule, "trigger"
                                    ).props("outlined dense").classes("w-full").tooltip(
                                        t("automation.trigger_event_hint")
                                    )
                                    ui.textarea(t("automation.conditions")).bind_value(
                                        rule, "conditions"
                                    ).props("outlined dense auto-grow rows=2").classes(
                                        "w-full"
                                    ).tooltip(t("automation.conditions_hint"))
                                    ui.textarea(t("automation.actions")).bind_value(
                                        rule, "actions"
                                    ).props("outlined dense auto-grow rows=2").classes(
                                        "w-full"
                                    ).tooltip(t("automation.actions_hint"))

                                def remove_rule(i: int = idx) -> None:
                                    rules_list.pop(i)
                                    rebuild_rules()

                                ui.button(icon="delete", on_click=remove_rule).props(
                                    "flat round color=red"
                                )

            rebuild_rules()

            def add_rule() -> None:
                rules_list.append(
                    {
                        "name": "",
                        "enabled": True,
                        "trigger": "",
                        "conditions": "",
                        "actions": "",
                    }
                )
                rebuild_rules()

            ui.button(t("automation.add_rule"), on_click=add_rule, icon="add").props(
                "outline color=primary"
            ).classes("mt-3")


def _build_automation_card(
    controller: BotController, rule: dict[str, Any], refresh_callback: Any
) -> None:
    """Build a single automation rule card with full controls."""
    rule_name = rule["name"]
    is_enabled = rule.get("enabled", True)

    with ui.card().classes(
        "w-full p-3 sm:p-4 bg-gray-50 border border-gray-100 rounded-lg hover:bg-gray-100 transition-colors"
    ):
        with ui.row().classes("w-full items-start justify-between flex-wrap gap-2"):
            # Rule info
            with ui.column().classes("gap-1 flex-grow min-w-0"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(rule_name).classes("font-semibold text-gray-800 truncate")
                    if is_enabled:
                        ui.chip(t("automation.active"), color="green").props("dense")
                    else:
                        ui.chip(t("tasks.disabled"), color="grey").props("dense")
                trigger_type = rule.get("trigger", "N/A")
                if hasattr(trigger_type, "type"):
                    trigger_type = trigger_type.type
                ui.label(f"Trigger: {trigger_type}").classes("text-xs sm:text-sm text-gray-500")

            # Rule controls
            with ui.row().classes("items-center gap-2 sm:gap-4 flex-wrap"):
                # Status info
                status = rule.get("status", "Ready")
                status_color = "green" if status in ("active", "Ready") else "gray"
                ui.chip(status, color=status_color).props("dense")

                # Action buttons
                with ui.row().classes("gap-1"):
                    # Trigger button
                    def on_trigger(rn: str = rule_name) -> None:
                        try:
                            result = controller.trigger_automation(rn)
                            if result.get("success"):
                                ui.notify(f"{rn} {t('common.success')}", type="positive")
                            else:
                                ui.notify(
                                    f"{t('common.error')}: {result.get('error', 'Unknown')}",
                                    type="negative",
                                )
                        except Exception as e:
                            ui.notify(f"{t('common.error')}: {e}", type="negative")

                    ui.button(icon="play_arrow", on_click=on_trigger).props(
                        "dense flat color=primary"
                    ).tooltip(t("automation.trigger"))

                    # Enable/Disable toggle
                    def on_toggle(rn: str = rule_name, enabled: bool = is_enabled) -> None:
                        try:
                            if enabled:
                                success = controller.disable_automation(rn)
                                msg = t("automation.rule_disabled")
                            else:
                                success = controller.enable_automation(rn)
                                msg = t("automation.rule_enabled_msg")
                            if success:
                                ui.notify(f"{rn} {msg}", type="positive")
                                refresh_callback()
                            else:
                                ui.notify(t("common.error"), type="negative")
                        except Exception as e:
                            ui.notify(f"{t('common.error')}: {e}", type="negative")

                    toggle_icon = "toggle_on" if is_enabled else "toggle_off"
                    toggle_color = "green" if is_enabled else "grey"
                    ui.button(icon=toggle_icon, on_click=on_toggle).props(
                        f"dense flat color={toggle_color}"
                    ).tooltip(t("automation.toggle_enabled"))

                    # Edit button
                    def edit_rule(rn: str = rule_name) -> None:
                        details = controller.get_automation_details(rn)
                        if "error" in details:
                            ui.notify(details["error"], type="negative")
                            return
                        _show_edit_rule_dialog(controller, details, refresh_callback)

                    ui.button(icon="edit", on_click=edit_rule).props(
                        "dense flat color=orange"
                    ).tooltip(t("automation.edit_rule"))

                    # Test button
                    def test_rule(rn: str = rule_name) -> None:
                        _show_test_rule_dialog(controller, rn)

                    ui.button(icon="science", on_click=test_rule).props(
                        "dense flat color=purple"
                    ).tooltip(t("automation.test_rule"))

                    # Details button
                    def show_details(rn: str = rule_name) -> None:
                        details = controller.get_automation_details(rn)
                        if "error" in details:
                            ui.notify(details["error"], type="negative")
                            return
                        _show_automation_details_dialog(controller, details, refresh_callback)

                    ui.button(icon="info", on_click=show_details).props(
                        "dense flat color=blue"
                    ).tooltip(t("automation.details"))

                    # Delete button
                    def delete_rule(rn: str = rule_name) -> None:
                        _show_delete_rule_dialog(controller, rn, refresh_callback)

                    ui.button(icon="delete", on_click=delete_rule).props(
                        "dense flat color=red"
                    ).tooltip(t("automation.delete_rule"))


def _show_automation_details_dialog(
    controller: BotController, details: dict[str, Any], refresh_callback: Any
) -> None:
    """Show automation rule details in a dialog."""
    with (
        ui.dialog() as dialog,
        ui.card().classes("w-full max-w-2xl p-6 max-h-screen overflow-y-auto"),
    ):
        ui.label(f"{t('automation.details')}: {details.get('name', 'Unknown')}").classes(
            "text-xl font-bold mb-4"
        )

        with ui.tabs().classes("w-full") as tabs:
            tab_info = ui.tab("info", label=t("common.info"))
            tab_actions = ui.tab("actions", label=t("automation.actions"))
            tab_history = ui.tab("history", label=t("automation.history"))
            tab_logs = ui.tab("logs", label=t("automation.logs"))

        with ui.tab_panels(tabs, value=tab_info).classes("w-full"):
            # Info tab
            with ui.tab_panel(tab_info), ui.column().classes("gap-3 w-full"):
                # Basic info
                with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-4"):
                    with ui.column().classes("gap-1"):
                        ui.label(t("tasks.status")).classes("text-xs text-gray-500")
                        status = "Enabled" if details.get("enabled") else "Disabled"
                        color = "green" if details.get("enabled") else "red"
                        ui.chip(status, color=color).props("dense")
                    with ui.column().classes("gap-1"):
                        ui.label(t("automation.trigger_type")).classes("text-xs text-gray-500")
                        ui.chip(details.get("trigger_type", "N/A"), color="purple").props(
                            "dense outline"
                        )
                    with ui.column().classes("gap-1"):
                        ui.label(t("automation.actions_count")).classes("text-xs text-gray-500")
                        ui.label(str(details.get("actions_count", 0))).classes("font-medium")
                    with ui.column().classes("gap-1"):
                        ui.label(t("automation.default_webhooks")).classes("text-xs text-gray-500")
                        webhooks = details.get("default_webhooks", [])
                        ui.label(", ".join(webhooks) if webhooks else "default").classes(
                            "font-medium text-sm"
                        )

                # Description
                desc = details.get("description", "")
                if desc:
                    ui.separator()
                    ui.label(t("tasks.description")).classes("text-xs text-gray-500")
                    ui.label(desc).classes("text-sm text-gray-700")

                # Schedule info (if applicable)
                next_run = details.get("next_run")
                if next_run:
                    ui.separator()
                    with ui.column().classes("gap-1"):
                        ui.label(t("tasks.next_run")).classes("text-xs text-gray-500")
                        ui.label(next_run).classes("font-medium")

            # Actions tab
            with ui.tab_panel(tab_actions):
                actions = details.get("actions", [])
                if not actions:
                    ui.label("No actions configured").classes("text-gray-400 py-4")
                else:
                    for i, action in enumerate(actions, 1):
                        with ui.card().classes("w-full p-3 bg-gray-50 rounded-lg mb-2"):
                            with ui.row().classes("items-center gap-2 mb-2"):
                                ui.chip(f"#{i}", color="blue").props("dense")
                                ui.chip(action.get("type", "unknown"), color="purple").props(
                                    "dense outline"
                                )
                            if action.get("type") == "send_text":
                                text = action.get("text", "")
                                if text:
                                    ui.label(f"Text: {text[:50]}...").classes(
                                        "text-sm text-gray-600"
                                    )
                            elif action.get("type") == "send_template":
                                ui.label(f"Template: {action.get('template', 'N/A')}").classes(
                                    "text-sm"
                                )
                            elif action.get("type") == "http_request":
                                ui.label(f"URL: {action.get('url', 'N/A')}").classes(
                                    "text-sm text-gray-600"
                                )
                            elif action.get("type") == "plugin_method":
                                ui.label(f"Plugin: {action.get('plugin_name', 'N/A')}").classes(
                                    "text-sm"
                                )
                                ui.label(f"Method: {action.get('method_name', 'N/A')}").classes(
                                    "text-sm text-gray-600"
                                )

            # History tab
            with ui.tab_panel(tab_history):
                recent = details.get("recent_executions", [])
                if not recent:
                    ui.label("No execution history").classes("text-gray-400 py-4")
                else:
                    for entry in recent[:10]:
                        status_icon = "check_circle" if entry.get("success") else "error"
                        status_color = "green" if entry.get("success") else "red"
                        with ui.row().classes(
                            "w-full items-center justify-between p-2 bg-gray-50 rounded mb-1"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon(status_icon, size="sm").classes(f"text-{status_color}-500")
                                ui.label(entry.get("triggered_at", "N/A")).classes("text-sm")
                            with ui.row().classes("items-center gap-2"):
                                ui.label(f"{entry.get('duration', 0):.2f}s").classes(
                                    "text-sm text-gray-600"
                                )
                                if entry.get("error"):
                                    ui.icon("warning", size="xs").classes(
                                        "text-orange-500"
                                    ).tooltip(entry.get("error"))

            # Logs tab
            with ui.tab_panel(tab_logs):
                logs = details.get("logs", [])
                if not logs:
                    ui.label(t("automation.no_logs")).classes("text-gray-400 py-4")
                else:
                    with ui.column().classes("w-full gap-1 max-h-64 overflow-y-auto"):
                        for log_entry in logs[-50:]:  # Show last 50 logs
                            level = log_entry.get("level", "info")
                            level_colors = {
                                "debug": "gray",
                                "info": "blue",
                                "warning": "orange",
                                "error": "red",
                            }
                            color = level_colors.get(level, "gray")
                            with ui.row().classes(
                                "w-full items-start gap-2 p-1 hover:bg-gray-50 rounded"
                            ):
                                ui.chip(level.upper(), color=color).props("dense size=sm")
                                ui.label(log_entry.get("timestamp", "")).classes(
                                    "text-xs text-gray-400 w-32"
                                )
                                ui.label(log_entry.get("message", "")).classes(
                                    "text-sm text-gray-700 flex-grow"
                                )

        with ui.row().classes("justify-end mt-4 gap-2"):
            # Trigger button in dialog
            def trigger_from_dialog() -> None:
                result = controller.trigger_automation(details.get("name", ""))
                if result.get("success"):
                    ui.notify(t("automation.triggered"), type="positive")
                else:
                    ui.notify(
                        f"{t('common.error')}: {result.get('error', 'Unknown')}", type="negative"
                    )

            ui.button(
                t("automation.trigger"), icon="play_arrow", on_click=trigger_from_dialog
            ).props("outline color=primary")
            ui.button(t("common.close"), on_click=dialog.close).props("flat")

    dialog.open()


def _show_create_rule_dialog(controller: BotController, refresh_callback: Any) -> None:
    """Show dialog to create a new automation rule."""
    rule_data: dict[str, Any] = {
        "name": "",
        "description": "",
        "enabled": True,
        "trigger_type": "schedule",
        "trigger_config": {},
        "actions": [],
    }

    with (
        ui.dialog() as dialog,
        ui.card().classes("w-full max-w-3xl p-6 max-h-screen overflow-y-auto"),
    ):
        ui.label(t("automation.create_rule")).classes("text-xl font-bold mb-4")

        with ui.stepper().props("vertical").classes("w-full") as stepper:
            # Step 1: Basic Info
            with ui.step(t("automation.basic_info")):
                with ui.column().classes("gap-4 w-full"):
                    ui.input(
                        t("automation.rule_name"), placeholder="my_automation_rule"
                    ).bind_value(rule_data, "name").props("outlined").classes("w-full")
                    ui.textarea(
                        t("automation.description"),
                        placeholder=t("automation.description_placeholder"),
                    ).bind_value(rule_data, "description").props(
                        "outlined auto-grow rows=2"
                    ).classes("w-full")
                    ui.switch(t("automation.enabled")).bind_value(rule_data, "enabled")

                with ui.stepper_navigation():
                    ui.button(t("common.next"), on_click=stepper.next).props("color=primary")

            # Step 2: Trigger Configuration
            with ui.step(t("automation.trigger_config")):
                with ui.column().classes("gap-4 w-full"):
                    # Trigger type selection - use dict format {value: label}
                    trigger_options = {
                        ttype: info["label"] for ttype, info in TRIGGER_TYPES_INFO.items()
                    }
                    ui.select(
                        label=t("automation.trigger_type"),
                        options=trigger_options,
                        value="schedule",
                    ).bind_value(rule_data, "trigger_type").props("outlined").classes("w-full")

                    # Dynamic trigger config based on type
                    trigger_config_container = ui.column().classes("gap-3 w-full")

                    def update_trigger_config() -> None:
                        trigger_config_container.clear()
                        with trigger_config_container:
                            ttype = rule_data.get("trigger_type", "schedule")
                            if ttype == "schedule":
                                ui.select(
                                    label=t("automation.schedule_mode"),
                                    options=["interval", "cron"],
                                    value="interval",
                                ).bind_value(rule_data["trigger_config"], "mode").props(
                                    "outlined"
                                ).classes("w-full")
                                ui.number(
                                    t("automation.interval_minutes"), min=1, value=60
                                ).bind_value(rule_data["trigger_config"], "minutes").props(
                                    "outlined"
                                ).classes("w-full")
                            elif ttype == "event":
                                ui.input(
                                    t("automation.event_type"), placeholder="im.message.receive_v1"
                                ).bind_value(rule_data["trigger_config"], "event_type").props(
                                    "outlined"
                                ).classes("w-full")
                            elif ttype == "webhook":
                                ui.input(
                                    t("automation.webhook_path"),
                                    placeholder="/automation/my_webhook",
                                ).bind_value(rule_data["trigger_config"], "path").props(
                                    "outlined"
                                ).classes("w-full")
                            elif ttype == "manual":
                                ui.label(t("automation.manual_trigger_hint")).classes(
                                    "text-sm text-gray-500"
                                )

                    update_trigger_config()

                with ui.stepper_navigation():
                    ui.button(t("common.back"), on_click=stepper.previous).props("flat")
                    ui.button(t("common.next"), on_click=stepper.next).props("color=primary")

            # Step 3: Actions
            with ui.step(t("automation.actions")):
                actions_container = ui.column().classes("gap-3 w-full")

                def rebuild_actions() -> None:
                    actions_container.clear()
                    with actions_container:
                        if not rule_data["actions"]:
                            ui.label(t("automation.no_actions")).classes("text-gray-400 py-4")
                        else:
                            for idx, action in enumerate(rule_data["actions"]):
                                _build_action_editor(
                                    action, idx, rule_data["actions"], rebuild_actions
                                )

                rebuild_actions()

                def add_action() -> None:
                    rule_data["actions"].append(
                        {
                            "type": "send_text",
                            "text": "",
                        }
                    )
                    rebuild_actions()

                ui.button(t("automation.add_action"), icon="add", on_click=add_action).props(
                    "outline color=primary"
                ).classes("mt-2")

                with ui.stepper_navigation():
                    ui.button(t("common.back"), on_click=stepper.previous).props("flat")
                    ui.button(t("common.next"), on_click=stepper.next).props("color=primary")

            # Step 4: Review & Create
            with ui.step(t("automation.review")):
                with ui.column().classes("gap-3 w-full"):
                    ui.label(t("automation.review_hint")).classes("text-sm text-gray-500 mb-2")

                    # Summary labels bound to rule_data
                    name_label = ui.label().classes("font-medium")
                    trigger_label = ui.label().classes("text-sm text-gray-600")
                    actions_label = ui.label().classes("text-sm text-gray-600")

                    # Update labels with timer to catch latest values
                    def refresh_summary() -> None:
                        name_label.text = (
                            f"{t('automation.rule_name')}: {rule_data.get('name', 'N/A')}"
                        )
                        trigger_label.text = f"{t('automation.trigger_type')}: {rule_data.get('trigger_type', 'N/A')}"
                        actions_label.text = (
                            f"{t('automation.actions')}: {len(rule_data.get('actions', []))}"
                        )

                    ui.timer(0.5, refresh_summary, once=False)

                with ui.stepper_navigation():
                    ui.button(t("common.back"), on_click=stepper.previous).props("flat")

                    def create_rule() -> None:
                        if not rule_data.get("name"):
                            ui.notify(t("automation.name_required"), type="warning")
                            return
                        if not rule_data.get("actions"):
                            ui.notify(t("automation.actions_required"), type="warning")
                            return

                        try:
                            success = controller.create_automation_rule(rule_data)
                            if success:
                                ui.notify(t("automation.rule_created"), type="positive")
                                dialog.close()
                                refresh_callback()
                            else:
                                ui.notify(t("common.error"), type="negative")
                        except Exception as e:
                            ui.notify(f"{t('common.error')}: {e}", type="negative")

                    ui.button(
                        t("automation.create_rule"), icon="check", on_click=create_rule
                    ).props("color=primary")

        with ui.row().classes("justify-end mt-4"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

    dialog.open()


def _build_action_editor(
    action: dict[str, Any], idx: int, actions_list: list, rebuild_callback: Any
) -> None:
    """Build an action editor card."""
    with ui.card().classes("w-full p-4 bg-gray-50 border border-gray-200 rounded-lg"):
        with ui.row().classes("w-full items-start justify-between gap-4"):
            with ui.column().classes("gap-3 flex-grow"):
                # Action type selector - use dict format {value: label}
                action_options = {atype: info["label"] for atype, info in ACTION_TYPES_INFO.items()}
                type_select = (
                    ui.select(
                        label=t("automation.action_type"),
                        options=action_options,
                        value=action.get("type", "send_text"),
                    )
                    .props("outlined dense")
                    .classes("w-full")
                )

                # Dynamic fields based on action type
                fields_container = ui.column().classes("gap-2 w-full")

                def update_fields() -> None:
                    action["type"] = type_select.value
                    fields_container.clear()
                    with fields_container:
                        atype = action.get("type", "send_text")

                        if atype == "send_text":
                            ui.textarea(
                                t("automation.text"), placeholder=t("automation.text_placeholder")
                            ).bind_value(action, "text").props(
                                "outlined dense auto-grow rows=2"
                            ).classes("w-full")
                        elif atype == "send_template":
                            ui.input(t("automation.template_name")).bind_value(
                                action, "template"
                            ).props("outlined dense").classes("w-full")
                        elif atype == "http_request":
                            with ui.row().classes("gap-2 w-full"):
                                ui.select(
                                    label=t("automation.method"),
                                    options=["GET", "POST", "PUT", "DELETE"],
                                ).bind_value(action, "method").props("outlined dense").classes(
                                    "w-32"
                                )
                                ui.input(t("automation.url")).bind_value(action, "url").props(
                                    "outlined dense"
                                ).classes("flex-grow")
                        elif atype == "plugin_method":
                            ui.input(t("automation.plugin_name")).bind_value(
                                action, "plugin_name"
                            ).props("outlined dense").classes("w-full")
                            ui.input(t("automation.method_name")).bind_value(
                                action, "method_name"
                            ).props("outlined dense").classes("w-full")
                        elif atype == "python_code":
                            ui.textarea(
                                t("automation.code"), placeholder="result = 'Hello World'"
                            ).bind_value(action, "code").props(
                                "outlined dense auto-grow rows=3"
                            ).classes("w-full font-mono")
                        elif atype == "ai_chat":
                            ui.textarea(t("automation.prompt")).bind_value(action, "prompt").props(
                                "outlined dense auto-grow rows=2"
                            ).classes("w-full")
                        elif atype == "delay":
                            ui.number(t("automation.delay_seconds"), min=0, step=0.1).bind_value(
                                action, "delay_seconds"
                            ).props("outlined dense").classes("w-full")
                        elif atype == "log":
                            ui.input(t("automation.message")).bind_value(action, "message").props(
                                "outlined dense"
                            ).classes("w-full")
                            ui.select(
                                label=t("automation.log_level"),
                                options=["debug", "info", "warning", "error"],
                            ).bind_value(action, "level").props("outlined dense").classes("w-full")
                        elif atype == "set_variable":
                            ui.input(t("automation.variable_name")).bind_value(
                                action, "variable_name"
                            ).props("outlined dense").classes("w-full")
                            ui.input(t("automation.variable_value")).bind_value(
                                action, "variable_value"
                            ).props("outlined dense").classes("w-full")
                        elif atype == "notify":
                            ui.input(t("automation.message")).bind_value(action, "message").props(
                                "outlined dense"
                            ).classes("w-full")
                            ui.select(
                                label=t("automation.channel"), options=["webhook", "log"]
                            ).bind_value(action, "channel").props("outlined dense").classes(
                                "w-full"
                            )
                        elif atype == "chain_rule":
                            ui.input(t("automation.chain_rule_name")).bind_value(
                                action, "rule_name"
                            ).props("outlined dense").classes("w-full")
                        elif atype == "ai_query":
                            ui.textarea(t("automation.query")).bind_value(action, "query").props(
                                "outlined dense auto-grow rows=2"
                            ).classes("w-full")
                            ui.input(t("automation.save_as")).bind_value(action, "save_as").props(
                                "outlined dense"
                            ).classes("w-full")
                        elif atype == "conditional":
                            ui.input(t("automation.condition")).bind_value(
                                action, "condition"
                            ).props("outlined dense").classes("w-full")
                            ui.label(t("automation.then_actions_hint")).classes(
                                "text-xs text-gray-500 mt-2"
                            )
                        elif atype == "loop":
                            ui.input(t("automation.loop_items")).bind_value(action, "items").props(
                                "outlined dense"
                            ).classes("w-full")
                            ui.number(
                                t("automation.max_iterations"), min=1, max=1000, value=100
                            ).bind_value(action, "max_iterations").props("outlined dense").classes(
                                "w-full"
                            )
                        elif atype == "parallel":
                            ui.number(
                                t("automation.max_concurrent"), min=1, max=10, value=5
                            ).bind_value(action, "max_concurrent").props("outlined dense").classes(
                                "w-full"
                            )

                type_select.on_value_change(lambda _: update_fields())
                update_fields()

            # Remove button
            def remove_action(i: int = idx) -> None:
                actions_list.pop(i)
                rebuild_callback()

            ui.button(icon="delete", on_click=remove_action).props("flat round color=red dense")


def _show_edit_rule_dialog(
    controller: BotController, details: dict[str, Any], refresh_callback: Any
) -> None:
    """Show dialog to edit an existing automation rule."""
    rule_name = details.get("name", "")
    rule_data: dict[str, Any] = {
        "name": rule_name,
        "description": details.get("description", ""),
        "enabled": details.get("enabled", True),
        "default_webhooks": details.get("default_webhooks", []),
    }

    with (
        ui.dialog() as dialog,
        ui.card().classes("w-full max-w-2xl p-6 max-h-screen overflow-y-auto"),
    ):
        ui.label(f"{t('automation.edit_rule')}: {rule_name}").classes("text-xl font-bold mb-4")

        with ui.column().classes("gap-4 w-full"):
            # Basic settings
            ui.label(t("automation.basic_settings")).classes("text-lg font-semibold text-gray-700")

            ui.textarea(
                t("automation.description"), placeholder=t("automation.description_placeholder")
            ).bind_value(rule_data, "description").props("outlined auto-grow rows=2").classes(
                "w-full"
            )

            ui.switch(t("automation.enabled")).bind_value(rule_data, "enabled")

            # Default webhooks
            ui.label(t("automation.default_webhooks")).classes(
                "text-lg font-semibold text-gray-700 mt-4"
            )
            webhooks_input = (
                ui.input(t("automation.webhooks_comma_separated"), placeholder="webhook1, webhook2")
                .props("outlined")
                .classes("w-full")
            )
            webhooks_input.value = ", ".join(rule_data.get("default_webhooks", []))

            def update_webhooks() -> None:
                rule_data["default_webhooks"] = [
                    w.strip() for w in webhooks_input.value.split(",") if w.strip()
                ]

            webhooks_input.on("blur", update_webhooks)

        with ui.row().classes("justify-end mt-6 gap-2"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

            def save_changes() -> None:
                try:
                    success = controller.update_automation_config(rule_name, rule_data)
                    if success:
                        ui.notify(t("automation.rule_updated"), type="positive")
                        dialog.close()
                        refresh_callback()
                    else:
                        ui.notify(t("common.error"), type="negative")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("common.save"), icon="save", on_click=save_changes).props("color=primary")

    dialog.open()


def _show_test_rule_dialog(controller: BotController, rule_name: str) -> None:
    """Show dialog to test an automation rule."""
    test_params: dict[str, Any] = {
        "dry_run": True,
        "context": "{}",
    }
    test_result: dict[str, Any] = {}

    with (
        ui.dialog() as dialog,
        ui.card().classes("w-full max-w-2xl p-6 max-h-screen overflow-y-auto"),
    ):
        ui.label(f"{t('automation.test_rule')}: {rule_name}").classes("text-xl font-bold mb-4")

        with ui.column().classes("gap-4 w-full"):
            # Test options
            ui.label(t("automation.test_options")).classes("text-lg font-semibold text-gray-700")

            ui.switch(t("automation.dry_run")).bind_value(test_params, "dry_run").tooltip(
                t("automation.dry_run_hint")
            )

            ui.textarea(t("automation.test_context"), placeholder='{"key": "value"}').bind_value(
                test_params, "context"
            ).props("outlined auto-grow rows=3").classes("w-full font-mono")

            # Results section
            ui.label(t("automation.test_results")).classes(
                "text-lg font-semibold text-gray-700 mt-4"
            )
            results_container = ui.column().classes("w-full gap-2")

            def show_results() -> None:
                results_container.clear()
                with results_container:
                    if not test_result:
                        ui.label(t("automation.no_test_results")).classes("text-gray-400 py-4")
                    else:
                        success = test_result.get("success", False)
                        with ui.card().classes(
                            f"w-full p-4 {'bg-green-50' if success else 'bg-red-50'} rounded-lg"
                        ):
                            with ui.row().classes("items-center gap-2 mb-2"):
                                icon = "check_circle" if success else "error"
                                color = "green" if success else "red"
                                ui.icon(icon, size="sm").classes(f"text-{color}-500")
                                ui.label(
                                    t("common.success") if success else t("common.error")
                                ).classes(f"font-medium text-{color}-700")

                            if test_result.get("duration"):
                                ui.label(
                                    f"{t('automation.duration')}: {test_result['duration']:.3f}s"
                                ).classes("text-sm text-gray-600")
                            if test_result.get("actions_executed"):
                                ui.label(
                                    f"{t('automation.actions_executed')}: {test_result['actions_executed']}"
                                ).classes("text-sm text-gray-600")
                            if test_result.get("error"):
                                ui.label(f"{t('common.error')}: {test_result['error']}").classes(
                                    "text-sm text-red-600 mt-2"
                                )

            show_results()

        with ui.row().classes("justify-end mt-6 gap-2"):
            ui.button(t("common.close"), on_click=dialog.close).props("flat")

            def run_test() -> None:
                try:
                    # Parse context JSON
                    import json

                    try:
                        ctx = json.loads(test_params.get("context", "{}") or "{}")
                    except json.JSONDecodeError:
                        ui.notify(t("automation.invalid_context_json"), type="warning")
                        return

                    # Trigger the rule
                    result = controller.trigger_automation(rule_name, context=ctx)
                    test_result.clear()
                    test_result.update(result)
                    show_results()

                    if result.get("success"):
                        ui.notify(t("automation.test_success"), type="positive")
                    else:
                        ui.notify(t("automation.test_failed"), type="negative")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("automation.run_test"), icon="play_arrow", on_click=run_test).props(
                "color=primary"
            )

    dialog.open()


def _show_delete_rule_dialog(
    controller: BotController, rule_name: str, refresh_callback: Any
) -> None:
    """Show confirmation dialog to delete an automation rule."""
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md p-6"):
        ui.label(t("automation.delete_rule")).classes("text-xl font-bold mb-4")

        with ui.column().classes("gap-4 w-full"):
            ui.icon("warning", size="xl").classes("text-orange-500 mx-auto")
            ui.label(t("automation.delete_confirm").format(name=rule_name)).classes(
                "text-center text-gray-700"
            )
            ui.label(t("automation.delete_warning")).classes("text-center text-sm text-red-500")

        with ui.row().classes("justify-end mt-6 gap-2"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

            def confirm_delete() -> None:
                try:
                    success = controller.delete_automation_rule(rule_name)
                    if success:
                        ui.notify(t("automation.rule_deleted"), type="positive")
                        dialog.close()
                        refresh_callback()
                    else:
                        ui.notify(t("common.error"), type="negative")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("automation.confirm_delete"), icon="delete", on_click=confirm_delete).props(
                "color=red"
            )
