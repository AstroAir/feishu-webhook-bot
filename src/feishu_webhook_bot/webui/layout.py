# ruff: noqa: E501
"""Main layout and entry points for the WebUI dashboard."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from nicegui import app, ui

from .components import config_to_form, form_to_config
from .controller import BotController
from .i18n import get_available_languages, get_lang, set_lang, t
from .pages import (
    build_ai_dashboard_page,
    build_auth_page,
    build_automation_page,
    build_bridge_page,
    build_events_page,
    build_feishu_page,
    build_general_page,
    build_logging_page,
    build_logs_page,
    build_messages_page,
    build_notifications_page,
    build_plugins_page,
    build_providers_page,
    build_qq_page,
    build_scheduler_page,
    build_status_page,
    build_tasks_page,
    build_templates_page,
)

# Navigation menu items organized by category (using i18n keys)
NAV_ITEMS = [
    {
        "id": "overview",
        "label_key": "nav.overview",
        "icon": "dashboard",
        "category_key": "nav.dashboard",
    },
    {
        "id": "general",
        "label_key": "nav.general",
        "icon": "settings",
        "category_key": "nav.configuration",
    },
    {
        "id": "webhooks",
        "label_key": "nav.webhooks",
        "icon": "webhook",
        "category_key": "nav.configuration",
    },
    {
        "id": "scheduler",
        "label_key": "nav.scheduler",
        "icon": "schedule",
        "category_key": "nav.configuration",
    },
    {
        "id": "plugins",
        "label_key": "nav.plugins",
        "icon": "extension",
        "category_key": "nav.configuration",
    },
    {
        "id": "logging",
        "label_key": "nav.logging",
        "icon": "description",
        "category_key": "nav.configuration",
    },
    {
        "id": "templates",
        "label_key": "nav.templates",
        "icon": "article",
        "category_key": "nav.configuration",
    },
    {
        "id": "notifications",
        "label_key": "nav.notifications",
        "icon": "notifications",
        "category_key": "nav.configuration",
    },
    {"id": "ai", "label_key": "nav.ai", "icon": "smart_toy", "category_key": "nav.features"},
    {"id": "tasks", "label_key": "nav.tasks", "icon": "task", "category_key": "nav.features"},
    {
        "id": "automation",
        "label_key": "nav.automation",
        "icon": "auto_fix_high",
        "category_key": "nav.features",
    },
    {
        "id": "providers",
        "label_key": "nav.providers",
        "icon": "cloud",
        "category_key": "nav.features",
    },
    {"id": "feishu", "label_key": "nav.feishu", "icon": "chat", "category_key": "nav.platforms"},
    {"id": "qq", "label_key": "nav.qq", "icon": "forum", "category_key": "nav.platforms"},
    {"id": "bridge", "label_key": "nav.bridge", "icon": "sync_alt", "category_key": "nav.features"},
    {
        "id": "messages",
        "label_key": "nav.messages",
        "icon": "message",
        "category_key": "nav.monitoring",
    },
    {"id": "auth", "label_key": "nav.auth", "icon": "security", "category_key": "nav.monitoring"},
    {"id": "events", "label_key": "nav.events", "icon": "event", "category_key": "nav.monitoring"},
    {"id": "logs", "label_key": "nav.logs", "icon": "terminal", "category_key": "nav.monitoring"},
]


def build_ui(config_path: Path) -> None:
    """Build the main dashboard UI."""
    controller = BotController(config_path=config_path)
    state: dict[str, Any] = {
        "form": config_to_form(controller.load_config()),
        "current_page": "overview",
    }

    async def reload_from_disk() -> None:
        try:
            cfg = controller.load_config()
            state["form"] = config_to_form(cfg)
            ui.notify("Configuration reloaded", type="positive")
            await ui.run_javascript("location.reload()")
        except Exception as e:
            ui.notify(f"Failed to reload: {e}", type="negative")

    async def save_to_disk() -> None:
        try:
            cfg = form_to_config(state["form"])
            controller.save_config(cfg)
            ui.notify("Configuration saved", type="positive")
        except Exception as e:
            ui.notify(f"Validation or save error: {e}", type="negative")

    async def on_start() -> None:
        try:
            controller.start()
            ui.notify("Bot started", type="positive")
        except Exception as e:
            ui.notify(f"Start failed: {e}", type="negative")

    async def on_stop() -> None:
        try:
            controller.stop()
            ui.notify("Bot stopped", type="positive")
        except Exception as e:
            ui.notify(f"Stop failed: {e}", type="negative")

    async def on_restart() -> None:
        try:
            controller.restart()
            ui.notify("Bot restarted", type="positive")
        except Exception as e:
            ui.notify(f"Restart failed: {e}", type="negative")

    # Main layout with left sidebar and mobile responsive
    ui.add_head_html("""
    <style>
        .nav-item { transition: background-color 0.15s; cursor: pointer; }
        .nav-item:hover { background-color: #f3f4f6; }
        .nav-item.active { background-color: #dbeafe; border-left: 3px solid #1e40af; }
        .sidebar-category { font-size: 0.7rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
        .main-container { display: flex; flex-direction: row; height: calc(100vh - 52px); width: 100%; }
        .left-sidebar { width: 220px; min-width: 220px; max-width: 220px; flex-shrink: 0; border-right: 1px solid #e5e7eb; background: #ffffff; overflow-y: auto; padding: 16px; transition: transform 0.3s ease, opacity 0.3s ease; }
        .main-content { flex: 1; min-width: 0; overflow-y: auto; padding: 24px; background: #f9fafb; }

        /* Mobile menu button */
        .mobile-menu-btn { display: none !important; }

        /* Header controls responsive */
        .header-controls { display: flex; flex-wrap: nowrap; align-items: center; gap: 0.5rem; }
        .header-desktop-controls { display: flex; align-items: center; gap: 0.5rem; }
        .header-mobile-controls { display: none; }

        /* Sidebar overlay for mobile */
        .sidebar-overlay { display: none; position: fixed; top: 52px; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 40; }
        .sidebar-overlay.active { display: block; }

        /* Mobile responsive styles */
        @media (max-width: 768px) {
            .mobile-menu-btn { display: flex !important; }
            .header-desktop-controls { display: none !important; }
            .header-mobile-controls { display: flex !important; flex-wrap: wrap; gap: 0.25rem; }

            .left-sidebar {
                position: fixed;
                top: 52px;
                left: 0;
                bottom: 0;
                z-index: 50;
                transform: translateX(-100%);
                box-shadow: 2px 0 8px rgba(0,0,0,0.1);
            }
            .left-sidebar.mobile-open { transform: translateX(0); }

            .main-content { padding: 16px; }
            .main-container { height: calc(100vh - 52px); }
        }

        /* Tablet responsive */
        @media (max-width: 1024px) and (min-width: 769px) {
            .left-sidebar { width: 200px; min-width: 200px; max-width: 200px; padding: 12px; }
            .main-content { padding: 20px; }
        }
    </style>
    <script>
        function toggleMobileSidebar() {
            const sidebar = document.querySelector('.left-sidebar');
            const overlay = document.querySelector('.sidebar-overlay');
            if (sidebar) {
                sidebar.classList.toggle('mobile-open');
                if (overlay) overlay.classList.toggle('active');
            }
        }
        function closeMobileSidebar() {
            const sidebar = document.querySelector('.left-sidebar');
            const overlay = document.querySelector('.sidebar-overlay');
            if (sidebar) {
                sidebar.classList.remove('mobile-open');
                if (overlay) overlay.classList.remove('active');
            }
        }
    </script>
    """)

    # Header - solid color, no gradient
    with ui.header(elevated=True).style("background:#1e40af").classes("px-4 py-2"):
        with ui.row().classes("w-full items-center justify-between gap-2"):
            with ui.row().classes("items-center gap-2"):
                # Mobile menu button
                ui.button(
                    icon="menu", on_click=lambda: ui.run_javascript("toggleMobileSidebar()")
                ).props("flat dense round color=white").classes("mobile-menu-btn")
                ui.icon("smart_toy", size="md").classes("text-white hidden sm:block")
                ui.label(t("app.title")).classes(
                    "text-base sm:text-lg font-semibold text-white truncate max-w-32 sm:max-w-none"
                )

            # Status chip (always visible)
            status_chip = ui.chip(t("app.status.stopped"), color="grey", text_color="white").props(
                "outline dense"
            )

            # Desktop controls
            with ui.row().classes("header-desktop-controls"):
                ui.button(t("header.start"), on_click=on_start).props(
                    "dense unelevated color=green-8"
                )
                ui.button(t("header.stop"), on_click=on_stop).props("dense unelevated color=red-8")
                ui.button(t("header.restart"), on_click=on_restart).props(
                    "dense unelevated color=orange-8"
                )
                ui.separator().props("vertical").classes("mx-1 h-6 opacity-50")
                ui.button(t("header.save"), on_click=save_to_disk).props(
                    "dense unelevated color=white text-color=blue-8"
                )
                ui.button(t("header.reset"), on_click=reload_from_disk).props(
                    "dense outline color=white"
                )
                ui.select(
                    {code: name for code, name in get_available_languages()},
                    value=get_lang(),
                    on_change=lambda e: (set_lang(e.value), ui.run_javascript("location.reload()")),
                ).props("dense outlined dark").classes("w-24").style("color: white")

            # Mobile controls (dropdown menu)
            with ui.element("div").classes("header-mobile-controls"):
                with ui.button(icon="more_vert").props("flat dense round color=white"):
                    with ui.menu().classes("bg-white"):
                        ui.menu_item(t("header.start"), on_click=on_start).classes("text-green-600")
                        ui.menu_item(t("header.stop"), on_click=on_stop).classes("text-red-600")
                        ui.menu_item(t("header.restart"), on_click=on_restart).classes(
                            "text-orange-600"
                        )
                        ui.separator()
                        ui.menu_item(t("header.save"), on_click=save_to_disk).classes(
                            "text-blue-600"
                        )
                        ui.menu_item(t("header.reset"), on_click=reload_from_disk)
                        ui.separator()
                        with ui.row().classes("px-4 py-2 items-center gap-2"):
                            ui.label(t("common.language")).classes("text-sm text-gray-600")
                            ui.select(
                                {code: name for code, name in get_available_languages()},
                                value=get_lang(),
                                on_change=lambda e: (
                                    set_lang(e.value),
                                    ui.run_javascript("location.reload()"),
                                ),
                            ).props("dense outlined").classes("w-20")

    # Main content area with left sidebar layout
    with ui.element("div").classes("main-container"):
        # Sidebar overlay for mobile (click to close)
        ui.element("div").classes("sidebar-overlay").on(
            "click", lambda: ui.run_javascript("closeMobileSidebar()")
        )

        # Left sidebar
        with ui.element("div").classes("left-sidebar"):
            # Config file info
            with ui.column().classes("mb-4 pb-3 border-b border-gray-200"):
                ui.label(t("sidebar.config_file")).classes(
                    "text-xs text-gray-500 uppercase tracking-wide"
                )
                ui.label(config_path.name).classes(
                    "text-sm font-medium text-gray-700 truncate"
                ).tooltip(str(config_path))

            # Navigation
            nav_container = ui.column().classes("w-full gap-0")
            nav_items_refs: dict[str, ui.element] = {}

            def update_nav_active() -> None:
                for pid, nav_el in nav_items_refs.items():
                    if pid == state["current_page"]:
                        nav_el.classes(add="active")
                    else:
                        nav_el.classes(remove="active")

            with nav_container:
                current_category_key = ""
                for item in NAV_ITEMS:
                    if item["category_key"] != current_category_key:
                        current_category_key = item["category_key"]
                        ui.label(t(current_category_key)).classes("sidebar-category mt-3 mb-1 px-2")

                    def make_nav_click(page_id: str):
                        async def on_click():
                            state["current_page"] = page_id
                            update_nav_active()
                            rebuild_content()
                            await ui.run_javascript("closeMobileSidebar()")

                        return on_click

                    nav_row = (
                        ui.row()
                        .classes("nav-item items-center gap-2 px-2 py-1.5 rounded w-full")
                        .on("click", make_nav_click(item["id"]))
                    )
                    with nav_row:
                        ui.icon(item["icon"], size="xs").classes("text-gray-500")
                        ui.label(t(item["label_key"])).classes("text-sm text-gray-700")
                    nav_items_refs[item["id"]] = nav_row
                    if item["id"] == state["current_page"]:
                        nav_row.classes(add="active")

            # Profile management section
            ui.label(t("sidebar.profiles")).classes("sidebar-category mt-4 mb-2 px-2")
            profiles_dir = config_path.parent / "profiles"
            profiles_dir.mkdir(exist_ok=True)
            profile_files = {p.stem: p for p in profiles_dir.glob("*.yaml")}

            async def save_profile() -> None:
                with ui.dialog() as dialog, ui.card().classes("p-4"):
                    ui.label(t("sidebar.save_profile")).classes("text-lg font-semibold mb-3")
                    name_input = (
                        ui.input(t("general.name")).props("outlined dense").classes("w-full")
                    )
                    with ui.row().classes("gap-2 mt-3"):
                        ui.button(t("common.cancel"), on_click=dialog.close).props("flat")
                        ui.button(
                            t("common.save"), on_click=lambda: dialog.submit(name_input.value)
                        ).props("color=primary")
                profile_name = await dialog
                if profile_name:
                    try:
                        cfg = form_to_config(state["form"])
                        profile_path = profiles_dir / f"{profile_name}.yaml"
                        with profile_path.open("w", encoding="utf-8") as f:
                            yaml.dump(cfg.to_dict(), f, sort_keys=False, allow_unicode=True)
                        ui.notify(t("notify.profile_saved"), type="positive")
                        await ui.run_javascript("location.reload()")
                    except Exception as e:
                        ui.notify(f"{t('notify.save_failed')}: {e}", type="negative")

            async def load_profile(profile_name: str) -> None:
                if not profile_name:
                    return
                try:
                    from ..core import BotConfig

                    profile_path = profile_files[profile_name]
                    with profile_path.open("r", encoding="utf-8") as f:
                        new_data = yaml.safe_load(f)
                    state["form"] = config_to_form(BotConfig(**new_data))
                    ui.notify(t("notify.profile_loaded"), type="positive")
                    await ui.run_javascript("location.reload()")
                except Exception as e:
                    ui.notify(f"{t('notify.load_failed')}: {e}", type="negative")

            ui.button(t("sidebar.save_profile"), on_click=save_profile).props(
                "flat dense size=sm"
            ).classes("w-full justify-start")
            if profile_files:
                ui.select(
                    list(profile_files.keys()),
                    label=t("sidebar.load_profile"),
                    on_change=lambda e: load_profile(e.value),
                ).props("dense outlined").classes("w-full mt-1")

            # Import/Export section
            ui.label(t("sidebar.import_export")).classes("sidebar-category mt-4 mb-2 px-2")

            async def on_upload(e: Any) -> None:
                try:
                    from ..core import BotConfig

                    content = e.content.read().decode("utf-8")
                    new_data = yaml.safe_load(content)
                    if not isinstance(new_data, dict):
                        raise ValueError("Invalid YAML format")
                    state["form"] = config_to_form(BotConfig(**new_data))
                    ui.notify(t("notify.config_imported"), type="positive")
                    await ui.run_javascript("location.reload()")
                except Exception as ex:
                    ui.notify(f"{t('notify.import_failed')}: {ex}", type="negative")

            ui.upload(on_upload=on_upload, auto_upload=True).props("flat dense").classes("w-full")

            def on_export() -> None:
                try:
                    cfg = form_to_config(state["form"])
                    yaml_str = yaml.dump(cfg.to_dict(), sort_keys=False, allow_unicode=True)
                    ui.download(yaml_str.encode("utf-8"), "config.yaml")
                    ui.notify(t("notify.config_exported"), type="positive")
                except Exception as ex:
                    ui.notify(f"{t('notify.export_failed')}: {ex}", type="negative")

            ui.button(t("sidebar.export_config"), on_click=on_export).props(
                "flat dense size=sm"
            ).classes("w-full justify-start mt-1")

        # Right main content area
        main_content = ui.element("div").classes("main-content")

    # Build content based on current page
    rebuild_webhooks_ref: list = []

    def rebuild_content() -> None:
        main_content.clear()
        with main_content, ui.column().classes("w-full gap-4"):
            page_id = state["current_page"]

            if page_id == "overview":
                build_overview_page(controller, state)
            elif page_id == "general" or page_id == "webhooks":
                build_general_page(state, rebuild_webhooks_ref)
            elif page_id == "scheduler":
                build_scheduler_page(state, controller)
            elif page_id == "plugins":
                build_plugins_page(state, controller)
            elif page_id == "logging":
                build_logging_page(state, controller)
            elif page_id == "templates":
                build_templates_page(state)
            elif page_id == "notifications":
                build_notifications_page(state)
            elif page_id == "status":
                build_status_page(state, controller)
            elif page_id == "ai":
                build_ai_dashboard_page(state, controller)
            elif page_id == "tasks":
                build_tasks_page(controller)
            elif page_id == "automation":
                build_automation_page(controller, state)
            elif page_id == "providers":
                build_providers_page(controller, state)
            elif page_id == "feishu":
                build_feishu_page(controller, state)
            elif page_id == "qq":
                build_qq_page(controller, state)
            elif page_id == "bridge":
                build_bridge_page(controller, state)
            elif page_id == "messages":
                build_messages_page(controller)
            elif page_id == "auth":
                build_auth_page(controller, state)
            elif page_id == "events":
                build_events_page(controller)
            elif page_id == "logs":
                build_logs_page(controller)

    rebuild_content()

    # Status chip updater
    def update_status_chip() -> None:
        s = controller.status()
        if s["running"]:
            status_chip.text = t("app.status.running")
            status_chip.props(remove="outline").update()
            status_chip.props("color=green text-color=white")
        else:
            status_chip.text = t("app.status.stopped")
            status_chip.props(add="outline").update()
            status_chip.props("color=grey text-color=white")

    ui.timer(1.5, update_status_chip)


def build_overview_page(controller: BotController, state: dict[str, Any]) -> None:
    """Build the overview/dashboard page."""
    # Page header with welcome message
    with ui.column().classes("w-full mb-4 sm:mb-8"):
        ui.label(t("dashboard.title")).classes("text-xl sm:text-3xl font-bold text-gray-800")
        ui.label(t("dashboard.welcome_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Status cards - full width grid layout
    with ui.element("div").classes(
        "grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6 mb-4 sm:mb-8 w-full"
    ):
        # Bot status card
        status = controller.status()
        with ui.card().classes(
            "p-3 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow"
        ):
            with ui.column().classes("gap-1 sm:gap-2 w-full"):
                color = "green" if status["running"] else "gray"
                with ui.row().classes("items-center gap-2 sm:justify-between w-full"):
                    with ui.element("div").classes(
                        f"w-8 h-8 sm:w-14 sm:h-14 rounded-full bg-{color}-100 flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon("power_settings_new", size="sm").classes(
                            f"text-{color}-600 sm:text-lg"
                        )
                    ui.label(t("dashboard.bot_status")).classes(
                        "text-xs sm:text-sm text-gray-500 font-medium truncate"
                    )
                ui.label(
                    t("app.status.running") if status["running"] else t("app.status.stopped")
                ).classes("text-lg sm:text-2xl font-bold text-gray-800")

        # Scheduler status
        with ui.card().classes(
            "p-3 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow"
        ):
            with ui.column().classes("gap-1 sm:gap-2 w-full"):
                color = "blue" if status["scheduler_running"] else "gray"
                with ui.row().classes("items-center gap-2 sm:justify-between w-full"):
                    with ui.element("div").classes(
                        f"w-8 h-8 sm:w-14 sm:h-14 rounded-full bg-{color}-100 flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon("schedule", size="sm").classes(f"text-{color}-600 sm:text-lg")
                    ui.label(t("dashboard.scheduler")).classes(
                        "text-xs sm:text-sm text-gray-500 font-medium truncate"
                    )
                ui.label(
                    t("dashboard.active")
                    if status["scheduler_running"]
                    else t("dashboard.inactive")
                ).classes("text-lg sm:text-2xl font-bold text-gray-800")

        # AI status
        ai_stats = controller.get_ai_stats()
        with ui.card().classes(
            "p-3 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow"
        ):
            with ui.column().classes("gap-1 sm:gap-2 w-full"):
                color = "purple" if ai_stats["enabled"] else "gray"
                with ui.row().classes("items-center gap-2 sm:justify-between w-full"):
                    with ui.element("div").classes(
                        f"w-8 h-8 sm:w-14 sm:h-14 rounded-full bg-{color}-100 flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon("smart_toy", size="sm").classes(f"text-{color}-600 sm:text-lg")
                    ui.label(t("dashboard.ai_agent")).classes(
                        "text-xs sm:text-sm text-gray-500 font-medium truncate"
                    )
                ui.label(
                    t("dashboard.enabled") if ai_stats["enabled"] else t("dashboard.disabled")
                ).classes("text-lg sm:text-2xl font-bold text-gray-800")

        # Message stats
        msg_stats = controller.get_message_stats()
        with ui.card().classes(
            "p-3 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow"
        ):
            with ui.column().classes("gap-1 sm:gap-2 w-full"):
                with ui.row().classes("items-center gap-2 sm:justify-between w-full"):
                    with ui.element("div").classes(
                        "w-8 h-8 sm:w-14 sm:h-14 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon("mail", size="sm").classes("text-blue-600 sm:text-lg")
                    ui.label(t("dashboard.messages")).classes(
                        "text-xs sm:text-sm text-gray-500 font-medium truncate"
                    )
                with ui.row().classes("items-baseline gap-1"):
                    ui.label(str(msg_stats["success"])).classes(
                        "text-lg sm:text-2xl font-bold text-gray-800"
                    )
                    ui.label(t("dashboard.sent")).classes("text-xs text-gray-400")

    # Two column layout for quick actions and plugins
    with ui.element("div").classes(
        "grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-8 w-full"
    ):
        # Quick actions card
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("dashboard.quick_actions")).classes(
                "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
            )
            with ui.element("div").classes("grid grid-cols-3 gap-2 sm:gap-4"):

                async def on_send_test_click() -> None:
                    state["current_page"] = "general"
                    await ui.run_javascript("location.reload()")

                async def on_reload_config_click() -> None:
                    try:
                        cfg = controller.load_config()
                        state["form"] = config_to_form(cfg)
                        ui.notify(t("notify.config_reloaded"), type="positive")
                    except Exception as e:
                        ui.notify(f"{t('common.error')}: {e}", type="negative")

                async def on_view_logs_click() -> None:
                    state["current_page"] = "logs"
                    await ui.run_javascript("location.reload()")

                with (
                    ui.card()
                    .classes(
                        "p-3 sm:p-5 bg-gradient-to-br from-blue-50 to-blue-100 border-0 rounded-xl cursor-pointer hover:from-blue-100 hover:to-blue-200 transition-all"
                    )
                    .on("click", on_send_test_click)
                ):
                    with ui.column().classes("items-center gap-2 sm:gap-3"):
                        with ui.element("div").classes(
                            "w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-blue-500 flex items-center justify-center"
                        ):
                            ui.icon("send", size="sm").classes("text-white")
                        ui.label(t("dashboard.send_test")).classes(
                            "text-xs sm:text-sm font-medium text-blue-700 text-center"
                        )

                with (
                    ui.card()
                    .classes(
                        "p-3 sm:p-5 bg-gradient-to-br from-green-50 to-green-100 border-0 rounded-xl cursor-pointer hover:from-green-100 hover:to-green-200 transition-all"
                    )
                    .on("click", on_reload_config_click)
                ):
                    with ui.column().classes("items-center gap-2 sm:gap-3"):
                        with ui.element("div").classes(
                            "w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-green-500 flex items-center justify-center"
                        ):
                            ui.icon("refresh", size="sm").classes("text-white")
                        ui.label(t("dashboard.reload_config")).classes(
                            "text-xs sm:text-sm font-medium text-green-700 text-center"
                        )

                with (
                    ui.card()
                    .classes(
                        "p-3 sm:p-5 bg-gradient-to-br from-gray-50 to-gray-100 border-0 rounded-xl cursor-pointer hover:from-gray-100 hover:to-gray-200 transition-all"
                    )
                    .on("click", on_view_logs_click)
                ):
                    with ui.column().classes("items-center gap-2 sm:gap-3"):
                        with ui.element("div").classes(
                            "w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gray-500 flex items-center justify-center"
                        ):
                            ui.icon("terminal", size="sm").classes("text-white")
                        ui.label(t("dashboard.view_logs")).classes(
                            "text-xs sm:text-sm font-medium text-gray-700 text-center"
                        )

        # Active plugins card
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("dashboard.active_plugins")).classes(
                "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
            )
            status = controller.status()
            if status["plugins"]:
                with ui.row().classes("gap-2 sm:gap-3 flex-wrap"):
                    for plugin in status["plugins"]:
                        ui.chip(plugin, color="blue").classes(
                            "text-xs sm:text-sm px-2 sm:px-4 py-1 sm:py-2"
                        )
            else:
                with ui.column().classes("items-center justify-center py-4 sm:py-8"):
                    ui.icon("extension_off", size="lg").classes("text-gray-300 mb-2 sm:mb-3")
                    ui.label(t("dashboard.no_plugins")).classes(
                        "text-sm sm:text-base text-gray-400"
                    )

    # Config summary - full width with better stats display
    with ui.card().classes(
        "p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm w-full"
    ):
        ui.label(t("dashboard.config_summary")).classes(
            "text-base sm:text-lg font-semibold text-gray-800 mb-4 sm:mb-6"
        )
        webhooks = state["form"].get("webhooks", [])
        templates = state["form"].get("templates", [])
        notifications = state["form"].get("notifications", [])
        with ui.element("div").classes("grid grid-cols-3 gap-2 sm:gap-8"):
            with ui.column().classes(
                "items-center gap-1 sm:gap-2 p-2 sm:p-4 bg-blue-50 rounded-xl"
            ):
                ui.label(str(len(webhooks))).classes("text-2xl sm:text-4xl font-bold text-blue-600")
                ui.label(t("nav.webhooks")).classes(
                    "text-xs sm:text-sm text-blue-700 font-medium text-center"
                )
            with ui.column().classes(
                "items-center gap-1 sm:gap-2 p-2 sm:p-4 bg-green-50 rounded-xl"
            ):
                ui.label(str(len(templates))).classes(
                    "text-2xl sm:text-4xl font-bold text-green-600"
                )
                ui.label(t("nav.templates")).classes(
                    "text-xs sm:text-sm text-green-700 font-medium text-center"
                )
            with ui.column().classes(
                "items-center gap-1 sm:gap-2 p-2 sm:p-4 bg-orange-50 rounded-xl"
            ):
                ui.label(str(len(notifications))).classes(
                    "text-2xl sm:text-4xl font-bold text-orange-600"
                )
                ui.label(t("nav.notifications")).classes(
                    "text-xs sm:text-sm text-orange-700 font-medium text-center"
                )


def run_ui(
    config_path: str | Path = "config.yaml", host: str = "127.0.0.1", port: int = 8080
) -> None:
    """Start the NiceGUI app."""
    path = Path(config_path)

    def root() -> None:
        build_ui(path)

    async def on_shutdown() -> None:
        logging.getLogger().info("Shutting down web UI...")

    app.on_shutdown(on_shutdown)
    ui.run(root, host=host, port=port, show=False, reload=False, title="Feishu Webhook Bot")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", default="config.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    run_ui(args.config, args.host, args.port)
