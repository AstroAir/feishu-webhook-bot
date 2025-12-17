# ruff: noqa: E501
"""Event Server page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_events_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the Event Server page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("events.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("events.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    event_status = controller.get_event_server_status()
    recent_events = event_status.get("recent_events", [])

    # Stats cards
    with ui.element("div").classes(
        "grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Server status
        running = event_status.get("running", False)
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("dns" if running else "dns", size="md").classes(
                    f"text-{'green' if running else 'gray'}-600"
                )
                ui.label(t("events.server")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Recent events count
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(recent_events))).classes(
                    "text-xl sm:text-2xl font-bold text-green-600"
                )
                ui.label(t("events.recent_count")).classes(
                    "text-xs sm:text-sm text-green-700 text-center"
                )

        # Host
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(event_status.get("host", "N/A")).classes(
                    "text-sm sm:text-base font-bold text-purple-600 truncate"
                )
                ui.label(t("events.host")).classes("text-xs sm:text-sm text-purple-700 text-center")

        # Port
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(event_status.get("port", "N/A"))).classes(
                    "text-xl sm:text-2xl font-bold text-orange-600"
                )
                ui.label(t("events.port")).classes("text-xs sm:text-sm text-orange-700 text-center")

    # Status and controls - two column
    with ui.element("div").classes(
        "grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6 w-full"
    ):
        # Server status card
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("events.server_status")).classes(
                "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
            )
            with ui.row().classes("items-center gap-6"):
                color = "green" if event_status["running"] else "gray"
                with ui.element("div").classes(
                    f"w-16 h-16 rounded-full bg-{color}-100 flex items-center justify-center"
                ):
                    ui.icon("dns", size="xl").classes(f"text-{color}-600")
                with ui.column().classes("gap-2"):
                    ui.chip(
                        t("app.status.running")
                        if event_status["running"]
                        else t("app.status.stopped"),
                        color="green" if event_status["running"] else "grey",
                    ).classes("text-sm")
                    ui.label(f"{t('events.host')}: {event_status['host']}").classes(
                        "text-sm text-gray-600"
                    )
                    ui.label(f"{t('events.port')}: {event_status['port']}").classes(
                        "text-sm text-gray-600"
                    )

        # Server controls card
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("events.server_controls")).classes(
                "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
            )

            async def on_start_server() -> None:
                try:
                    if controller.bot and controller.bot.event_server:
                        if not getattr(controller.bot.event_server, "running", False):
                            controller.bot.event_server.start()
                            ui.notify(t("common.success"), type="positive")
                        else:
                            ui.notify(t("common.info"), type="info")
                    else:
                        ui.notify(t("common.warning"), type="warning")
                except Exception as e:
                    ui.notify(f"{t('notify.start_failed')}: {e}", type="negative")

            async def on_stop_server() -> None:
                try:
                    if controller.bot and controller.bot.event_server:
                        if getattr(controller.bot.event_server, "running", False):
                            controller.bot.event_server.stop()
                            ui.notify(t("common.success"), type="positive")
                        else:
                            ui.notify(t("common.info"), type="info")
                    else:
                        ui.notify(t("common.warning"), type="warning")
                except Exception as e:
                    ui.notify(f"{t('notify.stop_failed')}: {e}", type="negative")

            with ui.row().classes("gap-4"):
                ui.button(t("events.start"), on_click=on_start_server, icon="play_arrow").props(
                    "color=green size=lg"
                )
                ui.button(t("events.stop"), on_click=on_stop_server, icon="stop").props(
                    "color=red size=lg"
                )

    # Recent events and webhook test - two column
    with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 w-full"):
        # Recent events card
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
                ui.label(t("events.recent_events")).classes(
                    "text-base sm:text-lg font-semibold text-gray-800"
                )
                ui.button(icon="refresh", on_click=lambda: rebuild_events()).props(
                    "flat round dense"
                )
            events_container = ui.column().classes("gap-2 max-h-64 overflow-auto w-full")

            def rebuild_events() -> None:
                events_container.clear()
                with events_container:
                    status = controller.get_event_server_status()
                    recent = status.get("recent_events", [])
                    if not recent:
                        with ui.column().classes("items-center py-8"):
                            ui.icon("event_busy", size="xl").classes("text-gray-300 mb-2")
                            ui.label(t("events.no_events")).classes("text-gray-400")
                    else:
                        for event in recent:
                            with ui.card().classes(
                                "w-full p-3 bg-gray-50 border border-gray-100 rounded-lg"
                            ):
                                ui.label(str(event)).classes("text-sm text-gray-700")

            rebuild_events()

        # Webhook test card
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("events.webhook_test")).classes(
                "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
            )
            test_payload = (
                ui.textarea(t("events.test_payload"))
                .classes("w-full")
                .props("outlined auto-grow rows=5")
            )
            test_payload.value = '{"type":"message.created","event":{"message":{"content":"test"}}}'

            async def on_send_webhook() -> None:
                try:
                    import json

                    json.loads(test_payload.value)
                    ui.notify(t("common.success"), type="info")
                except json.JSONDecodeError:
                    ui.notify(t("common.error"), type="negative")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("events.send_test"), on_click=on_send_webhook, icon="send").props(
                "color=primary"
            ).classes("mt-4")
