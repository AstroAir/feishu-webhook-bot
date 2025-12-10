"""Plugin configuration validator.

This module provides tools for validating plugin configurations
against their schemas at startup and runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger

if TYPE_CHECKING:
    from ..core.config import BotConfig
    from .base import BasePlugin

logger = get_logger("plugin.config_validator")


@dataclass
class ValidationResult:
    """Result of validating a plugin's configuration.

    Attributes:
        plugin_name: Name of the plugin validated
        is_valid: Whether the configuration is valid
        errors: List of error messages
        warnings: List of warning messages
        missing_required: Names of missing required fields
        invalid_values: Mapping of field names to error messages
    """

    plugin_name: str
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    invalid_values: dict[str, str] = field(default_factory=dict)


@dataclass
class StartupValidationReport:
    """Complete validation report for all plugins at startup.

    Attributes:
        all_valid: Whether all plugin configurations are valid
        results: List of individual validation results
        plugins_ready: Names of plugins with valid configurations
        plugins_need_config: Names of plugins needing configuration
        suggestions: Actionable suggestions for fixing issues
    """

    all_valid: bool
    results: list[ValidationResult] = field(default_factory=list)
    plugins_ready: list[str] = field(default_factory=list)
    plugins_need_config: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class ConfigValidator:
    """Validates plugin configurations against their schemas.

    This class provides methods for validating individual plugin
    configurations or all plugins at once.

    Example:
        ```python
        validator = ConfigValidator(bot_config)

        # Validate a single plugin
        result = validator.validate_plugin("feishu-calendar")
        if not result.is_valid:
            for error in result.errors:
                print(f"Error: {error}")

        # Generate startup report
        report = validator.generate_startup_report(loaded_plugins)
        if not report.all_valid:
            for suggestion in report.suggestions:
                print(suggestion)
        ```
    """

    def __init__(self, config: BotConfig):
        """Initialize the validator.

        Args:
            config: Bot configuration containing plugin settings
        """
        self.config = config

    def validate_plugin(self, plugin_name: str) -> ValidationResult:
        """Validate a single plugin's configuration.

        Args:
            plugin_name: Name of the plugin to validate

        Returns:
            ValidationResult with validation details
        """
        from .config_registry import ConfigSchemaRegistry

        schema = ConfigSchemaRegistry.get(plugin_name)

        if schema is None:
            # No schema registered - cannot validate, assume valid
            return ValidationResult(
                plugin_name=plugin_name,
                is_valid=True,
                warnings=["Plugin does not define a configuration schema"],
            )

        # Get existing configuration
        existing_config = self.config.plugins.get_plugin_settings(plugin_name)

        # Run schema validation
        is_valid, errors = schema.validate_config(existing_config)

        # Get missing required fields
        missing_fields = schema.get_missing_required(existing_config)
        missing_names = [f.name for f in missing_fields]

        # Build result
        return ValidationResult(
            plugin_name=plugin_name,
            is_valid=is_valid and not missing_names,
            errors=errors,
            warnings=[],
            missing_required=missing_names,
            invalid_values={},
        )

    def validate_all(self) -> list[ValidationResult]:
        """Validate all plugins with registered schemas.

        Returns:
            List of ValidationResult for each registered plugin
        """
        from .config_registry import ConfigSchemaRegistry

        results: list[ValidationResult] = []
        for plugin_name in ConfigSchemaRegistry.get_plugin_names():
            results.append(self.validate_plugin(plugin_name))
        return results

    def validate_plugins(self, plugin_names: list[str]) -> list[ValidationResult]:
        """Validate specific plugins.

        Args:
            plugin_names: List of plugin names to validate

        Returns:
            List of ValidationResult for each specified plugin
        """
        results: list[ValidationResult] = []
        for plugin_name in plugin_names:
            results.append(self.validate_plugin(plugin_name))
        return results

    def generate_startup_report(
        self, plugins: dict[str, BasePlugin]
    ) -> StartupValidationReport:
        """Generate comprehensive validation report at startup.

        This method validates all loaded plugins and generates a report
        with actionable suggestions for fixing configuration issues.

        Args:
            plugins: Dictionary of loaded plugins (name -> instance)

        Returns:
            StartupValidationReport with comprehensive status
        """
        from .config_registry import ConfigSchemaRegistry

        results: list[ValidationResult] = []
        ready: list[str] = []
        need_config: list[str] = []
        suggestions: list[str] = []

        for name, plugin in plugins.items():
            # Auto-register schema if not already registered
            if not ConfigSchemaRegistry.has_schema(name):
                ConfigSchemaRegistry.auto_register(plugin)

            result = self.validate_plugin(name)
            results.append(result)

            if result.is_valid:
                ready.append(name)
            else:
                need_config.append(name)

                # Generate suggestions
                if result.missing_required:
                    field_list = ", ".join(result.missing_required[:3])
                    if len(result.missing_required) > 3:
                        field_list += f" (and {len(result.missing_required) - 3} more)"
                    suggestions.append(
                        f"Plugin '{name}' missing required fields: {field_list}"
                    )
                    suggestions.append(
                        f"  -> Run: feishu-webhook-bot plugin setup {name}"
                    )

        all_valid = not need_config

        return StartupValidationReport(
            all_valid=all_valid,
            results=results,
            plugins_ready=ready,
            plugins_need_config=need_config,
            suggestions=suggestions,
        )

    def print_report(self, report: StartupValidationReport) -> None:
        """Print validation report to console using Rich.

        Args:
            report: Validation report to print
        """
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table

            console = Console()

            if report.all_valid:
                console.print(
                    Panel(
                        f"[green]All {len(report.plugins_ready)} plugin(s) configured correctly[/]",
                        title="Plugin Configuration",
                        border_style="green",
                    )
                )
                return

            # Create results table
            table = Table(title="Plugin Configuration Status")
            table.add_column("Plugin", style="cyan")
            table.add_column("Status")
            table.add_column("Issues")

            for result in report.results:
                if result.is_valid:
                    status = "[green]OK[/]"
                    issues = ""
                else:
                    status = "[red]Invalid[/]"
                    issues_list = []
                    if result.missing_required:
                        issues_list.append(f"Missing: {', '.join(result.missing_required[:2])}")
                    if result.errors:
                        issues_list.append(result.errors[0][:50])
                    issues = "; ".join(issues_list)

                table.add_row(result.plugin_name, status, issues)

            console.print(table)

            # Print suggestions
            if report.suggestions:
                console.print("\n[bold yellow]Suggestions:[/]")
                for suggestion in report.suggestions:
                    console.print(f"  {suggestion}")

        except ImportError:
            # Fallback without Rich
            print("Plugin Configuration Status:")
            print("-" * 40)

            for result in report.results:
                status = "OK" if result.is_valid else "INVALID"
                print(f"  {result.plugin_name}: {status}")
                if not result.is_valid:
                    if result.missing_required:
                        print(f"    Missing: {', '.join(result.missing_required)}")
                    for error in result.errors[:2]:
                        print(f"    Error: {error}")

            if report.suggestions:
                print("\nSuggestions:")
                for suggestion in report.suggestions:
                    print(f"  {suggestion}")

    def get_plugin_config_status(self, plugin_name: str) -> dict[str, Any]:
        """Get detailed configuration status for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Dictionary with configuration status details
        """
        from .config_registry import ConfigSchemaRegistry

        result = self.validate_plugin(plugin_name)
        schema = ConfigSchemaRegistry.get(plugin_name)
        existing_config = self.config.plugins.get_plugin_settings(plugin_name)

        status: dict[str, Any] = {
            "plugin_name": plugin_name,
            "has_schema": schema is not None,
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "missing_required": result.missing_required,
            "current_config": existing_config,
        }

        if schema:
            status["required_fields"] = [f.name for f in schema.get_required_fields()]
            status["optional_fields"] = [f.name for f in schema.get_optional_fields()]

        return status
