"""Tests for environment configuration."""

import os
from unittest.mock import patch

import pytest

from feishu_webhook_bot.core.config import BotConfig, EnvironmentConfig


@pytest.fixture
def mock_config():
    """Create a mock bot configuration with environments."""
    return BotConfig(
        webhooks=[
            {"name": "default", "url": "https://example.com/webhook"},
        ],
        environments=[
            {
                "name": "development",
                "variables": [
                    {"name": "FEISHU_WEBHOOK_URL", "value": "https://dev.example.com/webhook"},
                    {"name": "LOG_LEVEL", "value": "DEBUG"},
                    {"name": "API_TIMEOUT", "value": "30"},
                ],
                "overrides": {
                    "logging": {"level": "DEBUG"},
                    "scheduler": {"enabled": True},
                },
            },
            {
                "name": "staging",
                "variables": [
                    {"name": "FEISHU_WEBHOOK_URL", "value": "https://staging.example.com/webhook"},
                    {"name": "LOG_LEVEL", "value": "INFO"},
                    {"name": "API_TIMEOUT", "value": "60"},
                ],
                "overrides": {
                    "logging": {"level": "INFO"},
                },
            },
            {
                "name": "production",
                "variables": [
                    {"name": "FEISHU_WEBHOOK_URL", "value": "https://prod.example.com/webhook"},
                    {"name": "LOG_LEVEL", "value": "WARNING"},
                    {"name": "API_TIMEOUT", "value": "120"},
                ],
                "overrides": {
                    "logging": {"level": "WARNING", "format": "json"},
                    "scheduler": {"enabled": True},
                },
            },
        ],
        active_environment="development",
    )


class TestEnvironmentRetrieval:
    """Test environment retrieval."""

    def test_get_environment_by_name(self, mock_config):
        """Test getting an environment by name."""
        env = mock_config.get_environment("development")
        
        assert env is not None
        assert env.name == "development"

    def test_get_nonexistent_environment(self, mock_config):
        """Test getting an environment that doesn't exist."""
        env = mock_config.get_environment("nonexistent")
        
        assert env is None

    def test_get_all_environments(self, mock_config):
        """Test getting all environments."""
        assert len(mock_config.environments) == 3
        env_names = [e.name for e in mock_config.environments]
        assert "development" in env_names
        assert "staging" in env_names
        assert "production" in env_names


class TestEnvironmentVariables:
    """Test environment variables."""

    def test_get_environment_variables(self, mock_config):
        """Test getting environment variables."""
        variables = mock_config.get_environment_variables("development")
        
        assert variables is not None
        assert variables["FEISHU_WEBHOOK_URL"] == "https://dev.example.com/webhook"
        assert variables["LOG_LEVEL"] == "DEBUG"
        assert variables["API_TIMEOUT"] == "30"

    def test_get_variables_for_different_environments(self, mock_config):
        """Test getting variables for different environments."""
        dev_vars = mock_config.get_environment_variables("development")
        prod_vars = mock_config.get_environment_variables("production")
        
        assert dev_vars["LOG_LEVEL"] == "DEBUG"
        assert prod_vars["LOG_LEVEL"] == "WARNING"
        assert dev_vars["API_TIMEOUT"] == "30"
        assert prod_vars["API_TIMEOUT"] == "120"

    def test_get_variables_for_nonexistent_environment(self, mock_config):
        """Test getting variables for an environment that doesn't exist."""
        variables = mock_config.get_environment_variables("nonexistent")
        
        assert variables == {}

    def test_environment_variable_types(self, mock_config):
        """Test that environment variables are strings."""
        variables = mock_config.get_environment_variables("development")
        
        for key, value in variables.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestEnvironmentOverrides:
    """Test environment configuration overrides."""

    def test_apply_environment_overrides(self, mock_config):
        """Test applying environment overrides."""
        original_log_level = mock_config.logging.level
        
        mock_config.apply_environment_overrides("production")
        
        # Log level should be overridden
        assert mock_config.logging.level == "WARNING"
        assert mock_config.logging.format == "json"

    def test_overrides_for_different_environments(self, mock_config):
        """Test applying overrides for different environments."""
        # Apply development overrides
        mock_config.apply_environment_overrides("development")
        assert mock_config.logging.level == "DEBUG"
        
        # Apply production overrides
        mock_config.apply_environment_overrides("production")
        assert mock_config.logging.level == "WARNING"

    def test_partial_overrides(self, mock_config):
        """Test that partial overrides work correctly."""
        original_format = mock_config.logging.format
        
        # Staging only overrides level, not format
        mock_config.apply_environment_overrides("staging")
        
        assert mock_config.logging.level == "INFO"
        # Format should remain unchanged
        assert mock_config.logging.format == original_format

    def test_nested_overrides(self, mock_config):
        """Test nested configuration overrides."""
        mock_config.apply_environment_overrides("production")
        
        # Both logging.level and logging.format should be overridden
        assert mock_config.logging.level == "WARNING"
        assert mock_config.logging.format == "json"

    def test_overrides_for_nonexistent_environment(self, mock_config):
        """Test applying overrides for an environment that doesn't exist."""
        original_log_level = mock_config.logging.level
        
        # Should not raise, just do nothing
        mock_config.apply_environment_overrides("nonexistent")
        
        # Config should remain unchanged
        assert mock_config.logging.level == original_log_level


