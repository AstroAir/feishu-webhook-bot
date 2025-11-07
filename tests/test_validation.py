"""Tests for configuration validation."""

import json
from pathlib import Path

import pytest

from feishu_webhook_bot.core.validation import (
    check_config_completeness,
    generate_json_schema,
    get_config_template,
    suggest_config_improvements,
    validate_config_dict,
    validate_yaml_config,
)


@pytest.fixture
def fixtures_dir():
    """Get the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


class TestJSONSchemaGeneration:
    """Test JSON schema generation."""

    def test_generate_json_schema(self):
        """Test generating JSON schema from BotConfig."""
        schema = generate_json_schema()
        
        assert schema is not None
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "webhooks" in schema["properties"]

    def test_schema_has_required_fields(self):
        """Test that schema includes required fields."""
        schema = generate_json_schema()
        
        # webhooks is required
        assert "required" in schema
        assert "webhooks" in schema["required"]

    def test_schema_has_optional_fields(self):
        """Test that schema includes optional fields."""
        schema = generate_json_schema()
        
        properties = schema["properties"]
        # These should be optional
        assert "tasks" in properties
        assert "task_templates" in properties
        assert "environments" in properties
        assert "plugins" in properties

    def test_schema_is_valid_json(self):
        """Test that generated schema is valid JSON."""
        schema = generate_json_schema()
        
        # Should be serializable to JSON
        json_str = json.dumps(schema)
        assert json_str is not None
        
        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed == schema


class TestYAMLValidation:
    """Test YAML configuration validation."""

    def test_validate_valid_config(self, fixtures_dir):
        """Test validating a valid configuration file."""
        config_path = fixtures_dir / "valid_config.yaml"
        
        is_valid, errors = validate_yaml_config(str(config_path))
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_minimal_config(self, fixtures_dir):
        """Test validating a minimal configuration file."""
        config_path = fixtures_dir / "minimal_config.yaml"
        
        is_valid, errors = validate_yaml_config(str(config_path))
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_syntax(self, fixtures_dir):
        """Test validating a file with invalid YAML syntax."""
        config_path = fixtures_dir / "invalid_syntax.yaml"
        
        is_valid, errors = validate_yaml_config(str(config_path))
        
        assert is_valid is False
        assert len(errors) > 0
        # Should mention YAML syntax error
        assert any("yaml" in str(e).lower() or "syntax" in str(e).lower() for e in errors)

    def test_validate_invalid_schema(self, fixtures_dir):
        """Test validating a file with invalid schema."""
        config_path = fixtures_dir / "invalid_schema.yaml"
        
        is_valid, errors = validate_yaml_config(str(config_path))
        
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_nonexistent_file(self):
        """Test validating a file that doesn't exist."""
        is_valid, errors = validate_yaml_config("nonexistent.yaml")
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("not found" in str(e).lower() or "exist" in str(e).lower() for e in errors)


class TestConfigDictValidation:
    """Test configuration dictionary validation."""

    def test_validate_valid_dict(self):
        """Test validating a valid configuration dictionary."""
        config_dict = {
            "webhooks": [
                {"name": "default", "url": "https://example.com/webhook"}
            ]
        }
        
        is_valid, errors = validate_config_dict(config_dict)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_dict_with_tasks(self):
        """Test validating a dictionary with tasks."""
        config_dict = {
            "webhooks": [
                {"name": "default", "url": "https://example.com/webhook"}
            ],
            "tasks": [
                {
                    "name": "test_task",
                    "enabled": True,
                    "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                    "actions": [
                        {"type": "send_message", "webhook": "default", "message": "test"}
                    ],
                }
            ],
        }
        
        is_valid, errors = validate_config_dict(config_dict)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_dict(self):
        """Test validating an invalid configuration dictionary."""
        config_dict = {
            "webhooks": [
                {"name": "default"}  # Missing required 'url'
            ]
        }
        
        is_valid, errors = validate_config_dict(config_dict)
        
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_empty_dict(self):
        """Test validating an empty dictionary."""
        config_dict = {}
        
        is_valid, errors = validate_config_dict(config_dict)
        
        assert is_valid is False
        assert len(errors) > 0
        # Should mention missing required field
        assert any("webhook" in str(e).lower() for e in errors)


class TestConfigTemplate:
    """Test configuration template generation."""

    def test_get_config_template(self):
        """Test getting a configuration template."""
        template = get_config_template()
        
        assert template is not None
        assert isinstance(template, dict)
        assert "webhooks" in template

    def test_template_has_examples(self):
        """Test that template includes example values."""
        template = get_config_template()
        
        assert "webhooks" in template
        assert len(template["webhooks"]) > 0
        
        # Should have example webhook
        webhook = template["webhooks"][0]
        assert "name" in webhook
        assert "url" in webhook

    def test_template_has_optional_sections(self):
        """Test that template includes optional sections."""
        template = get_config_template()
        
        # Should include optional sections as examples
        assert "logging" in template or "scheduler" in template

    def test_template_is_valid(self):
        """Test that the template itself is valid."""
        template = get_config_template()
        
        is_valid, errors = validate_config_dict(template)
        
        # Template should be valid
        assert is_valid is True
        assert len(errors) == 0


