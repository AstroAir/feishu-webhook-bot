"""Tests for task templates."""

import pytest

from feishu_webhook_bot.core.config import (
    BotConfig,
)
from feishu_webhook_bot.tasks.templates import (
    TaskTemplateEngine,
    create_task_from_template_yaml,
)


@pytest.fixture
def mock_config():
    """Create a mock bot configuration with templates."""
    return BotConfig(
        webhooks=[
            {"name": "default", "url": "https://example.com/webhook"},
        ],
        task_templates=[
            {
                "name": "http_health_check",
                "description": "Template for HTTP health checks",
                "base_task": {
                    "name": "health_check_base",
                    "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                    "actions": [
                        {
                            "type": "http_request",
                            "request": {
                                "method": "GET",
                                "url": "${url}",
                                "timeout": 10,
                            },
                        },
                        {
                            "type": "send_message",
                            "webhook": "default",
                            "message": "Health check for ${service_name}: ${status}",
                        },
                    ],
                },
                "parameters": [
                    {"name": "url", "type": "string", "required": True},
                    {"name": "service_name", "type": "string", "required": True},
                    {
                        "name": "status",
                        "type": "string",
                        "required": False,
                        "default": "OK",
                    },
                ],
            },
            {
                "name": "notification_task",
                "description": "Template for sending notifications",
                "base_task": {
                    "name": "notification_base",
                    "schedule": {"mode": "interval", "arguments": {"hours": 1}},
                    "actions": [
                        {
                            "type": "send_message",
                            "webhooks": ["${webhook_name}"],
                            "message": "${message}",
                        }
                    ],
                },
                "parameters": [
                    {
                        "name": "webhook_name",
                        "type": "string",
                        "required": False,
                        "default": "default",
                    },
                    {"name": "message", "type": "string", "required": True},
                ],
            },
        ],
    )


@pytest.fixture
def template_engine(mock_config):
    """Create a template engine instance."""
    return TaskTemplateEngine(mock_config.task_templates)


class TestTemplateRetrieval:
    """Test template retrieval."""

    def test_get_existing_template(self, template_engine):
        """Test getting an existing template."""
        template = template_engine.get_template("http_health_check")

        assert template is not None
        assert template.name == "http_health_check"
        assert template.description == "Template for HTTP health checks"

    def test_get_nonexistent_template(self, template_engine):
        """Test getting a template that doesn't exist."""
        template = template_engine.get_template("nonexistent")

        assert template is None


