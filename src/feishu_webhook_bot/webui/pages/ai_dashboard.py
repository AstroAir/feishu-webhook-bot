# ruff: noqa: E501
"""AI Dashboard page."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ..controller import BotController
from ..i18n import t

# Available AI providers and models
AI_PROVIDERS = ["openai", "anthropic", "google", "groq", "cohere", "ollama"]
AVAILABLE_MODELS = [
    "openai:gpt-4o",
    "openai:gpt-4o-mini",
    "openai:gpt-4-turbo",
    "openai:gpt-3.5-turbo",
    "anthropic:claude-3-5-sonnet-20241022",
    "anthropic:claude-3-opus-20240229",
    "anthropic:claude-3-haiku-20240307",
    "google:gemini-pro",
    "google:gemini-1.5-pro",
    "groq:llama-3.1-70b-versatile",
    "groq:mixtral-8x7b-32768",
    "cohere:command-r-plus",
    "ollama:llama3.1",
    "ollama:mistral",
]


def build_ai_dashboard_page(state: dict[str, Any], controller: BotController) -> None:
    """Build the AI Dashboard page."""
    # Page header
    with ui.column().classes("w-full mb-4 sm:mb-6"):
        ui.label(t("ai.title")).classes("text-xl sm:text-2xl font-bold text-gray-800")
        ui.label(t("ai.desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    ai_stats = controller.get_ai_stats()
    cfg_ai = state["form"].setdefault("ai", {})

    # Stats cards - grid layout
    with ui.element("div").classes(
        "grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6 w-full"
    ):
        # Status card
        with ui.card().classes("p-3 sm:p-5 bg-white border border-gray-200 rounded-xl shadow-sm"):
            with ui.column().classes("gap-1 sm:gap-2 w-full"):
                color = "green" if ai_stats["enabled"] else "gray"
                with ui.row().classes("items-center gap-2"):
                    with ui.element("div").classes(
                        f"w-8 h-8 sm:w-12 sm:h-12 rounded-full bg-{color}-100 flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon(
                            "check_circle" if ai_stats["enabled"] else "cancel", size="sm"
                        ).classes(f"text-{color}-600")
                    ui.label(t("ai.status")).classes("text-xs sm:text-sm text-gray-500 truncate")
                ui.label(
                    t("dashboard.enabled") if ai_stats["enabled"] else t("dashboard.disabled")
                ).classes("text-base sm:text-xl font-bold text-gray-800")

        # Requests card
        with ui.card().classes("p-3 sm:p-5 bg-white border border-gray-200 rounded-xl shadow-sm"):
            with ui.column().classes("gap-1 sm:gap-2 w-full"):
                with ui.row().classes("items-center gap-2"):
                    with ui.element("div").classes(
                        "w-8 h-8 sm:w-12 sm:h-12 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon("query_stats", size="sm").classes("text-blue-600")
                    ui.label(t("ai.requests")).classes("text-xs sm:text-sm text-gray-500 truncate")
                ui.label(str(ai_stats["requests"])).classes(
                    "text-base sm:text-xl font-bold text-gray-800"
                )

        # Success rate card
        with ui.card().classes("p-3 sm:p-5 bg-white border border-gray-200 rounded-xl shadow-sm"):
            with ui.column().classes("gap-1 sm:gap-2 w-full"):
                with ui.row().classes("items-center gap-2"):
                    with ui.element("div").classes(
                        "w-8 h-8 sm:w-12 sm:h-12 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon("trending_up", size="sm").classes("text-green-600")
                    ui.label(t("ai.success_rate")).classes(
                        "text-xs sm:text-sm text-gray-500 truncate"
                    )
                ui.label(f"{ai_stats['success_rate']:.1%}").classes(
                    "text-base sm:text-xl font-bold text-gray-800"
                )

        # Tokens card
        with ui.card().classes("p-3 sm:p-5 bg-white border border-gray-200 rounded-xl shadow-sm"):
            with ui.column().classes("gap-1 sm:gap-2 w-full"):
                with ui.row().classes("items-center gap-2"):
                    with ui.element("div").classes(
                        "w-8 h-8 sm:w-12 sm:h-12 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon("token", size="sm").classes("text-purple-600")
                    ui.label(t("ai.tokens_used")).classes(
                        "text-xs sm:text-sm text-gray-500 truncate"
                    )
                ui.label(str(ai_stats["tokens_used"])).classes(
                    "text-base sm:text-xl font-bold text-gray-800"
                )

    # AI Configuration Section
    with ui.column().classes("w-full mb-3 sm:mb-4"):
        ui.label(t("ai.configuration")).classes("text-lg sm:text-xl font-semibold text-gray-800")
        ui.label(t("ai.configuration_desc")).classes("text-sm sm:text-base text-gray-500 mt-1")

    # Basic AI settings - two column
    with ui.element("div").classes(
        "grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6 w-full"
    ):
        # Basic settings card
        with ui.card().classes("p-4 sm:p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("ai.basic_settings")).classes(
                "text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4"
            )
            with ui.column().classes("gap-4 w-full"):
                ui.switch(t("ai.enable")).bind_value(cfg_ai, "enabled")
                ui.select(
                    AVAILABLE_MODELS,
                    label=t("ai.select_model"),
                    value=cfg_ai.get("model", AVAILABLE_MODELS[0]),
                ).bind_value(cfg_ai, "model").props("outlined").classes("w-full")
                ui.input(t("ai.api_key")).bind_value(cfg_ai, "api_key").props(
                    "type=password outlined clearable"
                ).classes("w-full")

        # Provider settings card
        with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("ai.provider_settings")).classes("text-lg font-semibold text-gray-800 mb-4")
            provider_cfg = cfg_ai.setdefault("provider_config", {})
            with ui.column().classes("gap-4 w-full"):
                ui.select(
                    AI_PROVIDERS,
                    label=t("ai.provider"),
                    value=provider_cfg.get("provider"),
                ).bind_value(provider_cfg, "provider").props("outlined clearable").classes("w-full")
                ui.input(t("ai.base_url")).bind_value(provider_cfg, "base_url").props(
                    "outlined clearable"
                ).classes("w-full").tooltip(t("ai.base_url_hint"))
                ui.input(t("ai.organization_id")).bind_value(provider_cfg, "organization_id").props(
                    "outlined clearable"
                ).classes("w-full")

    # Model parameters - two column
    with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6 w-full"):
        # Generation parameters card
        with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("ai.generation_params")).classes("text-lg font-semibold text-gray-800 mb-4")
            with ui.column().classes("gap-4 w-full"):
                with ui.row().classes("items-center gap-4 w-full"):
                    ui.label(t("ai.temperature")).classes("w-32 text-sm text-gray-600")
                    ui.slider(
                        min=0.0, max=2.0, step=0.1, value=cfg_ai.get("temperature", 0.7)
                    ).bind_value(cfg_ai, "temperature").classes("flex-grow")
                    ui.label().bind_text_from(
                        cfg_ai, "temperature", lambda v: f"{v:.1f}" if v else "0.7"
                    ).classes("w-12 text-sm")
                ui.number(t("ai.max_tokens"), min=1, max=128000).bind_value(
                    cfg_ai, "max_tokens"
                ).props("outlined").classes("w-full")
                ui.number(t("ai.max_conversation_turns"), min=1, max=100).bind_value(
                    cfg_ai, "max_conversation_turns"
                ).props("outlined").classes("w-full")
                ui.number(t("ai.conversation_timeout"), min=1, max=1440).bind_value(
                    cfg_ai, "conversation_timeout_minutes"
                ).props("outlined").classes("w-full")

        # Advanced settings card
        with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("ai.advanced_settings")).classes("text-lg font-semibold text-gray-800 mb-4")
            with ui.column().classes("gap-3 w-full"):
                ui.switch(t("ai.tools_enabled")).bind_value(cfg_ai, "tools_enabled")
                ui.switch(t("ai.web_search_enabled")).bind_value(cfg_ai, "web_search_enabled")
                ui.switch(t("ai.structured_output")).bind_value(cfg_ai, "structured_output_enabled")
                ui.switch(t("ai.streaming_enabled")).bind_value(
                    cfg_ai.setdefault("streaming", {}), "enabled"
                )
                ui.number(t("ai.max_retries"), min=1, max=10).bind_value(
                    cfg_ai, "max_retries"
                ).props("outlined").classes("w-full")

    # System prompt section
    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        ui.label(t("ai.system_prompt")).classes("text-lg font-semibold text-gray-800 mb-4")
        ui.textarea(t("ai.system_prompt_hint")).bind_value(cfg_ai, "system_prompt").props(
            "outlined auto-grow rows=4"
        ).classes("w-full")

    # Fallback models section
    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        ui.label(t("ai.fallback_models")).classes("text-lg font-semibold text-gray-800 mb-4")
        ui.label(t("ai.fallback_models_desc")).classes("text-sm text-gray-500 mb-3")
        fallback_list = cfg_ai.setdefault("fallback_models", [])
        fallback_container = ui.column().classes("gap-2 w-full")

        def rebuild_fallback_list() -> None:
            fallback_container.clear()
            with fallback_container:
                if not fallback_list:
                    ui.label(t("ai.no_fallback")).classes("text-gray-400 text-sm")
                else:
                    for idx, model in enumerate(fallback_list):
                        with ui.row().classes("items-center gap-2"):
                            ui.chip(model, color="blue").classes("px-3")

                            def remove_fallback(i: int = idx) -> None:
                                fallback_list.pop(i)
                                rebuild_fallback_list()

                            ui.button(icon="close", on_click=remove_fallback).props(
                                "flat round dense size=sm color=red"
                            )

        rebuild_fallback_list()

        with ui.row().classes("items-center gap-2 mt-3"):
            new_fallback = (
                ui.select(AVAILABLE_MODELS, label=t("ai.add_fallback"))
                .props("outlined dense")
                .classes("w-64")
            )

            def add_fallback() -> None:
                if new_fallback.value and new_fallback.value not in fallback_list:
                    fallback_list.append(new_fallback.value)
                    rebuild_fallback_list()
                    new_fallback.value = None

            ui.button(t("common.add"), on_click=add_fallback, icon="add").props("outline")

    # MCP Configuration Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.mcp_configuration")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.mcp_configuration_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        mcp_cfg = cfg_ai.setdefault("mcp", {})
        with ui.row().classes("items-center justify-between mb-4"):
            ui.switch(t("ai.mcp_enabled")).bind_value(mcp_cfg, "enabled")
            ui.number(t("ai.mcp_timeout"), min=1, max=300).bind_value(
                mcp_cfg, "timeout_seconds"
            ).props("outlined dense").classes("w-48")

        ui.label(t("ai.mcp_servers")).classes("text-lg font-semibold text-gray-800 mb-3")
        mcp_servers = mcp_cfg.setdefault("servers", [])
        mcp_servers_container = ui.column().classes("gap-3 w-full")

        def rebuild_mcp_servers() -> None:
            mcp_servers_container.clear()
            with mcp_servers_container:
                if not mcp_servers:
                    with ui.column().classes("items-center py-6"):
                        ui.icon("dns", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("ai.no_mcp_servers")).classes("text-gray-400")
                else:
                    for idx, server in enumerate(mcp_servers):
                        with (
                            ui.card().classes(
                                "w-full p-4 bg-gray-50 border border-gray-100 rounded-lg"
                            ),
                            ui.row().classes("items-start justify-between"),
                        ):
                            with ui.column().classes("gap-2 flex-grow"):
                                ui.input(t("ai.mcp_server_name")).bind_value(server, "name").props(
                                    "outlined dense"
                                ).classes("w-full")
                                ui.input(t("ai.mcp_server_command")).bind_value(
                                    server, "command"
                                ).props("outlined dense").classes("w-full")
                                ui.input(t("ai.mcp_server_args")).bind_value(server, "args").props(
                                    "outlined dense"
                                ).classes("w-full").tooltip(t("ai.mcp_args_hint"))

                            def remove_server(i: int = idx) -> None:
                                mcp_servers.pop(i)
                                rebuild_mcp_servers()

                            ui.button(icon="delete", on_click=remove_server).props(
                                "flat round color=red"
                            )

        rebuild_mcp_servers()

        def add_mcp_server() -> None:
            mcp_servers.append({"name": "", "command": "", "args": ""})
            rebuild_mcp_servers()

        ui.button(t("ai.add_mcp_server"), on_click=add_mcp_server, icon="add").props(
            "outline color=primary"
        ).classes("mt-3")

    # Conversation Persistence Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.conversation_persistence")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.conversation_persistence_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        persistence_cfg = cfg_ai.setdefault("conversation_persistence", {})
        with ui.column().classes("gap-4 w-full"):
            ui.switch(t("ai.persistence_enabled")).bind_value(persistence_cfg, "enabled")
            ui.input(t("ai.persistence_database")).bind_value(
                persistence_cfg, "database_url"
            ).props("outlined").classes("w-full").tooltip(t("ai.persistence_database_hint"))
            with ui.row().classes("gap-4 w-full"):
                ui.number(t("ai.max_history_days"), min=1, max=365).bind_value(
                    persistence_cfg, "max_history_days"
                ).props("outlined").classes("flex-1")
                ui.number(t("ai.cleanup_interval"), min=1, max=168).bind_value(
                    persistence_cfg, "cleanup_interval_hours"
                ).props("outlined").classes("flex-1")
            ui.switch(t("ai.auto_cleanup")).bind_value(persistence_cfg, "auto_cleanup")

    # Multi-Agent Configuration Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.multi_agent")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.multi_agent_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        multi_agent_cfg = cfg_ai.setdefault("multi_agent", {})
        with ui.column().classes("gap-4 w-full"):
            ui.switch(t("ai.multi_agent_enabled")).bind_value(multi_agent_cfg, "enabled")
            ui.select(
                ["sequential", "concurrent", "hierarchical"],
                label=t("ai.orchestration_mode"),
                value=multi_agent_cfg.get("orchestration_mode", "sequential"),
            ).bind_value(multi_agent_cfg, "orchestration_mode").props("outlined").classes("w-full")
            ui.number(t("ai.max_agents"), min=1, max=10).bind_value(
                multi_agent_cfg, "max_agents"
            ).props("outlined").classes("w-full")

    # Web Search Configuration Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.web_search_config")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.web_search_config_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        web_search_cfg = cfg_ai.setdefault("web_search", {})
        with ui.column().classes("gap-4 w-full"):
            # Basic settings
            with ui.row().classes("gap-4 w-full flex-wrap"):
                ui.switch(t("ai.web_search_enabled")).bind_value(web_search_cfg, "enabled")
                ui.switch(t("ai.web_search_cache_enabled")).bind_value(
                    web_search_cfg, "cache_enabled"
                )
                ui.switch(t("ai.web_search_failover")).bind_value(web_search_cfg, "enable_failover")
                ui.switch(t("ai.web_search_concurrent")).bind_value(
                    web_search_cfg, "concurrent_search"
                )

            with ui.row().classes("gap-4 w-full"):
                ui.number(t("ai.web_search_max_results"), min=1, max=50).bind_value(
                    web_search_cfg, "max_results"
                ).props("outlined").classes("flex-1")
                ui.number(t("ai.web_search_cache_ttl"), min=1, max=1440).bind_value(
                    web_search_cfg, "cache_ttl_minutes"
                ).props("outlined").classes("flex-1")

            # Search Providers
            ui.separator().classes("my-4")
            ui.label(t("ai.search_providers")).classes("text-lg font-semibold text-gray-800")
            ui.label(t("ai.search_provider_hint")).classes("text-sm text-gray-500 mb-2")

            search_providers = web_search_cfg.setdefault("providers", [])
            providers_container = ui.column().classes("gap-3 w-full")

            provider_types = [
                ("duckduckgo", t("ai.provider_duckduckgo")),
                ("tavily", t("ai.provider_tavily")),
                ("exa", t("ai.provider_exa")),
                ("brave", t("ai.provider_brave")),
                ("bing", t("ai.provider_bing")),
                ("google", t("ai.provider_google")),
            ]
            provider_options = {pt[0]: pt[1] for pt in provider_types}

            def rebuild_search_providers() -> None:
                providers_container.clear()
                with providers_container:
                    if not search_providers:
                        with ui.column().classes("items-center py-4"):
                            ui.icon("search_off", size="xl").classes("text-gray-300 mb-2")
                            ui.label(t("ai.no_search_providers")).classes("text-gray-400")
                    else:
                        for idx, provider in enumerate(search_providers):
                            with (
                                ui.card().classes(
                                    "w-full p-4 bg-gray-50 border border-gray-100 rounded-lg"
                                ),
                                ui.row().classes("items-start justify-between gap-4"),
                            ):
                                with ui.column().classes("gap-3 flex-grow"):
                                    with ui.row().classes("gap-3 items-center w-full"):
                                        ui.select(
                                            options=provider_options,
                                            label=t("ai.provider_type"),
                                            value=provider.get("provider", "duckduckgo"),
                                        ).bind_value(provider, "provider").props(
                                            "outlined dense"
                                        ).classes("w-48")
                                        ui.number(
                                            t("ai.provider_priority"),
                                            min=0,
                                            max=100,
                                            value=provider.get("priority", 100),
                                        ).bind_value(provider, "priority").props(
                                            "outlined dense"
                                        ).classes("w-32")
                                        ui.switch(t("ai.provider_enabled")).bind_value(
                                            provider, "enabled"
                                        )

                                    # API Key (not needed for DuckDuckGo)
                                    if provider.get("provider") != "duckduckgo":
                                        with ui.row().classes("gap-3 w-full"):
                                            ui.input(
                                                t("ai.provider_api_key"),
                                                value=provider.get("api_key", ""),
                                            ).bind_value(provider, "api_key").props(
                                                "outlined dense type=password"
                                            ).classes("flex-1")
                                            # Google needs CX
                                            if provider.get("provider") == "google":
                                                options = provider.setdefault("options", {})
                                                ui.input(
                                                    t("ai.google_cx"),
                                                    value=options.get("cx", ""),
                                                ).bind_value(options, "cx").props(
                                                    "outlined dense"
                                                ).classes("flex-1")

                                def remove_provider(i: int = idx) -> None:
                                    search_providers.pop(i)
                                    rebuild_search_providers()

                                ui.button(icon="delete", on_click=remove_provider).props(
                                    "flat round color=red"
                                )

            rebuild_search_providers()

            def add_search_provider() -> None:
                search_providers.append(
                    {
                        "provider": "duckduckgo",
                        "enabled": True,
                        "priority": len(search_providers) * 10,
                        "api_key": None,
                        "options": {},
                    }
                )
                rebuild_search_providers()

            ui.button(t("ai.add_search_provider"), on_click=add_search_provider, icon="add").props(
                "outline color=primary"
            ).classes("mt-3")

    # Output Validation Configuration Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.output_validation")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.output_validation_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        with ui.column().classes("gap-4 w-full"):
            ui.switch(t("ai.output_validators_enabled")).bind_value(
                cfg_ai, "output_validators_enabled"
            )
            ui.switch(t("ai.retry_on_validation_error")).bind_value(
                cfg_ai, "retry_on_validation_error"
            )

    # Available Models Configuration Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.available_models")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.available_models_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        available_models_list = cfg_ai.setdefault("available_models", [])
        available_models_container = ui.column().classes("gap-2 w-full")

        def rebuild_available_models() -> None:
            available_models_container.clear()
            with available_models_container:
                if not available_models_list:
                    ui.label(t("ai.no_available_models")).classes("text-gray-400 text-sm")
                else:
                    with ui.row().classes("gap-2 flex-wrap"):
                        for idx, model in enumerate(available_models_list):
                            with ui.row().classes("items-center gap-1"):
                                ui.chip(model, color="green").classes("px-3")

                                def remove_model(i: int = idx) -> None:
                                    available_models_list.pop(i)
                                    rebuild_available_models()

                                ui.button(icon="close", on_click=remove_model).props(
                                    "flat round dense size=sm color=red"
                                )

        rebuild_available_models()

        with ui.row().classes("items-center gap-2 mt-3"):
            new_model = (
                ui.select(AVAILABLE_MODELS, label=t("ai.add_available_model"))
                .props("outlined dense")
                .classes("w-64")
            )

            def add_available_model() -> None:
                if new_model.value and new_model.value not in available_models_list:
                    available_models_list.append(new_model.value)
                    rebuild_available_models()
                    new_model.value = None

            ui.button(t("common.add"), on_click=add_available_model, icon="add").props("outline")

    # Provider Advanced Settings Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.provider_advanced")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.provider_advanced_desc")).classes("text-gray-500 mt-1")

    with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6 w-full"):
        # Timeout and retry settings
        with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("ai.timeout_retry")).classes("text-lg font-semibold text-gray-800 mb-4")
            provider_cfg = cfg_ai.setdefault("provider_config", {})
            with ui.column().classes("gap-4 w-full"):
                ui.number(t("ai.request_timeout"), min=1, max=300).bind_value(
                    provider_cfg, "timeout"
                ).props("outlined").classes("w-full")
                ui.number(t("ai.provider_max_retries"), min=0, max=10).bind_value(
                    provider_cfg, "max_retries"
                ).props("outlined").classes("w-full")
                ui.input(t("ai.api_version")).bind_value(provider_cfg, "api_version").props(
                    "outlined clearable"
                ).classes("w-full")

        # Streaming settings
        with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("ai.streaming_config")).classes("text-lg font-semibold text-gray-800 mb-4")
            streaming_cfg = cfg_ai.setdefault("streaming", {})
            with ui.column().classes("gap-4 w-full"):
                ui.switch(t("ai.streaming_enabled")).bind_value(streaming_cfg, "enabled")
                ui.number(t("ai.debounce_ms"), min=0, max=1000).bind_value(
                    streaming_cfg, "debounce_ms"
                ).props("outlined").classes("w-full")

    # Command Configuration Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.command_config")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.command_config_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        command_cfg = cfg_ai.setdefault("commands", {})
        with ui.column().classes("gap-4 w-full"):
            ui.input(t("ai.command_prefix")).bind_value(command_cfg, "prefix").props(
                "outlined"
            ).classes("w-48").tooltip(t("ai.command_prefix_hint"))

            ui.label(t("ai.builtin_commands")).classes("text-md font-semibold text-gray-700 mt-2")
            ui.label(t("ai.builtin_commands_desc")).classes("text-sm text-gray-500 mb-2")

            builtin_commands = [
                ("/help", t("ai.cmd_help_desc")),
                ("/reset", t("ai.cmd_reset_desc")),
                ("/history", t("ai.cmd_history_desc")),
                ("/model", t("ai.cmd_model_desc")),
                ("/stats", t("ai.cmd_stats_desc")),
                ("/clear", t("ai.cmd_clear_desc")),
            ]
            with ui.element("div").classes("grid grid-cols-1 md:grid-cols-2 gap-2"):
                for cmd, desc in builtin_commands:
                    with ui.row().classes("items-center gap-2 p-2 bg-gray-50 rounded"):
                        ui.chip(cmd, color="blue").classes("font-mono")
                        ui.label(desc).classes("text-sm text-gray-600")

    # Additional Headers Configuration
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.additional_headers")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.additional_headers_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("w-full p-6 bg-white border border-gray-200 rounded-xl shadow-sm mb-6"):
        provider_cfg = cfg_ai.setdefault("provider_config", {})
        headers_dict = provider_cfg.setdefault("additional_headers", {})
        headers_list = [{"key": k, "value": v} for k, v in headers_dict.items()]
        headers_container = ui.column().classes("gap-2 w-full")

        def rebuild_headers() -> None:
            headers_container.clear()
            # Sync back to dict
            headers_dict.clear()
            for h in headers_list:
                if h.get("key"):
                    headers_dict[h["key"]] = h.get("value", "")

            with headers_container:
                if not headers_list:
                    ui.label(t("ai.no_headers")).classes("text-gray-400 text-sm")
                else:
                    for idx, header in enumerate(headers_list):
                        with ui.row().classes("items-center gap-2 w-full"):
                            ui.input(t("ai.header_key")).bind_value(header, "key").props(
                                "outlined dense"
                            ).classes("flex-1")
                            ui.input(t("ai.header_value")).bind_value(header, "value").props(
                                "outlined dense"
                            ).classes("flex-1")

                            def remove_header(i: int = idx) -> None:
                                headers_list.pop(i)
                                rebuild_headers()

                            ui.button(icon="delete", on_click=remove_header).props(
                                "flat round dense color=red"
                            )

        rebuild_headers()

        def add_header() -> None:
            headers_list.append({"key": "", "value": ""})
            rebuild_headers()

        ui.button(t("ai.add_header"), on_click=add_header, icon="add").props("outline").classes(
            "mt-3"
        )

    # Test Conversation Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.test_conversation")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.test_conversation_desc")).classes("text-gray-500 mt-1")

    with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6 w-full"):
        # Test input card
        with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            ui.label(t("ai.enter_message")).classes("text-lg font-semibold text-gray-800 mb-4")
            test_input = (
                ui.textarea(placeholder=t("ai.test_placeholder"))
                .classes("w-full")
                .props("outlined auto-grow rows=6")
            )
            response_area = (
                ui.textarea(t("ai.response"))
                .classes("w-full mt-4")
                .props("outlined readonly auto-grow rows=6")
            )

            async def send_ai_test() -> None:
                if not controller.bot or not controller.bot.ai_agent:
                    ui.notify(t("ai.bot_not_configured"), type="warning")
                    return
                if not test_input.value:
                    ui.notify(t("common.warning"), type="warning")
                    return
                try:
                    ui.notify(t("common.loading"), type="info")
                    response = await controller.bot.ai_agent.chat(test_input.value)
                    response_area.value = response if response else t("ai.no_response")
                    ui.notify(t("common.success"), type="positive")
                except Exception as e:
                    response_area.value = f"{t('common.error')}: {e}"
                    ui.notify(f"{t('common.error')}: {e}", type="negative")

            with ui.row().classes("gap-2 mt-4"):
                ui.button(t("ai.send"), on_click=send_ai_test, icon="send").props("color=primary")
                ui.button(
                    t("ai.clear"),
                    on_click=lambda: (
                        setattr(test_input, "value", ""),
                        setattr(response_area, "value", ""),
                    ),
                    icon="clear",
                ).props("outline")

        # Tools and status card
        with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm"):
            # Registered tools
            with ui.row().classes("items-center justify-between mb-4"):
                ui.label(t("ai.registered_tools")).classes("text-lg font-semibold text-gray-800")
                ui.button(icon="refresh", on_click=lambda: rebuild_tools()).props(
                    "flat round dense"
                )
            tools_container = ui.column().classes("gap-2 w-full mb-6")

            def rebuild_tools() -> None:
                tools_container.clear()
                with tools_container:
                    if not controller.bot or not controller.bot.ai_agent:
                        with ui.column().classes("items-center py-4"):
                            ui.icon("build_circle", size="lg").classes("text-gray-300 mb-2")
                            ui.label(t("ai.bot_not_configured")).classes("text-gray-400 text-sm")
                        return
                    try:
                        tool_registry = (
                            controller.bot.ai_agent.tools
                            if hasattr(controller.bot.ai_agent, "tools")
                            else None
                        )
                        if not tool_registry:
                            with ui.column().classes("items-center py-4"):
                                ui.icon("build_circle", size="lg").classes("text-gray-300 mb-2")
                                ui.label(t("ai.no_tools")).classes("text-gray-400 text-sm")
                            return
                        tools = (
                            tool_registry.list_tools()
                            if hasattr(tool_registry, "list_tools")
                            else []
                        )
                        if not tools:
                            with ui.column().classes("items-center py-4"):
                                ui.icon("build_circle", size="lg").classes("text-gray-300 mb-2")
                                ui.label(t("ai.no_tools")).classes("text-gray-400 text-sm")
                            return
                        with ui.row().classes("gap-2 flex-wrap"):
                            for tool_name in tools:
                                ui.chip(tool_name, color="blue").classes("px-3 py-1")
                    except Exception as e:
                        ui.label(f"{t('common.error')}: {e}").classes("text-red-500 text-sm")

            rebuild_tools()

            # Connected MCP servers
            with ui.row().classes("items-center justify-between mb-4"):
                ui.label(t("ai.connected_mcp")).classes("text-lg font-semibold text-gray-800")
                ui.button(icon="refresh", on_click=lambda: rebuild_mcp_status()).props(
                    "flat round dense"
                )
            mcp_status_container = ui.column().classes("gap-2 w-full")

            def rebuild_mcp_status() -> None:
                mcp_status_container.clear()
                with mcp_status_container:
                    stats = controller.get_ai_stats()
                    mcp_servers = stats["mcp_servers"]
                    if not mcp_servers:
                        with ui.column().classes("items-center py-4"):
                            ui.icon("dns", size="lg").classes("text-gray-300 mb-2")
                            ui.label(t("ai.no_mcp")).classes("text-gray-400 text-sm")
                        return
                    with ui.row().classes("gap-2 flex-wrap"):
                        for server in mcp_servers:
                            ui.chip(server, color="green").classes("px-3 py-1")

            rebuild_mcp_status()

    # Performance Statistics Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.performance_stats")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.performance_stats_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm w-full mb-6"):
        perf_stats_container = ui.column().classes("w-full")

        def rebuild_perf_stats() -> None:
            perf_stats_container.clear()
            with perf_stats_container:
                stats = controller.get_ai_performance_stats()
                if "error" in stats:
                    ui.label(f"{t('common.error')}: {stats['error']}").classes("text-red-500")
                    return

                with ui.element("div").classes("grid grid-cols-2 md:grid-cols-4 gap-4"):
                    # Total requests
                    with ui.card().classes("p-4 bg-blue-50 rounded-lg"):
                        ui.label(t("ai.total_requests")).classes("text-sm text-gray-600")
                        ui.label(str(stats.get("total_requests", 0))).classes(
                            "text-2xl font-bold text-blue-600"
                        )

                    # Success rate
                    with ui.card().classes("p-4 bg-green-50 rounded-lg"):
                        ui.label(t("ai.success_rate")).classes("text-sm text-gray-600")
                        rate = stats.get("success_rate_percent", 0)
                        color = "green" if rate >= 90 else "yellow" if rate >= 70 else "red"
                        ui.label(f"{rate}%").classes(f"text-2xl font-bold text-{color}-600")

                    # Average response time
                    with ui.card().classes("p-4 bg-purple-50 rounded-lg"):
                        ui.label(t("ai.avg_response_time")).classes("text-sm text-gray-600")
                        avg_time = stats.get("average_response_time_seconds", 0)
                        ui.label(f"{avg_time:.2f}s").classes("text-2xl font-bold text-purple-600")

                    # Total tokens
                    with ui.card().classes("p-4 bg-orange-50 rounded-lg"):
                        ui.label(t("ai.total_tokens")).classes("text-sm text-gray-600")
                        tokens = stats.get("total_tokens", 0)
                        ui.label(f"{tokens:,}").classes("text-2xl font-bold text-orange-600")

                # Token breakdown
                with ui.row().classes("mt-4 gap-4"):
                    ui.label(
                        f"{t('ai.input_tokens')}: {stats.get('total_input_tokens', 0):,}"
                    ).classes("text-sm text-gray-600")
                    ui.label(
                        f"{t('ai.output_tokens')}: {stats.get('total_output_tokens', 0):,}"
                    ).classes("text-sm text-gray-600")
                    ui.label(
                        f"{t('ai.successful')}: {stats.get('successful_requests', 0)} | "
                        f"{t('ai.failed')}: {stats.get('failed_requests', 0)}"
                    ).classes("text-sm text-gray-600")

        rebuild_perf_stats()
        ui.button(t("common.refresh"), on_click=rebuild_perf_stats, icon="refresh").props(
            "outline"
        ).classes("mt-4")

    # Active Conversations Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.active_conversations")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.active_conversations_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm w-full mb-6"):
        conv_container = ui.column().classes("w-full")

        def rebuild_conversations() -> None:
            conv_container.clear()
            with conv_container:
                conversations = controller.list_ai_conversations()
                if not conversations:
                    with ui.column().classes("items-center py-8"):
                        ui.icon("chat_bubble_outline", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("ai.no_conversations")).classes("text-gray-400")
                    return

                # Table header
                with ui.row().classes("w-full bg-gray-100 p-3 rounded-t-lg font-semibold text-sm"):
                    ui.label(t("ai.user_id")).classes("flex-1")
                    ui.label(t("ai.messages")).classes("w-20 text-center")
                    ui.label(t("ai.tokens")).classes("w-24 text-center")
                    ui.label(t("ai.last_activity")).classes("w-36")
                    ui.label(t("ai.actions")).classes("w-24 text-center")

                # Table rows
                for conv in conversations:
                    with ui.row().classes(
                        "w-full p-3 border-b border-gray-100 items-center hover:bg-gray-50"
                    ):
                        ui.label(
                            conv["user_id"][:20] + "..."
                            if len(conv["user_id"]) > 20
                            else conv["user_id"]
                        ).classes("flex-1 text-sm")
                        ui.label(str(conv["message_count"])).classes("w-20 text-center text-sm")
                        ui.label(f"{conv['total_tokens']:,}").classes("w-24 text-center text-sm")
                        last_activity = conv.get("last_activity", "N/A")
                        if last_activity and last_activity != "N/A":
                            last_activity = last_activity[:16].replace("T", " ")
                        ui.label(last_activity).classes("w-36 text-sm text-gray-500")

                        with ui.row().classes("w-24 justify-center gap-1"):

                            async def clear_conv(uid: str = conv["user_id"]) -> None:
                                result = await controller.clear_ai_conversation(uid)
                                if result.get("success"):
                                    ui.notify(t("common.success"), type="positive")
                                    rebuild_conversations()
                                else:
                                    ui.notify(
                                        result.get("error", t("common.error")), type="negative"
                                    )

                            async def delete_conv(uid: str = conv["user_id"]) -> None:
                                result = await controller.delete_ai_conversation(uid)
                                if result.get("success"):
                                    ui.notify(t("common.success"), type="positive")
                                    rebuild_conversations()
                                else:
                                    ui.notify(
                                        result.get("error", t("common.error")), type="negative"
                                    )

                            ui.button(icon="clear_all", on_click=clear_conv).props(
                                "flat round dense color=orange"
                            ).tooltip(t("ai.clear_history"))
                            ui.button(icon="delete", on_click=delete_conv).props(
                                "flat round dense color=red"
                            ).tooltip(t("ai.delete_conversation"))

        rebuild_conversations()
        ui.button(t("common.refresh"), on_click=rebuild_conversations, icon="refresh").props(
            "outline"
        ).classes("mt-4")

    # Tool Details Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.tool_details")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.tool_details_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm w-full mb-6"):
        tool_details_container = ui.column().classes("w-full")

        def rebuild_tool_details() -> None:
            tool_details_container.clear()
            with tool_details_container:
                tools = controller.get_ai_tool_list()
                if not tools:
                    with ui.column().classes("items-center py-8"):
                        ui.icon("build_circle", size="xl").classes("text-gray-300 mb-2")
                        ui.label(t("ai.no_tools")).classes("text-gray-400")
                    return

                tool_stats = controller.get_ai_tool_stats()

                # Summary stats
                with ui.row().classes("gap-4 mb-4"):
                    ui.label(f"{t('ai.total_tools')}: {tool_stats.get('total_tools', 0)}").classes(
                        "text-sm bg-blue-100 px-3 py-1 rounded-full"
                    )
                    ui.label(f"{t('ai.total_usage')}: {tool_stats.get('total_usage', 0)}").classes(
                        "text-sm bg-green-100 px-3 py-1 rounded-full"
                    )
                    error_rate = tool_stats.get("error_rate_percent", 0)
                    ui.label(f"{t('ai.error_rate')}: {error_rate}%").classes(
                        f"text-sm {'bg-red-100' if error_rate > 10 else 'bg-gray-100'} px-3 py-1 rounded-full"
                    )

                # Tool cards
                with ui.element("div").classes(
                    "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4"
                ):
                    for tool in tools:
                        with ui.card().classes("p-4 border border-gray-200 rounded-lg"):
                            with ui.row().classes("items-center gap-2 mb-2"):
                                ui.icon("build", size="sm").classes("text-blue-500")
                                ui.label(tool.get("name", "Unknown")).classes("font-semibold")
                            ui.label(tool.get("description", "No description")[:100]).classes(
                                "text-sm text-gray-600 mb-2"
                            )
                            with ui.row().classes("gap-2 text-xs"):
                                ui.chip(tool.get("category", "general"), color="blue").props(
                                    "dense"
                                )
                                ui.label(f"{t('ai.usage')}: {tool.get('usage_count', 0)}").classes(
                                    "text-gray-500"
                                )
                                if tool.get("error_count", 0) > 0:
                                    ui.label(
                                        f"{t('ai.errors')}: {tool.get('error_count', 0)}"
                                    ).classes("text-red-500")

        rebuild_tool_details()
        ui.button(t("common.refresh"), on_click=rebuild_tool_details, icon="refresh").props(
            "outline"
        ).classes("mt-4")

    # Multi-Agent Status Section
    with ui.column().classes("w-full mb-4"):
        ui.label(t("ai.multi_agent_status")).classes("text-xl font-semibold text-gray-800")
        ui.label(t("ai.multi_agent_status_desc")).classes("text-gray-500 mt-1")

    with ui.card().classes("p-6 bg-white border border-gray-200 rounded-xl shadow-sm w-full mb-6"):
        ma_status_container = ui.column().classes("w-full")

        def rebuild_ma_status() -> None:
            ma_status_container.clear()
            with ma_status_container:
                status = controller.get_multi_agent_status()
                if "error" in status:
                    ui.label(f"{t('common.error')}: {status['error']}").classes("text-red-500")
                    return

                with ui.row().classes("gap-4 items-center mb-4"):
                    enabled = status.get("enabled", False)
                    ui.chip(
                        t("ai.enabled") if enabled else t("ai.disabled"),
                        color="green" if enabled else "gray",
                    ).classes("px-3 py-1")
                    ui.label(f"{t('ai.orchestration_mode')}: {status.get('mode', 'N/A')}").classes(
                        "text-sm text-gray-600"
                    )
                    ui.label(f"{t('ai.agent_count')}: {status.get('agent_count', 0)}").classes(
                        "text-sm text-gray-600"
                    )

                agents = status.get("agents", [])
                if agents:
                    ui.label(t("ai.registered_agents")).classes("font-semibold mt-4 mb-2")
                    with ui.row().classes("gap-2 flex-wrap"):
                        for agent in agents:
                            with ui.chip(color="purple").classes("px-3 py-1"):
                                ui.label(
                                    f"{agent.get('name', 'Unknown')} ({agent.get('role', 'N/A')})"
                                )

        rebuild_ma_status()
        ui.button(t("common.refresh"), on_click=rebuild_ma_status, icon="refresh").props(
            "outline"
        ).classes("mt-4")