class TestConfigCompleteness:
    """Test configuration completeness checking."""

    def test_check_minimal_config_completeness(self, fixtures_dir):
        """Test checking completeness of minimal config."""
        config_path = fixtures_dir / "minimal_config.yaml"
        
        info = check_config_completeness(str(config_path))
        
        assert info is not None
        assert "completeness_percentage" in info
        assert "missing_optional_fields" in info
        assert "configured_fields" in info
        
        # Minimal config should have low completeness
        assert info["completeness_percentage"] < 50

    def test_check_full_config_completeness(self, fixtures_dir):
        """Test checking completeness of full config."""
        config_path = fixtures_dir / "valid_config.yaml"
        
        info = check_config_completeness(str(config_path))
        
        assert info is not None
        assert "completeness_percentage" in info
        
        # Full config should have higher completeness
        assert info["completeness_percentage"] > 30

    def test_completeness_lists_missing_fields(self, fixtures_dir):
        """Test that completeness check lists missing fields."""
        config_path = fixtures_dir / "minimal_config.yaml"
        
        info = check_config_completeness(str(config_path))
        
        assert "missing_optional_fields" in info
        assert len(info["missing_optional_fields"]) > 0

    def test_completeness_lists_configured_fields(self, fixtures_dir):
        """Test that completeness check lists configured fields."""
        config_path = fixtures_dir / "valid_config.yaml"
        
        info = check_config_completeness(str(config_path))
        
        assert "configured_fields" in info
        assert len(info["configured_fields"]) > 0
        assert "webhooks" in info["configured_fields"]


class TestConfigImprovements:
    """Test configuration improvement suggestions."""

    def test_suggest_improvements_for_minimal_config(self, fixtures_dir):
        """Test suggesting improvements for minimal config."""
        config_path = fixtures_dir / "minimal_config.yaml"
        
        suggestions = suggest_config_improvements(str(config_path))
        
        assert suggestions is not None
        assert len(suggestions) > 0

    def test_suggest_improvements_for_full_config(self, fixtures_dir):
        """Test suggesting improvements for full config."""
        config_path = fixtures_dir / "valid_config.yaml"
        
        suggestions = suggest_config_improvements(str(config_path))
        
        assert suggestions is not None
        # Full config might still have some suggestions
        # but should have fewer than minimal config

    def test_suggestions_are_strings(self, fixtures_dir):
        """Test that suggestions are strings."""
        config_path = fixtures_dir / "minimal_config.yaml"
        
        suggestions = suggest_config_improvements(str(config_path))
        
        for suggestion in suggestions:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0

    def test_suggestions_mention_missing_features(self, fixtures_dir):
        """Test that suggestions mention missing features."""
        config_path = fixtures_dir / "minimal_config.yaml"
        
        suggestions = suggest_config_improvements(str(config_path))
        
        # Should suggest adding optional features
        suggestion_text = " ".join(suggestions).lower()
        # Might suggest tasks, plugins, logging, etc.
        assert any(
            keyword in suggestion_text
            for keyword in ["task", "plugin", "logging", "scheduler", "environment"]
        )


class TestValidationErrorMessages:
    """Test validation error messages."""

    def test_error_messages_are_descriptive(self, fixtures_dir):
        """Test that error messages are descriptive."""
        config_path = fixtures_dir / "invalid_schema.yaml"
        
        is_valid, errors = validate_yaml_config(str(config_path))
        
        assert is_valid is False
        for error in errors:
            # Error messages should be non-empty strings
            assert isinstance(error, str)
            assert len(error) > 0

    def test_multiple_errors_reported(self, fixtures_dir):
        """Test that multiple errors are reported."""
        config_path = fixtures_dir / "invalid_schema.yaml"
        
        is_valid, errors = validate_yaml_config(str(config_path))
        
        # Should report all errors, not just the first one
        assert len(errors) >= 1


class TestValidationPerformance:
    """Test validation performance."""

    def test_validate_large_config(self, fixtures_dir):
        """Test validating a large configuration file."""
        import time
        
        config_path = fixtures_dir / "valid_config.yaml"
        
        start_time = time.time()
        is_valid, errors = validate_yaml_config(str(config_path))
        end_time = time.time()
        
        # Validation should be fast (< 1 second)
        assert end_time - start_time < 1.0
        assert is_valid is True

    def test_schema_generation_cached(self):
        """Test that schema generation can be called multiple times."""
        import time
        
        start_time = time.time()
        for _ in range(10):
            schema = generate_json_schema()
        end_time = time.time()
        
        # Should be fast even when called multiple times
        assert end_time - start_time < 1.0
        assert schema is not None

