"""Tests for the event server module."""

import base64
import hashlib
import hmac
import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from feishu_webhook_bot.core.config import EventServerConfig, ProviderConfigBase
from feishu_webhook_bot.core.event_server import EventServer


@pytest.fixture
def event_handler():
    """Mock event handler."""
    return MagicMock()


@pytest.fixture
def basic_config():
    """Basic event server config."""
    return EventServerConfig(
        enabled=True,
        host="127.0.0.1",
        port=8000,
        path="/webhook",
    )


@pytest.fixture
def config_with_auth(basic_config):
    """Config with authentication."""
    basic_config.verification_token = "test_token_12345"
    basic_config.signature_secret = "test_secret"
    return basic_config


def test_event_server_initialization(basic_config, event_handler):
    """Test event server initialization."""
    server = EventServer(basic_config, event_handler)
    
    assert server._config == basic_config
    assert server._handler == event_handler
    assert server._app is not None
    assert server._server is None
    assert server._thread is None


def test_event_server_health_check(basic_config, event_handler):
    """Test health check endpoint."""
    server = EventServer(basic_config, event_handler)
    client = TestClient(server._app)
    
    response = client.get("/healthz")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_event_server_url_verification(basic_config, event_handler):
    """Test URL verification challenge."""
    server = EventServer(basic_config, event_handler)
    client = TestClient(server._app)
    
    payload = {
        "type": "url_verification",
        "challenge": "test_challenge_123",
    }
    
    response = client.post("/webhook", json=payload)
    
    assert response.status_code == 200
    assert response.json() == {"challenge": "test_challenge_123"}
    event_handler.assert_not_called()


def test_event_server_receive_event(basic_config, event_handler):
    """Test receiving and handling event."""
    server = EventServer(basic_config, event_handler)
    client = TestClient(server._app)
    
    payload = {
        "type": "message",
        "event": {
            "text": "Hello",
            "sender": {"user_id": "user123"}
        }
    }
    
    response = client.post("/webhook", json=payload)
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    # Event server adds _provider to payload before calling handler
    expected_payload = {**payload, "_provider": "feishu"}
    event_handler.assert_called_once_with(expected_payload)