class TestTemplateInstantiation:
    """Test template instantiation."""

    def test_create_task_from_template_with_all_params(self, template_engine):
        """Test creating a task from template with all parameters."""
        task = template_engine.create_task_from_template(
            template_name="http_health_check",
            task_name="api_health_check",
            overrides={
                "url": "https://api.example.com/health",
                "service_name": "API Service",
                "status": "Healthy",
            },
        )

        assert task is not None
        assert task.name == "api_health_check"
        assert len(task.actions) == 2

        # Check URL substitution
        http_action = task.actions[0]
        assert http_action.request.url == "https://api.example.com/health"

        # Check message substitution
        message_action = task.actions[1]
        assert "API Service" in message_action.message
        assert "Healthy" in message_action.message

    def test_create_task_with_default_params(self, template_engine):
        """Test creating a task using default parameter values."""
        task = template_engine.create_task_from_template(
            template_name="http_health_check",
            task_name="api_health_check",
            overrides={
                "url": "https://api.example.com/health",
                "service_name": "API Service",
                # status will use default value "OK"
            },
        )

        assert task is not None
        message_action = task.actions[1]
        assert "OK" in message_action.message

    def test_create_task_with_overrides(self, template_engine):
        """Test creating a task with overrides."""
        task = template_engine.create_task_from_template(
            template_name="notification_task",
            task_name="custom_notification",
            overrides={
                "message": "Custom message",
                "enabled": False,
                "priority": 10,
                "schedule": {"mode": "interval", "arguments": {"minutes": 30}},
            },
        )

        assert task is not None
        assert task.name == "custom_notification"
        assert task.enabled is False
        assert task.priority == 10
        assert task.schedule.arguments["minutes"] == 30

    def test_create_task_missing_required_param(self, template_engine):
        """Test creating a task without required parameters."""
        with pytest.raises(ValueError, match="required"):
            template_engine.create_task_from_template(
                template_name="http_health_check",
                task_name="api_health_check",
                overrides={
                    "url": "https://api.example.com/health",
                    # Missing required 'service_name'
                },
            )

    def test_create_task_from_nonexistent_template(self, template_engine):
        """Test creating a task from a template that doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            template_engine.create_task_from_template(
                template_name="nonexistent",
                task_name="test_task",
                overrides={},
            )


class TestParameterValidation:
    """Test parameter validation."""

    def test_validate_all_required_params_present(self, template_engine):
        """Test validation when all required parameters are present."""
        parameters = {
            "url": "https://api.example.com/health",
            "service_name": "API Service",
        }

        # Should not raise
        is_valid, errors = template_engine.validate_template_parameters(
            "http_health_check", parameters
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_missing_required_param(self, template_engine):
        """Test validation when required parameter is missing."""
        parameters = {
            "url": "https://api.example.com/health",
            # Missing 'service_name'
        }

        is_valid, errors = template_engine.validate_template_parameters(
            "http_health_check", parameters
        )
        assert not is_valid
        assert any("required" in error.lower() for error in errors)

    def test_validate_with_optional_params(self, template_engine):
        """Test validation with optional parameters."""
        parameters = {
            "url": "https://api.example.com/health",
            "service_name": "API Service",
            "status": "Custom Status",
        }

        # Should not raise
        is_valid, errors = template_engine.validate_template_parameters(
            "http_health_check", parameters
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_extra_params_allowed(self, template_engine):
        """Test that extra parameters are allowed."""
        parameters = {
            "url": "https://api.example.com/health",
            "service_name": "API Service",
            "extra_param": "extra_value",  # Not in template
        }

        # Should not raise - extra params are allowed
        is_valid, errors = template_engine.validate_template_parameters(
            "http_health_check", parameters
        )
        assert is_valid
        assert len(errors) == 0


class TestYAMLTemplateCreation:
    """Test YAML-based template creation."""

    def test_create_task_from_yaml_template(self, mock_config):
        """Test creating a task from YAML template definition."""
        template_config = {
            "name": "http_health_check",
            "description": "Template for HTTP health checks",
            "base_task": {
                "name": "health_check_base",
                "schedule": {"mode": "interval", "arguments": {"minutes": 5}},
                "actions": [
                    {
                        "type": "http_request",
                        "request": {
                            "method": "GET",
                            "url": "${url}",
                            "timeout": 10,
                        },
                    },
                    {
                        "type": "send_message",
                        "message": "Health check for ${service_name}: ${status}",
                    },
                ],
            },
            "parameters": [
                {"name": "url", "type": "string", "required": True},
                {"name": "service_name", "type": "string", "required": True},
                {
                    "name": "status",
                    "type": "string",
                    "required": False,
                    "default": "OK",
                },
            ],
        }

        task = create_task_from_template_yaml(
            template_config,
            "api_health_check",
            {
                "url": "https://api.example.com/health",
                "service_name": "API Service",
            },
        )

        assert task is not None
        assert task.name == "api_health_check"

    def test_create_task_from_yaml_with_overrides(self, mock_config):
        """Test creating a task from YAML with overrides."""
        template_config = {
            "name": "notification_task",
            "description": "Template for sending notifications",
            "base_task": {
                "name": "notification_base",
                "schedule": {"mode": "interval", "arguments": {"hours": 1}},
                "actions": [
                    {
                        "type": "send_message",
                        "message": "${message}",
                    }
                ],
            },
            "parameters": [
                {"name": "message", "type": "string", "required": True},
            ],
        }

        task = create_task_from_template_yaml(
            template_config,
            "hourly_notification",
            {"message": "Hourly update"},
        )

        assert task is not None
        assert task.name == "hourly_notification"


class TestParameterSubstitution:
    """Test parameter substitution in templates."""

    def test_substitution_in_string_fields(self, template_engine):
        """Test parameter substitution in string fields."""
        task = template_engine.create_task_from_template(
            template_name="notification_task",
            task_name="test_notification",
            overrides={
                "webhook_name": "alerts",
                "message": "Test alert message",
            },
        )

        assert task is not None
        action = task.actions[0]
        assert "alerts" in (action.webhooks or [])
        assert action.message == "Test alert message"

    def test_substitution_in_nested_fields(self, template_engine):
        """Test parameter substitution in nested fields."""
        task = template_engine.create_task_from_template(
            template_name="http_health_check",
            task_name="api_check",
            overrides={
                "url": "https://api.example.com/status",
                "service_name": "API",
            },
        )

        assert task is not None
        http_action = task.actions[0]
        assert http_action.request.url == "https://api.example.com/status"

    def test_multiple_substitutions_in_same_field(self, template_engine):
        """Test multiple parameter substitutions in the same field."""
        task = template_engine.create_task_from_template(
            template_name="http_health_check",
            task_name="api_check",
            overrides={
                "url": "https://api.example.com/health",
                "service_name": "API Service",
                "status": "OK",
            },
        )

        assert task is not None
        message_action = task.actions[1]
        # Message should contain both service_name and status
        assert "API Service" in message_action.message
        assert "OK" in message_action.message
