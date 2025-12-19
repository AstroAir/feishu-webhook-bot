"""Tests for providers.feishu.webhook module.

Tests cover:
- FeishuProviderConfig
- FeishuProvider initialization
- FeishuProvider connect/disconnect
- FeishuProvider message sending methods
- Signature generation integration
- Circuit breaker integration
- Message tracker integration
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from feishu_webhook_bot.core.circuit_breaker import CircuitBreakerConfig
from feishu_webhook_bot.core.message_tracker import MessageStatus, MessageTracker
from feishu_webhook_bot.core.provider import Message, MessageType
from feishu_webhook_bot.providers.feishu.config import FeishuProviderConfig
from feishu_webhook_bot.providers.feishu.webhook import FeishuProvider


class TestFeishuProviderConfig:
    """Tests for FeishuProviderConfig."""

    def test_minimal_config(self) -> None:
        """Test minimal configuration."""
        config = FeishuProviderConfig(url="https://open.feishu.cn/webhook/xxx")

        assert config.url == "https://open.feishu.cn/webhook/xxx"
        assert config.provider_type == "feishu"
        assert config.secret is None
        assert config.headers == {}

    def test_full_config(self) -> None:
        """Test full configuration."""
        config = FeishuProviderConfig(
            name="my_bot",
            url="https://open.feishu.cn/webhook/xxx",
            secret="secret_key",
            headers={"X-Custom": "value"},
            timeout=30.0,
        )

        assert config.name == "my_bot"
        assert config.url == "https://open.feishu.cn/webhook/xxx"
        assert config.secret == "secret_key"
        assert config.headers == {"X-Custom": "value"}
        assert config.timeout == 30.0

    def test_default_provider_type(self) -> None:
        """Test default provider type is feishu."""
        config = FeishuProviderConfig(url="https://example.com")

        assert config.provider_type == "feishu"


class TestFeishuProviderInit:
    """Tests for FeishuProvider initialization."""

    def test_basic_init(self) -> None:
        """Test basic provider initialization."""
        config = FeishuProviderConfig(
            name="test_bot",
            url="https://open.feishu.cn/webhook/xxx",
        )

        provider = FeishuProvider(config)

        assert provider.config == config
        assert provider.name == "test_bot"
        assert provider.provider_type == "feishu"
        assert provider._client is None
        assert provider._connected is False

    def test_init_with_tracker(self) -> None:
        """Test initialization with message tracker."""
        config = FeishuProviderConfig(url="https://example.com")
        tracker = MagicMock(spec=MessageTracker)

        provider = FeishuProvider(config, message_tracker=tracker)

        assert provider._message_tracker is tracker

    def test_init_with_circuit_breaker_config(self) -> None:
        """Test initialization with circuit breaker config."""
        config = FeishuProviderConfig(url="https://example.com")
        cb_config = CircuitBreakerConfig(failure_threshold=10)

        provider = FeishuProvider(config, circuit_breaker_config=cb_config)

        assert provider._circuit_breaker is not None


class TestFeishuProviderConnection:
    """Tests for FeishuProvider connection management."""

    def test_connect(self) -> None:
        """Test connecting to Feishu API."""
        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)

        provider.connect()

        assert provider._connected is True
        assert provider._client is not None

        provider.disconnect()

    def test_connect_idempotent(self) -> None:
        """Test connect is idempotent."""
        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)

        provider.connect()
        client1 = provider._client

        provider.connect()
        client2 = provider._client

        assert client1 is client2

        provider.disconnect()

    def test_disconnect(self) -> None:
        """Test disconnecting from Feishu API."""
        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)

        provider.connect()
        provider.disconnect()

        assert provider._connected is False

    def test_context_manager(self) -> None:
        """Test provider as context manager."""
        config = FeishuProviderConfig(url="https://example.com")

        with FeishuProvider(config) as provider:
            assert provider._connected is True

        assert provider._connected is False


class TestFeishuProviderSendText:
    """Tests for FeishuProvider.send_text method."""

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_text_success(self, mock_request: MagicMock) -> None:
        """Test successful text message send."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com/webhook")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_text("Hello, World!", "")

        assert result.success is True
        assert result.message_id is not None
        mock_request.assert_called_once()

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_text_with_target_url(self, mock_request: MagicMock) -> None:
        """Test text message with explicit target URL."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com/default")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_text("Hello!", "https://example.com/custom")

        assert result.success is True

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_text_failure(self, mock_request: MagicMock) -> None:
        """Test text message send failure."""
        mock_request.side_effect = Exception("Connection refused")

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_text("Hello!", "")

        assert result.success is False
        assert "Connection refused" in result.error

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_text_with_tracker(self, mock_request: MagicMock) -> None:
        """Test text message with message tracker."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        tracker = MagicMock(spec=MessageTracker)
        provider = FeishuProvider(config, message_tracker=tracker)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_text("Hello!", "")

        assert result.success is True
        tracker.track.assert_called_once()
        tracker.update_status.assert_called_once()

        provider.disconnect()

    def test_send_text_not_connected(self) -> None:
        """Test send_text when not connected raises error."""
        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)

        result = provider.send_text("Hello!", "")

        assert result.success is False


