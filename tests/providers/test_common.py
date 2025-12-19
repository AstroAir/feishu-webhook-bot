"""Tests for providers.common module.

Tests cover:
- ProviderResponse model
- MessageContext dataclass
- RetryConfig dataclass
- AsyncHTTPProviderMixin
- EnhancedBaseProvider
- Utility functions (validate_response, parse_target, safe_int, truncate_string)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from feishu_webhook_bot.providers.common.async_http import AsyncHTTPProviderMixin
from feishu_webhook_bot.providers.common.models import (
    MessageContext,
    ProviderResponse,
    RetryConfig,
)
from feishu_webhook_bot.providers.common.utils import (
    create_response_validator,
    log_message_result,
    parse_target,
    safe_int,
    truncate_string,
    validate_response,
)

# ==============================================================================
# ProviderResponse Tests
# ==============================================================================


class TestProviderResponse:
    """Tests for ProviderResponse model."""

    def test_ok_factory_with_data(self) -> None:
        """Test ProviderResponse.ok() with data."""
        response = ProviderResponse.ok(data={"user_id": 123}, raw_response={"code": 0})

        assert response.success is True
        assert response.data == {"user_id": 123}
        assert response.error_code == 0
        assert response.error_msg == ""
        assert response.raw_response == {"code": 0}

    def test_ok_factory_without_data(self) -> None:
        """Test ProviderResponse.ok() without data."""
        response = ProviderResponse.ok()

        assert response.success is True
        assert response.data is None
        assert response.raw_response == {}

    def test_fail_factory_with_details(self) -> None:
        """Test ProviderResponse.fail() with error details."""
        response = ProviderResponse.fail(
            error_msg="Invalid token",
            error_code=10001,
            raw_response={"code": 10001, "msg": "Invalid token"},
        )

        assert response.success is False
        assert response.error_msg == "Invalid token"
        assert response.error_code == 10001
        assert response.raw_response == {"code": 10001, "msg": "Invalid token"}

    def test_fail_factory_defaults(self) -> None:
        """Test ProviderResponse.fail() with defaults."""
        response = ProviderResponse.fail("Error occurred")

        assert response.success is False
        assert response.error_msg == "Error occurred"
        assert response.error_code == -1
        assert response.raw_response == {}

    def test_direct_construction(self) -> None:
        """Test direct ProviderResponse construction."""
        response = ProviderResponse(
            success=True,
            data="test_data",
            error_code=0,
            error_msg="",
        )

        assert response.success is True
        assert response.data == "test_data"


# ==============================================================================
# MessageContext Tests
# ==============================================================================


class TestMessageContext:
    """Tests for MessageContext dataclass."""

    def test_create_message_context(self) -> None:
        """Test creating MessageContext."""
        ctx = MessageContext(
            message_id="msg_123",
            message_type="text",
            target="group:123456",
            provider_name="test_bot",
            provider_type="napcat",
        )

        assert ctx.message_id == "msg_123"
        assert ctx.message_type == "text"
        assert ctx.target == "group:123456"
        assert ctx.provider_name == "test_bot"
        assert ctx.provider_type == "napcat"

    def test_message_context_equality(self) -> None:
        """Test MessageContext equality."""
        ctx1 = MessageContext(
            message_id="msg_123",
            message_type="text",
            target="target",
            provider_name="bot",
            provider_type="type",
        )
        ctx2 = MessageContext(
            message_id="msg_123",
            message_type="text",
            target="target",
            provider_name="bot",
            provider_type="type",
        )

        assert ctx1 == ctx2


# ==============================================================================
# RetryConfig Tests
# ==============================================================================


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self) -> None:
        """Test RetryConfig default values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.backoff_seconds == 1.0
        assert config.backoff_multiplier == 2.0
        assert config.max_backoff_seconds == 30.0

    def test_custom_values(self) -> None:
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_attempts=5,
            backoff_seconds=0.5,
            backoff_multiplier=1.5,
            max_backoff_seconds=60.0,
        )

        assert config.max_attempts == 5
        assert config.backoff_seconds == 0.5
        assert config.backoff_multiplier == 1.5
        assert config.max_backoff_seconds == 60.0

    def test_from_policy_none(self) -> None:
        """Test RetryConfig.from_policy with None returns defaults."""
        config = RetryConfig.from_policy(None)

        assert config.max_attempts == 3
        assert config.backoff_seconds == 1.0

    def test_from_policy_with_values(self) -> None:
        """Test RetryConfig.from_policy with policy object."""
        mock_policy = MagicMock()
        mock_policy.max_attempts = 5
        mock_policy.backoff_seconds = 2.0
        mock_policy.backoff_multiplier = 3.0
        mock_policy.max_backoff_seconds = 120.0

        config = RetryConfig.from_policy(mock_policy)

        assert config.max_attempts == 5
        assert config.backoff_seconds == 2.0
        assert config.backoff_multiplier == 3.0
        assert config.max_backoff_seconds == 120.0

    def test_from_policy_partial_values(self) -> None:
        """Test RetryConfig.from_policy with partial values uses defaults."""
        mock_policy = MagicMock(spec=[])

        config = RetryConfig.from_policy(mock_policy)

        assert config.max_attempts == 3
        assert config.backoff_seconds == 1.0


