"""Task executor for running individual tasks."""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
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
from ..core.provider import BaseProvider
from ..core.templates import RenderedTemplate, TemplateRegistry

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
        providers: dict[str, BaseProvider] | None = None,
        template_registry: TemplateRegistry | None = None,
    ):
        """Initialize task executor.

        Args:
            task: Task definition configuration
            context: Execution context including parameters and environment variables
            plugin_manager: Plugin manager for executing plugin methods
            clients: Dictionary of webhook clients
            ai_agent: AI agent for AI-powered task actions
            providers: Dictionary of message providers (new architecture)
            template_registry: Template registry for rendering message templates
        """
        self.task = task
        self.context = context
        self.plugin_manager = plugin_manager
        self.clients = clients or {}
        self.providers = providers or {}
        self.ai_agent = ai_agent
        self.template_registry = template_registry
        self.logger = get_logger(f"task.{task.name}")

    def _execute_with_timeout(
        self,
        func: Any,
        timeout: float | None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function with timeout protection.

        Args:
            func: Function to execute
            timeout: Timeout in seconds (None or <=0 means no timeout)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            TimeoutError: If execution exceeds timeout
        """
        if timeout is None or timeout <= 0:
            return func(*args, **kwargs)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout)
            except FutureTimeout:
                raise TimeoutError(f"Execution timed out after {timeout}s")

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
        result: dict[str, Any] = {
            "task_name": self.task.name,
            "success": False,
            "start_time": start_time,
            "end_time": None,
            "duration": None,
            "actions_executed": 0,
            "actions_failed": 0,
            "error": None,
            "timed_out": False,
        }

        # Get task-level timeout
        task_timeout = getattr(self.task, "timeout", None)

        try:
            # Check conditions
            can_run, reason = self.can_execute()
            if not can_run:
                result["error"] = f"Conditions not met: {reason}"
                self.logger.info(f"Task {self.task.name} skipped: {reason}")
                return result

            # Execute actions with optional timeout
            for action in self.task.actions:
                try:
                    if task_timeout and task_timeout > 0:
                        # Calculate remaining time for this action
                        elapsed = time.time() - start_time
                        remaining = task_timeout - elapsed
                        if remaining <= 0:
                            raise TimeoutError(
                                f"Task {self.task.name} timed out after {task_timeout}s"
                            )
                        self._execute_with_timeout(
                            self._execute_action, remaining, action
                        )
                    else:
                        self._execute_action(action)

                    result["actions_executed"] += 1

                except TimeoutError as e:
                    result["error"] = str(e)
                    result["timed_out"] = True
                    self.logger.error(f"Task {self.task.name} timed out: {e}")
                    break

                except Exception as e:
                    result["actions_failed"] += 1
                    self.logger.error(f"Action {action.type} failed: {e}", exc_info=True)

                    if not self.task.error_handling.retry_on_failure:
                        raise

            if not result["timed_out"]:
                result["success"] = result["actions_failed"] == 0

        except TimeoutError as e:
            result["error"] = str(e)
            result["timed_out"] = True
            self.logger.error(f"Task {self.task.name} timed out: {e}")

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

    def _get_client_or_provider(self, name: str) -> Any:
        """Get a client or provider by name.

        Providers take precedence over legacy clients.

        Args:
            name: Client or provider name

        Returns:
            Client or provider instance, or None if not found
        """
        if name in self.providers:
            return self.providers[name]
        return self.clients.get(name)

    def _execute_send_message(self, action: TaskActionConfig) -> None:
        """Execute send message action."""
        if not self.clients and not self.providers:
            raise RuntimeError("No webhook clients or providers available")

        webhooks = action.webhooks or ["default"]

        # Handle template rendering if specified
        if action.template:
            if not self.template_registry:
                self.logger.warning(
                    f"Template '{action.template}' requested but no registry available, "
                    "falling back to plain message"
                )
            else:
                try:
                    rendered = self.template_registry.render(action.template, self.context)
                    self._send_rendered_template(rendered, webhooks)
                    return
                except Exception as e:
                    self.logger.error(f"Template rendering failed: {e}", exc_info=True)
                    raise

        # Fall back to plain message
        message = action.message or ""

        # Substitute template variables ${var} with context values
        message = self._substitute_template_vars(message)

        for webhook_name in webhooks:
            sender = self._get_client_or_provider(webhook_name)
            if not sender:
                self.logger.warning(f"Webhook/provider not found: {webhook_name}")
                continue

            # Check if it's a provider (has send_text with target param)
            if isinstance(sender, BaseProvider):
                sender.send_text(message, "")
            else:
                sender.send_text(message)

    def _send_rendered_template(
        self, rendered: RenderedTemplate, webhooks: list[str]
    ) -> None:
        """Send a rendered template to specified webhooks.

        Args:
            rendered: Rendered template with type and content
            webhooks: List of webhook names to send to
        """
        for webhook_name in webhooks:
            sender = self._get_client_or_provider(webhook_name)
            if not sender:
                self.logger.warning(f"Webhook/provider not found: {webhook_name}")
                continue

            message_type = rendered.type.lower()
            content = rendered.content

            try:
                if message_type == "text":
                    text_value = content if isinstance(content, str) else str(content)
                    if isinstance(sender, BaseProvider):
                        sender.send_text(text_value, "")
                    else:
                        sender.send_text(text_value)

                elif message_type in ("card", "interactive"):
                    if hasattr(sender, "send_card"):
                        sender.send_card(content)
                    else:
                        self.logger.warning(
                            f"Sender {webhook_name} does not support cards, "
                            "sending as text"
                        )
                        text = str(content)
                        if isinstance(sender, BaseProvider):
                            sender.send_text(text, "")
                        else:
                            sender.send_text(text)

                elif message_type == "post":
                    if not isinstance(content, dict):
                        raise ValueError("Post template must render to a dictionary")
                    if hasattr(sender, "send_rich_text"):
                        title = content.get("title", "")
                        rich_content = content.get("content", [])
                        language = content.get("language", "zh_cn")
                        sender.send_rich_text(title, rich_content, language=language)
                    else:
                        self.logger.warning(
                            f"Sender {webhook_name} does not support rich text, "
                            "sending as text"
                        )
                        text = str(content)
                        if isinstance(sender, BaseProvider):
                            sender.send_text(text, "")
                        else:
                            sender.send_text(text)

                else:
                    # Fallback: send as text
                    text = str(content)
                    if isinstance(sender, BaseProvider):
                        sender.send_text(text, "")
                    else:
                        sender.send_text(text)

                self.logger.debug(
                    f"Sent {message_type} template to {webhook_name}"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to send template to {webhook_name}: {e}",
                    exc_info=True,
                )
                raise

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

    # Safe builtins for sandboxed Python code execution
    _SAFE_BUILTINS: dict[str, Any] = {
        # Safe functions
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "frozenset": frozenset,
        "int": int,
        "isinstance": isinstance,
        "issubclass": issubclass,
        "iter": iter,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "next": next,
        "range": range,
        "repr": repr,
        "reversed": reversed,
        "round": round,
        "set": set,
        "slice": slice,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "type": type,
        "zip": zip,
        # Safe string methods
        "chr": chr,
        "ord": ord,
        "format": format,
        # Safe exceptions
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "AttributeError": AttributeError,
        "RuntimeError": RuntimeError,
        "StopIteration": StopIteration,
        # Constants
        "True": True,
        "False": False,
        "None": None,
        # Explicitly forbidden (set to None to prevent access)
        "__import__": None,
        "eval": None,
        "exec": None,
        "compile": None,
        "open": None,
        "input": None,
        "breakpoint": None,
        "globals": None,
        "locals": None,
        "vars": None,
        "dir": None,
        "getattr": None,
        "setattr": None,
        "delattr": None,
        "hasattr": None,
    }

    def _execute_python_code(self, action: TaskActionConfig) -> None:
        """Execute Python code action with security restrictions.

        The code runs in a sandboxed environment with:
        - Limited builtins (no import, eval, exec, file operations)
        - Timeout protection (uses task timeout or default 30s)
        - Safe utility modules (datetime, json, re, math)

        Args:
            action: Task action with code to execute

        Raises:
            ValueError: If code is not provided
            TimeoutError: If execution exceeds timeout
            Exception: If code raises an exception
        """
        if not action.code:
            raise ValueError("code required for python_code action")

        # Get timeout from task or use default
        timeout = getattr(self.task, "timeout", None) or 30.0

        # Import safe modules once
        import datetime as datetime_module
        import json as json_module
        import re as re_module
        import math as math_module
        import collections as collections_module
        import time as time_module

        # Create restricted execution environment
        exec_globals: dict[str, Any] = {
            "__builtins__": self._SAFE_BUILTINS.copy(),
            # Provide logger and context for task interaction
            "logger": self.logger,
            "context": self.context,
            # Safe utility modules (pre-imported)
            "datetime": datetime_module,
            "json": json_module,
            "re": re_module,
            "math": math_module,
            "collections": collections_module,
            "time": time_module,
        }

        def run_code() -> None:
            exec(action.code, exec_globals)

        # Execute with timeout protection
        self._execute_with_timeout(run_code, timeout)

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
        import concurrent.futures

        # Execute AI action with proper async handling
        # Handle both sync and async contexts safely
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        coro = execute_ai_task_action(action, self.context, self.ai_agent)

        if loop and loop.is_running():
            # Already in an async context - use thread pool to avoid nested asyncio.run()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                result = future.result()
        else:
            # Not in async context - safe to use asyncio.run()
            result = asyncio.run(coro)

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
            if error_handling.notification_webhook and (self.clients or self.providers):
                sender = self._get_client_or_provider(error_handling.notification_webhook)
                if sender:
                    try:
                        error_msg = f"⚠️ Task '{self.task.name}' failed: {error}"
                        if isinstance(sender, BaseProvider):
                            sender.send_text(error_msg, "")
                        else:
                            sender.send_text(error_msg)
                    except Exception as e:
                        self.logger.error(f"Failed to send error notification: {e}")

        elif error_handling.on_failure_action == "disable":
            self.logger.warning(f"Task {self.task.name} will be disabled due to failure")
            # Note: Actual disabling would need to be handled by TaskManager

        # "ignore" action does nothing