def test_event_server_verification_token_valid(config_with_auth, event_handler):
    """Test event with valid verification token."""
    server = EventServer(config_with_auth, event_handler)
    client = TestClient(server._app)
    
    payload = {
        "type": "message",
        "token": "test_token_12345",
        "event": {"text": "Hello"}
    }

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    timestamp = "1234567890"
    nonce = "token-valid-test"
    message = (timestamp + nonce).encode("utf-8") + body
    digest = hmac.new("test_secret".encode("utf-8"), message, hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode("utf-8")

    headers = {
        "X-Lark-Signature": signature,
        "X-Lark-Request-Timestamp": timestamp,
        "X-Lark-Request-Nonce": nonce,
    }
    
    response = client.post("/webhook", json=payload, headers=headers)

    assert response.status_code == 200
    # Event server adds _provider to payload before calling handler
    expected_payload = {**payload, "_provider": "feishu"}
    event_handler.assert_called_once_with(expected_payload)


def test_event_server_verification_token_invalid(config_with_auth, event_handler):
    """Test event with invalid verification token."""
    server = EventServer(config_with_auth, event_handler)
    client = TestClient(server._app)
    
    payload = {
        "type": "message",
        "token": "wrong_token",
        "event": {"text": "Hello"}
    }
    
    response = client.post("/webhook", json=payload)
    
    assert response.status_code == 403
    assert "Invalid verification token" in response.json()["detail"]
    event_handler.assert_not_called()


def test_event_server_verification_token_missing(config_with_auth, event_handler):
    """Test event with missing verification token."""
    server = EventServer(config_with_auth, event_handler)
    client = TestClient(server._app)
    
    payload = {
        "type": "message",
        "event": {"text": "Hello"}
    }
    
    response = client.post("/webhook", json=payload)
    
    assert response.status_code == 403
    event_handler.assert_not_called()


def test_event_server_signature_verification_valid(config_with_auth, event_handler):
    """Test event with valid signature."""
    server = EventServer(config_with_auth, event_handler)
    client = TestClient(server._app)
    
    payload = {
        "type": "message",
        "token": "test_token_12345",
        "event": {"text": "Hello"}
    }
    
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    timestamp = "1234567890"
    nonce = "test_nonce"
    
    # Calculate valid signature
    message = (timestamp + nonce).encode("utf-8") + body
    digest = hmac.new("test_secret".encode("utf-8"), message, hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode("utf-8")
    
    headers = {
        "X-Lark-Signature": signature,
        "X-Lark-Request-Timestamp": timestamp,
        "X-Lark-Request-Nonce": nonce,
    }
    
    response = client.post("/webhook", json=payload, headers=headers)
    
    assert response.status_code == 200
    event_handler.assert_called_once()


def test_event_server_signature_verification_invalid(config_with_auth, event_handler):
    """Test event with invalid signature."""
    server = EventServer(config_with_auth, event_handler)
    client = TestClient(server._app)
    
    payload = {
        "type": "message",
        "token": "test_token_12345",
        "event": {"text": "Hello"}
    }
    
    headers = {
        "X-Lark-Signature": "invalid_signature",
        "X-Lark-Request-Timestamp": "1234567890",
        "X-Lark-Request-Nonce": "test_nonce",
    }
    
    response = client.post("/webhook", json=payload, headers=headers)
    
    assert response.status_code == 403
    assert "Invalid signature" in response.json()["detail"]
    event_handler.assert_not_called()


def test_event_server_signature_verification_missing_headers(config_with_auth, event_handler):
    """Test event with missing signature headers."""
    server = EventServer(config_with_auth, event_handler)
    client = TestClient(server._app)
    
    payload = {
        "type": "message",
        "token": "test_token_12345",
        "event": {"text": "Hello"}
    }
    
    # Missing signature headers
    response = client.post("/webhook", json=payload)
    
    assert response.status_code == 403
    assert "Missing signature headers" in response.json()["detail"]
    event_handler.assert_not_called()


def test_event_server_handler_exception(basic_config):
    """Test that handler exceptions are caught and logged."""
    handler = MagicMock(side_effect=Exception("Handler error"))
    server = EventServer(basic_config, handler)
    client = TestClient(server._app)
    
    payload = {"type": "message", "event": {"text": "Hello"}}
    
    response = client.post("/webhook", json=payload)
    
    assert response.status_code == 500
    assert "Handler failure" in response.json()["detail"]
    handler.assert_called_once()


def test_event_server_start(basic_config, event_handler, mocker):
    """Test starting the event server."""
    server = EventServer(basic_config, event_handler)
    
    # Mock uvicorn components
    mock_server = MagicMock()
    mock_config = mocker.patch("feishu_webhook_bot.core.event_server.uvicorn.Config")
    mock_server_class = mocker.patch("feishu_webhook_bot.core.event_server.uvicorn.Server", return_value=mock_server)
    mock_thread = mocker.patch("feishu_webhook_bot.core.event_server.threading.Thread")
    
    server.start()
    
    # Verify Config was created
    mock_config.assert_called_once_with(
        server._app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )
    
    # Verify Server was created
    mock_server_class.assert_called_once()
    
    # Verify thread was started
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()


def test_event_server_start_already_running(basic_config, event_handler, mocker):
    """Test starting server when already running."""
    server = EventServer(basic_config, event_handler)
    
    # Simulate already running
    server._thread = MagicMock()
    
    mock_config = mocker.patch("feishu_webhook_bot.core.event_server.uvicorn.Config")
    
    server.start()
    
    # Should not create new config
    mock_config.assert_not_called()


def test_event_server_start_disabled(event_handler, mocker):
    """Test starting server when disabled."""
    config = EventServerConfig(enabled=False, host="127.0.0.1", port=8000, path="/webhook")
    server = EventServer(config, event_handler)
    
    mock_config = mocker.patch("feishu_webhook_bot.core.event_server.uvicorn.Config")
    
    server.start()
    
    # Should not create config
    mock_config.assert_not_called()


def test_event_server_stop(basic_config, event_handler):
    """Test stopping the event server."""
    server = EventServer(basic_config, event_handler)
    
    # Simulate running server
    mock_server = MagicMock()
    mock_thread = MagicMock()
    server._server = mock_server
    server._thread = mock_thread
    
    server.stop()
    
    # Verify server was signaled to exit
    assert mock_server.should_exit is True
    
    # Verify thread was joined
    mock_thread.join.assert_called_once_with(timeout=5)
    
    # Verify thread was cleared
    assert server._thread is None


def test_event_server_stop_not_running(basic_config, event_handler):
    """Test stopping server when not running."""
    server = EventServer(basic_config, event_handler)
    
    # Should not raise exception
    server.stop()


def test_event_server_is_running_true(basic_config, event_handler):
    """Test is_running property when server is running."""
    server = EventServer(basic_config, event_handler)
    
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    server._thread = mock_thread
    
    assert server.is_running is True


def test_event_server_is_running_false(basic_config, event_handler):
    """Test is_running property when server is not running."""
    server = EventServer(basic_config, event_handler)
    
    assert server.is_running is False


def test_event_server_is_running_thread_dead(basic_config, event_handler):
    """Test is_running property when thread exists but is dead."""
    server = EventServer(basic_config, event_handler)
    
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = False
    server._thread = mock_thread
    
    assert server.is_running is False


def test_verify_token_no_token_configured(basic_config, event_handler):
    """Test token verification when no token is configured."""
    server = EventServer(basic_config, event_handler)
    
    # Should not raise exception
    server._verify_token({"type": "message"})


def test_verify_signature_no_secret_configured(basic_config, event_handler):
    """Test signature verification when no secret is configured."""
    server = EventServer(basic_config, event_handler)

    mock_request = MagicMock()
    body = b"test body"

    # Should not raise exception
    server._verify_signature(mock_request, body)


def test_qq_event_no_access_token_configured(basic_config, event_handler):
    """Test QQ event when no access token is configured."""
    server = EventServer(basic_config, event_handler)
    client = TestClient(server._app)

    payload = {
        "message_type": "group",
        "group_id": 123456,
        "message": "Hello"
    }

    # Should accept event without Authorization header
    response = client.post("/qq/events", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    # Event server adds _provider to payload
    expected_payload = {**payload, "_provider": "napcat"}
    event_handler.assert_called_once_with(expected_payload)


def test_qq_event_with_valid_access_token(basic_config, event_handler):
    """Test QQ event with valid access token."""
    # Create napcat provider
    napcat_provider = ProviderConfigBase(
        provider_type="napcat",
        name="qq",
        http_url="http://localhost:3000",
        access_token="test_token_123"
    )

    server = EventServer(basic_config, event_handler, providers_config=[napcat_provider])
    client = TestClient(server._app)

    payload = {
        "message_type": "group",
        "group_id": 123456,
        "message": "Hello"
    }

    headers = {"Authorization": "test_token_123"}
    response = client.post("/qq/events", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    expected_payload = {**payload, "_provider": "napcat"}
    event_handler.assert_called_once_with(expected_payload)


def test_qq_event_with_bearer_token(basic_config, event_handler):
    """Test QQ event with Bearer token format."""
    napcat_provider = ProviderConfigBase(
        provider_type="napcat",
        name="qq",
        http_url="http://localhost:3000",
        access_token="test_token_456"
    )

    server = EventServer(basic_config, event_handler, providers_config=[napcat_provider])
    client = TestClient(server._app)

    payload = {
        "message_type": "private",
        "user_id": 987654,
        "message": "Hi"
    }

    # Test Bearer token format
    headers = {"Authorization": "Bearer test_token_456"}
    response = client.post("/qq/events", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    expected_payload = {**payload, "_provider": "napcat"}
    event_handler.assert_called_once_with(expected_payload)


def test_qq_event_missing_authorization_header(basic_config, event_handler):
    """Test QQ event missing Authorization header when token is configured."""
    napcat_provider = ProviderConfigBase(
        provider_type="napcat",
        name="qq",
        http_url="http://localhost:3000",
        access_token="test_token_789"
    )

    server = EventServer(basic_config, event_handler, providers_config=[napcat_provider])
    client = TestClient(server._app)

    payload = {
        "message_type": "group",
        "group_id": 123456,
        "message": "Hello"
    }

    # No Authorization header
    response = client.post("/qq/events", json=payload)

    assert response.status_code == 401
    assert "Missing Authorization header" in response.json()["detail"]
    event_handler.assert_not_called()


def test_qq_event_invalid_access_token(basic_config, event_handler):
    """Test QQ event with invalid access token."""
    napcat_provider = ProviderConfigBase(
        provider_type="napcat",
        name="qq",
        http_url="http://localhost:3000",
        access_token="correct_token"
    )

    server = EventServer(basic_config, event_handler, providers_config=[napcat_provider])
    client = TestClient(server._app)

    payload = {
        "message_type": "group",
        "group_id": 123456,
        "message": "Hello"
    }

    headers = {"Authorization": "wrong_token"}
    response = client.post("/qq/events", json=payload, headers=headers)

    assert response.status_code == 403
    assert "Invalid access token" in response.json()["detail"]
    event_handler.assert_not_called()


def test_qq_event_invalid_json(basic_config, event_handler):
    """Test QQ event with invalid JSON."""
    server = EventServer(basic_config, event_handler)
    client = TestClient(server._app)

    response = client.post(
        "/qq/events",
        content="invalid json",
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]
    event_handler.assert_not_called()
