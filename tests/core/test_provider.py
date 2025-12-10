"""Comprehensive tests for provider abstraction module.

Tests cover:
- MessageType enum
- Message dataclass
- SendResult dataclass
- ProviderConfig model
- BaseProvider abstract class
- ProviderRegistry (deprecated)
"""

from __future__ import annotations

from typing import Any

import pytest

from feishu_webhook_bot.core.provider import (
    BaseProvider,
    Message,
    MessageType,
    ProviderConfig,
    ProviderRegistry,
    SendResult,
)


# ==============================================================================
# MessageType Tests
# ==============================================================================


class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_type_values(self):
        """Test MessageType enum values."""
        assert MessageType.TEXT == "text"
        assert MessageType.RICH_TEXT == "rich_text"
        assert MessageType.CARD == "card"
        assert MessageType.IMAGE == "image"
        assert MessageType.FILE == "file"
        assert MessageType.AUDIO == "audio"
        assert MessageType.VIDEO == "video"
        assert MessageType.LOCATION == "location"
        assert MessageType.CONTACT == "contact"
        assert MessageType.SHARE == "share"
        assert MessageType.CUSTOM == "custom"

    def test_message_type_is_string(self):
        """Test MessageType is a string enum."""
        assert isinstance(MessageType.TEXT, str)
        assert MessageType.TEXT.value == "text"

    def test_message_type_from_string(self):
        """Test creating MessageType from string."""
        assert MessageType("text") == MessageType.TEXT
        assert MessageType("card") == MessageType.CARD


# ==============================================================================
# Message Tests
# ==============================================================================


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test Message creation."""
        msg = Message(type=MessageType.TEXT, content="Hello")

        assert msg.type == MessageType.TEXT
        assert msg.content == "Hello"
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test Message with metadata."""
        msg = Message(
            type=MessageType.CARD,
            content={"title": "Test"},
            metadata={"priority": "high"},
        )

        assert msg.type == MessageType.CARD
        assert msg.content == {"title": "Test"}
        assert msg.metadata["priority"] == "high"

    def test_message_different_content_types(self):
        """Test Message with different content types."""
        # String content
        msg_text = Message(type=MessageType.TEXT, content="Hello")
        assert isinstance(msg_text.content, str)

        # Dict content
        msg_card = Message(type=MessageType.CARD, content={"key": "value"})
        assert isinstance(msg_card.content, dict)

        # List content
        msg_rich = Message(type=MessageType.RICH_TEXT, content=[["text"]])
        assert isinstance(msg_rich.content, list)


# ==============================================================================
# SendResult Tests
# ==============================================================================


class TestSendResult:
    """Tests for SendResult dataclass."""

    def test_send_result_success(self):
        """Test successful SendResult."""
        result = SendResult(success=True, message_id="msg_123")

        assert result.success is True
        assert result.message_id == "msg_123"
        assert result.error is None
        assert result.raw_response is None

    def test_send_result_failure(self):
        """Test failed SendResult."""
        result = SendResult(success=False, error="Connection timeout")

        assert result.success is False
        assert result.message_id is None
        assert result.error == "Connection timeout"

    def test_send_result_with_raw_response(self):
        """Test SendResult with raw response."""
        raw = {"code": 0, "msg": "success"}
        result = SendResult(success=True, message_id="msg_123", raw_response=raw)

        assert result.raw_response == raw

    def test_send_result_ok_factory(self):
        """Test SendResult.ok() factory method."""
        result = SendResult.ok("msg_456")

        assert result.success is True
        assert result.message_id == "msg_456"
        assert result.error is None

    def test_send_result_ok_with_raw_response(self):
        """Test SendResult.ok() with raw response."""
        raw = {"data": {"message_id": "msg_456"}}
        result = SendResult.ok("msg_456", raw_response=raw)

        assert result.success is True
        assert result.raw_response == raw

    def test_send_result_fail_factory(self):
        """Test SendResult.fail() factory method."""
        result = SendResult.fail("API error")

        assert result.success is False
        assert result.error == "API error"
        assert result.message_id is None

    def test_send_result_fail_with_raw_response(self):
        """Test SendResult.fail() with raw response."""
        raw = {"code": 500, "msg": "Internal error"}
        result = SendResult.fail("API error", raw_response=raw)

        assert result.success is False
        assert result.raw_response == raw


# ==============================================================================
# ProviderConfig Tests
# ==============================================================================


