# ruff: noqa: E501

"""NiceGUI-based configuration and control panel for Feishu Webhook Bot.

This module provides a local web UI to:
- View and edit bot configuration (YAML)
- Start / Stop / Restart the bot
- Show current status and recent logs

Usage (CLI will wire this as `feishu-webhook-bot webui`):
    python -m feishu_webhook_bot.config_ui --config config.yaml --host 127.0.0.1 --port 8080
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from nicegui import app, ui

from .bot import FeishuBot
from .core import BotConfig, get_logger

log = get_logger("webui")


# ------------------------------
# Bot lifecycle controller
# ------------------------------


class UIMemoryLogHandler(logging.Handler):
    """A logging handler that stores recent records in a deque for the UI.

    Stores tuples of (levelno, formatted_message) to allow filtering by level.
    """

    def __init__(self, ring: deque[tuple[int, str]], max_level: int = logging.INFO) -> None:
        super().__init__(max_level)
        self.ring = ring
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.ring.append((record.levelno, msg))
        except Exception:
            # Do not break logging on UI issues
            pass


@dataclass
class BotController:
    """Manage bot instance, thread, config IO, and live logs."""

    config_path: Path
    bot: FeishuBot | None = None
    thread: threading.Thread | None = None
    running: bool = False
    _stop_event: threading.Event = field(default_factory=threading.Event)

    # logs
    log_lines: deque[tuple[int, str]] = field(default_factory=lambda: deque(maxlen=500))
    _ui_handler: UIMemoryLogHandler | None = None

    def load_config(self) -> BotConfig:
        """Load configuration from YAML; create default if file missing."""
        if not self.config_path.exists():
            # Create a default config based on project defaults
            cfg = BotConfig()
            self.save_config(cfg)
            return cfg
        return BotConfig.from_yaml(self.config_path)

    def save_config(self, config: BotConfig) -> None:
        """Persist configuration to YAML with validation via Pydantic."""
        data = config.to_dict()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    # ---- Bot control
    def _attach_ui_logger(self) -> None:
        """Attach an in-memory handler to the root logger so UI can display live logs.

        Note: the bot's setup_logging clears handlers in its initialization; therefore
        we attach this handler AFTER the bot instance is created.
        """

        if self._ui_handler is not None:
            # Already attached
            return

        self._ui_handler = UIMemoryLogHandler(self.log_lines)
        root = logging.getLogger()
        root.addHandler(self._ui_handler)

    def _detach_ui_logger(self) -> None:
        if self._ui_handler is None:
            return
        root = logging.getLogger()
        with suppress(Exception):
            root.removeHandler(self._ui_handler)
        self._ui_handler = None

    def start(self) -> None:
        if self.running:
            return

        cfg = self.load_config()

        # Create bot instance (this configures logging inside)
        self.bot = FeishuBot(cfg)
        self._attach_ui_logger()

        def target() -> None:
            try:
                # Run bot.start() which blocks until stopped
                assert self.bot is not None
                self.bot.start()
            except Exception as e:  # pragma: no cover - UI runtime safety
                log.error(f"Bot thread error: {e}")
            finally:
                self.running = False

        self._stop_event.clear()
        self.thread = threading.Thread(target=target, name="feishu-bot-thread", daemon=True)
        self.thread.start()
        self.running = True

    def stop(self, join_timeout: float = 5.0) -> None:
        if not self.running:
            return

        try:
            if self.bot:
                self.bot.stop()
        finally:
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=join_timeout)
            self.running = False

    def restart(self) -> None:
        self.stop()
        self.start()

    def status(self) -> dict[str, Any]:
        plugins = []
        scheduler_running = False
        if self.bot and self.bot.plugin_manager:
            plugins = self.bot.plugin_manager.list_plugins()
        if self.bot and self.bot.scheduler and self.bot.scheduler._scheduler:
            scheduler_running = self.bot.scheduler._scheduler.running
        return {
            "running": self.running,
            "plugins": plugins,
            "scheduler_running": scheduler_running,
        }

    # Convenience helpers used by UI actions
    def set_runtime_log_level(self, level_name: str) -> None:
        level = getattr(logging, level_name.upper(), logging.INFO)
        root = logging.getLogger()
        root.setLevel(level)
        # update handler levels as well
        for handler in root.handlers:
            with suppress(Exception):
                handler.setLevel(level)
        # Also set our library root
        logging.getLogger("feishu_bot").setLevel(level)

    def send_test_message(self, text: str, webhook_name: str) -> None:
        # Prefer using the bot if available to stay consistent
        if self.bot is not None:
            self.bot.send_message(text, webhook_name=webhook_name)
            return
        # Fallback: send using a temporary client
        cfg = self.load_config()
        webhook = cfg.get_webhook(webhook_name) or (cfg.webhooks[0] if cfg.webhooks else None)
        if not webhook:
            raise ValueError("No webhook configured")
        from .core.client import FeishuWebhookClient

        with FeishuWebhookClient(webhook) as client:
            client.send_text(text)

    # ---- Data getters for dashboards
    def get_ai_stats(self) -> dict[str, Any]:
        """Get AI agent statistics."""
        if not self.bot or not self.bot.ai_agent:
            return {
                "enabled": False,
                "current_model": "N/A",
                "requests": 0,
                "success_rate": 0.0,
                "tokens_used": 0,
                "mcp_servers": [],
            }
        try:
            stats = self.bot.ai_agent.get_stats() if hasattr(self.bot.ai_agent, "get_stats") else {}
            mcp_servers = []
            if self.bot.ai_agent.mcp_client:
                mcp_servers = self.bot.ai_agent.mcp_client.get_server_names()
            return {
                "enabled": True,
                "current_model": self.bot.config.ai.model if self.bot.config.ai else "N/A",
                "requests": stats.get("requests", 0),
                "success_rate": stats.get("success_rate", 0.0),
                "tokens_used": stats.get("tokens_used", 0),
                "mcp_servers": mcp_servers,
            }
        except Exception:
            return {
                "enabled": False,
                "current_model": "Error",
                "requests": 0,
                "success_rate": 0.0,
                "tokens_used": 0,
                "mcp_servers": [],
            }

    def get_task_list(self) -> list[dict[str, Any]]:
        """Get list of configured tasks."""
        if not self.bot or not self.bot.config or not self.bot.config.tasks:
            return []
        tasks = []
        for task_cfg in self.bot.config.tasks:
            tasks.append({
                "name": task_cfg.name,
                "description": task_cfg.description or "",
                "enabled": True,
                "next_run": "N/A",
            })
        return tasks

    def get_automation_rules(self) -> list[dict[str, Any]]:
        """Get list of automation rules."""
        if not self.bot or not self.bot.config or not self.bot.config.automations:
            return []
        rules = []
        for auto_cfg in self.bot.config.automations:
            rules.append({
                "name": auto_cfg.name,
                "trigger": auto_cfg.trigger if hasattr(auto_cfg, "trigger") else "event",
                "enabled": True,
                "status": "Ready",
            })
        return rules

    def get_provider_list(self) -> list[dict[str, Any]]:
        """Get list of providers."""
        if not self.bot:
            return []
        providers = []
        for name, provider in self.bot.providers.items():
            providers.append({
                "name": name,
                "type": provider.__class__.__name__,
                "status": "Connected",
            })
        return providers

    def get_message_stats(self) -> dict[str, Any]:
        """Get message statistics."""
        if not self.bot:
            return {
                "queue_size": 0,
                "queued": 0,
                "pending": 0,
                "failed": 0,
                "success": 0,
            }
        try:
            queue_stats = {}
            if self.bot.message_queue:
                queue_stats = self.bot.message_queue.get_queue_stats()

            tracker_stats = {}
            if self.bot.message_tracker:
                tracker_stats = self.bot.message_tracker.get_statistics()

            return {
                "queue_size": queue_stats.get("queue_size", 0),
                "queued": queue_stats.get("queued", 0),
                "pending": tracker_stats.get("pending", 0),
                "failed": tracker_stats.get("failed", 0),
                "success": tracker_stats.get("success", 0),
            }
        except Exception:
            return {
                "queue_size": 0,
                "queued": 0,
                "pending": 0,
                "failed": 0,
                "success": 0,
            }

    def get_user_list(self) -> list[dict[str, Any]]:
        """Get list of users (if auth is enabled)."""
        from .auth.service import AuthService

        users = []
        try:
            auth_service = AuthService()
            # Get all users from database
            from .auth.database import DatabaseManager

            db_manager = DatabaseManager()
            with db_manager.get_session() as session:
                from .auth.models import User

                user_objs = session.query(User).all()
                for user in user_objs:
                    users.append({
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "status": "Active" if not user.locked else "Locked",
                    })
        except Exception:
            pass
        return users

    def get_event_server_status(self) -> dict[str, Any]:
        """Get event server status."""
        if not self.bot or not self.bot.event_server:
            return {
                "running": False,
                "host": "N/A",
                "port": 0,
                "recent_events": [],
            }
        try:
            return {
                "running": getattr(self.bot.event_server, "running", False),
                "host": self.bot.config.event_server.host if self.bot.config.event_server else "N/A",
                "port": self.bot.config.event_server.port if self.bot.config.event_server else 0,
                "recent_events": [],
            }
        except Exception:
            return {
                "running": False,
                "host": "N/A",
                "port": 0,
                "recent_events": [],
            }


# ------------------------------
# UI helpers and page
# ------------------------------


def _config_to_form(cfg: BotConfig) -> dict[str, Any]:
    data = cfg.to_dict()
    # Ensure keys exist for predictable UI
    data.setdefault("general", {})
    data.setdefault("webhooks", [])
    data.setdefault("scheduler", {})
    data.setdefault("plugins", {})
    data.setdefault("logging", {})
    data.setdefault("templates", [])
    data.setdefault("notifications", [])
    return data


def _form_to_config(data: dict[str, Any]) -> BotConfig:
    # Let Pydantic validate and coerce types
    return BotConfig(**data)


def _webhook_card(item: dict[str, Any], on_remove: Callable[[], None] | None = None) -> None:
    with ui.card().classes("w-full p-4 bg-white rounded-lg shadow-sm border border-gray-200"):
        # Responsive 12-col grid: name(3), url(6), secret(2), delete(1)
        grid = ui.element("div").classes(
            "grid grid-cols-12 gap-x-4 gap-y-3 w-full items-end md:items-center"
        )
        with grid:
            ui.input("Name", validation={"Required": lambda v: bool(v and v.strip())}).bind_value(
                item, "name"
            ).props("dense clearable").classes("col-span-12 md:col-span-4 lg:col-span-3")
            ui.input(
                "URL",
                validation={
                    "Required": lambda v: bool(v and v.strip()),
                    "Must start with http(s)": lambda v: (v or "").startswith("http"),
                },
            ).bind_value(item, "url").props("dense clearable").classes(
                "col-span-12 md:col-span-8 lg:col-span-6"
            )
            ui.input("Secret (optional)").bind_value(item, "secret").props(
                "dense clearable"
            ).classes("col-span-12 lg:col-span-2")
            if on_remove:
                with ui.element("div").classes(
                    "col-span-12 lg:col-span-1 flex justify-end lg:justify-center items-center"
                ):
                    ui.button(icon="delete", color="negative", on_click=lambda: on_remove()).props(
                        "flat round dense"
                    )


TEMPLATE_TYPES = ["text", "markdown", "card", "post", "interactive", "json"]


def _template_card(item: dict[str, Any], on_remove: Callable[[], None] | None = None) -> None:
    item.setdefault("name", "new-template")
    item.setdefault("type", "text")
    item.setdefault("engine", "string")
    item.setdefault("description", "")
    item.setdefault("content", "")

    with ui.card().classes("w-full p-4 bg-white rounded-lg shadow-sm border border-gray-200 gap-3"):
        with ui.row().classes("items-end gap-3 flex-wrap"):
            ui.input("Name", validation={"Required": lambda v: bool(v and v.strip())}).bind_value(
                item, "name"
            ).props("dense")
            ui.select(TEMPLATE_TYPES, label="Type").bind_value(item, "type").props("dense")
            ui.select(["string", "format"], label="Engine").bind_value(item, "engine").props(
                "dense"
            )
            ui.input("Description (optional)").bind_value(item, "description").props(
                "dense"
            ).classes("grow")
            if on_remove:
                ui.button(icon="delete", color="negative", on_click=lambda: on_remove()).props(
                    "flat round dense"
                )

        ui.textarea("Content").bind_value(item, "content").classes("w-full").props("auto-grow")


def _notification_card(item: dict[str, Any], on_remove: Callable[[], None] | None = None) -> None:
    item.setdefault("name", "new-notification")
    item.setdefault("trigger", "")
    item.setdefault("conditions", [])
    item.setdefault("template", "")

    with ui.card().classes("w-full p-4 bg-white rounded-lg shadow-sm border border-gray-200 gap-3"):
        with ui.row().classes("items-end gap-3 flex-wrap"):
            ui.input("Name", validation={"Required": lambda v: bool(v and v.strip())}).bind_value(
                item, "name"
            ).props("dense")
            ui.input("Trigger", placeholder="e.g. event.message").bind_value(item, "trigger").props(
                "dense"
            )
            ui.input("Template name").bind_value(item, "template").props("dense")
            if on_remove:
                ui.button(icon="delete", color="negative", on_click=lambda: on_remove()).props(
                    "flat round dense"
                )

        conditions_box = (
            ui.textarea("Conditions (one per line)")
            .classes("w-full")
            .props("autocomplete=off auto-grow")
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
    container = ui.column().classes("w-full gap-4")

    def rebuild() -> None:
        container.clear()
        with container:
            for idx, item in enumerate(item_list):

                def remove_item(i: int = idx) -> None:
                    item_list.pop(i)
                    rebuild()

                card_builder(item, remove_item)

    rebuild()

    with ui.row().classes("items-center gap-2 flex-wrap pt-1"):

        def add_and_rebuild() -> None:
            item_list.append(default_item.copy())
            rebuild()

        ui.button(
            add_button_text,
            on_click=add_and_rebuild,
        ).props("outline")

    return rebuild


def build_ui(config_path: Path) -> None:
    controller = BotController(config_path=config_path)

    # Reactive state
    state: dict[str, Any] = {"form": _config_to_form(controller.load_config())}

    async def reload_from_disk() -> None:
        try:
            cfg = controller.load_config()
            state["form"] = _config_to_form(cfg)
            ui.notify("Configuration reloaded", type="positive")
            await ui.run_javascript("location.reload()")  # rebuild UI bindings
        except Exception as e:
            ui.notify(f"Failed to reload: {e}", type="negative")

    async def save_to_disk() -> None:
        try:
            cfg = _form_to_config(state["form"])  # validation happens here
            controller.save_config(cfg)
            ui.notify("Configuration saved", type="positive")
        except Exception as e:
            ui.notify(f"Validation or save error: {e}", type="negative")

    async def on_start() -> None:
        try:
            controller.start()
            ui.notify("Bot started", type="positive")
        except Exception as e:
            ui.notify(f"Start failed: {e}", type="negative")

    async def on_stop() -> None:
        try:
            controller.stop()
            ui.notify("Bot stopped", type="positive")
        except Exception as e:
            ui.notify(f"Stop failed: {e}", type="negative")

    async def on_restart() -> None:
        try:
            controller.restart()
            ui.notify("Bot restarted", type="positive")
        except Exception as e:
            ui.notify(f"Restart failed: {e}", type="negative")

    # Layout
    with (
        ui.header(elevated=True)
        .style("background:linear-gradient(90deg,#4f86ed,#3a6fd6)")
        .classes("px-4 py-2"),
        ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"),
    ):
        with ui.column().classes("gap-1 text-white"):
            with ui.row().classes("items-center gap-3 flex-wrap"):
                ui.label("Feishu Webhook Bot").classes("text-h6 font-medium text-white")
                ui.label("Configuration & Control").classes("text-white/90")
            with ui.row().classes("items-center gap-2 text-white/80 text-sm flex-wrap"):
                ui.icon("description").classes("text-white/70")
                with ui.element("div").classes("max-w-full md:max-w-xl"):
                    ui.label(str(config_path)).classes("text-white/80 text-sm").style(
                        "max-width: 28rem; overflow:hidden; text-overflow: ellipsis; white-space: nowrap;"
                    )

        with ui.row().classes("items-center gap-2 flex-wrap justify-end"):
            status_chip = ui.chip("Stopped", color="grey", text_color="white").props("outline")
            ui.button("Start", on_click=on_start).props("unelevated color=positive")
            ui.button("Stop", on_click=on_stop).props("unelevated color=negative")
            ui.button("Restart", on_click=on_restart).props("unelevated color=warning")
            ui.separator().props("vertical").classes("mx-1 opacity-50")
            ui.button("Save", on_click=save_to_disk).props("unelevated color=primary")
            ui.button("Reset", on_click=reload_from_disk).props(
                "outline color=white text-color=white"
            )
            ui.separator().props("vertical").classes("mx-1 opacity-50")

            async def on_upload(e: Any) -> None:
                try:
                    content = e.content.read().decode("utf-8")
                    new_data = yaml.safe_load(content)
                    if not isinstance(new_data, dict):
                        raise ValueError("Invalid YAML format. Must be a dictionary.")
                    state["form"] = _config_to_form(BotConfig(**new_data))
                    ui.notify("Configuration imported successfully. Reloading...", type="positive")
                    await ui.run_javascript("location.reload()")
                except Exception as ex:
                    ui.notify(f"Import failed: {ex}", type="negative")

            ui.upload(on_upload=on_upload, auto_upload=True).props(
                "flat color=white text-color=white icon=upload"
            ).classes("w-12")

            def on_export() -> None:
                try:
                    cfg = _form_to_config(state["form"])
                    yaml_str = yaml.dump(cfg.to_dict(), sort_keys=False, allow_unicode=True)
                    ui.download(yaml_str.encode("utf-8"), "config.yaml")
                    ui.notify("Configuration exported.", type="positive")
                except Exception as ex:
                    ui.notify(f"Export failed: {ex}", type="negative")

            ui.button("Export", on_click=on_export).props("outline color=white text-color=white")

        with ui.row().classes("items-center gap-2 flex-wrap justify-end"):
            # Profile management
            profiles_dir = config_path.parent / "profiles"
            profiles_dir.mkdir(exist_ok=True)
            profile_files = {p.stem: p for p in profiles_dir.glob("*.yaml")}

            async def save_profile() -> None:
                with ui.dialog() as dialog, ui.card():
                    name_input = ui.input("Profile Name")
                    ui.button("Save", on_click=lambda: dialog.submit(name_input.value))
                profile_name = await dialog
                if profile_name:
                    try:
                        cfg = _form_to_config(state["form"])
                        profile_path = profiles_dir / f"{profile_name}.yaml"
                        with profile_path.open("w", encoding="utf-8") as f:
                            yaml.dump(cfg.to_dict(), f, sort_keys=False, allow_unicode=True)
                        ui.notify(f"Profile '{profile_name}' saved.", type="positive")
                        # Refresh to show new profile entry
                        await ui.run_javascript("location.reload()")
                    except Exception as e:
                        ui.notify(f"Failed to save profile: {e}", type="negative")

            async def load_profile(profile_name: str) -> None:
                if not profile_name:
                    return
                try:
                    profile_path = profile_files[profile_name]
                    with profile_path.open("r", encoding="utf-8") as f:
                        new_data = yaml.safe_load(f)
                    state["form"] = _config_to_form(BotConfig(**new_data))
                    ui.notify(f"Profile '{profile_name}' loaded. Reloading...", type="positive")
                    await ui.run_javascript("location.reload()")
                except Exception as e:
                    ui.notify(f"Failed to load profile: {e}", type="negative")

            ui.button("Save Profile", on_click=save_profile).props(
                "outline color=white text-color=white"
            )
            ui.select(
                list(profile_files.keys()),
                label="Load Profile",
                on_change=lambda event: load_profile(event.value),
            ).props("dense outlined color=white")

    # Page container
    page = ui.column().classes("container mx-auto max-w-6xl w-full px-4 py-4 gap-5")

    with page, ui.tabs().classes("w-full") as tabs:
        t_general = ui.tab("General")
        t_scheduler = ui.tab("Scheduler")
        t_plugins = ui.tab("Plugins")
        t_logging = ui.tab("Logging")
        t_templates = ui.tab("Templates")
        t_notifications = ui.tab("Notifications")
        t_status = ui.tab("Status")
        t_ai = ui.tab("AI Dashboard")
        t_tasks = ui.tab("Tasks")
        t_automation = ui.tab("Automation")
        t_providers = ui.tab("Providers")
        t_messages = ui.tab("Messages")
        t_auth = ui.tab("Auth")
        t_events = ui.tab("Event Server")
        t_logs = ui.tab("Logs")

    with ui.tab_panels(tabs, value=t_general).classes("w-full"):
        # General tab
        with ui.tab_panel(t_general):
            general = state["form"].setdefault("general", {})
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.input("Bot Name").bind_value(general, "name").classes("w-96")
                ui.textarea("Bot Description").bind_value(general, "description").classes("w-full")
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-2"):
                ui.label("Webhook endpoints").classes("text-subtitle1 font-medium")
                ui.label(
                    "Tip: the webhook named 'default' will be used as the default when starting the bot."
                ).classes("text-sm text-gray-500")

            webhook_list: list[dict[str, Any]] = state["form"].setdefault("webhooks", [])
            rebuild_webhooks = build_list_editor(
                item_list=webhook_list,
                card_builder=_webhook_card,
                default_item={"name": "default", "url": "", "secret": None},
                add_button_text="Add webhook",
            )

            def set_default_to_first() -> None:
                if not webhook_list:
                    return
                # rename any existing 'default'
                for wh in webhook_list:
                    if wh.get("name") == "default":
                        wh["name"] = f"wh_{id(wh) % 1000}"
                webhook_list[0]["name"] = "default"
                rebuild_webhooks()
                ui.notify("Set first webhook as default.", type="positive")

            ui.button("Set first as default", on_click=set_default_to_first).props("outline")

        # Scheduler tab
        with ui.tab_panel(t_scheduler):
            sched = state["form"].setdefault("scheduler", {})
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.switch("Enable scheduler").bind_value(sched, "enabled")
                ui.input(
                    "Timezone", validation={"Required": lambda v: bool(v and v.strip())}
                ).bind_value(sched, "timezone").classes("w-80").tooltip(
                    "e.g., Asia/Shanghai, America/New_York"
                )
                ui.select(["memory", "sqlite"], label="Job store type").bind_value(
                    sched, "job_store_type"
                ).classes("w-64").tooltip("'memory' is volatile, 'sqlite' persists jobs to a file.")
                ui.input("Job store path (for sqlite)").bind_value(sched, "job_store_path").classes(
                    "w-96"
                ).tooltip("Required only if job store type is sqlite.")
                ui.label("If 'sqlite' is selected, provide a valid file path.").classes(
                    "text-sm text-gray-500"
                )

        # Plugins tab
        with ui.tab_panel(t_plugins):
            plug = state["form"].setdefault("plugins", {})
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.switch("Enable plugins").bind_value(plug, "enabled")
                ui.input("Plugin directory").bind_value(plug, "plugin_dir").classes("w-96")
                ui.switch("Auto reload (watch plugins)").bind_value(plug, "auto_reload").tooltip(
                    "Automatically reload the bot when plugin files change."
                )
                ui.number("Reload delay (seconds)").bind_value(plug, "reload_delay").props(
                    "step=0.1"
                ).classes("w-64").tooltip(
                    "Wait time before reloading after a file change is detected."
                )

            # Live plugin controls (when running)
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Plugin controls (available when bot is running)").classes("font-medium")
                plugin_controls = ui.column().classes("gap-1")

                def rebuild_plugin_controls() -> None:
                    plugin_controls.clear()
                    with plugin_controls:
                        if not controller.bot or not controller.bot.plugin_manager:
                            ui.label("Bot not running.")
                            return
                        names = controller.bot.plugin_manager.list_plugins()
                        if not names:
                            ui.label("No plugins loaded.")
                            return
                        for name in names:
                            with ui.row().classes("items-center gap-2"):
                                ui.label(name)

                                def on_toggle(n: str = name) -> None:
                                    if not controller.bot or not controller.bot.plugin_manager:
                                        ui.notify("Bot not running", type="warning")
                                        return
                                    pm = controller.bot.plugin_manager
                                    # naive toggle: try disable; if fails, try enable
                                    if pm.disable_plugin(n):
                                        ui.notify(f"Disabled {n}")
                                    elif pm.enable_plugin(n):
                                        ui.notify(f"Enabled {n}")
                                    else:
                                        ui.notify(f"No action on {n}")

                                ui.button("Toggle", on_click=on_toggle).props("dense")
                            ui.separator()

                ui.button("Refresh plugins", on_click=rebuild_plugin_controls).props("flat")

        # Logging tab
        with ui.tab_panel(t_logging):
            log_cfg = state["form"].setdefault("logging", {})
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                level_select = (
                    ui.select(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], label="Log level")
                    .bind_value(log_cfg, "level")
                    .classes("w-64")
                )
                ui.input("Format").bind_value(log_cfg, "format").classes("w-full").tooltip(
                    "Python logging format string."
                )
                ui.input("Log file (optional)").bind_value(log_cfg, "log_file").classes("w-96")
                ui.number("Max bytes").bind_value(log_cfg, "max_bytes").classes("w-64").tooltip(
                    "Maximum log file size in bytes before rotation."
                )
                ui.number("Backup count").bind_value(log_cfg, "backup_count").classes(
                    "w-64"
                ).tooltip("Number of old log files to keep.")
                ui.button(
                    "Apply runtime level",
                    on_click=lambda: controller.set_runtime_log_level(level_select.value or "INFO"),
                )

        # Templates tab
        with ui.tab_panel(t_templates):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-2"):
                ui.label("Message Templates").classes("text-subtitle1 font-medium")
                ui.label("Create and manage message templates for reuse.").classes(
                    "text-sm text-gray-500"
                )

            template_list: list[dict[str, Any]] = state["form"].setdefault("templates", [])
            build_list_editor(
                item_list=template_list,
                card_builder=_template_card,
                default_item={"name": "new-template", "type": "text", "content": ""},
                add_button_text="Add template",
            )

        # Notifications tab
        with ui.tab_panel(t_notifications):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-2"):
                ui.label("Notification Rules").classes("text-subtitle1 font-medium")
                ui.label("Define rules to trigger notifications based on events.").classes(
                    "text-sm text-gray-500"
                )

            notification_list: list[dict[str, Any]] = state["form"].setdefault("notifications", [])
            build_list_editor(
                item_list=notification_list,
                card_builder=_notification_card,
                default_item={
                    "name": "new-notification",
                    "trigger": "",
                    "conditions": [],
                    "template": "",
                },
                add_button_text="Add notification",
            )

        # Status tab
        with ui.tab_panel(t_status):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                status_label = ui.label("")
                plugin_list = ui.column()
                ui.label("")
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Send test message").classes("font-medium")
                cfg_webhooks = state["form"].get("webhooks", [])
                wh_names = [w.get("name", f"wh-{i}") for i, w in enumerate(cfg_webhooks)] or [
                    "default"
                ]
                sel_wh = ui.select(
                    wh_names, value=wh_names[0] if wh_names else None, label="Webhook"
                )
                msg_input = ui.input("Message").props("clearable").classes("w-full")

                async def send_test() -> None:
                    try:
                        if not msg_input.value:
                            ui.notify("Enter message text", type="warning")
                            return
                        controller.send_test_message(
                            msg_input.value, webhook_name=sel_wh.value or "default"
                        )
                        ui.notify("Message sent", type="positive")
                    except Exception as e:
                        ui.notify(f"Send failed: {e}", type="negative")

                ui.button("Send", on_click=send_test)

            async def refresh_status() -> None:
                s = controller.status()
                status_label.text = (
                    f"Bot running: {s['running']} | Scheduler: {s['scheduler_running']}"
                )
                plugin_list.clear()
                with plugin_list:
                    if not s["plugins"]:
                        ui.label("No plugins loaded.")
                    else:
                        for p in s["plugins"]:
                            ui.chip(p)

            # Jobs table
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Scheduled jobs").classes("font-medium")
                jobs_container = ui.column().classes("gap-1")

                def rebuild_jobs() -> None:
                    jobs_container.clear()
                    with jobs_container:
                        if not controller.bot or not controller.bot.scheduler:
                            ui.label("Scheduler not running.")
                            return
                        jobs = controller.bot.scheduler.get_jobs()
                        if not jobs:
                            ui.label("No scheduled jobs.")
                            return
                        for job in jobs:
                            with ui.row().classes("items-center gap-3"):
                                ui.label(job.id)
                                ui.label(f"Next: {job.next_run_time}").classes(
                                    "text-sm text-gray-600"
                                )

                                def _pause(jid: str = job.id) -> None:
                                    if controller.bot and controller.bot.scheduler:
                                        controller.bot.scheduler.pause_job(jid)

                                def _resume(jid: str = job.id) -> None:
                                    if controller.bot and controller.bot.scheduler:
                                        controller.bot.scheduler.resume_job(jid)

                                def _remove(jid: str = job.id) -> None:
                                    if controller.bot and controller.bot.scheduler:
                                        controller.bot.scheduler.remove_job(jid)

                                ui.button("Pause", on_click=_pause)
                                ui.button("Resume", on_click=_resume)
                                ui.button("Remove", color="negative", on_click=_remove)

                ui.button("Refresh status", on_click=refresh_status).props("flat")
                ui.button("Refresh jobs", on_click=rebuild_jobs).props("flat")

        # AI Dashboard tab
        with ui.tab_panel(t_ai):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("AI Agent Configuration").classes("text-subtitle1 font-medium")
                ai_stats = controller.get_ai_stats()

                with ui.row().classes("items-center gap-4 flex-wrap"):
                    ui.chip(f"Enabled: {ai_stats['enabled']}", color="blue")
                    ui.chip(f"Model: {ai_stats['current_model']}", color="blue")

                with ui.row().classes("items-center gap-4 flex-wrap"):
                    ui.label(f"Requests: {ai_stats['requests']}").classes("text-sm")
                    ui.label(f"Success Rate: {ai_stats['success_rate']:.1%}").classes("text-sm")
                    ui.label(f"Tokens Used: {ai_stats['tokens_used']}").classes("text-sm")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Model Selection").classes("font-medium")
                cfg_ai = state["form"].setdefault("ai", {})
                available_models = ["openai:gpt-4o", "openai:gpt-4-turbo", "anthropic:claude-3-opus",
                                   "google:gemini-pro", "groq:mixtral-8x7b"]
                ui.select(
                    available_models,
                    label="Select Model",
                    value=cfg_ai.get("model", available_models[0])
                ).bind_value(cfg_ai, "model").props("outlined")
                ui.input("Provider API Key").bind_value(cfg_ai, "api_key").props("type=password clearable")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Registered Tools").classes("font-medium")
                tools_container = ui.column().classes("gap-1")

                def rebuild_tools() -> None:
                    tools_container.clear()
                    with tools_container:
                        if not controller.bot or not controller.bot.ai_agent:
                            ui.label("Bot not running or AI not configured.").classes("text-gray-500")
                            return
                        try:
                            tool_registry = controller.bot.ai_agent.tools if hasattr(controller.bot.ai_agent, "tools") else None
                            if not tool_registry:
                                ui.label("No tools registered.").classes("text-gray-500")
                                return
                            tools = tool_registry.list_tools() if hasattr(tool_registry, "list_tools") else []
                            if not tools:
                                ui.label("No tools registered.").classes("text-gray-500")
                                return
                            for tool_name in tools:
                                ui.chip(tool_name).classes("w-auto")
                        except Exception as e:
                            ui.label(f"Error loading tools: {e}").classes("text-red-500 text-sm")

                rebuild_tools()
                ui.button("Refresh Tools", on_click=rebuild_tools).props("flat")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("MCP Servers").classes("font-medium")
                mcp_container = ui.column().classes("gap-1")

                def rebuild_mcp() -> None:
                    mcp_container.clear()
                    with mcp_container:
                        ai_stats = controller.get_ai_stats()
                        mcp_servers = ai_stats["mcp_servers"]
                        if not mcp_servers:
                            ui.label("No MCP servers connected.").classes("text-gray-500")
                            return
                        for server in mcp_servers:
                            ui.chip(server).classes("w-auto")

                rebuild_mcp()
                ui.button("Refresh MCP", on_click=rebuild_mcp).props("flat")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Test Conversation").classes("font-medium")
                with ui.row().classes("w-full gap-2"):
                    test_input = ui.textarea("Enter test message").classes("flex-grow h-24")

                    async def send_ai_test() -> None:
                        if not controller.bot or not controller.bot.ai_agent:
                            ui.notify("Bot not running or AI not configured.", type="warning")
                            return
                        if not test_input.value:
                            ui.notify("Please enter a test message.", type="warning")
                            return
                        try:
                            ui.notify("Sending to AI...", type="info")
                            # Note: This would need async handling
                            ui.notify("AI integration ready (streaming requires async handler)", type="info")
                        except Exception as e:
                            ui.notify(f"Error: {e}", type="negative")

                    ui.button("Send", on_click=send_ai_test).props("color=primary")

        # Tasks tab
        with ui.tab_panel(t_tasks):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Configured Tasks").classes("text-subtitle1 font-medium")
                tasks_container = ui.column().classes("gap-1 w-full")

                def rebuild_tasks() -> None:
                    tasks_container.clear()
                    with tasks_container:
                        task_list = controller.get_task_list()
                        if not task_list:
                            ui.label("No tasks configured.").classes("text-gray-500")
                            return

                        # Header row
                        with ui.row().classes("w-full items-center gap-2 p-2 bg-gray-50 rounded font-medium"):
                            ui.label("Name").classes("flex-grow")
                            ui.label("Description").classes("flex-grow")
                            ui.label("Status").classes("w-24")
                            ui.label("Next Run").classes("w-32")
                            ui.label("Actions").classes("w-48")

                        # Task rows
                        for task in task_list:
                            with ui.row().classes("w-full items-center gap-2 p-2 border-b border-gray-200"):
                                ui.label(task["name"]).classes("flex-grow")
                                ui.label(task.get("description", "")).classes("flex-grow text-sm text-gray-600")
                                ui.chip("Ready", color="green").classes("w-24")
                                ui.label(task.get("next_run", "N/A")).classes("w-32 text-sm")

                                def on_run_task(task_name: str = task["name"]) -> None:
                                    try:
                                        if controller.bot and controller.bot.task_manager:
                                            controller.bot.task_manager.run_task(task_name)
                                            ui.notify(f"Task '{task_name}' started.", type="positive")
                                        else:
                                            ui.notify("Bot not running.", type="warning")
                                    except Exception as e:
                                        ui.notify(f"Error running task: {e}", type="negative")

                                with ui.row().classes("gap-1"):
                                    ui.button("Run", on_click=on_run_task).props("size=sm dense")
                                    ui.button("Enable/Disable").props("size=sm dense outline")

                rebuild_tasks()
                ui.button("Refresh Tasks", on_click=rebuild_tasks).props("flat")

        # Automation tab
        with ui.tab_panel(t_automation):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Automation Rules").classes("text-subtitle1 font-medium")
                auto_container = ui.column().classes("gap-1 w-full")

                def rebuild_automations() -> None:
                    auto_container.clear()
                    with auto_container:
                        rules = controller.get_automation_rules()
                        if not rules:
                            ui.label("No automation rules configured.").classes("text-gray-500")
                            return

                        # Header row
                        with ui.row().classes("w-full items-center gap-2 p-2 bg-gray-50 rounded font-medium"):
                            ui.label("Rule Name").classes("flex-grow")
                            ui.label("Trigger").classes("w-32")
                            ui.label("Status").classes("w-24")
                            ui.label("Actions").classes("w-48")

                        # Rule rows
                        for rule in rules:
                            with ui.row().classes("w-full items-center gap-2 p-2 border-b border-gray-200"):
                                ui.label(rule["name"]).classes("flex-grow")
                                ui.label(rule.get("trigger", "N/A")).classes("w-32 text-sm")
                                ui.chip(rule.get("status", "Ready"), color="blue").classes("w-24")

                                def on_trigger(rule_name: str = rule["name"]) -> None:
                                    try:
                                        if controller.bot and controller.bot.automation_engine:
                                            controller.bot.automation_engine.trigger_rule(rule_name)
                                            ui.notify(f"Rule '{rule_name}' triggered.", type="positive")
                                        else:
                                            ui.notify("Bot not running.", type="warning")
                                    except Exception as e:
                                        ui.notify(f"Error triggering rule: {e}", type="negative")

                                with ui.row().classes("gap-1"):
                                    ui.button("Trigger", on_click=on_trigger).props("size=sm dense")
                                    ui.button("Enable/Disable").props("size=sm dense outline")

                rebuild_automations()
                ui.button("Refresh Rules", on_click=rebuild_automations).props("flat")

        # Provider Dashboard tab
        with ui.tab_panel(t_providers):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Message Providers").classes("text-subtitle1 font-medium")
                provider_container = ui.column().classes("gap-1 w-full")

                def rebuild_providers() -> None:
                    provider_container.clear()
                    with provider_container:
                        providers = controller.get_provider_list()
                        if not providers:
                            ui.label("No providers configured.").classes("text-gray-500")
                            return

                        # Header row
                        with ui.row().classes("w-full items-center gap-2 p-2 bg-gray-50 rounded font-medium"):
                            ui.label("Name").classes("flex-grow")
                            ui.label("Type").classes("w-40")
                            ui.label("Status").classes("w-24")
                            ui.label("Actions").classes("w-32")

                        # Provider rows
                        for provider in providers:
                            with ui.row().classes("w-full items-center gap-2 p-2 border-b border-gray-200"):
                                ui.label(provider["name"]).classes("flex-grow")
                                ui.label(provider.get("type", "Unknown")).classes("w-40 text-sm")
                                ui.chip(provider.get("status", "Unknown"), color="green").classes("w-24")

                                def on_test_provider(prov_name: str = provider["name"]) -> None:
                                    try:
                                        ui.notify(f"Testing connection to '{prov_name}'...", type="info")
                                        if controller.bot and controller.bot.get_provider(prov_name):
                                            ui.notify(f"Provider '{prov_name}' connected.", type="positive")
                                        else:
                                            ui.notify(f"Provider '{prov_name}' not found.", type="warning")
                                    except Exception as e:
                                        ui.notify(f"Connection test failed: {e}", type="negative")

                                ui.button("Test", on_click=on_test_provider).props("size=sm dense")

                rebuild_providers()
                ui.button("Refresh Providers", on_click=rebuild_providers).props("flat")

        # Message Stats tab
        with ui.tab_panel(t_messages):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Message Queue Status").classes("text-subtitle1 font-medium")
                msg_stats = controller.get_message_stats()

                with ui.row().classes("items-center gap-4 flex-wrap"):
                    ui.chip(f"Queue Size: {msg_stats['queue_size']}", color="blue")
                    ui.chip(f"Queued: {msg_stats['queued']}", color="blue")
                    ui.chip(f"Pending: {msg_stats['pending']}", color="warning")
                    ui.chip(f"Failed: {msg_stats['failed']}", color="red")
                    ui.chip(f"Success: {msg_stats['success']}", color="green")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Message Tracker Statistics").classes("text-subtitle1 font-medium")
                tracker_container = ui.column().classes("gap-2")

                def rebuild_message_stats() -> None:
                    tracker_container.clear()
                    with tracker_container:
                        stats = controller.get_message_stats()
                        with ui.grid(columns=2).classes("gap-3 w-full"):
                            ui.label("Total Pending").classes("text-sm")
                            ui.label(f"{stats['pending']}").classes("text-lg font-bold")

                            ui.label("Total Failed").classes("text-sm")
                            ui.label(f"{stats['failed']}").classes("text-lg font-bold text-red-600")

                            ui.label("Total Success").classes("text-sm")
                            ui.label(f"{stats['success']}").classes("text-lg font-bold text-green-600")

                            ui.label("Queue Size").classes("text-sm")
                            ui.label(f"{stats['queue_size']}").classes("text-lg font-bold")

                rebuild_message_stats()
                ui.button("Refresh Stats", on_click=rebuild_message_stats).props("flat")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Circuit Breaker Status").classes("text-subtitle1 font-medium")
                cb_container = ui.column().classes("gap-1")

                def rebuild_circuit_breakers() -> None:
                    cb_container.clear()
                    with cb_container:
                        from .core.circuit_breaker import CircuitBreakerManager
                        try:
                            manager = CircuitBreakerManager()
                            all_status = manager.get_all_status()
                            if not all_status:
                                ui.label("No circuit breakers active.").classes("text-gray-500")
                                return
                            for name, status in all_status.items():
                                with ui.row().classes("items-center gap-2 p-1"):
                                    color = "green" if status["state"] == "CLOSED" else "orange" if status["state"] == "HALF_OPEN" else "red"
                                    ui.chip(status["state"], color=color).classes("w-auto")
                                    ui.label(name).classes("flex-grow text-sm")
                        except Exception as e:
                            ui.label(f"Error loading breakers: {e}").classes("text-red-500 text-sm")

                rebuild_circuit_breakers()
                ui.button("Refresh", on_click=rebuild_circuit_breakers).props("flat")

        # Auth Management tab
        with ui.tab_panel(t_auth):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("User Management").classes("text-subtitle1 font-medium")
                ui.label("Manage user accounts and permissions.").classes("text-sm text-gray-500")
                users_container = ui.column().classes("gap-1 w-full")

                def rebuild_users() -> None:
                    users_container.clear()
                    with users_container:
                        users = controller.get_user_list()
                        if not users:
                            ui.label("No users found or auth module not available.").classes("text-gray-500")
                            return

                        # Header row
                        with ui.row().classes("w-full items-center gap-2 p-2 bg-gray-50 rounded font-medium"):
                            ui.label("ID").classes("w-12")
                            ui.label("Username").classes("flex-grow")
                            ui.label("Email").classes("flex-grow")
                            ui.label("Status").classes("w-24")
                            ui.label("Actions").classes("w-48")

                        # User rows
                        for user in users:
                            with ui.row().classes("w-full items-center gap-2 p-2 border-b border-gray-200"):
                                ui.label(str(user["id"])).classes("w-12 text-sm")
                                ui.label(user.get("username", "N/A")).classes("flex-grow text-sm")
                                ui.label(user.get("email", "N/A")).classes("flex-grow text-sm")
                                status_color = "green" if user.get("status") == "Active" else "red"
                                ui.chip(user.get("status", "Unknown"), color=status_color).classes("w-24")

                                def on_unlock(user_id: int = user["id"]) -> None:
                                    try:
                                        from .auth.service import AuthService
                                        auth_service = AuthService()
                                        auth_service.unlock_user(user_id)
                                        ui.notify(f"User {user_id} unlocked.", type="positive")
                                        rebuild_users()
                                    except Exception as e:
                                        ui.notify(f"Error unlocking user: {e}", type="negative")

                                with ui.row().classes("gap-1"):
                                    ui.button("Unlock", on_click=on_unlock).props("size=sm dense")
                                    ui.button("Verify").props("size=sm dense outline")

                rebuild_users()
                ui.button("Refresh Users", on_click=rebuild_users).props("flat")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Register New User").classes("font-medium")
                reg_username = ui.input("Username").props("clearable")
                reg_email = ui.input("Email", validation={"Email": lambda v: "@" in (v or "")}).props(
                    "clearable"
                )
                reg_password = ui.input("Password").props("type=password clearable")

                async def register_user() -> None:
                    if not all([reg_username.value, reg_email.value, reg_password.value]):
                        ui.notify("Please fill all fields.", type="warning")
                        return
                    try:
                        from .auth.service import AuthService
                        auth_service = AuthService()
                        auth_service.register_user(
                            reg_username.value, reg_email.value, reg_password.value
                        )
                        ui.notify("User registered successfully.", type="positive")
                        reg_username.value = ""
                        reg_email.value = ""
                        reg_password.value = ""
                    except Exception as e:
                        ui.notify(f"Registration failed: {e}", type="negative")

                ui.button("Register", on_click=register_user).props("color=primary")

        # Event Server tab
        with ui.tab_panel(t_events):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Event Server Status").classes("text-subtitle1 font-medium")
                event_status = controller.get_event_server_status()

                server_status_chip = ui.chip(
                    "Running" if event_status["running"] else "Stopped",
                    color="green" if event_status["running"] else "red"
                )

                with ui.row().classes("items-center gap-4 flex-wrap"):
                    server_status_chip
                    ui.label(f"Host: {event_status['host']}").classes("text-sm")
                    ui.label(f"Port: {event_status['port']}").classes("text-sm")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Server Controls").classes("font-medium")

                async def on_start_server() -> None:
                    try:
                        if controller.bot and controller.bot.event_server:
                            if not getattr(controller.bot.event_server, "running", False):
                                controller.bot.event_server.start()
                                ui.notify("Event server started.", type="positive")
                            else:
                                ui.notify("Event server already running.", type="info")
                        else:
                            ui.notify("Event server not configured.", type="warning")
                    except Exception as e:
                        ui.notify(f"Start failed: {e}", type="negative")

                async def on_stop_server() -> None:
                    try:
                        if controller.bot and controller.bot.event_server:
                            if getattr(controller.bot.event_server, "running", False):
                                controller.bot.event_server.stop()
                                ui.notify("Event server stopped.", type="positive")
                            else:
                                ui.notify("Event server not running.", type="info")
                        else:
                            ui.notify("Event server not configured.", type="warning")
                    except Exception as e:
                        ui.notify(f"Stop failed: {e}", type="negative")

                with ui.row().classes("gap-2"):
                    ui.button("Start", on_click=on_start_server).props("color=positive")
                    ui.button("Stop", on_click=on_stop_server).props("color=negative")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Recent Events").classes("font-medium")
                events_container = ui.column().classes("gap-1 h-48")

                def rebuild_events() -> None:
                    events_container.clear()
                    with events_container:
                        status = controller.get_event_server_status()
                        recent = status.get("recent_events", [])
                        if not recent:
                            ui.label("No recent events.").classes("text-gray-500")
                        else:
                            for event in recent:
                                ui.label(str(event)).classes("text-sm")

                rebuild_events()
                ui.button("Refresh Events", on_click=rebuild_events).props("flat")

            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Webhook Test").classes("font-medium")
                ui.label("Send a test webhook to the event server.").classes("text-sm text-gray-500")

                test_payload = ui.textarea("Test payload (JSON)").classes("w-full h-24").props(
                    "auto-grow"
                )
                test_payload.value = '{"type":"message.created","event":{"message":{"content":"test"}}}'

                async def on_send_webhook() -> None:
                    try:
                        import json
                        payload = json.loads(test_payload.value)
                        ui.notify("Webhook test sent (requires actual webhook server).", type="info")
                    except json.JSONDecodeError:
                        ui.notify("Invalid JSON payload.", type="negative")
                    except Exception as e:
                        ui.notify(f"Error sending webhook: {e}", type="negative")

                ui.button("Send Test Webhook", on_click=on_send_webhook).props("color=primary")

        # Logs tab
        with ui.tab_panel(t_logs):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Recent logs (in-memory; set a log file in Logging tab to persist)")
                with ui.row().classes("items-center gap-3 flex-wrap"):
                    level_filter = ui.select(
                        ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        value="ALL",
                        label="Filter",
                    )

                    def clear_logs() -> None:
                        controller.log_lines.clear()

                    ui.button("Clear", on_click=clear_logs).props("flat")

                    async def export_logs() -> None:
                        text = "\n".join(m for _, m in list(controller.log_lines))
                        from tempfile import NamedTemporaryFile

                        with NamedTemporaryFile(
                            "w", delete=False, suffix=".log", encoding="utf-8"
                        ) as tmp:
                            tmp.write(text)
                            tmp.flush()
                            ui.download(tmp.name)

                    ui.button("Export", on_click=export_logs).props("flat")
                log_area = (
                    ui.textarea()
                    .props("readonly autogrow")
                    .classes("w-full h-96 font-mono text-sm")
                )

            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }

            def update_log_area() -> None:
                rows: list[str] = []
                if controller.log_lines:
                    filt = level_filter.value or "ALL"
                    thresh = level_map.get(filt)
                    for lv, msg in list(controller.log_lines)[-500:]:
                        if thresh is None or lv >= thresh:
                            rows.append(msg)
                log_area.value = "\n".join(rows)

            ui.timer(1.0, update_log_area)

    # Background status chip updater
    def update_status_chip() -> None:
        s = controller.status()
        if s["running"]:
            status_chip.text = "Running"
            status_chip.props(remove="outline").update()
            status_chip.props("color=green text-color=white")
        else:
            status_chip.text = "Stopped"
            status_chip.props(add="outline").update()
            status_chip.props("color=grey text-color=white")

    ui.timer(1.5, update_status_chip)


def run_ui(
    config_path: str | Path = "config.yaml", host: str = "127.0.0.1", port: int = 8080
) -> None:
    """Start the NiceGUI app.

    Use a root function to avoid script-mode re-execution and ensure the '/' route exists.
    """
    path = Path(config_path)

    def root() -> None:
        build_ui(path)

    # Enable graceful shutdown
    async def on_shutdown() -> None:  # pragma: no cover
        logging.getLogger().info("Shutting down web UI...")

    app.on_shutdown(on_shutdown)

    # Pass the root function explicitly to avoid NiceGUI's script mode and 404 handler side-effects
    ui.run(root, host=host, port=port, show=False, reload=False, title="Feishu Webhook Bot Config")


if __name__ == "__main__":  # pragma: no cover - manual run helper
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", default="config.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    run_ui(args.config, args.host, args.port)
