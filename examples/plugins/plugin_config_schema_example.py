#!/usr/bin/env python3
"""Plugin Configuration Schema Example.

This example demonstrates the plugin configuration schema system:
- Defining configuration schemas using Pydantic models
- Field types and validation
- Environment variable fallbacks
- Sensitive field handling
- Schema generation and documentation
- Configuration validation
- ConfigSchemaBuilder for programmatic schema creation

The schema system enables type-safe plugin configuration with validation.
"""

from typing import Any

from pydantic import Field

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.plugins.config_schema import (
    ConfigSchemaBuilder,
    FieldType,
    PluginConfigField,
    PluginConfigSchema,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: Basic Configuration Fields
# =============================================================================
def demo_basic_fields() -> None:
    """Demonstrate basic configuration field types."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Configuration Fields")
    print("=" * 60)

    # Define basic fields
    fields = [
        PluginConfigField(
            name="api_key",
            field_type=FieldType.SECRET,
            description="API key for external service",
            required=True,
            sensitive=True,
            env_var="PLUGIN_API_KEY",
        ),
        PluginConfigField(
            name="timeout",
            field_type=FieldType.INT,
            description="Request timeout in seconds",
            required=False,
            default=30,
            min_value=1,
            max_value=300,
        ),
        PluginConfigField(
            name="enabled",
            field_type=FieldType.BOOL,
            description="Enable the plugin",
            required=False,
            default=True,
        ),
        PluginConfigField(
            name="base_url",
            field_type=FieldType.URL,
            description="Base URL for API",
            required=True,
            example="https://api.example.com",
        ),
    ]

    print("Configuration fields:")
    for field in fields:
        print(f"\n  {field.name}:")
        print(f"    Type: {field.field_type.value}")
        print(f"    Required: {field.required}")
        print(f"    Default: {field.default}")
        print(f"    Description: {field.description}")
        if field.env_var:
            print(f"    Env var: {field.env_var}")
        if field.sensitive:
            print("    Sensitive: Yes")


# =============================================================================
# Demo 2: Field Validation
# =============================================================================
def demo_field_validation() -> None:
    """Demonstrate field validation."""
    print("\n" + "=" * 60)
    print("Demo 2: Field Validation")
    print("=" * 60)

    # Integer field with range
    int_field = PluginConfigField(
        name="max_retries",
        field_type=FieldType.INT,
        description="Maximum retry attempts",
        min_value=0,
        max_value=10,
    )

    # Test validation
    test_values = [5, -1, 15, "not_int", None]

    print(f"Field: {int_field.name} (INT, range: 0-10)")
    print("\nValidation results:")
    for value in test_values:
        is_valid, error = int_field.validate_value(value)
        status = "VALID" if is_valid else f"INVALID: {error}"
        print(f"  {value!r}: {status}")

    # String field with pattern
    print("\n--- String field with pattern ---")
    email_field = PluginConfigField(
        name="admin_email",
        field_type=FieldType.EMAIL,
        description="Administrator email",
        pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
    )

    test_emails = ["admin@example.com", "invalid_email", "test@test.co.uk"]
    print(f"Field: {email_field.name} (EMAIL)")
    print("\nValidation results:")
    for email in test_emails:
        is_valid, error = email_field.validate_value(email)
        status = "VALID" if is_valid else f"INVALID: {error}"
        print(f"  {email!r}: {status}")


# =============================================================================
# Demo 3: Choice Fields
# =============================================================================
def demo_choice_fields() -> None:
    """Demonstrate choice/enum fields."""
    print("\n" + "=" * 60)
    print("Demo 3: Choice Fields")
    print("=" * 60)

    # Choice field
    log_level_field = PluginConfigField(
        name="log_level",
        field_type=FieldType.CHOICE,
        description="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    )

    print(f"Field: {log_level_field.name}")
    print(f"Choices: {log_level_field.choices}")
    print(f"Default: {log_level_field.default}")

    # Test validation
    test_values = ["INFO", "DEBUG", "TRACE", "info"]
    print("\nValidation results:")
    for value in test_values:
        is_valid, error = log_level_field.validate_value(value)
        status = "VALID" if is_valid else f"INVALID: {error}"
        print(f"  {value!r}: {status}")


# =============================================================================
# Demo 4: Plugin Configuration Schema (Pydantic Model)
# =============================================================================
def demo_config_schema() -> None:
    """Demonstrate complete plugin configuration schema using Pydantic model."""
    print("\n" + "=" * 60)
    print("Demo 4: Plugin Configuration Schema (Pydantic Model)")
    print("=" * 60)

    # Define schema by subclassing PluginConfigSchema (Pydantic BaseModel)
    class WeatherPluginConfig(PluginConfigSchema):
        """Weather plugin configuration schema."""

        api_key: str = Field(
            ...,
            description="Weather API key",
            json_schema_extra={"sensitive": True, "env_var": "WEATHER_API_KEY"},
        )
        default_city: str = Field(
            default="Beijing",
            description="Default city for weather queries",
        )
        units: str = Field(
            default="celsius",
            description="Temperature units",
            json_schema_extra={"choices": ["celsius", "fahrenheit"]},
        )
        cache_ttl: int = Field(
            default=300,
            description="Cache TTL in seconds",
            ge=60,
            le=3600,
        )

    # Get schema fields
    fields = WeatherPluginConfig.get_schema_fields()
    print("Schema: WeatherPluginConfig")
    print(f"\nFields ({len(fields)}):")
    for name, field_def in fields.items():
        req = "required" if field_def.required else "optional"
        print(f"  - {name} ({field_def.field_type.value}, {req})")

    # Validate a config
    print("\nValidating config:")
    test_config = {"api_key": "test_key", "cache_ttl": 600}
    is_valid, errors = WeatherPluginConfig.validate_config(test_config)
    print(f"  Config: {test_config}")
    print(f"  Valid: {is_valid}")
    if errors:
        print(f"  Errors: {errors}")


# =============================================================================
# Demo 5: Schema Validation
# =============================================================================
def demo_schema_validation() -> None:
    """Demonstrate schema-level validation."""
    print("\n" + "=" * 60)
    print("Demo 5: Schema Validation")
    print("=" * 60)

    # Define schema using Pydantic model
    class TestPluginConfig(PluginConfigSchema):
        """Test plugin configuration."""

        api_key: str = Field(..., description="API key")
        timeout: int = Field(default=30, description="Timeout", ge=1)
        enabled: bool = Field(default=True, description="Enabled")

    # Test configurations
    test_configs = [
        {
            "name": "Valid config",
            "config": {"api_key": "secret123", "timeout": 60, "enabled": True},
        },
        {
            "name": "Missing required field",
            "config": {"timeout": 60},
        },
        {
            "name": "Invalid type",
            "config": {"api_key": "secret", "timeout": "not_int"},
        },
        {
            "name": "Value out of range",
            "config": {"api_key": "secret", "timeout": -5},
        },
    ]

    print("Validating configurations:")
    for test in test_configs:
        print(f"\n  {test['name']}:")
        print(f"    Config: {test['config']}")

        is_valid, errors = TestPluginConfig.validate_config(test["config"])
        if is_valid:
            print("    Result: VALID")
        else:
            print("    Result: INVALID")
            for error in errors:
                print(f"      - {error}")


# =============================================================================
# Demo 6: Environment Variable Fallback
# =============================================================================
def demo_env_var_fallback() -> None:
    """Demonstrate environment variable fallback using PluginConfigField."""
    print("\n" + "=" * 60)
    print("Demo 6: Environment Variable Fallback")
    print("=" * 60)

    import os

    # Set environment variable for demo
    os.environ["DEMO_API_KEY"] = "env_secret_key"
    os.environ["DEMO_TIMEOUT"] = "45"

    # Define fields with env_var support
    fields = [
        PluginConfigField(
            name="api_key",
            field_type=FieldType.STRING,
            description="API key",
            required=True,
            env_var="DEMO_API_KEY",
        ),
        PluginConfigField(
            name="timeout",
            field_type=FieldType.INT,
            description="Timeout",
            env_var="DEMO_TIMEOUT",
            default=30,
        ),
        PluginConfigField(
            name="debug",
            field_type=FieldType.BOOL,
            description="Debug mode",
            env_var="DEMO_DEBUG",
            default=False,
        ),
    ]

    print("Environment variables set:")
    print("  DEMO_API_KEY=env_secret_key")
    print("  DEMO_TIMEOUT=45")
    print("  DEMO_DEBUG=(not set)")

    # Resolve configuration with env fallback
    config: dict[str, Any] = {}
    for field_def in fields:
        if field_def.env_var and field_def.env_var in os.environ:
            env_value = os.environ[field_def.env_var]
            # Convert type if needed
            if field_def.field_type == FieldType.INT:
                config[field_def.name] = int(env_value)
            elif field_def.field_type == FieldType.BOOL:
                config[field_def.name] = env_value.lower() in ("true", "1", "yes")
            else:
                config[field_def.name] = env_value
        elif field_def.default is not None:
            config[field_def.name] = field_def.default

    print("\nResolved configuration:")
    for key, value in config.items():
        # Mask sensitive values
        if key == "api_key":
            print(f"  {key}: {'*' * len(str(value))}")
        else:
            print(f"  {key}: {value}")

    # Cleanup
    del os.environ["DEMO_API_KEY"]
    del os.environ["DEMO_TIMEOUT"]


# =============================================================================
# Demo 7: Sensitive Field Handling
# =============================================================================
def demo_sensitive_fields() -> None:
    """Demonstrate sensitive field handling."""
    print("\n" + "=" * 60)
    print("Demo 7: Sensitive Field Handling")
    print("=" * 60)

    # Define schema with sensitive fields using Pydantic model
    class SecurePluginConfig(PluginConfigSchema):
        """Secure plugin configuration."""

        api_key: str = Field(
            ...,
            description="API key",
            json_schema_extra={"sensitive": True},
        )
        password: str = Field(
            ...,
            description="Database password",
            json_schema_extra={"sensitive": True},
        )
        username: str = Field(
            default="admin",
            description="Username",
        )

    config = {
        "api_key": "super_secret_key_12345",
        "password": "db_password_xyz",
        "username": "admin",
    }

    print("Original configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    # Mask sensitive fields manually
    fields = SecurePluginConfig.get_schema_fields()
    masked = {}
    for key, value in config.items():
        field_def = fields.get(key)
        if field_def and field_def.sensitive:
            masked[key] = "********"
        else:
            masked[key] = value

    print("\nMasked configuration (safe for logging):")
    for key, value in masked.items():
        print(f"  {key}: {value}")


# =============================================================================
# Demo 8: Schema Documentation Generation
# =============================================================================
def demo_schema_documentation() -> None:
    """Demonstrate schema documentation generation."""
    print("\n" + "=" * 60)
    print("Demo 8: Schema Documentation Generation")
    print("=" * 60)

    # Define schema using Pydantic model
    class NotificationPluginConfig(PluginConfigSchema):
        """Send notifications to various channels."""

        webhook_url: str = Field(
            ...,
            description="Webhook URL for notifications",
            json_schema_extra={
                "example": "https://hooks.example.com/notify",
                "help_url": "https://docs.example.com/webhooks",
            },
        )
        channel: str = Field(
            default="feishu",
            description="Notification channel",
            json_schema_extra={"choices": ["email", "slack", "feishu", "telegram"]},
        )
        retry_count: int = Field(
            default=3,
            description="Number of retry attempts",
            ge=0,
            le=10,
        )
        api_key: str = Field(
            ...,
            description="API key for authentication",
            json_schema_extra={"sensitive": True, "env_var": "NOTIFICATION_API_KEY"},
        )

    # Generate documentation manually
    fields = NotificationPluginConfig.get_schema_fields()
    print("\nNotificationPluginConfig Schema Documentation")
    print("=" * 45)
    print(f"Description: {NotificationPluginConfig.__doc__}")
    print("\nFields:")
    for name, field_def in fields.items():
        req = "(required)" if field_def.required else "(optional)"
        print(f"\n  {name} {req}")
        print(f"    Type: {field_def.field_type.value}")
        print(f"    Description: {field_def.description}")
        if field_def.default is not None:
            print(f"    Default: {field_def.default}")
        if field_def.example:
            print(f"    Example: {field_def.example}")
        if field_def.env_var:
            print(f"    Env var: {field_def.env_var}")
        if field_def.sensitive:
            print("    Sensitive: Yes")


# =============================================================================
# Demo 9: Conditional Fields
# =============================================================================
def demo_conditional_fields() -> None:
    """Demonstrate conditional/dependent fields using ConfigSchemaBuilder."""
    print("\n" + "=" * 60)
    print("Demo 9: Conditional Fields")
    print("=" * 60)

    # Use ConfigSchemaBuilder for programmatic schema creation
    builder = ConfigSchemaBuilder()
    builder.add_field(
        name="storage_type",
        field_type=FieldType.CHOICE,
        description="Storage backend type",
        choices=["local", "s3", "gcs"],
        required=True,
    )
    builder.add_field(
        name="local_path",
        field_type=FieldType.PATH,
        description="Local storage path",
        depends_on="storage_type",
        required=False,
    )
    builder.add_field(
        name="s3_bucket",
        field_type=FieldType.STRING,
        description="S3 bucket name",
        depends_on="storage_type",
        required=False,
    )
    builder.add_field(
        name="s3_region",
        field_type=FieldType.STRING,
        description="S3 region",
        depends_on="storage_type",
        default="us-east-1",
        required=False,
    )

    fields = builder.build()

    print("Conditional field configuration:")
    print("\nWhen storage_type = 'local':")
    print("  Required: local_path")
    print("  Not needed: s3_bucket, s3_region")

    print("\nWhen storage_type = 's3':")
    print("  Required: s3_bucket")
    print("  Optional: s3_region (default: us-east-1)")
    print("  Not needed: local_path")

    print("\nFields with dependencies:")
    for name, field_def in fields.items():
        if field_def.depends_on:
            print(f"  {name} -> depends on '{field_def.depends_on}'")

    # Example configurations
    configs = [
        {"storage_type": "local", "local_path": "/data/storage"},
        {"storage_type": "s3", "s3_bucket": "my-bucket", "s3_region": "ap-northeast-1"},
    ]

    print("\nExample configurations:")
    for config in configs:
        print(f"  {config}")


# =============================================================================
# Demo 10: Real-World Plugin Schema
# =============================================================================
def demo_real_world_schema() -> None:
    """Demonstrate a real-world plugin configuration schema."""
    print("\n" + "=" * 60)
    print("Demo 10: Real-World Plugin Schema")
    print("=" * 60)

    # Calendar plugin schema using Pydantic model
    class FeishuCalendarConfig(PluginConfigSchema):
        """Feishu Calendar integration plugin configuration."""

        app_id: str = Field(
            ...,
            description="Feishu App ID",
            json_schema_extra={"env_var": "FEISHU_APP_ID"},
        )
        app_secret: str = Field(
            ...,
            description="Feishu App Secret",
            json_schema_extra={"sensitive": True, "env_var": "FEISHU_APP_SECRET"},
        )
        default_calendar_id: str | None = Field(
            default=None,
            description="Default calendar ID for queries",
        )
        sync_interval: int = Field(
            default=15,
            description="Calendar sync interval in minutes",
            ge=5,
            le=60,
        )
        reminder_before: int = Field(
            default=10,
            description="Send reminder N minutes before event",
            ge=1,
            le=60,
        )
        notification_channel: str = Field(
            default="webhook",
            description="Channel for event notifications",
            json_schema_extra={"choices": ["webhook", "bot", "both"]},
        )
        include_declined: bool = Field(
            default=False,
            description="Include declined events in queries",
        )

    print("Plugin: FeishuCalendarConfig")
    print(f"Description: {FeishuCalendarConfig.__doc__}")

    fields = FeishuCalendarConfig.get_schema_fields()
    print("\nConfiguration fields:")
    for name, field_def in fields.items():
        req = "*" if field_def.required else ""
        default = f" (default: {field_def.default})" if field_def.default is not None else ""
        print(f"  {name}{req}: {field_def.field_type.value}{default}")

    # Validate example config
    print("\nValidating example config:")
    example_config = {
        "app_id": "cli_xxx",
        "app_secret": "secret_xxx",
        "sync_interval": 15,
    }
    is_valid, errors = FeishuCalendarConfig.validate_config(example_config)
    print(f"  Config: {example_config}")
    print(f"  Valid: {is_valid}")

    # Example configuration
    print("\nExample configuration (YAML):")
    print("""
plugins:
  feishu_calendar:
    app_id: "cli_xxx"
    app_secret: "${FEISHU_APP_SECRET}"
    default_calendar_id: "cal_xxx"
    sync_interval: 15
    reminder_before: 10
    notification_channel: "webhook"
    include_declined: false
""")


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all plugin config schema demonstrations."""
    print("=" * 60)
    print("Plugin Configuration Schema Examples")
    print("=" * 60)

    demos = [
        ("Basic Configuration Fields", demo_basic_fields),
        ("Field Validation", demo_field_validation),
        ("Choice Fields", demo_choice_fields),
        ("Plugin Configuration Schema", demo_config_schema),
        ("Schema Validation", demo_schema_validation),
        ("Environment Variable Fallback", demo_env_var_fallback),
        ("Sensitive Field Handling", demo_sensitive_fields),
        ("Schema Documentation Generation", demo_schema_documentation),
        ("Conditional Fields", demo_conditional_fields),
        ("Real-World Plugin Schema", demo_real_world_schema),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\nDemo {i} ({name}) failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