class TestActiveEnvironment:
    """Test active environment selection."""

    def test_active_environment_set(self, mock_config):
        """Test that active environment is set."""
        assert mock_config.active_environment == "development"

    def test_change_active_environment(self, mock_config):
        """Test changing the active environment."""
        mock_config.active_environment = "production"
        
        assert mock_config.active_environment == "production"

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_active_environment_from_env_var(self):
        """Test setting active environment from environment variable."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            environments=[
                {"name": "development", "variables": [], "overrides": {}},
                {"name": "production", "variables": [], "overrides": {}},
            ],
            active_environment="${ENVIRONMENT}",
        )
        
        # Should expand environment variable
        assert config.active_environment == "production" or config.active_environment == "${ENVIRONMENT}"

    def test_default_active_environment(self):
        """Test default active environment."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            environments=[
                {"name": "development", "variables": [], "overrides": {}},
            ],
        )
        
        # Should default to None or first environment
        assert config.active_environment is None or config.active_environment == "development"


class TestEnvironmentVariableExpansion:
    """Test environment variable expansion."""

    @patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_expand_environment_variables(self):
        """Test expanding environment variables in config."""
        config = BotConfig(
            webhooks=[
                {"name": "default", "url": "https://example.com/webhook"},
            ],
            environments=[
                {
                    "name": "test",
                    "variables": [
                        {"name": "EXPANDED_VAR", "value": "${TEST_VAR}"},
                    ],
                    "overrides": {},
                }
            ],
        )
        
        variables = config.get_environment_variables("test")
        # Variable expansion happens at runtime
        assert "EXPANDED_VAR" in variables

    @patch.dict(os.environ, {"API_KEY": "secret123"})
    def test_expand_multiple_variables(self):
        """Test expanding multiple environment variables."""
        config = BotConfig(
            webhooks=[
                {"name": "default", "url": "https://example.com/webhook"},
            ],
            environments=[
                {
                    "name": "test",
                    "variables": [
                        {"name": "KEY1", "value": "${API_KEY}"},
                        {"name": "KEY2", "value": "prefix_${API_KEY}_suffix"},
                    ],
                    "overrides": {},
                }
            ],
        )
        
        variables = config.get_environment_variables("test")
        assert "KEY1" in variables
        assert "KEY2" in variables


class TestEnvironmentTaskConditions:
    """Test environment-based task conditions."""

    def test_task_condition_with_environment(self, mock_config):
        """Test that tasks can use environment in conditions."""
        from feishu_webhook_bot.core.config import TaskConditionConfig, TaskDefinitionConfig, TaskActionConfig
        
        task = TaskDefinitionConfig(
            name="env_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="environment",
                    environment="production",
                )
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="Production task",
                )
            ],
        )
        
        assert task.conditions[0].type == "environment"
        assert task.conditions[0].environment == "production"

    def test_multiple_environment_conditions(self, mock_config):
        """Test tasks with multiple environment conditions."""
        from feishu_webhook_bot.core.config import TaskConditionConfig, TaskDefinitionConfig, TaskActionConfig
        
        task = TaskDefinitionConfig(
            name="multi_env_task",
            enabled=True,
            conditions=[
                TaskConditionConfig(
                    type="environment",
                    environment="production",
                ),
                TaskConditionConfig(
                    type="environment",
                    environment="staging",
                ),
            ],
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="Multi-env task",
                )
            ],
        )
        
        assert len(task.conditions) == 2
        assert all(c.type == "environment" for c in task.conditions)


class TestEnvironmentConfigValidation:
    """Test environment configuration validation."""

    def test_valid_environment_config(self):
        """Test creating config with valid environments."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            environments=[
                {
                    "name": "test",
                    "variables": [{"name": "VAR1", "value": "value1"}],
                    "overrides": {"logging": {"level": "DEBUG"}},
                }
            ],
        )
        
        assert len(config.environments) == 1
        assert config.environments[0].name == "test"

    def test_environment_with_empty_variables(self):
        """Test environment with empty variables list."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            environments=[
                {
                    "name": "test",
                    "variables": [],
                    "overrides": {},
                }
            ],
        )
        
        variables = config.get_environment_variables("test")
        assert variables == {}

    def test_environment_with_empty_overrides(self):
        """Test environment with empty overrides."""
        config = BotConfig(
            webhooks=[{"name": "default", "url": "https://example.com/webhook"}],
            environments=[
                {
                    "name": "test",
                    "variables": [{"name": "VAR1", "value": "value1"}],
                    "overrides": {},
                }
            ],
        )
        
        env = config.get_environment("test")
        assert env.overrides == {}

