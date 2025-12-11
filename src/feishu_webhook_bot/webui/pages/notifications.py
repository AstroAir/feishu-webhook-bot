# ruff: noqa: E501
"""Notifications configuration page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..components import build_list_editor, notification_card
from ..i18n import t

# Common trigger types
TRIGGER_TYPES = [
    ("message.received", "收到消息时触发"),
    ("message.sent", "发送消息后触发"),
    ("event.error", "发生错误时触发"),
    ("task.completed", "任务完成时触发"),
    ("task.failed", "任务失败时触发"),
    ("bot.started", "Bot 启动时触发"),
    ("bot.stopped", "Bot 停止时触发"),
    ("schedule.triggered", "定时任务触发时"),
]


def build_notifications_page(state: dict[str, Any]) -> None:
    """Build the Notifications configuration page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("notifications.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("notifications.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    notification_list: list[dict[str, Any]] = state["form"].setdefault("notifications", [])
    template_list: list[dict[str, Any]] = state["form"].get("templates", [])

    # Stats cards
    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"):
        # Total notifications
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(notification_list))).classes("text-xl sm:text-2xl font-bold text-blue-600")
                ui.label(t("notifications.total")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Active notifications (with trigger)
        active_count = len([n for n in notification_list if n.get("trigger")])
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(active_count)).classes("text-xl sm:text-2xl font-bold text-green-600")
                ui.label(t("notifications.active")).classes("text-xs sm:text-sm text-green-700 text-center")

        # With conditions
        with_conditions = len([n for n in notification_list if n.get("conditions")])
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(with_conditions)).classes("text-xl sm:text-2xl font-bold text-purple-600")
                ui.label(t("notifications.with_conditions")).classes("text-xs sm:text-sm text-purple-700 text-center")

        # Available templates
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(template_list))).classes("text-xl sm:text-2xl font-bold text-orange-600")
                ui.label(t("notifications.templates")).classes("text-xs sm:text-sm text-orange-700 text-center")

    # Trigger reference
    with ui.expansion(t("notifications.trigger_reference"), icon="help_outline").classes("w-full mb-4 bg-white rounded-xl border border-gray-200"):
        with ui.element("div").classes("grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 p-4"):
            for trigger, desc in TRIGGER_TYPES:
                with ui.card().classes("p-2 sm:p-3 bg-gray-50 rounded-lg"):
                    ui.label(trigger).classes("text-xs sm:text-sm font-mono text-blue-600 mb-1")
                    ui.label(desc).classes("text-xs text-gray-600")

    # Notification list section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("notifications.list")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("notifications.list_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    build_list_editor(
        item_list=notification_list,
        card_builder=notification_card,
        default_item={
            "name": "new-notification",
            "trigger": "",
            "conditions": [],
            "template": "",
        },
        add_button_text=t("notifications.add"),
    )

    # Quick add section
    with ui.column().classes("w-full mt-4 sm:mt-6 mb-3 sm:mb-4"):
        ui.label(t("notifications.quick_add")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("notifications.quick_add_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
        with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3"):
            def add_preset_notification(name: str, trigger: str, template: str = "") -> None:
                notification_list.append({
                    "name": name,
                    "trigger": trigger,
                    "conditions": [],
                    "template": template,
                })
                ui.notify(f"Added {name}", type="positive")

            ui.button("消息通知", on_click=lambda: add_preset_notification("msg-notify", "message.received"), icon="message").props("outline dense").classes("w-full")
            ui.button("错误告警", on_click=lambda: add_preset_notification("error-alert", "event.error"), icon="error").props("outline dense").classes("w-full")
            ui.button("任务完成", on_click=lambda: add_preset_notification("task-done", "task.completed"), icon="check_circle").props("outline dense").classes("w-full")
            ui.button("定时触发", on_click=lambda: add_preset_notification("schedule-notify", "schedule.triggered"), icon="schedule").props("outline dense").classes("w-full")
