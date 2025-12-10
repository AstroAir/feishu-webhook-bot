"""Tests for providers.base_http module."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from feishu_webhook_bot.providers.base_http import HTTPProviderMixin


class TestHTTPProviderMixin:
    """Tests for HTTPProviderMixin."""

    def test_http_request_with_retry_success(self) -> None:
        """Test successful HTTP request."""
        mixin = HTTPProviderMixin()
        mock_client = MagicMock(spec=httpx.Client)
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "data": "test"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = mixin._http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={"key": "value"},
            retry_policy=None,
            provider_name="test-provider",
            provider_type="test",
        )

        assert result == {"status": "ok", "data": "test"}
        mock_client.post.assert_called_once()

    def test_http_request_with_retry_no_client(self) -> None:
        """Test request fails when client is None."""
        mixin = HTTPProviderMixin()

        with pytest.raises(RuntimeError, match="HTTP client not initialized"):
            mixin._http_request_with_retry(
                client=None,
                url="https://api.example.com/test",
                payload={},
                retry_policy=None,
                provider_name="test-provider",
                provider_type="test",
            )

    def test_http_request_with_retry_retries_on_http_error(self) -> None:
        """Test request retries on HTTP error."""
        mixin = HTTPProviderMixin()
        mock_client = MagicMock(spec=httpx.Client)

        mock_error_response = MagicMock()
        mock_error_response.status_code = 500

        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {"status": "ok"}
        mock_success_response.raise_for_status = MagicMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                error = httpx.HTTPStatusError(
                    "Server Error",
                    request=MagicMock(),
                    response=mock_error_response,
                )
                raise error
            return mock_success_response

        mock_client.post.side_effect = side_effect

        mock_retry_policy = MagicMock()
        mock_retry_policy.max_attempts = 3
        mock_retry_policy.backoff_seconds = 0.01
        mock_retry_policy.backoff_multiplier = 2.0
        mock_retry_policy.max_backoff_seconds = 1.0

        result = mixin._http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={},
            retry_policy=mock_retry_policy,
            provider_name="test-provider",
            provider_type="test",
        )

        assert result == {"status": "ok"}
        assert mock_client.post.call_count == 2

    def test_http_request_with_retry_exhausts_retries(self) -> None:
        """Test request fails after exhausting retries."""
        mixin = HTTPProviderMixin()
        mock_client = MagicMock(spec=httpx.Client)

        mock_error_response = MagicMock()
        mock_error_response.status_code = 500

        error = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_error_response,
        )
        mock_client.post.side_effect = error

        mock_retry_policy = MagicMock()
        mock_retry_policy.max_attempts = 2
        mock_retry_policy.backoff_seconds = 0.01
        mock_retry_policy.backoff_multiplier = 2.0
        mock_retry_policy.max_backoff_seconds = 1.0

        with pytest.raises(httpx.HTTPStatusError):
            mixin._http_request_with_retry(
                client=mock_client,
                url="https://api.example.com/test",
                payload={},
                retry_policy=mock_retry_policy,
                provider_name="test-provider",
                provider_type="test",
            )

        assert mock_client.post.call_count == 2

    def test_http_request_with_response_validator(self) -> None:
        """Test request with response validator."""
        mixin = HTTPProviderMixin()
        mock_client = MagicMock(spec=httpx.Client)
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        def validator(result):
            if result.get("status") != "ok":
                raise ValueError("Invalid response")

        result = mixin._http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={},
            retry_policy=None,
            provider_name="test-provider",
            provider_type="test",
            response_validator=validator,
        )

        assert result == {"status": "ok"}

    def test_http_request_with_failing_validator(self) -> None:
        """Test request fails when validator raises."""
        mixin = HTTPProviderMixin()
        mock_client = MagicMock(spec=httpx.Client)
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "error"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        def validator(result):
            if result.get("status") != "ok":
                raise ValueError("Invalid response")

        with pytest.raises(ValueError, match="Invalid response"):
            mixin._http_request_with_retry(
                client=mock_client,
                url="https://api.example.com/test",
                payload={},
                retry_policy=None,
                provider_name="test-provider",
                provider_type="test",
                response_validator=validator,
            )

    def test_http_request_default_retry_values(self) -> None:
        """Test request uses default retry values when policy is None."""
        mixin = HTTPProviderMixin()
        mock_client = MagicMock(spec=httpx.Client)
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = mixin._http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={},
            retry_policy=None,
            provider_name="test-provider",
            provider_type="test",
        )

        assert result == {"status": "ok"}

    def test_log_message_send_result_success(self) -> None:
        """Test logging successful message send."""
        mixin = HTTPProviderMixin()

        mixin._log_message_send_result(
            success=True,
            message_type="text",
            message_id="msg_123",
            target="https://webhook.example.com",
            provider_name="test-provider",
            provider_type="feishu",
        )

    def test_log_message_send_result_failure(self) -> None:
        """Test logging failed message send."""
        mixin = HTTPProviderMixin()

        mixin._log_message_send_result(
            success=False,
            message_type="text",
            message_id="msg_123",
            target="https://webhook.example.com",
            provider_name="test-provider",
            provider_type="feishu",
            error="Connection refused",
        )

    def test_http_request_retries_on_generic_exception(self) -> None:
        """Test request retries on generic exceptions."""
        mixin = HTTPProviderMixin()
        mock_client = MagicMock(spec=httpx.Client)

        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {"status": "ok"}
        mock_success_response.raise_for_status = MagicMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network error")
            return mock_success_response

        mock_client.post.side_effect = side_effect

        mock_retry_policy = MagicMock()
        mock_retry_policy.max_attempts = 3
        mock_retry_policy.backoff_seconds = 0.01
        mock_retry_policy.backoff_multiplier = 2.0
        mock_retry_policy.max_backoff_seconds = 1.0

        result = mixin._http_request_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            payload={},
            retry_policy=mock_retry_policy,
            provider_name="test-provider",
            provider_type="test",
        )

        assert result == {"status": "ok"}
        assert mock_client.post.call_count == 2
