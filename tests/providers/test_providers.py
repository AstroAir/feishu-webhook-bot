"""Comprehensive tests for provider implementations.

Tests cover:
- BaseProvider interface and abstractions
- SendResult factory methods
- MessageType enum
- ProviderConfig validation
- ProviderRegistry singleton pattern
- FeishuProvider implementation
- NapcatProvider (QQ OneBot11) implementation
- Circuit breaker integration
- Message tracker integration
- Retry logic
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any
from unittest.mock import Mock, patch

import httpx
import pytest

from feishu_webhook_bot.core.circuit_breaker import CircuitBreakerConfig
from feishu_webhook_bot.core.message_tracker import MessageStatus, MessageTracker
from feishu_webhook_bot.core.provider import (
    BaseProvider,
    Message,
    MessageType,
    ProviderConfig,
    ProviderRegistry,
    SendResult,
)
from feishu_webhook_bot.providers.feishu import FeishuProvider, FeishuProviderConfig
from feishu_webhook_bot.providers.qq_napcat import NapcatProvider, NapcatProviderConfig

# ==============================================================================
# SendResult Tests
# ==============================================================================


class TestSendResult:
    """Tests for SendResult dataclass and factory methods."""

    def test_send_result_ok_factory(self):
        """Test SendResult.ok() factory method creates success result."""
        result = SendResult.ok("msg_123", {"code": 0})
        assert result.success is True
        assert result.message_id == "msg_123"
        assert result.error is None
        assert result.raw_response == {"code": 0}

    def test_send_result_ok_without_response(self):
        """Test SendResult.ok() without raw response."""
        result = SendResult.ok("msg_456")
        assert result.success is True
        assert result.message_id == "msg_456"
        assert result.raw_response is None

    def test_send_result_fail_factory(self):
        """Test SendResult.fail() factory method creates failure result."""
        result = SendResult.fail("Connection timeout", {"status": 500})
        assert result.success is False
        assert result.message_id is None
        assert result.error == "Connection timeout"
        assert result.raw_response == {"status": 500}

    def test_send_result_fail_without_response(self):
        """Test SendResult.fail() without raw response."""
        result = SendResult.fail("Network error")
        assert result.success is False
        assert result.error == "Network error"
        assert result.raw_response is None

    def test_send_result_direct_construction(self):
        """Test direct SendResult construction."""
        result = SendResult(
            success=True,
            message_id="direct_msg",
            error=None,
            raw_response={"data": "test"},
        )
        assert result.success is True
        assert result.message_id == "direct_msg"


# ==============================================================================
# MessageType Tests
# ==============================================================================


class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_type_enum_values(self):
        """Test all MessageType enum values exist."""
        assert MessageType.TEXT.value == "text"
        assert MessageType.RICH_TEXT.value == "rich_text"
        assert MessageType.CARD.value == "card"
        assert MessageType.IMAGE.value == "image"
        assert MessageType.FILE.value == "file"
        assert MessageType.AUDIO.value == "audio"
        assert MessageType.VIDEO.value == "video"
        assert MessageType.LOCATION.value == "location"
        assert MessageType.CONTACT.value == "contact"
        assert MessageType.SHARE.value == "share"
        assert MessageType.CUSTOM.value == "custom"

    def test_message_type_string_comparison(self):
        """Test MessageType string comparison."""
        assert MessageType.TEXT == "text"
        assert MessageType.CARD == "card"

    def test_message_type_from_string(self):
        """Test creating MessageType from string."""
        assert MessageType("text") == MessageType.TEXT
        assert MessageType("card") == MessageType.CARD


# ==============================================================================
# Message Tests
# ==============================================================================


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_construction(self):
        """Test Message construction with required fields."""
        msg = Message(type=MessageType.TEXT, content="Hello")
        assert msg.type == MessageType.TEXT
        assert msg.content == "Hello"
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test Message construction with metadata."""
        msg = Message(
            type=MessageType.CARD,
            content={"header": "Test"},
            metadata={"priority": "high"},
        )
        assert msg.type == MessageType.CARD
        assert msg.content == {"header": "Test"}
        assert msg.metadata == {"priority": "high"}

    def test_message_metadata_default(self):
        """Test Message metadata defaults to empty dict."""
        msg1 = Message(type=MessageType.TEXT, content="a")
        msg2 = Message(type=MessageType.TEXT, content="b")
        # Ensure separate default dicts
        msg1.metadata["key"] = "value"
        assert "key" not in msg2.metadata


# ==============================================================================
# ProviderConfig Tests
# ==============================================================================


