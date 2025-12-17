"""Workflow management for automation engine.

This module provides workflow orchestration, dependency management,
and workflow templates.
"""

from __future__ import annotations

import copy
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..core.logger import get_logger

logger = get_logger("automation.workflow")


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    WAITING = "waiting"


class DependencyType(str, Enum):
    """Type of dependency between workflows/rules."""

    SUCCESS = "success"
    COMPLETION = "completion"
    FAILURE = "failure"
    ANY = "any"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    name: str
    action_type: str
    config: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    condition: str | None = None
    retry_config: dict[str, Any] | None = None
    timeout: float | None = None
    on_error: str = "fail"


@dataclass
class WorkflowExecution:
    """Tracks the execution of a workflow."""

    workflow_id: str
    rule_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    current_step: int = 0
    total_steps: int = 0
    step_results: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    retries: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "rule_name": self.rule_name,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_results": self.step_results,
            "error": self.error,
            "retries": self.retries,
        }


@dataclass
class WorkflowTemplate:
    """Reusable workflow template."""

    name: str
    description: str
    steps: list[WorkflowStep]
    parameters: list[dict[str, Any]] = field(default_factory=list)
    default_context: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "name": s.name,
                    "action_type": s.action_type,
                    "config": s.config,
                    "depends_on": s.depends_on,
                    "condition": s.condition,
                    "retry_config": s.retry_config,
                    "timeout": s.timeout,
                    "on_error": s.on_error,
                }
                for s in self.steps
            ],
            "parameters": self.parameters,
            "default_context": self.default_context,
            "tags": self.tags,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowTemplate:
        """Create from dictionary."""
        steps = [
            WorkflowStep(
                name=s.get("name", ""),
                action_type=s.get("action_type", ""),
                config=s.get("config", {}),
                depends_on=s.get("depends_on", []),
                condition=s.get("condition"),
                retry_config=s.get("retry_config"),
                timeout=s.get("timeout"),
                on_error=s.get("on_error", "fail"),
            )
            for s in data.get("steps", [])
        ]
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=steps,
            parameters=data.get("parameters", []),
            default_context=data.get("default_context", {}),
            tags=data.get("tags", []),
            version=data.get("version", "1.0.0"),
        )


class DependencyResolver:
    """Resolves dependencies between workflow steps."""

    def __init__(self, steps: list[WorkflowStep]) -> None:
        self.steps = {s.name: s for s in steps}
        self._resolved: set[str] = set()
        self._in_progress: set[str] = set()

    def get_execution_order(self) -> list[list[str]]:
        """Get steps grouped by execution order (parallel groups).

        Returns:
            List of step name lists, where each inner list can be executed in parallel
        """
        order: list[list[str]] = []
        remaining = set(self.steps.keys())

        while remaining:
            # Find steps whose dependencies are all resolved
            ready = []
            for name in remaining:
                step = self.steps[name]
                if all(dep in self._resolved for dep in step.depends_on):
                    ready.append(name)

            if not ready:
                # Circular dependency detected
                raise ValueError(f"Circular dependency detected among: {remaining}")

            order.append(ready)
            for name in ready:
                self._resolved.add(name)
                remaining.remove(name)

        return order

    def can_execute(self, step_name: str, completed: set[str]) -> bool:
        """Check if a step can be executed given completed steps."""
        step = self.steps.get(step_name)
        if not step:
            return False
        return all(dep in completed for dep in step.depends_on)

    def get_next_steps(self, completed: set[str]) -> list[str]:
        """Get steps that can be executed next."""
        pending = set(self.steps.keys()) - completed - self._in_progress
        return [name for name in pending if self.can_execute(name, completed)]


