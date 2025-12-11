# ruff: noqa: E501
"""Logging configuration page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t

# Log level descriptions
LOG_LEVEL_INFO = {
    "DEBUG": "详细调试信息，用于开发和排查问题",
    "INFO": "一般运行信息，推荐生产环境使用",
    "WARNING": "警告信息，可能存在问题但不影响运行",
    "ERROR": "错误信息，功能可能受影响",
    "CRITICAL": "严重错误，系统可能无法正常运行",
}

# Common log formats
LOG_FORMATS = [
    ("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "标准格式"),
    ("%(asctime)s - %(name)s - %(levelname)s - %(message)s", "详细格式"),
    ("[%(levelname)s] %(message)s", "简洁格式"),
    ("%(asctime)s %(levelname)s %(message)s", "时间戳格式"),
]


def build_logging_page(state: dict[str, Any], controller: BotController) -> None:
    """Build the Logging configuration page."""
    log_cfg = state["form"].setdefault("logging", {})
    log_cfg.setdefault("level", "INFO")
    log_cfg.setdefault("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    log_cfg.setdefault("log_file", "")
    log_cfg.setdefault("max_bytes", 10485760)
    log_cfg.setdefault("backup_count", 5)
    
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("logging.settings")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("logging.settings_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Current log level indicator
    current_level = log_cfg.get("level", "INFO")
    level_colors = {"DEBUG": "blue", "INFO": "green", "WARNING": "orange", "ERROR": "red", "CRITICAL": "purple"}
    
    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"):
        for level, desc in LOG_LEVEL_INFO.items():
            is_current = level == current_level
            color = level_colors.get(level, "gray")
            with ui.card().classes(f"p-3 sm:p-4 {'bg-' + color + '-50 border-' + color + '-200' if is_current else 'bg-gray-50 border-gray-100'} border rounded-xl cursor-pointer hover:shadow-md transition-shadow"):
                with ui.column().classes("items-center gap-1"):
                    ui.label(level).classes(f"text-sm sm:text-base font-bold {'text-' + color + '-600' if is_current else 'text-gray-600'}")
                    if is_current:
                        ui.chip("当前", color=color).props("dense")

    # Basic settings card
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("logging.basic_settings")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("logging.basic_settings_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"):
        with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6"):
            # Log level selection
            with ui.column().classes("gap-3"):
                level_select = (
                    ui.select(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], label=t("logging.level"))
                    .bind_value(log_cfg, "level")
                    .classes("w-full")
                    .props("outlined")
                )
                ui.label(LOG_LEVEL_INFO.get(log_cfg.get("level", "INFO"), "")).classes("text-xs sm:text-sm text-gray-500")
            
            # Log format selection
            with ui.column().classes("gap-3"):
                ui.input(t("logging.format")).bind_value(log_cfg, "format").classes("w-full").props("outlined")
                with ui.row().classes("gap-2 flex-wrap"):
                    for fmt, name in LOG_FORMATS:
                        def set_format(f: str = fmt) -> None:
                            log_cfg["format"] = f
                        ui.button(name, on_click=set_format).props("dense outline size=sm")

    # File output settings
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("logging.file_settings")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("logging.file_settings_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"):
        with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6"):
            ui.input(t("logging.file")).bind_value(log_cfg, "log_file").classes("w-full").props("outlined").tooltip(t("logging.file_hint"))
            ui.number(t("logging.max_bytes"), min=1024, max=104857600, step=1048576).bind_value(log_cfg, "max_bytes").classes("w-full").props("outlined")
            ui.number(t("logging.backup_count"), min=0, max=100).bind_value(log_cfg, "backup_count").classes("w-full").props("outlined")

    # Runtime controls
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("logging.runtime_controls")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("logging.runtime_controls_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
        with ui.row().classes("items-center gap-3 flex-wrap"):
            ui.button(
                t("logging.apply_level"),
                on_click=lambda: (controller.set_runtime_log_level(level_select.value or "INFO"), ui.notify(t("common.success"), type="positive")),
                icon="check"
            ).props("color=primary")
            ui.button(
                t("logging.set_debug"),
                on_click=lambda: (controller.set_runtime_log_level("DEBUG"), ui.notify("Set to DEBUG", type="info")),
                icon="bug_report"
            ).props("outline")
            ui.button(
                t("logging.set_info"),
                on_click=lambda: (controller.set_runtime_log_level("INFO"), ui.notify("Set to INFO", type="info")),
                icon="info"
            ).props("outline")
