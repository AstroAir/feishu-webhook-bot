"""Configuration management for Feishu Webhook Bot.

This module provides configuration models and loading functionality using Pydantic
for validation and type safety.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DOTENV_LOADED = False


def _load_env_once() -> None:
    """Load environment variables from a .env file exactly once."""

    global _DOTENV_LOADED
    if not _DOTENV_LOADED:
        load_dotenv()
        _DOTENV_LOADED = True


def _expand_env_vars(data: Any) -> Any:
    """Recursively expand environment variables in configuration data."""

    if isinstance(data, str):
        return os.path.expandvars(data)
    if isinstance(data, dict):
        return {key: _expand_env_vars(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_expand_env_vars(item) for item in data]
    return data


class RetryPolicyConfig(BaseModel):
    """Configuration for HTTP retry behaviour."""

    max_attempts: int = Field(
        default=3,
        ge=1,
        description="Maximum number of attempts (including the first request)",
    )
    backoff_seconds: float = Field(
        default=1.0,
        ge=0.0,
        description="Initial delay in seconds before retrying",
    )
    backoff_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        description="Multiplier applied to the backoff delay after each failure",
    )
    max_backoff_seconds: float = Field(
        default=30.0,
        ge=0.0,
        description="Maximum delay cap between retries",
    )


class HTTPRequestConfig(BaseModel):
    """Configuration for an outbound HTTP request within an automation workflow."""

    method: str = Field(default="GET", description="HTTP method")
    url: str = Field(..., description="Request URL")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Additional headers to include"
    )
    params: dict[str, Any] = Field(default_factory=dict, description="Querystring parameters")
    json_body: dict[str, Any] | None = Field(
        default=None, description="JSON payload to send with the request"
    )
    data_body: dict[str, Any] | None = Field(
        default=None, description="Form data payload to send with the request"
    )
    timeout: float | None = Field(
        default=None, ge=0.0, description="Override timeout for this request"
    )
    retry: RetryPolicyConfig | None = Field(default=None, description="Retry policy override")
    save_as: str | None = Field(
        default=None,
        description="Store JSON response (if any) under this key for later actions",
    )

    @field_validator("method")
    @classmethod
    def normalise_method(cls, value: str) -> str:
        method = (value or "GET").strip().upper()
        valid_methods = {
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
        }
        if method not in valid_methods:
            raise ValueError(f"Unsupported HTTP method: {method}")
        return method


class AutomationScheduleConfig(BaseModel):
    """Schedule configuration for automation triggers."""

    mode: Literal["interval", "cron"] = Field(
        default="interval", description="Scheduler trigger type"
    )
    arguments: dict[str, Any] = Field(default_factory=dict, description="Trigger keyword arguments")

    @model_validator(mode="after")
    def validate_arguments(self) -> AutomationScheduleConfig:
        if not self.arguments:
            raise ValueError("Schedule trigger requires at least one argument")
        return self


class AutomationEventFilterCondition(BaseModel):
    """Condition used to filter inbound events."""

    path: str = Field(..., description="Dot-separated path to a value inside the event payload")
    equals: Any | None = Field(
        default=None, description="Expected exact value at the provided path"
    )
    contains: str | None = Field(
        default=None, description="Substring that must be present in the value"
    )

    @model_validator(mode="after")
    def validate_condition(self) -> AutomationEventFilterCondition:
        if self.equals is None and self.contains is None:
            raise ValueError("Event filter requires 'equals' or 'contains'")
        return self


class AutomationEventTriggerConfig(BaseModel):
    """Configuration describing event-based automation triggers."""

    event_type: str | None = Field(
        default=None, description="Match against the event.header.event_type value"
    )
    conditions: list[AutomationEventFilterCondition] = Field(
        default_factory=list, description="Additional payload-based filters"
    )


class AutomationTriggerConfig(BaseModel):
    """Wrapper describing how an automation rule is triggered."""

    type: Literal["schedule", "event"] = Field(default="schedule", description="Trigger category")
    schedule: AutomationScheduleConfig | None = Field(
        default=None, description="Schedule trigger configuration"
    )
    event: AutomationEventTriggerConfig | None = Field(
        default=None, description="Event trigger configuration"
    )

    @model_validator(mode="after")
    def ensure_configuration(self) -> AutomationTriggerConfig:
        if self.type == "schedule" and self.schedule is None:
            raise ValueError("Schedule trigger selected but schedule config missing")
        if self.type == "event" and self.event is None:
            raise ValueError("Event trigger selected but event config missing")
        return self


class AutomationActionConfig(BaseModel):
    """Action executed when an automation rule fires."""

    type: Literal["send_text", "send_template", "http_request"] = Field(
        ..., description="Automation action type"
    )
    text: str | None = Field(default=None, description="Text payload to send")
    template: str | None = Field(
        default=None, description="Template name to render for this action"
    )
    webhooks: list[str] = Field(default_factory=list, description="Target webhook names")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context for this action"
    )
    request: HTTPRequestConfig | None = Field(
        default=None, description="HTTP request configuration for external calls"
    )

    @model_validator(mode="after")
    def validate_action(self) -> AutomationActionConfig:
        if self.type == "send_text" and not (self.text or self.template):
            raise ValueError("send_text action requires 'text' or 'template'")
        if self.type == "send_template" and not self.template:
            raise ValueError("send_template action requires a template name")
        if self.type == "http_request" and self.request is None:
            raise ValueError("http_request action requires request configuration")
        return self


class AutomationRule(BaseModel):
    """Declarative automation rule definition."""

    name: str = Field(..., description="Automation rule name")
    description: str | None = Field(default=None, description="Optional human-readable description")
    enabled: bool = Field(default=True, description="Whether the automation is active")
    trigger: AutomationTriggerConfig = Field(
        ..., description="Trigger configuration for the automation"
    )
    actions: list[AutomationActionConfig] = Field(
        default_factory=list, description="Actions executed when the rule fires"
    )
    default_webhooks: list[str] = Field(
        default_factory=list, description="Fallback webhook names for actions"
    )
    default_context: dict[str, Any] = Field(
        default_factory=dict, description="Context made available to all actions"
    )

    @model_validator(mode="after")
    def ensure_actions(self) -> AutomationRule:
        if not self.actions:
            raise ValueError("Automation rule must define at least one action")
        return self


class WebhookConfig(BaseModel):
    """Configuration for a Feishu webhook endpoint."""

    url: str = Field(..., description="Feishu webhook URL")
    secret: str | None = Field(default=None, description="Webhook signing secret")
    name: str = Field(default="default", description="Webhook identifier name")
    timeout: float | None = Field(
        default=None,
        ge=0.0,
        description="Override request timeout in seconds for this webhook",
    )
    retry: RetryPolicyConfig | None = Field(
        default=None, description="Retry policy overrides for this webhook"
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="Extra HTTP headers sent with requests"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Webhook URL cannot be empty")
        if not value.startswith("http"):
            raise ValueError("Webhook URL must start with http:// or https://")
        return value.strip()


class SchedulerConfig(BaseModel):
    """Configuration for the APScheduler job scheduler."""

    enabled: bool = Field(default=True, description="Enable scheduler")
    timezone: str = Field(default="Asia/Shanghai", description="Timezone for jobs")
    job_store_type: str = Field(default="memory", description="Job store type")
    job_store_path: str | None = Field(default=None, description="Path to SQLite job store")

    @field_validator("job_store_type")
    @classmethod
    def validate_job_store_type(cls, value: str) -> str:
        if value not in ["memory", "sqlite"]:
            raise ValueError("job_store_type must be 'memory' or 'sqlite'")
        return value


class PluginConfig(BaseModel):
    """Configuration for the plugin system."""

    enabled: bool = Field(default=True, description="Enable plugin system")
    plugin_dir: str = Field(default="plugins", description="Plugin directory")
    auto_reload: bool = Field(default=True, description="Enable hot reload")
    reload_delay: float = Field(default=1.0, description="Reload delay in seconds")

    @field_validator("reload_delay")
    @classmethod
    def validate_reload_delay(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("reload_delay must be positive")
        return value


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )
    log_file: str | None = Field(default=None, description="Log file path")
    max_bytes: int = Field(default=10485760, description="Max log file size (10MB)")
    backup_count: int = Field(default=5, description="Number of backup files")


class GeneralConfig(BaseModel):
    """General bot configuration."""

    name: str = Field(default="Feishu Bot", description="Bot name")
    description: str = Field(
        default="A bot for sending Feishu messages.", description="Bot description"
    )


class TemplateConfig(BaseModel):
    """Configuration for a message template."""

    name: str = Field(..., description="Template name")
    content: str = Field(..., description="Template content")
    type: str = Field(
        default="text",
        description="Template type (text, card, post, custom)",
    )
    engine: Literal["string", "format"] = Field(
        default="string", description="Rendering engine used for this template"
    )
    description: str | None = Field(default=None, description="Human-readable template description")


class NotificationConfig(BaseModel):
    """Configuration for a notification rule."""

    name: str = Field(..., description="Notification rule name")
    trigger: str = Field(..., description="Event that triggers the notification")
    conditions: list[str] = Field(default_factory=list, description="List of conditions")
    template: str = Field(..., description="Template to use for the notification")


class HTTPClientConfig(BaseModel):
    """Default HTTP client configuration."""

    timeout: float = Field(default=10.0, ge=0.0, description="Default HTTP timeout")
    retry: RetryPolicyConfig = Field(
        default_factory=RetryPolicyConfig,
        description="Global retry policy for webhook calls",
    )


class EventServerConfig(BaseModel):
    """Configuration for the optional Feishu event ingestion server."""

    enabled: bool = Field(default=False, description="Enable inbound event server")
    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=8000, description="Bind port")
    path: str = Field(default="/feishu/events", description="Event webhook path")
    verification_token: str | None = Field(
        default=None,
        description="Feishu verification token to validate inbound requests",
    )
    signature_secret: str | None = Field(
        default=None,
        description="Feishu encrypt/signature secret for verifying requests",
    )
    auto_start: bool = Field(
        default=True,
        description="Automatically start server when bot starts",
    )


class BotConfig(BaseSettings):
    """Main configuration for the Feishu Webhook Bot."""

    model_config = SettingsConfigDict(
        env_prefix="FEISHU_BOT_",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalise_env_lists(cls, data: Any) -> Any:
        """Convert environment-style indexed dicts into ordered lists."""

        if isinstance(data, dict):
            webhooks = data.get("webhooks")
            if isinstance(webhooks, dict):
                try:
                    items = sorted(webhooks.items(), key=lambda item: int(item[0]))
                except ValueError:
                    items = sorted(webhooks.items())
                data["webhooks"] = [entry for _, entry in items]
        return data

    webhooks: list[WebhookConfig] = Field(
        default_factory=lambda: [
            WebhookConfig(url="https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL")
        ],
        description="List of webhook configurations",
    )
    scheduler: SchedulerConfig = Field(
        default_factory=SchedulerConfig, description="Scheduler configuration"
    )
    plugins: PluginConfig = Field(default_factory=PluginConfig, description="Plugin configuration")
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    general: GeneralConfig = Field(
        default_factory=GeneralConfig, description="General configuration"
    )
    templates: list[TemplateConfig] = Field(
        default_factory=list, description="List of message templates"
    )
    notifications: list[NotificationConfig] = Field(
        default_factory=list, description="List of notification rules"
    )
    http: HTTPClientConfig = Field(
        default_factory=HTTPClientConfig, description="Default HTTP client settings"
    )
    automations: list[AutomationRule] = Field(default_factory=list, description="Automation rules")
    event_server: EventServerConfig = Field(
        default_factory=EventServerConfig, description="Inbound event server settings"
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> BotConfig:
        """Load configuration from a YAML file."""

        _load_env_once()
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, encoding="utf-8") as handle:
            try:
                config_data = yaml.safe_load(handle)
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid YAML in config file: {exc}") from exc

        if not config_data:
            config_data = {}

        config_data = _expand_env_vars(config_data)
        return cls(**config_data)

    @classmethod
    def from_json(cls, path: str | Path) -> BotConfig:
        """Load configuration from a JSON file."""

        import json

        _load_env_once()
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, encoding="utf-8") as handle:
            try:
                config_data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in config file: {exc}") from exc

        config_data = _expand_env_vars(config_data)
        return cls(**config_data)

    def get_webhook(self, name: str = "default") -> WebhookConfig | None:
        """Get webhook configuration by name."""

        for webhook in self.webhooks:
            if webhook.name == name:
                return webhook
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""

        return self.model_dump()
