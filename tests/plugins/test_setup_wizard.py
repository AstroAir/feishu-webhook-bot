"""Tests for the plugin setup wizard."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import Field

from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema
from feishu_webhook_bot.plugins.manifest import PluginManifest
from feishu_webhook_bot.plugins.setup_wizard import PluginSetupWizard


class BasicTestSchema(PluginConfigSchema):
    """Basic plugin schema for testing."""

    api_key: str = Field(
        ...,
        description="Your API key",
        json_schema_extra={"sensitive": True, "example": "sk_live_123456"},
    )
    enabled: bool = Field(default=True, description="Enable the plugin")
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1,
        le=300,
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        json_schema_extra={"choices": ["DEBUG", "INFO", "WARNING", "ERROR"]},
    )


class GroupedTestSchema(PluginConfigSchema):
    """Schema with field groups for testing."""

    api_key: str = Field(..., description="API key")
    enabled: bool = Field(default=True, description="Enable plugin")
    timeout: int = Field(default=30, description="Timeout")
    log_level: str = Field(default="INFO", description="Log level")

    @classmethod
    def get_field_groups(cls) -> dict[str, list[str]]:
        return {
            "Basic Settings": ["api_key", "enabled"],
            "Advanced Settings": ["timeout", "log_level"],
        }


@pytest.fixture
def basic_schema() -> type[PluginConfigSchema]:
    """Basic plugin schema for testing."""
    return BasicTestSchema


@pytest.fixture
def grouped_schema() -> type[PluginConfigSchema]:
    """Grouped plugin schema for testing."""
    return GroupedTestSchema


@pytest.fixture
def manifest() -> PluginManifest:
    """Plugin manifest for testing."""
    return PluginManifest(
        name="Test Plugin",
        version="1.0.0",
        description="A test plugin",
        author="Test Author",
    )


class TestPluginSetupWizardInitialization:
    """Test wizard initialization."""

    def test_init_basic(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test basic initialization."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        assert wizard.plugin_name == "test-plugin"
        assert wizard.schema == basic_schema
        assert wizard.new_config == {}
        assert wizard.existing_config == {}

    def test_init_with_manifest(
        self, basic_schema: type[PluginConfigSchema], manifest: PluginManifest
    ) -> None:
        """Test initialization with manifest."""
        wizard = PluginSetupWizard("test-plugin", basic_schema, manifest)
        assert wizard.manifest == manifest

    def test_init_with_existing_config(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test initialization with existing configuration."""
        existing = {"api_key": "existing_key"}
        wizard = PluginSetupWizard("test-plugin", basic_schema, existing_config=existing)
        assert wizard.existing_config == existing


class TestPluginSetupWizardSchemaAccess:
    """Test schema field access."""

    def test_get_schema_fields(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test getting schema fields."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        fields = wizard.schema.get_schema_fields()
        assert "api_key" in fields
        assert "enabled" in fields
        assert "timeout" in fields
        assert "log_level" in fields

    def test_get_required_fields(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test getting required fields."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        required = wizard.schema.get_required_fields()
        assert len(required) == 1
        assert required[0].name == "api_key"

    def test_get_optional_fields(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test getting optional fields."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        optional = wizard.schema.get_optional_fields()
        assert len(optional) == 3
        names = [f.name for f in optional]
        assert "enabled" in names
        assert "timeout" in names
        assert "log_level" in names

    def test_get_field_groups(self, grouped_schema: type[PluginConfigSchema]) -> None:
        """Test getting field groups."""
        wizard = PluginSetupWizard("test-plugin", grouped_schema)
        groups = wizard.schema.get_field_groups()
        assert "Basic Settings" in groups
        assert "Advanced Settings" in groups
        assert "api_key" in groups["Basic Settings"]


class TestPluginSetupWizardRun:
    """Test the complete wizard flow."""

    def test_run_cancelled_keyboard_interrupt(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test wizard cancellation via Ctrl+C."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)

        with patch.object(wizard, "_show_header", side_effect=KeyboardInterrupt()):
            config = wizard.run()

        assert config == {}

    def test_run_with_manifest(
        self, basic_schema: type[PluginConfigSchema], manifest: PluginManifest
    ) -> None:
        """Test wizard run with manifest."""
        wizard = PluginSetupWizard("test-plugin", basic_schema, manifest)
        wizard.new_config = {"api_key": "test_key"}

        with (
            patch.object(wizard, "_show_header"),
            patch.object(wizard, "_show_plugin_info"),
            patch.object(wizard, "_check_dependencies", return_value=True),
            patch.object(wizard, "_show_permissions"),
            patch.object(wizard, "_collect_configuration"),
            patch.object(wizard, "_show_summary"),
            patch.object(wizard, "_confirm", return_value=True),
        ):
            config = wizard.run()

        assert config == {"api_key": "test_key"}

    def test_run_save_declined(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test wizard when save is declined."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        wizard.new_config = {"api_key": "test_key"}

        with (
            patch.object(wizard, "_show_header"),
            patch.object(wizard, "_collect_configuration"),
            patch.object(wizard, "_show_summary"),
            patch.object(wizard, "_confirm", return_value=False),
        ):
            config = wizard.run()

        assert config == {}


class TestPluginSetupWizardValidation:
    """Test schema validation through wizard."""

    def test_validate_config_valid(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test validation with valid config."""
        is_valid, errors = basic_schema.validate_config({"api_key": "test_key", "timeout": 60})
        assert is_valid is True
        assert errors == []

    def test_validate_config_missing_required(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test validation with missing required field."""
        is_valid, errors = basic_schema.validate_config({"timeout": 60})
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_config_invalid_range(self, basic_schema: type[PluginConfigSchema]) -> None:
        """Test validation with out-of-range value."""
        is_valid, errors = basic_schema.validate_config({"api_key": "test", "timeout": 500})
        assert is_valid is False
