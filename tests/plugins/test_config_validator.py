"""Tests for plugins.config_validator module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from pydantic import Field

from feishu_webhook_bot.plugins.config_registry import ConfigSchemaRegistry
from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema
from feishu_webhook_bot.plugins.config_validator import (
    ConfigValidator,
    StartupValidationReport,
    ValidationResult,
)


class MockConfigSchema(PluginConfigSchema):
    """Mock config schema for testing."""

    api_key: str = Field(..., description="API key")
    timeout: int = Field(default=30, description="Timeout")


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_valid_result(self) -> None:
        """Test creating a valid result."""
        result = ValidationResult(
            plugin_name="test-plugin",
            is_valid=True,
        )

        assert result.plugin_name == "test-plugin"
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.missing_required == []
        assert result.invalid_values == {}

    def test_create_invalid_result(self) -> None:
        """Test creating an invalid result."""
        result = ValidationResult(
            plugin_name="test-plugin",
            is_valid=False,
            errors=["Missing required field"],
            missing_required=["api_key"],
            invalid_values={"timeout": "Must be integer"},
        )

        assert result.is_valid is False
        assert "Missing required field" in result.errors
        assert "api_key" in result.missing_required
        assert "timeout" in result.invalid_values


class TestStartupValidationReport:
    """Tests for StartupValidationReport dataclass."""

    def test_create_all_valid_report(self) -> None:
        """Test creating a report with all valid plugins."""
        report = StartupValidationReport(
            all_valid=True,
            plugins_ready=["plugin-a", "plugin-b"],
        )

        assert report.all_valid is True
        assert "plugin-a" in report.plugins_ready
        assert report.plugins_need_config == []
        assert report.suggestions == []

    def test_create_report_with_issues(self) -> None:
        """Test creating a report with configuration issues."""
        report = StartupValidationReport(
            all_valid=False,
            plugins_ready=["plugin-a"],
            plugins_need_config=["plugin-b"],
            suggestions=["Run: feishu-webhook-bot plugin setup plugin-b"],
        )

        assert report.all_valid is False
        assert "plugin-b" in report.plugins_need_config
        assert len(report.suggestions) == 1


class TestConfigValidator:
    """Tests for ConfigValidator."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        ConfigSchemaRegistry.clear()

    def teardown_method(self) -> None:
        """Clear registry after each test."""
        ConfigSchemaRegistry.clear()

    def _create_mock_config(self, plugin_settings: dict[str, Any]) -> MagicMock:
        """Create a mock BotConfig."""
        mock_config = MagicMock()
        mock_config.plugins.get_plugin_settings.side_effect = lambda name: plugin_settings.get(
            name, {}
        )
        return mock_config

    def test_validate_plugin_with_valid_config(self) -> None:
        """Test validating plugin with valid configuration."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)
        mock_config = self._create_mock_config(
            {"test-plugin": {"api_key": "secret123", "timeout": 60}}
        )

        validator = ConfigValidator(mock_config)
        result = validator.validate_plugin("test-plugin")

        assert result.is_valid is True
        assert result.errors == []
        assert result.missing_required == []

    def test_validate_plugin_with_missing_required(self) -> None:
        """Test validating plugin with missing required field."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)
        mock_config = self._create_mock_config({"test-plugin": {"timeout": 60}})

        validator = ConfigValidator(mock_config)
        result = validator.validate_plugin("test-plugin")

        assert result.is_valid is False
        assert "api_key" in result.missing_required

    def test_validate_plugin_without_schema(self) -> None:
        """Test validating plugin without registered schema."""
        mock_config = self._create_mock_config({})

        validator = ConfigValidator(mock_config)
        result = validator.validate_plugin("unknown-plugin")

        assert result.is_valid is True
        assert "Plugin does not define a configuration schema" in result.warnings

    def test_validate_all(self) -> None:
        """Test validating all registered plugins."""
        ConfigSchemaRegistry.register("plugin-a", MockConfigSchema)
        ConfigSchemaRegistry.register("plugin-b", MockConfigSchema)
        mock_config = self._create_mock_config(
            {
                "plugin-a": {"api_key": "key1"},
                "plugin-b": {},
            }
        )

        validator = ConfigValidator(mock_config)
        results = validator.validate_all()

        assert len(results) == 2
        plugin_names = [r.plugin_name for r in results]
        assert "plugin-a" in plugin_names
        assert "plugin-b" in plugin_names

    def test_validate_plugins_specific(self) -> None:
        """Test validating specific plugins."""
        ConfigSchemaRegistry.register("plugin-a", MockConfigSchema)
        ConfigSchemaRegistry.register("plugin-b", MockConfigSchema)
        mock_config = self._create_mock_config(
            {"plugin-a": {"api_key": "key1"}}
        )

        validator = ConfigValidator(mock_config)
        results = validator.validate_plugins(["plugin-a"])

        assert len(results) == 1
        assert results[0].plugin_name == "plugin-a"

    def test_generate_startup_report_all_valid(self) -> None:
        """Test generating startup report with all valid plugins."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)
        mock_config = self._create_mock_config(
            {"test-plugin": {"api_key": "secret"}}
        )

        mock_plugin = MagicMock()
        mock_plugin.metadata.return_value.name = "test-plugin"

        validator = ConfigValidator(mock_config)
        report = validator.generate_startup_report({"test-plugin": mock_plugin})

        assert report.all_valid is True
        assert "test-plugin" in report.plugins_ready
        assert report.plugins_need_config == []

    def test_generate_startup_report_with_issues(self) -> None:
        """Test generating startup report with configuration issues."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)
        mock_config = self._create_mock_config({"test-plugin": {}})

        mock_plugin = MagicMock()
        mock_plugin.metadata.return_value.name = "test-plugin"

        validator = ConfigValidator(mock_config)
        report = validator.generate_startup_report({"test-plugin": mock_plugin})

        assert report.all_valid is False
        assert "test-plugin" in report.plugins_need_config
        assert len(report.suggestions) > 0

    def test_get_plugin_config_status(self) -> None:
        """Test getting detailed plugin config status."""
        ConfigSchemaRegistry.register("test-plugin", MockConfigSchema)
        mock_config = self._create_mock_config(
            {"test-plugin": {"api_key": "secret", "timeout": 60}}
        )

        validator = ConfigValidator(mock_config)
        status = validator.get_plugin_config_status("test-plugin")

        assert status["plugin_name"] == "test-plugin"
        assert status["has_schema"] is True
        assert status["is_valid"] is True
        assert "api_key" in status["required_fields"]
        assert "timeout" in status["optional_fields"]

    def test_get_plugin_config_status_no_schema(self) -> None:
        """Test getting status for plugin without schema."""
        mock_config = self._create_mock_config({})

        validator = ConfigValidator(mock_config)
        status = validator.get_plugin_config_status("unknown-plugin")

        assert status["plugin_name"] == "unknown-plugin"
        assert status["has_schema"] is False
        assert status["is_valid"] is True

    def test_print_report_all_valid(self) -> None:
        """Test printing report with all valid plugins."""
        mock_config = self._create_mock_config({})
        validator = ConfigValidator(mock_config)

        report = StartupValidationReport(
            all_valid=True,
            plugins_ready=["plugin-a"],
        )

        validator.print_report(report)

    def test_print_report_with_issues(self) -> None:
        """Test printing report with issues."""
        mock_config = self._create_mock_config({})
        validator = ConfigValidator(mock_config)

        report = StartupValidationReport(
            all_valid=False,
            results=[
                ValidationResult(
                    plugin_name="plugin-a",
                    is_valid=False,
                    errors=["Missing field"],
                    missing_required=["api_key"],
                )
            ],
            plugins_need_config=["plugin-a"],
            suggestions=["Fix plugin-a"],
        )

        validator.print_report(report)