class WorkflowOrchestrator:
    """Orchestrates workflow execution with dependency management."""

    def __init__(
        self,
        action_executor: Callable[[dict[str, Any], dict[str, Any]], Any],
        max_concurrent: int = 5,
    ) -> None:
        self.action_executor = action_executor
        self.max_concurrent = max_concurrent
        self._executions: dict[str, WorkflowExecution] = {}
        self._lock = threading.Lock()

    def execute_workflow(
        self,
        workflow_id: str,
        rule_name: str,
        steps: list[WorkflowStep],
        initial_context: dict[str, Any] | None = None,
        parallel: bool = True,
    ) -> WorkflowExecution:
        """Execute a workflow.

        Args:
            workflow_id: Unique workflow execution ID
            rule_name: Name of the automation rule
            steps: List of workflow steps
            initial_context: Initial execution context
            parallel: Whether to execute independent steps in parallel

        Returns:
            WorkflowExecution with final status
        """
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            rule_name=rule_name,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now().isoformat(),
            total_steps=len(steps),
            context=initial_context.copy() if initial_context else {},
        )

        with self._lock:
            self._executions[workflow_id] = execution

        try:
            if parallel:
                self._execute_parallel(execution, steps)
            else:
                self._execute_sequential(execution, steps)

            if execution.status == WorkflowStatus.RUNNING:
                execution.status = WorkflowStatus.COMPLETED

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            logger.error("Workflow %s failed: %s", workflow_id, e, exc_info=True)

        finally:
            execution.completed_at = datetime.now().isoformat()

        return execution

    def _execute_sequential(
        self,
        execution: WorkflowExecution,
        steps: list[WorkflowStep],
    ) -> None:
        """Execute steps sequentially."""
        for i, step in enumerate(steps):
            if execution.status != WorkflowStatus.RUNNING:
                break

            execution.current_step = i + 1

            # Check condition
            if step.condition and not self._evaluate_condition(step.condition, execution.context):
                execution.step_results[step.name] = {
                    "status": "skipped",
                    "reason": "condition_not_met",
                }
                continue

            # Execute step
            result = self._execute_step(step, execution.context)
            execution.step_results[step.name] = result

            # Handle failure
            if not result.get("success", False):
                if step.on_error == "fail":
                    execution.status = WorkflowStatus.FAILED
                    execution.error = result.get("error")
                    break
                elif step.on_error == "continue":
                    continue
                elif step.on_error == "retry":
                    self._retry_step(step, execution)

    def _execute_parallel(
        self,
        execution: WorkflowExecution,
        steps: list[WorkflowStep],
    ) -> None:
        """Execute steps in parallel where possible."""
        resolver = DependencyResolver(steps)
        execution_order = resolver.get_execution_order()

        for group in execution_order:
            if execution.status != WorkflowStatus.RUNNING:
                break

            if len(group) == 1:
                # Single step, execute directly
                step = next(s for s in steps if s.name == group[0])
                self._execute_single_step(step, execution)
            else:
                # Multiple steps, execute in parallel
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(len(group), self.max_concurrent)
                ) as executor:
                    futures = {}
                    for step_name in group:
                        step = next(s for s in steps if s.name == step_name)
                        futures[executor.submit(self._execute_single_step, step, execution)] = (
                            step_name
                        )

                    for future in concurrent.futures.as_completed(futures):
                        step_name = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            logger.error("Step %s failed: %s", step_name, e)
                            execution.step_results[step_name] = {
                                "success": False,
                                "error": str(e),
                            }

    def _execute_single_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
    ) -> None:
        """Execute a single step."""
        execution.current_step += 1

        # Check condition
        if step.condition and not self._evaluate_condition(step.condition, execution.context):
            execution.step_results[step.name] = {
                "status": "skipped",
                "reason": "condition_not_met",
            }
            return

        # Execute with timeout if specified
        result = self._execute_step(step, execution.context)
        execution.step_results[step.name] = result

        # Handle failure
        if not result.get("success", False) and step.on_error == "fail":
            execution.status = WorkflowStatus.FAILED
            execution.error = result.get("error")

    def _execute_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a step and return the result."""
        start_time = time.time()

        try:
            action_config = {
                "type": step.action_type,
                **step.config,
            }

            result = self.action_executor(action_config, context)

            # Handle ActionResult objects
            if hasattr(result, "to_dict"):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {"success": True, "data": result}

            result_dict["duration"] = time.time() - start_time
            return result_dict

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
            }

    def _retry_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
    ) -> None:
        """Retry a failed step based on retry configuration."""
        retry_config = step.retry_config or {}
        max_retries = retry_config.get("max_retries", 3)
        delay = retry_config.get("delay", 1.0)
        backoff = retry_config.get("backoff", 2.0)

        for _attempt in range(max_retries):
            execution.retries += 1
            time.sleep(delay)
            delay *= backoff

            result = self._execute_step(step, execution.context)
            execution.step_results[step.name] = result

            if result.get("success", False):
                return

        # All retries failed
        if step.on_error == "fail":
            execution.status = WorkflowStatus.FAILED
            execution.error = f"Step '{step.name}' failed after {max_retries} retries"

    def _evaluate_condition(
        self,
        condition: str,
        context: dict[str, Any],
    ) -> bool:
        """Evaluate a condition expression."""
        safe_context = {
            "context": context,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "True": True,
            "False": False,
            "None": None,
        }
        safe_context.update(context)

        try:
            return bool(eval(condition, {"__builtins__": {}}, safe_context))
        except Exception as e:
            logger.warning("Condition evaluation failed: %s", e)
            return False

    def get_execution(self, workflow_id: str) -> WorkflowExecution | None:
        """Get a workflow execution by ID."""
        return self._executions.get(workflow_id)

    def cancel_execution(self, workflow_id: str) -> bool:
        """Cancel a running workflow execution."""
        execution = self._executions.get(workflow_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.CANCELLED
            return True
        return False

    def pause_execution(self, workflow_id: str) -> bool:
        """Pause a running workflow execution."""
        execution = self._executions.get(workflow_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.PAUSED
            return True
        return False

    def resume_execution(self, workflow_id: str) -> bool:
        """Resume a paused workflow execution."""
        execution = self._executions.get(workflow_id)
        if execution and execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.RUNNING
            return True
        return False

    def get_active_executions(self) -> list[WorkflowExecution]:
        """Get all active (running/paused) executions."""
        return [
            e
            for e in self._executions.values()
            if e.status in (WorkflowStatus.RUNNING, WorkflowStatus.PAUSED)
        ]


class WorkflowTemplateRegistry:
    """Registry for workflow templates."""

    def __init__(self) -> None:
        self._templates: dict[str, WorkflowTemplate] = {}
        self._lock = threading.Lock()

    def register(self, template: WorkflowTemplate) -> None:
        """Register a workflow template."""
        with self._lock:
            self._templates[template.name] = template
            logger.info("Registered workflow template: %s", template.name)

    def unregister(self, name: str) -> bool:
        """Unregister a workflow template."""
        with self._lock:
            if name in self._templates:
                del self._templates[name]
                return True
            return False

    def get(self, name: str) -> WorkflowTemplate | None:
        """Get a template by name."""
        return self._templates.get(name)

    def list_templates(
        self,
        tags: list[str] | None = None,
    ) -> list[WorkflowTemplate]:
        """List all templates, optionally filtered by tags."""
        templates = list(self._templates.values())
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        return templates

    def instantiate(
        self,
        template_name: str,
        parameters: dict[str, Any] | None = None,
    ) -> tuple[list[WorkflowStep], dict[str, Any]] | None:
        """Instantiate a template with parameters.

        Args:
            template_name: Name of the template
            parameters: Parameter values to substitute

        Returns:
            Tuple of (steps, context) or None if template not found
        """
        template = self.get(template_name)
        if not template:
            return None

        parameters = parameters or {}

        # Validate required parameters
        for param_config in template.parameters:
            param_name = param_config.get("name")
            required = param_config.get("required", False)
            default = param_config.get("default")

            if param_name not in parameters:
                if required and default is None:
                    raise ValueError(f"Missing required parameter: {param_name}")
                if default is not None:
                    parameters[param_name] = default

        # Create steps with parameter substitution
        steps = []
        for step in template.steps:
            new_config = self._substitute_params(step.config, parameters)
            new_step = WorkflowStep(
                name=step.name,
                action_type=step.action_type,
                config=new_config,
                depends_on=step.depends_on.copy(),
                condition=self._substitute_params_str(step.condition, parameters)
                if step.condition
                else None,
                retry_config=step.retry_config.copy() if step.retry_config else None,
                timeout=step.timeout,
                on_error=step.on_error,
            )
            steps.append(new_step)

        # Create context with default values and parameters
        context = copy.deepcopy(template.default_context)
        context.update(parameters)

        return steps, context

    def _substitute_params(
        self,
        value: Any,
        params: dict[str, Any],
    ) -> Any:
        """Recursively substitute parameters in a value."""
        if isinstance(value, str):
            return self._substitute_params_str(value, params)
        if isinstance(value, dict):
            return {k: self._substitute_params(v, params) for k, v in value.items()}
        if isinstance(value, list):
            return [self._substitute_params(v, params) for v in value]
        return value

    def _substitute_params_str(
        self,
        value: str,
        params: dict[str, Any],
    ) -> str:
        """Substitute parameters in a string value."""
        from string import Template

        try:
            return Template(value).safe_substitute(**params)
        except Exception:
            return value

    def import_templates(self, templates_data: list[dict[str, Any]]) -> int:
        """Import templates from a list of dictionaries.

        Returns:
            Number of templates imported
        """
        count = 0
        for data in templates_data:
            try:
                template = WorkflowTemplate.from_dict(data)
                self.register(template)
                count += 1
            except Exception as e:
                logger.error("Failed to import template: %s", e)
        return count

    def export_templates(
        self,
        names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Export templates to a list of dictionaries.

        Args:
            names: Optional list of template names to export (None = all)

        Returns:
            List of template dictionaries
        """
        if names:
            templates = [self._templates[n] for n in names if n in self._templates]
        else:
            templates = list(self._templates.values())

        return [t.to_dict() for t in templates]


