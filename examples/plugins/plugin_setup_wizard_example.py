"""Example usage of the PluginSetupWizard for interactive plugin configuration.

This example demonstrates:
- Creating a configuration schema for a plugin using Pydantic models
- Creating a plugin manifest
- Running the interactive setup wizard
- Handling user input and validation

Note: The PluginSetupWizard expects a PluginConfigSchema subclass (Pydantic model),
not a dictionary schema. This example shows how to properly define schemas.
"""

from pydantic import Field

from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema
from feishu_webhook_bot.plugins.manifest import PluginManifest
from feishu_webhook_bot.plugins.setup_wizard import PluginSetupWizard


def example_basic_setup() -> None:
    """Example: Basic plugin setup wizard using Pydantic schema."""
    print("Example 1: Basic Plugin Setup")
    print("-" * 40)

    # Define schema using Pydantic model
    class ExamplePluginConfig(PluginConfigSchema):
        """Example plugin configuration."""

        api_key: str = Field(
            ...,
            description="Your API key for the service",
            json_schema_extra={"sensitive": True, "example": "sk_live_abc123"},
        )
        api_url: str = Field(
            default="https://api.example.com",
            description="Base URL for the API",
        )
        timeout: int = Field(
            default=30,
            description="Request timeout in seconds",
            ge=1,
            le=300,
        )

    # Create manifest
    manifest = PluginManifest(
        name="Example Plugin",
        version="1.0.0",
        description="A simple example plugin for API integration",
        author="Your Name",
    )

    # Create wizard with Pydantic schema class
    wizard = PluginSetupWizard(
        plugin_name="example-plugin",
        schema=ExamplePluginConfig,
        manifest=manifest,
    )
    config = wizard.run()

    if config:
        print("\nConfiguration saved:")
        for key, value in config.items():
            print(f"  {key}: {value}")
    else:
        print("Setup cancelled.")


