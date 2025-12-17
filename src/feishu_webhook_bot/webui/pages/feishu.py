# ruff: noqa: E501
"""Feishu page - Dedicated Feishu bot configuration and management."""

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


def build_feishu_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the Feishu dedicated page."""
    # Page header
    build_page_header(t("feishu.title"), t("feishu.desc"))

    # Get Feishu providers
    msg_providers = controller.get_message_provider_list()
    feishu_providers = [p for p in msg_providers if p.get("provider_type") == "feishu"]

    # Get active providers
    active_providers = controller.get_provider_list()
    feishu_active = [p for p in active_providers if "Feishu" in p.get("type", "")]
    connected_count = len([p for p in feishu_active if p.get("status") == "Connected"])

    # Stats cards
    build_stats_cards(
        [
            {
                "value": len(feishu_providers),
                "label": t("feishu.configured"),
                "color": "blue",
                "icon": "settings",
            },
            {
                "value": connected_count,
                "label": t("feishu.connected"),
                "color": "green",
                "icon": "link",
            },
            {
                "value": len(feishu_active),
                "label": t("feishu.active"),
                "color": "purple",
                "icon": "power",
            },
            {
                "value": "0",
                "label": t("feishu.messages_today"),
                "color": "orange",
                "icon": "message",
            },
        ]
    )

    # Provider Configuration Section
    if state is not None:
        providers_cfg = state["form"].setdefault("providers", [])
        [p for p in providers_cfg if p.get("provider_type") == "feishu"]

        build_section_header(t("feishu.config_title"), t("feishu.config_desc"))

        with ui.card().classes(
            "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
        ):
            providers_container = ui.column().classes("gap-3 w-full")

            def rebuild_feishu_config() -> None:
                providers_container.clear()
                with providers_container:
                    feishu_list = [p for p in providers_cfg if p.get("provider_type") == "feishu"]
                    if not feishu_list:
                        build_empty_state("cloud_off", t("feishu.no_configured"))
                    else:
                        for _idx, provider in enumerate(feishu_list):
                            real_idx = providers_cfg.index(provider)
                            _build_feishu_config_card(
                                provider, real_idx, providers_cfg, rebuild_feishu_config
                            )

            rebuild_feishu_config()

            # Add button
            def add_feishu_provider() -> None:
                providers_cfg.append(
                    {
                        "provider_type": "feishu",
                        "name": f"feishu_{len([p for p in providers_cfg if p.get('provider_type') == 'feishu']) + 1}",
                        "enabled": True,
                        "webhook_url": "",
                        "secret": "",
                        "timeout": 30,
                    }
                )
                rebuild_feishu_config()

            ui.button(t("feishu.add_provider"), on_click=add_feishu_provider, icon="add").props(
                "outline color=blue"
            ).classes("mt-3")

    # Active Providers Section
    _build_active_feishu_section(controller)

    # Message Send Test Section
    _build_feishu_send_section(controller)

    # Webhook Info Section
    _build_feishu_webhook_info(controller)


def _build_feishu_config_card(
    provider: dict[str, Any],
    idx: int,
    providers_list: list[dict[str, Any]],
    rebuild_callback: Any,
) -> None:
    """Build a Feishu provider configuration card."""
    with ui.card().classes("w-full p-4 bg-gray-50 border-l-4 border-blue-500 rounded-lg"):
        # Header
        with ui.row().classes("items-center justify-between mb-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("chat").classes("text-blue-600")
                ui.chip("飞书", color="blue").props("dense")
                ui.label(provider.get("name", "")).classes("font-medium")

            def remove_provider(i: int = idx) -> None:
                providers_list.pop(i)
                rebuild_callback()

            ui.button(icon="delete", on_click=remove_provider).props("flat round color=red dense")

        # Basic settings
        with ui.row().classes("gap-3 w-full mb-2"):
            ui.input(t("feishu.provider_name")).bind_value(provider, "name").props(
                "outlined dense"
            ).classes("flex-1")
            ui.switch(t("common.enabled")).bind_value(provider, "enabled")

        # Webhook settings
        with ui.row().classes("gap-3 w-full mb-2"):
            ui.input(t("feishu.webhook_url")).bind_value(provider, "webhook_url").props(
                "outlined dense"
            ).classes("flex-1")
            ui.input(t("feishu.webhook_secret")).bind_value(provider, "secret").props(
                "type=password outlined dense"
            ).classes("w-48")

        # Timeout
        with ui.row().classes("gap-3 w-full"):
            ui.number(t("common.timeout"), min=1, max=300).bind_value(provider, "timeout").props(
                "outlined dense"
            ).classes("w-32")


def _build_active_feishu_section(controller: BotController) -> None:
    """Build the active Feishu providers section."""
    build_section_header(t("feishu.active_title"), t("feishu.active_desc"))

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        with ui.row().classes("items-center justify-between mb-3"):
            ui.label(t("feishu.registered_providers")).classes(
                "text-base font-semibold text-gray-800"
            )
            ui.button(icon="refresh", on_click=lambda: rebuild_active()).props("flat round dense")

        active_container = ui.column().classes("gap-2 w-full")

        def rebuild_active() -> None:
            active_container.clear()
            with active_container:
                providers = controller.get_provider_list()
                feishu_providers = [p for p in providers if "Feishu" in p.get("type", "")]

                if not feishu_providers:
                    build_empty_state("cloud_off", t("feishu.no_active"))
                    return

                for provider in feishu_providers:
                    _build_active_feishu_row(controller, provider)

        rebuild_active()


def _build_active_feishu_row(controller: BotController, provider: dict[str, Any]) -> None:
    """Build a single active Feishu provider row."""
    with ui.row().classes("w-full items-center justify-between p-3 bg-gray-50 rounded-lg"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("chat").classes("text-blue-600")
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
                    controller.send_test_to_provider(prov_name, "飞书 WebUI 测试消息")
                    ui.notify(t("feishu.test_sent"), type="positive")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("common.test"), on_click=on_test).props("dense outline")
            ui.button(t("feishu.send_test"), on_click=on_send_test).props(
                "dense outline color=primary"
            )


def _build_feishu_send_section(controller: BotController) -> None:
    """Build the Feishu message send section."""
    build_section_header(t("feishu.send_title"), t("feishu.send_desc"))

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
    ):
        # Get available Feishu providers
        providers = controller.get_provider_list()
        feishu_names = [p["name"] for p in providers if "Feishu" in p.get("type", "")]

        # Message type selector at top
        with ui.row().classes("gap-4 w-full items-center mb-3"):
            msg_type = ui.toggle(
                {
                    "text": t("feishu.type_text"),
                    "card": t("feishu.type_card"),
                },
                value="text",
            ).props("dense")

        with ui.row().classes("gap-4 w-full items-end"):
            message_input = (
                ui.textarea(
                    t("common.message"),
                    placeholder=t("feishu.message_placeholder"),
                )
                .props("outlined")
                .classes("flex-1")
            )

        with ui.row().classes("gap-3 w-full mt-3 items-end"):
            if feishu_names:
                target_select = (
                    ui.select(
                        feishu_names,
                        label=t("feishu.provider"),
                        value=feishu_names[0],
                    )
                    .props("outlined dense")
                    .classes("w-48")
                )
            else:
                target_select = (
                    ui.select(
                        ["default"],
                        label=t("feishu.provider"),
                        value="default",
                    )
                    .props("outlined dense disabled")
                    .classes("w-48")
                )

        # Card options (shown when card type selected)
        card_options = ui.column().classes("gap-3 w-full mt-3")

        with card_options, ui.row().classes("gap-3 w-full"):
            card_title = (
                ui.input(
                    t("feishu.card_title"),
                    placeholder=t("feishu.card_title_placeholder"),
                    value="消息通知",
                )
                .props("outlined dense")
                .classes("flex-1")
            )
            card_color = (
                ui.select(
                    [
                        "blue",
                        "green",
                        "red",
                        "orange",
                        "purple",
                        "grey",
                        "turquoise",
                        "yellow",
                        "carmine",
                        "violet",
                        "indigo",
                    ],
                    label=t("feishu.card_color"),
                    value="blue",
                )
                .props("outlined dense")
                .classes("w-32")
            )

        card_options.set_visibility(False)

        def on_type_change():
            card_options.set_visibility(msg_type.value == "card")

        msg_type.on_value_change(on_type_change)

        # Send button
        with ui.row().classes("gap-2 mt-4"):

            def do_send():
                target = target_select.value
                msg = message_input.value
                if not msg:
                    ui.notify(t("common.fill_required"), type="warning")
                    return

                try:
                    if msg_type.value == "text":
                        controller.send_test_to_provider(target, msg)
                    else:
                        # Send as card
                        controller.send_card_to_provider(
                            target,
                            title=card_title.value or "消息",
                            content=msg,
                            color=card_color.value,
                        )
                    ui.notify(t("feishu.send_success"), type="positive")
                    message_input.value = ""
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("common.send"), on_click=do_send, icon="send").props("color=primary")


def _build_feishu_webhook_info(controller: BotController) -> None:
    """Build Feishu webhook information section."""
    build_section_header(t("feishu.webhook_info_title"), t("feishu.webhook_info_desc"))

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"
    ):
        # Event server info
        status = controller.status()
        event_server_running = status.get("running", False)

        with ui.row().classes("items-center gap-3 mb-4"):
            color = "green" if event_server_running else "gray"
            ui.icon("webhook").classes(f"text-{color}-600")
            ui.label(t("feishu.event_server")).classes("font-medium")
            ui.chip(
                t("common.running") if event_server_running else t("common.stopped"),
                color=color,
            ).props("dense")

        # Webhook endpoint info
        with ui.column().classes("gap-2"):
            ui.label(t("feishu.webhook_endpoint")).classes("text-sm font-medium text-gray-600")
            with ui.row().classes("items-center gap-2 bg-gray-100 p-2 rounded"):
                endpoint = "/feishu/events"
                ui.label(endpoint).classes("font-mono text-sm")
                ui.button(
                    icon="content_copy",
                    on_click=lambda: ui.run_javascript(
                        f"navigator.clipboard.writeText('{endpoint}')"
                    ),
                ).props("flat dense round")

        # Tips
        with ui.expansion(t("feishu.setup_tips"), icon="help_outline").classes("mt-4"):
            with ui.column().classes("gap-2 text-sm text-gray-600"):
                ui.markdown("""
1. 在飞书开放平台创建应用
2. 配置事件订阅 URL: `http://your-server:port/feishu/events`
3. 添加所需的事件权限
4. 将 Webhook URL 配置到上方的 Provider 中
                """)