# ==============================================================================
# Utility Functions Tests
# ==============================================================================


class TestValidateResponse:
    """Tests for validate_response function."""

    def test_validate_success_response(self) -> None:
        """Test validation passes for successful response."""
        result = {"code": 0, "msg": "success", "data": {}}

        validate_response(result)

    def test_validate_failure_raises(self) -> None:
        """Test validation raises for failed response."""
        result = {"code": 10001, "msg": "Invalid token"}

        with pytest.raises(ValueError, match="API error.*Invalid token"):
            validate_response(result)

    def test_validate_custom_fields(self) -> None:
        """Test validation with custom field names."""
        result = {"status": "ok", "message": "success"}

        validate_response(
            result,
            error_field="status",
            success_value="ok",
            message_field="message",
        )

    def test_validate_custom_fields_failure(self) -> None:
        """Test validation with custom fields raises on failure."""
        result = {"status": "failed", "message": "Error"}

        with pytest.raises(ValueError, match="API error.*Error"):
            validate_response(
                result,
                error_field="status",
                success_value="ok",
                message_field="message",
            )


class TestCreateResponseValidator:
    """Tests for create_response_validator function."""

    def test_create_default_validator(self) -> None:
        """Test creating validator with defaults."""
        validator = create_response_validator()

        validator({"code": 0, "msg": "ok"})

        with pytest.raises(ValueError):
            validator({"code": 1, "msg": "error"})

    def test_create_custom_validator(self) -> None:
        """Test creating validator with custom settings."""
        validator = create_response_validator(
            error_field="status",
            success_value="ok",
            message_field="msg",
        )

        validator({"status": "ok", "msg": "success"})

        with pytest.raises(ValueError):
            validator({"status": "failed", "msg": "error"})


