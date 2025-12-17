"""Tests for providers.qq_napcat module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.core.circuit_breaker import CircuitBreakerConfig
from feishu_webhook_bot.core.message_tracker import MessageTracker
from feishu_webhook_bot.providers.qq_napcat import NapcatProvider, NapcatProviderConfig


class TestNapcatProviderConfig:
    """Tests for NapcatProviderConfig."""

    def test_create_config(self) -> None:
        """Test creating Napcat provider config."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

        assert config.name == "test-napcat"
        assert config.http_url == "http://127.0.0.1:3000"
        assert config.provider_type == "napcat"
        assert config.access_token is None

    def test_create_config_with_token(self) -> None:
        """Test creating config with access token."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
            access_token="secret_token",
        )

        assert config.access_token == "secret_token"


class TestNapcatProvider:
    """Tests for NapcatProvider."""

    def test_init(self) -> None:
        """Test provider initialization."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

        provider = NapcatProvider(config)

        assert provider.config == config
        assert provider._client is None
        assert provider._connected is False

    def test_init_with_tracker(self) -> None:
        """Test provider initialization with message tracker."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        tracker = MagicMock(spec=MessageTracker)

        provider = NapcatProvider(config, message_tracker=tracker)

        assert provider._message_tracker is tracker

    def test_init_with_circuit_breaker_config(self) -> None:
        """Test provider initialization with circuit breaker config."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        cb_config = CircuitBreakerConfig(failure_threshold=5)

        provider = NapcatProvider(config, circuit_breaker_config=cb_config)

        assert provider._circuit_breaker is not None

    def test_connect(self) -> None:
        """Test connecting to Napcat API."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        provider.connect()

        assert provider._connected is True
        assert provider._client is not None

        provider.disconnect()

    def test_connect_with_token(self) -> None:
        """Test connecting with access token."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
            access_token="secret_token",
        )
        provider = NapcatProvider(config)

        provider.connect()

        assert provider._connected is True

        provider.disconnect()

    def test_disconnect(self) -> None:
        """Test disconnecting from Napcat API."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        provider.disconnect()

        assert provider._connected is False

    def test_parse_target_private(self) -> None:
        """Test parsing private message target."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        user_id, group_id = provider._parse_target("private:123456789")

        assert user_id == 123456789
        assert group_id is None

    def test_parse_target_group(self) -> None:
        """Test parsing group message target."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        user_id, group_id = provider._parse_target("group:987654321")

        assert user_id is None
        assert group_id == 987654321

    def test_parse_target_invalid_format(self) -> None:
        """Test parsing invalid target format."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        user_id, group_id = provider._parse_target("invalid")

        assert user_id is None
        assert group_id is None

    def test_parse_target_invalid_id(self) -> None:
        """Test parsing target with invalid ID."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        user_id, group_id = provider._parse_target("private:not_a_number")

        assert user_id is None
        assert group_id is None

    def test_send_text_invalid_target(self) -> None:
        """Test sending text with invalid target."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        result = provider.send_text("Hello", "invalid_target")

        assert result.success is False
        assert "Invalid target format" in result.error

        provider.disconnect()

    def test_send_card_not_supported(self) -> None:
        """Test sending card returns not supported."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        result = provider.send_card({}, "group:123456")

        assert result.success is False
        assert "not supported" in result.error.lower()

    def test_get_capabilities(self) -> None:
        """Test getting provider capabilities."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        caps = provider.get_capabilities()

        assert caps["text"] is True
        assert caps["rich_text"] is True
        assert caps["card"] is False
        assert caps["image"] is True
        assert caps["file"] is True
        assert caps["audio"] is True
        assert caps["video"] is True
        assert caps["forward"] is True
        assert caps["poke"] is True

    def test_convert_rich_text_to_segments(self) -> None:
        """Test converting rich text to OneBot segments."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        content = [
            [{"type": "text", "text": "Hello "}],
            [{"type": "at", "user_id": "123456"}],
            [{"type": "link", "text": "Link", "href": "https://example.com"}],
        ]

        segments = provider._convert_rich_text_to_segments("Title", content)

        assert len(segments) >= 1
        assert segments[0]["type"] == "text"
        assert "Title" in segments[0]["data"]["text"]

    def test_convert_rich_text_without_title(self) -> None:
        """Test converting rich text without title."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        content = [[{"type": "text", "text": "Hello"}]]

        segments = provider._convert_rich_text_to_segments("", content)

        text_found = False
        for seg in segments:
            if seg["type"] == "text" and "Hello" in seg["data"]["text"]:
                text_found = True
                break

        assert text_found

    @patch.object(NapcatProvider, "_http_request_with_retry")
    def test_send_text_success(self, mock_request: MagicMock) -> None:
        """Test successful text message send."""
        mock_request.return_value = {"status": "ok", "data": {"message_id": 12345}}

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_text("Hello", "private:123456789")

        assert result.success is True

        provider.disconnect()

    @patch.object(NapcatProvider, "_http_request_with_retry")
    def test_send_text_failure(self, mock_request: MagicMock) -> None:
        """Test failed text message send."""
        mock_request.side_effect = Exception("Connection refused")

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_text("Hello", "private:123456789")

        assert result.success is False
        assert "Connection refused" in result.error

        provider.disconnect()

    @patch.object(NapcatProvider, "_http_request_with_retry")
    def test_send_image_success(self, mock_request: MagicMock) -> None:
        """Test successful image message send."""
        mock_request.return_value = {"status": "ok", "data": {"message_id": 12345}}

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_image("https://example.com/image.jpg", "group:123456")

        assert result.success is True

        provider.disconnect()

    @patch.object(NapcatProvider, "_http_request_with_retry")
    def test_send_rich_text_success(self, mock_request: MagicMock) -> None:
        """Test successful rich text message send."""
        mock_request.return_value = {"status": "ok", "data": {"message_id": 12345}}

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_rich_text(
            "Title",
            [[{"type": "text", "text": "Content"}]],
            "group:123456",
        )

        assert result.success is True

        provider.disconnect()

    def test_send_onebot_message_not_connected(self) -> None:
        """Test sending message when not connected raises error."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)

        with pytest.raises(RuntimeError, match="not connected"):
            provider._send_onebot_message(
                "msg_123",
                123456789,
                None,
                [{"type": "text", "data": {"text": "Hello"}}],
            )

    def test_send_onebot_message_no_target(self) -> None:
        """Test sending message without target raises error."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        with pytest.raises(ValueError, match="user_id or group_id"):
            provider._send_onebot_message(
                "msg_123",
                None,
                None,
                [{"type": "text", "data": {"text": "Hello"}}],
            )

        provider.disconnect()