class TestFeishuProviderSendCard:
    """Tests for FeishuProvider.send_card method."""

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_card_success(self, mock_request: MagicMock) -> None:
        """Test successful card message send."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        card = {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": "Test"}},
        }

        result = provider.send_card(card, "")

        assert result.success is True
        mock_request.assert_called_once()

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_card_failure(self, mock_request: MagicMock) -> None:
        """Test card message send failure."""
        mock_request.side_effect = Exception("Invalid card format")

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_card({}, "")

        assert result.success is False

        provider.disconnect()


class TestFeishuProviderSendRichText:
    """Tests for FeishuProvider.send_rich_text method."""

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_rich_text_success(self, mock_request: MagicMock) -> None:
        """Test successful rich text message send."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        content = [
            [{"tag": "text", "text": "Hello, "}],
            [{"tag": "at", "user_id": "ou_xxx"}],
        ]

        result = provider.send_rich_text("Title", content, "")

        assert result.success is True

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_rich_text_with_language(self, mock_request: MagicMock) -> None:
        """Test rich text with custom language."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_rich_text("Title", [[]], "", language="en_us")

        assert result.success is True

        provider.disconnect()


class TestFeishuProviderSendImage:
    """Tests for FeishuProvider.send_image method."""

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_image_success(self, mock_request: MagicMock) -> None:
        """Test successful image message send."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_image("img_xxx", "")

        assert result.success is True

        provider.disconnect()


class TestFeishuProviderSendMessage:
    """Tests for FeishuProvider.send_message method."""

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_message_text(self, mock_request: MagicMock) -> None:
        """Test send_message with TEXT type."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        message = Message(type=MessageType.TEXT, content="Hello!")
        result = provider.send_message(message, "")

        assert result.success is True

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_message_card(self, mock_request: MagicMock) -> None:
        """Test send_message with CARD type."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        message = Message(type=MessageType.CARD, content={"header": {}})
        result = provider.send_message(message, "")

        assert result.success is True

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_message_rich_text(self, mock_request: MagicMock) -> None:
        """Test send_message with RICH_TEXT type."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        message = Message(
            type=MessageType.RICH_TEXT,
            content={"title": "Test", "content": [[]]},
        )
        result = provider.send_message(message, "")

        assert result.success is True

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_message_image(self, mock_request: MagicMock) -> None:
        """Test send_message with IMAGE type."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        message = Message(type=MessageType.IMAGE, content="img_xxx")
        result = provider.send_message(message, "")

        assert result.success is True

        provider.disconnect()

    def test_send_message_unsupported_type(self) -> None:
        """Test send_message with unsupported type."""
        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()

        message = Message(type=MessageType.FILE, content="file_xxx")
        result = provider.send_message(message, "")

        assert result.success is False
        assert "Unsupported" in result.error

        provider.disconnect()


class TestFeishuProviderSignature:
    """Tests for FeishuProvider signature integration."""

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_with_signature(self, mock_request: MagicMock) -> None:
        """Test message includes signature when secret configured."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(
            url="https://example.com",
            secret="test_secret",
        )
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        provider.send_text("Hello!", "")

        call_args = mock_request.call_args
        payload = call_args[1]["payload"]

        assert "sign" in payload
        assert "timestamp" in payload

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_send_without_signature(self, mock_request: MagicMock) -> None:
        """Test message without signature when no secret."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        provider.send_text("Hello!", "")

        call_args = mock_request.call_args
        payload = call_args[1]["payload"]

        assert "sign" not in payload
        assert "timestamp" not in payload

        provider.disconnect()

    def test_generate_sign_method(self) -> None:
        """Test _generate_sign method."""
        config = FeishuProviderConfig(
            url="https://example.com",
            secret="test_secret",
        )
        provider = FeishuProvider(config)

        sign = provider._generate_sign(1704067200)

        assert isinstance(sign, str)
        assert len(sign) > 0

    def test_generate_sign_no_secret(self) -> None:
        """Test _generate_sign returns empty without secret."""
        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)

        sign = provider._generate_sign(1704067200)

        assert sign == ""


class TestFeishuProviderCapabilities:
    """Tests for FeishuProvider.get_capabilities method."""

    def test_get_capabilities(self) -> None:
        """Test provider capabilities."""
        config = FeishuProviderConfig(url="https://example.com")
        provider = FeishuProvider(config)

        caps = provider.get_capabilities()

        assert caps["text"] is True
        assert caps["rich_text"] is True
        assert caps["card"] is True
        assert caps["image"] is True
        assert caps["file"] is False
        assert caps["audio"] is False
        assert caps["video"] is False


class TestFeishuProviderTrackerIntegration:
    """Tests for FeishuProvider message tracker integration."""

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_tracker_success_flow(self, mock_request: MagicMock) -> None:
        """Test tracker is updated on success."""
        mock_request.return_value = {"code": 0, "msg": "success"}

        config = FeishuProviderConfig(url="https://example.com")
        tracker = MagicMock(spec=MessageTracker)
        provider = FeishuProvider(config, message_tracker=tracker)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        provider.send_text("Hello!", "")

        tracker.track.assert_called_once()
        tracker.update_status.assert_called_once()

        call_args = tracker.update_status.call_args
        assert call_args[0][1] == MessageStatus.SENT

        provider.disconnect()

    @patch.object(FeishuProvider, "_http_request_with_retry")
    def test_tracker_failure_flow(self, mock_request: MagicMock) -> None:
        """Test tracker is updated on failure."""
        mock_request.side_effect = Exception("Network error")

        config = FeishuProviderConfig(url="https://example.com")
        tracker = MagicMock(spec=MessageTracker)
        provider = FeishuProvider(config, message_tracker=tracker)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        provider.send_text("Hello!", "")

        tracker.track.assert_called_once()
        tracker.update_status.assert_called_once()

        call_args = tracker.update_status.call_args
        assert call_args[0][1] == MessageStatus.FAILED
        assert "error" in call_args[1]

        provider.disconnect()
