# ruff: noqa: E501
"""Logs page."""

from __future__ import annotations

import logging

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_logs_page(controller: BotController) -> None:
    """Build the Logs page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("logs.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("logs.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Get log stats
    log_lines = list(controller.log_lines) if controller.log_lines else []
    debug_count = len([line for line in log_lines if line[0] == logging.DEBUG])
    info_count = len([line for line in log_lines if line[0] == logging.INFO])
    warning_count = len([line for line in log_lines if line[0] == logging.WARNING])
    error_count = len([line for line in log_lines if line[0] >= logging.ERROR])

    # Stats cards
    with ui.element("div").classes(
        "grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Total logs
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(log_lines))).classes("text-xl sm:text-2xl font-bold text-blue-600")
                ui.label(t("logs.total")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Debug
        with ui.card().classes("p-3 sm:p-4 bg-gray-50 border border-gray-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(debug_count)).classes("text-xl sm:text-2xl font-bold text-gray-600")
                ui.label("DEBUG").classes("text-xs sm:text-sm text-gray-700 text-center")

        # Info
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(info_count)).classes("text-xl sm:text-2xl font-bold text-green-600")
                ui.label("INFO").classes("text-xs sm:text-sm text-green-700 text-center")

        # Warning
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(warning_count)).classes(
                    "text-xl sm:text-2xl font-bold text-orange-600"
                )
                ui.label("WARNING").classes("text-xs sm:text-sm text-orange-700 text-center")

        # Error
        with ui.card().classes("p-3 sm:p-4 bg-red-50 border border-red-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(error_count)).classes("text-xl sm:text-2xl font-bold text-red-600")
                ui.label("ERROR").classes("text-xs sm:text-sm text-red-700 text-center")

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"
    ):
        # Controls row
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4 w-full flex-wrap gap-2"):
            with ui.row().classes("items-center gap-4"):
                level_filter = (
                    ui.select(
                        ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        value="ALL",
                        label=t("logs.filter"),
                    )
                    .props("outlined dense")
                    .classes("w-40")
                )

            with ui.row().classes("gap-2"):

                def clear_logs() -> None:
                    controller.log_lines.clear()

                async def export_logs() -> None:
                    text = "\n".join(m for _, m in list(controller.log_lines))
                    from tempfile import NamedTemporaryFile

                    with NamedTemporaryFile(
                        "w", delete=False, suffix=".log", encoding="utf-8"
                    ) as tmp:
                        tmp.write(text)
                        tmp.flush()
                        ui.download(tmp.name)

                ui.button(t("logs.clear"), on_click=clear_logs, icon="delete_sweep").props("flat")
                ui.button(t("logs.export"), on_click=export_logs, icon="download").props(
                    "flat color=primary"
                )

        # Log display area
        log_area = (
            ui.textarea()
            .props("readonly outlined")
            .classes("w-full font-mono text-xs bg-gray-900 text-green-400")
            .style("height: 500px; font-family: 'Consolas', 'Monaco', monospace;")
        )

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    def update_log_area() -> None:
        rows: list[str] = []
        if controller.log_lines:
            filt = level_filter.value or "ALL"
            thresh = level_map.get(filt)
            for lv, msg in list(controller.log_lines)[-500:]:
                if thresh is None or lv >= thresh:
                    rows.append(msg)
        log_area.value = "\n".join(rows)

    ui.timer(1.0, update_log_area)
