# ruff: noqa: E501
"""Providers page - Message providers (Feishu/QQ) configuration."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t

# Message provider types
MESSAGE_PROVIDER_TYPES = ["feishu", "napcat"]


def build_providers_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the Providers page with message provider configuration."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("providers.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("providers.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    providers = controller.get_provider_list()
    msg_providers = controller.get_message_provider_list()

    # Stats cards
    with ui.element("div").classes(
        "grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Total message providers
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(msg_providers))).classes(
                    "text-xl sm:text-2xl font-bold text-blue-600"
                )
                ui.label(t("providers.total")).classes(
                    "text-xs sm:text-sm text-blue-700 text-center"
                )

        # Connected providers
        connected_count = len([p for p in providers if p.get("status") == "Connected"])
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(connected_count)).classes(
                    "text-xl sm:text-2xl font-bold text-green-600"
                )
                ui.label(t("providers.connected")).classes(
                    "text-xs sm:text-sm text-green-700 text-center"
                )

        # Feishu count
        feishu_count = len([p for p in msg_providers if p.get("provider_type") == "feishu"])
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(feishu_count)).classes("text-xl sm:text-2xl font-bold text-purple-600")
                ui.label(t("providers.feishu_count")).classes(
                    "text-xs sm:text-sm text-purple-700 text-center"
                )

        # QQ count
        qq_count = len([p for p in msg_providers if p.get("provider_type") == "napcat"])
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(qq_count)).classes("text-xl sm:text-2xl font-bold text-orange-600")
                ui.label(t("providers.qq_count")).classes(
                    "text-xs sm:text-sm text-orange-700 text-center"
                )

    # Message Provider configuration section
    if state is not None:
        msg_providers_cfg = state["form"].setdefault("providers", [])

        with ui.column().classes("w-full mb-3 sm:mb-4"):
            ui.label(t("providers.msg_provider_config")).classes(
                "text-lg sm:text-xl font-semibold text-gray-800"
            )
            ui.label(t("providers.msg_provider_config_desc")).classes(
                "text-sm sm:text-base text-gray-500 mt-1"
            )

        # Message provider list configuration
        with ui.card().classes(
            "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
        ):
            providers_container = ui.column().classes("gap-3 w-full")

            def rebuild_msg_provider_config() -> None:
                providers_container.clear()
                with providers_container:
                    if not msg_providers_cfg:
                        with ui.column().classes("items-center py-8"):
                            ui.icon("cloud_off", size="xl").classes("text-gray-300 mb-2")
                            ui.label(t("providers.no_configured")).classes("text-gray-400")
                    else:
                        for idx, provider in enumerate(msg_providers_cfg):
                            _build_provider_card(
                                provider, idx, msg_providers_cfg, rebuild_msg_provider_config
                            )

            rebuild_msg_provider_config()

            # Add provider buttons
            with ui.row().classes("gap-2 mt-3"):

                def add_feishu_provider() -> None:
                    msg_providers_cfg.append(
                        {
                            "provider_type": "feishu",
                            "name": f"feishu_{len(msg_providers_cfg) + 1}",
                            "enabled": True,
                            "webhook_url": "",
                            "secret": "",
                            "timeout": 30,
                        }
                    )
                    rebuild_msg_provider_config()

                def add_qq_provider() -> None:
                    msg_providers_cfg.append(
                        {
                            "provider_type": "napcat",
                            "name": f"qq_{len(msg_providers_cfg) + 1}",
                            "enabled": True,
                            "http_url": "",
                            "access_token": "",
                            "bot_qq": "",
                            "default_target": "",
                            "timeout": 30,
                        }
                    )
                    rebuild_msg_provider_config()

                ui.button(
                    t("providers.add_feishu"), on_click=add_feishu_provider, icon="chat"
                ).props("outline color=blue")
                ui.button(t("providers.add_qq"), on_click=add_qq_provider, icon="forum").props(
                    "outline color=green"
                )

    # Active providers status
    _build_active_providers_section(controller)


def _build_provider_card(
    provider: dict[str, Any],
    idx: int,
    providers_list: list[dict[str, Any]],
    rebuild_callback: Any,
) -> None:
    """Build a single provider configuration card."""
    prov_type = provider.get("provider_type", "feishu")
    is_feishu = prov_type == "feishu"
    border_color = "blue" if is_feishu else "green"

    with ui.card().classes(
        f"w-full p-4 bg-gray-50 border-l-4 border-{border_color}-500 rounded-lg"
    ):
        # Header row
        with ui.row().classes("items-center justify-between mb-3"):
            with ui.row().classes("items-center gap-2"):
                icon = "chat" if is_feishu else "forum"
                ui.icon(icon).classes(f"text-{border_color}-600")
                ui.chip("飞书" if is_feishu else "QQ/Napcat", color=border_color).props("dense")
                ui.label(provider.get("name", "")).classes("font-medium")

            def remove_provider(i: int = idx) -> None:
                providers_list.pop(i)
                rebuild_callback()

            ui.button(icon="delete", on_click=remove_provider).props("flat round color=red dense")

        # Basic settings row
        with ui.row().classes("gap-3 w-full mb-2"):
            ui.input(t("providers.provider_name")).bind_value(provider, "name").props(
                "outlined dense"
            ).classes("flex-1")

            ui.select(MESSAGE_PROVIDER_TYPES, label=t("providers.provider_type")).bind_value(
                provider, "provider_type"
            ).props("outlined dense").classes("w-32")

            ui.switch(t("providers.enabled")).bind_value(provider, "enabled")

        # Provider-specific fields
        if is_feishu:
            _build_feishu_fields(provider)
        else:
            _build_napcat_fields(provider)

        # Common settings
        with ui.row().classes("gap-3 w-full"):
            ui.number(t("providers.timeout"), min=1, max=300).bind_value(provider, "timeout").props(
                "outlined dense"
            ).classes("w-32")


def _build_feishu_fields(provider: dict[str, Any]) -> None:
    """Build Feishu-specific configuration fields."""
    with ui.row().classes("gap-3 w-full mb-2"):
        ui.input(t("providers.webhook_url")).bind_value(provider, "webhook_url").props(
            "outlined dense"
        ).classes("flex-1")
        ui.input(t("providers.webhook_secret")).bind_value(provider, "secret").props(
            "type=password outlined dense"
        ).classes("w-48")


def _build_napcat_fields(provider: dict[str, Any]) -> None:
    """Build Napcat/QQ-specific configuration fields."""
    with ui.row().classes("gap-3 w-full mb-2"):
        ui.input(t("providers.http_url")).bind_value(provider, "http_url").props(
            "outlined dense"
        ).classes("flex-1")
        ui.input(t("providers.access_token")).bind_value(provider, "access_token").props(
            "type=password outlined dense"
        ).classes("w-48")

    with ui.row().classes("gap-3 w-full mb-2"):
        ui.input(t("providers.bot_qq")).bind_value(provider, "bot_qq").props(
            "outlined dense"
        ).classes("w-40")
        ui.input(t("providers.default_target")).bind_value(provider, "default_target").props(
            "outlined dense"
        ).classes("flex-1")
        ui.label(t("providers.target_hint")).classes("text-xs text-gray-400 self-center")


def _build_active_providers_section(controller: BotController) -> None:
    """Build the active providers status section."""
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("providers.active_providers")).classes(
            "text-lg sm:text-xl font-semibold text-gray-800"
        )
        ui.label(t("providers.active_providers_desc")).classes(
            "text-sm sm:text-base text-gray-500 mt-1"
        )

    with ui.card().classes(
        "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"
    ):
        with ui.row().classes("items-center justify-between mb-3 sm:mb-4"):
            ui.label(t("providers.registered_providers")).classes(
                "text-base sm:text-lg font-semibold text-gray-800"
            )
            ui.button(icon="refresh", on_click=lambda: rebuild_providers()).props(
                "flat round dense"
            )

        provider_container = ui.column().classes("gap-2 w-full")

        def rebuild_providers() -> None:
            provider_container.clear()
            with provider_container:
                providers = controller.get_provider_list()
                if not providers:
                    with ui.column().classes("items-center py-8"):
                        ui.icon("cloud_off", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("providers.no_providers")).classes("text-gray-400")
                    return

                for provider in providers:
                    _build_active_provider_row(controller, provider)

        rebuild_providers()


def _build_active_provider_row(controller: BotController, provider: dict[str, Any]) -> None:
    """Build a single active provider row."""
    prov_type = provider.get("type", "Unknown")
    is_feishu = "Feishu" in prov_type
    is_qq = "Napcat" in prov_type
    icon = "chat" if is_feishu else ("forum" if is_qq else "cloud")
    color = "blue" if is_feishu else ("green" if is_qq else "gray")

    with ui.row().classes("w-full items-center justify-between p-3 bg-gray-50 rounded-lg"):
        with ui.row().classes("items-center gap-3"):
            ui.icon(icon).classes(f"text-{color}-600")
            with ui.column().classes("gap-0"):
                ui.label(provider["name"]).classes("font-medium text-gray-800")
                ui.label(f"Type: {prov_type}").classes("text-sm text-gray-500")

        with ui.row().classes("items-center gap-2"):
            status = provider.get("status", "unknown")
            status_color = "green" if status == "Connected" else "gray"
            ui.chip(status, color=status_color).props("dense")

            def on_test_provider(prov_name: str = provider["name"]) -> None:
                try:
                    ui.notify(t("common.loading"), type="info")
                    if controller.bot and controller.bot.get_provider(prov_name):
                        ui.notify(t("common.success"), type="positive")
                    else:
                        ui.notify(t("common.warning"), type="warning")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            def on_send_test(prov_name: str = provider["name"]) -> None:
                try:
                    controller.send_test_to_provider(prov_name, "Test message from WebUI")
                    ui.notify(t("providers.test_sent"), type="positive")
                except Exception as e:
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            ui.button(t("providers.test"), on_click=on_test_provider).props("dense outline")
            ui.button(t("providers.send_test"), on_click=on_send_test).props(
                "dense outline color=primary"
            )