class TestProviderConfig:
    """Tests for ProviderConfig Pydantic model."""

    def test_provider_config_required_fields(self):
        """Test ProviderConfig requires provider_type."""
        config = ProviderConfig(provider_type="test")
        assert config.provider_type == "test"
        assert config.name == "default"
        assert config.enabled is True

    def test_provider_config_optional_fields(self):
        """Test ProviderConfig optional fields."""
        config = ProviderConfig(
            provider_type="feishu",
            name="my_provider",
            enabled=False,
            timeout=30.0,
        )
        assert config.name == "my_provider"
        assert config.enabled is False
        assert config.timeout == 30.0

    def test_provider_config_extra_fields_allowed(self):
        """Test ProviderConfig allows extra fields."""
        config = ProviderConfig(
            provider_type="test",
            custom_field="value",
        )
        assert config.custom_field == "value"

    def test_provider_config_timeout_validation(self):
        """Test ProviderConfig timeout must be non-negative."""
        with pytest.raises(ValueError):
            ProviderConfig(provider_type="test", timeout=-1.0)


# ==============================================================================
# BaseProvider Tests
# ==============================================================================


class ConcreteProvider(BaseProvider):
    """Concrete implementation for testing abstract BaseProvider."""

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def send_message(self, message: Message, target: str) -> SendResult:
        return SendResult.ok("test_msg")

    def send_text(self, text: str, target: str) -> SendResult:
        return SendResult.ok("text_msg")

    def send_card(self, card: dict[str, Any], target: str) -> SendResult:
        return SendResult.ok("card_msg")

    def send_rich_text(
        self,
        title: str,
        content: list[list[dict[str, Any]]],
        target: str,
        language: str = "zh_cn",
    ) -> SendResult:
        return SendResult.ok("rich_text_msg")

    def send_image(self, image_key: str, target: str) -> SendResult:
        return SendResult.ok("image_msg")


class TestBaseProvider:
    """Tests for BaseProvider abstract class."""

    @pytest.fixture
    def provider(self):
        """Create a concrete provider for testing."""
        config = ProviderConfig(provider_type="test", name="test_provider")
        return ConcreteProvider(config)

    def test_provider_initialization(self, provider):
        """Test BaseProvider initialization."""
        assert provider.name == "test_provider"
        assert provider.provider_type == "test"
        assert provider.is_connected is False

    def test_provider_connect_disconnect(self, provider):
        """Test connect and disconnect methods."""
        provider.connect()
        assert provider.is_connected is True
        provider.disconnect()
        assert provider.is_connected is False

    def test_provider_context_manager(self, provider):
        """Test BaseProvider context manager protocol."""
        with provider as p:
            assert p.is_connected is True
        assert provider.is_connected is False

    def test_provider_close_calls_disconnect(self, provider):
        """Test close() method calls disconnect()."""
        provider.connect()
        provider.close()
        assert provider.is_connected is False

    def test_provider_capabilities_default(self, provider):
        """Test default capabilities."""
        caps = provider.get_capabilities()
        assert caps["text"] is True
        assert caps["rich_text"] is True
        assert caps["card"] is True
        assert caps["image"] is True
        assert caps["file"] is False
        assert caps["audio"] is False
        assert caps["video"] is False

    def test_provider_send_file_not_supported(self, provider):
        """Test send_file returns unsupported error by default."""
        result = provider.send_file("file_key", "target")
        assert result.success is False
        assert "not supported" in result.error

    def test_provider_send_audio_not_supported(self, provider):
        """Test send_audio returns unsupported error by default."""
        result = provider.send_audio("audio_key", "target")
        assert result.success is False
        assert "not supported" in result.error

    def test_provider_send_video_not_supported(self, provider):
        """Test send_video returns unsupported error by default."""
        result = provider.send_video("video_key", "target")
        assert result.success is False
        assert "not supported" in result.error

    def test_provider_repr(self, provider):
        """Test BaseProvider __repr__."""
        repr_str = repr(provider)
        assert "ConcreteProvider" in repr_str
        assert "test_provider" in repr_str
        assert "test" in repr_str


# ==============================================================================
# ProviderRegistry Tests
# ==============================================================================


