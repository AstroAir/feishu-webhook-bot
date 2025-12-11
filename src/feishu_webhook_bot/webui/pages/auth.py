# ruff: noqa: E501
"""Auth management page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_auth_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the Auth management page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("auth.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("auth.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Get user stats
    users = controller.get_user_list()
    active_users = len([u for u in users if u.get("status") == "Active"])
    locked_users = len([u for u in users if u.get("status") == "Locked"])

    # Stats cards
    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"):
        # Total users
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(users))).classes("text-xl sm:text-2xl font-bold text-blue-600")
                ui.label(t("auth.total_users")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Active users
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(active_users)).classes("text-xl sm:text-2xl font-bold text-green-600")
                ui.label(t("auth.active_users")).classes("text-xs sm:text-sm text-green-700 text-center")

        # Locked users
        with ui.card().classes("p-3 sm:p-4 bg-red-50 border border-red-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(locked_users)).classes("text-xl sm:text-2xl font-bold text-red-600")
                ui.label(t("auth.locked_users")).classes("text-xs sm:text-sm text-red-700 text-center")

        # Auth status
        auth_enabled = state["form"].get("auth", {}).get("enabled", False) if state else False
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("check_circle" if auth_enabled else "cancel", size="md").classes(f"text-{'green' if auth_enabled else 'gray'}-600")
                ui.label(t("auth.auth_status")).classes("text-xs sm:text-sm text-purple-700 text-center")

    # Auth configuration section
    if state is not None:
        cfg_auth = state["form"].setdefault("auth", {})
        # Initialize default values if not present
        cfg_auth.setdefault("enabled", False)
        cfg_auth.setdefault("database_url", "sqlite:///./auth.db")
        cfg_auth.setdefault("jwt_secret_key", "")
        cfg_auth.setdefault("access_token_expire_minutes", 30)
        cfg_auth.setdefault("max_failed_attempts", 5)
        cfg_auth.setdefault("lockout_duration_minutes", 30)
        cfg_auth.setdefault("require_email_verification", False)

        with ui.column().classes("w-full mb-3 sm:mb-4"):
            ui.label(t("auth.configuration")).classes("text-lg sm:text-xl font-semibold text-gray-800")
            ui.label(t("auth.configuration_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

        with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6 w-full"):
            # Basic auth settings
            with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
                ui.label(t("auth.basic_settings")).classes("text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4")
                with ui.column().classes("gap-4 w-full"):
                    ui.switch(t("auth.enabled")).bind_value(cfg_auth, "enabled")
                    ui.input(t("auth.database_url")).bind_value(cfg_auth, "database_url").props("outlined").classes("w-full").tooltip(t("auth.database_url_hint"))
                    ui.input(t("auth.jwt_secret")).bind_value(cfg_auth, "jwt_secret_key").props("type=password outlined").classes("w-full")

            # Security settings
            with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
                ui.label(t("auth.security_settings")).classes("text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4")
                with ui.column().classes("gap-4 w-full"):
                    ui.number(t("auth.token_expire"), min=1, max=1440).bind_value(cfg_auth, "access_token_expire_minutes").props("outlined").classes("w-full")
                    ui.number(t("auth.max_failed_attempts"), min=1, max=20).bind_value(cfg_auth, "max_failed_attempts").props("outlined").classes("w-full")
                    ui.number(t("auth.lockout_duration"), min=1, max=1440).bind_value(cfg_auth, "lockout_duration_minutes").props("outlined").classes("w-full")
                    ui.switch(t("auth.require_email_verification")).bind_value(cfg_auth, "require_email_verification")

    # User management section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("auth.user_management")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("auth.user_management_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")
    
    # Two column layout
    with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 w-full"):
        # User list card - takes 2 columns
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm lg:col-span-2"):
            with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
                ui.label(t("auth.user_management")).classes("text-base sm:text-lg font-semibold text-gray-800")
                ui.button(icon="refresh", on_click=lambda: rebuild_users()).props("flat round dense")
            users_container = ui.column().classes("gap-3 w-full")

            def rebuild_users() -> None:
                users_container.clear()
                with users_container:
                    users = controller.get_user_list()
                    if not users:
                        with ui.column().classes("items-center py-12"):
                            ui.icon("people_outline", size="xl").classes("text-gray-300 mb-3")
                            ui.label(t("auth.no_users")).classes("text-gray-400 text-lg")
                        return

                    # User cards
                    for user in users:
                        with ui.card().classes("w-full p-4 bg-gray-50 border border-gray-100 rounded-lg hover:bg-gray-100 transition-colors"):
                            with ui.row().classes("w-full items-center justify-between"):
                                with ui.row().classes("items-center gap-4"):
                                    with ui.element("div").classes("w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center"):
                                        ui.icon("person", size="sm").classes("text-blue-600")
                                    with ui.column().classes("gap-0"):
                                        ui.label(user.get("username", "N/A")).classes("font-semibold text-gray-800")
                                        ui.label(user.get("email", "N/A")).classes("text-sm text-gray-500")
                                with ui.row().classes("items-center gap-3"):
                                    status_color = "green" if user.get("status") == "Active" else "red"
                                    ui.chip(user.get("status", "Unknown"), color=status_color)

                                    def on_unlock(user_id: int = user["id"]) -> None:
                                        try:
                                            from ...auth.service import AuthService
                                            auth_service = AuthService()
                                            auth_service.unlock_user(user_id)
                                            ui.notify(t("common.success"), type="positive")
                                            rebuild_users()
                                        except Exception as e:
                                            ui.notify(f"{t('common.error')}: {e}", type="negative")

                                    ui.button(t("auth.unlock"), on_click=on_unlock).props("dense outline")

            rebuild_users()

        # Register user card
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("auth.register_user")).classes("text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4")
            with ui.column().classes("gap-4 w-full"):
                reg_username = ui.input(t("auth.username")).props("outlined clearable").classes("w-full")
                reg_email = ui.input(t("auth.email"), validation={t("auth.email"): lambda v: "@" in (v or "")}).props("outlined clearable").classes("w-full")
                reg_password = ui.input(t("auth.password")).props("type=password outlined clearable").classes("w-full")

                async def register_user() -> None:
                    if not all([reg_username.value, reg_email.value, reg_password.value]):
                        ui.notify(t("common.warning"), type="warning")
                        return
                    try:
                        from ...auth.service import AuthService
                        auth_service = AuthService()
                        auth_service.register_user(reg_username.value, reg_email.value, reg_password.value)
                        ui.notify(t("common.success"), type="positive")
                        reg_username.value = ""
                        reg_email.value = ""
                        reg_password.value = ""
                    except Exception as e:
                        ui.notify(f"{t('common.error')}: {e}", type="negative")

                ui.button(t("auth.register"), on_click=register_user, icon="person_add").props("color=primary").classes("w-full")