class TestProviderConfig:
    """Tests for ProviderConfig model."""

    def test_config_required_fields(self):
        """Test ProviderConfig with required fields."""
        config = ProviderConfig(provider_type="feishu")

        assert config.provider_type == "feishu"
        assert config.name == "default"
        assert config.enabled is True
        assert config.timeout is None
        assert config.retry is None

    def test_config_all_fields(self):
        """Test ProviderConfig with all fields."""
        config = ProviderConfig(
            provider_type="feishu",
            name="primary",
            enabled=False,
            timeout=30.0,
        )

        assert config.provider_type == "feishu"
        assert config.name == "primary"
        assert config.enabled is False
        assert config.timeout == 30.0

    def test_config_timeout_validation(self):
        """Test ProviderConfig timeout must be non-negative."""
        # Valid timeout
        config = ProviderConfig(provider_type="test", timeout=0.0)
        assert config.timeout == 0.0

        # Invalid timeout
        with pytest.raises(ValueError):
            ProviderConfig(provider_type="test", timeout=-1.0)

    def test_config_extra_fields_allowed(self):
        """Test ProviderConfig allows extra fields."""
        config = ProviderConfig(
            provider_type="custom",
            custom_field="value",
            another_field=123,
        )

        assert config.custom_field == "value"
        assert config.another_field == 123


# ==============================================================================
# BaseProvider Tests
# ==============================================================================


class ConcreteProvider(BaseProvider):
    """Concrete implementation of BaseProvider for testing."""

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def send_message(self, message: Message, target: str) -> SendResult:
        return SendResult.ok(f"msg_{target}")

    def send_text(self, text: str, target: str) -> SendResult:
        return SendResult.ok(f"text_{target}")

    def send_card(self, card: dict[str, Any], target: str) -> SendResult:
        return SendResult.ok(f"card_{target}")

    def send_rich_text(
        self,
        title: str,
        content: list[list[dict[str, Any]]],
        target: str,
        language: str = "zh_cn",
    ) -> SendResult:
        return SendResult.ok(f"rich_{target}")

    def send_image(self, image_key: str, target: str) -> SendResult:
        return SendResult.ok(f"img_{target}")


class TestBaseProvider:
    """Tests for BaseProvider abstract class."""

    def test_provider_initialization(self):
        """Test provider initialization."""
        config = ProviderConfig(provider_type="test", name="test_provider")
        provider = ConcreteProvider(config)

        assert provider.name == "test_provider"
        assert provider.provider_type == "test"
        assert provider.is_connected is False

    def test_provider_connect(self):
        """Test provider connect."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        provider.connect()

        assert provider.is_connected is True

    def test_provider_disconnect(self):
        """Test provider disconnect."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        provider.connect()
        provider.disconnect()

        assert provider.is_connected is False

    def test_provider_close(self):
        """Test provider close (alias for disconnect)."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        provider.connect()
        provider.close()

        assert provider.is_connected is False

    def test_provider_context_manager(self):
        """Test provider as context manager."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        with provider as p:
            assert p.is_connected is True

        assert provider.is_connected is False

    def test_provider_send_text(self):
        """Test provider send_text."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        result = provider.send_text("Hello", "user123")

        assert result.success is True
        assert result.message_id == "text_user123"

    def test_provider_send_card(self):
        """Test provider send_card."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        result = provider.send_card({"title": "Test"}, "user123")

        assert result.success is True
        assert result.message_id == "card_user123"

    def test_provider_send_image(self):
        """Test provider send_image."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        result = provider.send_image("img_key", "user123")

        assert result.success is True

    def test_provider_send_file_not_supported(self):
        """Test provider send_file returns not supported."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        result = provider.send_file("file_key", "user123")

        assert result.success is False
        assert "not supported" in result.error

    def test_provider_send_audio_not_supported(self):
        """Test provider send_audio returns not supported."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        result = provider.send_audio("audio_key", "user123")

        assert result.success is False
        assert "not supported" in result.error

    def test_provider_send_video_not_supported(self):
        """Test provider send_video returns not supported."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        result = provider.send_video("video_key", "user123")

        assert result.success is False
        assert "not supported" in result.error

    def test_provider_get_capabilities(self):
        """Test provider get_capabilities."""
        config = ProviderConfig(provider_type="test")
        provider = ConcreteProvider(config)

        caps = provider.get_capabilities()

        assert caps["text"] is True
        assert caps["rich_text"] is True
        assert caps["card"] is True
        assert caps["image"] is True
        assert caps["file"] is False
        assert caps["audio"] is False
        assert caps["video"] is False

    def test_provider_repr(self):
        """Test provider string representation."""
        config = ProviderConfig(provider_type="feishu", name="primary")
        provider = ConcreteProvider(config)

        repr_str = repr(provider)

        assert "ConcreteProvider" in repr_str
        assert "primary" in repr_str
        assert "feishu" in repr_str


