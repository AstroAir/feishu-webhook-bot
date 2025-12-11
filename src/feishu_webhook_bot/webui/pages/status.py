# ruff: noqa: E501
"""Status page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_status_page(state: dict[str, Any], controller: BotController) -> None:
    """Build the Status page."""
    # Get status info
    status = controller.status()
    cfg_webhooks = state["form"].get("webhooks", [])
    
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("status.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("status.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Stats cards
    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"):
        # Bot status
        running = status.get("running", False)
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("power_settings_new", size="md").classes(f"text-{'green' if running else 'gray'}-600")
                ui.label(t("status.bot_running") if running else t("status.bot_stopped")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Scheduler status
        scheduler_running = status.get("scheduler_running", False)
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("schedule", size="md").classes(f"text-{'green' if scheduler_running else 'gray'}-600")
                ui.label(t("status.scheduler_active") if scheduler_running else t("status.scheduler_inactive")).classes("text-xs sm:text-sm text-green-700 text-center")

        # Plugins count
        plugins = status.get("plugins", [])
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(plugins))).classes("text-xl sm:text-2xl font-bold text-purple-600")
                ui.label(t("status.plugins_loaded")).classes("text-xs sm:text-sm text-purple-700 text-center")

        # Webhooks count
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(cfg_webhooks))).classes("text-xl sm:text-2xl font-bold text-orange-600")
                ui.label(t("status.webhooks_configured")).classes("text-xs sm:text-sm text-orange-700 text-center")

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
        status_label = ui.label("").classes("font-medium")
        plugin_list = ui.column().classes("gap-1")

    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mt-6"):
        ui.label(t("status.send_test")).classes("text-lg font-semibold text-gray-800 mb-4")
        cfg_webhooks = state["form"].get("webhooks", [])
        wh_names = [w.get("name", f"wh-{i}") for i, w in enumerate(cfg_webhooks)] or ["default"]
        sel_wh = ui.select(wh_names, value=wh_names[0] if wh_names else None, label="Webhook").props("outlined dense")
        msg_input = ui.input(t("status.message")).props("outlined dense clearable").classes("w-full")

        async def send_test() -> None:
            try:
                if not msg_input.value:
                    ui.notify(t("common.warning"), type="warning")
                    return
                controller.send_test_message(msg_input.value, webhook_name=sel_wh.value or "default")
                ui.notify(t("common.success"), type="positive")
            except Exception as e:
                ui.notify(f"{t('common.error')}: {e}", type="negative")

        ui.button(t("status.send"), on_click=send_test).props("color=primary")

    async def refresh_status() -> None:
        s = controller.status()
        status_label.text = f"{t('dashboard.bot_status')}: {t('app.status.running') if s['running'] else t('app.status.stopped')} | {t('dashboard.scheduler')}: {t('dashboard.active') if s['scheduler_running'] else t('dashboard.inactive')}"
        plugin_list.clear()
        with plugin_list:
            if not s["plugins"]:
                ui.label(t("dashboard.no_plugins")).classes("text-gray-500")
            else:
                with ui.row().classes("gap-2 flex-wrap"):
                    for p in s["plugins"]:
                        ui.chip(p, color="blue")

    # Scheduled jobs section
    with ui.column().classes("w-full mb-4 mt-6"):
        ui.label(t("status.scheduled_jobs")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("status.scheduled_jobs_desc")).classes("text-gray-500 mt-1")
    
    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
        jobs_container = ui.column().classes("gap-2 w-full")

        def rebuild_jobs() -> None:
            jobs_container.clear()
            with jobs_container:
                if not controller.bot or not controller.bot.scheduler:
                    ui.label(t("status.scheduler_not_running")).classes("text-gray-500")
                    return
                jobs = controller.bot.scheduler.get_jobs()
                if not jobs:
                    ui.label(t("status.no_jobs")).classes("text-gray-500")
                    return
                for job in jobs:
                    with ui.row().classes("items-center gap-3 p-2 bg-gray-50 rounded"):
                        ui.label(job.id).classes("font-medium")
                        ui.label(f"{t('tasks.next_run')}: {job.next_run_time}").classes("text-sm text-gray-600")

                        def _pause(jid: str = job.id) -> None:
                            if controller.bot and controller.bot.scheduler:
                                controller.bot.scheduler.pause_job(jid)

                        def _resume(jid: str = job.id) -> None:
                            if controller.bot and controller.bot.scheduler:
                                controller.bot.scheduler.resume_job(jid)

                        def _remove(jid: str = job.id) -> None:
                            if controller.bot and controller.bot.scheduler:
                                controller.bot.scheduler.remove_job(jid)

                        ui.button(t("status.pause"), on_click=_pause).props("dense size=sm")
                        ui.button(t("status.resume"), on_click=_resume).props("dense size=sm")
                        ui.button(t("status.remove"), on_click=_remove).props("dense size=sm color=red")

        with ui.row().classes("gap-2"):
            ui.button(t("status.refresh_status"), on_click=refresh_status).props("flat color=primary")
            ui.button(t("status.refresh_jobs"), on_click=rebuild_jobs).props("flat color=primary")
