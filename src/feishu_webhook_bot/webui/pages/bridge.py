# ruff: noqa: E501
"""Message Bridge page - Cross-platform message forwarding configuration."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t


def build_bridge_page(controller: BotController, state: dict[str, Any] | None = None) -> None:
    """Build the Message Bridge configuration page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("bridge.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("bridge.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Get bridge config
    bridge_cfg = None
    if state is not None:
        bridge_cfg = state["form"].setdefault("message_bridge", {
            "enabled": False,
            "rules": [],
            "default_format": "[{source}] {sender}: {content}",
            "rate_limit_per_minute": 60,
            "retry_on_failure": True,
            "max_retries": 3,
        })

    # Stats cards
    rules_count = len(bridge_cfg.get("rules", [])) if bridge_cfg else 0
    enabled_rules = len([r for r in bridge_cfg.get("rules", []) if r.get("enabled", True)]) if bridge_cfg else 0
    msg_providers = controller.get_message_provider_list()

    with ui.element("div").classes(
        "grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Total rules
        with ui.card().classes("p-3 sm:p-4 bg-blue-50 border border-blue-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(rules_count)).classes(
                    "text-xl sm:text-2xl font-bold text-blue-600"
                )
                ui.label(t("bridge.total_rules")).classes(
                    "text-xs sm:text-sm text-blue-700 text-center"
                )

        # Enabled rules
        with ui.card().classes("p-3 sm:p-4 bg-green-50 border border-green-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(enabled_rules)).classes(
                    "text-xl sm:text-2xl font-bold text-green-600"
                )
                ui.label(t("bridge.enabled_rules")).classes(
                    "text-xs sm:text-sm text-green-700 text-center"
                )

        # Available providers
        with ui.card().classes("p-3 sm:p-4 bg-purple-50 border border-purple-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                ui.label(str(len(msg_providers))).classes(
                    "text-xl sm:text-2xl font-bold text-purple-600"
                )
                ui.label(t("bridge.available_providers")).classes(
                    "text-xs sm:text-sm text-purple-700 text-center"
                )

        # Bridge status
        bridge_enabled = bridge_cfg.get("enabled", False) if bridge_cfg else False
        with ui.card().classes("p-3 sm:p-4 bg-orange-50 border border-orange-100 rounded-xl"):
            with ui.column().classes("items-center gap-1"):
                icon = "sync" if bridge_enabled else "sync_disabled"
                color = "green" if bridge_enabled else "gray"
                ui.icon(icon, size="md").classes(f"text-{color}-600")
                ui.label(t("bridge.status")).classes(
                    "text-xs sm:text-sm text-orange-700 text-center"
                )

    if state is not None and bridge_cfg is not None:
        # Global settings
        with ui.column().classes("w-full mb-3 sm:mb-4"):
            ui.label(t("bridge.global_settings")).classes(
                "text-lg sm:text-xl font-semibold text-gray-800"
            )
            ui.label(t("bridge.global_settings_desc")).classes(
                "text-sm sm:text-base text-gray-500 mt-1"
            )

        with ui.card().classes(
            "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-4 sm:mb-6"
        ):
            with ui.row().classes("gap-4 items-center mb-4"):
                ui.switch(t("bridge.enable_bridge")).bind_value(bridge_cfg, "enabled")
                ui.label(t("bridge.enable_hint")).classes("text-sm text-gray-500")

            with ui.row().classes("gap-3 w-full mb-2"):
                ui.input(t("bridge.default_format")).bind_value(
                    bridge_cfg, "default_format"
                ).props("outlined dense").classes("flex-1")
                ui.label(t("bridge.format_hint")).classes(
                    "text-xs text-gray-400 self-center"
                )

            with ui.row().classes("gap-3 w-full"):
                ui.number(
                    t("bridge.rate_limit"), min=1, max=1000
                ).bind_value(bridge_cfg, "rate_limit_per_minute").props(
                    "outlined dense"
                ).classes("w-40")
                ui.switch(t("bridge.retry_on_failure")).bind_value(
                    bridge_cfg, "retry_on_failure"
                )
                ui.number(
                    t("bridge.max_retries"), min=0, max=10
                ).bind_value(bridge_cfg, "max_retries").props("outlined dense").classes("w-32")

        # Bridge rules section
        with ui.column().classes("w-full mb-3 sm:mb-4"):
            ui.label(t("bridge.rules_config")).classes(
                "text-lg sm:text-xl font-semibold text-gray-800"
            )
            ui.label(t("bridge.rules_config_desc")).classes(
                "text-sm sm:text-base text-gray-500 mt-1"
            )

        with ui.card().classes(
            "w-full p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"
        ):
            rules_list = bridge_cfg.setdefault("rules", [])
            rules_container = ui.column().classes("gap-3 w-full")

            # Get provider names for dropdowns
            provider_names = [p.get("name", "") for p in msg_providers]

            def rebuild_rules() -> None:
                rules_container.clear()
                with rules_container:
                    if not rules_list:
                        with ui.column().classes("items-center py-8"):
                            ui.icon("sync_disabled", size="xl").classes("text-gray-300 mb-2")
                            ui.label(t("bridge.no_rules")).classes("text-gray-400")
                    else:
                        for idx, rule in enumerate(rules_list):
                            _build_rule_card(rule, idx, rules_list, provider_names, rebuild_rules)

            rebuild_rules()

            def add_rule() -> None:
                rules_list.append({
                    "name": f"rule_{len(rules_list) + 1}",
                    "enabled": True,
                    "description": "",
                    "source_provider": provider_names[0] if provider_names else "",
                    "source_chat_type": "all",
                    "source_chat_ids": [],
                    "target_provider": provider_names[1] if len(provider_names) > 1 else (provider_names[0] if provider_names else ""),
                    "target_chat_id": "",
                    "include_sender_info": True,
                    "message_prefix": "",
                    "message_suffix": "",
                    "forward_images": True,
                    "forward_at_mentions": False,
                    "keyword_whitelist": [],
                    "keyword_blacklist": [],
                    "sender_whitelist": [],
                    "sender_blacklist": [],
                })
                rebuild_rules()

            ui.button(
                t("bridge.add_rule"), on_click=add_rule, icon="add"
            ).props("outline color=primary").classes("mt-3")


def _build_rule_card(
    rule: dict[str, Any],
    idx: int,
    rules_list: list[dict[str, Any]],
    provider_names: list[str],
    rebuild_callback: Any,
) -> None:
    """Build a single bridge rule configuration card."""
    with ui.card().classes("w-full p-4 bg-gray-50 border-l-4 border-indigo-500 rounded-lg"):
        # Header row
        with ui.row().classes("items-center justify-between mb-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("sync_alt").classes("text-indigo-600")
                ui.label(rule.get("name", "")).classes("font-medium")
                ui.switch("").bind_value(rule, "enabled").props("dense")

            def remove_rule(i: int = idx) -> None:
                rules_list.pop(i)
                rebuild_callback()

            ui.button(icon="delete", on_click=remove_rule).props("flat round color=red dense")

        # Basic settings
        with ui.row().classes("gap-3 w-full mb-2"):
            ui.input(t("bridge.rule_name")).bind_value(
                rule, "name"
            ).props("outlined dense").classes("w-48")
            ui.input(t("bridge.description")).bind_value(
                rule, "description"
            ).props("outlined dense").classes("flex-1")

        # Source configuration
        with ui.expansion(t("bridge.source_config"), icon="input").classes("w-full mb-2"):
            with ui.column().classes("gap-2 p-2"):
                with ui.row().classes("gap-3 w-full"):
                    ui.select(
                        provider_names or [""],
                        label=t("bridge.source_provider")
                    ).bind_value(rule, "source_provider").props("outlined dense").classes("flex-1")
                    ui.select(
                        ["all", "private", "group"],
                        label=t("bridge.chat_type")
                    ).bind_value(rule, "source_chat_type").props("outlined dense").classes("w-32")

                ui.input(t("bridge.source_chat_ids")).bind_value(
                    rule, "source_chat_ids_str"
                ).props("outlined dense").classes("w-full")
                ui.label(t("bridge.chat_ids_hint")).classes("text-xs text-gray-400")

        # Target configuration
        with ui.expansion(t("bridge.target_config"), icon="output").classes("w-full mb-2"):
            with ui.column().classes("gap-2 p-2"):
                with ui.row().classes("gap-3 w-full"):
                    ui.select(
                        provider_names or [""],
                        label=t("bridge.target_provider")
                    ).bind_value(rule, "target_provider").props("outlined dense").classes("flex-1")
                    ui.input(t("bridge.target_chat_id")).bind_value(
                        rule, "target_chat_id"
                    ).props("outlined dense").classes("flex-1")

        # Message transformation
        with ui.expansion(t("bridge.message_transform"), icon="transform").classes("w-full mb-2"):
            with ui.column().classes("gap-2 p-2"):
                with ui.row().classes("gap-3 w-full items-center"):
                    ui.switch(t("bridge.include_sender")).bind_value(rule, "include_sender_info")
                    ui.switch(t("bridge.forward_images")).bind_value(rule, "forward_images")
                    ui.switch(t("bridge.forward_mentions")).bind_value(rule, "forward_at_mentions")

                with ui.row().classes("gap-3 w-full"):
                    ui.input(t("bridge.message_prefix")).bind_value(
                        rule, "message_prefix"
                    ).props("outlined dense").classes("flex-1")
                    ui.input(t("bridge.message_suffix")).bind_value(
                        rule, "message_suffix"
                    ).props("outlined dense").classes("flex-1")

        # Filtering
        with ui.expansion(t("bridge.filtering"), icon="filter_list").classes("w-full"):
            with ui.column().classes("gap-2 p-2"):
                ui.input(t("bridge.keyword_whitelist")).bind_value(
                    rule, "keyword_whitelist_str"
                ).props("outlined dense").classes("w-full")
                ui.input(t("bridge.keyword_blacklist")).bind_value(
                    rule, "keyword_blacklist_str"
                ).props("outlined dense").classes("w-full")
                ui.label(t("bridge.filter_hint")).classes("text-xs text-gray-400")
