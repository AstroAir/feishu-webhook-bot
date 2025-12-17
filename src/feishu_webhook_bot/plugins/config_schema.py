"""Plugin configuration schema framework.

This module provides a framework for defining plugin configuration schemas
using Pydantic models with extended metadata support.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, get_type_hints

from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo


class FieldType(str, Enum):
    """Supported configuration field types."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"
    SECRET = "secret"  # Sensitive field, masked in logs/output
    URL = "url"  # URL validation
    PATH = "path"  # File path validation
    EMAIL = "email"  # Email validation
    CHOICE = "choice"  # Enum/choice field
    DATETIME = "datetime"  # Date/time field


@dataclass
class PluginConfigField:
    """Definition of a single plugin configuration field.

    Attributes:
        name: Field name (key in configuration)
        field_type: Type of the field value
        description: Human-readable description
        required: Whether the field is required
        default: Default value if not provided
        sensitive: Whether the field contains sensitive data (e.g., API keys)
        env_var: Environment variable to use as fallback
        example: Example value for documentation
        choices: Valid choices for CHOICE type fields
        validator: Custom validation function
        depends_on: Name of field this depends on (conditional field)
        min_value: Minimum value for numeric fields
        max_value: Maximum value for numeric fields
        pattern: Regex pattern for STRING fields
        help_url: URL to documentation for this field
    """

    name: str
    field_type: FieldType
    description: str
    required: bool = True
    default: Any = None
    sensitive: bool = False
    env_var: str | None = None
    example: str | None = None
    choices: list[Any] | None = None
    validator: Callable[[Any], bool] | None = None
    depends_on: str | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    pattern: str | None = None
    help_url: str | None = None

    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate a value against this field's constraints.

        Args:
            value: The value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            if self.required:
                return False, f"Field '{self.name}' is required"
            return True, ""

        # Type validation
        if self.field_type == FieldType.INT:
            if not isinstance(value, int) or isinstance(value, bool):
                return False, f"Field '{self.name}' must be an integer"
            if self.min_value is not None and value < self.min_value:
                return False, f"Field '{self.name}' must be >= {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Field '{self.name}' must be <= {self.max_value}"

        elif self.field_type == FieldType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False, f"Field '{self.name}' must be a number"
            if self.min_value is not None and value < self.min_value:
                return False, f"Field '{self.name}' must be >= {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Field '{self.name}' must be <= {self.max_value}"

        elif self.field_type == FieldType.BOOL:
            if not isinstance(value, bool):
                return False, f"Field '{self.name}' must be a boolean"

        elif self.field_type == FieldType.LIST:
            if not isinstance(value, list):
                return False, f"Field '{self.name}' must be a list"

        elif self.field_type == FieldType.DICT:
            if not isinstance(value, dict):
                return False, f"Field '{self.name}' must be a dictionary"

        elif self.field_type in (FieldType.STRING, FieldType.SECRET):
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be a string"
            if self.pattern and not re.match(self.pattern, value):
                return False, f"Field '{self.name}' must match pattern: {self.pattern}"

        elif self.field_type == FieldType.URL:
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be a string"
            if not re.match(r"^https?://", value):
                return False, f"Field '{self.name}' must be a valid URL"

        elif self.field_type == FieldType.EMAIL:
            if not isinstance(value, str):
                return False, f"Field '{self.name}' must be a string"
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", value):
                return False, f"Field '{self.name}' must be a valid email"

        elif self.field_type == FieldType.CHOICE:
            if self.choices and value not in self.choices:
                return False, f"Field '{self.name}' must be one of: {self.choices}"

        # Custom validator
        if self.validator:
            try:
                if not self.validator(value):
                    return False, f"Field '{self.name}' failed custom validation"
            except Exception as e:
                return False, f"Field '{self.name}' validation error: {e}"

        return True, ""


