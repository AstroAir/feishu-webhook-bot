"""Interactive plugin configuration wizard.

This module provides an interactive CLI wizard for configuring plugins,
guiding users through the configuration process with validation and help.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core.logger import get_logger

if TYPE_CHECKING:
    from .config_schema import PluginConfigField, PluginConfigSchema
    from .manifest import PluginManifest

logger = get_logger("plugin.setup_wizard")


class PluginSetupWizard:
    """Interactive wizard for configuring plugins.

    Provides a user-friendly CLI interface for:
    - Displaying plugin information
    - Collecting configuration values
    - Validating inputs
    - Showing configuration summary

    Example:
        ```python
        wizard = PluginSetupWizard(
            plugin_name="my-plugin",
            schema=MyPluginConfigSchema,
            manifest=plugin_manifest,
            existing_config={"timeout": 30},
        )

        new_config = wizard.run()
        if new_config:
            # User completed configuration
            updater.update_plugin_settings("my-plugin", new_config)
        else:
            # User cancelled
            print("Setup cancelled")
        ```
    """

    def __init__(
        self,
        plugin_name: str,
        schema: type[PluginConfigSchema],
        manifest: PluginManifest | None = None,
        existing_config: dict[str, Any] | None = None,
    ):
        """Initialize the setup wizard.

        Args:
            plugin_name: Name of the plugin being configured
            schema: Plugin configuration schema class
            manifest: Optional plugin manifest for additional info
            existing_config: Existing configuration values to pre-fill
        """
        self.plugin_name = plugin_name
        self.schema = schema
        self.manifest = manifest
        self.existing_config = existing_config or {}
        self.new_config: dict[str, Any] = {}

        # Import Rich components
        try:
            from rich.console import Console

            self.console = Console()
            self._has_rich = True
        except ImportError:
            self.console = None
            self._has_rich = False

    def run(self) -> dict[str, Any]:
        """Run the interactive setup wizard.

        Returns:
            The collected configuration dictionary, or empty dict if cancelled
        """
        try:
            self._show_header()

            if self.manifest:
                self._show_plugin_info()
                if not self._check_dependencies() and not self._confirm(
                    "Continue anyway?", default=False
                ):
                    return {}
                self._show_permissions()

            self._collect_configuration()
            self._show_summary()

            if self._confirm("Save this configuration?", default=True):
                return self.new_config
            return {}

        except KeyboardInterrupt:
            self._print("\n\nSetup cancelled.")
            return {}

    def _show_header(self) -> None:
        """Display wizard header with plugin name."""
        if self._has_rich:
            from rich.panel import Panel

            self.console.print(
                Panel(
                    f"[bold cyan]Plugin Configuration Wizard[/]\n"
                    f"Configuring: [bold]{self.plugin_name}[/]",
                    title="Setup",
                    border_style="blue",
                )
            )
        else:
            print("=" * 50)
            print("Plugin Configuration Wizard")
            print(f"Configuring: {self.plugin_name}")
            print("=" * 50)

    def _show_plugin_info(self) -> None:
        """Display plugin information from manifest."""
        if not self.manifest:
            return

        self._print("")
        self._print(f"[bold]Description:[/] {self.manifest.description}")
        self._print(f"[bold]Version:[/] {self.manifest.version}")
        self._print(f"[bold]Author:[/] {self.manifest.author}")

        if self.manifest.homepage:
            self._print(f"[bold]Homepage:[/] {self.manifest.homepage}")

    def _check_dependencies(self) -> bool:
        """Check and display dependency status.

        Returns:
            True if all required dependencies are satisfied
        """
        if not self.manifest or not self.manifest.python_dependencies:
            return True

        from .dependency_checker import DependencyChecker

        checker = DependencyChecker({})
        all_satisfied = True

        self._print("\n[bold]Python Dependencies:[/]")

        if self._has_rich:
            from rich.table import Table

            table = Table()
            table.add_column("Package")
            table.add_column("Required")
            table.add_column("Status")

            for dep in self.manifest.python_dependencies:
                status = checker.check_python_dependency(dep)
                if status.satisfied:
                    status_text = "[green]Installed[/]"
                else:
                    status_text = "[red]Missing[/]"
                    if not dep.optional:
                        all_satisfied = False

                table.add_row(dep.name, dep.version or "any", status_text)

            self.console.print(table)
        else:
            for dep in self.manifest.python_dependencies:
                status = checker.check_python_dependency(dep)
                status_text = "Installed" if status.satisfied else "MISSING"
                print(f"  {dep.name} ({dep.version or 'any'}): {status_text}")
                if not status.satisfied and not dep.optional:
                    all_satisfied = False

        if not all_satisfied:
            self._print("\n[yellow]Some required dependencies are missing.[/]")
            if self.manifest.get_pip_install_command():
                self._print(f"Install with: {self.manifest.get_pip_install_command()}")

        return all_satisfied

    def _show_permissions(self) -> None:
        """Display permission requests."""
        if not self.manifest or not self.manifest.permissions:
            return

        self._print("\n[bold yellow]Requested Permissions:[/]")
        for perm in self.manifest.permissions:
            self._print(f"  - [bold]{perm.permission.value}[/]: {perm.reason}")
            if perm.scope:
                self._print(f"    Scope: {perm.scope}")

    def _collect_configuration(self) -> None:
        """Collect configuration values interactively."""
        fields = self.schema.get_schema_fields()
        groups = self.schema.get_field_groups()

        for group_name, field_names in groups.items():
            self._print(f"\n[bold underline]{group_name}[/]")

            for field_name in field_names:
                if field_name not in fields:
                    continue

                field_def = fields[field_name]

                # Check field dependencies
                if field_def.depends_on and not self.new_config.get(field_def.depends_on):
                    continue

                value = self._prompt_field(field_def)
                if value is not None:
                    self.new_config[field_name] = value

    def _prompt_field(self, field_def: PluginConfigField) -> Any:
        """Prompt user for a single field value.

        Args:
            field_def: Field definition

        Returns:
            The entered value, or None if skipped
        """
        from .config_schema import FieldType

        # Get current/default value
        current = self.existing_config.get(field_def.name, field_def.default)

        # Show field info
        if field_def.example:
            self._print(f"    [dim]Example: {field_def.example}[/]")
        if field_def.help_url:
            self._print(f"    [dim]Help: {field_def.help_url}[/]")

        # Build prompt text
        prompt_text = f"  {field_def.name}"
        if field_def.description:
            prompt_text += f" ({field_def.description})"

        # Handle different field types
        if field_def.field_type == FieldType.BOOL:
            return self._confirm(prompt_text, default=current if current is not None else False)

        if field_def.field_type == FieldType.CHOICE and field_def.choices:
            self._print(f"    Options: {', '.join(str(c) for c in field_def.choices)}")
            while True:
                value = self._prompt(prompt_text, default=str(current) if current else None)
                if value in [str(c) for c in field_def.choices]:
                    return value
                self._print("[red]Invalid choice. Please select from the options above.[/]")

        if field_def.field_type == FieldType.SECRET:
            # Show hint about existing value
            if current:
                prompt_text += " [leave blank to keep existing]"

            value = self._prompt(prompt_text, password=True)
            if not value and current:
                return current
            return value

        if field_def.field_type == FieldType.INT:
            while True:
                value = self._prompt(
                    prompt_text, default=str(current) if current is not None else None
                )
                try:
                    int_value = int(value) if value else None
                    if int_value is not None:
                        is_valid, error = field_def.validate_value(int_value)
                        if is_valid:
                            return int_value
                        self._print(f"[red]{error}[/]")
                    elif not field_def.required:
                        return field_def.default
                    else:
                        self._print("[red]This field is required.[/]")
                except ValueError:
                    self._print("[red]Please enter a valid integer.[/]")

        if field_def.field_type == FieldType.FLOAT:
            while True:
                value = self._prompt(
                    prompt_text, default=str(current) if current is not None else None
                )
                try:
                    float_value = float(value) if value else None
                    if float_value is not None:
                        is_valid, error = field_def.validate_value(float_value)
                        if is_valid:
                            return float_value
                        self._print(f"[red]{error}[/]")
                    elif not field_def.required:
                        return field_def.default
                    else:
                        self._print("[red]This field is required.[/]")
                except ValueError:
                    self._print("[red]Please enter a valid number.[/]")

        if field_def.field_type == FieldType.LIST:
            self._print("    [dim]Enter values separated by commas[/]")
            default_str = ",".join(str(v) for v in current) if current else ""
            value = self._prompt(prompt_text, default=default_str)
            if value:
                return [v.strip() for v in value.split(",") if v.strip()]
            return [] if not field_def.required else None

        # Default: string prompt
        while True:
            value = self._prompt(prompt_text, default=str(current) if current is not None else None)

            if not value:
                if field_def.required:
                    self._print("[red]This field is required.[/]")
                    continue
                return field_def.default

            is_valid, error = field_def.validate_value(value)
            if is_valid:
                return value
            self._print(f"[red]{error}[/]")

    def _show_summary(self) -> None:
        """Display configuration summary."""
        self._print("\n[bold]Configuration Summary:[/]")

        fields = self.schema.get_schema_fields()

        if self._has_rich:
            from rich.table import Table

            table = Table()
            table.add_column("Setting")
            table.add_column("Value")

            for name, value in self.new_config.items():
                field_def = fields.get(name)
                display_value = "********" if field_def and field_def.sensitive else str(value)
                table.add_row(name, display_value)

            self.console.print(table)
        else:
            for name, value in self.new_config.items():
                field_def = fields.get(name)
                display_value = "********" if field_def and field_def.sensitive else str(value)
                print(f"  {name}: {display_value}")

    def _print(self, message: str) -> None:
        """Print a message to the console.

        Args:
            message: Message to print (may contain Rich markup)
        """
        if self._has_rich:
            self.console.print(message)
        else:
            # Strip Rich markup for plain output
            import re

            plain = re.sub(r"\[/?[^\]]+\]", "", message)
            print(plain)

    def _prompt(self, message: str, default: str | None = None, password: bool = False) -> str:
        """Prompt user for input.

        Args:
            message: Prompt message
            default: Default value
            password: Whether to hide input

        Returns:
            User input string
        """
        if self._has_rich:
            from rich.prompt import Prompt

            return Prompt.ask(message, default=default, password=password) or ""
        else:
            if password:
                import getpass

                return getpass.getpass(f"{message}: ")
            else:
                prompt_str = f"{message}"
                if default:
                    prompt_str += f" [{default}]"
                prompt_str += ": "
                value = input(prompt_str)
                return value if value else (default or "")

    def _confirm(self, message: str, default: bool = True) -> bool:
        """Ask for confirmation.

        Args:
            message: Confirmation message
            default: Default value

        Returns:
            User's confirmation
        """
        if self._has_rich:
            from rich.prompt import Confirm

            return Confirm.ask(message, default=default)
        else:
            default_str = "Y/n" if default else "y/N"
            response = input(f"{message} [{default_str}]: ").strip().lower()
            if not response:
                return default
            return response in ("y", "yes")


def run_setup_wizard(
    plugin_name: str,
    schema: type[PluginConfigSchema],
    manifest: PluginManifest | None = None,
    existing_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience function to run the setup wizard.

    Args:
        plugin_name: Name of the plugin
        schema: Configuration schema class
        manifest: Optional plugin manifest
        existing_config: Existing configuration values

    Returns:
        New configuration dictionary, or empty dict if cancelled
    """
    wizard = PluginSetupWizard(
        plugin_name=plugin_name,
        schema=schema,
        manifest=manifest,
        existing_config=existing_config,
    )
    return wizard.run()
