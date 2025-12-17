#!/usr/bin/env python3
"""Configuration Validation Example.

This example demonstrates configuration validation utilities:
- JSON schema generation for BotConfig
- YAML configuration file validation
- Dictionary configuration validation
- Error message formatting
- Custom validation rules
- Schema export for IDE support

The validation utilities help ensure configuration correctness
before the bot starts.
"""

import tempfile
from pathlib import Path
from typing import Any

import yaml

from feishu_webhook_bot.core import BotConfig, LoggingConfig, get_logger, setup_logging
from feishu_webhook_bot.core.validation import (
    generate_json_schema,
    validate_config_dict,
    validate_yaml_config,
)

# Setup logging
setup_logging(LoggingConfig(level="INFO"))
logger = get_logger(__name__)


# =============================================================================
# Demo 1: JSON Schema Generation
# =============================================================================
def demo_json_schema_generation() -> None:
    """Demonstrate JSON schema generation for BotConfig."""
    print("\n" + "=" * 60)
    print("Demo 1: JSON Schema Generation")
    print("=" * 60)

    # Generate schema without saving
    print("Generating JSON schema for BotConfig...")
    schema = generate_json_schema()

    print(f"\nSchema title: {schema.get('title', 'N/A')}")
    print(f"Schema type: {schema.get('type', 'N/A')}")

    # Show top-level properties
    properties = schema.get("properties", {})
    print(f"\nTop-level properties ({len(properties)}):")
    for prop_name, prop_info in list(properties.items())[:10]:
        prop_type = prop_info.get("type", prop_info.get("anyOf", "complex"))
        print(f"  - {prop_name}: {prop_type}")

    if len(properties) > 10:
        print(f"  ... and {len(properties) - 10} more")

    # Show required fields
    required = schema.get("required", [])
    print(f"\nRequired fields: {required if required else 'None'}")


# =============================================================================
# Demo 2: Save Schema to File
# =============================================================================
def demo_save_schema_to_file() -> None:
    """Demonstrate saving JSON schema to file."""
    print("\n" + "=" * 60)
    print("Demo 2: Save Schema to File")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        schema_path = Path(tmpdir) / "config-schema.json"

        # Generate and save schema
        print(f"Saving schema to: {schema_path}")
        generate_json_schema(output_path=schema_path)

        # Verify file was created
        print(f"File exists: {schema_path.exists()}")
        print(f"File size: {schema_path.stat().st_size} bytes")

        # Read and display part of the file
        with open(schema_path) as f:
            content = f.read()

        print("\nFirst 500 characters of schema:")
        print("-" * 40)
        print(content[:500])
        print("-" * 40)


# =============================================================================
# Demo 3: Validate YAML Configuration
# =============================================================================
def demo_validate_yaml_config() -> None:
    """Demonstrate YAML configuration validation."""
    print("\n" + "=" * 60)
    print("Demo 3: Validate YAML Configuration")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test 1: Valid configuration
        print("\n--- Test 1: Valid configuration ---")
        valid_config_path = Path(tmpdir) / "valid_config.yaml"
        valid_config = {
            "webhooks": [
                {
                    "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                    "name": "default",
                    "secret": "my_secret",
                }
            ],
            "scheduler": {
                "enabled": True,
                "timezone": "Asia/Shanghai",
            },
        }
        with open(valid_config_path, "w") as f:
            yaml.dump(valid_config, f)

        is_valid, errors = validate_yaml_config(valid_config_path)
        print(f"Valid: {is_valid}")
        print(f"Errors: {errors if errors else 'None'}")

        # Test 2: Missing required field
        print("\n--- Test 2: Missing required field ---")
        invalid_config_path = Path(tmpdir) / "invalid_config.yaml"
        invalid_config = {
            "webhooks": [
                {"name": "missing_url"}  # Missing 'url' field
            ],
        }
        with open(invalid_config_path, "w") as f:
            yaml.dump(invalid_config, f)

        is_valid, errors = validate_yaml_config(invalid_config_path)
        print(f"Valid: {is_valid}")
        print("Errors:")
        for error in errors:
            print(f"  - {error}")

        # Test 3: Invalid YAML syntax
        print("\n--- Test 3: Invalid YAML syntax ---")
        syntax_error_path = Path(tmpdir) / "syntax_error.yaml"
        with open(syntax_error_path, "w") as f:
            f.write("invalid: yaml: [syntax")

        is_valid, errors = validate_yaml_config(syntax_error_path)
        print(f"Valid: {is_valid}")
        print("Errors:")
        for error in errors:
            print(f"  - {error[:80]}...")

        # Test 4: Non-existent file
        print("\n--- Test 4: Non-existent file ---")
        is_valid, errors = validate_yaml_config(Path(tmpdir) / "nonexistent.yaml")
        print(f"Valid: {is_valid}")
        print("Errors:")
        for error in errors:
            print(f"  - {error}")