class PluginConfigSchema(BaseModel):
    """Base class for plugin configuration schemas.

    Plugins can define their configuration schema by subclassing this class
    and defining Pydantic fields with extended metadata.

    Example:
        ```python
        from pydantic import Field
        from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema

        class MyPluginConfig(PluginConfigSchema):
            api_key: str = Field(
                ...,
                description="API key for the service",
                json_schema_extra={"sensitive": True, "env_var": "MY_API_KEY"}
            )
            timeout: int = Field(
                default=30,
                description="Request timeout in seconds",
                ge=1,
                le=300
            )
        ```
    """

    # Class-level metadata
    _plugin_name: ClassVar[str] = ""
    _field_groups: ClassVar[dict[str, list[str]]] = {}

    @classmethod
    def get_schema_fields(cls) -> dict[str, PluginConfigField]:
        """Get all defined configuration fields.

        Returns:
            Dictionary mapping field names to PluginConfigField instances
        """
        fields: dict[str, PluginConfigField] = {}

        for field_name, field_info in cls.model_fields.items():
            fields[field_name] = cls._field_info_to_config_field(field_name, field_info)

        return fields

    @classmethod
    def _field_info_to_config_field(
        cls, field_name: str, field_info: FieldInfo
    ) -> PluginConfigField:
        """Convert a Pydantic FieldInfo to PluginConfigField.

        Args:
            field_name: Name of the field
            field_info: Pydantic field info

        Returns:
            PluginConfigField instance
        """
        # Get type hints for the class
        hints = get_type_hints(cls)
        field_type_hint = hints.get(field_name, str)

        # Determine field type
        field_type = cls._infer_field_type(field_type_hint, field_info)

        # Extract metadata from json_schema_extra
        extra = field_info.json_schema_extra or {}
        if callable(extra):
            extra = {}

        # Determine if required
        required = field_info.is_required()

        # Get default value
        default = None if field_info.default is PydanticUndefined else field_info.default
        if field_info.default_factory is not None:
            try:
                default = field_info.default_factory()
            except Exception:
                default = None

        return PluginConfigField(
            name=field_name,
            field_type=field_type,
            description=field_info.description or "",
            required=required,
            default=default,
            sensitive=extra.get("sensitive", False),
            env_var=extra.get("env_var"),
            example=extra.get("example"),
            choices=extra.get("choices"),
            depends_on=extra.get("depends_on"),
            min_value=getattr(field_info, "ge", None) or getattr(field_info, "gt", None),
            max_value=getattr(field_info, "le", None) or getattr(field_info, "lt", None),
            pattern=getattr(field_info, "pattern", None),
            help_url=extra.get("help_url"),
        )

    @classmethod
    def _infer_field_type(cls, type_hint: type, field_info: FieldInfo) -> FieldType:
        """Infer FieldType from Python type hint.

        Args:
            type_hint: Python type annotation
            field_info: Pydantic field info for additional context

        Returns:
            Inferred FieldType
        """
        extra = field_info.json_schema_extra or {}
        if callable(extra):
            extra = {}

        # Check for explicit type in extra
        if "field_type" in extra:
            return FieldType(extra["field_type"])

        # Check for sensitive flag
        if extra.get("sensitive"):
            return FieldType.SECRET

        # Get origin type for generics
        origin = getattr(type_hint, "__origin__", None)

        if origin is list:
            return FieldType.LIST
        if origin is dict:
            return FieldType.DICT

        # Handle basic types
        if type_hint is bool:
            return FieldType.BOOL
        if type_hint is int:
            return FieldType.INT
        if type_hint is float:
            return FieldType.FLOAT
        if type_hint is str:
            return FieldType.STRING

        # Default to string
        return FieldType.STRING

    @classmethod
    def get_required_fields(cls) -> list[PluginConfigField]:
        """Get only required fields.

        Returns:
            List of required PluginConfigField instances
        """
        return [f for f in cls.get_schema_fields().values() if f.required]

    @classmethod
    def get_optional_fields(cls) -> list[PluginConfigField]:
        """Get only optional fields.

        Returns:
            List of optional PluginConfigField instances
        """
        return [f for f in cls.get_schema_fields().values() if not f.required]

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a configuration dictionary.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors: list[str] = []

        # Try Pydantic validation first
        try:
            cls.model_validate(config)
        except ValidationError as e:
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{field_path}: {error['msg']}")

        # Additional field-level validation
        fields = cls.get_schema_fields()
        for field_name, field_def in fields.items():
            value = config.get(field_name, field_def.default)
            is_valid, error_msg = field_def.validate_value(value)
            if not is_valid and error_msg not in errors:
                errors.append(error_msg)

        return len(errors) == 0, errors

    @classmethod
    def get_missing_required(cls, config: dict[str, Any]) -> list[PluginConfigField]:
        """Get list of missing required fields.

        Args:
            config: Configuration dictionary to check

        Returns:
            List of PluginConfigField instances that are required but not in config
        """
        missing = []
        for field_def in cls.get_required_fields():
            if field_def.name not in config or config[field_def.name] is None:
                missing.append(field_def)
        return missing

    @classmethod
    def generate_template(cls) -> dict[str, Any]:
        """Generate a configuration template with defaults.

        Returns:
            Dictionary with all fields populated with defaults or example values
        """
        template: dict[str, Any] = {}
        for field_name, field_def in cls.get_schema_fields().items():
            if field_def.default is not None:
                template[field_name] = field_def.default
            elif field_def.example is not None:
                template[field_name] = field_def.example
            elif field_def.field_type == FieldType.BOOL:
                template[field_name] = False
            elif field_def.field_type == FieldType.INT:
                template[field_name] = 0
            elif field_def.field_type == FieldType.FLOAT:
                template[field_name] = 0.0
            elif field_def.field_type == FieldType.LIST:
                template[field_name] = []
            elif field_def.field_type == FieldType.DICT:
                template[field_name] = {}
            elif field_def.field_type == FieldType.CHOICE and field_def.choices:
                template[field_name] = field_def.choices[0]
            else:
                template[field_name] = ""
        return template

    @classmethod
    def get_field_groups(cls) -> dict[str, list[str]]:
        """Get field groups for UI organization.

        Returns:
            Dictionary mapping group names to lists of field names
        """
        if cls._field_groups:
            return cls._field_groups

        # Default: all fields in one group
        return {"General": list(cls.get_schema_fields().keys())}