class TestNapcatProviderOneBot11APIs:
    """Tests for OneBot11 API methods."""

    @patch.object(NapcatProvider, "_make_http_request")
    def test_delete_msg(self, mock_request: MagicMock) -> None:
        """Test deleting a message."""
        mock_request.return_value = {"status": "ok", "data": None}

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        result = provider.delete_msg(12345)

        assert result is True
        mock_request.assert_called_once()
        provider.disconnect()

    @patch.object(NapcatProvider, "_make_http_request")
    def test_delete_msg_failure(self, mock_request: MagicMock) -> None:
        """Test deleting a message failure."""
        mock_request.side_effect = Exception("API error")

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        result = provider.delete_msg(12345)

        assert result is False
        provider.disconnect()

    @patch.object(NapcatProvider, "_make_http_request")
    def test_get_login_info(self, mock_request: MagicMock) -> None:
        """Test getting login info."""
        mock_request.return_value = {
            "status": "ok",
            "data": {"user_id": 123456789, "nickname": "TestBot"},
        }

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        info = provider.get_login_info()

        assert info["user_id"] == 123456789
        assert info["nickname"] == "TestBot"
        provider.disconnect()

    @patch.object(NapcatProvider, "_make_http_request")
    def test_get_stranger_info(self, mock_request: MagicMock) -> None:
        """Test getting stranger info."""
        mock_request.return_value = {
            "status": "ok",
            "data": {
                "user_id": 123456789,
                "nickname": "TestUser",
                "sex": "male",
                "age": 25,
            },
        }

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        user = provider.get_stranger_info(123456789)

        assert user is not None
        assert user.user_id == 123456789
        assert user.nickname == "TestUser"
        assert user.sex == "male"
        provider.disconnect()

    @patch.object(NapcatProvider, "_make_http_request")
    def test_get_group_info(self, mock_request: MagicMock) -> None:
        """Test getting group info."""
        mock_request.return_value = {
            "status": "ok",
            "data": {
                "group_id": 987654321,
                "group_name": "Test Group",
                "member_count": 100,
                "max_member_count": 500,
            },
        }

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        group = provider.get_group_info(987654321)

        assert group is not None
        assert group.group_id == 987654321
        assert group.group_name == "Test Group"
        assert group.member_count == 100
        provider.disconnect()

    @patch.object(NapcatProvider, "_make_http_request")
    def test_set_group_ban(self, mock_request: MagicMock) -> None:
        """Test banning a group member."""
        mock_request.return_value = {"status": "ok", "data": None}

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        result = provider.set_group_ban(987654321, 123456789, duration=60)

        assert result is True
        provider.disconnect()

    @patch.object(NapcatProvider, "_make_http_request")
    def test_send_poke(self, mock_request: MagicMock) -> None:
        """Test sending poke."""
        mock_request.return_value = {"status": "ok", "data": None}

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()

        result = provider.send_poke(123456789, group_id=987654321)

        assert result is True
        provider.disconnect()

    @patch.object(NapcatProvider, "_http_request_with_retry")
    def test_send_audio(self, mock_request: MagicMock) -> None:
        """Test sending audio message."""
        mock_request.return_value = {"status": "ok", "data": {"message_id": 12345}}

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_audio("audio.mp3", "group:123456")

        assert result.success is True
        provider.disconnect()

    @patch.object(NapcatProvider, "_http_request_with_retry")
    def test_send_video(self, mock_request: MagicMock) -> None:
        """Test sending video message."""
        mock_request.return_value = {"status": "ok", "data": {"message_id": 12345}}

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_video("video.mp4", "group:123456")

        assert result.success is True
        provider.disconnect()

    @patch.object(NapcatProvider, "_http_request_with_retry")
    def test_send_reply(self, mock_request: MagicMock) -> None:
        """Test sending reply message."""
        mock_request.return_value = {"status": "ok", "data": {"message_id": 12345}}

        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )
        provider = NapcatProvider(config)
        provider.connect()
        provider._circuit_breaker.call = lambda fn, *args: fn(*args)

        result = provider.send_reply(99999, "Reply text", "group:123456")

        assert result.success is True
        provider.disconnect()