# =============================================================================
# Demo 4: Validate Configuration Dictionary
# =============================================================================
def demo_validate_config_dict() -> None:
    """Demonstrate dictionary configuration validation."""
    print("\n" + "=" * 60)
    print("Demo 4: Validate Configuration Dictionary")
    print("=" * 60)

    # Test 1: Valid dictionary
    print("\n--- Test 1: Valid dictionary ---")
    valid_dict = {
        "webhooks": [
            {
                "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                "name": "default",
            }
        ],
    }
    is_valid, errors = validate_config_dict(valid_dict)
    print(f"Valid: {is_valid}")
    print(f"Errors: {errors if errors else 'None'}")

    # Test 2: Invalid type
    print("\n--- Test 2: Invalid type ---")
    invalid_type_dict = {
        "webhooks": "not_a_list",  # Should be a list
    }
    is_valid, errors = validate_config_dict(invalid_type_dict)
    print(f"Valid: {is_valid}")
    print("Errors:")
    for error in errors:
        print(f"  - {error}")

    # Test 3: Invalid nested value
    print("\n--- Test 3: Invalid nested value ---")
    invalid_nested_dict = {
        "webhooks": [
            {
                "url": "https://example.com/webhook",
                "name": "test",
            }
        ],
        "scheduler": {
            "enabled": "not_a_boolean",  # Should be boolean
        },
    }
    is_valid, errors = validate_config_dict(invalid_nested_dict)
    print(f"Valid: {is_valid}")
    print("Errors:")
    for error in errors:
        print(f"  - {error}")

    # Test 4: Extra unknown fields (should be allowed)
    print("\n--- Test 4: Extra unknown fields ---")
    extra_fields_dict = {
        "webhooks": [{"url": "https://example.com/webhook", "name": "test"}],
        "custom_field": "custom_value",  # Extra field
    }
    is_valid, errors = validate_config_dict(extra_fields_dict)
    print(f"Valid: {is_valid}")
    print(f"Errors: {errors if errors else 'None'}")


