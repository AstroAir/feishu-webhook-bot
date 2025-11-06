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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Callable

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

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
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
    bot: Optional[FeishuBot] = None
    thread: Optional[threading.Thread] = None
    running: bool = False
    _stop_event: threading.Event = field(default_factory=threading.Event)

    # logs
    log_lines: deque[tuple[int, str]] = field(default_factory=lambda: deque(maxlen=500))
    _ui_handler: Optional[UIMemoryLogHandler] = None

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
        try:
            root = logging.getLogger()
            root.removeHandler(self._ui_handler)
        except Exception:
            pass
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
        for h in root.handlers:
            try:
                h.setLevel(level)
            except Exception:
                pass
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


# ------------------------------
# UI helpers and page
# ------------------------------


def _config_to_form(cfg: BotConfig) -> dict[str, Any]:
    data = cfg.to_dict()
    # Ensure keys exist for predictable UI
    data.setdefault("webhooks", [])
    data.setdefault("scheduler", {})
    data.setdefault("plugins", {})
    data.setdefault("logging", {})
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
            ui.input("Name", validation={"Required": lambda v: bool(v and v.strip())}) \
                .bind_value(item, "name").props("dense clearable").classes("col-span-12 md:col-span-4 lg:col-span-3")
            ui.input("URL", validation={
                "Required": lambda v: bool(v and v.strip()),
                "Must start with http(s)": lambda v: (v or "").startswith("http"),
            }).bind_value(item, "url").props("dense clearable").classes("col-span-12 md:col-span-8 lg:col-span-6")
            ui.input("Secret (optional)").bind_value(item, "secret").props("dense clearable") \
                .classes("col-span-12 lg:col-span-2")
            if on_remove:
                with ui.element("div").classes(
                    "col-span-12 lg:col-span-1 flex justify-end lg:justify-center items-center"
                ):
                    ui.button(icon="delete", color="negative", on_click=lambda: on_remove()).props("flat round dense")


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
    with ui.header(elevated=True).style("background:linear-gradient(90deg,#4f86ed,#3a6fd6)").classes("px-4 py-2"):
        with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
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
                ui.button("Reset", on_click=reload_from_disk).props("outline color=white text-color=white")

    # Page container
    page = ui.column().classes("container mx-auto max-w-6xl w-full px-4 py-4 gap-5")

    with page:
        with ui.tabs().classes("w-full") as tabs:
            t_webhooks = ui.tab("Webhooks")
            t_scheduler = ui.tab("Scheduler")
            t_plugins = ui.tab("Plugins")
            t_logging = ui.tab("Logging")
            t_status = ui.tab("Status")
            t_logs = ui.tab("Logs")

    with ui.tab_panels(tabs, value=t_webhooks).classes("w-full"):
        # Webhooks tab
        with ui.tab_panel(t_webhooks):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-2"):
                ui.label("Webhook endpoints").classes("text-subtitle1 font-medium")
                ui.label("Tip: the webhook named 'default' will be used as the default when starting the bot.")\
                    .classes("text-sm text-gray-500")
            webhook_list: list[dict[str, Any]] = state["form"].setdefault("webhooks", [])
            container = ui.column().classes("w-full gap-4")

            def rebuild_webhooks() -> None:
                container.clear()
                with container:
                    for idx, wh in enumerate(webhook_list):
                        def remove_idx(i: int = idx) -> None:
                            webhook_list.pop(i)
                            rebuild_webhooks()

                        _webhook_card(wh, on_remove=remove_idx)

            rebuild_webhooks()

            with ui.row().classes("items-center gap-2 flex-wrap pt-1"):
                ui.button(
                    "Add webhook",
                    on_click=lambda: [
                        webhook_list.append({"name": "default", "url": "", "secret": None}),
                        rebuild_webhooks(),
                    ],
                ).props("outline")

                def set_default_to_first() -> None:
                    if not webhook_list:
                        return
                    # rename any existing 'default'
                    for wh in webhook_list:
                        if wh.get("name") == "default":
                            wh["name"] = f"wh_{id(wh) % 1000}"
                    webhook_list[0]["name"] = "default"
                    rebuild_webhooks()

                ui.button("Set first as default", on_click=set_default_to_first).props("outline")

        # Scheduler tab
        with ui.tab_panel(t_scheduler):
            sched = state["form"].setdefault("scheduler", {})
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.switch("Enable scheduler").bind_value(sched, "enabled")
                ui.input("Timezone", validation={"Required": lambda v: bool(v and v.strip())})\
                    .bind_value(sched, "timezone").classes("w-80")
                ui.select(["memory", "sqlite"], label="Job store type")\
                    .bind_value(sched, "job_store_type").classes("w-64")
                ui.input("Job store path (for sqlite)").bind_value(sched, "job_store_path").classes("w-96")
                ui.label("If 'sqlite' is selected, provide a valid file path.").classes("text-sm text-gray-500")

        # Plugins tab
        with ui.tab_panel(t_plugins):
            plug = state["form"].setdefault("plugins", {})
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.switch("Enable plugins").bind_value(plug, "enabled")
                ui.input("Plugin directory").bind_value(plug, "plugin_dir").classes("w-96")
                ui.switch("Auto reload (watch plugins)").bind_value(plug, "auto_reload")
                ui.number("Reload delay (seconds)").bind_value(plug, "reload_delay").props("step=0.1").classes("w-64")

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
                                def on_toggle(n=name):
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
                level_select = ui.select(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], label="Log level")\
                    .bind_value(log_cfg, "level").classes("w-64")
                ui.input("Format").bind_value(log_cfg, "format").classes("w-full")
                ui.input("Log file (optional)").bind_value(log_cfg, "log_file").classes("w-96")
                ui.number("Max bytes").bind_value(log_cfg, "max_bytes").classes("w-64")
                ui.number("Backup count").bind_value(log_cfg, "backup_count").classes("w-64")
                ui.button("Apply runtime level", on_click=lambda: controller.set_runtime_log_level(level_select.value or "INFO"))

        # Status tab
        with ui.tab_panel(t_status):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                status_label = ui.label("")
                plugin_list = ui.column()
                ui.label("")
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Send test message").classes("font-medium")
                cfg_webhooks = state["form"].get("webhooks", [])
                wh_names = [w.get("name", f"wh-{i}") for i, w in enumerate(cfg_webhooks)] or ["default"]
                sel_wh = ui.select(wh_names, value=wh_names[0] if wh_names else None, label="Webhook")
                msg_input = ui.input("Message").props("clearable").classes("w-full")
                async def send_test() -> None:
                    try:
                        if not msg_input.value:
                            ui.notify("Enter message text", type="warning")
                            return
                        controller.send_test_message(msg_input.value, webhook_name=sel_wh.value or "default")
                        ui.notify("Message sent", type="positive")
                    except Exception as e:
                        ui.notify(f"Send failed: {e}", type="negative")
                ui.button("Send", on_click=send_test)

            async def refresh_status() -> None:
                s = controller.status()
                status_label.text = f"Bot running: {s['running']} | Scheduler: {s['scheduler_running']}"
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
                                ui.label(f"Next: {job.next_run_time}").classes("text-sm text-gray-600")
                                def _pause(jid=job.id):
                                    if controller.bot and controller.bot.scheduler:
                                        controller.bot.scheduler.pause_job(jid)
                                def _resume(jid=job.id):
                                    if controller.bot and controller.bot.scheduler:
                                        controller.bot.scheduler.resume_job(jid)
                                def _remove(jid=job.id):
                                    if controller.bot and controller.bot.scheduler:
                                        controller.bot.scheduler.remove_job(jid)
                                ui.button("Pause", on_click=_pause)
                                ui.button("Resume", on_click=_resume)
                                ui.button("Remove", color="negative", on_click=_remove)
                ui.button("Refresh status", on_click=refresh_status).props("flat")
                ui.button("Refresh jobs", on_click=rebuild_jobs).props("flat")

        # Logs tab
        with ui.tab_panel(t_logs):
            with ui.card().classes("w-full p-5 bg-white shadow-sm border border-gray-200 gap-3"):
                ui.label("Recent logs (in-memory; set a log file in Logging tab to persist)")
                with ui.row().classes("items-center gap-3 flex-wrap"):
                    level_filter = ui.select(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], value="ALL", label="Filter")
                    def clear_logs() -> None:
                        controller.log_lines.clear()
                    ui.button("Clear", on_click=clear_logs).props("flat")
                    async def export_logs() -> None:
                        text = "\n".join(m for _, m in list(controller.log_lines))
                        from tempfile import NamedTemporaryFile
                        with NamedTemporaryFile("w", delete=False, suffix=".log", encoding="utf-8") as tmp:
                            tmp.write(text)
                            tmp.flush()
                            ui.download(tmp.name)
                    ui.button("Export", on_click=export_logs).props("flat")
                log_area = ui.textarea().props("readonly autogrow").classes("w-full h-96 font-mono text-sm")

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
                    thresh = level_map.get(filt, None)
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


def run_ui(config_path: str | Path = "config.yaml", host: str = "127.0.0.1", port: int = 8080) -> None:
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
