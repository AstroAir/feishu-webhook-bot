"""Task executor for running individual tasks."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from datetime import time as dt_time
from typing import TYPE_CHECKING, Any

import httpx

from ..core.config import (
    TaskActionConfig,
    TaskConditionConfig,
    TaskDefinitionConfig,
)
from ..core.logger import get_logger

if TYPE_CHECKING:
    from ..ai.agent import AIAgent

logger = get_logger("task.executor")


class TaskExecutor:
    """Executes individual tasks with condition checking and error handling."""

    def __init__(
        self,
        task: TaskDefinitionConfig,
        context: dict[str, Any],
        plugin_manager: Any = None,
        clients: dict[str, Any] | None = None,
        ai_agent: AIAgent | None = None,
    ):
        """Initialize task executor.

        Args:
            task: Task definition configuration
            context: Execution context including parameters and environment variables
            plugin_manager: Plugin manager for executing plugin methods
            clients: Dictionary of webhook clients
            ai_agent: AI agent for AI-powered task actions
        """
        self.task = task
        self.context = context
        self.plugin_manager = plugin_manager
        self.clients = clients or {}
        self.ai_agent = ai_agent
        self.logger = get_logger(f"task.{task.name}")

    def can_execute(self) -> tuple[bool, str]:
        """Check if task conditions are met.

        Returns:
            Tuple of (can_execute, reason)
        """
        if not self.task.enabled:
            return False, "Task is disabled"

        for condition in self.task.conditions:
            can_run, reason = self._check_condition(condition)
            if not can_run:
                return False, reason

        return True, "All conditions met"

    def _check_condition(self, condition: TaskConditionConfig) -> tuple[bool, str]:
        """Check a single condition.

        Args:
            condition: Condition configuration

        Returns:
            Tuple of (condition_met, reason)
        """
        if condition.type == "time_range":
            if not condition.start_time or not condition.end_time:
                return True, "No time range specified"

            now = datetime.now().time()
            start = dt_time.fromisoformat(condition.start_time)
            end = dt_time.fromisoformat(condition.end_time)

            if start <= now <= end:
                return True, "Within time range"
            return False, f"Outside time range {condition.start_time}-{condition.end_time}"

        elif condition.type == "day_of_week":
            if not condition.days:
                return True, "No day restriction"

            current_day = datetime.now().strftime("%a").lower()
            day_map = {
                "mon": "monday",
                "tue": "tuesday",
                "wed": "wednesday",
                "thu": "thursday",
                "fri": "friday",
                "sat": "saturday",
                "sun": "sunday",
            }

            allowed_days = [day.lower()[:3] for day in condition.days]
            if current_day in allowed_days or day_map.get(current_day, "") in condition.days:
                return True, "Day of week matches"
            return False, f"Day {current_day} not in allowed days"

        elif condition.type == "environment":
            if not condition.environment:
                return True, "No environment restriction"

            current_env = self.context.get("environment", "")
            if current_env == condition.environment:
                return True, "Environment matches"
            return False, f"Environment {current_env} != {condition.environment}"

        elif condition.type == "custom":
            if not condition.expression:
                return True, "No custom expression"

            try:
                # Evaluate custom expression with context
                # Make context available as both local variable and via self.context
                eval_globals: dict[str, Any] = {"__builtins__": {}}
                eval_locals: dict[str, Any] = {"context": self.context}
                result = eval(condition.expression, eval_globals, eval_locals)
                if result:
                    return True, "Custom condition met"
                return False, "Custom condition not met"
            except Exception as e:
                self.logger.error(f"Error evaluating custom condition: {e}")
                return False, f"Custom condition error: {e}"

        return True, "Unknown condition type"

    def execute(self) -> dict[str, Any]:
        """Execute the task.

        Returns:
            Execution result dictionary
        """
        start_time = time.time()
        result = {
            "task_name": self.task.name,
            "success": False,
            "start_time": start_time,
            "end_time": None,
            "duration": None,
            "actions_executed": 0,
            "actions_failed": 0,
            "error": None,
        }

        try:
            # Check conditions
            can_run, reason = self.can_execute()
            if not can_run:
                result["error"] = f"Conditions not met: {reason}"
                self.logger.info(f"Task {self.task.name} skipped: {reason}")
                return result

            # Execute actions
            for action in self.task.actions:
                try:
                    self._execute_action(action)
                    result["actions_executed"] = result["actions_executed"] + 1  # type: ignore[operator]
                except Exception as e:
                    result["actions_failed"] = result["actions_failed"] + 1  # type: ignore[operator]
                    self.logger.error(f"Action {action.type} failed: {e}", exc_info=True)

                    if not self.task.error_handling.retry_on_failure:
                        raise

            result["success"] = result["actions_failed"] == 0

        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Task {self.task.name} failed: {e}", exc_info=True)
            self._handle_error(e)

        finally:
            end_time = time.time()
            result["end_time"] = end_time
            result["duration"] = end_time - start_time

        return result

    def _execute_action(self, action: TaskActionConfig) -> None:
        """Execute a single action.

        Args:
            action: Action configuration
        """
        self.logger.debug(f"Executing action: {action.type}")

        if action.type == "plugin_method":
            self._execute_plugin_method(action)
        elif action.type == "send_message":
            self._execute_send_message(action)
        elif action.type == "http_request":
            self._execute_http_request(action)
        elif action.type == "python_code":
            self._execute_python_code(action)
        elif action.type in ("ai_chat", "ai_query"):
            self._execute_ai_action(action)
        else:
            raise ValueError(f"Unknown action type: {action.type}")

    def _execute_plugin_method(self, action: TaskActionConfig) -> None:
        """Execute a plugin method."""
        if not self.plugin_manager:
            raise RuntimeError("Plugin manager not available")

        if not action.plugin_name or not action.method_name:
            raise ValueError("plugin_name and method_name required for plugin_method action")

        plugin = self.plugin_manager.get_plugin(action.plugin_name)
        if not plugin:
            raise ValueError(f"Plugin not found: {action.plugin_name}")

        method = getattr(plugin, action.method_name, None)
        if not method or not callable(method):
            raise ValueError(
                f"Method {action.method_name} not found in plugin {action.plugin_name}"
            )

        # Call the method with parameters
        method(**action.parameters)

    def _execute_send_message(self, action: TaskActionConfig) -> None:
        """Execute send message action."""
        if not self.clients:
            raise RuntimeError("No webhook clients available")

        message = action.message or ""

        # Substitute template variables ${var} with context values
        message = self._substitute_template_vars(message)

        webhooks = action.webhooks or ["default"]

        for webhook_name in webhooks:
            client = self.clients.get(webhook_name)
            if not client:
                self.logger.warning(f"Webhook client not found: {webhook_name}")
                continue

            if action.template:
                # TODO: Integrate with template system
                self.logger.warning("Template rendering not yet implemented in task executor")
                client.send_text(message)
            else:
                client.send_text(message)

    def _substitute_template_vars(self, text: str) -> str:
        """Substitute ${var} template variables with context values.

        Args:
            text: Text containing template variables

        Returns:
            Text with variables substituted
        """
        import re

        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            value = self.context.get(var_name, match.group(0))
            return str(value)

        # Match ${variable_name} pattern
        return re.sub(r"\$\{([^}]+)\}", replacer, text)

    def _execute_http_request(self, action: TaskActionConfig) -> Any:
        """Execute HTTP request action."""
        if not action.request:
            raise ValueError("request configuration required for http_request action")

        request = action.request

        with httpx.Client(timeout=request.timeout or 10.0) as client:
            response = client.request(
                request.method,
                request.url,
                headers=request.headers,
                params=request.params,
                json=request.json_body,
                data=request.data_body,
            )
            response.raise_for_status()

            if request.save_as:
                if "application/json" in response.headers.get("content-type", ""):
                    self.context[request.save_as] = response.json()
                else:
                    self.context[request.save_as] = response.text

            return response

    def _execute_python_code(self, action: TaskActionConfig) -> None:
        """Execute Python code action."""
        if not action.code:
            raise ValueError("code required for python_code action")

        # Execute code with limited context for security
        exec_globals = {
            "__builtins__": __builtins__,
            "logger": self.logger,
            "context": self.context,
        }
        exec(action.code, exec_globals)

    def _execute_ai_action(self, action: TaskActionConfig) -> None:
        """Execute AI chat or query action.

        Args:
            action: Action configuration with AI parameters

        Raises:
            RuntimeError: If AI agent is not available
            ValueError: If action configuration is invalid
        """
        if not self.ai_agent:
            raise RuntimeError("AI agent not available - ensure AI is enabled in bot configuration")

        # Import here to avoid circular dependency
        from ..ai.task_integration import execute_ai_task_action

        # Execute AI action asynchronously
        result = asyncio.run(execute_ai_task_action(action, self.context, self.ai_agent))

        if not result.success:
            error_msg = result.error or "AI action failed"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.logger.info(
            "AI action completed: %s (confidence: %s, tools: %s)",
            result.response[:100] + "..." if len(result.response) > 100 else result.response,
            result.confidence,
            result.tools_called,
        )

    def _handle_error(self, error: Exception) -> None:
        """Handle task execution error.

        Args:
            error: The exception that occurred
        """
        error_handling = self.task.error_handling

        if error_handling.on_failure_action == "log":
            self.logger.error(f"Task {self.task.name} failed: {error}")

        elif error_handling.on_failure_action == "notify":
            if error_handling.notification_webhook and self.clients:
                client = self.clients.get(error_handling.notification_webhook)
                if client:
                    try:
                        client.send_text(f"⚠️ Task '{self.task.name}' failed: {error}")
                    except Exception as e:
                        self.logger.error(f"Failed to send error notification: {e}")

        elif error_handling.on_failure_action == "disable":
            self.logger.warning(f"Task {self.task.name} will be disabled due to failure")
            # Note: Actual disabling would need to be handled by TaskManager

        # "ignore" action does nothing
