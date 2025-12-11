# ruff: noqa: E501
"""Tasks page."""

from __future__ import annotations

import json
from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_tasks_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the Tasks page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("tasks.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("tasks.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    task_list = controller.get_task_list()
    stats = controller.get_all_task_stats()

    # Stats cards - Enhanced with execution statistics
    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"):
        # Total tasks
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(stats.get("total_tasks", len(task_list)))).classes("text-xl sm:text-2xl font-bold text-blue-600")
                ui.label(t("tasks.total")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Enabled tasks
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(stats.get("enabled_tasks", 0))).classes("text-xl sm:text-2xl font-bold text-green-600")
                ui.label(t("tasks.enabled")).classes("text-xs sm:text-sm text-green-700 text-center")

        # Scheduled tasks
        scheduled_count = len([tk for tk in task_list if tk.get("next_run") and tk.get("next_run") != "N/A"])
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(scheduled_count)).classes("text-xl sm:text-2xl font-bold text-purple-600")
                ui.label(t("tasks.scheduled")).classes("text-xs sm:text-sm text-purple-700 text-center")

        # Total executions
        with ui.card().classes("p-3 sm:p-4 bg-indigo-50 border border-indigo-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(stats.get("total_executions", 0))).classes("text-xl sm:text-2xl font-bold text-indigo-600")
                ui.label(t("tasks.total_runs")).classes("text-xs sm:text-sm text-indigo-700 text-center")

        # Success rate
        success_rate = stats.get("overall_success_rate", 0)
        rate_color = "green" if success_rate >= 80 else "orange" if success_rate >= 50 else "red"
        with ui.card().classes("p-3 sm:p-4 bg-teal-50 border border-teal-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(f"{success_rate:.1f}%").classes(f"text-xl sm:text-2xl font-bold text-{rate_color}-600")
                ui.label(t("tasks.success_rate")).classes("text-xs sm:text-sm text-teal-700 text-center")

        # Bot status
        bot_running = controller.running
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                status_icon = "check_circle" if bot_running else "cancel"
                status_color = "green" if bot_running else "gray"
                ui.icon(status_icon, size="md").classes(f"text-{status_color}-600")
                ui.label(t("tasks.bot_status")).classes("text-xs sm:text-sm text-orange-700 text-center")

    # Task list card
    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4 flex-wrap gap-2"):
            ui.label(t("tasks.list")).classes("text-base sm:text-lg font-semibold text-gray-800")
            with ui.row().classes("gap-2"):
                ui.button(icon="refresh", on_click=lambda: rebuild_tasks()).props("flat round dense").tooltip(t("common.refresh"))

                def on_reload_tasks() -> None:
                    result = controller.reload_tasks()
                    if result.get("success"):
                        ui.notify(t("tasks.reload_success").format(count=result.get("tasks_reloaded", 0)), type="positive")
                        rebuild_tasks()
                    else:
                        ui.notify(f"{t('common.error')}: {result.get('error')}", type="negative")

                ui.button(icon="sync", on_click=on_reload_tasks).props("flat round dense").tooltip(t("tasks.reload"))

                def show_template_dialog() -> None:
                    _show_create_from_template_dialog(controller, rebuild_tasks)

                templates = controller.get_task_templates()
                if templates:
                    ui.button(t("tasks.from_template"), icon="content_copy", on_click=show_template_dialog).props("dense outline color=secondary")

                ui.button(t("tasks.run_all"), icon="play_arrow", on_click=lambda: run_all_tasks()).props("dense color=primary")

        tasks_container = ui.column().classes("gap-3 w-full")

        def run_all_tasks() -> None:
            try:
                if controller.bot and controller.bot.task_manager:
                    for task in task_list:
                        controller.run_task(task["name"])
                    ui.notify(t("tasks.all_started"), type="positive")
                else:
                    ui.notify(t("plugins.bot_not_running"), type="warning")
            except Exception as e:
                ui.notify(f"{t('common.error')}: {e}", type="negative")

        def rebuild_tasks() -> None:
            tasks_container.clear()
            with tasks_container:
                current_tasks = controller.get_task_list()
                if not current_tasks:
                    with ui.column().classes("items-center py-8 sm:py-12"):
                        ui.icon("task_alt", size="xl").classes("text-gray-300 mb-3")
                        ui.label(t("tasks.no_tasks")).classes("text-gray-400 text-base sm:text-lg")
                        ui.label(t("tasks.no_tasks_hint")).classes("text-gray-400 text-sm")
                    return

                # Task cards
                for task in current_tasks:
                    _build_task_card(controller, task, rebuild_tasks)

        rebuild_tasks()

    # Execution history section
    with ui.column().classes("w-full mt-4 sm:mt-6 mb-3 sm:mb-4"):
        ui.label(t("tasks.history")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("tasks.history_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
            ui.label(t("tasks.recent_executions")).classes("text-base sm:text-lg font-semibold text-gray-800")
            ui.button(icon="refresh", on_click=lambda: rebuild_history()).props("flat round dense")

        history_container = ui.column().classes("gap-2 w-full")

        def rebuild_history() -> None:
            history_container.clear()
            with history_container:
                history = controller.get_task_history(limit=10)
                if not history:
                    with ui.column().classes("items-center py-6"):
                        ui.icon("history", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("tasks.no_history")).classes("text-gray-400")
                    return

                for entry in history:
                    status_color = "green" if entry.get("success") else "red"
                    status_icon = "check_circle" if entry.get("success") else "error"
                    with ui.row().classes("w-full items-center justify-between p-3 bg-gray-50 rounded-lg"):
                        with ui.row().classes("items-center gap-3"):
                            ui.icon(status_icon, size="sm").classes(f"text-{status_color}-500")
                            with ui.column().classes("gap-0"):
                                ui.label(entry.get("task_name", "Unknown")).classes("font-medium text-gray-800")
                                ui.label(entry.get("executed_at", "N/A")).classes("text-xs text-gray-500")
                        with ui.row().classes("items-center gap-2"):
                            duration = entry.get("duration", 0)
                            ui.label(f"{duration:.2f}s").classes("text-sm text-gray-600")
                            if entry.get("error"):
                                ui.icon("warning", size="sm").classes("text-orange-500").tooltip(entry.get("error"))

        rebuild_history()

    # Task configuration section (if state available)
    if state is not None:
        with ui.column().classes("w-full mt-4 sm:mt-6 mb-3 sm:mb-4"):
            ui.label(t("tasks.config")).classes("text-lg sm:text-xl font-semibold text-gray-800")
            ui.label(t("tasks.config_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

        tasks_config = state["form"].setdefault("tasks", [])
        with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            if not tasks_config:
                with ui.column().classes("items-center py-8"):
                    ui.icon("settings", size="lg").classes("text-gray-300 mb-2")
                    ui.label(t("tasks.no_config")).classes("text-gray-400")
            else:
                for idx, task_cfg in enumerate(tasks_config):
                    with ui.card().classes("w-full p-3 bg-gray-50 rounded-lg mb-2"):
                        with ui.row().classes("items-center gap-2 flex-wrap"):
                            ui.input(t("tasks.name")).bind_value(task_cfg, "name").props("dense outlined").classes("flex-1 min-w-32")
                            ui.input(t("tasks.description")).bind_value(task_cfg, "description").props("dense outlined").classes("flex-1 min-w-48")


def _build_task_card(controller: BotController, task: dict[str, Any], refresh_callback: Any) -> None:
    """Build a single task card with full controls."""
    task_name = task["name"]
    is_enabled = task.get("enabled", True)

    with ui.card().classes("w-full p-3 sm:p-4 bg-gray-50 border border-gray-100 rounded-lg hover:bg-gray-100 transition-colors"):
        with ui.row().classes("w-full items-start justify-between flex-wrap gap-2"):
            # Task info
            with ui.column().classes("gap-1 flex-grow min-w-0"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(task_name).classes("font-semibold text-gray-800 truncate")
                    if is_enabled:
                        ui.chip(t("tasks.ready"), color="green").props("dense")
                    else:
                        ui.chip(t("tasks.disabled"), color="grey").props("dense")
                ui.label(task.get("description", "") or t("tasks.no_description")).classes("text-xs sm:text-sm text-gray-500 truncate")

            # Task controls
            with ui.row().classes("items-center gap-2 sm:gap-4 flex-wrap"):
                # Next run info
                with ui.column().classes("items-center gap-0"):
                    ui.label(t("tasks.next_run")).classes("text-xs text-gray-400")
                    ui.label(task.get("next_run", "N/A")).classes("text-xs sm:text-sm font-medium")

                # Action buttons
                with ui.row().classes("gap-1"):
                    # Run button
                    def on_run(tn: str = task_name) -> None:
                        try:
                            result = controller.run_task(tn)
                            if result.get("success"):
                                ui.notify(f"{tn} {t('common.success')}", type="positive")
                            else:
                                ui.notify(f"{t('common.error')}: {result.get('error', 'Unknown')}", type="negative")
                        except Exception as e:
                            ui.notify(f"{t('common.error')}: {e}", type="negative")

                    ui.button(icon="play_arrow", on_click=on_run).props("dense flat color=primary").tooltip(t("tasks.run"))

                    # Pause/Resume button
                    def on_pause(tn: str = task_name) -> None:
                        try:
                            if controller.pause_task(tn):
                                ui.notify(f"{tn} {t('tasks.paused')}", type="positive")
                                refresh_callback()
                            else:
                                ui.notify(t("common.error"), type="negative")
                        except Exception as e:
                            ui.notify(f"{t('common.error')}: {e}", type="negative")

                    def on_resume(tn: str = task_name) -> None:
                        try:
                            if controller.resume_task(tn):
                                ui.notify(f"{tn} {t('tasks.resumed')}", type="positive")
                                refresh_callback()
                            else:
                                ui.notify(t("common.error"), type="negative")
                        except Exception as e:
                            ui.notify(f"{t('common.error')}: {e}", type="negative")

                    ui.button(icon="pause", on_click=on_pause).props("dense flat color=orange").tooltip(t("tasks.pause"))
                    ui.button(icon="play_circle", on_click=on_resume).props("dense flat color=green").tooltip(t("tasks.resume"))

                    # Enable/Disable toggle
                    def on_toggle(tn: str = task_name, enabled: bool = is_enabled) -> None:
                        try:
                            if enabled:
                                success = controller.disable_task(tn)
                                msg = t("tasks.task_disabled")
                            else:
                                success = controller.enable_task(tn)
                                msg = t("tasks.task_enabled")
                            if success:
                                ui.notify(f"{tn} {msg}", type="positive")
                                refresh_callback()
                            else:
                                ui.notify(t("common.error"), type="negative")
                        except Exception as e:
                            ui.notify(f"{t('common.error')}: {e}", type="negative")

                    toggle_icon = "toggle_on" if is_enabled else "toggle_off"
                    toggle_color = "green" if is_enabled else "grey"
                    ui.button(icon=toggle_icon, on_click=on_toggle).props(f"dense flat color={toggle_color}").tooltip(t("tasks.toggle_enabled"))

                    # Run with params button
                    def show_run_params(tn: str = task_name) -> None:
                        _show_run_with_params_dialog(controller, tn)

                    ui.button(icon="tune", on_click=show_run_params).props("dense flat color=secondary").tooltip(t("tasks.run_with_params"))

                    # Edit button
                    def show_edit(tn: str = task_name) -> None:
                        _show_edit_task_dialog(controller, tn, refresh_callback)

                    ui.button(icon="edit", on_click=show_edit).props("dense flat color=orange").tooltip(t("tasks.edit_task"))

                    # Details button
                    def show_details(tn: str = task_name) -> None:
                        details = controller.get_task_details(tn)
                        if "error" in details:
                            ui.notify(details["error"], type="negative")
                            return
                        _show_task_details_dialog(details)

                    ui.button(icon="info", on_click=show_details).props("dense flat color=blue").tooltip(t("tasks.details"))

                    # Delete button
                    def show_delete_confirm(tn: str = task_name) -> None:
                        _show_delete_task_dialog(controller, tn, refresh_callback)

                    ui.button(icon="delete", on_click=show_delete_confirm).props("dense flat color=red").tooltip(t("tasks.delete_task"))


def _show_task_details_dialog(details: dict[str, Any]) -> None:
    """Show task details in a dialog."""
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-6 max-h-screen overflow-y-auto"):
        ui.label(f"{t('tasks.details')}: {details.get('name', 'Unknown')}").classes("text-xl font-bold mb-4")

        with ui.tabs().classes("w-full") as tabs:
            tab_info = ui.tab("info", label=t("common.info"))
            tab_actions = ui.tab("actions", label=t("tasks.actions"))
            tab_conditions = ui.tab("conditions", label=t("automation.conditions"))
            tab_history = ui.tab("history", label=t("tasks.history"))

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
                            ui.label(t("tasks.schedule")).classes("text-xs text-gray-500")
                            ui.label(details.get("schedule", "N/A")).classes("font-medium text-sm")
                        with ui.column().classes("gap-1"):
                            ui.label("Timeout").classes("text-xs text-gray-500")
                            ui.label(f"{details.get('timeout', 0)}s").classes("font-medium")
                        with ui.column().classes("gap-1"):
                            ui.label("Max Concurrent").classes("text-xs text-gray-500")
                            ui.label(str(details.get("max_concurrent", 1))).classes("font-medium")

                    ui.separator()

                    # Execution stats
                    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-3 gap-4"):
                        with ui.column().classes("gap-1"):
                            ui.label(t("tasks.total_runs")).classes("text-xs text-gray-500")
                            ui.label(str(details.get("total_runs", 0))).classes("text-lg font-bold text-blue-600")
                        with ui.column().classes("gap-1"):
                            ui.label(t("tasks.success_rate")).classes("text-xs text-gray-500")
                            rate = details.get("success_rate", 0)
                            color = "green" if rate >= 80 else "orange" if rate >= 50 else "red"
                            ui.label(f"{rate:.1f}%").classes(f"text-lg font-bold text-{color}-600")
                        with ui.column().classes("gap-1"):
                            ui.label("Actions").classes("text-xs text-gray-500")
                            ui.label(str(details.get("actions_count", 0))).classes("font-medium")

                    # Error handling
                    error_handling = details.get("error_handling", {})
                    if error_handling:
                        ui.separator()
                        ui.label(t("tasks.error_handling")).classes("text-sm font-semibold mb-2")
                        with ui.element("div").classes("grid grid-cols-3 gap-4"):
                            with ui.column().classes("gap-1"):
                                ui.label("Retry on failure").classes("text-xs text-gray-500")
                                retry = error_handling.get("retry_on_failure", False)
                                ui.chip("Yes" if retry else "No", color="green" if retry else "grey").props("dense")
                            with ui.column().classes("gap-1"):
                                ui.label("Max retries").classes("text-xs text-gray-500")
                                ui.label(str(error_handling.get("max_retries", 0))).classes("font-medium")
                            with ui.column().classes("gap-1"):
                                ui.label("On failure").classes("text-xs text-gray-500")
                                ui.label(error_handling.get("on_failure_action", "log")).classes("font-medium")

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
                            if action.get("type") == "plugin_method":
                                ui.label(f"Plugin: {action.get('plugin_name', 'N/A')}").classes("text-sm")
                                ui.label(f"Method: {action.get('method_name', 'N/A')}").classes("text-sm text-gray-600")
                            elif action.get("type") == "send_message":
                                msg = action.get("message", "")
                                if msg:
                                    ui.label(f"Message: {msg[:50]}...").classes("text-sm text-gray-600")
                                if action.get("template"):
                                    ui.label(f"Template: {action.get('template')}").classes("text-sm text-gray-600")
                            elif action.get("type") == "http_request":
                                ui.label(f"URL: {action.get('url', 'N/A')}").classes("text-sm text-gray-600")
                                ui.label(f"Method: {action.get('method', 'GET')}").classes("text-sm")
                            elif action.get("type") in ("ai_chat", "ai_query"):
                                prompt = action.get("prompt", "")
                                if prompt:
                                    ui.label(f"Prompt: {prompt[:50]}...").classes("text-sm text-gray-600")

            # Conditions tab
            with ui.tab_panel(tab_conditions):
                conditions = details.get("conditions", [])
                if not conditions:
                    ui.label("No conditions configured").classes("text-gray-400 py-4")
                else:
                    for i, cond in enumerate(conditions, 1):
                        with ui.card().classes("w-full p-3 bg-gray-50 rounded-lg mb-2"):
                            with ui.row().classes("items-center gap-2"):
                                ui.chip(f"#{i}", color="blue").props("dense")
                                ui.chip(cond.get("type", "unknown"), color="orange").props("dense outline")
                            if cond.get("type") == "time_range":
                                ui.label(f"Time: {cond.get('start_time', '')} - {cond.get('end_time', '')}").classes("text-sm")
                            elif cond.get("type") == "day_of_week":
                                ui.label(f"Days: {', '.join(cond.get('days', []))}").classes("text-sm")
                            elif cond.get("type") == "environment":
                                ui.label(f"Environment: {cond.get('environment', '')}").classes("text-sm")
                            elif cond.get("type") == "custom":
                                ui.label(f"Expression: {cond.get('expression', '')}").classes("text-sm text-gray-600")

            # History tab
            with ui.tab_panel(tab_history):
                recent = details.get("recent_history", [])
                if not recent:
                    ui.label("No execution history").classes("text-gray-400 py-4")
                else:
                    for entry in recent[:10]:
                        status_icon = "check_circle" if entry.get("success") else "error"
                        status_color = "green" if entry.get("success") else "red"
                        with ui.row().classes("w-full items-center justify-between p-2 bg-gray-50 rounded mb-1"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon(status_icon, size="sm").classes(f"text-{status_color}-500")
                                ui.label(entry.get("executed_at", "N/A")).classes("text-sm")
                            with ui.row().classes("items-center gap-2"):
                                ui.label(f"{entry.get('duration', 0):.2f}s").classes("text-sm text-gray-600")
                                if entry.get("error"):
                                    ui.icon("warning", size="xs").classes("text-orange-500").tooltip(entry.get("error"))

        with ui.row().classes("justify-end mt-4"):
            ui.button(t("common.close"), on_click=dialog.close).props("flat")

    dialog.open()


def _show_create_from_template_dialog(controller: BotController, refresh_callback: Any) -> None:
    """Show dialog for creating a task from template."""
    templates = controller.get_task_templates()
    if not templates:
        ui.notify(t("tasks.no_templates"), type="warning")
        return

    form_data = {
        "template_name": templates[0]["name"] if templates else "",
        "task_name": "",
        "params": "{}",
    }

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg p-6"):
        ui.label(t("tasks.create_from_template")).classes("text-xl font-bold mb-4")

        # Template selection
        template_options = {tpl["name"]: tpl["name"] for tpl in templates}
        ui.select(
            template_options,
            label=t("tasks.select_template"),
            value=form_data["template_name"],
            on_change=lambda e: form_data.update({"template_name": e.value})
        ).classes("w-full mb-3").props("outlined")

        # Show selected template info
        selected_tpl = next((t for t in templates if t["name"] == form_data["template_name"]), None)
        if selected_tpl:
            ui.label(selected_tpl.get("description", "")).classes("text-sm text-gray-500 mb-2")
            if selected_tpl.get("parameters"):
                ui.label(t("tasks.template_params")).classes("text-sm font-medium mt-2")
                for param in selected_tpl["parameters"]:
                    req = " *" if param.get("required") else ""
                    ui.label(f"• {param['name']}{req}: {param.get('type', 'string')}").classes("text-xs text-gray-600")

        # Task name input
        ui.input(
            label=t("tasks.new_task_name"),
            validation={t("common.required"): lambda v: bool(v and v.strip())}
        ).bind_value(form_data, "task_name").classes("w-full mb-3").props("outlined")

        # Parameters JSON input
        ui.textarea(
            label=t("tasks.params_json"),
            placeholder='{"key": "value"}'
        ).bind_value(form_data, "params").classes("w-full mb-4").props("outlined rows=4")

        with ui.row().classes("justify-end gap-2"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

            def on_create() -> None:
                if not form_data["task_name"].strip():
                    ui.notify(t("tasks.name_required"), type="warning")
                    return
                try:
                    params = json.loads(form_data["params"]) if form_data["params"].strip() else {}
                except json.JSONDecodeError:
                    ui.notify(t("tasks.invalid_json"), type="negative")
                    return

                result = controller.create_task_from_template(
                    form_data["template_name"],
                    form_data["task_name"],
                    params
                )
                if result.get("success"):
                    ui.notify(t("tasks.task_created").format(name=form_data["task_name"]), type="positive")
                    dialog.close()
                    refresh_callback()
                else:
                    ui.notify(f"{t('common.error')}: {result.get('error')}", type="negative")

            ui.button(t("common.create"), on_click=on_create).props("color=primary")

    dialog.open()


def _show_run_with_params_dialog(controller: BotController, task_name: str) -> None:
    """Show dialog for running a task with custom parameters."""
    details = controller.get_task_details(task_name)
    params_info = details.get("parameters", [])

    form_data = {"params": "{}", "force": False}

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg p-6"):
        ui.label(f"{t('tasks.run_with_params')}: {task_name}").classes("text-xl font-bold mb-4")

        if params_info:
            ui.label(t("tasks.available_params")).classes("text-sm font-medium mb-2")
            for param in params_info:
                default_val = f" (default: {param.get('default')})" if param.get("default") else ""
                ui.label(f"• {param['name']}: {param.get('type', 'string')}{default_val}").classes("text-xs text-gray-600")
            ui.separator().classes("my-3")

        ui.textarea(
            label=t("tasks.params_json"),
            placeholder='{"key": "value"}'
        ).bind_value(form_data, "params").classes("w-full mb-3").props("outlined rows=4")

        ui.switch(t("tasks.force_run")).bind_value(form_data, "force")

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

            def on_run() -> None:
                try:
                    params = json.loads(form_data["params"]) if form_data["params"].strip() else {}
                except json.JSONDecodeError:
                    ui.notify(t("tasks.invalid_json"), type="negative")
                    return

                result = controller.run_task_with_params(task_name, params, force=form_data["force"])
                if result.get("success"):
                    ui.notify(f"{task_name} {t('common.success')}", type="positive")
                    dialog.close()
                else:
                    ui.notify(f"{t('common.error')}: {result.get('error')}", type="negative")

            ui.button(t("tasks.run"), on_click=on_run, icon="play_arrow").props("color=primary")

    dialog.open()


def _show_edit_task_dialog(controller: BotController, task_name: str, refresh_callback: Any) -> None:
    """Show dialog for editing task configuration."""
    details = controller.get_task_details(task_name)
    if "error" in details:
        ui.notify(details["error"], type="negative")
        return

    # Parse current schedule
    current_schedule = details.get("schedule", "")
    schedule_type = "none"
    schedule_value = ""
    if current_schedule:
        if current_schedule.startswith("cron:"):
            schedule_type = "cron"
            schedule_value = current_schedule.replace("cron:", "").strip()
        elif "minute" in str(current_schedule) or "hour" in str(current_schedule):
            schedule_type = "interval"
            schedule_value = str(current_schedule)
        else:
            schedule_value = str(current_schedule)
            schedule_type = "cron" if any(c in schedule_value for c in "* /") else "interval"

    form_data = {
        "timeout": details.get("timeout", 300),
        "max_concurrent": details.get("max_concurrent", 1),
        "description": details.get("description", ""),
        "schedule_type": schedule_type,
        "cron_expr": schedule_value if schedule_type == "cron" else "",
        "interval_minutes": 60,
    }

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg p-6 max-h-screen overflow-y-auto"):
        ui.label(f"{t('tasks.edit_task')}: {task_name}").classes("text-xl font-bold mb-4")

        # Basic settings
        ui.label(t("tasks.basic_settings")).classes("text-sm font-semibold text-gray-600 mb-2")
        ui.input(label=t("tasks.description")).bind_value(form_data, "description").classes("w-full mb-3").props("outlined")

        with ui.row().classes("gap-4 w-full mb-4"):
            ui.number(label=t("tasks.timeout"), min=0, max=3600).bind_value(form_data, "timeout").props("outlined").classes("flex-1")
            ui.number(label=t("tasks.max_concurrent"), min=1, max=10).bind_value(form_data, "max_concurrent").props("outlined").classes("flex-1")

        ui.separator().classes("my-3")

        # Schedule settings
        ui.label(t("tasks.schedule_settings")).classes("text-sm font-semibold text-gray-600 mb-2")

        schedule_options = {
            "none": t("tasks.schedule_none"),
            "cron": t("tasks.schedule_cron"),
            "interval": t("tasks.schedule_interval"),
        }
        schedule_select = ui.select(
            schedule_options,
            label=t("tasks.schedule_type"),
            value=form_data["schedule_type"],
        ).classes("w-full mb-3").props("outlined")

        # Dynamic schedule input container
        schedule_input_container = ui.column().classes("w-full gap-2")

        def update_schedule_inputs() -> None:
            schedule_input_container.clear()
            with schedule_input_container:
                if schedule_select.value == "cron":
                    ui.input(
                        label=t("tasks.cron_expression"),
                        placeholder="0 9 * * 1-5"
                    ).bind_value(form_data, "cron_expr").classes("w-full").props("outlined")
                    ui.label(t("tasks.cron_hint")).classes("text-xs text-gray-500")
                elif schedule_select.value == "interval":
                    ui.number(
                        label=t("tasks.interval_minutes"),
                        min=1, max=1440
                    ).bind_value(form_data, "interval_minutes").props("outlined").classes("w-full")

        schedule_select.on_value_change(lambda _: update_schedule_inputs())
        update_schedule_inputs()

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

            def on_save() -> None:
                updates = {
                    "timeout": form_data["timeout"],
                    "max_concurrent": form_data["max_concurrent"],
                    "description": form_data["description"],
                }
                # Add schedule update
                if schedule_select.value == "cron" and form_data["cron_expr"]:
                    updates["cron"] = form_data["cron_expr"]
                    updates["interval"] = None
                elif schedule_select.value == "interval" and form_data["interval_minutes"]:
                    updates["interval"] = {"minutes": form_data["interval_minutes"]}
                    updates["cron"] = None
                elif schedule_select.value == "none":
                    updates["cron"] = None
                    updates["interval"] = None

                result = controller.update_task_config(task_name, updates)
                if result.get("success"):
                    ui.notify(t("tasks.task_updated"), type="positive")
                    dialog.close()
                    refresh_callback()
                else:
                    ui.notify(f"{t('common.error')}: {result.get('error')}", type="negative")

            ui.button(t("common.save"), on_click=on_save).props("color=primary")

    dialog.open()


def _show_delete_task_dialog(controller: BotController, task_name: str, refresh_callback: Any) -> None:
    """Show confirmation dialog for deleting a task."""
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md p-6"):
        ui.label(t("tasks.delete_task")).classes("text-xl font-bold mb-4")

        with ui.column().classes("gap-3 w-full"):
            ui.icon("warning", size="xl").classes("text-orange-500 mx-auto")
            ui.label(t("tasks.delete_confirm").format(name=task_name)).classes("text-center text-gray-700")
            ui.label(t("tasks.delete_warning")).classes("text-center text-sm text-gray-500")

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

            def on_delete() -> None:
                result = controller.delete_task(task_name)
                if result.get("success"):
                    ui.notify(t("tasks.task_deleted").format(name=task_name), type="positive")
                    dialog.close()
                    refresh_callback()
                else:
                    ui.notify(f"{t('common.error')}: {result.get('error')}", type="negative")

            ui.button(t("common.delete"), on_click=on_delete, icon="delete").props("color=red")
