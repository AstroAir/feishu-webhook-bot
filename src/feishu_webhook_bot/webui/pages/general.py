# ruff: noqa: E501
"""General configuration page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..components import build_list_editor, webhook_card
from ..i18n import t


def build_general_page(state: dict[str, Any], rebuild_webhooks_ref: list) -> None:
    """Build the General configuration page."""
    general = state["form"].setdefault("general", {})
    webhook_list: list[dict[str, Any]] = state["form"].setdefault("webhooks", [])

    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("general.basic_settings")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("general.basic_settings_desc")).classes(
            "text-sm sm:text-base text-gray-500 mt-1"
        )

    # Stats cards
    bot_name = general.get("name", "")
    has_description = bool(general.get("description", "").strip())
    default_webhook = next((w for w in webhook_list if w.get("name") == "default"), None)

    with ui.element("div").classes(
        "grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Bot name status
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("smart_toy", size="md").classes("text-blue-600")
                ui.label(bot_name if bot_name else t("general.not_set")).classes(
                    "text-xs sm:text-sm text-blue-700 text-center truncate w-full"
                )

        # Description status
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("check_circle" if has_description else "cancel", size="md").classes(
                    f"text-{'green' if has_description else 'gray'}-600"
                )
                ui.label(t("general.description_status")).classes(
                    "text-xs sm:text-sm text-green-700 text-center"
                )

        # Webhooks count
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(webhook_list))).classes(
                    "text-xl sm:text-2xl font-bold text-purple-600"
                )
                ui.label(t("general.webhooks_count")).classes(
                    "text-xs sm:text-sm text-purple-700 text-center"
                )

        # Default webhook
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.icon("check_circle" if default_webhook else "cancel", size="md").classes(
                    f"text-{'green' if default_webhook else 'gray'}-600"
                )
                ui.label(t("general.default_webhook")).classes(
                    "text-xs sm:text-sm text-orange-700 text-center"
                )

    # Basic settings card
    with (
        ui.card().classes(
            "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
        ),
        ui.column().classes("gap-4 w-full"),
    ):
        ui.input(t("general.bot_name")).bind_value(general, "name").classes(
            "w-full max-w-lg"
        ).props("outlined")
        ui.textarea(t("general.bot_description")).bind_value(general, "description").classes(
            "w-full"
        ).props("outlined auto-grow rows=4")

    # Webhook endpoints section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("general.webhook_endpoints")).classes(
            "text-lg sm:text-xl font-semibold text-gray-800"
        )
        ui.label(t("general.webhook_endpoints_desc")).classes(
            "text-sm sm:text-base text-gray-500 mt-1"
        )

    webhook_list: list[dict[str, Any]] = state["form"].setdefault("webhooks", [])
    rebuild_webhooks = build_list_editor(
        item_list=webhook_list,
        card_builder=webhook_card,
        default_item={"name": "default", "url": "", "secret": None},
        add_button_text=t("general.add_webhook"),
    )
    rebuild_webhooks_ref.append(rebuild_webhooks)

    def set_default_to_first() -> None:
        if not webhook_list:
            return
        for wh in webhook_list:
            if wh.get("name") == "default":
                wh["name"] = f"wh_{id(wh) % 1000}"
        webhook_list[0]["name"] = "default"
        rebuild_webhooks()
        ui.notify(t("notify.config_saved"), type="positive")

    with ui.row().classes("mt-4"):
        ui.button(t("general.set_first_default"), on_click=set_default_to_first).props(
            "outline color=grey-7"
        )