# ==============================================================================
# ProviderRegistry Tests (Deprecated)
# ==============================================================================


class TestProviderRegistry:
    """Tests for ProviderRegistry (deprecated)."""

    def setup_method(self):
        """Reset registry before each test."""
        ProviderRegistry.reset_instance()

    def teardown_method(self):
        """Reset registry after each test."""
        ProviderRegistry.reset_instance()

    def test_registry_singleton(self):
        """Test ProviderRegistry is a singleton."""
        with pytest.warns(DeprecationWarning):
            reg1 = ProviderRegistry()
        with pytest.warns(DeprecationWarning):
            reg2 = ProviderRegistry()

        assert reg1 is reg2

    def test_registry_deprecation_warning(self):
        """Test ProviderRegistry emits deprecation warning."""
        with pytest.warns(DeprecationWarning, match="deprecated"):
            ProviderRegistry()

    def test_registry_register(self):
        """Test registering a provider."""
        with pytest.warns(DeprecationWarning):
            registry = ProviderRegistry()

        config = ProviderConfig(provider_type="test", name="test1")
        provider = ConcreteProvider(config)

        registry.register(provider)

        assert registry.get("test1") is provider

    def test_registry_register_set_default(self):
        """Test registering a provider as default."""
        with pytest.warns(DeprecationWarning):
            registry = ProviderRegistry()

        config1 = ProviderConfig(provider_type="test", name="first")
        config2 = ProviderConfig(provider_type="test", name="second")
        provider1 = ConcreteProvider(config1)
        provider2 = ConcreteProvider(config2)

        registry.register(provider1)
        registry.register(provider2, set_default=True)

        # Default should be second
        assert registry.get() is provider2

    def test_registry_unregister(self):
        """Test unregistering a provider."""
        with pytest.warns(DeprecationWarning):
            registry = ProviderRegistry()

        config = ProviderConfig(provider_type="test", name="test1")
        provider = ConcreteProvider(config)

        registry.register(provider)
        removed = registry.unregister("test1")

        assert removed is provider
        assert registry.get("test1") is None

    def test_registry_get_all(self):
        """Test getting all providers."""
        with pytest.warns(DeprecationWarning):
            registry = ProviderRegistry()

        config1 = ProviderConfig(provider_type="test", name="p1")
        config2 = ProviderConfig(provider_type="test", name="p2")
        provider1 = ConcreteProvider(config1)
        provider2 = ConcreteProvider(config2)

        registry.register(provider1)
        registry.register(provider2)

        all_providers = registry.get_all()

        assert len(all_providers) == 2
        assert "p1" in all_providers
        assert "p2" in all_providers

    def test_registry_clear(self):
        """Test clearing all providers."""
        with pytest.warns(DeprecationWarning):
            registry = ProviderRegistry()

        config = ProviderConfig(provider_type="test", name="test1")
        provider = ConcreteProvider(config)
        provider.connect()

        registry.register(provider)
        registry.clear()

        assert registry.get("test1") is None
        assert provider.is_connected is False

    def test_registry_get_default(self):
        """Test getting default provider."""
        with pytest.warns(DeprecationWarning):
            registry = ProviderRegistry()

        config = ProviderConfig(provider_type="test", name="default_provider")
        provider = ConcreteProvider(config)

        registry.register(provider)

        # Get without name returns default
        assert registry.get() is provider

    def test_registry_unregister_updates_default(self):
        """Test unregistering default provider updates default."""
        with pytest.warns(DeprecationWarning):
            registry = ProviderRegistry()

        config1 = ProviderConfig(provider_type="test", name="first")
        config2 = ProviderConfig(provider_type="test", name="second")
        provider1 = ConcreteProvider(config1)
        provider2 = ConcreteProvider(config2)

        registry.register(provider1)  # This becomes default
        registry.register(provider2)

        # Unregister default
        registry.unregister("first")

        # Default should now be second
        assert registry.get() is provider2
