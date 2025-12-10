"""Tests for the plugin setup wizard."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.plugins.setup_wizard import PluginSetupWizard


@pytest.fixture
def basic_schema() -> dict:
    """Basic plugin schema for testing."""
    return {
        "fields": [
            {
                "name": "api_key",
                "type": "SECRET",
                "description": "Your API key",
                "required": True,
                "example": "sk_live_123456",
            },
            {
                "name": "enabled",
                "type": "BOOL",
                "description": "Enable the plugin",
                "default": True,
                "required": False,
            },
            {
                "name": "timeout",
                "type": "INT",
                "description": "Request timeout in seconds",
                "default": 30,
                "minimum": 1,
                "maximum": 300,
                "required": False,
            },
            {
                "name": "log_level",
                "type": "CHOICE",
                "description": "Logging level",
                "choices": ["DEBUG", "INFO", "WARNING", "ERROR"],
                "default": "INFO",
                "required": False,
            },
        ]
    }


@pytest.fixture
def manifest() -> dict:
    """Plugin manifest for testing."""
    return {
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "author": "Test Author",
        "dependencies": [],
        "permissions": [
            {"name": "read_events", "description": "Read calendar events"},
            {"name": "send_messages", "description": "Send messages"},
        ],
    }


class TestPluginSetupWizardInitialization:
    """Test wizard initialization."""

    def test_init_basic(self, basic_schema: dict) -> None:
        """Test basic initialization."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        assert wizard.plugin_name == "test-plugin"
        assert wizard.schema == basic_schema
        assert wizard.new_config == {}
        assert wizard.existing_config == {}

    def test_init_with_manifest(self, basic_schema: dict, manifest: dict) -> None:
        """Test initialization with manifest."""
        wizard = PluginSetupWizard("test-plugin", basic_schema, manifest)
        assert wizard.manifest == manifest

    def test_init_with_existing_config(self, basic_schema: dict) -> None:
        """Test initialization with existing configuration."""
        existing = {"api_key": "existing_key"}
        wizard = PluginSetupWizard("test-plugin", basic_schema, existing_config=existing)
        assert wizard.existing_config == existing


class TestPluginSetupWizardValidation:
    """Test input validation."""

    def test_validate_required_field(self, basic_schema: dict) -> None:
        """Test validation of required fields."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        api_key_field = basic_schema["fields"][0]

        is_valid, msg = wizard._validate_input(api_key_field, "")
        assert not is_valid
        assert "required" in msg.lower()

        is_valid, msg = wizard._validate_input(api_key_field, "sk_live_123")
        assert is_valid
        assert msg == ""

    def test_validate_optional_field(self, basic_schema: dict) -> None:
        """Test validation of optional fields."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        enabled_field = basic_schema["fields"][1]

        is_valid, msg = wizard._validate_input(enabled_field, "")
        assert is_valid
        assert msg == ""

    def test_validate_int_field_range(self, basic_schema: dict) -> None:
        """Test integer field range validation."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        timeout_field = basic_schema["fields"][2]

        is_valid, msg = wizard._validate_input(timeout_field, 0)
        assert not is_valid
        assert "least" in msg.lower()

        is_valid, msg = wizard._validate_input(timeout_field, 400)
        assert not is_valid
        assert "most" in msg.lower()

        is_valid, msg = wizard._validate_input(timeout_field, 60)
        assert is_valid
        assert msg == ""

    def test_validate_choice_field(self, basic_schema: dict) -> None:
        """Test choice field validation."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        log_level_field = basic_schema["fields"][3]

        is_valid, msg = wizard._validate_input(log_level_field, "INVALID")
        assert not is_valid
        assert "must be one of" in msg.lower()

        is_valid, msg = wizard._validate_input(log_level_field, "DEBUG")
        assert is_valid
        assert msg == ""

    def test_validate_string_pattern(self, basic_schema: dict) -> None:
        """Test string pattern validation."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        email_field = {
            "name": "email",
            "type": "STRING",
            "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$",
            "required": True,
        }

        is_valid, msg = wizard._validate_input(email_field, "invalid-email")
        assert not is_valid
        assert "pattern" in msg.lower()

        is_valid, msg = wizard._validate_input(email_field, "test@example.com")
        assert is_valid
        assert msg == ""


class TestPluginSetupWizardFieldFinding:
    """Test field discovery and lookup."""

    def test_find_field_by_name(self, basic_schema: dict) -> None:
        """Test finding field by name."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        field = wizard._find_field_by_name("api_key")
        assert field is not None
        assert field["name"] == "api_key"
        assert field["type"] == "SECRET"

    def test_find_field_by_name_not_found(self, basic_schema: dict) -> None:
        """Test finding non-existent field."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        field = wizard._find_field_by_name("nonexistent")
        assert field is None

    def test_find_field_in_list(self, basic_schema: dict) -> None:
        """Test finding field in field list."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        fields = basic_schema["fields"]
        field = wizard._find_field("timeout", fields)
        assert field is not None
        assert field["name"] == "timeout"
        assert field["type"] == "INT"


