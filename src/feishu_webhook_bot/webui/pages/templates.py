# ruff: noqa: E501
"""Templates configuration page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..components import build_list_editor, template_card
from ..i18n import t

# Template type descriptions
TEMPLATE_TYPE_INFO = {
    "text": "纯文本消息，支持简单的变量替换",
    "markdown": "Markdown 格式消息，支持富文本",
    "card": "卡片消息，支持复杂的交互式布局",
    "post": "富文本消息，支持图文混排",
    "interactive": "交互式消息，支持按钮和表单",
    "json": "自定义 JSON 格式消息",
}


def build_templates_page(state: dict[str, Any]) -> None:
    """Build the Templates configuration page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("templates.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("templates.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    template_list: list[dict[str, Any]] = state["form"].setdefault("templates", [])

    # Stats cards
    with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"):
        # Total templates
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(template_list))).classes("text-xl sm:text-2xl font-bold text-blue-600")
                ui.label(t("templates.total")).classes("text-xs sm:text-sm text-blue-700 text-center")

        # Text templates
        text_count = len([t for t in template_list if t.get("type") == "text"])
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(text_count)).classes("text-xl sm:text-2xl font-bold text-green-600")
                ui.label("Text").classes("text-xs sm:text-sm text-green-700 text-center")

        # Card templates
        card_count = len([t for t in template_list if t.get("type") == "card"])
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(card_count)).classes("text-xl sm:text-2xl font-bold text-purple-600")
                ui.label("Card").classes("text-xs sm:text-sm text-purple-700 text-center")

        # Other templates
        other_count = len(template_list) - text_count - card_count
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(other_count)).classes("text-xl sm:text-2xl font-bold text-orange-600")
                ui.label(t("templates.other")).classes("text-xs sm:text-sm text-orange-700 text-center")

    # Template type reference
    with ui.expansion(t("templates.type_reference"), icon="help_outline").classes("w-full mb-4 bg-white rounded-xl border border-gray-200"):
        with ui.element("div").classes("grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4"):
            for type_name, desc in TEMPLATE_TYPE_INFO.items():
                with ui.card().classes("p-3 bg-gray-50 rounded-lg"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.chip(type_name, color="blue").classes("text-xs")
                    ui.label(desc).classes("text-xs sm:text-sm text-gray-600")

    # Template list section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("templates.list")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("templates.list_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    build_list_editor(
        item_list=template_list,
        card_builder=template_card,
        default_item={"name": "new-template", "type": "text", "engine": "string", "content": "", "description": ""},
        add_button_text=t("templates.add"),
    )

    # Quick add section
    with ui.column().classes("w-full mt-4 sm:mt-6 mb-3 sm:mb-4"):
        ui.label(t("templates.quick_add")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("templates.quick_add_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    with ui.card().classes("w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
        with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3"):
            def add_preset(preset_type: str, preset_name: str, preset_content: str) -> None:
                template_list.append({
                    "name": preset_name,
                    "type": preset_type,
                    "engine": "string",
                    "content": preset_content,
                    "description": f"Quick add: {preset_type}",
                })
                ui.notify(f"Added {preset_name}", type="positive")

            # Preset buttons
            ui.button("文本通知", on_click=lambda: add_preset("text", "text-notify", "通知: {message}"), icon="text_fields").props("outline dense").classes("w-full")
            ui.button("Markdown", on_click=lambda: add_preset("markdown", "md-template", "**标题**\n\n{content}"), icon="code").props("outline dense").classes("w-full")
            ui.button("卡片消息", on_click=lambda: add_preset("card", "card-template", '{"header":{"title":"标题"},"elements":[]}'), icon="dashboard").props("outline dense").classes("w-full")
            ui.button("富文本", on_click=lambda: add_preset("post", "post-template", '{"title":"标题","content":[]}'), icon="article").props("outline dense").classes("w-full")
            ui.button("交互式", on_click=lambda: add_preset("interactive", "interactive-template", '{"elements":[],"actions":[]}'), icon="touch_app").props("outline dense").classes("w-full")
            ui.button("JSON", on_click=lambda: add_preset("json", "json-template", '{"msg_type":"text","content":{}}'), icon="data_object").props("outline dense").classes("w-full")
