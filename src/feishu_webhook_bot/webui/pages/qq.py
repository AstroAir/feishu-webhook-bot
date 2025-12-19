# ruff: noqa: E501
"""QQ page - Dedicated QQ/Napcat bot configuration and management."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t
from .provider_components import (
    build_empty_state,
    build_page_header,
    build_section_header,
    build_stats_cards,
)


def build_qq_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the QQ/Napcat dedicated page."""
    # Page header
    build_page_header(t("qq.title"), t("qq.desc"))

    # Get QQ providers
    msg_providers = controller.get_message_provider_list()
    qq_providers = [p for p in msg_providers if p.get("provider_type") == "napcat"]

    # Get active providers
    active_providers = controller.get_provider_list()
    qq_active = [p for p in active_providers if "Napcat" in p.get("type", "")]
    connected_count = len([p for p in qq_active if p.get("status") == "Connected"])

    # Stats cards
    build_stats_cards(
        [
            {
                "value": len(qq_providers),
                "label": t("qq.configured"),
                "color": "green",
                "icon": "settings",
            },
            {"value": connected_count, "label": t("qq.connected"), "color": "blue", "icon": "link"},
            {"value": len(qq_active), "label": t("qq.active"), "color": "purple", "icon": "power"},
            {"value": "0", "label": t("qq.messages_today"), "color": "orange", "icon": "message"},
        ]
    )

    # Provider Configuration Section
    if state is not None:
        providers_cfg = state["form"].setdefault("providers", [])

        build_section_header(t("qq.config_title"), t("qq.config_desc"))

        with ui.card().classes(
            "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
        ):
            providers_container = ui.column().classes("gap-3 w-full")

            def rebuild_qq_config() -> None:
                providers_container.clear()
                with providers_container:
                    qq_list = [p for p in providers_cfg if p.get("provider_type") == "napcat"]
                    if not qq_list:
                        build_empty_state("cloud_off", t("qq.no_configured"))
                    else:
                        for provider in qq_list:
                            real_idx = providers_cfg.index(provider)
                            _build_qq_config_card(
                                provider, real_idx, providers_cfg, rebuild_qq_config
                            )

            rebuild_qq_config()

            # Add button
            def add_qq_provider() -> None:
                providers_cfg.append(
                    {
                        "provider_type": "napcat",
                        "name": f"qq_{len([p for p in providers_cfg if p.get('provider_type') == 'napcat']) + 1}",
                        "enabled": True,
                        "http_url": "http://127.0.0.1:3000",
                        "access_token": "",
                        "bot_qq": "",
                        "default_target": "",
                        "timeout": 30,
                    }
                )
                rebuild_qq_config()

            ui.button(t("qq.add_provider"), on_click=add_qq_provider, icon="add").props(
                "outline color=green"
            ).classes("mt-3")

    # Active Providers Section
    _build_active_qq_section(controller)

    # QQ-Specific Features Section
    _build_qq_features_section(controller)

    # Extended Features Section (NapCat)
    _build_qq_extended_features(controller)

    # Group Management Section
    _build_qq_group_management(controller)

    # Message Send Test Section
    _build_qq_send_section(controller)

    # Event Callback Configuration
    _build_qq_event_config(state)


