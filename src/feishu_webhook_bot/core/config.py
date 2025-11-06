"""Configuration management for Feishu Webhook Bot.

This module provides configuration models and loading functionality using Pydantic
for validation and type safety.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebhookConfig(BaseModel):
    """Configuration for a Feishu webhook endpoint.

    Attributes:
        url: The webhook URL
        secret: Optional signing secret for secure webhooks
        name: Optional name for this webhook (for logging/identification)
    """

    url: str = Field(..., description="Feishu webhook URL")
    secret: str | None = Field(default=None, description="Webhook signing secret")
    name: str = Field(default="default", description="Webhook identifier name")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that the URL is not empty and looks like a webhook URL."""
        if not v or not v.strip():
            raise ValueError("Webhook URL cannot be empty")
        if not v.startswith("http"):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v.strip()


class SchedulerConfig(BaseModel):
    """Configuration for the APScheduler job scheduler.

    Attributes:
        enabled: Whether to enable the scheduler
        timezone: Timezone for scheduled jobs (e.g., 'Asia/Shanghai')
        job_store_type: Type of job store ('memory' or 'sqlite')
        job_store_path: Path to SQLite database (if job_store_type is 'sqlite')
    """

    enabled: bool = Field(default=True, description="Enable scheduler")
    timezone: str = Field(default="Asia/Shanghai", description="Timezone for jobs")
    job_store_type: str = Field(default="memory", description="Job store type")
    job_store_path: str | None = Field(
        default=None, description="Path to SQLite job store"
    )

    @field_validator("job_store_type")
    @classmethod
    def validate_job_store_type(cls, v: str) -> str:
        """Validate job store type."""
        if v not in ["memory", "sqlite"]:
            raise ValueError("job_store_type must be 'memory' or 'sqlite'")
        return v


class PluginConfig(BaseModel):
    """Configuration for the plugin system.

    Attributes:
        enabled: Whether to enable plugins
        plugin_dir: Directory containing plugin files
        auto_reload: Whether to automatically reload plugins on file changes
        reload_delay: Delay in seconds before reloading after file change
    """

    enabled: bool = Field(default=True, description="Enable plugin system")
    plugin_dir: str = Field(default="plugins", description="Plugin directory")
    auto_reload: bool = Field(default=True, description="Enable hot reload")
    reload_delay: float = Field(default=1.0, description="Reload delay in seconds")

    @field_validator("reload_delay")
    @classmethod
    def validate_reload_delay(cls, v: float) -> float:
        """Validate reload delay is positive."""
        if v <= 0:
            raise ValueError("reload_delay must be positive")
        return v


class LoggingConfig(BaseModel):
    """Configuration for logging.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log format string
        log_file: Path to log file (None for console only)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
    """

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )
    log_file: str | None = Field(default=None, description="Log file path")
    max_bytes: int = Field(default=10485760, description="Max log file size (10MB)")
    backup_count: int = Field(default=5, description="Number of backup files")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v_upper


class BotConfig(BaseSettings):
    """Main configuration for the Feishu Webhook Bot.

    This class uses Pydantic Settings to support loading from:
    - YAML/JSON configuration files
    - Environment variables
    - Default values

    Attributes:
        webhooks: List of webhook configurations
        scheduler: Scheduler configuration
        plugins: Plugin system configuration
        logging: Logging configuration
    """

    model_config = SettingsConfigDict(
        env_prefix="FEISHU_BOT_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    webhooks: list[WebhookConfig] = Field(
        default_factory=lambda: [
            WebhookConfig(url="https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL")
        ],
        description="List of webhook configurations",
    )
    scheduler: SchedulerConfig = Field(
        default_factory=SchedulerConfig, description="Scheduler configuration"
    )
    plugins: PluginConfig = Field(
        default_factory=PluginConfig, description="Plugin configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> BotConfig:
        """Load configuration from a YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            BotConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            try:
                config_data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in config file: {e}") from e

        if not config_data:
            config_data = {}

        return cls(**config_data)

    @classmethod
    def from_json(cls, path: str | Path) -> BotConfig:
        """Load configuration from a JSON file.

        Args:
            path: Path to JSON configuration file

        Returns:
            BotConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        import json

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            try:
                config_data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in config file: {e}") from e

        return cls(**config_data)

    def get_webhook(self, name: str = "default") -> WebhookConfig | None:
        """Get webhook configuration by name.

        Args:
            name: Name of the webhook to retrieve

        Returns:
            WebhookConfig if found, None otherwise
        """
        for webhook in self.webhooks:
            if webhook.name == name:
                return webhook
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return self.model_dump()
