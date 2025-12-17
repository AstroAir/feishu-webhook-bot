# ruff: noqa: E501
"""Shared components for provider pages (Feishu/QQ).

This module provides reusable UI components for both Feishu and QQ provider pages,
ensuring consistent layout and behavior while allowing platform-specific customization.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_stats_cards(
    stats: list[dict[str, Any]],
    columns: int = 4,
) -> None:
    """Build a row of statistics cards.

    Args:
        stats: List of stat dicts with keys: value, label, color, icon
        columns: Number of columns in the grid
    """
    with ui.element("div").classes(
        f"grid grid-cols-2 sm:grid-cols-{columns} gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        for stat in stats:
            color = stat.get("color", "blue")
            with (
                ui.card().classes(f"p-3 sm:p-4 bg-{color}-50 border border-{color}-100 rounded-xl"),
                ui.column().classes("items-center gap-1"),
            ):
                ui.label(str(stat.get("value", 0))).classes(
                    f"text-xl sm:text-2xl font-bold text-{color}-600"
                )
                ui.label(stat.get("label", "")).classes(
                    f"text-xs sm:text-sm text-{color}-700 text-center"
                )


def build_page_header(title: str, description: str) -> None:
    """Build a page header with title and description.

    Args:
        title: Page title
        description: Page description
    """
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(title).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(description).classes("text-sm sm:text-base text-gray-500 mt-1")


def build_section_header(title: str, description: str | None = None) -> None:
    """Build a section header.

    Args:
        title: Section title
        description: Optional section description
    """
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(title).classes("text-lg sm:text-xl font-semibold text-gray-800")
        if description:
            ui.label(description).classes("text-sm sm:text-base text-gray-500 mt-1")


def build_empty_state(icon: str, message: str) -> None:
    """Build an empty state placeholder.

    Args:
        icon: Material icon name
        message: Message to display
    """
    with ui.column().classes("items-center py-8"):
        ui.icon(icon, size="xl").classes("text-gray-300 mb-2")
        ui.label(message).classes("text-gray-400")


def build_provider_status_card(
    provider: dict[str, Any],
    platform_icon: str,
    platform_color: str,
    on_test: Callable[[], None] | None = None,
    on_send_test: Callable[[], None] | None = None,
) -> None:
    """Build a provider status card.

    Args:
        provider: Provider info dict
        platform_icon: Material icon for the platform
        platform_color: Color theme for the platform
        on_test: Optional callback for test connection
        on_send_test: Optional callback for send test message
    """
    with ui.row().classes("w-full items-center justify-between p-3 bg-gray-50 rounded-lg"):
        with ui.row().classes("items-center gap-3"):
            ui.icon(platform_icon).classes(f"text-{platform_color}-600")
            with ui.column().classes("gap-0"):
                ui.label(provider.get("name", "Unknown")).classes("font-medium text-gray-800")
                ui.label(f"Type: {provider.get('type', 'Unknown')}").classes(
                    "text-sm text-gray-500"
                )

        with ui.row().classes("items-center gap-2"):
            status = provider.get("status", "unknown")
            status_color = "green" if status == "Connected" else "gray"
            ui.chip(status, color=status_color).props("dense")

            if on_test:
                ui.button(t("providers.test"), on_click=on_test).props("dense outline")
            if on_send_test:
                ui.button(t("providers.send_test"), on_click=on_send_test).props(
                    "dense outline color=primary"
                )


def build_message_send_form(
    platform: str,
    targets: list[str],
    on_send: Callable[[str, str], None],
    support_image: bool = False,
    support_at: bool = False,
) -> None:
    """Build a message send form.

    Args:
        platform: Platform name (feishu/qq)
        targets: List of available targets
        on_send: Callback with (message, target) when send is clicked
        support_image: Whether to show image URL input
        support_at: Whether to show @mention input
    """
    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"
    ):
        build_section_header(
            t(f"{platform}.send_test_title"),
            t(f"{platform}.send_test_desc"),
        )

        message_input = (
            ui.textarea(
                t("common.message"),
                placeholder=t(f"{platform}.message_placeholder"),
            )
            .props("outlined")
            .classes("w-full mb-3")
        )

        with ui.row().classes("gap-3 w-full items-end"):
            if targets:
                target_select = (
                    ui.select(
                        targets,
                        label=t("common.target"),
                        value=targets[0] if targets else "",
                    )
                    .props("outlined dense")
                    .classes("flex-1")
                )
            else:
                target_input = (
                    ui.input(
                        t("common.target"),
                        placeholder=t(f"{platform}.target_placeholder"),
                    )
                    .props("outlined dense")
                    .classes("flex-1")
                )

            if support_image:
                ui.input(
                    t("common.image_url"),
                    placeholder="https://...",
                ).props("outlined dense").classes("w-48")

            if support_at:
                ui.input(
                    t("qq.at_user"),
                    placeholder="QQ号",
                ).props("outlined dense").classes("w-32")

            def do_send():
                msg = message_input.value
                tgt = target_select.value if targets else target_input.value
                if msg and tgt:
                    on_send(msg, tgt)
                    message_input.value = ""
                else:
                    ui.notify(t("common.fill_required"), type="warning")

            ui.button(t("common.send"), on_click=do_send, icon="send").props("color=primary")


def build_config_card(
    title: str,
    fields: list[dict[str, Any]],
    data: dict[str, Any],
    on_delete: Callable[[], None] | None = None,
    border_color: str = "blue",
    icon: str = "settings",
) -> None:
    """Build a configuration card with fields.

    Args:
        title: Card title
        fields: List of field definitions
        data: Data dict to bind values to
        on_delete: Optional delete callback
        border_color: Border color theme
        icon: Material icon
    """
    with ui.card().classes(
        f"w-full p-4 bg-gray-50 border-l-4 border-{border_color}-500 rounded-lg"
    ):
        # Header
        with ui.row().classes("items-center justify-between mb-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon(icon).classes(f"text-{border_color}-600")
                ui.label(title).classes("font-medium")

            if on_delete:
                ui.button(icon="delete", on_click=on_delete).props("flat round color=red dense")

        # Fields
        for field in fields:
            field_type = field.get("type", "input")
            key = field.get("key")
            label = field.get("label", key)
            props = field.get("props", "outlined dense")
            classes = field.get("classes", "flex-1")

            if field.get("row_start", False):
                row = ui.row().classes("gap-3 w-full mb-2")
                row.__enter__()

            if field_type == "input":
                ui.input(label).bind_value(data, key).props(props).classes(classes)
            elif field_type == "password":
                ui.input(label).bind_value(data, key).props(f"type=password {props}").classes(
                    classes
                )
            elif field_type == "number":
                ui.number(label, min=field.get("min", 0), max=field.get("max", 9999)).bind_value(
                    data, key
                ).props(props).classes(classes)
            elif field_type == "switch":
                ui.switch(label).bind_value(data, key)
            elif field_type == "select":
                ui.select(field.get("options", []), label=label).bind_value(data, key).props(
                    props
                ).classes(classes)
            elif field_type == "hint":
                ui.label(label).classes("text-xs text-gray-400 self-center")

            if field.get("row_end", False):
                row.__exit__(None, None, None)


def build_connection_test_button(
    controller: BotController,
    provider_name: str,
    platform: str,
) -> None:
    """Build a connection test button for a provider.

    Args:
        controller: Bot controller instance
        provider_name: Name of the provider to test
        platform: Platform name for i18n
    """

    async def on_test():
        try:
            ui.notify(t("common.testing"), type="info")
            if controller.bot and controller.bot.get_provider(provider_name):
                ui.notify(t("common.connection_success"), type="positive")
            else:
                ui.notify(t("common.connection_failed"), type="warning")
        except Exception as e:
            ui.notify(f"{t('common.error')}: {e}", type="negative")

    ui.button(
        t(f"{platform}.test_connection"),
        on_click=on_test,
        icon="wifi_tethering",
    ).props("outline")
