"""Example usage of the PluginSetupWizard for interactive plugin configuration.

This example demonstrates:
- Creating a configuration schema for a plugin
- Creating a plugin manifest
- Running the interactive setup wizard
- Handling user input and validation
"""

from feishu_webhook_bot.plugins.setup_wizard import PluginSetupWizard


def example_basic_setup() -> None:
    """Example: Basic plugin setup wizard."""
    print("Example 1: Basic Plugin Setup")
    print("-" * 40)

    schema = {
        "fields": [
            {
                "name": "api_key",
                "type": "SECRET",
                "description": "Your API key for the service",
                "required": True,
                "example": "sk_live_abc123",
            },
            {
                "name": "api_url",
                "type": "STRING",
                "description": "Base URL for the API",
                "default": "https://api.example.com",
                "required": True,
            },
            {
                "name": "timeout",
                "type": "INT",
                "description": "Request timeout in seconds",
                "default": 30,
                "minimum": 1,
                "maximum": 300,
            },
        ]
    }

    manifest = {
        "name": "Example Plugin",
        "version": "1.0.0",
        "description": "A simple example plugin for API integration",
        "author": "Your Name",
        "dependencies": [],
    }

    wizard = PluginSetupWizard("example-plugin", schema, manifest)
    config = wizard.run()

    if config:
        print("\nConfiguration saved:")
        for key, value in config.items():
            print(f"  {key}: {value}")
    else:
        print("Setup cancelled.")


def example_grouped_setup() -> None:
    """Example: Plugin setup with grouped fields."""
    print("\nExample 2: Grouped Field Setup")
    print("-" * 40)

    schema = {
        "groups": [
            {
                "name": "Authentication",
                "fields": ["username", "password"],
            },
            {
                "name": "Connection Settings",
                "fields": ["host", "port", "ssl_enabled"],
            },
            {
                "name": "Advanced",
                "fields": ["log_level", "retry_count"],
            },
        ],
        "fields": [
            {
                "name": "username",
                "type": "STRING",
                "description": "Username for authentication",
                "required": True,
            },
            {
                "name": "password",
                "type": "SECRET",
                "description": "Password for authentication",
                "required": True,
            },
            {
                "name": "host",
                "type": "STRING",
                "description": "Server hostname",
                "default": "localhost",
                "required": True,
            },
            {
                "name": "port",
                "type": "INT",
                "description": "Server port",
                "default": 5432,
                "minimum": 1,
                "maximum": 65535,
            },
            {
                "name": "ssl_enabled",
                "type": "BOOL",
                "description": "Enable SSL/TLS encryption",
                "default": True,
            },
            {
                "name": "log_level",
                "type": "CHOICE",
                "description": "Logging level",
                "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "default": "INFO",
            },
            {
                "name": "retry_count",
                "type": "INT",
                "description": "Number of retry attempts",
                "default": 3,
                "minimum": 0,
                "maximum": 10,
            },
        ],
    }

    manifest = {
        "name": "Database Plugin",
        "version": "2.0.0",
        "description": "Connect to remote database servers",
        "author": "DB Team",
        "dependencies": ["psycopg2-binary"],
        "permissions": [
            {"name": "database_access", "description": "Access database"},
            {"name": "create_tables", "description": "Create and modify tables"},
        ],
    }

    wizard = PluginSetupWizard("db-plugin", schema, manifest)
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
    """Example: Plugin setup with custom validation patterns."""
    print("\nExample 3: Setup with Pattern Validation")
    print("-" * 40)

    schema = {
        "fields": [
            {
                "name": "email",
                "type": "STRING",
                "description": "Contact email address",
                "required": True,
                "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$",
                "example": "user@example.com",
            },
            {
                "name": "phone",
                "type": "STRING",
                "description": "Phone number (optional)",
                "required": False,
                "pattern": r"^\+?1?\d{9,15}$",
                "example": "+1234567890",
            },
            {
                "name": "webhook_url",
                "type": "STRING",
                "description": "Webhook URL",
                "required": True,
                "pattern": r"^https?://",
                "example": "https://example.com/webhook",
            },
        ]
    }

    manifest = {
        "name": "Webhook Plugin",
        "version": "1.0.0",
        "description": "Send events to webhook endpoints",
        "author": "Integration Team",
    }

    wizard = PluginSetupWizard("webhook-plugin", schema, manifest)
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

    schema = {
        "fields": [
            {
                "name": "api_key",
                "type": "SECRET",
                "description": "API key",
                "required": True,
            },
            {
                "name": "api_url",
                "type": "STRING",
                "description": "API URL",
                "required": True,
            },
            {
                "name": "enabled",
                "type": "BOOL",
                "description": "Plugin enabled",
                "default": True,
            },
        ]
    }

    existing_config = {
        "api_key": "sk_live_existing",
        "api_url": "https://api.existing.com",
        "enabled": True,
    }

    manifest = {
        "name": "Update Plugin",
        "version": "1.0.0",
        "description": "Update configuration for an existing plugin",
    }

    wizard = PluginSetupWizard(
        "update-plugin", schema, manifest, existing_config
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

    schema = {
        "fields": [
            {
                "name": "use_auth",
                "type": "BOOL",
                "description": "Use authentication",
                "default": False,
            },
            {
                "name": "username",
                "type": "STRING",
                "description": "Username (only if auth enabled)",
                "dependencies": [{"field": "use_auth", "value": True}],
            },
            {
                "name": "password",
                "type": "SECRET",
                "description": "Password (only if auth enabled)",
                "dependencies": [{"field": "use_auth", "value": True}],
            },
            {
                "name": "connection_type",
                "type": "CHOICE",
                "description": "Connection type",
                "choices": ["direct", "proxy", "vpn"],
                "default": "direct",
            },
            {
                "name": "proxy_url",
                "type": "STRING",
                "description": "Proxy URL (only if proxy selected)",
                "dependencies": [{"field": "connection_type", "value": "proxy"}],
            },
        ]
    }

    manifest = {
        "name": "Conditional Plugin",
        "version": "1.0.0",
        "description": "Plugin with conditional configuration fields",
    }

    wizard = PluginSetupWizard("conditional-plugin", schema, manifest)
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
