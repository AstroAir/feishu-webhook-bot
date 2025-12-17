# ruff: noqa: E501
"""Messages page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_messages_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the Messages page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("messages.queue_status")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("messages.queue_status_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    msg_stats = controller.get_message_stats()

    # Calculate success rate
    total = msg_stats["success"] + msg_stats["failed"]
    (msg_stats["success"] / total * 100) if total > 0 else 0

    # Stats cards - grid layout
    with ui.element("div").classes(
        "grid grid-cols-3 sm:grid-cols-5 gap-2 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Queue size
        with ui.card().classes("p-2 sm:p-5 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-0.5 sm:gap-1"):
                ui.label(str(msg_stats["queue_size"])).classes(
                    "text-xl sm:text-3xl font-bold text-blue-600"
                )
                ui.label(t("messages.queue_size")).classes(
                    "text-xs sm:text-sm text-blue-700 text-center"
                )
        # Queued
        with ui.card().classes("p-2 sm:p-5 bg-indigo-50 border border-indigo-100 rounded-xl"):
            with ui.column().classes("items-center gap-0.5 sm:gap-1"):
                ui.label(str(msg_stats["queued"])).classes(
                    "text-xl sm:text-3xl font-bold text-indigo-600"
                )
                ui.label(t("messages.queued")).classes(
                    "text-xs sm:text-sm text-indigo-700 text-center"
                )
        # Pending
        with ui.card().classes("p-2 sm:p-5 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-0.5 sm:gap-1"):
                ui.label(str(msg_stats["pending"])).classes(
                    "text-xl sm:text-3xl font-bold text-orange-600"
                )
                ui.label(t("messages.pending")).classes(
                    "text-xs sm:text-sm text-orange-700 text-center"
                )
        # Failed
        with ui.card().classes("p-2 sm:p-5 bg-red-50 border border-red-100 rounded-xl"):
            with ui.column().classes("items-center gap-0.5 sm:gap-1"):
                ui.label(str(msg_stats["failed"])).classes(
                    "text-xl sm:text-3xl font-bold text-red-600"
                )
                ui.label(t("messages.failed")).classes(
                    "text-xs sm:text-sm text-red-700 text-center"
                )
        # Success
        with ui.card().classes("p-2 sm:p-5 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-0.5 sm:gap-1"):
                ui.label(str(msg_stats["success"])).classes(
                    "text-xl sm:text-3xl font-bold text-green-600"
                )
                ui.label(t("messages.success")).classes(
                    "text-xs sm:text-sm text-green-700 text-center"
                )

    # Two column layout
    with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 w-full"):
        # Message tracker stats
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
                ui.label(t("messages.tracker_stats")).classes(
                    "text-base sm:text-lg font-semibold text-gray-800"
                )
                ui.button(icon="refresh", on_click=lambda: rebuild_message_stats()).props(
                    "flat round dense"
                )
            tracker_container = ui.column().classes("gap-3 sm:gap-4 w-full")

            def rebuild_message_stats() -> None:
                tracker_container.clear()
                with tracker_container:
                    stats = controller.get_message_stats()
                    with ui.element("div").classes("grid grid-cols-2 gap-2 sm:gap-4"):
                        with ui.column().classes("items-center p-2 sm:p-4 bg-orange-50 rounded-lg"):
                            ui.label(str(stats["pending"])).classes(
                                "text-lg sm:text-2xl font-bold text-orange-600"
                            )
                            ui.label(t("messages.total_pending")).classes(
                                "text-xs text-orange-700 text-center"
                            )
                        with ui.column().classes("items-center p-2 sm:p-4 bg-red-50 rounded-lg"):
                            ui.label(str(stats["failed"])).classes(
                                "text-lg sm:text-2xl font-bold text-red-600"
                            )
                            ui.label(t("messages.total_failed")).classes(
                                "text-xs text-red-700 text-center"
                            )
                        with ui.column().classes("items-center p-2 sm:p-4 bg-green-50 rounded-lg"):
                            ui.label(str(stats["success"])).classes(
                                "text-lg sm:text-2xl font-bold text-green-600"
                            )
                            ui.label(t("messages.total_success")).classes(
                                "text-xs text-green-700 text-center"
                            )
                        with ui.column().classes("items-center p-2 sm:p-4 bg-blue-50 rounded-lg"):
                            ui.label(str(stats["queue_size"])).classes(
                                "text-lg sm:text-2xl font-bold text-blue-600"
                            )
                            ui.label(t("messages.queue_size")).classes(
                                "text-xs text-blue-700 text-center"
                            )

            rebuild_message_stats()

        # Circuit breaker status
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
                ui.label(t("messages.circuit_breaker")).classes(
                    "text-base sm:text-lg font-semibold text-gray-800"
                )
                ui.button(icon="refresh", on_click=lambda: rebuild_circuit_breakers()).props(
                    "flat round dense"
                )
            cb_container = ui.column().classes("gap-2 sm:gap-3 w-full")

            def rebuild_circuit_breakers() -> None:
                cb_container.clear()
                with cb_container:
                    from ...core.circuit_breaker import CircuitBreakerRegistry

                    try:
                        registry = CircuitBreakerRegistry()
                        all_status = registry.get_all_status()
                        if not all_status:
                            with ui.column().classes("items-center py-8"):
                                ui.icon("electric_bolt", size="xl").classes("text-gray-300 mb-2")
                                ui.label(t("messages.no_breakers")).classes("text-gray-400")
                            return
                        for name, status in all_status.items():
                            with (
                                ui.card().classes(
                                    "w-full p-3 bg-gray-50 border border-gray-100 rounded-lg"
                                ),
                                ui.row().classes("items-center justify-between"),
                            ):
                                ui.label(name).classes("font-medium text-gray-800")
                                color = (
                                    "green"
                                    if status["state"] == "CLOSED"
                                    else "orange"
                                    if status["state"] == "HALF_OPEN"
                                    else "red"
                                )
                                ui.chip(status["state"], color=color)
                    except Exception as e:
                        ui.label(f"{t('common.error')}: {e}").classes("text-red-500 text-sm")

            rebuild_circuit_breakers()
