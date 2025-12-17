"""Comprehensive tests for configuration validation utilities.

Tests cover:
- JSON schema generation
- YAML configuration validation
- Configuration dictionary validation
- Configuration template generation
- Completeness checking
- Improvement suggestions
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import yaml

from feishu_webhook_bot.core.validation import (
    check_config_completeness,
    generate_json_schema,
    get_config_template,
    suggest_config_improvements,
    validate_config_dict,
    validate_yaml_config,
)

# ==============================================================================
# JSON Schema Generation Tests
# ==============================================================================


class TestGenerateJsonSchema:
    """Tests for JSON schema generation."""

    def test_generate_schema_returns_dict(self):
        """Test generate_json_schema returns a dictionary."""
        schema = generate_json_schema()

        assert isinstance(schema, dict)
        assert "properties" in schema or "$defs" in schema

    def test_generate_schema_has_title(self):
        """Test generated schema has title."""
        schema = generate_json_schema()

        assert "title" in schema

    def test_generate_schema_saves_to_file(self):
        """Test generate_json_schema saves to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "schema.json"

            schema = generate_json_schema(output_path)

            assert output_path.exists()
            with open(output_path) as f:
                saved_schema = json.load(f)
            assert saved_schema == schema

    def test_generate_schema_creates_parent_dirs(self):
        """Test generate_json_schema creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "schema.json"

            generate_json_schema(output_path)

            assert output_path.exists()


# ==============================================================================
# YAML Configuration Validation Tests
# ==============================================================================


class TestValidateYamlConfig:
    """Tests for YAML configuration validation."""

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            is_valid, errors = validate_yaml_config(config_path)

            assert is_valid is True
            assert errors == []
        finally:
            Path(config_path).unlink()

    def test_validate_file_not_found(self):
        """Test validation with nonexistent file."""
        is_valid, errors = validate_yaml_config("/nonexistent/config.yaml")

        assert is_valid is False
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_validate_invalid_yaml_syntax(self):
        """Test validation with invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: syntax: [")
            config_path = f.name

        try:
            is_valid, errors = validate_yaml_config(config_path)

            assert is_valid is False
            assert len(errors) == 1
            assert "YAML" in errors[0] or "syntax" in errors[0].lower()
        finally:
            Path(config_path).unlink()

    def test_validate_invalid_schema(self):
        """Test validation with invalid schema."""
        config = {
            "webhooks": "not a list",  # Should be a list
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            is_valid, errors = validate_yaml_config(config_path)

            assert is_valid is False
            assert len(errors) > 0
        finally:
            Path(config_path).unlink()


# ==============================================================================
# Configuration Dictionary Validation Tests
# ==============================================================================


class TestValidateConfigDict:
    """Tests for configuration dictionary validation."""

    def test_validate_valid_dict(self):
        """Test validation of valid dictionary."""
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
        }

        is_valid, errors = validate_config_dict(config)

        assert is_valid is True
        assert errors == []

    def test_validate_empty_dict(self):
        """Test validation of empty dictionary."""
        is_valid, errors = validate_config_dict({})

        # Empty config should be valid with defaults
        assert is_valid is True

    def test_validate_invalid_type(self):
        """Test validation with invalid type."""
        config = {
            "webhooks": "not a list",
        }

        is_valid, errors = validate_config_dict(config)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_missing_required_field(self):
        """Test validation with missing required field in nested object."""
        config = {
            "webhooks": [{"name": "default"}],  # Missing 'url'
        }

        is_valid, errors = validate_config_dict(config)

        assert is_valid is False
        assert any("url" in e.lower() for e in errors)


# ==============================================================================
# Configuration Template Tests
# ==============================================================================


class TestGetConfigTemplate:
    """Tests for configuration template generation."""

    def test_get_template_returns_dict(self):
        """Test get_config_template returns dictionary."""
        template = get_config_template()

        assert isinstance(template, dict)

    def test_get_template_has_sections(self):
        """Test template has expected sections."""
        template = get_config_template()

        # Should have common sections
        assert "webhooks" in template or "scheduler" in template or "plugins" in template

    def test_get_template_is_valid(self):
        """Test template is valid configuration."""
        template = get_config_template()

        is_valid, errors = validate_config_dict(template)

        assert is_valid is True


# ==============================================================================
# Completeness Checking Tests
# ==============================================================================


class TestCheckConfigCompleteness:
    """Tests for configuration completeness checking."""

    def test_check_completeness_valid_config(self):
        """Test completeness check with valid config."""
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
            "scheduler": {"enabled": True},
            "plugins": {"enabled": True},
            "logging": {"level": "INFO"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            result = check_config_completeness(config_path)

            assert result["is_valid"] is True
            assert "completeness_percentage" in result
            assert "configured_sections" in result
        finally:
            Path(config_path).unlink()

    def test_check_completeness_invalid_config(self):
        """Test completeness check with invalid config."""
        result = check_config_completeness("/nonexistent/config.yaml")

        assert result["is_valid"] is False
        assert len(result["warnings"]) > 0

    def test_check_completeness_percentage(self):
        """Test completeness percentage calculation."""
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
            "scheduler": {"enabled": True},
            "plugins": {"enabled": True},
            "logging": {"level": "INFO"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            result = check_config_completeness(config_path)

            assert 0 <= result["completeness_percentage"] <= 100
        finally:
            Path(config_path).unlink()

    def test_check_completeness_missing_sections(self):
        """Test completeness identifies missing sections."""
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            result = check_config_completeness(config_path)

            # Should identify optional sections as missing
            assert (
                len(result["optional_sections"]) > 0 or len(result["missing_optional_fields"]) > 0
            )
        finally:
            Path(config_path).unlink()


# ==============================================================================
# Improvement Suggestions Tests
# ==============================================================================


class TestSuggestConfigImprovements:
    """Tests for configuration improvement suggestions."""

    def test_suggest_improvements_returns_list(self):
        """Test suggest_config_improvements returns list."""
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            suggestions = suggest_config_improvements(config_path)

            assert isinstance(suggestions, list)
        finally:
            Path(config_path).unlink()

    def test_suggest_improvements_invalid_config(self):
        """Test suggestions for invalid config."""
        suggestions = suggest_config_improvements("/nonexistent/config.yaml")

        assert len(suggestions) == 1
        assert "Cannot load" in suggestions[0]

    def test_suggest_improvements_disabled_scheduler(self):
        """Test suggestions when scheduler is disabled."""
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
            "scheduler": {"enabled": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            suggestions = suggest_config_improvements(config_path)

            assert any("scheduler" in s.lower() for s in suggestions)
        finally:
            Path(config_path).unlink()

    def test_suggest_improvements_debug_logging(self):
        """Test suggestions when logging is DEBUG."""
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
            "logging": {"level": "DEBUG"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            suggestions = suggest_config_improvements(config_path)

            assert any("DEBUG" in s for s in suggestions)
        finally:
            Path(config_path).unlink()

    def test_suggest_improvements_no_tasks(self):
        """Test suggestions when no tasks configured."""
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
            "tasks": [],
            "automations": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            suggestions = suggest_config_improvements(config_path)

            assert any("task" in s.lower() or "automation" in s.lower() for s in suggestions)
        finally:
            Path(config_path).unlink()


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestValidationIntegration:
    """Integration tests for validation utilities."""

    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        # Create config
        config = {
            "webhooks": [{"name": "default", "url": "https://example.com/webhook"}],
            "scheduler": {"enabled": True},
            "plugins": {"enabled": True, "auto_reload": False},
            "logging": {"level": "INFO"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            # Validate YAML
            is_valid, errors = validate_yaml_config(config_path)
            assert is_valid is True

            # Check completeness
            completeness = check_config_completeness(config_path)
            assert completeness["is_valid"] is True

            # Get suggestions
            suggestions = suggest_config_improvements(config_path)
            assert isinstance(suggestions, list)

        finally:
            Path(config_path).unlink()

    def test_schema_validates_template(self):
        """Test that generated schema validates template."""
        template = get_config_template()
        generate_json_schema()

        # Template should be valid according to schema
        is_valid, errors = validate_config_dict(template)
        assert is_valid is True
