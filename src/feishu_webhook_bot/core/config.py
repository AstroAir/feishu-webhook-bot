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


class TaskConditionConfig(BaseModel):
    """Condition that must be met for a task to execute."""

    type: Literal["time_range", "day_of_week", "environment", "custom"] = Field(
        ..., description="Type of condition"
    )
    start_time: str | None = Field(default=None, description="Start time for time_range (HH:MM)")
    end_time: str | None = Field(default=None, description="End time for time_range (HH:MM)")
    days: list[str] | None = Field(
        default=None, description="Days of week for day_of_week condition"
    )
    environment: str | None = Field(
        default=None, description="Required environment name for environment condition"
    )
    expression: str | None = Field(
        default=None, description="Custom Python expression for custom condition"
    )


class TaskErrorHandlingConfig(BaseModel):
    """Error handling configuration for tasks."""

    retry_on_failure: bool = Field(default=True, description="Whether to retry on failure")
    max_retries: int = Field(default=3, ge=0, description="Maximum number of retries")
    retry_delay: float = Field(default=60.0, ge=0.0, description="Delay between retries in seconds")
    on_failure_action: Literal["log", "notify", "disable", "ignore"] = Field(
        default="log", description="Action to take on failure"
    )
    notification_webhook: str | None = Field(
        default=None, description="Webhook to notify on failure"
    )


class TaskParameterConfig(BaseModel):
    """Parameter definition for a task."""

    name: str = Field(..., description="Parameter name")
    type: Literal["string", "int", "float", "bool", "list", "dict"] = Field(
        default="string", description="Parameter type"
    )
    default: Any | None = Field(default=None, description="Default value")
    required: bool = Field(default=False, description="Whether parameter is required")
    description: str | None = Field(default=None, description="Parameter description")


class TaskActionConfig(BaseModel):
    """Action to be executed as part of a task."""

    type: Literal["plugin_method", "send_message", "http_request", "python_code"] = Field(
        ..., description="Type of action to execute"
    )
    plugin_name: str | None = Field(default=None, description="Plugin name for plugin_method")
    method_name: str | None = Field(default=None, description="Method name for plugin_method")
    message: str | None = Field(default=None, description="Message for send_message")
    template: str | None = Field(default=None, description="Template name for send_message")
    request: HTTPRequestConfig | None = Field(
        default=None, description="HTTP request config for http_request"
    )
    code: str | None = Field(default=None, description="Python code for python_code action")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Parameters to pass to the action"
    )
    webhooks: list[str] = Field(default_factory=list, description="Target webhooks")


class TaskDefinitionConfig(BaseModel):
    """Configuration for an automated task."""

    name: str = Field(..., description="Unique task name")
    description: str | None = Field(default=None, description="Task description")
    enabled: bool = Field(default=True, description="Whether task is enabled")

    # Scheduling
    schedule: AutomationScheduleConfig | None = Field(
        default=None, description="Schedule configuration"
    )
    cron: str | None = Field(default=None, description="Cron expression (alternative to schedule)")
    interval: dict[str, Any] | None = Field(
        default=None, description="Interval configuration (alternative to schedule)"
    )

    # Dependencies
    depends_on: list[str] = Field(
        default_factory=list, description="List of task names this task depends on"
    )
    run_after: list[str] = Field(
        default_factory=list, description="Tasks that must complete before this one"
    )

    # Parameters and conditions
    parameters: list[TaskParameterConfig] = Field(
        default_factory=list, description="Task parameters"
    )
    conditions: list[TaskConditionConfig] = Field(
        default_factory=list, description="Conditions for task execution"
    )

    # Actions
    actions: list[TaskActionConfig] = Field(
        default_factory=list, description="Actions to execute"
    )

    # Error handling
    error_handling: TaskErrorHandlingConfig = Field(
        default_factory=TaskErrorHandlingConfig, description="Error handling configuration"
    )

    # Execution settings
    timeout: float | None = Field(default=None, ge=0.0, description="Task timeout in seconds")
    priority: int = Field(default=100, description="Task priority (lower runs first)")
    max_concurrent: int = Field(
        default=1, ge=1, description="Maximum concurrent executions"
    )

    # Context
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context for task execution"
    )

    @model_validator(mode="after")
    def validate_schedule(self) -> TaskDefinitionConfig:
        """Ensure at least one scheduling method is defined."""
        if not any([self.schedule, self.cron, self.interval]):
            raise ValueError("Task must define schedule, cron, or interval")
        return self

    @model_validator(mode="after")
    def validate_actions(self) -> TaskDefinitionConfig:
        """Ensure at least one action is defined."""
        if not self.actions:
            raise ValueError("Task must define at least one action")
        return self


class TaskTemplateConfig(BaseModel):
    """Reusable task template definition."""

    name: str = Field(..., description="Template name")
    description: str | None = Field(default=None, description="Template description")
    base_task: TaskDefinitionConfig = Field(..., description="Base task configuration")
    parameters: list[TaskParameterConfig] = Field(
        default_factory=list, description="Template parameters that can be overridden"
    )


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


