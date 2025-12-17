"""Base provider abstraction for multi-platform messaging support."""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .config import RetryPolicyConfig
from .logger import get_logger

logger = get_logger(__name__)


class MessageType(str, Enum):
    """Universal message types supported across providers."""

    TEXT = "text"
    RICH_TEXT = "rich_text"
    CARD = "card"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    CONTACT = "contact"
    SHARE = "share"
    CUSTOM = "custom"


@dataclass
class Message:
    """Universal message representation."""

    type: MessageType
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SendResult:
    """Result of a message send operation."""

    success: bool
    message_id: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] | None = None

    @classmethod
    def ok(cls, message_id: str, raw_response: dict[str, Any] | None = None) -> SendResult:
        return cls(success=True, message_id=message_id, raw_response=raw_response)

    @classmethod
    def fail(cls, error: str, raw_response: dict[str, Any] | None = None) -> SendResult:
        return cls(success=False, error=error, raw_response=raw_response)


class ProviderConfig(BaseModel):
    """Base configuration for message providers."""

    model_config = {"extra": "allow"}

    provider_type: str = Field(..., description="Provider type identifier")
    name: str = Field(default="default", description="Provider instance name")
    enabled: bool = Field(default=True, description="Whether this provider is enabled")
    timeout: float | None = Field(default=None, ge=0.0, description="Request timeout")
    retry: RetryPolicyConfig | None = Field(default=None, description="Retry policy")


class BaseProvider(ABC):
    """Abstract base class for message providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.logger = get_logger(f"provider.{config.provider_type}.{config.name}")
        self._connected = False

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def provider_type(self) -> str:
        return self.config.provider_type

    @property
    def is_connected(self) -> bool:
        return self._connected

    def __enter__(self) -> BaseProvider:
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()

    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    def close(self) -> None:
        self.disconnect()

    @abstractmethod
    def send_message(self, message: Message, target: str) -> SendResult:
        pass

    @abstractmethod
    def send_text(self, text: str, target: str) -> SendResult:
        pass

    @abstractmethod
    def send_card(self, card: dict[str, Any], target: str) -> SendResult:
        pass

    @abstractmethod
    def send_rich_text(
        self,
        title: str,
        content: list[list[dict[str, Any]]],
        target: str,
        language: str = "zh_cn",
    ) -> SendResult:
        pass

    @abstractmethod
    def send_image(self, image_key: str, target: str) -> SendResult:
        pass

    def send_file(self, file_key: str, target: str) -> SendResult:
        return SendResult.fail(f"File messages not supported by {self.provider_type}")

    def send_audio(self, audio_key: str, target: str) -> SendResult:
        return SendResult.fail(f"Audio messages not supported by {self.provider_type}")

    def send_video(self, video_key: str, target: str) -> SendResult:
        return SendResult.fail(f"Video messages not supported by {self.provider_type}")

    def get_capabilities(self) -> dict[str, bool]:
        return {
            "text": True,
            "rich_text": True,
            "card": True,
            "image": True,
            "file": False,
            "audio": False,
            "video": False,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} type={self.provider_type}>"


class ProviderRegistry:
    """Registry for managing multiple provider instances.

    .. deprecated::
        ProviderRegistry is deprecated and will be removed in a future version.
        Use bot.providers dict directly instead for provider management.
        This singleton pattern can cause issues in testing and is not used
        by the bot.py orchestrator.
    """

    _instance: ProviderRegistry | None = None

    def __new__(cls) -> ProviderRegistry:
        import warnings

        warnings.warn(
            "ProviderRegistry is deprecated. Use bot.providers dict directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
            cls._instance._default = None
        return cls._instance

    @property
    def _providers(self) -> dict[str, BaseProvider]:
        return self.__dict__.get("_providers", {})

    @_providers.setter
    def _providers(self, value: dict[str, BaseProvider]) -> None:
        self.__dict__["_providers"] = value

    @property
    def _default(self) -> str | None:
        return self.__dict__.get("_default")

    @_default.setter
    def _default(self, value: str | None) -> None:
        self.__dict__["_default"] = value

    def register(self, provider: BaseProvider, set_default: bool = False) -> None:
        self._providers[provider.name] = provider
        if set_default or self._default is None:
            self._default = provider.name

    def unregister(self, name: str) -> BaseProvider | None:
        provider = self._providers.pop(name, None)
        if provider and self._default == name:
            self._default = next(iter(self._providers), None)
        return provider

    def get(self, name: str | None = None) -> BaseProvider | None:
        return self._providers.get(name or self._default or "")

    def get_all(self) -> dict[str, BaseProvider]:
        return dict(self._providers)

    def clear(self) -> None:
        for p in self._providers.values():
            with contextlib.suppress(Exception):
                p.disconnect()
        self._providers.clear()
        self._default = None

    @classmethod
    def reset_instance(cls) -> None:
        if cls._instance:
            cls._instance.clear()
        cls._instance = None
