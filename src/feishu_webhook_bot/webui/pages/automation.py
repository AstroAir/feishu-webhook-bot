# ruff: noqa: E501
"""Automation page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_automation_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the Automation page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("automation.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("automation.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    rules = controller.get_automation_rules()

    # Stats cards
    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"):
        # Total rules
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(rules))).classes("text-xl sm:text-2xl font-bold text-blue-600")
                ui.label(t("automation.total_rules")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Active rules
        active_count = len([r for r in rules if r.get("enabled", True)])
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(active_count)).classes("text-xl sm:text-2xl font-bold text-green-600")
                ui.label(t("automation.active")).classes("text-xs sm:text-sm text-green-700 text-center")

        # Ready rules
        ready_count = len([r for r in rules if r.get("status") == "Ready"])
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(ready_count)).classes("text-xl sm:text-2xl font-bold text-purple-600")
                ui.label(t("automation.ready")).classes("text-xs sm:text-sm text-purple-700 text-center")

        # Bot status
        bot_running = controller.running
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("check_circle" if bot_running else "cancel", size="md").classes(f"text-{'green' if bot_running else 'gray'}-600")
                ui.label(t("automation.bot_status")).classes("text-xs sm:text-sm text-orange-700 text-center")

    # Active rules status section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("automation.active_rules")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("automation.active_rules_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"):
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
            ui.label(t("automation.registered_rules")).classes("text-base sm:text-lg font-semibold text-gray-800")
            ui.button(icon="refresh", on_click=lambda: rebuild_automations()).props("flat round dense")
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

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"):
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
            ui.label(t("automation.recent_executions")).classes("text-base sm:text-lg font-semibold text-gray-800")
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
                    with ui.row().classes("w-full items-center justify-between p-3 bg-gray-50 rounded-lg"):
                        with ui.row().classes("items-center gap-3"):
                            ui.icon(status_icon, size="sm").classes(f"text-{status_color}-500")
                            with ui.column().classes("gap-0"):
                                ui.label(entry.get("rule_name", "Unknown")).classes("font-medium text-gray-800")
                                ui.label(entry.get("triggered_at", "N/A")).classes("text-xs text-gray-500")
                        with ui.row().classes("items-center gap-2"):
                            duration = entry.get("duration", 0)
                            ui.label(f"{duration:.2f}s").classes("text-sm text-gray-600")
                            actions = entry.get("actions_executed", 0)
                            ui.chip(f"{actions} actions", color="blue").props("dense")
                            if entry.get("error"):
                                ui.icon("warning", size="sm").classes("text-orange-500").tooltip(entry.get("error"))

        rebuild_history()

    # Automation configuration section (if state available for editing)
    if state is not None:
        automation_cfg = state["form"].setdefault("automation", {})

        with ui.column().classes("w-full mb-3 sm:mb-4"):
            ui.label(t("automation.configuration")).classes("text-lg sm:text-xl font-semibold text-gray-800")
            ui.label(t("automation.configuration_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

        with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6 w-full"):
            # Basic settings
            with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
                ui.label(t("automation.basic_settings")).classes("text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4")
                with ui.column().classes("gap-4 w-full"):
                    ui.switch(t("automation.enabled")).bind_value(automation_cfg, "enabled")
                    ui.number(t("automation.max_concurrent"), min=1, max=100).bind_value(automation_cfg, "max_concurrent").props("outlined").classes("w-full")
                    ui.number(t("automation.timeout"), min=1, max=3600).bind_value(automation_cfg, "timeout_seconds").props("outlined").classes("w-full")

            # Error handling
            with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
                ui.label(t("automation.error_handling")).classes("text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4")
                with ui.column().classes("gap-4 w-full"):
                    ui.switch(t("automation.retry_on_error")).bind_value(automation_cfg, "retry_on_error")
                    ui.number(t("automation.max_retries"), min=0, max=10).bind_value(automation_cfg, "max_retries").props("outlined").classes("w-full")
                    ui.number(t("automation.retry_delay"), min=0, max=300).bind_value(automation_cfg, "retry_delay_seconds").props("outlined").classes("w-full")

        # Rules configuration
        with ui.column().classes("w-full mb-3 sm:mb-4"):
            ui.label(t("automation.rules_config")).classes("text-lg sm:text-xl font-semibold text-gray-800")
            ui.label(t("automation.rules_config_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

        with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"):
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
                            with ui.card().classes("w-full p-4 bg-gray-50 border border-gray-100 rounded-lg"):
                                with ui.row().classes("items-start justify-between gap-4"):
                                    with ui.column().classes("gap-3 flex-grow"):
                                        with ui.row().classes("gap-3 w-full"):
                                            ui.input(t("automation.rule_name")).bind_value(rule, "name").props("outlined dense").classes("flex-1")
                                            ui.switch(t("automation.rule_enabled")).bind_value(rule, "enabled")
                                        ui.input(t("automation.trigger_event")).bind_value(rule, "trigger").props("outlined dense").classes("w-full").tooltip(t("automation.trigger_event_hint"))
                                        ui.textarea(t("automation.conditions")).bind_value(rule, "conditions").props("outlined dense auto-grow rows=2").classes("w-full").tooltip(t("automation.conditions_hint"))
                                        ui.textarea(t("automation.actions")).bind_value(rule, "actions").props("outlined dense auto-grow rows=2").classes("w-full").tooltip(t("automation.actions_hint"))

                                    def remove_rule(i: int = idx) -> None:
                                        rules_list.pop(i)
                                        rebuild_rules()

                                    ui.button(icon="delete", on_click=remove_rule).props("flat round color=red")

            rebuild_rules()

            def add_rule() -> None:
                rules_list.append({
                    "name": "",
                    "enabled": True,
                    "trigger": "",
                    "conditions": "",
                    "actions": "",
                })
                rebuild_rules()

            ui.button(t("automation.add_rule"), on_click=add_rule, icon="add").props("outline color=primary").classes("mt-3")


def _build_automation_card(controller: BotController, rule: dict[str, Any], refresh_callback: Any) -> None:
    """Build a single automation rule card with full controls."""
    rule_name = rule["name"]
    is_enabled = rule.get("enabled", True)

    with ui.card().classes("w-full p-3 sm:p-4 bg-gray-50 border border-gray-100 rounded-lg hover:bg-gray-100 transition-colors"):
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
                                ui.notify(f"{t('common.error')}: {result.get('error', 'Unknown')}", type="negative")
                        except Exception as e:
                            ui.notify(f"{t('common.error')}: {e}", type="negative")

                    ui.button(icon="play_arrow", on_click=on_trigger).props("dense flat color=primary").tooltip(t("automation.trigger"))

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
                    ui.button(icon=toggle_icon, on_click=on_toggle).props(f"dense flat color={toggle_color}").tooltip(t("automation.toggle_enabled"))

                    # Details button
                    def show_details(rn: str = rule_name) -> None:
                        details = controller.get_automation_details(rn)
                        if "error" in details:
                            ui.notify(details["error"], type="negative")
                            return
                        _show_automation_details_dialog(details)

                    ui.button(icon="info", on_click=show_details).props("dense flat color=blue").tooltip(t("automation.details"))


def _show_automation_details_dialog(details: dict[str, Any]) -> None:
    """Show automation rule details in a dialog."""
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-6 max-h-screen overflow-y-auto"):
        ui.label(f"{t('automation.details')}: {details.get('name', 'Unknown')}").classes("text-xl font-bold mb-4")

        with ui.tabs().classes("w-full") as tabs:
            tab_info = ui.tab("info", label=t("common.info"))
            tab_actions = ui.tab("actions", label=t("automation.actions"))
            tab_history = ui.tab("history", label=t("automation.history"))

        with ui.tab_panels(tabs, value=tab_info).classes("w-full"):
            # Info tab
            with ui.tab_panel(tab_info):
                with ui.column().classes("gap-3 w-full"):
                    # Basic info
                    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-4"):
                        with ui.column().classes("gap-1"):
                            ui.label(t("tasks.status")).classes("text-xs text-gray-500")
                            status = "Enabled" if details.get("enabled") else "Disabled"
                            color = "green" if details.get("enabled") else "red"
                            ui.chip(status, color=color).props("dense")
                        with ui.column().classes("gap-1"):
                            ui.label(t("automation.trigger_type")).classes("text-xs text-gray-500")
                            ui.chip(details.get("trigger_type", "N/A"), color="purple").props("dense outline")
                        with ui.column().classes("gap-1"):
                            ui.label(t("automation.actions_count")).classes("text-xs text-gray-500")
                            ui.label(str(details.get("actions_count", 0))).classes("font-medium")
                        with ui.column().classes("gap-1"):
                            ui.label(t("automation.default_webhooks")).classes("text-xs text-gray-500")
                            webhooks = details.get("default_webhooks", [])
                            ui.label(", ".join(webhooks) if webhooks else "default").classes("font-medium text-sm")

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
                                ui.chip(action.get("type", "unknown"), color="purple").props("dense outline")
                            if action.get("type") == "send_text":
                                text = action.get("text", "")
                                if text:
                                    ui.label(f"Text: {text[:50]}...").classes("text-sm text-gray-600")
                            elif action.get("type") == "send_template":
                                ui.label(f"Template: {action.get('template', 'N/A')}").classes("text-sm")
                            elif action.get("type") == "http_request":
                                ui.label(f"URL: {action.get('url', 'N/A')}").classes("text-sm text-gray-600")
                            elif action.get("type") == "plugin_method":
                                ui.label(f"Plugin: {action.get('plugin_name', 'N/A')}").classes("text-sm")
                                ui.label(f"Method: {action.get('method_name', 'N/A')}").classes("text-sm text-gray-600")

            # History tab
            with ui.tab_panel(tab_history):
                recent = details.get("recent_executions", [])
                if not recent:
                    ui.label("No execution history").classes("text-gray-400 py-4")
                else:
                    for entry in recent[:10]:
                        status_icon = "check_circle" if entry.get("success") else "error"
                        status_color = "green" if entry.get("success") else "red"
                        with ui.row().classes("w-full items-center justify-between p-2 bg-gray-50 rounded mb-1"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon(status_icon, size="sm").classes(f"text-{status_color}-500")
                                ui.label(entry.get("triggered_at", "N/A")).classes("text-sm")
                            with ui.row().classes("items-center gap-2"):
                                ui.label(f"{entry.get('duration', 0):.2f}s").classes("text-sm text-gray-600")
                                if entry.get("error"):
                                    ui.icon("warning", size="xs").classes("text-orange-500").tooltip(entry.get("error"))

        with ui.row().classes("justify-end mt-4"):
            ui.button(t("common.close"), on_click=dialog.close).props("flat")

    dialog.open()
