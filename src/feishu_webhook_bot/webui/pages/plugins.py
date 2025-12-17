# ruff: noqa: E501, SIM117
"""Plugins configuration page."""

from __future__ import annotations

from datetime import datetime
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

    # State for plugin config editing
    selected_plugin = {"name": None, "config": {}, "schema": None}

    # Get plugin stats
    plugin_names = []
    if controller.bot and controller.bot.plugin_manager:
        plugin_names = controller.bot.plugin_manager.list_plugins()

    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("plugins.settings")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("plugins.settings_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Stats cards
    with ui.element("div").classes(
        "grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Total plugins
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(plugin_names))).classes(
                    "text-xl sm:text-2xl font-bold text-blue-600"
                )
                ui.label(t("plugins.total")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Plugin status
        enabled = plug.get("enabled", False)
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                icon_name = "check_circle" if enabled else "cancel"
                icon_color = "green" if enabled else "gray"
                ui.icon(icon_name, size="md").classes(f"text-{icon_color}-600")
                ui.label(t("plugins.status")).classes(
                    "text-xs sm:text-sm text-green-700 text-center"
                )

        # Auto reload
        auto_reload = plug.get("auto_reload", False)
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                icon_name = "sync" if auto_reload else "sync_disabled"
                icon_color = "purple" if auto_reload else "gray"
                ui.icon(icon_name, size="md").classes(f"text-{icon_color}-600")
                ui.label(t("plugins.auto_reload_status")).classes(
                    "text-xs sm:text-sm text-purple-700 text-center"
                )

        # Bot status
        bot_running = controller.running
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                icon_name = "check_circle" if bot_running else "cancel"
                icon_color = "green" if bot_running else "gray"
                ui.icon(icon_name, size="md").classes(f"text-{icon_color}-600")
                ui.label(t("plugins.bot_status")).classes(
                    "text-xs sm:text-sm text-orange-700 text-center"
                )

    # Basic settings
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("plugins.basic_settings")).classes(
            "text-lg sm:text-xl font-semibold text-gray-800"
        )
        ui.label(t("plugins.basic_settings_desc")).classes(
            "text-sm sm:text-base text-gray-500 mt-1"
        )

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6"):
            with ui.column().classes("gap-4"):
                ui.switch(t("plugins.enable")).bind_value(plug, "enabled")
                ui.input(t("plugins.directory")).bind_value(plug, "plugin_dir").classes(
                    "w-full"
                ).props("outlined")
            with ui.column().classes("gap-4"):
                ui.switch(t("plugins.auto_reload")).bind_value(plug, "auto_reload")
                ui.number(t("plugins.reload_delay"), min=0.1, max=60, step=0.1).bind_value(
                    plug, "reload_delay"
                ).props("outlined").classes("w-full")

    # Plugin list section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("plugins.plugin_list")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("plugins.plugin_list_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4 flex-wrap gap-2"):
            ui.label(t("plugins.loaded_plugins")).classes(
                "text-base sm:text-lg font-semibold text-gray-800"
            )
            with ui.row().classes("gap-2"):
                ui.button(
                    t("plugins.reload_all"), on_click=lambda: reload_all_plugins(), icon="refresh"
                ).props("flat color=primary")
                ui.button(
                    t("plugins.refresh"), on_click=lambda: rebuild_plugin_list(), icon="sync"
                ).props("flat color=secondary")

        plugin_list_container = ui.column().classes("gap-3 w-full")

        def get_plugin_manager():
            """Get plugin manager if available."""
            if controller.bot and controller.bot.plugin_manager:
                return controller.bot.plugin_manager
            return None

        def reload_all_plugins() -> None:
            """Reload all plugins."""
            pm = get_plugin_manager()
            if not pm:
                ui.notify(t("plugins.bot_not_running"), type="warning")
                return
            pm.reload_plugins()
            ui.notify(t("plugins.all_reloaded"), type="positive")
            rebuild_plugin_list()

        def rebuild_plugin_list() -> None:
            """Rebuild the plugin list UI."""
            plugin_list_container.clear()
            with plugin_list_container:
                pm = get_plugin_manager()
                if not pm:
                    with ui.column().classes("items-center py-8"):
                        ui.icon("extension_off", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("plugins.bot_not_running")).classes("text-gray-400")
                        ui.label(t("plugins.start_bot_hint")).classes("text-gray-400 text-sm")
                    return

                plugins_info = pm.get_all_plugin_info()
                if not plugins_info:
                    with ui.column().classes("items-center py-8"):
                        ui.icon("extension", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("plugins.no_plugins")).classes("text-gray-400")
                    return

                for info in plugins_info:
                    build_plugin_card(info, pm)

        def build_plugin_card(info, pm) -> None:
            """Build a card for a single plugin."""
            is_enabled = pm.is_plugin_enabled(info.name)
            status_color = "green" if is_enabled else "yellow"
            status_icon = "check_circle" if is_enabled else "pause_circle"

            with ui.card().classes(
                "w-full p-4 bg-gray-50 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
            ):
                # Header row
                with ui.row().classes("items-center justify-between w-full mb-2"):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("extension", size="sm").classes("text-blue-500")
                        ui.label(info.name).classes("font-semibold text-gray-800 text-lg")
                        ui.badge(f"v{info.version}").classes("bg-blue-100 text-blue-700")
                        ui.icon(status_icon, size="xs").classes(f"text-{status_color}-500")

                    # Action buttons
                    with ui.row().classes("gap-1"):
                        # Enable/Disable button
                        def toggle_plugin(n: str = info.name, enabled: bool = is_enabled) -> None:
                            if enabled:
                                if pm.disable_plugin(n):
                                    ui.notify(t("plugins.disabled").format(name=n), type="info")
                            else:
                                if pm.enable_plugin(n):
                                    ui.notify(t("plugins.enabled").format(name=n), type="positive")
                            rebuild_plugin_list()

                        btn_icon = "pause" if is_enabled else "play_arrow"
                        btn_color = "warning" if is_enabled else "positive"
                        btn_tip = t("plugins.disable") if is_enabled else t("plugins.enable_btn")
                        ui.button(icon=btn_icon, on_click=toggle_plugin).props(
                            f"dense flat color={btn_color}"
                        ).tooltip(btn_tip)

                        # Reload button
                        def reload_single(n: str = info.name) -> None:
                            if pm.reload_plugin(n):
                                ui.notify(t("plugins.reloaded").format(name=n), type="positive")
                            else:
                                ui.notify(
                                    t("plugins.reload_failed").format(name=n), type="negative"
                                )
                            rebuild_plugin_list()

                        ui.button(icon="refresh", on_click=reload_single).props(
                            "dense flat color=primary"
                        ).tooltip(t("plugins.reload"))

                        # Config button
                        def open_config(n: str = info.name) -> None:
                            selected_plugin["name"] = n
                            selected_plugin["config"] = pm.get_plugin_config(n).copy()
                            selected_plugin["schema"] = pm.get_plugin_schema(n)
                            rebuild_config_editor()
                            config_dialog.open()

                        ui.button(icon="settings", on_click=open_config).props(
                            "dense flat color=secondary"
                        ).tooltip(t("plugins.configure"))

                # Info row
                with ui.row().classes("items-center gap-4 text-sm text-gray-600 flex-wrap"):
                    if info.author:
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("person", size="xs").classes("text-gray-400")
                            ui.label(info.author)
                    if info.description:
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("info", size="xs").classes("text-gray-400")
                            desc = (
                                info.description[:60] + "..."
                                if len(info.description) > 60
                                else info.description
                            )
                            ui.label(desc)
                    if info.has_schema:
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("schema", size="xs").classes("text-green-500")
                            ui.label(t("plugins.has_schema"))
                    if info.permissions:
                        with ui.row().classes("items-center gap-1"):
                            perm_color = "green" if info.permissions_granted else "yellow"
                            ui.icon("security", size="xs").classes(f"text-{perm_color}-500")
                            ui.label(f"{len(info.permissions)} {t('plugins.permissions')}")
                    if info.jobs:
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("schedule", size="xs").classes("text-gray-400")
                            ui.label(f"{len(info.jobs)} {t('plugins.jobs')}")
                    if info.load_time:
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("access_time", size="xs").classes("text-gray-400")
                            load_dt = datetime.fromtimestamp(info.load_time)
                            ui.label(load_dt.strftime("%H:%M:%S"))

                # File path row (collapsible)
                if info.file_path:
                    with ui.expansion(t("plugins.show_details")).classes("w-full mt-2"):
                        with ui.column().classes("gap-2 text-sm"):
                            with ui.row().classes("items-center gap-1"):
                                ui.icon("folder", size="xs").classes("text-gray-400")
                                ui.label(t("plugins.file_path") + ":").classes("text-gray-500")
                                ui.label(info.file_path).classes("text-gray-600 font-mono text-xs")
                            if info.config:
                                with ui.row().classes("items-start gap-1"):
                                    ui.icon("tune", size="xs").classes("text-gray-400")
                                    ui.label(t("plugins.current_config") + ":").classes(
                                        "text-gray-500"
                                    )
                                with ui.element("pre").classes(
                                    "bg-gray-100 p-2 rounded text-xs overflow-x-auto"
                                ):
                                    import json

                                    # Mask sensitive values
                                    display_config = {}
                                    for k, v in info.config.items():
                                        if any(
                                            s in k.lower()
                                            for s in ["secret", "key", "password", "token"]
                                        ):
                                            display_config[k] = "***"
                                        else:
                                            display_config[k] = v
                                    ui.label(
                                        json.dumps(display_config, indent=2, ensure_ascii=False)
                                    )
                            # Show permissions
                            if info.permissions:
                                with ui.row().classes("items-start gap-1"):
                                    ui.icon("security", size="xs").classes("text-gray-400")
                                    ui.label(t("plugins.permissions") + ":").classes(
                                        "text-gray-500"
                                    )
                                with ui.column().classes("gap-1 ml-4"):
                                    for perm in info.permissions:
                                        perm_icon = (
                                            "check_circle"
                                            if info.permissions_granted
                                            else "warning"
                                        )
                                        perm_color = (
                                            "green" if info.permissions_granted else "yellow"
                                        )
                                        with ui.row().classes("items-center gap-1"):
                                            ui.icon(perm_icon, size="xs").classes(
                                                f"text-{perm_color}-500"
                                            )
                                            ui.label(perm).classes("text-xs font-mono")

        rebuild_plugin_list()

    # Plugin configuration dialog
    with ui.dialog() as config_dialog, ui.card().classes("w-full max-w-2xl"):
        config_editor_container = ui.column().classes("w-full p-4")

        def rebuild_config_editor() -> None:
            """Rebuild the configuration editor."""
            config_editor_container.clear()
            with config_editor_container:
                plugin_name = selected_plugin["name"]
                if not plugin_name:
                    ui.label(t("plugins.no_plugin_selected")).classes("text-gray-500")
                    return

                # Header
                with ui.row().classes("items-center justify-between w-full mb-4"):
                    ui.label(t("plugins.config_for").format(name=plugin_name)).classes(
                        "text-xl font-bold text-gray-800"
                    )
                    ui.button(icon="close", on_click=config_dialog.close).props("flat round")

                schema = selected_plugin["schema"]
                config = selected_plugin["config"]

                if not schema and not config:
                    ui.label(t("plugins.no_config_available")).classes("text-gray-500 py-4")
                    return

                # Build config fields
                if schema:
                    ui.label(t("plugins.config_schema")).classes(
                        "text-sm font-semibold text-gray-600 mb-2"
                    )
                    for field_name, field_info in schema.items():
                        with ui.row().classes("items-center gap-2 w-full mb-2"):
                            field_type = field_info.get("type", "string")
                            required = field_info.get("required", False)
                            default = field_info.get("default")
                            description = field_info.get("description", "")
                            sensitive = field_info.get("sensitive", False)

                            # Ensure field exists in config
                            if field_name not in config:
                                config[field_name] = default

                            label_text = field_name
                            if required:
                                label_text += " *"

                            if field_type == "bool":
                                ui.switch(label_text).bind_value(config, field_name).tooltip(
                                    description
                                )
                            elif field_type == "int":
                                min_val = field_info.get("min_value")
                                max_val = field_info.get("max_value")
                                ui.number(label_text, min=min_val, max=max_val).bind_value(
                                    config, field_name
                                ).props("outlined").classes("w-full").tooltip(description)
                            elif field_type == "float":
                                min_val = field_info.get("min_value")
                                max_val = field_info.get("max_value")
                                ui.number(
                                    label_text, min=min_val, max=max_val, step=0.1
                                ).bind_value(config, field_name).props("outlined").classes(
                                    "w-full"
                                ).tooltip(description)
                            elif field_type == "choice":
                                choices = field_info.get("choices", [])
                                ui.select(label_text, options=choices).bind_value(
                                    config, field_name
                                ).props("outlined").classes("w-full").tooltip(description)
                            elif sensitive or field_type == "secret":
                                ui.input(
                                    label_text, password=True, password_toggle_button=True
                                ).bind_value(config, field_name).props("outlined").classes(
                                    "w-full"
                                ).tooltip(description)
                            else:
                                ui.input(label_text).bind_value(config, field_name).props(
                                    "outlined"
                                ).classes("w-full").tooltip(description)
                else:
                    # No schema, show raw config editor
                    ui.label(t("plugins.current_config")).classes(
                        "text-sm font-semibold text-gray-600 mb-2"
                    )
                    for key, value in config.items():
                        with ui.row().classes("items-center gap-2 w-full mb-2"):
                            if isinstance(value, bool):
                                ui.switch(key).bind_value(config, key)
                            elif isinstance(value, (int, float)):
                                ui.number(key).bind_value(config, key).props("outlined").classes(
                                    "w-full"
                                )
                            else:
                                is_sensitive = (
                                    "secret" in key.lower()
                                    or "key" in key.lower()
                                    or "password" in key.lower()
                                )
                                if is_sensitive:
                                    ui.input(
                                        key, password=True, password_toggle_button=True
                                    ).bind_value(config, key).props("outlined").classes("w-full")
                                else:
                                    ui.input(key).bind_value(config, key).props("outlined").classes(
                                        "w-full"
                                    )

                # Action buttons
                with ui.row().classes("justify-end gap-2 mt-4 pt-4 border-t"):
                    ui.button(t("plugins.cancel"), on_click=config_dialog.close).props("flat")

                    def save_config() -> None:
                        pm = get_plugin_manager()
                        if not pm:
                            ui.notify(t("plugins.bot_not_running"), type="warning")
                            return
                        success, errors = pm.update_plugin_config(
                            selected_plugin["name"],
                            selected_plugin["config"],
                            save_to_file=True,
                            reload_plugin=False,
                        )
                        if success:
                            ui.notify(t("plugins.config_saved"), type="positive")
                            config_dialog.close()
                        else:
                            for err in errors:
                                ui.notify(err, type="negative")

                    def save_and_reload() -> None:
                        pm = get_plugin_manager()
                        if not pm:
                            ui.notify(t("plugins.bot_not_running"), type="warning")
                            return
                        success, errors = pm.update_plugin_config(
                            selected_plugin["name"],
                            selected_plugin["config"],
                            save_to_file=True,
                            reload_plugin=True,
                        )
                        if success:
                            ui.notify(t("plugins.config_saved_reloaded"), type="positive")
                            config_dialog.close()
                            rebuild_plugin_list()
                        else:
                            for err in errors:
                                ui.notify(err, type="negative")

                    ui.button(t("plugins.save"), on_click=save_config).props("color=primary")
                    ui.button(t("plugins.save_and_reload"), on_click=save_and_reload).props(
                        "color=positive"
                    )
