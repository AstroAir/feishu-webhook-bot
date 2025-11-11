"""Task template utilities for creating tasks from templates."""

from __future__ import annotations

import re
from typing import Any

from ..core.config import (
    TaskDefinitionConfig,
    TaskTemplateConfig,
)
from ..core.logger import get_logger

logger = get_logger("task.templates")


class TaskTemplateEngine:
    """Engine for creating tasks from templates."""

    def __init__(self, templates: list[TaskTemplateConfig]):
        """Initialize template engine.

        Args:
            templates: List of task templates
        """
        self.templates = {t.name: t for t in templates}

    def get_template(self, name: str) -> TaskTemplateConfig | None:
        """Get a template by name.

        Args:
            name: Template name

        Returns:
            Template configuration or None
        """
        return self.templates.get(name)

    def create_task_from_template(
        self,
        template_name: str,
        task_name: str,
        overrides: dict[str, Any] | None = None,
    ) -> TaskDefinitionConfig:
        """Create a task from a template.

        Args:
            template_name: Name of the template to use
            task_name: Name for the new task
            overrides: Dictionary of values to override/substitute in the template

        Returns:
            New task configuration

        Raises:
            ValueError: If template not found or required parameters missing
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        # Validate parameters if overrides provided
        if overrides and template.parameters:
            is_valid, errors = self.validate_template_parameters(template_name, overrides)
            if not is_valid:
                raise ValueError(f"Template validation failed: {', '.join(errors)}")

        # Start with base task configuration
        task_dict = template.base_task.model_dump()

        # Update task name
        task_dict["name"] = task_name

        # Apply parameter defaults
        params = {}
        if template.parameters:
            for param in template.parameters:
                overrides_dict = overrides or {}
                if param.name in overrides_dict:
                    params[param.name] = overrides_dict[param.name]
                elif param.default is not None:
                    params[param.name] = param.default

        # Substitute parameters in task dict
        if params:
            task_dict = self._substitute_parameters(task_dict, params)

        # Apply additional overrides (non-parameter fields)
        if overrides:
            param_names = {p.name for p in (template.parameters or [])}
            non_param_overrides = {k: v for k, v in overrides.items() if k not in param_names}
            if non_param_overrides:
                self._apply_overrides(task_dict, non_param_overrides)

        # Create new task instance
        return TaskDefinitionConfig(**task_dict)

    def _apply_overrides(self, base: dict[str, Any], overrides: dict[str, Any]) -> None:
        """Apply overrides to base configuration recursively.

        Args:
            base: Base configuration dictionary (modified in place)
            overrides: Override values
        """
        for key, value in overrides.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._apply_overrides(base[key], value)
            else:
                base[key] = value

    def _substitute_parameters(self, obj: Any, params: dict[str, Any]) -> Any:
        """Recursively substitute ${param_name} placeholders in configuration.

        Args:
            obj: Configuration object (dict, list, or primitive)
            params: Parameter values to substitute

        Returns:
            Configuration with substituted values
        """
        if isinstance(obj, dict):
            return {k: self._substitute_parameters(v, params) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_parameters(item, params) for item in obj]
        elif isinstance(obj, str):
            # Replace ${param_name} patterns
            def replacer(match: re.Match[str]) -> str:
                param_name = match.group(1)
                if param_name in params:
                    return str(params[param_name])
                return match.group(0)  # Keep original if not found

            return re.sub(r"\$\{([^}]+)\}", replacer, obj)
        else:
            return obj

    def list_templates(self) -> list[str]:
        """List all available template names.

        Returns:
            List of template names
        """
        return list(self.templates.keys())

    def validate_template_parameters(
        self,
        template_name: str,
        parameters: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate parameters against template requirements.

        Args:
            template_name: Template name
            parameters: Parameters to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        template = self.get_template(template_name)
        if not template:
            return False, [f"Template not found: {template_name}"]

        errors = []

        # Check required parameters
        for param in template.parameters:
            if param.required and param.name not in parameters:
                errors.append(f"required parameter missing: {param.name}")

        # Check parameter types
        for param in template.parameters:
            if param.name in parameters:
                value = parameters[param.name]
                expected_type = param.type

                # Basic type checking
                type_map = {
                    "string": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                }

                if expected_type in type_map:
                    expected_python_type = type_map[expected_type]
                    if not isinstance(value, expected_python_type):
                        errors.append(
                            f"Parameter {param.name} has wrong type: "
                            f"expected {expected_type}, got {type(value).__name__}"
                        )

        return len(errors) == 0, errors


def create_task_from_template_yaml(
    template_config: dict[str, Any],
    task_name: str,
    parameters: dict[str, Any] | None = None,
) -> TaskDefinitionConfig:
    """Create a task from a template defined in YAML.

    This is a convenience function for creating tasks from templates
    when working with raw YAML data.

    Args:
        template_config: Template configuration dictionary
        task_name: Name for the new task
        parameters: Parameters to apply to the template

    Returns:
        New task configuration

    Example:
        ```yaml
        task_templates:
          - name: "http_check"
            description: "Template for HTTP health checks"
            base_task:
              name: "template"
              schedule:
                mode: "interval"
                arguments:
                  minutes: 5
              actions:
                - type: "http_request"
                  request:
                    method: "GET"
                    url: "${url}"
                    save_as: "response"
                - type: "send_message"
                  message: "Health check: ${status}"
            parameters:
              - name: "url"
                type: "string"
                required: true
              - name: "status"
                type: "string"
                default: "OK"
        ```

        ```python
        task = create_task_from_template_yaml(
            template_config,
            "api_health_check",
            {"url": "https://api.example.com/health", "status": "Healthy"}
        )
        ```
    """
    template = TaskTemplateConfig(**template_config)
    engine = TaskTemplateEngine([template])
    return engine.create_task_from_template(
        template.name,
        task_name,
        parameters,
    )
