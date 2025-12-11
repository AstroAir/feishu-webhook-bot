# ruff: noqa: E501
"""Bot lifecycle controller and logging handler for WebUI."""

from __future__ import annotations

import logging
import threading
from collections import deque
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..bot import FeishuBot
from ..core import BotConfig, get_logger

log = get_logger("webui")


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
            pass


@dataclass
class BotController:
    """Manage bot instance, thread, config IO, and live logs."""

    config_path: Path
    bot: FeishuBot | None = None
    thread: threading.Thread | None = None
    running: bool = False
    _stop_event: threading.Event = field(default_factory=threading.Event)

    log_lines: deque[tuple[int, str]] = field(default_factory=lambda: deque(maxlen=500))
    _ui_handler: UIMemoryLogHandler | None = None

    def load_config(self) -> BotConfig:
        """Load configuration from YAML; create default if file missing."""
        if not self.config_path.exists():
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

    def _attach_ui_logger(self) -> None:
        """Attach an in-memory handler to the root logger so UI can display live logs."""
        if self._ui_handler is not None:
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
        self.bot = FeishuBot(cfg)
        self._attach_ui_logger()

        def target() -> None:
            try:
                assert self.bot is not None
                self.bot.start()
            except Exception as e:
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

    def set_runtime_log_level(self, level_name: str) -> None:
        level = getattr(logging, level_name.upper(), logging.INFO)
        root = logging.getLogger()
        root.setLevel(level)
        for handler in root.handlers:
            with suppress(Exception):
                handler.setLevel(level)
        logging.getLogger("feishu_bot").setLevel(level)

    def send_test_message(self, text: str, webhook_name: str) -> None:
        if self.bot is not None:
            self.bot.send_message(text, webhook_name=webhook_name)
            return
        cfg = self.load_config()
        webhook = cfg.get_webhook(webhook_name) or (cfg.webhooks[0] if cfg.webhooks else None)
        if not webhook:
            raise ValueError("No webhook configured")
        from ..core.client import FeishuWebhookClient

        with FeishuWebhookClient(webhook) as client:
            client.send_text(text)

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
        """Get list of active providers from running bot."""
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

    def get_message_provider_list(self) -> list[dict[str, Any]]:
        """Get list of message providers from config (Feishu/Napcat)."""
        try:
            cfg = self.load_config()
            providers = []
            for p in cfg.providers or []:
                providers.append({
                    "name": p.name,
                    "provider_type": p.provider_type,
                    "enabled": p.enabled,
                    "webhook_url": getattr(p, "webhook_url", None),
                    "http_url": getattr(p, "http_url", None),
                    "secret": getattr(p, "secret", None),
                    "access_token": getattr(p, "access_token", None),
                    "bot_qq": getattr(p, "bot_qq", None),
                    "default_target": getattr(p, "default_target", None),
                    "timeout": p.timeout,
                })
            return providers
        except Exception:
            return []

    def send_test_to_provider(self, provider_name: str, message: str) -> bool:
        """Send a test message via a specific provider.

        Args:
            provider_name: Name of the provider to use
            message: Test message to send

        Returns:
            True if sent successfully
        """
        if not self.bot:
            raise ValueError("Bot not running")

        provider = self.bot.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider not found: {provider_name}")

        result = provider.send_text(message)
        if not result.success:
            raise ValueError(f"Send failed: {result.error}")
        return True

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
        from ..auth.service import AuthService

        users = []
        try:
            auth_service = AuthService()
            from ..auth.database import DatabaseManager

            db_manager = DatabaseManager()
            with db_manager.get_session() as session:
                from ..auth.models import User

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

    # =========================================================================
    # Task Management Methods
    # =========================================================================
    def get_task_details(self, task_name: str) -> dict[str, Any]:
        """Get detailed information about a task.

        Args:
            task_name: Name of the task

        Returns:
            Detailed task information dictionary
        """
        if not self.bot or not self.bot.task_manager:
            # Fallback to config
            if self.bot and self.bot.config:
                task = self.bot.config.get_task(task_name)
                if task:
                    return {
                        "name": task.name,
                        "description": task.description or "",
                        "enabled": task.enabled,
                        "schedule": task.cron or str(task.interval) if task.interval else "N/A",
                        "timeout": task.timeout,
                        "max_concurrent": task.max_concurrent,
                        "actions_count": len(task.actions) if task.actions else 0,
                        "conditions_count": len(task.conditions) if task.conditions else 0,
                        "error_handling": {
                            "retry_on_failure": task.error_handling.retry_on_failure if task.error_handling else False,
                            "max_retries": task.error_handling.max_retries if task.error_handling else 0,
                            "on_failure_action": task.error_handling.on_failure_action if task.error_handling else "log",
                        },
                        "status": {"registered": False, "next_run": None},
                        "recent_history": [],
                        "total_runs": 0,
                        "success_rate": 0,
                        "actions": self._get_task_actions_info(task),
                        "conditions": self._get_task_conditions_info(task),
                        "parameters": self._get_task_parameters_info(task),
                        "plugin_methods": self._get_available_plugin_methods(),
                    }
            return {"error": f"Task not found: {task_name}"}

        details = self.bot.task_manager.get_task_details(task_name)
        # Enhance with plugin info
        if "error" not in details:
            task = self.bot.task_manager.get_task(task_name)
            if task:
                details["actions"] = self._get_task_actions_info(task)
                details["conditions"] = self._get_task_conditions_info(task)
                details["parameters"] = self._get_task_parameters_info(task)
            details["plugin_methods"] = self._get_available_plugin_methods()
        return details

    def _get_task_actions_info(self, task: Any) -> list[dict[str, Any]]:
        """Get detailed info about task actions."""
        actions = []
        for action in task.actions:
            action_info = {
                "type": action.type,
                "parameters": dict(action.parameters) if action.parameters else {},
            }
            if action.type == "plugin_method":
                action_info["plugin_name"] = action.plugin_name
                action_info["method_name"] = action.method_name
            elif action.type == "send_message":
                action_info["message"] = action.message
                action_info["template"] = action.template
                action_info["webhooks"] = action.webhooks
            elif action.type == "http_request":
                action_info["url"] = action.url
                action_info["method"] = action.method
            elif action.type in ("ai_chat", "ai_query"):
                action_info["prompt"] = action.prompt
            actions.append(action_info)
        return actions

    def _get_task_conditions_info(self, task: Any) -> list[dict[str, Any]]:
        """Get detailed info about task conditions."""
        conditions = []
        for cond in task.conditions:
            cond_info = {"type": cond.type}
            if cond.type == "time_range":
                cond_info["start_time"] = cond.start_time
                cond_info["end_time"] = cond.end_time
            elif cond.type == "day_of_week":
                cond_info["days"] = cond.days
            elif cond.type == "environment":
                cond_info["environment"] = cond.environment
            elif cond.type == "custom":
                cond_info["expression"] = cond.expression
            conditions.append(cond_info)
        return conditions

    def _get_task_parameters_info(self, task: Any) -> list[dict[str, Any]]:
        """Get detailed info about task parameters."""
        params = []
        for param in task.parameters:
            params.append({
                "name": param.name,
                "type": param.type,
                "default": param.default,
                "required": param.required,
                "description": param.description,
            })
        return params

    def _get_available_plugin_methods(self) -> list[dict[str, Any]]:
        """Get list of available plugin methods that can be called from tasks."""
        methods = []
        if not self.bot or not self.bot.plugin_manager:
            return methods

        for plugin_name, plugin in self.bot.plugin_manager.plugins.items():
            # Get public methods (not starting with _)
            for method_name in dir(plugin):
                if method_name.startswith("_"):
                    continue
                method = getattr(plugin, method_name, None)
                if callable(method) and not method_name.startswith("on_"):
                    # Skip lifecycle methods
                    if method_name in ("metadata", "register_job", "cleanup_jobs",
                                       "get_config_value", "get_all_config",
                                       "validate_config", "get_missing_config",
                                       "get_manifest", "handle_event"):
                        continue
                    methods.append({
                        "plugin": plugin_name,
                        "method": method_name,
                        "full_name": f"{plugin_name}.{method_name}",
                    })
        return methods

    def get_task_history(self, task_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Get task execution history.

        Args:
            task_name: Optional filter by task name
            limit: Maximum number of entries to return

        Returns:
            List of execution history entries
        """
        if not self.bot or not self.bot.task_manager:
            return []
        return self.bot.task_manager.get_execution_history(task_name, limit)

    def run_task(self, task_name: str, force: bool = False) -> dict[str, Any]:
        """Run a task immediately.

        Args:
            task_name: Name of the task to run
            force: If True, bypass concurrent execution limit

        Returns:
            Execution result dictionary
        """
        if not self.bot or not self.bot.task_manager:
            return {"success": False, "error": "Task manager not available"}
        return self.bot.task_manager.run_task(task_name, force=force)

    def enable_task(self, task_name: str) -> bool:
        """Enable a task.

        Args:
            task_name: Name of the task to enable

        Returns:
            True if task was enabled, False if not found
        """
        if not self.bot or not self.bot.task_manager:
            return False
        return self.bot.task_manager.enable_task(task_name)

    def disable_task(self, task_name: str) -> bool:
        """Disable a task.

        Args:
            task_name: Name of the task to disable

        Returns:
            True if task was disabled, False if not found
        """
        if not self.bot or not self.bot.task_manager:
            return False
        return self.bot.task_manager.disable_task(task_name)

    def pause_task(self, task_name: str) -> bool:
        """Pause a task (keep registered but don't execute).

        Args:
            task_name: Name of the task to pause

        Returns:
            True if task was paused, False if not found
        """
        if not self.bot or not self.bot.task_manager:
            return False
        return self.bot.task_manager.pause_task(task_name)

    def resume_task(self, task_name: str) -> bool:
        """Resume a paused task.

        Args:
            task_name: Name of the task to resume

        Returns:
            True if task was resumed, False if not found
        """
        if not self.bot or not self.bot.task_manager:
            return False
        return self.bot.task_manager.resume_task(task_name)

    def run_task_with_params(
        self, task_name: str, params: dict[str, Any] | None = None, force: bool = False
    ) -> dict[str, Any]:
        """Run a task with custom parameters.

        Args:
            task_name: Name of the task to run
            params: Custom parameters to override task defaults
            force: If True, bypass concurrent execution limit

        Returns:
            Execution result dictionary
        """
        if not self.bot or not self.bot.task_manager:
            return {"success": False, "error": "Task manager not available"}
        return self.bot.task_manager.run_task_with_params(task_name, params, force)

    def update_task_config(self, task_name: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update task configuration at runtime.

        Args:
            task_name: Name of the task to update
            updates: Dictionary of configuration updates

        Returns:
            Result dictionary with success status
        """
        if not self.bot or not self.bot.task_manager:
            return {"success": False, "error": "Task manager not available"}
        return self.bot.task_manager.update_task_config(task_name, updates)

    def get_task_action_types(self) -> list[dict[str, Any]]:
        """Get available task action types with descriptions.

        Returns:
            List of action type definitions
        """
        return [
            {
                "type": "plugin_method",
                "name": "Plugin Method",
                "description": "Call a method from a loaded plugin",
                "required_fields": ["plugin_name", "method_name"],
                "optional_fields": ["parameters"],
            },
            {
                "type": "send_message",
                "name": "Send Message",
                "description": "Send a message via webhook",
                "required_fields": [],
                "optional_fields": ["message", "template", "webhooks"],
            },
            {
                "type": "http_request",
                "name": "HTTP Request",
                "description": "Make an HTTP request to an external API",
                "required_fields": ["url"],
                "optional_fields": ["method", "headers", "body", "timeout"],
            },
            {
                "type": "python_code",
                "name": "Python Code",
                "description": "Execute custom Python code",
                "required_fields": ["code"],
                "optional_fields": [],
            },
            {
                "type": "ai_chat",
                "name": "AI Chat",
                "description": "Send a prompt to AI agent and get response",
                "required_fields": ["prompt"],
                "optional_fields": ["model", "temperature"],
            },
            {
                "type": "ai_query",
                "name": "AI Query",
                "description": "Query AI agent for information",
                "required_fields": ["prompt"],
                "optional_fields": ["model"],
            },
        ]

    def get_task_condition_types(self) -> list[dict[str, Any]]:
        """Get available task condition types with descriptions.

        Returns:
            List of condition type definitions
        """
        return [
            {
                "type": "time_range",
                "name": "Time Range",
                "description": "Only run within a specific time range",
                "fields": ["start_time", "end_time"],
            },
            {
                "type": "day_of_week",
                "name": "Day of Week",
                "description": "Only run on specific days",
                "fields": ["days"],
            },
            {
                "type": "environment",
                "name": "Environment",
                "description": "Only run in specific environment",
                "fields": ["environment"],
            },
            {
                "type": "custom",
                "name": "Custom Expression",
                "description": "Custom Python expression that evaluates to True/False",
                "fields": ["expression"],
            },
        ]

    def call_plugin_method(
        self, plugin_name: str, method_name: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Call a plugin method directly.

        Args:
            plugin_name: Name of the plugin
            method_name: Name of the method to call
            params: Parameters to pass to the method

        Returns:
            Result dictionary
        """
        if not self.bot or not self.bot.plugin_manager:
            return {"success": False, "error": "Plugin manager not available"}

        plugin = self.bot.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            return {"success": False, "error": f"Plugin not found: {plugin_name}"}

        method = getattr(plugin, method_name, None)
        if not method or not callable(method):
            return {"success": False, "error": f"Method not found: {method_name}"}

        try:
            result = method(**(params or {}))
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_task_stats(self) -> dict[str, Any]:
        """Get statistics for all tasks.

        Returns:
            Dictionary with task statistics including counts and success rates
        """
        if not self.bot or not self.bot.task_manager:
            # Fallback to config-based stats
            if self.bot and self.bot.config and self.bot.config.tasks:
                tasks = self.bot.config.tasks
                total = len(tasks)
                enabled = sum(1 for t in tasks if t.enabled)
                return {
                    "total_tasks": total,
                    "enabled_tasks": enabled,
                    "disabled_tasks": total - enabled,
                    "registered_jobs": 0,
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "overall_success_rate": 0,
                }
            return {
                "total_tasks": 0,
                "enabled_tasks": 0,
                "disabled_tasks": 0,
                "registered_jobs": 0,
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "overall_success_rate": 0,
            }
        return self.bot.task_manager.get_all_task_stats()

    def get_task_templates(self) -> list[dict[str, Any]]:
        """Get available task templates.

        Returns:
            List of task template information dictionaries
        """
        if not self.bot or not self.bot.config:
            return []

        templates = getattr(self.bot.config, "task_templates", [])
        result = []
        for tpl in templates:
            tpl_info = {
                "name": tpl.name if hasattr(tpl, "name") else tpl.get("name", ""),
                "description": tpl.description if hasattr(tpl, "description") else tpl.get(
                    "description", ""
                ),
                "parameters": [],
            }
            params = tpl.parameters if hasattr(tpl, "parameters") else tpl.get(
                "parameters", []
            )
            for param in params:
                tpl_info["parameters"].append({
                    "name": param.name if hasattr(param, "name") else param.get("name", ""),
                    "type": param.type if hasattr(param, "type") else param.get("type", "string"),
                    "required": param.required if hasattr(param, "required") else param.get(
                        "required", False
                    ),
                    "default": param.default if hasattr(param, "default") else param.get(
                        "default", None
                    ),
                    "description": param.description if hasattr(param, "description") else param.get(
                        "description", ""
                    ),
                })
            result.append(tpl_info)
        return result

    def create_task_from_template(
        self,
        template_name: str,
        task_name: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new task from a template.

        Args:
            template_name: Name of the template to use
            task_name: Name for the new task
            params: Parameters to pass to the template

        Returns:
            Result dictionary with success status
        """
        if not self.bot or not self.bot.config:
            return {"success": False, "error": "Bot not configured"}

        templates = getattr(self.bot.config, "task_templates", [])
        if not templates:
            return {"success": False, "error": "No task templates configured"}

        # Find template
        template = None
        for tpl in templates:
            tpl_name = tpl.name if hasattr(tpl, "name") else tpl.get("name", "")
            if tpl_name == template_name:
                template = tpl
                break

        if not template:
            return {"success": False, "error": f"Template not found: {template_name}"}

        try:
            from ..tasks.templates import TaskTemplateEngine

            engine = TaskTemplateEngine([template])
            new_task = engine.create_task_from_template(
                template_name, task_name, params or {}
            )

            # Add to config
            self.bot.config.tasks.append(new_task)

            # Register with task manager if available
            if self.bot.task_manager:
                self.bot.task_manager._task_instances[task_name] = new_task
                if new_task.enabled:
                    self.bot.task_manager._register_task(new_task)

            return {
                "success": True,
                "task_name": task_name,
                "template_name": template_name,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def reload_tasks(self) -> dict[str, Any]:
        """Reload all tasks from configuration.

        Returns:
            Result dictionary with reload status
        """
        if not self.bot or not self.bot.task_manager:
            return {"success": False, "error": "Task manager not available"}

        try:
            self.bot.task_manager.reload_tasks()
            task_count = len(self.bot.task_manager._task_instances)
            return {
                "success": True,
                "tasks_reloaded": task_count,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_task(self, task_name: str) -> dict[str, Any]:
        """Delete a task from configuration.

        Args:
            task_name: Name of the task to delete

        Returns:
            Result dictionary with success status
        """
        if not self.bot or not self.bot.config:
            return {"success": False, "error": "Bot not configured"}

        # Find and remove task from config
        task_found = False
        for i, task in enumerate(self.bot.config.tasks):
            if task.name == task_name:
                self.bot.config.tasks.pop(i)
                task_found = True
                break

        if not task_found:
            return {"success": False, "error": f"Task not found: {task_name}"}

        # Remove from task manager if running
        if self.bot.task_manager:
            self.bot.task_manager.disable_task(task_name)
            if task_name in self.bot.task_manager._task_instances:
                del self.bot.task_manager._task_instances[task_name]

        return {"success": True, "task_name": task_name}

    def get_plugin_info(self, plugin_name: str) -> dict[str, Any]:
        """Get detailed information about a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin information dictionary
        """
        if not self.bot or not self.bot.plugin_manager:
            return {"error": "Plugin manager not available"}

        plugin = self.bot.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            return {"error": f"Plugin not found: {plugin_name}"}

        metadata = plugin.metadata()
        config = plugin.get_all_config()

        # Get available methods
        methods = []
        for method_name in dir(plugin):
            if method_name.startswith("_") or method_name.startswith("on_"):
                continue
            method = getattr(plugin, method_name, None)
            if callable(method):
                if method_name in ("metadata", "register_job", "cleanup_jobs",
                                   "get_config_value", "get_all_config",
                                   "validate_config", "get_missing_config",
                                   "get_manifest", "handle_event"):
                    continue
                # Try to get docstring
                doc = method.__doc__ or ""
                methods.append({
                    "name": method_name,
                    "description": doc.split("\n")[0] if doc else "",
                })

        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "author": metadata.author,
            "enabled": metadata.enabled,
            "config": config,
            "methods": methods,
            "job_count": len(plugin._job_ids),
        }

    # =========================================================================
    # Automation Management Methods
    # =========================================================================
    def get_automation_details(self, rule_name: str) -> dict[str, Any]:
        """Get detailed information about an automation rule.

        Args:
            rule_name: Name of the rule

        Returns:
            Detailed rule information dictionary
        """
        if not self.bot or not self.bot.automation_engine:
            # Fallback to config
            if self.bot and self.bot.config:
                for rule in self.bot.config.automations:
                    if rule.name == rule_name:
                        return {
                            "name": rule.name,
                            "description": rule.description or "",
                            "enabled": rule.enabled,
                            "trigger_type": rule.trigger.type if rule.trigger else "unknown",
                            "actions_count": len(rule.actions) if rule.actions else 0,
                            "actions": self._get_automation_actions_info(rule),
                            "default_webhooks": rule.default_webhooks or [],
                            "registered": False,
                            "next_run": None,
                            "recent_executions": [],
                            "plugin_methods": self._get_available_plugin_methods(),
                        }
            return {"error": f"Rule not found: {rule_name}"}

        details = self.bot.automation_engine.get_rule_status(rule_name)
        # Enhance with action details
        if "error" not in details:
            for rule in self.bot.config.automations:
                if rule.name == rule_name:
                    details["actions"] = self._get_automation_actions_info(rule)
                    details["plugin_methods"] = self._get_available_plugin_methods()
                    break
        return details

    def _get_automation_actions_info(self, rule: Any) -> list[dict[str, Any]]:
        """Get detailed info about automation rule actions."""
        actions = []
        for action in rule.actions:
            action_info = {
                "type": action.type,
            }
            if action.type == "send_text":
                action_info["text"] = action.text
                action_info["webhooks"] = action.webhooks
            elif action.type == "send_template":
                action_info["template"] = action.template
                action_info["variables"] = dict(action.variables) if action.variables else {}
            elif action.type == "http_request":
                action_info["url"] = action.url
                action_info["method"] = action.method
            elif action.type == "plugin_method":
                action_info["plugin_name"] = getattr(action, "plugin_name", None)
                action_info["method_name"] = getattr(action, "method_name", None)
            actions.append(action_info)
        return actions

    def get_automation_history(self, rule_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Get automation execution history.

        Args:
            rule_name: Optional filter by rule name
            limit: Maximum number of entries to return

        Returns:
            List of execution history entries
        """
        if not self.bot or not self.bot.automation_engine:
            return []
        return self.bot.automation_engine.get_execution_history(rule_name, limit)

    def trigger_automation(self, rule_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Manually trigger an automation rule.

        Args:
            rule_name: Name of the rule to trigger
            context: Optional context to pass to the rule

        Returns:
            Execution result dictionary
        """
        if not self.bot or not self.bot.automation_engine:
            return {"success": False, "error": "Automation engine not available"}
        return self.bot.automation_engine.trigger_rule(rule_name, context)

    def enable_automation(self, rule_name: str) -> bool:
        """Enable an automation rule.

        Args:
            rule_name: Name of the rule to enable

        Returns:
            True if rule was enabled, False if not found
        """
        if not self.bot or not self.bot.automation_engine:
            return False
        return self.bot.automation_engine.enable_rule(rule_name)

    def disable_automation(self, rule_name: str) -> bool:
        """Disable an automation rule.

        Args:
            rule_name: Name of the rule to disable

        Returns:
            True if rule was disabled, False if not found
        """
        if not self.bot or not self.bot.automation_engine:
            return False
        return self.bot.automation_engine.disable_rule(rule_name)

    def get_automation_action_types(self) -> list[dict[str, Any]]:
        """Get available automation action types.

        Returns:
            List of action type definitions
        """
        return [
            {
                "type": "send_text",
                "name": "Send Text",
                "description": "Send a plain text message",
                "fields": ["text", "webhooks"],
            },
            {
                "type": "send_template",
                "name": "Send Template",
                "description": "Send a message using a template",
                "fields": ["template", "variables", "webhooks"],
            },
            {
                "type": "http_request",
                "name": "HTTP Request",
                "description": "Make an HTTP request",
                "fields": ["url", "method", "headers", "body"],
            },
            {
                "type": "plugin_method",
                "name": "Plugin Method",
                "description": "Call a plugin method",
                "fields": ["plugin_name", "method_name", "parameters"],
            },
        ]

    def get_automation_trigger_types(self) -> list[dict[str, Any]]:
        """Get available automation trigger types.

        Returns:
            List of trigger type definitions
        """
        return [
            {
                "type": "schedule",
                "name": "Schedule",
                "description": "Trigger on a schedule (cron expression)",
                "fields": ["schedule"],
            },
            {
                "type": "event",
                "name": "Event",
                "description": "Trigger on a specific event",
                "fields": ["event", "conditions"],
            },
            {
                "type": "webhook",
                "name": "Webhook",
                "description": "Trigger when webhook receives data",
                "fields": ["webhook_name", "filters"],
            },
        ]

    def get_automation_stats(self) -> dict[str, Any]:
        """Get automation engine statistics.

        Returns:
            Statistics dictionary
        """
        if not self.bot or not self.bot.automation_engine:
            return {
                "total_rules": 0,
                "enabled_rules": 0,
                "total_executions": 0,
                "success_rate": 0,
            }

        rules = self.get_automation_rules()
        history = self.get_automation_history(limit=100)

        total = len(rules)
        enabled = sum(1 for r in rules if r.get("enabled", True))
        total_execs = len(history)
        successful = sum(1 for h in history if h.get("success"))
        success_rate = (successful / total_execs * 100) if total_execs > 0 else 0

        return {
            "total_rules": total,
            "enabled_rules": enabled,
            "disabled_rules": total - enabled,
            "total_executions": total_execs,
            "successful_executions": successful,
            "failed_executions": total_execs - successful,
            "success_rate": round(success_rate, 1),
        }

    def update_automation_config(
        self, rule_name: str, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Update automation rule configuration at runtime.

        Args:
            rule_name: Name of the rule to update
            updates: Dictionary of configuration updates

        Returns:
            Result dictionary with success status
        """
        if not self.bot or not self.bot.automation_engine:
            return {"success": False, "error": "Automation engine not available"}

        try:
            engine = self.bot.automation_engine
            rule = None
            for r in engine._rules:
                if r.name == rule_name:
                    rule = r
                    break

            if not rule:
                return {"success": False, "error": f"Rule not found: {rule_name}"}

            updated_fields = []

            if "enabled" in updates:
                rule.enabled = updates["enabled"]
                updated_fields.append("enabled")
                if rule.enabled:
                    engine.enable_rule(rule_name)
                else:
                    engine.disable_rule(rule_name)

            if "description" in updates:
                rule.description = updates["description"]
                updated_fields.append("description")

            if "default_webhooks" in updates:
                rule.default_webhooks = updates["default_webhooks"]
                updated_fields.append("default_webhooks")

            return {
                "success": True,
                "updated_fields": updated_fields,
                "rule_name": rule_name,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Scheduler Management Methods
    # =========================================================================
    def get_scheduler_jobs(self) -> list[dict[str, Any]]:
        """Get list of all scheduled jobs.

        Returns:
            List of job information dictionaries
        """
        if not self.bot or not self.bot.scheduler:
            return []
        try:
            jobs = self.bot.scheduler.get_jobs()
            result = []
            for job in jobs:
                job_info = {
                    "id": job.id,
                    "name": getattr(job, "name", job.id),
                    "next_run": str(job.next_run_time) if job.next_run_time else None,
                    "trigger": str(job.trigger) if hasattr(job, "trigger") else "unknown",
                    "paused": job.next_run_time is None,
                }
                result.append(job_info)
            return result
        except Exception:
            return []

    def pause_scheduler_job(self, job_id: str) -> bool:
        """Pause a scheduled job.

        Args:
            job_id: ID of the job to pause

        Returns:
            True if job was paused, False otherwise
        """
        if not self.bot or not self.bot.scheduler:
            return False
        try:
            self.bot.scheduler.pause_job(job_id)
            return True
        except Exception:
            return False

    def resume_scheduler_job(self, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: ID of the job to resume

        Returns:
            True if job was resumed, False otherwise
        """
        if not self.bot or not self.bot.scheduler:
            return False
        try:
            self.bot.scheduler.resume_job(job_id)
            return True
        except Exception:
            return False

    def remove_scheduler_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: ID of the job to remove

        Returns:
            True if job was removed, False otherwise
        """
        if not self.bot or not self.bot.scheduler:
            return False
        try:
            self.bot.scheduler.remove_job(job_id)
            return True
        except Exception:
            return False

    def get_scheduler_status(self) -> dict[str, Any]:
        """Get scheduler status information.

        Returns:
            Scheduler status dictionary
        """
        if not self.bot or not self.bot.scheduler:
            return {
                "running": False,
                "timezone": "N/A",
                "job_count": 0,
                "job_store_type": "N/A",
            }
        try:
            jobs = self.bot.scheduler.get_jobs()
            return {
                "running": self.bot.scheduler._scheduler.running if self.bot.scheduler._scheduler else False,
                "timezone": str(self.bot.scheduler.config.timezone) if self.bot.scheduler.config else "N/A",
                "job_count": len(jobs),
                "job_store_type": self.bot.scheduler.config.job_store_type if self.bot.scheduler.config else "memory",
            }
        except Exception:
            return {
                "running": False,
                "timezone": "N/A",
                "job_count": 0,
                "job_store_type": "N/A",
            }

    # =========================================================================
    # AI Management Methods
    # =========================================================================
    def list_ai_conversations(self) -> list[dict[str, Any]]:
        """List all active AI conversations.

        Returns:
            List of conversation summaries
        """
        if not self.bot or not self.bot.ai_agent:
            return []
        try:
            conv_manager = self.bot.ai_agent.conversation_manager
            conversations = []
            for user_id, conv in conv_manager._conversations.items():
                conversations.append({
                    "user_id": user_id,
                    "message_count": conv.message_count,
                    "input_tokens": conv.input_tokens,
                    "output_tokens": conv.output_tokens,
                    "total_tokens": conv.input_tokens + conv.output_tokens,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "last_activity": conv.last_activity.isoformat() if conv.last_activity else None,
                    "has_summary": conv.summary is not None,
                })
            return conversations
        except Exception as e:
            log.error(f"Error listing conversations: {e}")
            return []

    def get_ai_conversation_details(self, user_id: str) -> dict[str, Any]:
        """Get detailed information about a specific conversation.

        Args:
            user_id: User ID of the conversation

        Returns:
            Conversation details dictionary
        """
        if not self.bot or not self.bot.ai_agent:
            return {"error": "AI agent not available"}
        try:
            conv_manager = self.bot.ai_agent.conversation_manager
            if user_id not in conv_manager._conversations:
                return {"error": f"Conversation not found: {user_id}"}
            conv = conv_manager._conversations[user_id]
            return conv.get_analytics()
        except Exception as e:
            log.error(f"Error getting conversation details: {e}")
            return {"error": str(e)}

    async def export_ai_conversation(self, user_id: str) -> dict[str, Any]:
        """Export a conversation to JSON format.

        Args:
            user_id: User ID of the conversation

        Returns:
            Export result with data or error
        """
        if not self.bot or not self.bot.ai_agent:
            return {"success": False, "error": "AI agent not available"}
        try:
            conv_manager = self.bot.ai_agent.conversation_manager
            json_data = await conv_manager.export_conversation(user_id)
            return {"success": True, "data": json_data}
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            log.error(f"Error exporting conversation: {e}")
            return {"success": False, "error": str(e)}

    async def delete_ai_conversation(self, user_id: str) -> dict[str, Any]:
        """Delete a conversation.

        Args:
            user_id: User ID of the conversation

        Returns:
            Deletion result
        """
        if not self.bot or not self.bot.ai_agent:
            return {"success": False, "error": "AI agent not available"}
        try:
            conv_manager = self.bot.ai_agent.conversation_manager
            await conv_manager.delete_conversation(user_id)
            return {"success": True, "user_id": user_id}
        except Exception as e:
            log.error(f"Error deleting conversation: {e}")
            return {"success": False, "error": str(e)}

    async def clear_ai_conversation(self, user_id: str) -> dict[str, Any]:
        """Clear a conversation's history but keep the record.

        Args:
            user_id: User ID of the conversation

        Returns:
            Clear result
        """
        if not self.bot or not self.bot.ai_agent:
            return {"success": False, "error": "AI agent not available"}
        try:
            conv_manager = self.bot.ai_agent.conversation_manager
            await conv_manager.clear_conversation(user_id)
            return {"success": True, "user_id": user_id}
        except Exception as e:
            log.error(f"Error clearing conversation: {e}")
            return {"success": False, "error": str(e)}

    def get_ai_tool_list(self) -> list[dict[str, Any]]:
        """Get list of registered AI tools with details.

        Returns:
            List of tool information dictionaries
        """
        if not self.bot or not self.bot.ai_agent:
            return []
        try:
            tool_registry = self.bot.ai_agent.tool_registry
            tools = []
            for name in tool_registry.list_tools():
                info = tool_registry.get_tool_info(name)
                if info:
                    tools.append(info)
            return tools
        except Exception as e:
            log.error(f"Error getting tool list: {e}")
            return []

    def get_ai_tool_details(self, tool_name: str) -> dict[str, Any]:
        """Get detailed information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool details dictionary
        """
        if not self.bot or not self.bot.ai_agent:
            return {"error": "AI agent not available"}
        try:
            tool_registry = self.bot.ai_agent.tool_registry
            info = tool_registry.get_tool_info(tool_name)
            if not info:
                return {"error": f"Tool not found: {tool_name}"}
            return info
        except Exception as e:
            log.error(f"Error getting tool details: {e}")
            return {"error": str(e)}

    def get_ai_tool_stats(self) -> dict[str, Any]:
        """Get AI tool usage statistics.

        Returns:
            Tool statistics dictionary
        """
        if not self.bot or not self.bot.ai_agent:
            return {
                "total_tools": 0,
                "total_usage": 0,
                "total_errors": 0,
                "error_rate_percent": 0,
                "most_used_tools": [],
                "categories": [],
            }
        try:
            return self.bot.ai_agent.tool_registry.get_stats()
        except Exception as e:
            log.error(f"Error getting tool stats: {e}")
            return {"error": str(e)}

    async def discover_mcp_tools(self) -> list[dict[str, Any]]:
        """Discover tools from all connected MCP servers.

        Returns:
            List of MCP tool definitions
        """
        if not self.bot or not self.bot.ai_agent:
            return []
        try:
            mcp_client = self.bot.ai_agent.mcp_client
            if not mcp_client or not mcp_client.is_started():
                return []
            return await mcp_client.discover_tools()
        except Exception as e:
            log.error(f"Error discovering MCP tools: {e}")
            return []

    def get_mcp_server_details(self, server_name: str) -> dict[str, Any]:
        """Get detailed information about an MCP server.

        Args:
            server_name: Name of the MCP server

        Returns:
            Server details dictionary
        """
        if not self.bot or not self.bot.ai_agent:
            return {"error": "AI agent not available"}
        try:
            mcp_client = self.bot.ai_agent.mcp_client
            if not mcp_client:
                return {"error": "MCP client not available"}
            if server_name not in mcp_client._servers:
                return {"error": f"Server not found: {server_name}"}
            server_info = mcp_client._servers[server_name]
            return {
                "name": server_name,
                "config": server_info.get("config", {}),
                "connected": server_info.get("connected", False),
            }
        except Exception as e:
            log.error(f"Error getting MCP server details: {e}")
            return {"error": str(e)}

    def get_mcp_stats(self) -> dict[str, Any]:
        """Get MCP client statistics.

        Returns:
            MCP statistics dictionary
        """
        if not self.bot or not self.bot.ai_agent:
            return {
                "enabled": False,
                "started": False,
                "server_count": 0,
                "servers": [],
                "mcp_available": False,
            }
        try:
            mcp_client = self.bot.ai_agent.mcp_client
            if not mcp_client:
                return {
                    "enabled": False,
                    "started": False,
                    "server_count": 0,
                    "servers": [],
                    "mcp_available": False,
                }
            return mcp_client.get_stats()
        except Exception as e:
            log.error(f"Error getting MCP stats: {e}")
            return {"error": str(e)}

    async def test_ai_connection(self) -> dict[str, Any]:
        """Test AI agent connection and configuration.

        Returns:
            Test result with status and details
        """
        if not self.bot:
            return {"success": False, "error": "Bot not running"}

        result = {
            "success": True,
            "ai_enabled": False,
            "model": None,
            "api_key_configured": False,
            "mcp_enabled": False,
            "mcp_servers_connected": 0,
            "multi_agent_enabled": False,
            "tools_count": 0,
            "errors": [],
        }

        try:
            if not self.bot.config.ai or not self.bot.config.ai.enabled:
                result["errors"].append("AI is not enabled in configuration")
                return result

            result["ai_enabled"] = True
            result["model"] = self.bot.config.ai.model
            result["api_key_configured"] = bool(self.bot.config.ai.api_key)

            if not self.bot.ai_agent:
                result["errors"].append("AI agent not initialized")
                return result

            result["tools_count"] = len(self.bot.ai_agent.tool_registry.list_tools())

            if self.bot.config.ai.mcp and self.bot.config.ai.mcp.enabled:
                result["mcp_enabled"] = True
                if self.bot.ai_agent.mcp_client and self.bot.ai_agent.mcp_client.is_started():
                    result["mcp_servers_connected"] = self.bot.ai_agent.mcp_client.get_server_count()

            if self.bot.config.ai.multi_agent and self.bot.config.ai.multi_agent.enabled:
                result["multi_agent_enabled"] = True

            return result

        except Exception as e:
            log.error(f"Error testing AI connection: {e}")
            result["success"] = False
            result["errors"].append(str(e))
            return result

    async def test_ai_chat(self, message: str, user_id: str = "test-user") -> dict[str, Any]:
        """Test AI chat functionality.

        Args:
            message: Test message to send
            user_id: User ID for the test conversation

        Returns:
            Test result with response or error
        """
        if not self.bot or not self.bot.ai_agent:
            return {"success": False, "error": "AI agent not available"}

        try:
            response = await self.bot.ai_agent.chat(user_id, message)
            return {
                "success": True,
                "message": message,
                "response": response,
                "user_id": user_id,
            }
        except Exception as e:
            log.error(f"Error testing AI chat: {e}")
            return {"success": False, "error": str(e)}

    async def test_ai_streaming(self, message: str, user_id: str = "test-user") -> dict[str, Any]:
        """Test AI streaming chat functionality.

        Args:
            message: Test message to send
            user_id: User ID for the test conversation

        Returns:
            Test result with streamed response or error
        """
        if not self.bot or not self.bot.ai_agent:
            return {"success": False, "error": "AI agent not available"}

        try:
            chunks = []
            async for chunk in self.bot.ai_agent.chat_stream(user_id, message):
                chunks.append(chunk)

            return {
                "success": True,
                "message": message,
                "response": "".join(chunks),
                "chunk_count": len(chunks),
                "user_id": user_id,
                "streaming": True,
            }
        except Exception as e:
            log.error(f"Error testing AI streaming: {e}")
            return {"success": False, "error": str(e)}

    def get_multi_agent_status(self) -> dict[str, Any]:
        """Get multi-agent orchestrator status.

        Returns:
            Multi-agent status dictionary
        """
        if not self.bot or not self.bot.ai_agent:
            return {
                "enabled": False,
                "mode": "N/A",
                "agent_count": 0,
                "agents": [],
            }
        try:
            return self.bot.ai_agent.orchestrator.get_stats()
        except Exception as e:
            log.error(f"Error getting multi-agent status: {e}")
            return {"error": str(e)}

    async def test_multi_agent(self, message: str, mode: str | None = None) -> dict[str, Any]:
        """Test multi-agent orchestration.

        Args:
            message: Test message to process
            mode: Orchestration mode (sequential, concurrent, hierarchical)

        Returns:
            Test result with response or error
        """
        if not self.bot or not self.bot.ai_agent:
            return {"success": False, "error": "AI agent not available"}

        try:
            orchestrator = self.bot.ai_agent.orchestrator
            if not orchestrator.config.enabled:
                return {"success": False, "error": "Multi-agent is not enabled"}

            response = await orchestrator.orchestrate(message, mode=mode)
            return {
                "success": True,
                "message": message,
                "response": response,
                "mode": mode or orchestrator.config.orchestration_mode,
            }
        except Exception as e:
            log.error(f"Error testing multi-agent: {e}")
            return {"success": False, "error": str(e)}

    async def switch_ai_model(self, model_name: str) -> dict[str, Any]:
        """Switch the AI model at runtime.

        Args:
            model_name: Name of the model to switch to

        Returns:
            Switch result
        """
        if not self.bot or not self.bot.ai_agent:
            return {"success": False, "error": "AI agent not available"}

        try:
            success = await self.bot.ai_agent.switch_model(model_name)
            return {
                "success": success,
                "model": model_name,
                "previous_model": self.bot.ai_agent.current_model if not success else None,
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            log.error(f"Error switching model: {e}")
            return {"success": False, "error": str(e)}

    def get_ai_performance_stats(self) -> dict[str, Any]:
        """Get comprehensive AI performance statistics.

        Returns:
            Performance statistics dictionary
        """
        if not self.bot or not self.bot.ai_agent:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate_percent": 0,
                "average_response_time_seconds": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
            }
        try:
            metrics = self.bot.ai_agent._metrics
            total = metrics.get("total_requests", 0)
            successful = metrics.get("successful_requests", 0)
            failed = metrics.get("failed_requests", 0)
            success_rate = (successful / total * 100) if total > 0 else 0
            avg_time = (
                metrics.get("total_response_time", 0) / successful
                if successful > 0
                else 0
            )

            return {
                "total_requests": total,
                "successful_requests": successful,
                "failed_requests": failed,
                "success_rate_percent": round(success_rate, 2),
                "average_response_time_seconds": round(avg_time, 3),
                "total_input_tokens": metrics.get("total_input_tokens", 0),
                "total_output_tokens": metrics.get("total_output_tokens", 0),
                "total_tokens": metrics.get("total_input_tokens", 0) + metrics.get("total_output_tokens", 0),
            }
        except Exception as e:
            log.error(f"Error getting AI performance stats: {e}")
            return {"error": str(e)}