# Built-in workflow templates
BUILTIN_TEMPLATES = [
    {
        "name": "http_check_and_notify",
        "description": "Check HTTP endpoint and send notification",
        "steps": [
            {
                "name": "check_endpoint",
                "action_type": "http_request",
                "config": {
                    "method": "GET",
                    "url": "${endpoint_url}",
                    "timeout": 10,
                    "save_as": "response",
                },
            },
            {
                "name": "notify_result",
                "action_type": "send_text",
                "config": {
                    "text": "Endpoint ${endpoint_url} status: ${response.status}",
                },
                "depends_on": ["check_endpoint"],
            },
        ],
        "parameters": [
            {
                "name": "endpoint_url",
                "type": "string",
                "required": True,
                "description": "URL to check",
            },
        ],
        "tags": ["monitoring", "http"],
    },
    {
        "name": "scheduled_report",
        "description": "Fetch data and send formatted report",
        "steps": [
            {
                "name": "fetch_data",
                "action_type": "http_request",
                "config": {
                    "method": "GET",
                    "url": "${data_url}",
                    "save_as": "data",
                },
            },
            {
                "name": "send_report",
                "action_type": "send_template",
                "config": {
                    "template": "${template_name}",
                },
                "depends_on": ["fetch_data"],
            },
        ],
        "parameters": [
            {
                "name": "data_url",
                "type": "string",
                "required": True,
                "description": "URL to fetch data from",
            },
            {
                "name": "template_name",
                "type": "string",
                "required": True,
                "description": "Template to use for report",
            },
        ],
        "tags": ["reporting"],
    },
    {
        "name": "conditional_notification",
        "description": "Send notification based on condition",
        "steps": [
            {
                "name": "check_condition",
                "action_type": "set_variable",
                "config": {
                    "name": "should_notify",
                    "expression": "${condition_expression}",
                },
            },
            {
                "name": "send_notification",
                "action_type": "send_text",
                "config": {
                    "text": "${notification_message}",
                },
                "depends_on": ["check_condition"],
                "condition": "should_notify == True",
            },
        ],
        "parameters": [
            {
                "name": "condition_expression",
                "type": "string",
                "required": True,
                "description": "Condition to evaluate",
            },
            {
                "name": "notification_message",
                "type": "string",
                "required": True,
                "description": "Message to send",
            },
        ],
        "tags": ["notification", "conditional"],
    },
    {
        "name": "data_pipeline",
        "description": "Multi-step data processing pipeline",
        "steps": [
            {
                "name": "fetch_source",
                "action_type": "http_request",
                "config": {
                    "method": "GET",
                    "url": "${source_url}",
                    "save_as": "source_data",
                },
            },
            {
                "name": "transform_data",
                "action_type": "python_code",
                "config": {
                    "code": "${transform_code}",
                    "save_as": "transformed_data",
                },
                "depends_on": ["fetch_source"],
            },
            {
                "name": "send_to_destination",
                "action_type": "http_request",
                "config": {
                    "method": "POST",
                    "url": "${destination_url}",
                    "json_body": "${transformed_data}",
                },
                "depends_on": ["transform_data"],
            },
        ],
        "parameters": [
            {
                "name": "source_url",
                "type": "string",
                "required": True,
                "description": "Source data URL",
            },
            {
                "name": "transform_code",
                "type": "string",
                "required": True,
                "description": "Python code to transform data",
            },
            {
                "name": "destination_url",
                "type": "string",
                "required": True,
                "description": "Destination URL",
            },
        ],
        "tags": ["data", "pipeline", "etl"],
    },
]


def create_default_template_registry() -> WorkflowTemplateRegistry:
    """Create a template registry with built-in templates."""
    registry = WorkflowTemplateRegistry()
    registry.import_templates(BUILTIN_TEMPLATES)
    return registry


__all__ = [
    "WorkflowStatus",
    "DependencyType",
    "WorkflowStep",
    "WorkflowExecution",
    "WorkflowTemplate",
    "DependencyResolver",
    "WorkflowOrchestrator",
    "WorkflowTemplateRegistry",
    "BUILTIN_TEMPLATES",
    "create_default_template_registry",
]