class TestPluginSetupWizardDependencies:
    """Test dependency checking."""

    def test_check_dependencies_all_present(self, basic_schema: dict) -> None:
        """Test when all dependencies are present."""
        manifest = {
            "dependencies": ["os", "sys"],  # Standard library modules
        }
        wizard = PluginSetupWizard("test-plugin", basic_schema, manifest)
        assert wizard._check_dependencies() is True

    def test_check_dependencies_missing(self, basic_schema: dict) -> None:
        """Test when dependencies are missing."""
        manifest = {
            "dependencies": ["nonexistent_module_xyz"],
        }
        wizard = PluginSetupWizard("test-plugin", basic_schema, manifest)
        assert wizard._check_dependencies() is False

    def test_check_dependencies_empty(self, basic_schema: dict) -> None:
        """Test when no dependencies are specified."""
        manifest = {"dependencies": []}
        wizard = PluginSetupWizard("test-plugin", basic_schema, manifest)
        assert wizard._check_dependencies() is True

    def test_check_dependencies_no_manifest(self, basic_schema: dict) -> None:
        """Test when manifest has no dependencies field."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        assert wizard._check_dependencies() is True


class TestPluginSetupWizardFieldDependencies:
    """Test field-level dependencies."""

    def test_check_field_dependencies_no_dependencies(self, basic_schema: dict) -> None:
        """Test field with no dependencies."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        field = basic_schema["fields"][0]
        assert wizard._check_field_dependencies(field) is True

    def test_check_field_dependencies_satisfied(self, basic_schema: dict) -> None:
        """Test field with satisfied dependencies."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        wizard.new_config = {"enabled": True}
        field = {
            "name": "api_key",
            "type": "STRING",
            "dependencies": [{"field": "enabled", "value": True}],
        }
        assert wizard._check_field_dependencies(field) is True

    def test_check_field_dependencies_unsatisfied(self, basic_schema: dict) -> None:
        """Test field with unsatisfied dependencies."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        wizard.new_config = {"enabled": False}
        field = {
            "name": "api_key",
            "type": "STRING",
            "dependencies": [{"field": "enabled", "value": True}],
        }
        assert wizard._check_field_dependencies(field) is False


class TestPluginSetupWizardRun:
    """Test the complete wizard flow."""

    def test_run_basic_flow(self, basic_schema: dict) -> None:
        """Test basic wizard flow."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        wizard._check_dependencies = MagicMock(return_value=True)
        wizard.new_config = {"api_key": "sk_live_test"}

        with patch.object(wizard, "_show_header"):
            with patch.object(wizard, "_show_plugin_info"):
                with patch.object(wizard, "_collect_configuration"):
                    with patch.object(wizard, "_show_summary"):
                        with patch(
                            "feishu_webhook_bot.plugins.setup_wizard.Confirm.ask",
                            return_value=True,
                        ):
                            config = wizard.run()

        assert isinstance(config, dict)
        assert config == {"api_key": "sk_live_test"}

    def test_run_cancelled(self, basic_schema: dict) -> None:
        """Test wizard cancellation via Ctrl+C."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)

        with patch.object(wizard, "_show_header"):
            with patch.object(wizard, "_collect_configuration", side_effect=KeyboardInterrupt()):
                config = wizard.run()

        assert config == {}

    def test_run_save_cancelled(self, basic_schema: dict) -> None:
        """Test cancellation at save confirmation."""
        wizard = PluginSetupWizard("test-plugin", basic_schema)
        wizard.new_config = {"api_key": "test"}
        wizard._check_dependencies = MagicMock(return_value=True)

        with patch.object(wizard, "_show_header"):
            with patch.object(wizard, "_show_plugin_info"):
                with patch.object(wizard, "_collect_configuration"):
                    with patch.object(wizard, "_show_summary"):
                        with patch(
                            "feishu_webhook_bot.plugins.setup_wizard.Confirm.ask",
                            return_value=False,
                        ):
                            config = wizard.run()

        assert config == {}


class TestPluginSetupWizardGroupedSchema:
    """Test wizard with grouped fields."""

    def test_collect_configuration_with_groups(self) -> None:
        """Test configuration collection with grouped fields."""
        schema = {
            "groups": [
                {
                    "name": "Basic Settings",
                    "fields": ["api_key", "enabled"],
                },
                {
                    "name": "Advanced Settings",
                    "fields": ["timeout", "log_level"],
                },
            ],
            "fields": [
                {
                    "name": "api_key",
                    "type": "SECRET",
                    "required": True,
                },
                {
                    "name": "enabled",
                    "type": "BOOL",
                    "default": True,
                },
                {
                    "name": "timeout",
                    "type": "INT",
                    "default": 30,
                },
                {
                    "name": "log_level",
                    "type": "CHOICE",
                    "choices": ["DEBUG", "INFO"],
                },
            ],
        }

        wizard = PluginSetupWizard("test-plugin", schema)

        with patch.object(wizard, "_show_group_header") as mock_header:
            with patch.object(wizard, "_collect_field"):
                wizard._collect_configuration()

        assert mock_header.call_count == 2