def example_grouped_setup() -> None:
    """Example: Plugin setup with grouped fields using Pydantic schema."""
    print("\nExample 2: Grouped Field Setup")
    print("-" * 40)

    # Define schema using Pydantic model with field groups
    class DatabasePluginConfig(PluginConfigSchema):
        """Database plugin configuration."""

        # Authentication fields
        username: str = Field(..., description="Username for authentication")
        password: str = Field(
            ...,
            description="Password for authentication",
            json_schema_extra={"sensitive": True},
        )

        # Connection fields
        host: str = Field(default="localhost", description="Server hostname")
        port: int = Field(default=5432, description="Server port", ge=1, le=65535)
        ssl_enabled: bool = Field(default=True, description="Enable SSL/TLS encryption")

        # Advanced fields
        log_level: str = Field(
            default="INFO",
            description="Logging level",
            json_schema_extra={"choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
        )
        retry_count: int = Field(default=3, description="Number of retry attempts", ge=0, le=10)

        @classmethod
        def get_field_groups(cls) -> dict[str, list[str]]:
            return {
                "Authentication": ["username", "password"],
                "Connection Settings": ["host", "port", "ssl_enabled"],
                "Advanced": ["log_level", "retry_count"],
            }

    # Create manifest
    manifest = PluginManifest(
        name="Database Plugin",
        version="2.0.0",
        description="Connect to remote database servers",
        author="DB Team",
    )

    # Create wizard
    wizard = PluginSetupWizard(
        plugin_name="db-plugin",
        schema=DatabasePluginConfig,
        manifest=manifest,
    )
    config = wizard.run()

    if config:
        print("\nConfiguration saved:")
        for key, value in config.items():
            if "password" in key.lower():
                print(f"  {key}: {'*' * 8}")
            else:
                print(f"  {key}: {value}")
    else:
        print("Setup cancelled.")


def example_with_validation() -> None:
    """Example: Plugin setup with custom validation patterns using Pydantic."""
    print("\nExample 3: Setup with Pattern Validation")
    print("-" * 40)

    # Define schema with pattern validation
    class WebhookPluginConfig(PluginConfigSchema):
        """Webhook plugin configuration."""

        email: str = Field(
            ...,
            description="Contact email address",
            pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
            json_schema_extra={"example": "user@example.com"},
        )
        phone: str | None = Field(
            default=None,
            description="Phone number (optional)",
            pattern=r"^\+?1?\d{9,15}$",
            json_schema_extra={"example": "+1234567890"},
        )
        webhook_url: str = Field(
            ...,
            description="Webhook URL",
            pattern=r"^https?://",
            json_schema_extra={"example": "https://example.com/webhook"},
        )

    manifest = PluginManifest(
        name="Webhook Plugin",
        version="1.0.0",
        description="Send events to webhook endpoints",
        author="Integration Team",
    )

    wizard = PluginSetupWizard(
        plugin_name="webhook-plugin",
        schema=WebhookPluginConfig,
        manifest=manifest,
    )
    config = wizard.run()

    if config:
        print("\nConfiguration saved:")
        for key, value in config.items():
            print(f"  {key}: {value}")
    else:
        print("Setup cancelled.")


def example_with_existing_config() -> None:
    """Example: Setup wizard with pre-populated existing configuration."""
    print("\nExample 4: Edit Existing Configuration")
    print("-" * 40)

    # Define schema
    class UpdatePluginConfig(PluginConfigSchema):
        """Update plugin configuration."""

        api_key: str = Field(
            ...,
            description="API key",
            json_schema_extra={"sensitive": True},
        )
        api_url: str = Field(..., description="API URL")
        enabled: bool = Field(default=True, description="Plugin enabled")

    existing_config = {
        "api_key": "sk_live_existing",
        "api_url": "https://api.existing.com",
        "enabled": True,
    }

    manifest = PluginManifest(
        name="Update Plugin",
        version="1.0.0",
        description="Update configuration for an existing plugin",
    )

    wizard = PluginSetupWizard(
        plugin_name="update-plugin",
        schema=UpdatePluginConfig,
        manifest=manifest,
        existing_config=existing_config,
    )
    config = wizard.run()

    if config:
        print("\nUpdated configuration:")
        for key, value in config.items():
            if "key" in key.lower():
                print(f"  {key}: {'*' * 8}")
            else:
                print(f"  {key}: {value}")
    else:
        print("Update cancelled.")


def example_conditional_fields() -> None:
    """Example: Plugin setup with conditional/dependent fields."""
    print("\nExample 5: Conditional Fields")
    print("-" * 40)

    # Define schema with conditional fields
    class ConditionalPluginConfig(PluginConfigSchema):
        """Plugin with conditional configuration fields."""

        use_auth: bool = Field(default=False, description="Use authentication")
        username: str | None = Field(
            default=None,
            description="Username (only if auth enabled)",
            json_schema_extra={"depends_on": "use_auth"},
        )
        password: str | None = Field(
            default=None,
            description="Password (only if auth enabled)",
            json_schema_extra={"sensitive": True, "depends_on": "use_auth"},
        )
        connection_type: str = Field(
            default="direct",
            description="Connection type",
            json_schema_extra={"choices": ["direct", "proxy", "vpn"]},
        )
        proxy_url: str | None = Field(
            default=None,
            description="Proxy URL (only if proxy selected)",
            json_schema_extra={"depends_on": "connection_type"},
        )

    manifest = PluginManifest(
        name="Conditional Plugin",
        version="1.0.0",
        description="Plugin with conditional configuration fields",
    )

    wizard = PluginSetupWizard(
        plugin_name="conditional-plugin",
        schema=ConditionalPluginConfig,
        manifest=manifest,
    )
    config = wizard.run()

    if config:
        print("\nConfiguration saved:")
        for key, value in config.items():
            print(f"  {key}: {value}")
    else:
        print("Setup cancelled.")


if __name__ == "__main__":
    print("PluginSetupWizard Examples")
    print("=" * 40)
    print("\nNote: These examples are designed for interactive use.")
    print("Uncomment the examples you want to run.\n")

    # Uncomment to run examples:
    # example_basic_setup()
    # example_grouped_setup()
    # example_with_validation()
    # example_with_existing_config()
    # example_conditional_fields()

    print("\nTo use these examples interactively:")
    print("1. Import PluginSetupWizard from feishu_webhook_bot.plugins.setup_wizard")
    print("2. Define your schema and manifest dictionaries")
    print("3. Create a PluginSetupWizard instance")
    print("4. Call the run() method to start the interactive wizard")
    print("5. The wizard returns a dict with the collected configuration")
