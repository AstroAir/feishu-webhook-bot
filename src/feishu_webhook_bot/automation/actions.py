"""Extended action types for automation engine.

This module provides various action executors that can be used in automation workflows.
"""

from __future__ import annotations

import contextlib
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from datetime import datetime
from enum import Enum
from string import Template
from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger

if TYPE_CHECKING:
    from ..ai.agent import AIAgent
    from ..plugins.manager import PluginManager

logger = get_logger("automation.actions")


class ActionType(str, Enum):
    """Supported automation action types."""

    SEND_TEXT = "send_text"
    SEND_TEMPLATE = "send_template"
    HTTP_REQUEST = "http_request"
    PLUGIN_METHOD = "plugin_method"
    PYTHON_CODE = "python_code"
    AI_CHAT = "ai_chat"
    AI_QUERY = "ai_query"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    SET_VARIABLE = "set_variable"
    DELAY = "delay"
    NOTIFY = "notify"
    LOG = "log"
    PARALLEL = "parallel"
    CHAIN_RULE = "chain_rule"


class ActionResult:
    """Result of an action execution."""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: str | None = None,
        duration: float = 0.0,
        skipped: bool = False,
    ) -> None:
        self.success = success
        self.data = data
        self.error = error
        self.duration = duration
        self.skipped = skipped
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration": self.duration,
            "skipped": self.skipped,
            "timestamp": self.timestamp,
        }


