"""Tests for plugin configuration schema framework."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.plugins.config_schema import (
    ConfigSchemaBuilder,
    FieldType,
    PluginConfigField,
    PluginConfigSchema,
)


class TestFieldType:
    """Tests for FieldType enum."""

    def test_all_field_types_defined(self) -> None:
        """Verify all expected field types are defined."""
        expected_types = [
            "STRING",
            "INT",
            "FLOAT",
            "BOOL",
            "SECRET",
            "URL",
            "PATH",
            "CHOICE",
            "LIST",
            "DICT",
        ]
        for type_name in expected_types:
            assert hasattr(FieldType, type_name)


class TestPluginConfigField:
    """Tests for PluginConfigField dataclass."""

    def test_create_basic_field(self) -> None:
        """Test creating a basic string field."""
        field = PluginConfigField(
            name="test_field",
            field_type=FieldType.STRING,
            description="A test field",
        )
        assert field.name == "test_field"
        assert field.field_type == FieldType.STRING
        assert field.description == "A test field"
        assert field.required is True
        assert field.default is None

    def test_create_optional_field(self) -> None:
        """Test creating an optional field with default."""
        field = PluginConfigField(
            name="timeout",
            field_type=FieldType.INT,
            description="Request timeout",
            required=False,
            default=30,
        )
        assert field.required is False
        assert field.default == 30

    def test_create_secret_field(self) -> None:
        """Test creating a sensitive secret field."""
        field = PluginConfigField(
            name="api_key",
            field_type=FieldType.SECRET,
            description="API key",
            sensitive=True,
            env_var="MY_API_KEY",
        )
        assert field.sensitive is True
        assert field.env_var == "MY_API_KEY"

    def test_create_choice_field(self) -> None:
        """Test creating a field with choices."""
        field = PluginConfigField(
            name="log_level",
            field_type=FieldType.CHOICE,
            description="Logging level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
        )
        assert field.choices == ["DEBUG", "INFO", "WARNING", "ERROR"]
        assert field.default == "INFO"

    def test_field_with_validation_constraints(self) -> None:
        """Test field with min/max value constraints."""
        field = PluginConfigField(
            name="port",
            field_type=FieldType.INT,
            description="Server port",
            min_value=1,
            max_value=65535,
            default=8080,
        )
        assert field.min_value == 1
        assert field.max_value == 65535

    def test_field_with_regex_pattern(self) -> None:
        """Test field with regex pattern validation."""
        field = PluginConfigField(
            name="email",
            field_type=FieldType.STRING,
            description="Email address",
            pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
        )
        assert field.pattern is not None

    def test_field_with_dependencies(self) -> None:
        """Test field that depends on another field."""
        field = PluginConfigField(
            name="ssl_cert_path",
            field_type=FieldType.PATH,
            description="SSL certificate path",
            depends_on="ssl_enabled",
        )
        assert field.depends_on == "ssl_enabled"

    def test_validate_value_string(self) -> None:
        """Test string value validation."""
        field = PluginConfigField(
            name="name",
            field_type=FieldType.STRING,
            description="Name",
            required=True,
        )
        is_valid, error = field.validate_value("test")
        assert is_valid is True
        assert error == ""  # Empty string on success

    def test_validate_value_int_in_range(self) -> None:
        """Test integer value validation within range."""
        field = PluginConfigField(
            name="port",
            field_type=FieldType.INT,
            description="Port",
            min_value=1,
            max_value=100,
        )
        is_valid, error = field.validate_value(50)
        assert is_valid is True

    def test_validate_value_int_out_of_range(self) -> None:
        """Test integer value validation out of range."""
        field = PluginConfigField(
            name="port",
            field_type=FieldType.INT,
            description="Port",
            min_value=1,
            max_value=100,
        )
        is_valid, error = field.validate_value(200)
        assert is_valid is False
        assert error is not None
        assert "100" in error

    def test_validate_value_choice_valid(self) -> None:
        """Test choice value validation with valid choice."""
        field = PluginConfigField(
            name="level",
            field_type=FieldType.CHOICE,
            description="Level",
            choices=["low", "medium", "high"],
        )
        is_valid, error = field.validate_value("medium")
        assert is_valid is True

    def test_validate_value_choice_invalid(self) -> None:
        """Test choice value validation with invalid choice."""
        field = PluginConfigField(
            name="level",
            field_type=FieldType.CHOICE,
            description="Level",
            choices=["low", "medium", "high"],
        )
        is_valid, error = field.validate_value("extreme")
        assert is_valid is False
        assert error is not None

    def test_validate_value_pattern(self) -> None:
        """Test pattern validation."""
        field = PluginConfigField(
            name="email",
            field_type=FieldType.STRING,
            description="Email",
            pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
        )
        is_valid, _ = field.validate_value("test@example.com")
        assert is_valid is True

        is_valid, error = field.validate_value("invalid-email")
        assert is_valid is False


class TestConfigSchemaBuilder:
    """Tests for ConfigSchemaBuilder."""

    def test_empty_builder(self) -> None:
        """Test building empty schema."""
        builder = ConfigSchemaBuilder()
        fields = builder.build()
        assert fields == {}

    def test_add_single_field(self) -> None:
        """Test adding a single field."""
        builder = ConfigSchemaBuilder()
        builder.add_field(
            name="api_key",
            field_type=FieldType.SECRET,
            description="API key",
            required=True,
        )
        fields = builder.build()
        assert "api_key" in fields
        assert fields["api_key"].name == "api_key"
        assert fields["api_key"].field_type == FieldType.SECRET

    def test_add_multiple_fields(self) -> None:
        """Test adding multiple fields."""
        builder = ConfigSchemaBuilder()
        builder.add_field(
            name="host",
            field_type=FieldType.STRING,
            description="Server host",
            default="localhost",
        )
        builder.add_field(
            name="port",
            field_type=FieldType.INT,
            description="Server port",
            default=8080,
        )
        fields = builder.build()
        assert len(fields) == 2
        assert "host" in fields
        assert "port" in fields

    def test_add_field_with_all_options(self) -> None:
        """Test adding field with all available options."""
        builder = ConfigSchemaBuilder()
        builder.add_field(
            name="timeout",
            field_type=FieldType.INT,
            description="Request timeout",
            required=False,
            default=30,
            min_value=1,
            max_value=300,
            env_var="APP_TIMEOUT",
            example="60",
            help_url="https://example.com/docs/timeout",
        )
        fields = builder.build()
        field = fields["timeout"]
        assert field.min_value == 1
        assert field.max_value == 300
        assert field.env_var == "APP_TIMEOUT"
        assert field.example == "60"
        assert field.help_url == "https://example.com/docs/timeout"

    def test_builder_fluent_interface(self) -> None:
        """Test that builder supports fluent/chained calls."""
        builder = ConfigSchemaBuilder()
        result = builder.add_field(
            name="field1",
            field_type=FieldType.STRING,
            description="Field 1",
        ).add_field(
            name="field2",
            field_type=FieldType.INT,
            description="Field 2",
        )
        # add_field should return self for chaining
        assert result is builder
        fields = builder.build()
        assert len(fields) == 2


class TestPluginConfigSchema:
    """Tests for PluginConfigSchema base class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create a concrete schema class for testing
        class TestSchema(PluginConfigSchema):
            @classmethod
            def get_schema_fields(cls) -> dict[str, PluginConfigField]:
                builder = ConfigSchemaBuilder()
                builder.add_field(
                    name="api_key",
                    field_type=FieldType.SECRET,
                    description="API key",
                    required=True,
                )
                builder.add_field(
                    name="timeout",
                    field_type=FieldType.INT,
                    description="Timeout",
                    required=False,
                    default=30,
                )
                builder.add_field(
                    name="debug",
                    field_type=FieldType.BOOL,
                    description="Debug mode",
                    required=False,
                    default=False,
                )
                return builder.build()

            @classmethod
            def get_field_groups(cls) -> dict[str, list[str]]:
                return {
                    "Auth": ["api_key"],
                    "Network": ["timeout"],
                    "Debug": ["debug"],
                }

        self.TestSchema = TestSchema

    def test_get_required_fields(self) -> None:
        """Test getting required fields."""
        required = self.TestSchema.get_required_fields()
        assert len(required) == 1
        assert required[0].name == "api_key"

    def test_get_optional_fields(self) -> None:
        """Test getting optional fields."""
        optional = self.TestSchema.get_optional_fields()
        assert len(optional) == 2
        names = [f.name for f in optional]
        assert "timeout" in names
        assert "debug" in names

    def test_validate_config_valid(self) -> None:
        """Test validating a valid configuration."""
        config = {"api_key": "secret123", "timeout": 60}
        is_valid, errors = self.TestSchema.validate_config(config)
        assert is_valid is True
        assert errors == []

    def test_validate_config_missing_required(self) -> None:
        """Test validating config with missing required field."""
        config = {"timeout": 60}
        is_valid, errors = self.TestSchema.validate_config(config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("api_key" in e for e in errors)

    def test_validate_config_with_defaults(self) -> None:
        """Test that defaults are used for missing optional fields."""
        config = {"api_key": "secret123"}
        is_valid, errors = self.TestSchema.validate_config(config)
        assert is_valid is True

    def test_get_missing_required(self) -> None:
        """Test getting missing required fields."""
        config = {"timeout": 30}
        missing = self.TestSchema.get_missing_required(config)
        assert len(missing) == 1
        assert missing[0].name == "api_key"

    def test_get_missing_required_none(self) -> None:
        """Test getting missing required fields when all provided."""
        config = {"api_key": "secret123"}
        missing = self.TestSchema.get_missing_required(config)
        assert len(missing) == 0

    def test_generate_template(self) -> None:
        """Test generating configuration template."""
        template = self.TestSchema.generate_template()
        assert isinstance(template, dict)
        assert "api_key" in template
        assert "timeout" in template
        assert template["timeout"] == 30  # default value
        assert template["debug"] is False  # default value

    def test_field_groups(self) -> None:
        """Test field groups are correctly defined."""
        groups = self.TestSchema.get_field_groups()
        assert "Auth" in groups
        assert "api_key" in groups["Auth"]


class TestConfigSchemaIntegration:
    """Integration tests for config schema with real plugin scenarios."""

    def test_calendar_plugin_like_schema(self) -> None:
        """Test schema similar to the Feishu Calendar plugin."""

        class CalendarSchema(PluginConfigSchema):
            @classmethod
            def get_schema_fields(cls) -> dict[str, PluginConfigField]:
                builder = ConfigSchemaBuilder()
                builder.add_field(
                    name="app_id",
                    field_type=FieldType.SECRET,
                    description="Feishu app ID",
                    required=True,
                    env_var="FEISHU_APP_ID",
                )
                builder.add_field(
                    name="app_secret",
                    field_type=FieldType.SECRET,
                    description="Feishu app secret",
                    required=True,
                    sensitive=True,
                    env_var="FEISHU_APP_SECRET",
                )
                builder.add_field(
                    name="calendar_ids",
                    field_type=FieldType.LIST,
                    description="Calendar IDs to monitor",
                    default=["primary"],
                    required=False,
                )
                builder.add_field(
                    name="reminder_minutes",
                    field_type=FieldType.LIST,
                    description="Reminder times",
                    default=[15, 5],
                    required=False,
                )
                return builder.build()

        # Test validation with missing credentials
        config: dict[str, Any] = {"calendar_ids": ["primary"]}
        is_valid, errors = CalendarSchema.validate_config(config)
        assert is_valid is False

        # Test validation with all required fields
        config = {
            "app_id": "cli_xxx",
            "app_secret": "secret",
            "calendar_ids": ["primary", "shared"],
        }
        is_valid, errors = CalendarSchema.validate_config(config)
        assert is_valid is True

    def test_schema_with_dependent_fields(self) -> None:
        """Test schema with field dependencies."""

        class SSLSchema(PluginConfigSchema):
            @classmethod
            def get_schema_fields(cls) -> dict[str, PluginConfigField]:
                builder = ConfigSchemaBuilder()
                builder.add_field(
                    name="ssl_enabled",
                    field_type=FieldType.BOOL,
                    description="Enable SSL",
                    default=False,
                    required=False,
                )
                builder.add_field(
                    name="ssl_cert_path",
                    field_type=FieldType.PATH,
                    description="Path to SSL certificate",
                    required=False,
                    depends_on="ssl_enabled",
                )
                builder.add_field(
                    name="ssl_key_path",
                    field_type=FieldType.PATH,
                    description="Path to SSL key",
                    required=False,
                    depends_on="ssl_enabled",
                )
                return builder.build()

        fields = SSLSchema.get_schema_fields()
        assert fields["ssl_cert_path"].depends_on == "ssl_enabled"
        assert fields["ssl_key_path"].depends_on == "ssl_enabled"
