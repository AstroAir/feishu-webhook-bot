# ruff: noqa: E501
"""Plugins configuration page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_plugins_page(state: dict[str, Any], controller: BotController) -> None:
    """Build the Plugins configuration page."""
    plug = state["form"].setdefault("plugins", {})
    plug.setdefault("enabled", False)
    plug.setdefault("plugin_dir", "plugins")
    plug.setdefault("auto_reload", False)
    plug.setdefault("reload_delay", 1.0)

    # Get plugin stats
    plugin_names = []
    if controller.bot and controller.bot.plugin_manager:
        plugin_names = controller.bot.plugin_manager.list_plugins()
    
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("plugins.settings")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("plugins.settings_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Stats cards
    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"):
        # Total plugins
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(plugin_names))).classes("text-xl sm:text-2xl font-bold text-blue-600")
                ui.label(t("plugins.total")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Plugin status
        enabled = plug.get("enabled", False)
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("check_circle" if enabled else "cancel", size="md").classes(f"text-{'green' if enabled else 'gray'}-600")
                ui.label(t("plugins.status")).classes("text-xs sm:text-sm text-green-700 text-center")

        # Auto reload
        auto_reload = plug.get("auto_reload", False)
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("sync" if auto_reload else "sync_disabled", size="md").classes(f"text-{'purple' if auto_reload else 'gray'}-600")
                ui.label(t("plugins.auto_reload_status")).classes("text-xs sm:text-sm text-purple-700 text-center")

        # Bot status
        bot_running = controller.running
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("check_circle" if bot_running else "cancel", size="md").classes(f"text-{'green' if bot_running else 'gray'}-600")
                ui.label(t("plugins.bot_status")).classes("text-xs sm:text-sm text-orange-700 text-center")

    # Basic settings
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("plugins.basic_settings")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("plugins.basic_settings_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"):
        with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6"):
            with ui.column().classes("gap-4"):
                ui.switch(t("plugins.enable")).bind_value(plug, "enabled")
                ui.input(t("plugins.directory")).bind_value(plug, "plugin_dir").classes("w-full").props("outlined")
            with ui.column().classes("gap-4"):
                ui.switch(t("plugins.auto_reload")).bind_value(plug, "auto_reload")
                ui.number(t("plugins.reload_delay"), min=0.1, max=60, step=0.1).bind_value(plug, "reload_delay").props("outlined").classes("w-full")

    # Plugin controls section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("plugins.controls")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("plugins.controls_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")
    
    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
            ui.label(t("plugins.loaded_plugins")).classes("text-base sm:text-lg font-semibold text-gray-800")
            ui.button(t("plugins.refresh"), on_click=lambda: rebuild_plugin_controls(), icon="refresh").props("flat color=primary")

        plugin_controls = ui.column().classes("gap-2 w-full")

        def rebuild_plugin_controls() -> None:
            plugin_controls.clear()
            with plugin_controls:
                if not controller.bot or not controller.bot.plugin_manager:
                    with ui.column().classes("items-center py-8"):
                        ui.icon("extension_off", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("plugins.bot_not_running")).classes("text-gray-400")
                        ui.label(t("plugins.start_bot_hint")).classes("text-gray-400 text-sm")
                    return
                names = controller.bot.plugin_manager.list_plugins()
                if not names:
                    with ui.column().classes("items-center py-8"):
                        ui.icon("extension", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("plugins.no_plugins")).classes("text-gray-400")
                    return
                for name in names:
                    with ui.card().classes("w-full p-3 bg-gray-50 border border-gray-100 rounded-lg"):
                        with ui.row().classes("items-center justify-between w-full"):
                            with ui.row().classes("items-center gap-3"):
                                ui.icon("extension", size="sm").classes("text-blue-500")
                                ui.label(name).classes("font-medium text-gray-800")
                            with ui.row().classes("gap-2"):
                                def on_toggle(n: str = name) -> None:
                                    if not controller.bot or not controller.bot.plugin_manager:
                                        ui.notify(t("plugins.bot_not_running"), type="warning")
                                        return
                                    pm = controller.bot.plugin_manager
                                    if pm.disable_plugin(n):
                                        ui.notify(f"Disabled {n}", type="info")
                                    elif pm.enable_plugin(n):
                                        ui.notify(f"Enabled {n}", type="positive")
                                    else:
                                        ui.notify(f"No action on {n}", type="warning")
                                    rebuild_plugin_controls()

                                ui.button(t("plugins.toggle"), on_click=on_toggle, icon="power_settings_new").props("dense outline")

        rebuild_plugin_controls()
