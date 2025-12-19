"""Tests for providers.qq.async_provider module.

Tests cover:
- AsyncNapcatMixin async connection
- Async message sending methods
- Async group management operations
- Async message history retrieval
- Async OCR operations
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.providers.qq.async_provider import AsyncNapcatMixin
from feishu_webhook_bot.providers.qq.config import NapcatProviderConfig


class MockAsyncProvider(AsyncNapcatMixin):
    """Mock provider for testing async operations."""

    def __init__(self, config: NapcatProviderConfig):
        self.config = config
        self._async_client = None
        self._connected = False
        self._api_response = None
        self._api_error = None
        self._message_tracker = None  # Required by AsyncNapcatMixin
        self.name = config.name
        self.provider_type = "napcat"

    async def _async_call_api(self, endpoint: str, payload: dict) -> any:
        if self._api_error:
            raise self._api_error
        return self._api_response

    def _parse_target(self, target: str) -> tuple[int | None, int | None]:
        parts = target.split(":")
        if len(parts) != 2:
            return None, None
        target_type, target_id = parts[0], parts[1]
        try:
            if target_type == "private":
                return int(target_id), None
            elif target_type == "group":
                return None, int(target_id)
        except ValueError:
            pass
        return None, None

    def set_response(self, response):
        self._api_response = response
        self._api_error = None

    def set_error(self, error):
        self._api_error = error
        self._api_response = None


class TestAsyncNapcatMixinConnection:
    """Tests for async connection management."""

    @pytest.fixture
    def config(self):
        return NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

    @pytest.fixture
    def provider(self, config):
        return MockAsyncProvider(config)

    @pytest.mark.anyio
    async def test_async_connect(self, provider):
        """Test async connect creates client."""
        await provider.async_connect()

        assert provider._async_client is not None

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_connect_with_token(self):
        """Test async connect with access token."""
        config = NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
            access_token="secret_token",
        )
        provider = MockAsyncProvider(config)

        await provider.async_connect()

        assert provider._async_client is not None

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_disconnect(self, provider):
        """Test async disconnect."""
        await provider.async_connect()
        await provider.async_disconnect()

        assert provider._connected is False

    @pytest.mark.anyio
    async def test_async_context_manager(self, config):
        """Test async context manager protocol."""
        provider = MockAsyncProvider(config)

        async with provider:
            assert provider._async_client is not None

        assert provider._async_client is None


class TestAsyncNapcatMixinSendText:
    """Tests for async text sending."""

    @pytest.fixture
    def config(self):
        return NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

    @pytest.fixture
    def provider(self, config):
        return MockAsyncProvider(config)

    @pytest.mark.anyio
    async def test_async_send_text_private_success(self, provider):
        """Test async send text to private chat."""
        provider.set_response({"message_id": 12345})
        await provider.async_connect()

        result = await provider.async_send_text("Hello!", "private:123456789")

        assert result.success is True
        assert result.message_id is not None  # UUID is generated internally

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_send_text_group_success(self, provider):
        """Test async send text to group."""
        provider.set_response({"message_id": 67890})
        await provider.async_connect()

        result = await provider.async_send_text("Hello group!", "group:987654321")

        assert result.success is True

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_send_text_invalid_target(self, provider):
        """Test async send with invalid target."""
        await provider.async_connect()

        result = await provider.async_send_text("Hello!", "invalid")

        assert result.success is False
        assert "Invalid target" in result.error

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_send_text_failure(self, provider):
        """Test async send text failure."""
        provider.set_error(Exception("Connection refused"))
        await provider.async_connect()

        result = await provider.async_send_text("Hello!", "group:123456")

        assert result.success is False

        await provider.async_disconnect()


class TestAsyncNapcatMixinSendImage:
    """Tests for async image sending."""

    @pytest.fixture
    def config(self):
        return NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

    @pytest.fixture
    def provider(self, config):
        return MockAsyncProvider(config)

    @pytest.mark.anyio
    async def test_async_send_image_success(self, provider):
        """Test async send image."""
        provider.set_response({"message_id": 12345})
        await provider.async_connect()

        result = await provider.async_send_image("https://example.com/image.jpg", "group:123456")

        assert result.success is True

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_send_image_failure(self, provider):
        """Test async send image failure."""
        provider.set_error(Exception("Upload failed"))
        await provider.async_connect()

        result = await provider.async_send_image("https://example.com/img.jpg", "group:123")

        assert result.success is False

        await provider.async_disconnect()


class TestAsyncNapcatMixinSendReply:
    """Tests for async reply sending."""

    @pytest.fixture
    def config(self):
        return NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

    @pytest.fixture
    def provider(self, config):
        return MockAsyncProvider(config)

    @pytest.mark.anyio
    async def test_async_send_reply_success(self, provider):
        """Test async send reply."""
        provider.set_response({"message_id": 12345})
        await provider.async_connect()

        result = await provider.async_send_reply(99999, "Reply text", "group:123456")

        assert result.success is True

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_send_reply_invalid_target(self, provider):
        """Test async reply with invalid target."""
        await provider.async_connect()

        result = await provider.async_send_reply(99999, "Reply", "invalid")

        assert result.success is False

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_send_reply_failure(self, provider):
        """Test async reply failure."""
        provider.set_error(Exception("Error"))
        await provider.async_connect()

        result = await provider.async_send_reply(99999, "Reply", "group:123")

        assert result.success is False

        await provider.async_disconnect()


class TestAsyncNapcatMixinGroupOperations:
    """Tests for async group operations."""

    @pytest.fixture
    def config(self):
        return NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

    @pytest.fixture
    def provider(self, config):
        return MockAsyncProvider(config)

    @pytest.mark.anyio
    async def test_async_set_group_ban_success(self, provider):
        """Test async group ban."""
        provider.set_response(None)
        await provider.async_connect()

        result = await provider.async_set_group_ban(123456, 789012, duration=3600)

        assert result is True

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_set_group_ban_unban(self, provider):
        """Test async unban (duration=0)."""
        provider.set_response(None)
        await provider.async_connect()

        result = await provider.async_set_group_ban(123456, 789012, duration=0)

        assert result is True

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_set_group_ban_failure(self, provider):
        """Test async ban failure."""
        provider.set_error(Exception("Not admin"))
        await provider.async_connect()

        result = await provider.async_set_group_ban(123456, 789012)

        assert result is False

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_set_group_kick_success(self, provider):
        """Test async group kick."""
        provider.set_response(None)
        await provider.async_connect()

        result = await provider.async_set_group_kick(123456, 789012)

        assert result is True

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_set_group_kick_reject(self, provider):
        """Test async kick with reject add."""
        provider.set_response(None)
        await provider.async_connect()

        result = await provider.async_set_group_kick(123456, 789012, reject_add_request=True)

        assert result is True

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_set_group_kick_failure(self, provider):
        """Test async kick failure."""
        provider.set_error(Exception("Error"))
        await provider.async_connect()

        result = await provider.async_set_group_kick(123456, 789012)

        assert result is False

        await provider.async_disconnect()


class TestAsyncNapcatMixinMessageHistory:
    """Tests for async message history operations."""

    @pytest.fixture
    def config(self):
        return NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

    @pytest.fixture
    def provider(self, config):
        return MockAsyncProvider(config)

    @pytest.mark.anyio
    async def test_async_get_group_msg_history_success(self, provider):
        """Test async get group message history."""
        provider.set_response(
            {
                "messages": [
                    {"message_id": 1, "content": "Hello"},
                    {"message_id": 2, "content": "World"},
                ]
            }
        )
        await provider.async_connect()

        result = await provider.async_get_group_msg_history(123456)

        assert len(result) == 2

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_get_group_msg_history_with_params(self, provider):
        """Test history with custom params."""
        provider.set_response({"messages": []})
        await provider.async_connect()

        result = await provider.async_get_group_msg_history(123456, message_seq=1000, count=50)

        assert result == []

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_get_group_msg_history_failure(self, provider):
        """Test history retrieval failure."""
        provider.set_error(Exception("Error"))
        await provider.async_connect()

        result = await provider.async_get_group_msg_history(123456)

        assert result == []

        await provider.async_disconnect()


class TestAsyncNapcatMixinOCR:
    """Tests for async OCR operations."""

    @pytest.fixture
    def config(self):
        return NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

    @pytest.fixture
    def provider(self, config):
        return MockAsyncProvider(config)

    @pytest.mark.anyio
    async def test_async_ocr_image_success(self, provider):
        """Test async OCR."""
        provider.set_response(
            {
                "texts": [
                    {"text": "Hello", "coordinates": [0, 0, 100, 50]},
                    {"text": "World", "coordinates": [0, 50, 100, 100]},
                ]
            }
        )
        await provider.async_connect()

        result = await provider.async_ocr_image("https://example.com/image.jpg")

        assert len(result) == 2
        assert result[0]["text"] == "Hello"

        await provider.async_disconnect()

    @pytest.mark.anyio
    async def test_async_ocr_image_failure(self, provider):
        """Test async OCR failure."""
        provider.set_error(Exception("OCR failed"))
        await provider.async_connect()

        result = await provider.async_ocr_image("https://example.com/image.jpg")

        assert result == []

        await provider.async_disconnect()


class TestAsyncNapcatMixinNotConnected:
    """Tests for operations when not connected - async_connect is called automatically."""

    @pytest.fixture
    def config(self):
        return NapcatProviderConfig(
            name="test-napcat",
            http_url="http://127.0.0.1:3000",
        )

    @pytest.fixture
    def provider(self, config):
        return MockAsyncProvider(config)

    @pytest.mark.anyio
    async def test_async_send_text_auto_connects(self, provider):
        """Test send text auto connects."""
        provider.set_response({"message_id": 12345})

        result = await provider.async_send_text("Hello!", "group:123456")

        # The mixin auto-connects, so it should succeed
        assert result.success is True

    @pytest.mark.anyio
    async def test_async_send_text_invalid_target(self, provider):
        """Test send text with invalid target fails."""
        result = await provider.async_send_text("Hello!", "invalid")

        assert result.success is False
        assert "Invalid target" in result.error

    @pytest.mark.anyio
    async def test_async_send_image_auto_connects(self, provider):
        """Test send image auto connects."""
        provider.set_response({"message_id": 12345})

        result = await provider.async_send_image("https://example.com/img.jpg", "group:123")

        assert result.success is True

    @pytest.mark.anyio
    async def test_async_send_reply_auto_connects(self, provider):
        """Test send reply auto connects."""
        provider.set_response({"message_id": 12345})

        result = await provider.async_send_reply(99999, "Reply", "group:123")

        assert result.success is True