class PluginSettingsConfig(BaseModel):
    """Plugin-specific settings that can be configured in YAML."""

    plugin_name: str = Field(..., description="Name of the plugin these settings apply to")
    enabled: bool = Field(default=True, description="Whether this plugin is enabled")
    settings: dict[str, Any] = Field(
        default_factory=dict, description="Plugin-specific configuration parameters"
    )
    priority: int = Field(
        default=100, description="Plugin loading priority (lower numbers load first)"
    )


class PluginConfig(BaseModel):
    """Configuration for the plugin system."""

    enabled: bool = Field(default=True, description="Enable plugin system")
    plugin_dir: str = Field(default="plugins", description="Plugin directory")
    auto_reload: bool = Field(default=True, description="Enable hot reload")
    reload_delay: float = Field(default=1.0, description="Reload delay in seconds")
    plugin_settings: list[PluginSettingsConfig] = Field(
        default_factory=list, description="Per-plugin configuration settings"
    )

    @field_validator("reload_delay")
    @classmethod
    def validate_reload_delay(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("reload_delay must be positive")
        return value

    def get_plugin_settings(self, plugin_name: str) -> dict[str, Any]:
        """Get settings for a specific plugin."""
        for plugin_setting in self.plugin_settings:
            if plugin_setting.plugin_name == plugin_name:
                return plugin_setting.settings
        return {}


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


class AuthConfig(BaseModel):
    """Configuration for authentication system."""

    enabled: bool = Field(default=False, description="Enable authentication system")
    database_url: str = Field(
        default="sqlite:///./auth.db",
        description="Database URL for user storage (SQLAlchemy format)",
    )
    jwt_secret_key: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for JWT token signing (MUST be changed in production)",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration time in minutes"
    )
    max_failed_attempts: int = Field(
        default=5, description="Maximum failed login attempts before account lockout"
    )
    lockout_duration_minutes: int = Field(
        default=30, description="Account lockout duration in minutes"
    )
    require_email_verification: bool = Field(
        default=False, description="Require email verification for new accounts"
    )


class EnvironmentVariableConfig(BaseModel):
    """Environment variable definition."""

    name: str = Field(..., description="Variable name")
    value: Any = Field(..., description="Variable value")
    description: str | None = Field(default=None, description="Variable description")


class EnvironmentConfig(BaseModel):
    """Environment-specific configuration."""

    name: str = Field(..., description="Environment name (e.g., dev, staging, production)")
    description: str | None = Field(default=None, description="Environment description")
    variables: list[EnvironmentVariableConfig] = Field(
        default_factory=list, description="Environment-specific variables"
    )
    overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration overrides for this environment (can override any config field)",
    )
    enabled: bool = Field(default=True, description="Whether this environment is active")


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
    auth: AuthConfig = Field(
        default_factory=AuthConfig, description="Authentication system settings"
    )

    # New enhanced configuration sections
    tasks: list[TaskDefinitionConfig] = Field(
        default_factory=list, description="Automated task definitions"
    )
    task_templates: list[TaskTemplateConfig] = Field(
        default_factory=list, description="Reusable task templates"
    )
    environments: list[EnvironmentConfig] = Field(
        default_factory=list, description="Environment-specific configurations"
    )
    active_environment: str | None = Field(
        default=None, description="Currently active environment name"
    )
    config_hot_reload: bool = Field(
        default=False, description="Enable hot-reloading of configuration changes"
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

    def get_task(self, name: str) -> TaskDefinitionConfig | None:
        """Get task configuration by name."""
        for task in self.tasks:
            if task.name == name:
                return task
        return None

    def get_task_template(self, name: str) -> TaskTemplateConfig | None:
        """Get task template by name."""
        for template in self.task_templates:
            if template.name == name:
                return template
        return None

    def get_environment(self, name: str | None = None) -> EnvironmentConfig | None:
        """Get environment configuration by name, or active environment if name is None."""
        env_name = name or self.active_environment
        if not env_name:
            return None
        for env in self.environments:
            if env.name == env_name and env.enabled:
                return env
        return None

    def apply_environment_overrides(self, environment_name: str | None = None) -> BotConfig:
        """Apply environment-specific overrides to configuration.

        Args:
            environment_name: Name of environment to apply. If None, uses active_environment.

        Returns a new BotConfig instance with environment overrides applied.
        """
        env_name = environment_name or self.active_environment
        if not env_name:
            return self

        env = self.get_environment(env_name)
        if not env or not env.overrides:
            return self

        # Create a copy of the current config as dict
        config_dict = self.model_dump()

        # Apply overrides recursively
        def apply_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> None:
            for key, value in overrides.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    apply_overrides(base[key], value)
                else:
                    base[key] = value

        apply_overrides(config_dict, env.overrides)

        # Create new config instance with overrides
        return BotConfig(**config_dict)

    def get_environment_variables(self, environment_name: str | None = None) -> dict[str, Any]:
        """Get all environment variables from specified or active environment.

        Args:
            environment_name: Name of environment to get variables from. If None, uses active_environment.
        """
        env = self.get_environment(environment_name)
        if not env:
            return {}
        return {var.name: var.value for var in env.variables}

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""

        return self.model_dump()