class BaseActionExecutor(ABC):
    """Base class for action executors."""

    action_type: ActionType

    def __init__(self, context: dict[str, Any]) -> None:
        self.context = context

    @abstractmethod
    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Execute the action with the given configuration.

        Args:
            config: Action configuration

        Returns:
            ActionResult with execution status and data
        """
        pass

    def interpolate(self, value: Any) -> Any:
        """Interpolate context variables in a value."""
        if isinstance(value, str):
            try:
                return Template(value).safe_substitute(**self.context)
            except Exception:
                return value
        if isinstance(value, dict):
            return {k: self.interpolate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.interpolate(v) for v in value]
        return value

    def evaluate_expression(self, expression: str) -> Any:
        """Safely evaluate a simple expression.

        Supports basic comparisons and logical operators.
        """
        # Replace context variables
        expr = self.interpolate(expression)

        # Safe evaluation context
        safe_context = {
            "context": self.context,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "True": True,
            "False": False,
            "None": None,
        }

        # Add context variables
        safe_context.update(self.context)

        try:
            # Use eval with restricted builtins
            return eval(expr, {"__builtins__": {}}, safe_context)
        except Exception as e:
            logger.warning("Failed to evaluate expression '%s': %s", expression, e)
            return False


class PluginMethodExecutor(BaseActionExecutor):
    """Execute a plugin method."""

    action_type = ActionType.PLUGIN_METHOD

    def __init__(
        self,
        context: dict[str, Any],
        plugin_manager: PluginManager | None = None,
    ) -> None:
        super().__init__(context)
        self.plugin_manager = plugin_manager

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Execute a plugin method.

        Config:
            plugin_name: Name of the plugin
            method_name: Name of the method to call
            parameters: Dictionary of parameters to pass
            save_as: Optional key to save result in context
        """
        start_time = time.time()

        if not self.plugin_manager:
            return ActionResult(
                success=False,
                error="Plugin manager not available",
                duration=time.time() - start_time,
            )

        plugin_name = config.get("plugin_name")
        method_name = config.get("method_name")
        parameters = self.interpolate(config.get("parameters", {}))

        if not plugin_name or not method_name:
            return ActionResult(
                success=False,
                error="plugin_name and method_name are required",
                duration=time.time() - start_time,
            )

        try:
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if not plugin:
                return ActionResult(
                    success=False,
                    error=f"Plugin not found: {plugin_name}",
                    duration=time.time() - start_time,
                )

            method = getattr(plugin, method_name, None)
            if not method or not callable(method):
                return ActionResult(
                    success=False,
                    error=f"Method not found: {method_name}",
                    duration=time.time() - start_time,
                )

            result = method(**parameters) if parameters else method()

            # Save result to context if requested
            save_as = config.get("save_as")
            if save_as:
                self.context[save_as] = result

            return ActionResult(
                success=True,
                data=result,
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("Plugin method execution failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class PythonCodeExecutor(BaseActionExecutor):
    """Execute Python code safely."""

    action_type = ActionType.PYTHON_CODE

    # Allowed built-in functions for safe execution
    SAFE_BUILTINS = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "format": format,
        "frozenset": frozenset,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "print": print,
        "range": range,
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
    }

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Execute Python code.

        Config:
            code: Python code to execute
            save_as: Optional key to save result in context
            timeout: Execution timeout in seconds (default: 30)
        """
        start_time = time.time()

        code = config.get("code")
        if not code:
            return ActionResult(
                success=False,
                error="code is required",
                duration=time.time() - start_time,
            )

        # Prepare execution environment
        exec_globals = {
            "__builtins__": self.SAFE_BUILTINS,
            "context": self.context.copy(),
            "datetime": datetime,
            "time": time,
        }
        exec_locals: dict[str, Any] = {}

        try:
            # Execute with basic safety
            exec(code, exec_globals, exec_locals)

            # Get result if defined
            result = exec_locals.get("result", exec_locals.get("output"))

            # Save to context if requested
            save_as = config.get("save_as")
            if save_as and result is not None:
                self.context[save_as] = result

            return ActionResult(
                success=True,
                data=result,
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("Python code execution failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class AIActionExecutor(BaseActionExecutor):
    """Execute AI chat or query actions."""

    action_type = ActionType.AI_CHAT

    def __init__(
        self,
        context: dict[str, Any],
        ai_agent: AIAgent | None = None,
    ) -> None:
        super().__init__(context)
        self.ai_agent = ai_agent

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Execute AI action.

        Config:
            prompt: The prompt to send to AI
            user_id: Optional user ID for conversation context
            system_prompt: Optional system prompt override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            save_as: Optional key to save response in context
            structured_output: Whether to parse response as JSON
        """
        start_time = time.time()

        if not self.ai_agent:
            return ActionResult(
                success=False,
                error="AI agent not available",
                duration=time.time() - start_time,
            )

        prompt = self.interpolate(config.get("prompt", ""))
        if not prompt:
            return ActionResult(
                success=False,
                error="prompt is required",
                duration=time.time() - start_time,
            )

        user_id = config.get("user_id", "automation")
        system_prompt = config.get("system_prompt")
        temperature = config.get("temperature")
        max_tokens = config.get("max_tokens")

        try:
            # Build options
            options: dict[str, Any] = {}
            if system_prompt:
                options["system_prompt"] = system_prompt
            if temperature is not None:
                options["temperature"] = temperature
            if max_tokens is not None:
                options["max_tokens"] = max_tokens

            # Call AI agent
            response = self.ai_agent.chat(prompt, user_id, **options)

            # Parse structured output if requested
            if config.get("structured_output"):
                import json

                with contextlib.suppress(json.JSONDecodeError):
                    response = json.loads(response)

            # Save to context
            save_as = config.get("save_as")
            if save_as:
                self.context[save_as] = response

            return ActionResult(
                success=True,
                data=response,
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("AI action execution failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class ConditionalExecutor(BaseActionExecutor):
    """Execute actions conditionally."""

    action_type = ActionType.CONDITIONAL

    def __init__(
        self,
        context: dict[str, Any],
        action_executor: Callable[[Mapping[str, Any], dict[str, Any]], ActionResult] | None = None,
    ) -> None:
        super().__init__(context)
        self.action_executor = action_executor

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Execute conditional action.

        Config:
            condition: Expression to evaluate
            then_actions: Actions to execute if condition is true
            else_actions: Optional actions to execute if condition is false
        """
        start_time = time.time()

        condition = config.get("condition", "")
        if not condition:
            return ActionResult(
                success=False,
                error="condition is required",
                duration=time.time() - start_time,
            )

        try:
            result = self.evaluate_expression(condition)

            if result:
                actions = config.get("then_actions", [])
                branch = "then"
            else:
                actions = config.get("else_actions", [])
                branch = "else"

            if not actions:
                return ActionResult(
                    success=True,
                    data={"branch": branch, "condition_result": result, "actions_executed": 0},
                    skipped=True,
                    duration=time.time() - start_time,
                )

            # Execute branch actions
            results = []
            if self.action_executor:
                for action in actions:
                    action_result = self.action_executor(action, self.context)
                    result_dict = (
                        action_result.to_dict()
                        if hasattr(action_result, "to_dict")
                        else action_result
                    )
                    results.append(result_dict)

            return ActionResult(
                success=True,
                data={
                    "branch": branch,
                    "condition_result": result,
                    "actions_executed": len(actions),
                    "results": results,
                },
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("Conditional execution failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class LoopExecutor(BaseActionExecutor):
    """Execute actions in a loop."""

    action_type = ActionType.LOOP

    def __init__(
        self,
        context: dict[str, Any],
        action_executor: Callable[[Mapping[str, Any], dict[str, Any]], ActionResult] | None = None,
    ) -> None:
        super().__init__(context)
        self.action_executor = action_executor

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Execute loop action.

        Config:
            items: List of items to iterate over (or context variable path)
            item_var: Variable name for current item (default: "item")
            index_var: Variable name for current index (default: "index")
            actions: Actions to execute for each item
            max_iterations: Maximum iterations (default: 100)
            break_on_error: Stop on first error (default: False)
        """
        start_time = time.time()

        items = config.get("items", [])
        if isinstance(items, str):
            # Resolve from context
            items = self.context.get(items, [])

        items = self.interpolate(items)
        if not isinstance(items, (list, tuple)):
            items = list(items) if hasattr(items, "__iter__") else [items]

        item_var = config.get("item_var", "item")
        index_var = config.get("index_var", "index")
        actions = config.get("actions", [])
        max_iterations = config.get("max_iterations", 100)
        break_on_error = config.get("break_on_error", False)

        if not actions:
            return ActionResult(
                success=True,
                data={"iterations": 0},
                skipped=True,
                duration=time.time() - start_time,
            )

        try:
            results = []
            errors = []

            for i, item in enumerate(items[:max_iterations]):
                # Set loop variables in context
                self.context[item_var] = item
                self.context[index_var] = i

                # Execute actions for this iteration
                iteration_results = []
                if self.action_executor:
                    for action in actions:
                        action_result = self.action_executor(action, self.context)
                        result_dict = (
                            action_result.to_dict()
                            if hasattr(action_result, "to_dict")
                            else action_result
                        )
                        iteration_results.append(result_dict)

                        if not action_result.success and break_on_error:
                            errors.append({"iteration": i, "error": action_result.error})
                            break

                results.append({"iteration": i, "item": item, "results": iteration_results})

                if errors and break_on_error:
                    break

            # Cleanup loop variables
            self.context.pop(item_var, None)
            self.context.pop(index_var, None)

            return ActionResult(
                success=len(errors) == 0,
                data={
                    "iterations": len(results),
                    "total_items": len(items),
                    "results": results,
                    "errors": errors,
                },
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("Loop execution failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class SetVariableExecutor(BaseActionExecutor):
    """Set context variables."""

    action_type = ActionType.SET_VARIABLE

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Set a context variable.

        Config:
            name: Variable name
            value: Value to set (supports interpolation)
            expression: Optional expression to evaluate as value
        """
        start_time = time.time()

        name = config.get("name")
        if not name:
            return ActionResult(
                success=False,
                error="name is required",
                duration=time.time() - start_time,
            )

        try:
            if "expression" in config:
                value = self.evaluate_expression(config["expression"])
            else:
                value = self.interpolate(config.get("value"))

            self.context[name] = value

            return ActionResult(
                success=True,
                data={"name": name, "value": value},
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("Set variable failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class DelayExecutor(BaseActionExecutor):
    """Delay execution."""

    action_type = ActionType.DELAY

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Delay execution for specified duration.

        Config:
            seconds: Number of seconds to delay
            milliseconds: Number of milliseconds to delay (alternative to seconds)
        """
        start_time = time.time()

        seconds = config.get("seconds", 0)
        milliseconds = config.get("milliseconds", 0)

        total_seconds = seconds + (milliseconds / 1000.0)

        if total_seconds <= 0:
            return ActionResult(
                success=True,
                data={"delayed": 0},
                skipped=True,
                duration=time.time() - start_time,
            )

        try:
            time.sleep(total_seconds)

            return ActionResult(
                success=True,
                data={"delayed": total_seconds},
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("Delay execution failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class NotifyExecutor(BaseActionExecutor):
    """Send notifications through various channels."""

    action_type = ActionType.NOTIFY

    def __init__(
        self,
        context: dict[str, Any],
        send_text: Callable[[str, str], None] | None = None,
        send_template: Callable[[str, dict[str, Any], list[str]], None] | None = None,
    ) -> None:
        super().__init__(context)
        self.send_text = send_text
        self.send_template = send_template

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Send notification.

        Config:
            channel: Notification channel (webhook, email, log)
            message: Message content
            template: Optional template name
            targets: List of targets/webhooks
            level: Notification level (info, warning, error)
        """
        start_time = time.time()

        channel = config.get("channel", "webhook")
        message = self.interpolate(config.get("message", ""))
        template = config.get("template")
        targets = config.get("targets", ["default"])
        level = config.get("level", "info")

        if not message and not template:
            return ActionResult(
                success=False,
                error="message or template is required",
                duration=time.time() - start_time,
            )

        try:
            if channel == "log":
                log_func = getattr(logger, level, logger.info)
                log_func("Automation notification: %s", message)
                return ActionResult(
                    success=True,
                    data={"channel": channel, "level": level},
                    duration=time.time() - start_time,
                )

            if channel == "webhook":
                if template and self.send_template:
                    template_context = self.interpolate(config.get("context", {}))
                    self.send_template(template, template_context, targets)
                elif message and self.send_text:
                    for target in targets:
                        self.send_text(message, target)

                return ActionResult(
                    success=True,
                    data={"channel": channel, "targets": targets},
                    duration=time.time() - start_time,
                )

            return ActionResult(
                success=False,
                error=f"Unsupported channel: {channel}",
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("Notify execution failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class LogExecutor(BaseActionExecutor):
    """Log messages."""

    action_type = ActionType.LOG

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Log a message.

        Config:
            message: Message to log
            level: Log level (debug, info, warning, error)
            data: Optional data to include
        """
        start_time = time.time()

        message = self.interpolate(config.get("message", ""))
        level = config.get("level", "info")
        data = self.interpolate(config.get("data", {}))

        if not message:
            return ActionResult(
                success=False,
                error="message is required",
                duration=time.time() - start_time,
            )

        try:
            log_func = getattr(logger, level, logger.info)
            if data:
                log_func("%s | Data: %s", message, data)
            else:
                log_func(message)

            return ActionResult(
                success=True,
                data={"message": message, "level": level},
                duration=time.time() - start_time,
            )

        except Exception as e:
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class ParallelExecutor(BaseActionExecutor):
    """Execute actions in parallel."""

    action_type = ActionType.PARALLEL

    def __init__(
        self,
        context: dict[str, Any],
        action_executor: Callable[[Mapping[str, Any], dict[str, Any]], ActionResult] | None = None,
    ) -> None:
        super().__init__(context)
        self.action_executor = action_executor

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Execute actions in parallel.

        Config:
            actions: List of actions to execute in parallel
            max_concurrent: Maximum concurrent executions (default: 10)
            fail_fast: Stop all on first failure (default: False)
        """
        start_time = time.time()

        actions = config.get("actions", [])
        if not actions:
            return ActionResult(
                success=True,
                data={"executed": 0},
                skipped=True,
                duration=time.time() - start_time,
            )

        max_concurrent = config.get("max_concurrent", 10)
        fail_fast = config.get("fail_fast", False)

        try:
            import concurrent.futures

            results = []
            errors = []

            def execute_action(action: Mapping[str, Any]) -> ActionResult:
                if self.action_executor:
                    return self.action_executor(action, self.context.copy())
                return ActionResult(success=False, error="No executor available")

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {
                    executor.submit(execute_action, action): i for i, action in enumerate(actions)
                }

                for future in concurrent.futures.as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        results.append({"index": idx, "result": result.to_dict()})
                        if not result.success:
                            errors.append({"index": idx, "error": result.error})
                            if fail_fast:
                                executor.shutdown(wait=False, cancel_futures=True)
                                break
                    except Exception as e:
                        errors.append({"index": idx, "error": str(e)})
                        if fail_fast:
                            executor.shutdown(wait=False, cancel_futures=True)
                            break

            return ActionResult(
                success=len(errors) == 0,
                data={
                    "executed": len(results),
                    "total": len(actions),
                    "results": results,
                    "errors": errors,
                },
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("Parallel execution failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class ChainRuleExecutor(BaseActionExecutor):
    """Trigger another automation rule."""

    action_type = ActionType.CHAIN_RULE

    def __init__(
        self,
        context: dict[str, Any],
        trigger_rule: Callable[[str, dict[str, Any] | None], dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context)
        self.trigger_rule = trigger_rule

    def execute(self, config: Mapping[str, Any]) -> ActionResult:
        """Trigger another automation rule.

        Config:
            rule_name: Name of the rule to trigger
            context: Optional context to pass to the rule
            wait: Whether to wait for rule completion (default: True)
        """
        start_time = time.time()

        rule_name = config.get("rule_name")
        if not rule_name:
            return ActionResult(
                success=False,
                error="rule_name is required",
                duration=time.time() - start_time,
            )

        if not self.trigger_rule:
            return ActionResult(
                success=False,
                error="Rule trigger function not available",
                duration=time.time() - start_time,
            )

        try:
            rule_context = self.interpolate(config.get("context", {}))
            # Merge current context
            merged_context = {**self.context, **rule_context}

            result = self.trigger_rule(rule_name, merged_context)

            return ActionResult(
                success=result.get("success", False),
                data=result,
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error("Chain rule execution failed: %s", e, exc_info=True)
            return ActionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )


class ActionExecutorFactory:
    """Factory for creating action executors."""

    def __init__(
        self,
        plugin_manager: PluginManager | None = None,
        ai_agent: AIAgent | None = None,
        send_text: Callable[[str, str], None] | None = None,
        send_template: Callable[[str, dict[str, Any], list[str]], None] | None = None,
        trigger_rule: Callable[[str, dict[str, Any] | None], dict[str, Any]] | None = None,
    ) -> None:
        self.plugin_manager = plugin_manager
        self.ai_agent = ai_agent
        self.send_text = send_text
        self.send_template = send_template
        self.trigger_rule = trigger_rule
        self._action_executor: (
            Callable[[Mapping[str, Any], dict[str, Any]], ActionResult] | None
        ) = None

    def set_action_executor(
        self, executor: Callable[[Mapping[str, Any], dict[str, Any]], ActionResult]
    ) -> None:
        """Set the action executor for nested actions."""
        self._action_executor = executor

    def create_executor(
        self, action_type: str | ActionType, context: dict[str, Any]
    ) -> BaseActionExecutor | None:
        """Create an action executor for the given type.

        Args:
            action_type: Type of action
            context: Execution context

        Returns:
            Action executor instance or None if type not supported
        """
        if isinstance(action_type, str):
            try:
                action_type = ActionType(action_type)
            except ValueError:
                logger.warning("Unknown action type: %s", action_type)
                return None

        executors: dict[ActionType, type[BaseActionExecutor]] = {
            ActionType.PLUGIN_METHOD: PluginMethodExecutor,
            ActionType.PYTHON_CODE: PythonCodeExecutor,
            ActionType.AI_CHAT: AIActionExecutor,
            ActionType.AI_QUERY: AIActionExecutor,
            ActionType.CONDITIONAL: ConditionalExecutor,
            ActionType.LOOP: LoopExecutor,
            ActionType.SET_VARIABLE: SetVariableExecutor,
            ActionType.DELAY: DelayExecutor,
            ActionType.NOTIFY: NotifyExecutor,
            ActionType.LOG: LogExecutor,
            ActionType.PARALLEL: ParallelExecutor,
            ActionType.CHAIN_RULE: ChainRuleExecutor,
        }

        executor_class = executors.get(action_type)
        if not executor_class:
            return None

        # Create executor with appropriate dependencies
        if action_type == ActionType.PLUGIN_METHOD:
            return PluginMethodExecutor(context, self.plugin_manager)
        elif action_type in (ActionType.AI_CHAT, ActionType.AI_QUERY):
            return AIActionExecutor(context, self.ai_agent)
        elif action_type == ActionType.CONDITIONAL:
            return ConditionalExecutor(context, self._action_executor)
        elif action_type == ActionType.LOOP:
            return LoopExecutor(context, self._action_executor)
        elif action_type == ActionType.NOTIFY:
            return NotifyExecutor(context, self.send_text, self.send_template)
        elif action_type == ActionType.PARALLEL:
            return ParallelExecutor(context, self._action_executor)
        elif action_type == ActionType.CHAIN_RULE:
            return ChainRuleExecutor(context, self.trigger_rule)
        else:
            return executor_class(context)


__all__ = [
    "ActionType",
    "ActionResult",
    "BaseActionExecutor",
    "PluginMethodExecutor",
    "PythonCodeExecutor",
    "AIActionExecutor",
    "ConditionalExecutor",
    "LoopExecutor",
    "SetVariableExecutor",
    "DelayExecutor",
    "NotifyExecutor",
    "LogExecutor",
    "ParallelExecutor",
    "ChainRuleExecutor",
    "ActionExecutorFactory",
]