def _build_qq_config_card(
    provider: dict[str, Any],
    idx: int,
    providers_list: list[dict[str, Any]],
    rebuild_callback: Any,
) -> None:
    """Build a QQ/Napcat provider configuration card."""
    with ui.card().classes("w-full p-4 bg-gray-50 border-l-4 border-green-500 rounded-lg"):
        # Header
        with ui.row().classes("items-center justify-between mb-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("forum").classes("text-green-600")
                ui.chip("QQ/Napcat", color="green").props("dense")
                ui.label(provider.get("name", "")).classes("font-medium")

            def remove_provider(i: int = idx) -> None:
                providers_list.pop(i)
                rebuild_callback()

            ui.button(icon="delete", on_click=remove_provider).props("flat round color=red dense")

        # Basic settings
        with ui.row().classes("gap-3 w-full mb-2"):
            ui.input(t("qq.provider_name")).bind_value(provider, "name").props(
                "outlined dense"
            ).classes("flex-1")
            ui.switch(t("common.enabled")).bind_value(provider, "enabled")

        # HTTP settings
        with ui.row().classes("gap-3 w-full mb-2"):
            ui.input(t("qq.http_url")).bind_value(provider, "http_url").props(
                "outlined dense"
            ).classes("flex-1")
            ui.input(t("qq.access_token")).bind_value(provider, "access_token").props(
                "type=password outlined dense"
            ).classes("w-48")

        # QQ-specific settings
        with ui.row().classes("gap-3 w-full mb-2"):
            ui.input(t("qq.bot_qq")).bind_value(provider, "bot_qq").props("outlined dense").classes(
                "w-40"
            )
            ui.input(t("qq.default_target")).bind_value(provider, "default_target").props(
                "outlined dense"
            ).classes("flex-1")
            ui.label(t("qq.target_hint")).classes("text-xs text-gray-400 self-center")

        # Timeout
        with ui.row().classes("gap-3 w-full"):
            ui.number(t("common.timeout"), min=1, max=300).bind_value(provider, "timeout").props(
                "outlined dense"
            ).classes("w-32")


def _build_active_qq_section(controller: BotController) -> None:
    """Build the active QQ providers section."""
    build_section_header(t("qq.active_title"), t("qq.active_desc"))

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        with ui.row().classes("items-center justify-between mb-3"):
            ui.label(t("qq.registered_providers")).classes("text-base font-semibold text-gray-800")
            ui.button(icon="refresh", on_click=lambda: rebuild_active()).props("flat round dense")

        active_container = ui.column().classes("gap-2 w-full")

        def rebuild_active() -> None:
            active_container.clear()
            with active_container:
                providers = controller.get_provider_list()
                qq_providers = [p for p in providers if "Napcat" in p.get("type", "")]

                if not qq_providers:
                    build_empty_state("cloud_off", t("qq.no_active"))
                    return

                for provider in qq_providers:
                    _build_active_qq_row(controller, provider)

        rebuild_active()


def _build_active_qq_row(controller: BotController, provider: dict[str, Any]) -> None:
    """Build a single active QQ provider row."""
    with ui.row().classes("w-full items-center justify-between p-3 bg-gray-50 rounded-lg"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("forum").classes("text-green-600")
            with ui.column().classes("gap-0"):
                ui.label(provider["name"]).classes("font-medium text-gray-800")
                ui.label(f"Type: {provider.get('type', 'Unknown')}").classes(
                    "text-sm text-gray-500"
                )

        with ui.row().classes("items-center gap-2"):
            status = provider.get("status", "unknown")
            status_color = "green" if status == "Connected" else "gray"
            ui.chip(status, color=status_color).props("dense")

            def on_test(prov_name: str = provider["name"]) -> None:
                try:
                    ui.notify(t("common.testing"), type="info")
                    if controller.bot and controller.bot.get_provider(prov_name):
                        ui.notify(t("common.connection_success"), type="positive")
                    else:
                        ui.notify(t("common.connection_failed"), type="warning")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            def on_send_test(prov_name: str = provider["name"]) -> None:
                try:
                    controller.send_test_to_provider(prov_name, "QQ WebUI 测试消息")
                    ui.notify(t("qq.test_sent"), type="positive")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("common.test"), on_click=on_test).props("dense outline")
            ui.button(t("qq.send_test"), on_click=on_send_test).props("dense outline color=primary")


def _build_qq_features_section(controller: BotController) -> None:
    """Build QQ-specific features section."""
    build_section_header(t("qq.features_title"), t("qq.features_desc"))

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        # Feature cards grid
        with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-3"):
            # Poke feature
            poke_card = ui.card().classes(
                "p-3 bg-yellow-50 border border-yellow-200 rounded-lg cursor-pointer hover:shadow-md transition-shadow"
            )
            with poke_card, ui.column().classes("items-center gap-2"):
                ui.icon("touch_app", size="md").classes("text-yellow-600")
                ui.label(t("qq.feature_poke")).classes("text-sm font-medium text-center")

            async def show_poke_dialog():
                with ui.dialog() as dialog, ui.card().classes("p-4 w-80"):
                    ui.label(t("qq.poke_title")).classes("text-lg font-semibold mb-3")
                    user_input = (
                        ui.input(t("qq.user_id"), placeholder="目标QQ号")
                        .props("outlined dense")
                        .classes("w-full mb-2")
                    )
                    group_input = (
                        ui.input(t("qq.group_id"), placeholder="群号 (可选，私聊留空)")
                        .props("outlined dense")
                        .classes("w-full mb-2")
                    )
                    with ui.row().classes("gap-2 justify-end"):
                        ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

                        def do_poke():
                            try:
                                user_id = int(user_input.value)
                                group_id = int(group_input.value) if group_input.value else None
                                controller.qq_poke(user_id, group_id)
                                ui.notify(t("qq.poke_sent"), type="positive")
                                dialog.close()
                            except ValueError:
                                ui.notify(t("qq.invalid_id"), type="warning")
                            except Exception as e:
                                ui.notify(f"{t('common.error')}: {e}", type="negative")

                        ui.button(t("qq.poke_send"), on_click=do_poke).props("color=primary")
                dialog.open()

            poke_card.on("click", show_poke_dialog)

            # Mute feature
            mute_card = ui.card().classes(
                "p-3 bg-red-50 border border-red-200 rounded-lg cursor-pointer hover:shadow-md transition-shadow"
            )
            with mute_card, ui.column().classes("items-center gap-2"):
                ui.icon("volume_off", size="md").classes("text-red-600")
                ui.label(t("qq.feature_mute")).classes("text-sm font-medium text-center")

            async def show_mute_dialog():
                with ui.dialog() as dialog, ui.card().classes("p-4 w-80"):
                    ui.label(t("qq.mute_title")).classes("text-lg font-semibold mb-3")
                    group_input = (
                        ui.input(t("qq.group_id"), placeholder="群号")
                        .props("outlined dense")
                        .classes("w-full mb-2")
                    )
                    user_input = (
                        ui.input(t("qq.user_id"), placeholder="QQ号")
                        .props("outlined dense")
                        .classes("w-full mb-2")
                    )
                    duration_input = (
                        ui.number(t("qq.mute_duration"), value=10, min=0, max=43200)
                        .props("outlined dense")
                        .classes("w-full mb-2")
                    )
                    ui.label(t("qq.mute_duration_hint")).classes("text-xs text-gray-400 mb-2")
                    with ui.row().classes("gap-2 justify-end"):
                        ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

                        def do_mute():
                            try:
                                group_id = int(group_input.value)
                                user_id = int(user_input.value)
                                duration = int(duration_input.value) * 60  # Convert to seconds
                                controller.qq_mute(group_id, user_id, duration)
                                ui.notify(t("qq.mute_success"), type="positive")
                                dialog.close()
                            except ValueError:
                                ui.notify(t("qq.invalid_id"), type="warning")
                            except Exception as e:
                                ui.notify(f"{t('common.error')}: {e}", type="negative")

                        ui.button(t("qq.mute_confirm"), on_click=do_mute).props("color=red")
                dialog.open()

            mute_card.on("click", show_mute_dialog)

            # Kick feature
            kick_card = ui.card().classes(
                "p-3 bg-orange-50 border border-orange-200 rounded-lg cursor-pointer hover:shadow-md transition-shadow"
            )
            with kick_card, ui.column().classes("items-center gap-2"):
                ui.icon("person_remove", size="md").classes("text-orange-600")
                ui.label(t("qq.feature_kick")).classes("text-sm font-medium text-center")

            async def show_kick_dialog():
                with ui.dialog() as dialog, ui.card().classes("p-4 w-80"):
                    ui.label(t("qq.kick_title")).classes("text-lg font-semibold mb-3")
                    group_input = (
                        ui.input(t("qq.group_id"), placeholder="群号")
                        .props("outlined dense")
                        .classes("w-full mb-2")
                    )
                    user_input = (
                        ui.input(t("qq.user_id"), placeholder="QQ号")
                        .props("outlined dense")
                        .classes("w-full mb-2")
                    )
                    reject_switch = ui.switch(t("qq.reject_add")).classes("mb-2")
                    with ui.row().classes("gap-2 justify-end"):
                        ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

                        def do_kick():
                            try:
                                group_id = int(group_input.value)
                                user_id = int(user_input.value)
                                controller.qq_kick(group_id, user_id, reject_switch.value)
                                ui.notify(t("qq.kick_success"), type="positive")
                                dialog.close()
                            except ValueError:
                                ui.notify(t("qq.invalid_id"), type="warning")
                            except Exception as e:
                                ui.notify(f"{t('common.error')}: {e}", type="negative")

                        ui.button(t("qq.kick_confirm"), on_click=do_kick).props("color=orange")
                dialog.open()

            kick_card.on("click", show_kick_dialog)

            # Status feature
            status_card = ui.card().classes(
                "p-3 bg-blue-50 border border-blue-200 rounded-lg cursor-pointer hover:shadow-md transition-shadow"
            )
            with status_card, ui.column().classes("items-center gap-2"):
                ui.icon("info", size="md").classes("text-blue-600")
                ui.label(t("qq.feature_status")).classes("text-sm font-medium text-center")

            async def show_status_dialog():
                with ui.dialog() as dialog, ui.card().classes("p-4 w-96"):
                    ui.label(t("qq.bot_status_title")).classes("text-lg font-semibold mb-3")

                    status_container = ui.column().classes("gap-2 w-full")

                    def refresh_status():
                        status_container.clear()
                        with status_container:
                            # Get login info
                            login_info = controller.qq_get_login_info()
                            status_info = controller.qq_get_status()
                            version_info = controller.qq_get_version_info()

                            # Login info
                            with ui.row().classes("items-center gap-2 p-2 bg-gray-50 rounded"):
                                ui.icon("account_circle").classes("text-blue-500")
                                if "error" not in login_info:
                                    ui.label(f"QQ: {login_info.get('user_id', 'N/A')}").classes(
                                        "font-medium"
                                    )
                                    ui.label(f"({login_info.get('nickname', '')})").classes(
                                        "text-gray-500"
                                    )
                                else:
                                    ui.label(login_info.get("error", "未知错误")).classes(
                                        "text-red-500"
                                    )

                            # Online status
                            with ui.row().classes("items-center gap-2 p-2 bg-gray-50 rounded"):
                                online = status_info.get("online", False)
                                color = "green" if online else "red"
                                ui.icon("circle", size="xs").classes(f"text-{color}-500")
                                ui.label(
                                    t("qq.status_online") if online else t("qq.status_offline")
                                ).classes("text-sm")
                                if status_info.get("good", False):
                                    ui.chip(t("qq.status_good"), color="green").props("dense")

                            # Version info
                            if "error" not in version_info:
                                with ui.row().classes("items-center gap-2 p-2 bg-gray-50 rounded"):
                                    ui.icon("info_outline").classes("text-gray-500")
                                    ui.label(
                                        f"{version_info.get('app_name', 'OneBot')} v{version_info.get('app_version', 'N/A')}"
                                    ).classes("text-sm")

                    refresh_status()

                    with ui.row().classes("gap-2 justify-end mt-4"):
                        ui.button(
                            t("common.refresh"), on_click=refresh_status, icon="refresh"
                        ).props("flat")
                        ui.button(t("common.close"), on_click=dialog.close).props("flat")
                dialog.open()

            status_card.on("click", show_status_dialog)


def _build_qq_extended_features(controller: BotController) -> None:
    """Build QQ extended features section (NapCat APIs)."""
    build_section_header(t("qq.extended_title"), t("qq.extended_desc"))

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        with ui.element("div").classes("grid grid-cols-2 sm:grid-cols-4 gap-3"):
            # AI Voice
            _build_feature_card(
                "record_voice_over",
                "purple",
                t("qq.feature_ai_voice"),
                lambda: _show_ai_voice_dialog(controller),
            )
            # Message History
            _build_feature_card(
                "history",
                "blue",
                t("qq.feature_msg_history"),
                lambda: _show_msg_history_dialog(controller),
            )
            # Group Notice
            _build_feature_card(
                "campaign", "green", t("qq.feature_notice"), lambda: _show_notice_dialog(controller)
            )
            # OCR
            _build_feature_card(
                "document_scanner",
                "orange",
                t("qq.feature_ocr"),
                lambda: _show_ocr_dialog(controller),
            )


def _build_feature_card(icon: str, color: str, label: str, on_click: Any) -> None:
    """Build a clickable feature card."""
    card = ui.card().classes(
        f"p-3 bg-{color}-50 border border-{color}-200 rounded-lg cursor-pointer hover:shadow-md transition-shadow"
    )
    with card, ui.column().classes("items-center gap-2"):
        ui.icon(icon, size="md").classes(f"text-{color}-600")
        ui.label(label).classes("text-sm font-medium text-center")
    card.on("click", on_click)


async def _show_ai_voice_dialog(controller: BotController) -> None:
    """Show AI voice dialog."""
    with ui.dialog() as dialog, ui.card().classes("p-4 w-96"):
        ui.label(t("qq.ai_voice_title")).classes("text-lg font-semibold mb-3")
        group_input = (
            ui.input(t("qq.group_id"), placeholder="群号")
            .props("outlined dense")
            .classes("w-full mb-2")
        )
        char_select = (
            ui.select([], label=t("qq.ai_voice_character"))
            .props("outlined dense")
            .classes("w-full mb-2")
        )
        text_input = (
            ui.textarea(t("qq.ai_voice_text"), placeholder="输入文本...")
            .props("outlined")
            .classes("w-full mb-2")
        )

        async def load_characters():
            if group_input.value:
                try:
                    chars = controller.qq_get_ai_characters(int(group_input.value))
                    if chars:
                        char_select.options = {c.get("id", ""): c.get("name", "") for c in chars}
                    else:
                        ui.notify(t("qq.ai_voice_no_characters"), type="warning")
                except Exception as e:
                    ui.notify(str(e), type="negative")

        ui.button(t("common.load"), on_click=load_characters).props("flat dense")

        with ui.row().classes("gap-2 justify-end mt-3"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

            def send_voice():
                try:
                    controller.qq_send_ai_voice(
                        int(group_input.value), char_select.value, text_input.value
                    )
                    ui.notify(t("qq.ai_voice_success"), type="positive")
                    dialog.close()
                except Exception as e:
                    ui.notify(str(e), type="negative")

            ui.button(t("qq.ai_voice_send"), on_click=send_voice).props("color=primary")
    dialog.open()


async def _show_msg_history_dialog(controller: BotController) -> None:
    """Show message history dialog."""
    with ui.dialog() as dialog, ui.card().classes("p-4 w-[500px]"):
        ui.label(t("qq.msg_history_title")).classes("text-lg font-semibold mb-3")
        with ui.row().classes("gap-2 w-full mb-3"):
            group_input = (
                ui.input(t("qq.group_id"), placeholder="群号")
                .props("outlined dense")
                .classes("flex-1")
            )
            count_input = (
                ui.number(t("qq.msg_history_count"), value=20, min=1, max=100)
                .props("outlined dense")
                .classes("w-24")
            )

        history_container = ui.column().classes("gap-2 w-full max-h-80 overflow-auto")

        def load_history():
            history_container.clear()
            with history_container:
                try:
                    messages = controller.qq_get_group_msg_history(
                        int(group_input.value), 0, int(count_input.value)
                    )
                    if not messages:
                        ui.label(t("qq.msg_history_empty")).classes(
                            "text-gray-400 text-center py-4"
                        )
                    else:
                        for msg in messages:
                            with ui.row().classes("w-full p-2 bg-gray-50 rounded gap-2"):
                                sender = msg.get("sender", {})
                                ui.label(sender.get("nickname", "未知")).classes(
                                    "font-medium text-sm"
                                )
                                content = msg.get("message", [])
                                text = "".join(
                                    [
                                        s.get("data", {}).get("text", "")
                                        for s in content
                                        if s.get("type") == "text"
                                    ]
                                )
                                ui.label(text[:100] + ("..." if len(text) > 100 else "")).classes(
                                    "text-sm text-gray-600 flex-1"
                                )
                except Exception as e:
                    ui.label(str(e)).classes("text-red-500")

        ui.button(t("qq.msg_history_load"), on_click=load_history, icon="history").props(
            "color=primary"
        )
        with history_container:
            ui.label(t("qq.msg_history_empty")).classes("text-gray-400 text-center py-4")

        with ui.row().classes("gap-2 justify-end mt-3"):
            ui.button(t("common.close"), on_click=dialog.close).props("flat")
    dialog.open()


async def _show_notice_dialog(controller: BotController) -> None:
    """Show group notice dialog."""
    with ui.dialog() as dialog, ui.card().classes("p-4 w-96"):
        ui.label(t("qq.notice_title")).classes("text-lg font-semibold mb-3")
        group_input = (
            ui.input(t("qq.group_id"), placeholder="群号")
            .props("outlined dense")
            .classes("w-full mb-2")
        )
        content_input = (
            ui.textarea(t("qq.notice_content"), placeholder="公告内容...")
            .props("outlined")
            .classes("w-full mb-2")
        )

        notice_container = ui.column().classes("gap-2 w-full max-h-60 overflow-auto mb-3")

        def load_notices():
            notice_container.clear()
            with notice_container:
                try:
                    notices = controller.qq_get_group_notice(int(group_input.value))
                    if not notices:
                        ui.label(t("qq.notice_empty")).classes("text-gray-400 text-center py-2")
                    else:
                        for notice in notices[:5]:
                            with ui.card().classes("w-full p-2 bg-gray-50"):
                                ui.label(notice.get("content", "")[:100]).classes("text-sm")
                except Exception as e:
                    ui.label(str(e)).classes("text-red-500")

        ui.button(t("common.load"), on_click=load_notices).props("flat dense")

        with ui.row().classes("gap-2 justify-end"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")

            def send_notice():
                try:
                    controller.qq_send_group_notice(int(group_input.value), content_input.value)
                    ui.notify(t("qq.notice_success"), type="positive")
                    dialog.close()
                except Exception as e:
                    ui.notify(str(e), type="negative")

            ui.button(t("qq.notice_send"), on_click=send_notice).props("color=primary")
    dialog.open()


async def _show_ocr_dialog(controller: BotController) -> None:
    """Show OCR dialog."""
    with ui.dialog() as dialog, ui.card().classes("p-4 w-96"):
        ui.label(t("qq.ocr_title")).classes("text-lg font-semibold mb-3")
        image_input = (
            ui.input(t("qq.ocr_image_url"), placeholder="图片URL")
            .props("outlined dense")
            .classes("w-full mb-2")
        )

        result_container = ui.column().classes("gap-2 w-full")

        def perform_ocr():
            result_container.clear()
            with result_container:
                try:
                    results = controller.qq_ocr_image(image_input.value)
                    if not results:
                        ui.label(t("qq.ocr_empty")).classes("text-gray-400")
                    else:
                        ui.label(t("qq.ocr_result")).classes("font-medium mb-1")
                        for item in results:
                            ui.label(item.get("text", "")).classes("text-sm bg-gray-50 p-2 rounded")
                except Exception as e:
                    ui.label(str(e)).classes("text-red-500")

        with ui.row().classes("gap-2 justify-end"):
            ui.button(t("common.cancel"), on_click=dialog.close).props("flat")
            ui.button(t("qq.ocr_perform"), on_click=perform_ocr).props("color=primary")
    dialog.open()


def _build_qq_group_management(controller: BotController) -> None:
    """Build QQ group management section."""
    build_section_header(t("qq.group_mgmt_title"), t("qq.group_mgmt_desc"))

    # Shared state for group management
    current_group_id = {"value": ""}

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        with ui.tabs().classes("w-full") as tabs:
            tab_groups = ui.tab("groups", label=t("qq.tab_group_list"), icon="groups")
            tab_info = ui.tab("info", label=t("qq.tab_group_info"), icon="info")
            tab_members = ui.tab("members", label=t("qq.tab_members"), icon="people")
            tab_friends = ui.tab("friends", label=t("qq.tab_friends"), icon="person")

        with ui.tab_panels(tabs, value=tab_groups).classes("w-full"):
            # Group List Tab
            with ui.tab_panel(tab_groups):
                groups_container = ui.column().classes("gap-2 w-full py-3")

                def refresh_groups():
                    groups_container.clear()
                    with groups_container:
                        groups = controller.qq_get_group_list()
                        if not groups:
                            build_empty_state("groups", t("qq.no_groups"))
                        else:
                            ui.label(f"{t('qq.total_groups')}: {len(groups)}").classes(
                                "text-sm text-gray-500 mb-2"
                            )
                            for group in groups:
                                with ui.row().classes(
                                    "w-full items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
                                ):
                                    with ui.row().classes("items-center gap-3"):
                                        ui.icon("group").classes("text-blue-500")
                                        with ui.column().classes("gap-0"):
                                            ui.label(group.get("group_name", "未知群")).classes(
                                                "font-medium"
                                            )
                                            ui.label(f"ID: {group.get('group_id', '')}").classes(
                                                "text-xs text-gray-400"
                                            )
                                    with ui.row().classes("items-center gap-2"):
                                        ui.chip(
                                            f"{group.get('member_count', 0)} {t('qq.members')}"
                                        ).props("dense")

                                        def view_group(gid: int = group.get("group_id")):
                                            current_group_id["value"] = str(gid)
                                            tabs.set_value("info")

                                        ui.button(icon="visibility", on_click=view_group).props(
                                            "flat dense round"
                                        )

                with ui.row().classes("gap-2 mb-3"):
                    ui.button(t("common.refresh"), on_click=refresh_groups, icon="refresh").props(
                        "outline"
                    )

                refresh_groups()

            # Group Info Tab
            with ui.tab_panel(tab_info):
                with ui.column().classes("gap-3 w-full py-3"):
                    with ui.row().classes("gap-3 items-end"):
                        group_id_input = (
                            ui.input(
                                t("qq.group_id"),
                                placeholder="输入群号",
                            )
                            .props("outlined dense")
                            .classes("w-48")
                        )

                        # Sync with current_group_id
                        def sync_group_id():
                            if current_group_id["value"]:
                                group_id_input.value = current_group_id["value"]

                        ui.timer(0.5, sync_group_id, once=True)

                    info_container = ui.column().classes("gap-2 w-full")

                    def query_group_info():
                        group_id = group_id_input.value
                        if not group_id:
                            ui.notify(t("qq.enter_group_id"), type="warning")
                            return

                        info_container.clear()
                        with info_container:
                            try:
                                info = controller.qq_get_group_info(int(group_id))
                                if "error" in info:
                                    ui.label(info["error"]).classes("text-red-500")
                                else:
                                    with ui.card().classes("w-full p-4 bg-gray-50 rounded-lg"):
                                        with ui.row().classes("items-center gap-3 mb-3"):
                                            ui.icon("group", size="lg").classes("text-blue-500")
                                            ui.label(info.get("group_name", "未知")).classes(
                                                "text-xl font-bold"
                                            )

                                        with ui.element("div").classes("grid grid-cols-2 gap-4"):
                                            with ui.column().classes("gap-1"):
                                                ui.label(t("qq.group_id")).classes(
                                                    "text-xs text-gray-400"
                                                )
                                                ui.label(str(info.get("group_id", ""))).classes(
                                                    "font-medium"
                                                )
                                            with ui.column().classes("gap-1"):
                                                ui.label(t("qq.member_count")).classes(
                                                    "text-xs text-gray-400"
                                                )
                                                ui.label(
                                                    f"{info.get('member_count', 0)} / {info.get('max_member_count', 0)}"
                                                ).classes("font-medium")

                                    ui.notify(t("qq.query_success"), type="positive")
                            except Exception as e:
                                ui.label(f"{t('common.error')}: {e}").classes("text-red-500")

                    with ui.row().classes("gap-2"):
                        ui.button(t("qq.query"), on_click=query_group_info, icon="search").props(
                            "color=primary"
                        )

                    # Placeholder
                    with info_container:
                        with ui.card().classes("w-full p-4 bg-gray-50 rounded-lg"):
                            ui.label(t("qq.group_info_placeholder")).classes(
                                "text-gray-400 text-center"
                            )

            # Members Tab
            with ui.tab_panel(tab_members), ui.column().classes("gap-3 w-full py-3"):
                with ui.row().classes("gap-3 items-end"):
                    member_group_input = (
                        ui.input(
                            t("qq.group_id"),
                            placeholder="输入群号",
                        )
                        .props("outlined dense")
                        .classes("w-48")
                    )

                members_container = ui.column().classes("gap-2 w-full")

                def load_members():
                    group_id = member_group_input.value
                    if not group_id:
                        ui.notify(t("qq.enter_group_id"), type="warning")
                        return

                    members_container.clear()
                    with members_container:
                        try:
                            members = controller.qq_get_group_member_list(int(group_id))
                            if not members:
                                build_empty_state("people", t("qq.no_members"))
                            else:
                                ui.label(f"{t('qq.total_members')}: {len(members)}").classes(
                                    "text-sm text-gray-500 mb-2"
                                )

                                # Create a scrollable table
                                with ui.scroll_area().classes("h-64"):
                                    for member in members[:100]:  # Limit to 100
                                        with ui.row().classes(
                                            "w-full items-center justify-between p-2 border-b"
                                        ):
                                            with ui.row().classes("items-center gap-2"):
                                                role = member.get("role", "member")
                                                icon_color = (
                                                    "orange"
                                                    if role == "owner"
                                                    else "blue"
                                                    if role == "admin"
                                                    else "gray"
                                                )
                                                ui.icon("person").classes(f"text-{icon_color}-500")
                                                with ui.column().classes("gap-0"):
                                                    display_name = member.get("card") or member.get(
                                                        "nickname", "未知"
                                                    )
                                                    ui.label(display_name).classes(
                                                        "text-sm font-medium"
                                                    )
                                                    ui.label(
                                                        f"QQ: {member.get('user_id', '')}"
                                                    ).classes("text-xs text-gray-400")
                                            with ui.row().classes("items-center gap-1"):
                                                if role == "owner":
                                                    ui.chip("群主", color="orange").props("dense")
                                                elif role == "admin":
                                                    ui.chip("管理员", color="blue").props("dense")
                        except Exception as e:
                            ui.label(f"{t('common.error')}: {e}").classes("text-red-500")

                with ui.row().classes("gap-2"):
                    ui.button(t("qq.load_members"), on_click=load_members, icon="people").props(
                        "color=primary"
                    )

                with members_container:
                    build_empty_state("people", t("qq.no_members_loaded"))

            # Friends Tab
            with ui.tab_panel(tab_friends):
                friends_container = ui.column().classes("gap-2 w-full py-3")

                def refresh_friends():
                    friends_container.clear()
                    with friends_container:
                        friends = controller.qq_get_friend_list()
                        if not friends:
                            build_empty_state("person", t("qq.no_friends"))
                        else:
                            ui.label(f"{t('qq.total_friends')}: {len(friends)}").classes(
                                "text-sm text-gray-500 mb-2"
                            )
                            with ui.scroll_area().classes("h-64"):
                                for friend in friends:
                                    with ui.row().classes(
                                        "w-full items-center justify-between p-2 border-b"
                                    ):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("person").classes("text-green-500")
                                            with ui.column().classes("gap-0"):
                                                ui.label(friend.get("nickname", "未知")).classes(
                                                    "text-sm font-medium"
                                                )
                                                if friend.get("remark"):
                                                    ui.label(
                                                        f"备注: {friend.get('remark')}"
                                                    ).classes("text-xs text-gray-400")
                                        ui.label(f"QQ: {friend.get('user_id', '')}").classes(
                                            "text-xs text-gray-400"
                                        )

                with ui.row().classes("gap-2 mb-3"):
                    ui.button(t("common.refresh"), on_click=refresh_friends, icon="refresh").props(
                        "outline"
                    )

                refresh_friends()


def _build_qq_send_section(controller: BotController) -> None:
    """Build the QQ message send section."""
    build_section_header(t("qq.send_title"), t("qq.send_desc"))

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        # Get available QQ providers
        providers = controller.get_provider_list()
        qq_names = [p["name"] for p in providers if "Napcat" in p.get("type", "")]

        # Target type selector
        with ui.row().classes("gap-4 w-full items-center mb-3"):
            target_type = ui.toggle(
                {
                    "private": t("qq.private_msg"),
                    "group": t("qq.group_msg"),
                },
                value="group",
            ).props("dense")

        with ui.row().classes("gap-4 w-full items-end"):
            message_input = (
                ui.textarea(
                    t("common.message"),
                    placeholder=t("qq.message_placeholder"),
                )
                .props("outlined")
                .classes("flex-1")
            )

        with ui.row().classes("gap-3 w-full mt-3 items-end"):
            target_input = (
                ui.input(
                    t("qq.target_id"),
                    placeholder=t("qq.target_id_placeholder"),
                )
                .props("outlined dense")
                .classes("w-40")
            )

            if qq_names:
                provider_select = (
                    ui.select(
                        qq_names,
                        label=t("qq.provider"),
                        value=qq_names[0],
                    )
                    .props("outlined dense")
                    .classes("w-48")
                )
            else:
                provider_select = (
                    ui.select(
                        ["default"],
                        label=t("qq.provider"),
                        value="default",
                    )
                    .props("outlined dense disabled")
                    .classes("w-48")
                )

        # Image URL (optional)
        with ui.row().classes("gap-3 w-full mt-2"):
            image_input = (
                ui.input(
                    t("qq.image_url"),
                    placeholder="图片URL (可选)",
                )
                .props("outlined dense")
                .classes("flex-1")
            )

        # Send buttons
        with ui.row().classes("gap-2 mt-4"):

            def do_send():
                target_id = target_input.value
                msg = message_input.value
                if not target_id or not msg:
                    ui.notify(t("common.fill_required"), type="warning")
                    return

                try:
                    # Build target string
                    prefix = "private" if target_type.value == "private" else "group"
                    target_str = f"{prefix}:{target_id}"

                    prov_name = provider_select.value if qq_names else None
                    controller.qq_send_message(msg, target_str, prov_name)
                    ui.notify(t("qq.send_success"), type="positive")
                    message_input.value = ""
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("common.send"), on_click=do_send, icon="send").props("color=primary")

            def do_send_image():
                target_id = target_input.value
                if not target_id:
                    ui.notify(t("qq.enter_target_id"), type="warning")
                    return
                if not image_input.value:
                    ui.notify(t("qq.enter_image_url"), type="warning")
                    return
                try:
                    prefix = "private" if target_type.value == "private" else "group"
                    target_str = f"{prefix}:{target_id}"
                    prov_name = provider_select.value if qq_names else None
                    controller.qq_send_image(image_input.value, target_str, prov_name)
                    ui.notify(t("qq.image_sent"), type="positive")
                    image_input.value = ""
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("qq.send_image"), on_click=do_send_image, icon="image").props(
                "outline color=green"
            )


def _build_qq_event_config(state: dict[str, Any] | None) -> None:
    """Build QQ event callback configuration section."""
    build_section_header(t("qq.event_config_title"), t("qq.event_config_desc"))

    # Initialize QQ event config in state
    if state is not None:
        qq_config = state["form"].setdefault(
            "qq_events",
            {
                "enable_welcome": False,
                "welcome_message": "欢迎 [CQ:at,qq={user_id}] 加入群聊！",
                "enable_auto_reply": False,
                "auto_reply_rules": [],
                "log_notice_events": True,
                "log_request_events": True,
                "log_message_events": False,
                "auto_approve_friend": False,
                "auto_approve_group": False,
            },
        )
    else:
        qq_config = {
            "enable_welcome": False,
            "welcome_message": "欢迎 [CQ:at,qq={user_id}] 加入群聊！",
            "enable_auto_reply": False,
            "auto_reply_rules": [],
            "log_notice_events": True,
            "log_request_events": True,
            "log_message_events": False,
            "auto_approve_friend": False,
            "auto_approve_group": False,
        }

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"
    ):
        # Welcome message config
        with ui.expansion(t("qq.welcome_config"), icon="waving_hand").classes("w-full"):
            with ui.column().classes("gap-3 py-3"):
                ui.switch(t("qq.enable_welcome")).bind_value(qq_config, "enable_welcome").classes(
                    "mb-2"
                )
                ui.textarea(
                    t("qq.welcome_message"),
                    placeholder=t("qq.welcome_message_placeholder"),
                ).bind_value(qq_config, "welcome_message").props("outlined").classes("w-full")

        # Auto reply config
        with ui.expansion(t("qq.auto_reply_config"), icon="quickreply").classes("w-full mt-2"):
            with ui.column().classes("gap-3 py-3"):
                ui.switch(t("qq.enable_auto_reply")).bind_value(
                    qq_config, "enable_auto_reply"
                ).classes("mb-2")
                ui.label(t("qq.auto_reply_rules")).classes("text-sm text-gray-500")
                build_empty_state("rule", t("qq.no_rules_configured"))

        # Auto approve config
        with ui.expansion(t("qq.auto_approve_config"), icon="check_circle").classes("w-full mt-2"):
            with ui.column().classes("gap-3 py-3"):
                ui.switch(t("qq.auto_approve_friend")).bind_value(qq_config, "auto_approve_friend")
                ui.switch(t("qq.auto_approve_group")).bind_value(qq_config, "auto_approve_group")

        # Event logging config
        with ui.expansion(t("qq.event_log_config"), icon="history").classes("w-full mt-2"):
            with ui.column().classes("gap-3 py-3"):
                ui.switch(t("qq.log_notice_events")).bind_value(qq_config, "log_notice_events")
                ui.switch(t("qq.log_request_events")).bind_value(qq_config, "log_request_events")
                ui.switch(t("qq.log_message_events")).bind_value(qq_config, "log_message_events")