class TestParseTarget:
    """Tests for parse_target function."""

    def test_parse_group_target(self) -> None:
        """Test parsing group target."""
        target_type, target_id = parse_target("group:123456789")

        assert target_type == "group"
        assert target_id == "123456789"

    def test_parse_private_target(self) -> None:
        """Test parsing private target."""
        target_type, target_id = parse_target("private:987654321")

        assert target_type == "private"
        assert target_id == "987654321"

    def test_parse_custom_separator(self) -> None:
        """Test parsing with custom separator."""
        target_type, target_id = parse_target("user|12345", separator="|")

        assert target_type == "user"
        assert target_id == "12345"

    def test_parse_invalid_format(self) -> None:
        """Test parsing invalid format returns empty strings."""
        target_type, target_id = parse_target("invalid")

        assert target_type == ""
        assert target_id == ""

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string."""
        target_type, target_id = parse_target("")

        assert target_type == ""
        assert target_id == ""

    def test_parse_multiple_separators(self) -> None:
        """Test parsing with multiple separators only splits on first."""
        target_type, target_id = parse_target("type:id:extra")

        assert target_type == "type"
        assert target_id == "id:extra"


class TestSafeInt:
    """Tests for safe_int function."""

    def test_convert_valid_int(self) -> None:
        """Test converting valid integer."""
        assert safe_int(42) == 42

    def test_convert_string_int(self) -> None:
        """Test converting string to integer."""
        assert safe_int("123") == 123

    def test_convert_float(self) -> None:
        """Test converting float to integer."""
        assert safe_int(3.14) == 3

    def test_invalid_returns_default(self) -> None:
        """Test invalid value returns default."""
        assert safe_int("not_a_number") == 0

    def test_invalid_with_custom_default(self) -> None:
        """Test invalid value with custom default."""
        assert safe_int("invalid", default=-1) == -1

    def test_none_returns_default(self) -> None:
        """Test None returns default."""
        assert safe_int(None) == 0

    def test_empty_string_returns_default(self) -> None:
        """Test empty string returns default."""
        assert safe_int("") == 0


class TestTruncateString:
    """Tests for truncate_string function."""

    def test_short_string_unchanged(self) -> None:
        """Test short string is not truncated."""
        result = truncate_string("Hello", max_length=100)

        assert result == "Hello"

    def test_exact_length_unchanged(self) -> None:
        """Test string at exact max length is unchanged."""
        result = truncate_string("Hello", max_length=5)

        assert result == "Hello"

    def test_long_string_truncated(self) -> None:
        """Test long string is truncated with suffix."""
        result = truncate_string("Hello World", max_length=8)

        assert result == "Hello..."
        assert len(result) == 8

    def test_custom_suffix(self) -> None:
        """Test truncation with custom suffix."""
        result = truncate_string("Hello World", max_length=10, suffix="…")

        assert result == "Hello Wor…"
        assert len(result) == 10

    def test_empty_suffix(self) -> None:
        """Test truncation with empty suffix."""
        result = truncate_string("Hello World", max_length=5, suffix="")

        assert result == "Hello"

    def test_empty_string(self) -> None:
        """Test empty string."""
        result = truncate_string("", max_length=10)

        assert result == ""


class TestLogMessageResult:
    """Tests for log_message_result function."""

    def test_log_success(self) -> None:
        """Test logging successful message."""
        log_message_result(
            success=True,
            message_type="text",
            message_id="msg_123",
            target="group:123456",
            provider_name="test_bot",
            provider_type="napcat",
        )

    def test_log_failure(self) -> None:
        """Test logging failed message."""
        log_message_result(
            success=False,
            message_type="text",
            message_id="msg_123",
            target="group:123456",
            provider_name="test_bot",
            provider_type="napcat",
            error="Connection refused",
        )


# ==============================================================================
# AsyncHTTPProviderMixin Tests
# ==============================================================================


class TestAsyncHTTPProviderMixin:
    """Tests for AsyncHTTPProviderMixin."""

    @pytest.mark.anyio
    async def test_async_http_request_success(self) -> None:
        """Test successful async HTTP request."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "data": "test"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = await mixin._async_http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={"key": "value"},
            retry_policy=None,
            provider_name="test-provider",
            provider_type="test",
        )

        assert result == {"status": "ok", "data": "test"}
        mock_client.post.assert_called_once()

    @pytest.mark.anyio
    async def test_async_http_request_no_client_raises(self) -> None:
        """Test request fails when client is None."""
        mixin = AsyncHTTPProviderMixin()

        with pytest.raises(RuntimeError, match="Async HTTP client not initialized"):
            await mixin._async_http_request_with_retry(
                client=None,
                url="https://api.example.com/test",
                payload={},
                retry_policy=None,
                provider_name="test-provider",
                provider_type="test",
            )

    @pytest.mark.anyio
    async def test_async_http_request_get_method(self) -> None:
        """Test async HTTP GET request."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        result = await mixin._async_http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={"q": "search"},
            retry_policy=None,
            provider_name="test",
            provider_type="test",
            method="GET",
        )

        assert result == {"data": "test"}
        mock_client.get.assert_called_once()

    @pytest.mark.anyio
    async def test_async_http_request_with_headers(self) -> None:
        """Test async HTTP request with custom headers."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        await mixin._async_http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={},
            retry_policy=None,
            provider_name="test",
            provider_type="test",
            headers={"Authorization": "Bearer token"},
        )

        mock_client.post.assert_called_with(
            "https://api.example.com/test",
            json={},
            headers={"Authorization": "Bearer token"},
        )

    @pytest.mark.anyio
    async def test_async_http_request_with_validator(self) -> None:
        """Test async request with response validator."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        def validator(result: dict[str, Any]) -> None:
            if result.get("status") != "ok":
                raise ValueError("Invalid response")

        result = await mixin._async_http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={},
            retry_policy=None,
            provider_name="test",
            provider_type="test",
            response_validator=validator,
        )

        assert result == {"status": "ok"}

    @pytest.mark.anyio
    async def test_async_http_request_validator_fails(self) -> None:
        """Test async request fails when validator raises."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "error"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        def validator(result: dict[str, Any]) -> None:
            if result.get("status") != "ok":
                raise ValueError("Invalid response")

        with pytest.raises(ValueError, match="Invalid response"):
            await mixin._async_http_request_with_retry(
                client=mock_client,
                url="https://api.example.com/test",
                payload={},
                retry_policy=None,
                provider_name="test",
                provider_type="test",
                response_validator=validator,
            )

    @pytest.mark.anyio
    async def test_async_http_request_retries_on_error(self) -> None:
        """Test async request retries on HTTP error."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        mock_error_response = MagicMock()
        mock_error_response.status_code = 500

        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {"status": "ok"}
        mock_success_response.raise_for_status = MagicMock()

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.HTTPStatusError(
                    "Server Error",
                    request=MagicMock(),
                    response=mock_error_response,
                )
            return mock_success_response

        mock_client.post.side_effect = side_effect

        mock_retry_policy = MagicMock()
        mock_retry_policy.max_attempts = 3
        mock_retry_policy.backoff_seconds = 0.01
        mock_retry_policy.backoff_multiplier = 2.0
        mock_retry_policy.max_backoff_seconds = 1.0

        result = await mixin._async_http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={},
            retry_policy=mock_retry_policy,
            provider_name="test",
            provider_type="test",
        )

        assert result == {"status": "ok"}
        assert mock_client.post.call_count == 2

    @pytest.mark.anyio
    async def test_async_request_json_simple(self) -> None:
        """Test simple async request without retry."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_client.request.return_value = mock_response

        result = await mixin._async_request_json(
            client=mock_client,
            method="POST",
            url="https://api.example.com/test",
            json={"key": "value"},
        )

        assert result == mock_response
        mock_client.request.assert_called_once()

    @pytest.mark.anyio
    async def test_async_request_json_no_client_raises(self) -> None:
        """Test _async_request_json raises when client is None."""
        mixin = AsyncHTTPProviderMixin()

        with pytest.raises(RuntimeError, match="Async HTTP client not initialized"):
            await mixin._async_request_json(
                client=None,
                method="GET",
                url="https://api.example.com/test",
            )

    @pytest.mark.anyio
    async def test_async_http_request_delete_method(self) -> None:
        """Test async HTTP DELETE request."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"deleted": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.delete.return_value = mock_response

        result = await mixin._async_http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test/123",
            payload={},
            retry_policy=None,
            provider_name="test",
            provider_type="test",
            method="DELETE",
        )

        assert result == {"deleted": True}
        mock_client.delete.assert_called_once()

    @pytest.mark.anyio
    async def test_async_http_request_put_method(self) -> None:
        """Test async HTTP PUT request."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"updated": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.put.return_value = mock_response

        result = await mixin._async_http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test/123",
            payload={"name": "updated"},
            retry_policy=None,
            provider_name="test",
            provider_type="test",
            method="PUT",
        )

        assert result == {"updated": True}
        mock_client.put.assert_called_once()

    @pytest.mark.anyio
    async def test_async_http_request_patch_method(self) -> None:
        """Test async HTTP PATCH request."""
        mixin = AsyncHTTPProviderMixin()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {"patched": True}
        mock_response.raise_for_status = MagicMock()
        mock_client.patch.return_value = mock_response

        result = await mixin._async_http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test/123",
            payload={"field": "value"},
            retry_policy=None,
            provider_name="test",
            provider_type="test",
            method="PATCH",
        )

        assert result == {"patched": True}
        mock_client.patch.assert_called_once()