class TestProviderRegistry:
    """Tests for ProviderRegistry singleton."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before and after each test."""
        ProviderRegistry.reset_instance()
        yield
        ProviderRegistry.reset_instance()

    @pytest.fixture
    def registry(self):
        """Get a fresh registry instance."""
        return ProviderRegistry()

    @pytest.fixture
    def sample_provider(self):
        """Create a sample provider for testing."""
        config = ProviderConfig(provider_type="test", name="sample")
        return ConcreteProvider(config)

    def test_registry_singleton_pattern(self):
        """Test ProviderRegistry is a singleton."""
        registry1 = ProviderRegistry()
        registry2 = ProviderRegistry()
        assert registry1 is registry2

    def test_registry_register_provider(self, registry, sample_provider):
        """Test registering a provider."""
        registry.register(sample_provider)
        assert registry.get("sample") is sample_provider

    def test_registry_register_sets_default(self, registry, sample_provider):
        """Test first registered provider becomes default."""
        registry.register(sample_provider)
        assert registry.get() is sample_provider

    def test_registry_register_explicit_default(self, registry):
        """Test setting explicit default provider."""
        config1 = ProviderConfig(provider_type="test", name="first")
        config2 = ProviderConfig(provider_type="test", name="second")
        provider1 = ConcreteProvider(config1)
        provider2 = ConcreteProvider(config2)

        registry.register(provider1)
        registry.register(provider2, set_default=True)

        assert registry.get() is provider2

    def test_registry_unregister_provider(self, registry, sample_provider):
        """Test unregistering a provider."""
        registry.register(sample_provider)
        removed = registry.unregister("sample")
        assert removed is sample_provider
        assert registry.get("sample") is None

    def test_registry_unregister_updates_default(self, registry):
        """Test unregistering default provider updates default."""
        config1 = ProviderConfig(provider_type="test", name="first")
        config2 = ProviderConfig(provider_type="test", name="second")
        provider1 = ConcreteProvider(config1)
        provider2 = ConcreteProvider(config2)

        registry.register(provider1)  # becomes default
        registry.register(provider2)

        registry.unregister("first")
        # Default should change to second
        assert registry.get() is provider2

    def test_registry_unregister_nonexistent(self, registry):
        """Test unregistering nonexistent provider returns None."""
        result = registry.unregister("nonexistent")
        assert result is None

    def test_registry_get_by_name(self, registry, sample_provider):
        """Test getting provider by name."""
        registry.register(sample_provider)
        assert registry.get("sample") is sample_provider

    def test_registry_get_not_found(self, registry):
        """Test getting nonexistent provider returns None."""
        assert registry.get("nonexistent") is None

    def test_registry_get_default(self, registry, sample_provider):
        """Test getting default provider."""
        registry.register(sample_provider)
        assert registry.get() is sample_provider

    def test_registry_get_all(self, registry):
        """Test getting all providers."""
        config1 = ProviderConfig(provider_type="test", name="p1")
        config2 = ProviderConfig(provider_type="test", name="p2")
        provider1 = ConcreteProvider(config1)
        provider2 = ConcreteProvider(config2)

        registry.register(provider1)
        registry.register(provider2)

        all_providers = registry.get_all()
        assert len(all_providers) == 2
        assert all_providers["p1"] is provider1
        assert all_providers["p2"] is provider2

    def test_registry_clear(self, registry, sample_provider):
        """Test clearing all providers."""
        sample_provider.connect()
        registry.register(sample_provider)

        registry.clear()

        assert registry.get() is None
        assert registry.get("sample") is None
        assert sample_provider.is_connected is False

    def test_registry_reset_instance(self, sample_provider):
        """Test resetting singleton instance."""
        registry = ProviderRegistry()
        registry.register(sample_provider)

        ProviderRegistry.reset_instance()

        new_registry = ProviderRegistry()
        assert new_registry.get("sample") is None


# ==============================================================================
# FeishuProviderConfig Tests
# ==============================================================================


class TestFeishuProviderConfig:
    """Tests for FeishuProviderConfig."""

    def test_feishu_config_required_url(self):
        """Test FeishuProviderConfig requires url."""
        config = FeishuProviderConfig(url="https://open.feishu.cn/webhook/xxx")
        assert config.url == "https://open.feishu.cn/webhook/xxx"
        assert config.provider_type == "feishu"

    def test_feishu_config_optional_secret(self):
        """Test FeishuProviderConfig optional secret."""
        config = FeishuProviderConfig(
            url="https://example.com/webhook",
            secret="my_secret_key",
        )
        assert config.secret == "my_secret_key"

    def test_feishu_config_headers(self):
        """Test FeishuProviderConfig custom headers."""
        config = FeishuProviderConfig(
            url="https://example.com/webhook",
            headers={"X-Custom": "value"},
        )
        assert config.headers == {"X-Custom": "value"}


# ==============================================================================
# FeishuProvider Tests
# ==============================================================================