# Sentinel for missing default
class _MissingSentinel:
    pass


_MISSING = _MissingSentinel()


@dataclass
class ConfigSchemaBuilder:
    """Fluent builder for creating plugin configuration schemas.

    Provides a programmatic way to define configuration schemas without
    subclassing PluginConfigSchema.

    There are two ways to use this builder:

    1. Simple mode (for use in get_schema_fields overrides):
        ```python
        def get_schema_fields(cls) -> dict[str, PluginConfigField]:
            builder = ConfigSchemaBuilder()
            builder.add_field("api_key", FieldType.SECRET, "API key", required=True)
            builder.add_field("timeout", FieldType.INT, "Timeout", default=30)
            return builder.build()  # Returns dict[str, PluginConfigField]
        ```

    2. Full mode (creates a dynamic schema class):
        ```python
        SchemaClass = (
            ConfigSchemaBuilder("my-plugin")
            .group("Authentication")
            .add_field("api_key", FieldType.SECRET, "API key", required=True)
            .end_group()
            .build_schema()  # Returns type[PluginConfigSchema]
        )
        ```
    """

    plugin_name: str = ""
    _fields: list[PluginConfigField] = field(default_factory=list)
    _groups: dict[str, list[str]] = field(default_factory=dict)
    _current_group: str | None = None

    def group(self, name: str) -> ConfigSchemaBuilder:
        """Start a new field group.

        Args:
            name: Group name for UI organization

        Returns:
            Self for chaining
        """
        self._current_group = name
        if name not in self._groups:
            self._groups[name] = []
        return self

    def end_group(self) -> ConfigSchemaBuilder:
        """End the current field group.

        Returns:
            Self for chaining
        """
        self._current_group = None
        return self

    def add_field(
        self,
        name: str,
        field_type: FieldType,
        description: str,
        *,
        required: bool = True,
        default: Any = None,
        sensitive: bool = False,
        env_var: str | None = None,
        example: str | None = None,
        choices: list[Any] | None = None,
        validator: Callable[[Any], bool] | None = None,
        depends_on: str | None = None,
        min_value: int | float | None = None,
        max_value: int | float | None = None,
        pattern: str | None = None,
        help_url: str | None = None,
    ) -> ConfigSchemaBuilder:
        """Add a configuration field.

        Args:
            name: Field name
            field_type: Type of the field
            description: Human-readable description
            required: Whether the field is required
            default: Default value
            sensitive: Whether the field is sensitive
            env_var: Environment variable fallback
            example: Example value
            choices: Valid choices for CHOICE type
            validator: Custom validation function
            depends_on: Field dependency
            min_value: Minimum numeric value
            max_value: Maximum numeric value
            pattern: Regex pattern for strings
            help_url: Documentation URL

        Returns:
            Self for chaining
        """
        config_field = PluginConfigField(
            name=name,
            field_type=field_type,
            description=description,
            required=required,
            default=default,
            sensitive=sensitive,
            env_var=env_var,
            example=example,
            choices=choices,
            validator=validator,
            depends_on=depends_on,
            min_value=min_value,
            max_value=max_value,
            pattern=pattern,
            help_url=help_url,
        )
        self._fields.append(config_field)

        if self._current_group:
            self._groups[self._current_group].append(name)

        return self

    def build(self) -> dict[str, PluginConfigField]:
        """Build a dictionary of field definitions.

        Simple mode for use in get_schema_fields() overrides.

        Returns:
            Dictionary mapping field names to PluginConfigField instances
        """
        return {f.name: f for f in self._fields}

    def build_schema(self) -> type[PluginConfigSchema]:
        """Build a full configuration schema class.

        Full mode that creates a dynamic Pydantic model.

        Returns:
            A dynamically created PluginConfigSchema subclass

        Raises:
            ValueError: If plugin_name is not set
        """
        if not self.plugin_name:
            raise ValueError("plugin_name is required for build_schema()")

        from pydantic import Field, create_model

        # Build field definitions for Pydantic
        field_definitions: dict[str, tuple[type, Any]] = {}

        for config_field in self._fields:
            # Determine Python type
            python_type = self._get_python_type(config_field.field_type)

            # Build field info
            field_kwargs: dict[str, Any] = {
                "description": config_field.description,
                "json_schema_extra": {
                    "sensitive": config_field.sensitive,
                    "env_var": config_field.env_var,
                    "example": config_field.example,
                    "choices": config_field.choices,
                    "depends_on": config_field.depends_on,
                    "help_url": config_field.help_url,
                },
            }

            if config_field.min_value is not None:
                field_kwargs["ge"] = config_field.min_value
            if config_field.max_value is not None:
                field_kwargs["le"] = config_field.max_value
            if config_field.pattern:
                field_kwargs["pattern"] = config_field.pattern

            if config_field.required:
                field_definitions[config_field.name] = (python_type, Field(**field_kwargs))
            else:
                field_definitions[config_field.name] = (
                    python_type,
                    Field(default=config_field.default, **field_kwargs),
                )

        # Create the model
        model = create_model(
            f"{self.plugin_name.replace('-', '_').title()}Config",
            __base__=PluginConfigSchema,
            **field_definitions,
        )

        # Set class variables
        model._plugin_name = self.plugin_name
        model._field_groups = (
            self._groups if self._groups else {"General": [f.name for f in self._fields]}
        )

        return model

    @staticmethod
    def _get_python_type(field_type: FieldType) -> type:
        """Get Python type for a FieldType.

        Args:
            field_type: The FieldType enum value

        Returns:
            Corresponding Python type
        """
        type_map: dict[FieldType, type] = {
            FieldType.STRING: str,
            FieldType.INT: int,
            FieldType.FLOAT: float,
            FieldType.BOOL: bool,
            FieldType.LIST: list,
            FieldType.DICT: dict,
            FieldType.SECRET: str,
            FieldType.URL: str,
            FieldType.PATH: str,
            FieldType.EMAIL: str,
            FieldType.CHOICE: str,
            FieldType.DATETIME: str,
        }
        return type_map.get(field_type, str)
