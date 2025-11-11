"""Configuration validation utilities and JSON schema generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .config import BotConfig
from .logger import get_logger

logger = get_logger("validation")


def generate_json_schema(output_path: str | Path | None = None) -> dict[str, Any]:
    """Generate JSON schema for BotConfig.

    Args:
        output_path: Optional path to save the schema to

    Returns:
        JSON schema dictionary

    Example:
        ```python
        schema = generate_json_schema("config-schema.json")
        ```
    """
    schema = BotConfig.model_json_schema()

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        logger.info(f"JSON schema saved to {output_file}")

    return schema


def validate_yaml_config(config_path: str | Path) -> tuple[bool, list[str]]:
    """Validate a YAML configuration file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Tuple of (is_valid, list_of_errors)

    Example:
        ```python
        is_valid, errors = validate_yaml_config("config.yaml")
        if not is_valid:
            for error in errors:
                print(f"Error: {error}")
        ```
    """
    errors = []
    config_file = Path(config_path)

    # Check if file exists
    if not config_file.exists():
        return False, [f"Configuration file not found: {config_path}"]

    # Try to parse YAML
    try:
        with open(config_file, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, [f"Invalid YAML syntax: {e}"]

    # Try to validate with Pydantic
    try:
        BotConfig(**yaml_data)
        return True, []
    except ValidationError as e:
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"{loc}: {msg}")
        return False, errors
    except Exception as e:
        return False, [f"Validation error: {e}"]


def validate_config_dict(config_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a configuration dictionary.

    Args:
        config_data: Configuration dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)

    Example:
        ```python
        config_dict = {"webhooks": [...], "scheduler": {...}}
        is_valid, errors = validate_config_dict(config_dict)
        ```
    """
    try:
        BotConfig(**config_data)
        return True, []
    except ValidationError as e:
        errors = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"{loc}: {msg}")
        return False, errors
    except Exception as e:
        return False, [f"Validation error: {e}"]


def get_config_template() -> dict[str, Any]:
    """Get a template configuration with all available options.

    Returns:
        Template configuration dictionary

    Example:
        ```python
        template = get_config_template()
        with open("config-template.yaml", "w") as f:
            yaml.dump(template, f)
        ```
    """
    # Create a default config and convert to dict
    config = BotConfig()
    return config.to_dict()


def check_config_completeness(config_path: str | Path) -> dict[str, Any]:
    """Check configuration completeness and suggest missing sections.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Dictionary with completeness information

    Example:
        ```python
        info = check_config_completeness("config.yaml")
        print(f"Completeness: {info['completeness_percentage']}%")
        for section in info['missing_sections']:
            print(f"Missing: {section}")
        ```
    """
    result: dict[str, Any] = {
        "is_valid": False,
        "completeness_percentage": 0,
        "configured_fields": [],
        "configured_sections": [],
        "missing_optional_fields": [],
        "missing_sections": [],
        "optional_sections": [],
        "warnings": [],
    }

    # Validate first
    is_valid, errors = validate_yaml_config(config_path)
    result["is_valid"] = is_valid

    if not is_valid:
        result["warnings"] = errors
        return result

    # Load config
    try:
        config = BotConfig.from_yaml(config_path)
    except Exception as e:
        result["warnings"] = [f"Failed to load config: {e}"]
        return result

    # Check sections
    all_sections = [
        "webhooks",
        "scheduler",
        "plugins",
        "logging",
        "general",
        "templates",
        "notifications",
        "http",
        "automations",
        "event_server",
        "auth",
        "tasks",
        "task_templates",
        "environments",
    ]

    required_sections = ["webhooks", "scheduler", "plugins", "logging"]
    optional_sections = [s for s in all_sections if s not in required_sections]

    config_dict = config.to_dict()

    for section in all_sections:
        if section in config_dict:
            value = config_dict[section]
            # Check if section has meaningful content
            if (
                isinstance(value, list)
                and len(value) > 0
                or isinstance(value, dict)
                and any(v is not None and v != {} and v != [] for v in value.values())
                or value is not None
                and value != {}
                and value != []
            ):
                result["configured_sections"].append(section)
                result["configured_fields"].append(section)

    # Determine missing sections
    for section in required_sections:
        if section not in result["configured_sections"]:
            result["missing_sections"].append(section)

    for section in optional_sections:
        if section not in result["configured_sections"]:
            result["optional_sections"].append(section)
            result["missing_optional_fields"].append(section)

    # Calculate completeness
    total_sections = len(all_sections)
    configured_count = len(result["configured_sections"])
    result["completeness_percentage"] = int((configured_count / total_sections) * 100)

    # Add warnings
    if not config.webhooks or config.webhooks[0].url.endswith("YOUR_WEBHOOK_URL"):
        result["warnings"].append("Webhook URL not configured (still using placeholder)")

    if config.active_environment and not config.environments:
        result["warnings"].append(
            f"Active environment '{config.active_environment}' set but no environments defined"
        )

    return result


def suggest_config_improvements(config_path: str | Path) -> list[str]:
    """Suggest improvements for a configuration file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        List of suggestions

    Example:
        ```python
        suggestions = suggest_config_improvements("config.yaml")
        for suggestion in suggestions:
            print(f"💡 {suggestion}")
        ```
    """
    suggestions = []

    try:
        config = BotConfig.from_yaml(config_path)
    except Exception as e:
        return [f"Cannot load config: {e}"]

    # Check scheduler
    if not config.scheduler.enabled:
        suggestions.append(
            "Scheduler is disabled - enable it to use scheduled tasks and automations"
        )

    # Check plugins
    if not config.plugins.enabled:
        suggestions.append("Plugin system is disabled - enable it to use plugins")
    elif not config.plugins.auto_reload:
        suggestions.append("Plugin auto-reload is disabled - enable it for development")

    # Check logging
    if config.logging.level == "DEBUG":
        suggestions.append("Logging level is DEBUG - consider using INFO or WARNING for production")
    if not config.logging.log_file:
        suggestions.append("No log file configured - logs will only go to console")

    # Check tasks and automations
    if not config.tasks and not config.automations:
        suggestions.append(
            "No tasks or automations configured - add some to automate your workflows"
        )

    # Check templates
    if (config.tasks or config.automations) and not config.templates:
        suggestions.append("Consider defining message templates for reusable content")

    # Check environments
    if not config.environments:
        suggestions.append(
            "No environments configured - consider setting up dev/staging/production profiles"
        )

    # Check hot reload
    if not config.config_hot_reload:
        suggestions.append(
            "Config hot-reload is disabled - enable it to reload configuration without restart"
        )

    return suggestions