# =============================================================================
# Demo 5: Comprehensive Validation Scenarios
# =============================================================================
def demo_comprehensive_validation() -> None:
    """Demonstrate comprehensive validation scenarios."""
    print("\n" + "=" * 60)
    print("Demo 5: Comprehensive Validation Scenarios")
    print("=" * 60)

    test_cases = [
        {
            "name": "Minimal valid config",
            "config": {
                "webhooks": [{"url": "https://example.com/webhook", "name": "default"}],
            },
        },
        {
            "name": "Full config with all options",
            "config": {
                "webhooks": [
                    {
                        "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                        "name": "primary",
                        "secret": "secret123",
                    },
                    {
                        "url": "https://open.feishu.cn/open-apis/bot/v2/hook/yyy",
                        "name": "secondary",
                    },
                ],
                "scheduler": {
                    "enabled": True,
                    "timezone": "Asia/Shanghai",
                    "job_store_type": "memory",
                },
                "plugins": {
                    "enabled": True,
                    "plugin_dir": "./plugins",
                    "hot_reload": True,
                },
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
        },
        {
            "name": "Empty webhooks list",
            "config": {
                "webhooks": [],
            },
        },
        {
            "name": "Invalid URL format",
            "config": {
                "webhooks": [{"url": "not_a_valid_url", "name": "invalid"}],
            },
        },
        {
            "name": "Missing webhooks entirely",
            "config": {
                "scheduler": {"enabled": True},
            },
        },
    ]

    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        is_valid, errors = validate_config_dict(test["config"])
        print(f"Valid: {is_valid}")
        if errors:
            print("Errors:")
            for error in errors[:3]:  # Show first 3 errors
                print(f"  - {error}")
            if len(errors) > 3:
                print(f"  ... and {len(errors) - 3} more errors")


# =============================================================================
# Demo 6: Schema for IDE Support
# =============================================================================
def demo_schema_for_ide() -> None:
    """Demonstrate using schema for IDE support."""
    print("\n" + "=" * 60)
    print("Demo 6: Schema for IDE Support")
    print("=" * 60)

    print("JSON Schema can be used for IDE autocompletion and validation.")
    print("\nTo use with VS Code:")
    print("1. Generate the schema file:")
    print("   generate_json_schema('config-schema.json')")
    print("\n2. Add to your YAML file:")
    print("   # yaml-language-server: $schema=./config-schema.json")
    print("\n3. Or configure in .vscode/settings.json:")
    print('   "yaml.schemas": {')
    print('     "./config-schema.json": "config.yaml"')
    print("   }")

    # Generate example schema
    with tempfile.TemporaryDirectory() as tmpdir:
        schema_path = Path(tmpdir) / "config-schema.json"
        generate_json_schema(schema_path)

        # Show how to reference in YAML
        print("\n--- Example YAML with schema reference ---")
        example_yaml = """# yaml-language-server: $schema=./config-schema.json

webhooks:
  - url: https://open.feishu.cn/open-apis/bot/v2/hook/xxx
    name: default
    secret: my_secret

scheduler:
  enabled: true
  timezone: Asia/Shanghai

plugins:
  enabled: true
  plugin_dir: ./plugins
"""
        print(example_yaml)


# =============================================================================
# Demo 7: Custom Validation Function
# =============================================================================
def demo_custom_validation() -> None:
    """Demonstrate custom validation functions."""
    print("\n" + "=" * 60)
    print("Demo 7: Custom Validation Functions")
    print("=" * 60)

    def validate_webhook_urls(config_dict: dict[str, Any]) -> tuple[bool, list[str]]:
        """Custom validation for webhook URLs."""
        errors = []

        webhooks = config_dict.get("webhooks", [])
        for i, webhook in enumerate(webhooks):
            url = webhook.get("url", "")

            # Check for Feishu webhook URL pattern
            if not url.startswith("https://"):
                errors.append(f"webhooks[{i}].url: Must use HTTPS")

            if "feishu.cn" not in url and "larksuite.com" not in url:
                errors.append(f"webhooks[{i}].url: Should be a Feishu/Lark webhook URL")

            # Check for secret if using signed webhooks
            if "hook/v2" in url and not webhook.get("secret"):
                errors.append(f"webhooks[{i}]: v2 webhooks should have a secret configured")

        return len(errors) == 0, errors

    def validate_scheduler_timezone(
        config_dict: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Custom validation for scheduler timezone."""
        errors = []

        scheduler = config_dict.get("scheduler", {})
        timezone = scheduler.get("timezone", "UTC")

        # List of common valid timezones
        valid_timezones = [
            "UTC",
            "Asia/Shanghai",
            "Asia/Tokyo",
            "America/New_York",
            "Europe/London",
        ]

        if timezone not in valid_timezones:
            errors.append(
                f"scheduler.timezone: '{timezone}' may not be valid. "
                f"Common options: {', '.join(valid_timezones)}"
            )

        return len(errors) == 0, errors

    def full_validation(config_dict: dict[str, Any]) -> tuple[bool, list[str]]:
        """Run all validations."""
        all_errors = []

        # Standard validation
        is_valid, errors = validate_config_dict(config_dict)
        all_errors.extend(errors)

        # Custom validations
        _, url_errors = validate_webhook_urls(config_dict)
        all_errors.extend(url_errors)

        _, tz_errors = validate_scheduler_timezone(config_dict)
        all_errors.extend(tz_errors)

        return len(all_errors) == 0, all_errors

    # Test with various configs
    test_configs = [
        {
            "name": "Valid Feishu config",
            "config": {
                "webhooks": [
                    {
                        "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                        "name": "default",
                        "secret": "my_secret",
                    }
                ],
                "scheduler": {"timezone": "Asia/Shanghai"},
            },
        },
        {
            "name": "HTTP URL (should warn)",
            "config": {
                "webhooks": [{"url": "http://example.com/webhook", "name": "insecure"}],
            },
        },
        {
            "name": "Missing secret for v2 webhook",
            "config": {
                "webhooks": [
                    {
                        "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                        "name": "no_secret",
                    }
                ],
            },
        },
        {
            "name": "Unknown timezone",
            "config": {
                "webhooks": [{"url": "https://open.feishu.cn/webhook", "name": "test"}],
                "scheduler": {"timezone": "Mars/Olympus"},
            },
        },
    ]

    for test in test_configs:
        print(f"\n--- {test['name']} ---")
        is_valid, errors = full_validation(test["config"])
        print(f"Valid: {is_valid}")
        if errors:
            print("Issues:")
            for error in errors:
                print(f"  - {error}")


# =============================================================================
# Demo 8: Real-World Validation Workflow
# =============================================================================
def demo_real_world_workflow() -> None:
    """Demonstrate a real-world validation workflow."""
    print("\n" + "=" * 60)
    print("Demo 8: Real-World Validation Workflow")
    print("=" * 60)

    class ConfigValidator:
        """Configuration validator with comprehensive checks."""

        def __init__(self):
            self.schema = generate_json_schema()

        def validate_file(self, config_path: Path) -> tuple[bool, list[str], BotConfig | None]:
            """Validate a configuration file.

            Returns:
                Tuple of (is_valid, errors, config_object)
            """
            errors = []

            # Check file exists
            if not config_path.exists():
                return False, [f"Configuration file not found: {config_path}"], None

            # Check file extension
            if config_path.suffix not in [".yaml", ".yml"]:
                errors.append("Warning: Expected .yaml or .yml extension")

            # Validate YAML
            is_valid, yaml_errors = validate_yaml_config(config_path)
            if not is_valid:
                return False, yaml_errors, None

            # Load and return config
            with open(config_path) as f:
                data = yaml.safe_load(f)

            try:
                config = BotConfig(**data)
                return True, errors, config
            except Exception as e:
                return False, [str(e)], None

        def validate_and_report(self, config_path: Path) -> None:
            """Validate and print a detailed report."""
            print(f"\nValidating: {config_path}")
            print("-" * 40)

            is_valid, errors, config = self.validate_file(config_path)

            if is_valid:
                print("Status: VALID")
                if config:
                    print("\nConfiguration Summary:")
                    print(f"  Webhooks: {len(config.webhooks)}")
                    print(f"  Scheduler enabled: {config.scheduler.enabled}")
                    print(f"  Plugins enabled: {config.plugins.enabled}")
            else:
                print("Status: INVALID")
                print(f"\nErrors ({len(errors)}):")
                for error in errors:
                    print(f"  - {error}")

            if errors and is_valid:
                print(f"\nWarnings ({len(errors)}):")
                for error in errors:
                    print(f"  - {error}")

    # Use the validator
    validator = ConfigValidator()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test configs
        configs = {
            "valid_config.yaml": {
                "webhooks": [
                    {
                        "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                        "name": "default",
                    }
                ],
                "scheduler": {"enabled": True},
            },
            "invalid_config.yaml": {
                "webhooks": [{"name": "missing_url"}],
            },
            "config.txt": {  # Wrong extension
                "webhooks": [{"url": "https://example.com/webhook", "name": "test"}],
            },
        }

        for filename, config_data in configs.items():
            config_path = Path(tmpdir) / filename
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)
            validator.validate_and_report(config_path)


# =============================================================================
# Main Entry Point
# =============================================================================
def main() -> None:
    """Run all configuration validation demonstrations."""
    print("=" * 60)
    print("Configuration Validation Examples")
    print("=" * 60)

    demos = [
        ("JSON Schema Generation", demo_json_schema_generation),
        ("Save Schema to File", demo_save_schema_to_file),
        ("Validate YAML Configuration", demo_validate_yaml_config),
        ("Validate Configuration Dictionary", demo_validate_config_dict),
        ("Comprehensive Validation Scenarios", demo_comprehensive_validation),
        ("Schema for IDE Support", demo_schema_for_ide),
        ("Custom Validation Functions", demo_custom_validation),
        ("Real-World Validation Workflow", demo_real_world_workflow),
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
