#!/usr/bin/env python3
"""Plugin Configuration Schema Example.

This example demonstrates the plugin configuration schema system:
- Defining configuration schemas
- Field types and validation
- Environment variable fallbacks
- Sensitive field handling
- Schema generation and documentation
- Configuration validation

The schema system enables type-safe plugin configuration with validation.
"""

from typing import Any

from feishu_webhook_bot.core import LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.plugins.config_schema import (
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
            print(f"    Sensitive: Yes")


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
# Demo 4: Plugin Configuration Schema
# =============================================================================
def demo_config_schema() -> None:
    """Demonstrate complete plugin configuration schema."""
    print("\n" + "=" * 60)
    print("Demo 4: Plugin Configuration Schema")
    print("=" * 60)

    # Define schema
    schema = PluginConfigSchema(
        name="weather_plugin",
        version="1.0.0",
        description="Weather information plugin",
        fields=[
            PluginConfigField(
                name="api_key",
                field_type=FieldType.SECRET,
                description="Weather API key",
                required=True,
                sensitive=True,
                env_var="WEATHER_API_KEY",
            ),
            PluginConfigField(
                name="default_city",
                field_type=FieldType.STRING,
                description="Default city for weather queries",
                required=False,
                default="Beijing",
            ),
            PluginConfigField(
                name="units",
                field_type=FieldType.CHOICE,
                description="Temperature units",
                choices=["celsius", "fahrenheit"],
                default="celsius",
            ),
            PluginConfigField(
                name="cache_ttl",
                field_type=FieldType.INT,
                description="Cache TTL in seconds",
                default=300,
                min_value=60,
                max_value=3600,
            ),
        ],
    )

    print(f"Schema: {schema.name} v{schema.version}")
    print(f"Description: {schema.description}")
    print(f"\nFields ({len(schema.fields)}):")
    for field in schema.fields:
        req = "required" if field.required else "optional"
        print(f"  - {field.name} ({field.field_type.value}, {req})")


# =============================================================================
# Demo 5: Schema Validation
# =============================================================================
def demo_schema_validation() -> None:
    """Demonstrate schema-level validation."""
    print("\n" + "=" * 60)
    print("Demo 5: Schema Validation")
    print("=" * 60)

    schema = PluginConfigSchema(
        name="test_plugin",
        version="1.0.0",
        fields=[
            PluginConfigField(
                name="api_key",
                field_type=FieldType.STRING,
                description="API key",
                required=True,
            ),
            PluginConfigField(
                name="timeout",
                field_type=FieldType.INT,
                description="Timeout",
                default=30,
                min_value=1,
            ),
            PluginConfigField(
                name="enabled",
                field_type=FieldType.BOOL,
                description="Enabled",
                default=True,
            ),
        ],
    )

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

        is_valid, errors = schema.validate(test["config"])
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
    """Demonstrate environment variable fallback."""
    print("\n" + "=" * 60)
    print("Demo 6: Environment Variable Fallback")
    print("=" * 60)

    import os

    # Set environment variable for demo
    os.environ["DEMO_API_KEY"] = "env_secret_key"
    os.environ["DEMO_TIMEOUT"] = "45"

    schema = PluginConfigSchema(
        name="env_demo",
        version="1.0.0",
        fields=[
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
        ],
    )

    print("Environment variables set:")
    print("  DEMO_API_KEY=env_secret_key")
    print("  DEMO_TIMEOUT=45")
    print("  DEMO_DEBUG=(not set)")

    # Resolve configuration with env fallback
    config: dict[str, Any] = {}
    resolved = schema.resolve_with_env(config)

    print("\nResolved configuration:")
    for key, value in resolved.items():
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

    schema = PluginConfigSchema(
        name="secure_plugin",
        version="1.0.0",
        fields=[
            PluginConfigField(
                name="api_key",
                field_type=FieldType.SECRET,
                description="API key",
                sensitive=True,
            ),
            PluginConfigField(
                name="password",
                field_type=FieldType.SECRET,
                description="Database password",
                sensitive=True,
            ),
            PluginConfigField(
                name="username",
                field_type=FieldType.STRING,
                description="Username",
                sensitive=False,
            ),
        ],
    )

    config = {
        "api_key": "super_secret_key_12345",
        "password": "db_password_xyz",
        "username": "admin",
    }

    print("Original configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    # Mask sensitive fields
    masked = schema.mask_sensitive(config)

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

    schema = PluginConfigSchema(
        name="notification_plugin",
        version="2.0.0",
        description="Send notifications to various channels",
        fields=[
            PluginConfigField(
                name="webhook_url",
                field_type=FieldType.URL,
                description="Webhook URL for notifications",
                required=True,
                example="https://hooks.example.com/notify",
                help_url="https://docs.example.com/webhooks",
            ),
            PluginConfigField(
                name="channel",
                field_type=FieldType.CHOICE,
                description="Notification channel",
                choices=["email", "slack", "feishu", "telegram"],
                default="feishu",
            ),
            PluginConfigField(
                name="retry_count",
                field_type=FieldType.INT,
                description="Number of retry attempts",
                default=3,
                min_value=0,
                max_value=10,
            ),
            PluginConfigField(
                name="api_key",
                field_type=FieldType.SECRET,
                description="API key for authentication",
                required=True,
                sensitive=True,
                env_var="NOTIFICATION_API_KEY",
            ),
        ],
    )

    # Generate documentation
    doc = schema.generate_documentation()
    print(doc)


# =============================================================================
# Demo 9: Conditional Fields
# =============================================================================
def demo_conditional_fields() -> None:
    """Demonstrate conditional/dependent fields."""
    print("\n" + "=" * 60)
    print("Demo 9: Conditional Fields")
    print("=" * 60)

    schema = PluginConfigSchema(
        name="storage_plugin",
        version="1.0.0",
        fields=[
            PluginConfigField(
                name="storage_type",
                field_type=FieldType.CHOICE,
                description="Storage backend type",
                choices=["local", "s3", "gcs"],
                required=True,
            ),
            PluginConfigField(
                name="local_path",
                field_type=FieldType.PATH,
                description="Local storage path",
                depends_on="storage_type",  # Only needed if storage_type is "local"
            ),
            PluginConfigField(
                name="s3_bucket",
                field_type=FieldType.STRING,
                description="S3 bucket name",
                depends_on="storage_type",  # Only needed if storage_type is "s3"
            ),
            PluginConfigField(
                name="s3_region",
                field_type=FieldType.STRING,
                description="S3 region",
                depends_on="storage_type",
                default="us-east-1",
            ),
        ],
    )

    print("Conditional field configuration:")
    print("\nWhen storage_type = 'local':")
    print("  Required: local_path")
    print("  Not needed: s3_bucket, s3_region")

    print("\nWhen storage_type = 's3':")
    print("  Required: s3_bucket")
    print("  Optional: s3_region (default: us-east-1)")
    print("  Not needed: local_path")

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

    # Calendar plugin schema
    calendar_schema = PluginConfigSchema(
        name="feishu_calendar",
        version="1.0.0",
        description="Feishu Calendar integration plugin",
        fields=[
            PluginConfigField(
                name="app_id",
                field_type=FieldType.STRING,
                description="Feishu App ID",
                required=True,
                env_var="FEISHU_APP_ID",
            ),
            PluginConfigField(
                name="app_secret",
                field_type=FieldType.SECRET,
                description="Feishu App Secret",
                required=True,
                sensitive=True,
                env_var="FEISHU_APP_SECRET",
            ),
            PluginConfigField(
                name="default_calendar_id",
                field_type=FieldType.STRING,
                description="Default calendar ID for queries",
                required=False,
            ),
            PluginConfigField(
                name="sync_interval",
                field_type=FieldType.INT,
                description="Calendar sync interval in minutes",
                default=15,
                min_value=5,
                max_value=60,
            ),
            PluginConfigField(
                name="reminder_before",
                field_type=FieldType.INT,
                description="Send reminder N minutes before event",
                default=10,
                min_value=1,
                max_value=60,
            ),
            PluginConfigField(
                name="notification_channel",
                field_type=FieldType.CHOICE,
                description="Channel for event notifications",
                choices=["webhook", "bot", "both"],
                default="webhook",
            ),
            PluginConfigField(
                name="include_declined",
                field_type=FieldType.BOOL,
                description="Include declined events in queries",
                default=False,
            ),
        ],
    )

    print(f"Plugin: {calendar_schema.name}")
    print(f"Version: {calendar_schema.version}")
    print(f"Description: {calendar_schema.description}")

    print("\nConfiguration fields:")
    for field in calendar_schema.fields:
        req = "*" if field.required else ""
        default = f" (default: {field.default})" if field.default is not None else ""
        print(f"  {field.name}{req}: {field.field_type.value}{default}")

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