class TestFeishuProvider:
    """Tests for FeishuProvider implementation."""

    @pytest.fixture
    def feishu_config(self):
        """Create Feishu provider config."""
        return FeishuProviderConfig(
            url="https://open.feishu.cn/webhook/test",
            name="test_feishu",
        )

    @pytest.fixture
    def feishu_config_with_secret(self):
        """Create Feishu provider config with signing secret."""
        return FeishuProviderConfig(
            url="https://open.feishu.cn/webhook/test",
            name="test_feishu_signed",
            secret="test_secret_123",
        )

    @pytest.fixture
    def mock_tracker(self):
        """Create mock message tracker."""
        tracker = Mock(spec=MessageTracker)
        return tracker

    @pytest.fixture
    def provider(self, feishu_config):
        """Create Feishu provider."""
        return FeishuProvider(feishu_config)

    @pytest.fixture
    def provider_with_tracker(self, feishu_config, mock_tracker):
        """Create Feishu provider with message tracker."""
        return FeishuProvider(feishu_config, message_tracker=mock_tracker)

    @pytest.fixture
    def provider_with_secret(self, feishu_config_with_secret):
        """Create Feishu provider with signing secret."""
        return FeishuProvider(feishu_config_with_secret)

    def test_feishu_provider_initialization(self, provider, feishu_config):
        """Test FeishuProvider initialization."""
        assert provider.name == "test_feishu"
        assert provider.provider_type == "feishu"
        assert provider.config.url == feishu_config.url
        assert provider.is_connected is False

    def test_feishu_provider_with_circuit_breaker_config(self, feishu_config):
        """Test FeishuProvider with custom circuit breaker config."""
        cb_config = CircuitBreakerConfig(
            failure_threshold=10,
            timeout_seconds=120.0,
        )
        provider = FeishuProvider(feishu_config, circuit_breaker_config=cb_config)
        assert provider._circuit_breaker.config.failure_threshold == 10

    def test_feishu_connect(self, provider):
        """Test FeishuProvider connect creates HTTP client."""
        provider.connect()
        assert provider.is_connected is True
        assert provider._client is not None
        provider.disconnect()

    def test_feishu_connect_idempotent(self, provider):
        """Test calling connect multiple times is idempotent."""
        provider.connect()
        client1 = provider._client
        provider.connect()
        assert provider._client is client1
        provider.disconnect()

    def test_feishu_disconnect(self, provider):
        """Test FeishuProvider disconnect closes client."""
        provider.connect()
        provider.disconnect()
        assert provider.is_connected is False

    @patch("httpx.Client")
    def test_feishu_send_text_success(self, mock_client_cls, provider):
        """Test FeishuProvider send_text success."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_text("Hello, Feishu!", "")

        assert result.success is True
        assert result.message_id is not None
        mock_client.post.assert_called_once()

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_text_with_target(self, mock_client_cls, provider):
        """Test FeishuProvider send_text with custom target URL."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        provider.send_text("Test", "https://custom.url/webhook")

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://custom.url/webhook"

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_text_api_error(self, mock_client_cls, provider):
        """Test FeishuProvider send_text handles API error."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 9001, "msg": "Invalid webhook"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_text("Test", "")

        assert result.success is False
        assert "Invalid webhook" in result.error

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_text_tracks_message(
        self, mock_client_cls, provider_with_tracker, mock_tracker
    ):
        """Test FeishuProvider send_text tracks message with tracker."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider_with_tracker.connect()
        result = provider_with_tracker.send_text("Tracked message", "")

        mock_tracker.track.assert_called_once()
        mock_tracker.update_status.assert_called_once_with(result.message_id, MessageStatus.SENT)

        provider_with_tracker.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_text_tracks_failure(
        self, mock_client_cls, provider_with_tracker, mock_tracker
    ):
        """Test FeishuProvider send_text tracks failure with tracker."""
        mock_client = Mock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client_cls.return_value = mock_client

        provider_with_tracker.connect()
        result = provider_with_tracker.send_text("Failed message", "")

        assert result.success is False
        mock_tracker.update_status.assert_called()
        call_args = mock_tracker.update_status.call_args
        assert call_args[0][1] == MessageStatus.FAILED

        provider_with_tracker.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_card_success(self, mock_client_cls, provider):
        """Test FeishuProvider send_card success."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        card = {
            "header": {"title": {"tag": "plain_text", "content": "Test Card"}},
            "elements": [],
        }
        result = provider.send_card(card, "")

        assert result.success is True
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["msg_type"] == "interactive"
        assert payload["card"] == card

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_rich_text_success(self, mock_client_cls, provider):
        """Test FeishuProvider send_rich_text success."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        content = [[{"tag": "text", "text": "Hello"}]]
        result = provider.send_rich_text("Title", content, "")

        assert result.success is True
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["msg_type"] == "post"
        assert "post" in payload["content"]

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_rich_text_with_language(self, mock_client_cls, provider):
        """Test FeishuProvider send_rich_text with custom language."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        content = [[{"tag": "text", "text": "Hello"}]]
        provider.send_rich_text("Title", content, "", language="en_us")

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert "en_us" in payload["content"]["post"]

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_image_success(self, mock_client_cls, provider):
        """Test FeishuProvider send_image success."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_image("img_v2_xxx", "")

        assert result.success is True
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["msg_type"] == "image"
        assert payload["content"]["image_key"] == "img_v2_xxx"

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_message_text_type(self, mock_client_cls, provider):
        """Test FeishuProvider send_message with TEXT type."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        message = Message(type=MessageType.TEXT, content="Hello")
        result = provider.send_message(message, "")

        assert result.success is True

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_message_card_type(self, mock_client_cls, provider):
        """Test FeishuProvider send_message with CARD type."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        message = Message(type=MessageType.CARD, content={"header": {}})
        result = provider.send_message(message, "")

        assert result.success is True

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_message_rich_text_type(self, mock_client_cls, provider):
        """Test FeishuProvider send_message with RICH_TEXT type."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        message = Message(
            type=MessageType.RICH_TEXT,
            content={"title": "Test", "content": [], "language": "zh_cn"},
        )
        result = provider.send_message(message, "")

        assert result.success is True

        provider.disconnect()

    @patch("httpx.Client")
    def test_feishu_send_message_unsupported_type(self, mock_client_cls, provider):
        """Test FeishuProvider send_message with unsupported type."""
        provider.connect()
        message = Message(type=MessageType.FILE, content="file_key")
        result = provider.send_message(message, "")

        assert result.success is False
        assert "Unsupported" in result.error

        provider.disconnect()

    def test_feishu_hmac_signature_generation(self, provider_with_secret):
        """Test FeishuProvider HMAC signature generation."""
        timestamp = 1609459200

        sign = provider_with_secret._generate_sign(timestamp)

        # Verify signature format (base64 encoded)
        assert sign is not None
        assert len(sign) > 0
        # Should be valid base64
        base64.b64decode(sign)

    def test_feishu_hmac_signature_correct(self, provider_with_secret):
        """Test FeishuProvider generates correct HMAC signature."""
        timestamp = 1609459200
        secret = "test_secret_123"

        # Calculate expected signature
        string_to_sign = f"{timestamp}\n{secret}"
        expected_hmac = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        expected_sign = base64.b64encode(expected_hmac).decode("utf-8")

        actual_sign = provider_with_secret._generate_sign(timestamp)

        assert actual_sign == expected_sign

    def test_feishu_hmac_signature_empty_without_secret(self, provider):
        """Test FeishuProvider returns empty sign without secret."""
        sign = provider._generate_sign(1609459200)
        assert sign == ""

    @patch("httpx.Client")
    def test_feishu_request_includes_signature(self, mock_client_cls, provider_with_secret):
        """Test FeishuProvider includes signature in request."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider_with_secret.connect()
        provider_with_secret.send_text("Test", "")

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert "timestamp" in payload
        assert "sign" in payload

        provider_with_secret.disconnect()

    def test_feishu_send_without_connect_returns_error(self, provider):
        """Test FeishuProvider returns error if not connected."""
        result = provider.send_text("Test", "")
        assert result.success is False
        assert "not connected" in result.error.lower()

    def test_feishu_capabilities(self, provider):
        """Test FeishuProvider capabilities."""
        caps = provider.get_capabilities()
        assert caps["text"] is True
        assert caps["rich_text"] is True
        assert caps["card"] is True
        assert caps["image"] is True
        assert caps["file"] is False
        assert caps["audio"] is False
        assert caps["video"] is False

    @patch("httpx.Client")
    @patch("time.sleep")
    def test_feishu_retry_on_http_error(self, mock_sleep, mock_client_cls, provider):
        """Test FeishuProvider retries on HTTP error."""
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=Mock(status_code=500)
        )

        mock_response_ok = Mock()
        mock_response_ok.json.return_value = {"code": 0}
        mock_response_ok.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.side_effect = [mock_response_fail, mock_response_ok]
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_text("Test", "")

        assert result.success is True
        assert mock_client.post.call_count == 2
        mock_sleep.assert_called_once()

        provider.disconnect()

    @patch("httpx.Client")
    @patch("time.sleep")
    def test_feishu_max_retries_exceeded(self, mock_sleep, mock_client_cls, provider):
        """Test FeishuProvider fails after max retries."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=Mock(status_code=500)
        )

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_text("Test", "")

        assert result.success is False
        assert mock_client.post.call_count == 3  # Default max_attempts

        provider.disconnect()


# ==============================================================================
# NapcatProviderConfig Tests
# ==============================================================================


class TestNapcatProviderConfig:
    """Tests for NapcatProviderConfig."""

    def test_napcat_config_required_url(self):
        """Test NapcatProviderConfig requires http_url."""
        config = NapcatProviderConfig(http_url="http://127.0.0.1:3000")
        assert config.http_url == "http://127.0.0.1:3000"
        assert config.provider_type == "napcat"

    def test_napcat_config_optional_token(self):
        """Test NapcatProviderConfig optional access_token."""
        config = NapcatProviderConfig(
            http_url="http://127.0.0.1:3000",
            access_token="my_token",
        )
        assert config.access_token == "my_token"


# ==============================================================================
# NapcatProvider Tests
# ==============================================================================


class TestNapcatProvider:
    """Tests for NapcatProvider implementation."""

    @pytest.fixture
    def napcat_config(self):
        """Create Napcat provider config."""
        return NapcatProviderConfig(
            http_url="http://127.0.0.1:3000",
            name="test_napcat",
        )

    @pytest.fixture
    def napcat_config_with_token(self):
        """Create Napcat provider config with auth token."""
        return NapcatProviderConfig(
            http_url="http://127.0.0.1:3000",
            name="test_napcat_auth",
            access_token="test_token_123",
        )

    @pytest.fixture
    def mock_tracker(self):
        """Create mock message tracker."""
        tracker = Mock(spec=MessageTracker)
        return tracker

    @pytest.fixture
    def provider(self, napcat_config):
        """Create Napcat provider."""
        return NapcatProvider(napcat_config)

    @pytest.fixture
    def provider_with_tracker(self, napcat_config, mock_tracker):
        """Create Napcat provider with message tracker."""
        return NapcatProvider(napcat_config, message_tracker=mock_tracker)

    @pytest.fixture
    def provider_with_token(self, napcat_config_with_token):
        """Create Napcat provider with auth token."""
        return NapcatProvider(napcat_config_with_token)

    def test_napcat_provider_initialization(self, provider, napcat_config):
        """Test NapcatProvider initialization."""
        assert provider.name == "test_napcat"
        assert provider.provider_type == "napcat"
        assert provider.config.http_url == napcat_config.http_url
        assert provider.is_connected is False

    def test_napcat_provider_with_circuit_breaker_config(self, napcat_config):
        """Test NapcatProvider with custom circuit breaker config."""
        cb_config = CircuitBreakerConfig(
            failure_threshold=15,
            timeout_seconds=180.0,
        )
        provider = NapcatProvider(napcat_config, circuit_breaker_config=cb_config)
        assert provider._circuit_breaker.config.failure_threshold == 15

    def test_napcat_connect(self, provider):
        """Test NapcatProvider connect creates HTTP client."""
        provider.connect()
        assert provider.is_connected is True
        assert provider._client is not None
        provider.disconnect()

    def test_napcat_connect_with_token(self, provider_with_token):
        """Test NapcatProvider connect sets auth header."""
        provider_with_token.connect()
        assert provider_with_token.is_connected is True
        provider_with_token.disconnect()

    def test_napcat_disconnect(self, provider):
        """Test NapcatProvider disconnect closes client."""
        provider.connect()
        provider.disconnect()
        assert provider.is_connected is False

    # Target parsing tests

    def test_napcat_parse_target_private(self, provider):
        """Test NapcatProvider parses private message target."""
        user_id, group_id = provider._parse_target("private:123456789")
        assert user_id == 123456789
        assert group_id is None

    def test_napcat_parse_target_group(self, provider):
        """Test NapcatProvider parses group message target."""
        user_id, group_id = provider._parse_target("group:987654321")
        assert user_id is None
        assert group_id == 987654321

    def test_napcat_parse_target_invalid_format(self, provider):
        """Test NapcatProvider handles invalid target format."""
        user_id, group_id = provider._parse_target("invalid")
        assert user_id is None
        assert group_id is None

    def test_napcat_parse_target_invalid_id(self, provider):
        """Test NapcatProvider handles non-numeric target ID."""
        user_id, group_id = provider._parse_target("private:not_a_number")
        assert user_id is None
        assert group_id is None

    def test_napcat_parse_target_unknown_type(self, provider):
        """Test NapcatProvider handles unknown target type."""
        user_id, group_id = provider._parse_target("unknown:123")
        assert user_id is None
        assert group_id is None

    @patch("httpx.Client")
    def test_napcat_send_text_private_success(self, mock_client_cls, provider):
        """Test NapcatProvider send_text to private chat."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok", "retcode": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_text("Hello QQ!", "private:123456")

        assert result.success is True
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/send_private_msg"
        payload = call_args[1]["json"]
        assert payload["user_id"] == 123456

        provider.disconnect()

    @patch("httpx.Client")
    def test_napcat_send_text_group_success(self, mock_client_cls, provider):
        """Test NapcatProvider send_text to group chat."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok", "retcode": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_text("Hello Group!", "group:654321")

        assert result.success is True
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/send_group_msg"
        payload = call_args[1]["json"]
        assert payload["group_id"] == 654321

        provider.disconnect()

    @patch("httpx.Client")
    def test_napcat_send_text_invalid_target(self, mock_client_cls, provider):
        """Test NapcatProvider send_text with invalid target."""
        provider.connect()
        result = provider.send_text("Test", "invalid_target")

        assert result.success is False
        assert "Invalid target format" in result.error

        provider.disconnect()

    @patch("httpx.Client")
    def test_napcat_send_text_api_error(self, mock_client_cls, provider):
        """Test NapcatProvider send_text handles API error."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "failed", "msg": "User not found"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_text("Test", "private:123")

        assert result.success is False

        provider.disconnect()

    @patch("httpx.Client")
    def test_napcat_send_text_tracks_message(
        self, mock_client_cls, provider_with_tracker, mock_tracker
    ):
        """Test NapcatProvider send_text tracks message."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider_with_tracker.connect()
        result = provider_with_tracker.send_text("Tracked", "private:123")

        mock_tracker.track.assert_called_once()
        mock_tracker.update_status.assert_called_once_with(result.message_id, MessageStatus.SENT)

        provider_with_tracker.disconnect()

    def test_napcat_send_card_not_supported(self, provider):
        """Test NapcatProvider send_card returns not supported."""
        provider.connect()
        result = provider.send_card({"card": "data"}, "private:123")

        assert result.success is False
        assert "not supported" in result.error.lower()

        provider.disconnect()

    @patch("httpx.Client")
    def test_napcat_send_rich_text_success(self, mock_client_cls, provider):
        """Test NapcatProvider send_rich_text converts to segments."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        content = [[{"type": "text", "text": "Hello"}]]
        result = provider.send_rich_text("Title", content, "group:123")

        assert result.success is True

        provider.disconnect()

    @patch("httpx.Client")
    def test_napcat_send_image_success(self, mock_client_cls, provider):
        """Test NapcatProvider send_image success."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_image("https://example.com/image.jpg", "private:123")

        assert result.success is True
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["message"][0]["type"] == "image"
        assert payload["message"][0]["data"]["file"] == "https://example.com/image.jpg"

        provider.disconnect()

    @patch("httpx.Client")
    def test_napcat_send_message_text_type(self, mock_client_cls, provider):
        """Test NapcatProvider send_message with TEXT type."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        message = Message(type=MessageType.TEXT, content="Hello")
        result = provider.send_message(message, "private:123")

        assert result.success is True

        provider.disconnect()

    @patch("httpx.Client")
    def test_napcat_send_message_image_type(self, mock_client_cls, provider):
        """Test NapcatProvider send_message with IMAGE type."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        provider.connect()
        message = Message(type=MessageType.IMAGE, content="http://img.url")
        result = provider.send_message(message, "group:123")

        assert result.success is True

        provider.disconnect()

    def test_napcat_send_message_card_type(self, provider):
        """Test NapcatProvider send_message with CARD type fails."""
        provider.connect()
        message = Message(type=MessageType.CARD, content={})
        result = provider.send_message(message, "private:123")

        assert result.success is False
        assert "not supported" in result.error.lower()

        provider.disconnect()

    def test_napcat_send_message_unsupported_type(self, provider):
        """Test NapcatProvider send_message with unsupported type."""
        provider.connect()
        message = Message(type=MessageType.FILE, content="file")
        result = provider.send_message(message, "private:123")

        assert result.success is False

        provider.disconnect()

    def test_napcat_send_without_connect_returns_error(self, provider):
        """Test NapcatProvider returns error if not connected."""
        result = provider.send_text("Test", "private:123")
        assert result.success is False
        assert "not connected" in result.error.lower()

    def test_napcat_capabilities(self, provider):
        """Test NapcatProvider capabilities."""
        caps = provider.get_capabilities()
        assert caps["text"] is True
        assert caps["rich_text"] is True
        assert caps["card"] is False  # Not supported by OneBot11
        assert caps["image"] is True
        assert caps["file"] is False
        assert caps["audio"] is False
        assert caps["video"] is False

    # Rich text conversion tests

    def test_napcat_convert_rich_text_with_title(self, provider):
        """Test NapcatProvider converts rich text with title."""
        segments = provider._convert_rich_text_to_segments("Title", [])
        assert len(segments) == 1
        assert segments[0]["data"]["text"] == "Title\n"

    def test_napcat_convert_rich_text_text_element(self, provider):
        """Test NapcatProvider converts text elements."""
        content = [[{"type": "text", "text": "Hello"}]]
        segments = provider._convert_rich_text_to_segments("", content)
        assert len(segments) == 1
        assert "Hello" in segments[0]["data"]["text"]

    def test_napcat_convert_rich_text_at_mention(self, provider):
        """Test NapcatProvider converts @mentions to CQ code."""
        content = [[{"type": "at", "user_id": "123456"}]]
        segments = provider._convert_rich_text_to_segments("", content)
        assert len(segments) == 1
        assert "[CQ:at,qq=123456]" in segments[0]["data"]["text"]

    def test_napcat_convert_rich_text_link(self, provider):
        """Test NapcatProvider converts links."""
        content = [[{"type": "link", "text": "Click", "href": "https://example.com"}]]
        segments = provider._convert_rich_text_to_segments("", content)
        assert len(segments) == 1
        assert "Click(https://example.com)" in segments[0]["data"]["text"]

    def test_napcat_convert_rich_text_mixed(self, provider):
        """Test NapcatProvider converts mixed content."""
        content = [
            [
                {"type": "text", "text": "Hello "},
                {"type": "at", "user_id": "123"},
                {"type": "text", "text": " check this "},
                {"type": "link", "text": "link", "href": "https://x.com"},
            ]
        ]
        segments = provider._convert_rich_text_to_segments("Test", content)
        assert len(segments) == 2  # Title + paragraph

    @patch("httpx.Client")
    @patch("time.sleep")
    def test_napcat_retry_on_http_error(self, mock_sleep, mock_client_cls, provider):
        """Test NapcatProvider retries on HTTP error."""
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=Mock(status_code=500)
        )

        mock_response_ok = Mock()
        mock_response_ok.json.return_value = {"status": "ok"}
        mock_response_ok.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.side_effect = [mock_response_fail, mock_response_ok]
        mock_client_cls.return_value = mock_client

        provider.connect()
        result = provider.send_text("Test", "private:123")

        assert result.success is True
        assert mock_client.post.call_count == 2

        provider.disconnect()


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestProviderIntegration:
    """Integration tests for provider components."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset registry before and after each test."""
        ProviderRegistry.reset_instance()
        yield
        ProviderRegistry.reset_instance()

    def test_multiple_provider_types_in_registry(self):
        """Test registry handles multiple provider types."""
        registry = ProviderRegistry()

        feishu_config = FeishuProviderConfig(
            url="https://feishu.webhook/test",
            name="feishu_1",
        )
        napcat_config = NapcatProviderConfig(
            http_url="http://127.0.0.1:3000",
            name="qq_1",
        )

        feishu_provider = FeishuProvider(feishu_config)
        napcat_provider = NapcatProvider(napcat_config)

        registry.register(feishu_provider)
        registry.register(napcat_provider)

        assert registry.get("feishu_1").provider_type == "feishu"
        assert registry.get("qq_1").provider_type == "napcat"

    def test_provider_with_shared_tracker(self):
        """Test multiple providers sharing message tracker."""
        tracker = Mock(spec=MessageTracker)

        feishu_config = FeishuProviderConfig(url="https://feishu/test", name="f1")
        napcat_config = NapcatProviderConfig(http_url="http://127.0.0.1:3000", name="q1")

        feishu = FeishuProvider(feishu_config, message_tracker=tracker)
        napcat = NapcatProvider(napcat_config, message_tracker=tracker)

        assert feishu._message_tracker is tracker
        assert napcat._message_tracker is tracker

    def test_provider_with_shared_circuit_breaker_config(self):
        """Test multiple providers with same circuit breaker config."""
        cb_config = CircuitBreakerConfig(failure_threshold=20)

        feishu_config = FeishuProviderConfig(url="https://feishu/test", name="f1")
        napcat_config = NapcatProviderConfig(http_url="http://127.0.0.1:3000", name="q1")

        feishu = FeishuProvider(feishu_config, circuit_breaker_config=cb_config)
        napcat = NapcatProvider(napcat_config, circuit_breaker_config=cb_config)

        assert feishu._circuit_breaker.config.failure_threshold == 20
        assert napcat._circuit_breaker.config.failure_threshold == 20

    @patch("httpx.Client")
    def test_provider_context_manager_with_operations(self, mock_client_cls):
        """Test provider context manager with actual operations."""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        config = FeishuProviderConfig(url="https://test.com/webhook", name="ctx_test")

        with FeishuProvider(config) as provider:
            result = provider.send_text("Test message", "")
            assert result.success is True

    def test_registry_clear_disconnects_all_providers(self):
        """Test registry.clear() disconnects all providers."""
        registry = ProviderRegistry()

        config1 = ProviderConfig(provider_type="test", name="p1")
        config2 = ProviderConfig(provider_type="test", name="p2")
        provider1 = ConcreteProvider(config1)
        provider2 = ConcreteProvider(config2)

        provider1.connect()
        provider2.connect()

        registry.register(provider1)
        registry.register(provider2)

        registry.clear()

        assert provider1.is_connected is False
        assert provider2.is_connected is False
