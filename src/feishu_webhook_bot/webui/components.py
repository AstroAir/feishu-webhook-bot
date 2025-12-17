# ruff: noqa: E501
"""Reusable UI components for the WebUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from ..core import BotConfig
from .i18n import t


def config_to_form(cfg: BotConfig) -> dict[str, Any]:
    """Convert BotConfig to form data dictionary."""
    data = cfg.to_dict()
    data.setdefault("general", {})
    data.setdefault("webhooks", [])
    data.setdefault("scheduler", {})
    data.setdefault("plugins", {})
    data.setdefault("logging", {})
    data.setdefault("templates", [])
    data.setdefault("notifications", [])
    return data


def form_to_config(data: dict[str, Any]) -> BotConfig:
    """Convert form data to BotConfig with validation."""
    return BotConfig(**data)


def webhook_card(item: dict[str, Any], on_remove: Callable[[], None] | None = None) -> None:
    """Render a webhook configuration card."""
    with ui.card().classes("w-full p-3 sm:p-4 bg-white rounded-lg border border-gray-200"):
        grid = ui.element("div").classes(
            "grid grid-cols-12 gap-x-2 sm:gap-x-4 gap-y-2 sm:gap-y-3 w-full items-end md:items-center"
        )
        with grid:
            ui.input(
                t("general.name"),
                validation={t("common.required"): lambda v: bool(v and v.strip())},
            ).bind_value(item, "name").props("dense outlined").classes(
                "col-span-12 md:col-span-4 lg:col-span-3"
            )
            ui.input(
                t("general.url"),
                validation={
                    t("common.required"): lambda v: bool(v and v.strip()),
                    "Must start with http(s)": lambda v: (v or "").startswith("http"),
                },
            ).bind_value(item, "url").props("dense outlined").classes(
                "col-span-12 md:col-span-8 lg:col-span-6"
            )
            ui.input(t("general.secret")).bind_value(item, "secret").props(
                "dense outlined"
            ).classes("col-span-12 lg:col-span-2")
            if on_remove:
                with ui.element("div").classes(
                    "col-span-12 lg:col-span-1 flex justify-end lg:justify-center items-center"
                ):
                    ui.button(icon="delete", color="red", on_click=lambda: on_remove()).props(
                        "flat round dense"
                    )


TEMPLATE_TYPES = ["text", "markdown", "card", "post", "interactive", "json"]


def template_card(item: dict[str, Any], on_remove: Callable[[], None] | None = None) -> None:
    """Render a template configuration card."""
    item.setdefault("name", "new-template")
    item.setdefault("type", "text")
    item.setdefault("engine", "string")
    item.setdefault("description", "")
    item.setdefault("content", "")

    with ui.card().classes(
        "w-full p-3 sm:p-4 bg-white rounded-lg border border-gray-200 gap-2 sm:gap-3"
    ):
        with ui.row().classes("items-end gap-2 sm:gap-3 flex-wrap"):
            ui.input(
                t("templates.name"),
                validation={t("common.required"): lambda v: bool(v and v.strip())},
            ).bind_value(item, "name").props("dense outlined")
            ui.select(TEMPLATE_TYPES, label=t("templates.type")).bind_value(item, "type").props(
                "dense outlined"
            )
            ui.select(["string", "format"], label=t("templates.engine")).bind_value(
                item, "engine"
            ).props("dense outlined")
            ui.input(t("templates.description")).bind_value(item, "description").props(
                "dense outlined"
            ).classes("grow")
            if on_remove:
                ui.button(icon="delete", color="red", on_click=lambda: on_remove()).props(
                    "flat round dense"
                )

        ui.textarea(t("templates.content")).bind_value(item, "content").classes("w-full").props(
            "outlined auto-grow"
        )


def notification_card(item: dict[str, Any], on_remove: Callable[[], None] | None = None) -> None:
    """Render a notification rule card."""
    item.setdefault("name", "new-notification")
    item.setdefault("trigger", "")
    item.setdefault("conditions", [])
    item.setdefault("template", "")

    with ui.card().classes(
        "w-full p-3 sm:p-4 bg-white rounded-lg border border-gray-200 gap-2 sm:gap-3"
    ):
        with ui.row().classes("items-end gap-2 sm:gap-3 flex-wrap"):
            ui.input(
                t("notifications.name"),
                validation={t("common.required"): lambda v: bool(v and v.strip())},
            ).bind_value(item, "name").props("dense outlined")
            ui.input(t("notifications.trigger"), placeholder="e.g. event.message").bind_value(
                item, "trigger"
            ).props("dense outlined")
            ui.input(t("notifications.template")).bind_value(item, "template").props(
                "dense outlined"
            )
            if on_remove:
                ui.button(icon="delete", color="red", on_click=lambda: on_remove()).props(
                    "flat round dense"
                )

        conditions_box = (
            ui.textarea(t("notifications.conditions"))
            .classes("w-full")
            .props("outlined autocomplete=off auto-grow")
        )
        conditions_box.value = "\n".join(item.get("conditions", []))

        def _update_conditions(event: Any) -> None:
            lines = [line.strip() for line in (event.value or "").splitlines() if line.strip()]
            item["conditions"] = lines

        conditions_box.on("change", _update_conditions)


def build_list_editor(
    item_list: list[dict[str, Any]],
    card_builder: Callable[[dict[str, Any], Callable[[], None] | None], None],
    default_item: dict[str, Any],
    add_button_text: str,
) -> Callable[[], None]:
    """Build a generic UI for editing a list of items in cards."""
    container = ui.column().classes("w-full gap-3")

    def rebuild() -> None:
        container.clear()
        with container:
            for idx, item in enumerate(item_list):

                def remove_item(i: int = idx) -> None:
                    item_list.pop(i)
                    rebuild()

                card_builder(item, remove_item)

    rebuild()

    with ui.row().classes("items-center gap-2 flex-wrap pt-2"):

        def add_and_rebuild() -> None:
            item_list.append(default_item.copy())
            rebuild()

        ui.button(
            add_button_text,
            on_click=add_and_rebuild,
        ).props("outline color=primary")

    return rebuild


def stat_card(title: str, value: str | int, icon: str = "info", color: str = "blue") -> None:
    """Render a statistics card for the dashboard."""
    with ui.card().classes("p-3 sm:p-4 bg-white border border-gray-200 rounded-lg"):
        with ui.row().classes("items-center gap-2 sm:gap-3"):
            ui.icon(icon, size="sm").classes(f"text-{color}-500")
            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-xs text-gray-500 uppercase tracking-wide")
                ui.label(str(value)).classes("text-lg sm:text-xl font-semibold text-gray-800")


def section_header(title: str, description: str = "") -> None:
    """Render a section header."""
    with ui.column().classes("gap-1 mb-2 sm:mb-3"):
        ui.label(title).classes("text-base sm:text-lg font-semibold text-gray-800")
        if description:
            ui.label(description).classes("text-xs sm:text-sm text-gray-500")
