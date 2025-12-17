# ruff: noqa: E501
"""Scheduler configuration page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_scheduler_page(state: dict[str, Any], controller: BotController | None = None) -> None:
    """Build the Scheduler configuration page."""
    sched = state["form"].setdefault("scheduler", {})
    sched.setdefault("enabled", False)
    sched.setdefault("timezone", "Asia/Shanghai")
    sched.setdefault("job_store_type", "memory")

    # Get scheduler stats
    tasks_list = sched.get("tasks", [])
    active_jobs = 0
    scheduler_running = False
    if controller and controller.bot and controller.bot.scheduler:
        scheduler_running = True
        try:
            jobs = (
                controller.bot.scheduler.get_jobs()
                if hasattr(controller.bot.scheduler, "get_jobs")
                else []
            )
            active_jobs = len(jobs)
        except Exception:
            pass

    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("scheduler.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("scheduler.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Stats cards
    with ui.element("div").classes(
        "grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Scheduler status
        enabled = sched.get("enabled", False)
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("check_circle" if enabled else "cancel", size="md").classes(
                    f"text-{'green' if enabled else 'gray'}-600"
                )
                ui.label(t("scheduler.status")).classes(
                    "text-xs sm:text-sm text-blue-700 text-center"
                )

        # Configured tasks
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(tasks_list))).classes(
                    "text-xl sm:text-2xl font-bold text-green-600"
                )
                ui.label(t("scheduler.configured_tasks")).classes(
                    "text-xs sm:text-sm text-green-700 text-center"
                )

        # Active jobs
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(active_jobs)).classes("text-xl sm:text-2xl font-bold text-purple-600")
                ui.label(t("scheduler.active_jobs_count")).classes(
                    "text-xs sm:text-sm text-purple-700 text-center"
                )

        # Scheduler running
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("play_circle" if scheduler_running else "pause_circle", size="md").classes(
                    f"text-{'green' if scheduler_running else 'gray'}-600"
                )
                ui.label(t("scheduler.runtime_status")).classes(
                    "text-xs sm:text-sm text-orange-700 text-center"
                )

    # Basic settings section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("scheduler.basic_settings")).classes(
            "text-lg sm:text-xl font-semibold text-gray-800"
        )
        ui.label(t("scheduler.basic_settings_desc")).classes(
            "text-sm sm:text-base text-gray-500 mt-1"
        )

    with ui.element("div").classes(
        "grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6 w-full"
    ):
        # Enable and timezone
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("scheduler.general")).classes(
                "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
            )
            with ui.column().classes("gap-4 w-full"):
                ui.switch(t("scheduler.enable")).bind_value(sched, "enabled")
                ui.input(
                    t("scheduler.timezone"),
                    validation={t("common.required"): lambda v: bool(v and v.strip())},
                ).bind_value(sched, "timezone").classes("w-full").props("outlined").tooltip(
                    t("scheduler.timezone_hint")
                )

        # Job store settings
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("scheduler.job_store")).classes(
                "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
            )
            with ui.column().classes("gap-4 w-full"):
                ui.select(["memory", "sqlite"], label=t("scheduler.job_store_type")).bind_value(
                    sched, "job_store_type"
                ).classes("w-full").props("outlined")
                ui.input(t("scheduler.job_store_path")).bind_value(sched, "job_store_path").classes(
                    "w-full"
                ).props("outlined").tooltip(t("scheduler.sqlite_hint"))

    # Advanced settings
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("scheduler.advanced_settings")).classes(
            "text-lg sm:text-xl font-semibold text-gray-800"
        )
        ui.label(t("scheduler.advanced_settings_desc")).classes(
            "text-sm sm:text-base text-gray-500 mt-1"
        )

    with (
        ui.card().classes(
            "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
        ),
        ui.column().classes("gap-4 w-full"),
    ):
        with ui.row().classes("gap-2 sm:gap-4 w-full flex-wrap sm:flex-nowrap"):
            ui.number(t("scheduler.max_instances"), min=1, max=100).bind_value(
                sched, "max_instances"
            ).props("outlined").classes("flex-1 min-w-32")
            ui.number(t("scheduler.coalesce_time"), min=0, max=3600).bind_value(
                sched, "coalesce_time"
            ).props("outlined").classes("flex-1 min-w-32")
        with ui.row().classes("gap-2 sm:gap-4 w-full flex-wrap sm:flex-nowrap"):
            ui.number(t("scheduler.misfire_grace_time"), min=0, max=3600).bind_value(
                sched, "misfire_grace_time"
            ).props("outlined").classes("flex-1 min-w-32")
            ui.number(t("scheduler.job_defaults_max_instances"), min=1, max=10).bind_value(
                sched, "job_defaults_max_instances"
            ).props("outlined").classes("flex-1 min-w-32")

    # Scheduled tasks configuration
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("scheduler.tasks_config")).classes(
            "text-lg sm:text-xl font-semibold text-gray-800"
        )
        ui.label(t("scheduler.tasks_config_desc")).classes(
            "text-sm sm:text-base text-gray-500 mt-1"
        )

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        tasks_list = sched.setdefault("tasks", [])
        tasks_container = ui.column().classes("gap-3 w-full")

        def rebuild_tasks() -> None:
            tasks_container.clear()
            with tasks_container:
                if not tasks_list:
                    with ui.column().classes("items-center py-8"):
                        ui.icon("schedule", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("scheduler.no_tasks")).classes("text-gray-400")
                else:
                    for idx, task in enumerate(tasks_list):
                        with (
                            ui.card().classes(
                                "w-full p-4 bg-gray-50 border border-gray-100 rounded-lg"
                            ),
                            ui.row().classes("items-start justify-between gap-4"),
                        ):
                            with ui.column().classes("gap-3 flex-grow"):
                                with ui.row().classes("gap-3 w-full"):
                                    ui.input(t("scheduler.task_name")).bind_value(
                                        task, "name"
                                    ).props("outlined dense").classes("flex-1")
                                    ui.select(
                                        ["cron", "interval", "date"],
                                        label=t("scheduler.trigger_type"),
                                    ).bind_value(task, "trigger_type").props(
                                        "outlined dense"
                                    ).classes("w-32")
                                ui.input(t("scheduler.trigger_expression")).bind_value(
                                    task, "trigger_expression"
                                ).props("outlined dense").classes("w-full").tooltip(
                                    t("scheduler.trigger_expression_hint")
                                )
                                ui.input(t("scheduler.task_function")).bind_value(
                                    task, "function"
                                ).props("outlined dense").classes("w-full").tooltip(
                                    t("scheduler.task_function_hint")
                                )
                                ui.textarea(t("scheduler.task_description")).bind_value(
                                    task, "description"
                                ).props("outlined dense auto-grow rows=2").classes("w-full")

                            def remove_task(i: int = idx) -> None:
                                tasks_list.pop(i)
                                rebuild_tasks()

                            ui.button(icon="delete", on_click=remove_task).props(
                                "flat round color=red"
                            )

        rebuild_tasks()

        def add_task() -> None:
            tasks_list.append(
                {
                    "name": "",
                    "trigger_type": "cron",
                    "trigger_expression": "",
                    "function": "",
                    "description": "",
                }
            )
            rebuild_tasks()

        ui.button(t("scheduler.add_task"), on_click=add_task, icon="add").props(
            "outline color=primary"
        ).classes("mt-3")

    # Running jobs status (if controller available)
    if controller is not None:
        with ui.column().classes("w-full mb-4"):
            ui.label(t("scheduler.running_jobs")).classes("text-xl font-semibold text-gray-800")
            ui.label(t("scheduler.running_jobs_desc")).classes("text-gray-500 mt-1")

        with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            with ui.row().classes("items-center justify-between mb-4"):
                ui.label(t("scheduler.active_jobs")).classes("text-lg font-semibold text-gray-800")
                ui.button(icon="refresh", on_click=lambda: rebuild_jobs()).props("flat round dense")
            jobs_container = ui.column().classes("gap-2 w-full")

            def rebuild_jobs() -> None:
                jobs_container.clear()
                with jobs_container:
                    if not controller.bot or not controller.bot.scheduler:
                        with ui.column().classes("items-center py-6"):
                            ui.icon("schedule", size="xl").classes("text-gray-300 mb-2")
                            ui.label(t("scheduler.scheduler_not_running")).classes("text-gray-400")
                        return
                    try:
                        jobs = controller.get_scheduler_jobs()
                        if not jobs:
                            with ui.column().classes("items-center py-6"):
                                ui.icon("event_busy", size="xl").classes("text-gray-300 mb-2")
                                ui.label(t("scheduler.no_active_jobs")).classes("text-gray-400")
                            return
                        for job in jobs:
                            _build_job_card(controller, job, rebuild_jobs)
                    except Exception as e:
                        ui.label(f"{t('common.error')}: {e}").classes("text-red-500 text-sm")

            rebuild_jobs()

        # Scheduler status card
        with ui.card().classes(
            "w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mt-4"
        ):
            ui.label(t("scheduler.scheduler_status")).classes(
                "text-lg font-semibold text-gray-800 mb-4"
            )
            status = controller.get_scheduler_status()
            with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-4"):
                with ui.column().classes("gap-1"):
                    ui.label(t("scheduler.status")).classes("text-xs text-gray-500")
                    running = status.get("running", False)
                    ui.label("Running" if running else "Stopped").classes(
                        f"font-medium text-{'green' if running else 'red'}-600"
                    )
                with ui.column().classes("gap-1"):
                    ui.label(t("scheduler.timezone")).classes("text-xs text-gray-500")
                    ui.label(status.get("timezone", "N/A")).classes("font-medium")
                with ui.column().classes("gap-1"):
                    ui.label(t("scheduler.job_count")).classes("text-xs text-gray-500")
                    ui.label(str(status.get("job_count", 0))).classes("font-medium")
                with ui.column().classes("gap-1"):
                    ui.label(t("scheduler.job_store_type")).classes("text-xs text-gray-500")
                    ui.label(status.get("job_store_type", "memory")).classes("font-medium")


def _build_job_card(controller: BotController, job: dict[str, Any], refresh_callback: Any) -> None:
    """Build a single job card with controls."""
    job_id = job.get("id", "unknown")
    job_name = job.get("name", job_id)
    is_paused = job.get("paused", False)

    with ui.row().classes("items-center justify-between p-3 bg-gray-50 rounded-lg w-full"):
        with ui.column().classes("gap-0 flex-grow"):
            ui.label(job_name).classes("font-medium text-gray-800")
            next_run = job.get("next_run", "N/A")
            ui.label(f"Next run: {next_run}").classes("text-sm text-gray-500")
            trigger = job.get("trigger", "unknown")
            ui.label(f"Trigger: {trigger}").classes("text-xs text-gray-400")

        with ui.row().classes("items-center gap-2"):
            # Status chip
            if is_paused:
                ui.chip(t("scheduler.paused"), color="orange").props("dense")
            else:
                ui.chip(t("scheduler.active"), color="green").props("dense")

            # Pause/Resume button
            def on_pause(jid: str = job_id) -> None:
                try:
                    if controller.pause_scheduler_job(jid):
                        ui.notify(f"{jid} {t('scheduler.job_paused')}", type="positive")
                        refresh_callback()
                    else:
                        ui.notify(t("common.error"), type="negative")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            def on_resume(jid: str = job_id) -> None:
                try:
                    if controller.resume_scheduler_job(jid):
                        ui.notify(f"{jid} {t('scheduler.job_resumed')}", type="positive")
                        refresh_callback()
                    else:
                        ui.notify(t("common.error"), type="negative")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            if is_paused:
                ui.button(icon="play_circle", on_click=on_resume).props(
                    "dense flat color=green"
                ).tooltip(t("scheduler.resume_job"))
            else:
                ui.button(icon="pause", on_click=on_pause).props("dense flat color=orange").tooltip(
                    t("scheduler.pause_job")
                )

            # Remove button
            def on_remove(jid: str = job_id) -> None:
                try:
                    if controller.remove_scheduler_job(jid):
                        ui.notify(f"{jid} {t('scheduler.job_removed')}", type="positive")
                        refresh_callback()
                    else:
                        ui.notify(t("common.error"), type="negative")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(icon="delete", on_click=on_remove).props("dense flat color=red").tooltip(
                t("scheduler.remove_job")
            )
