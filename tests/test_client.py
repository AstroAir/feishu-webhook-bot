"Tests for the core client module."

import base64
import hashlib
import hmac
import json
import time

import pytest
from pytest_httpx import HTTPXMock

from feishu_webhook_bot.core import FeishuWebhookClient, WebhookConfig
from feishu_webhook_bot.core.client import CardBuilder


@pytest.fixture
def webhook_config():
    """Provides a basic WebhookConfig."""
    return WebhookConfig(url="https://example.com/webhook", name="test")


@pytest.fixture
def secure_webhook_config():
    """Provides a WebhookConfig with a secret."""
    return WebhookConfig(
        url="https://example.com/webhook", name="test-secure", secret="test-secret"
    )


def test_webhook_config_validation():
    """Test webhook config validation for URL format."""
    with pytest.raises(ValueError, match="Webhook URL cannot be empty"):
        WebhookConfig(url="", name="test")
    with pytest.raises(ValueError, match="Webhook URL must start with"):
        WebhookConfig(url="not-a-url", name="test")


def test_client_initialization_and_context_manager(webhook_config):
    """Test client initialization and use as a context manager."""
    with FeishuWebhookClient(webhook_config) as client:
        assert client.config == webhook_config
        assert client.timeout == 10.0
    # After exiting context, the internal client should be closed
    assert client._client.is_closed


def test_generate_sign(secure_webhook_config):
    """Test the HMAC-SHA256 signature generation."""
    client = FeishuWebhookClient(secure_webhook_config)
    timestamp = int(time.time())

    # Calculate expected signature manually
    string_to_sign = f"{timestamp}\n{secure_webhook_config.secret}"
    hmac_code = hmac.new(
        secure_webhook_config.secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    expected_sign = base64.b64encode(hmac_code).decode("utf-8")

    generated_sign = client._generate_sign(timestamp)
    assert generated_sign == expected_sign


def test_send_text(webhook_config, httpx_mock: HTTPXMock):
    """Test sending a simple text message."""
    httpx_mock.add_response(json={"code": 0, "msg": "success"})
    client = FeishuWebhookClient(webhook_config)
    client.send_text("Hello World")

    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url == webhook_config.url
    payload = json.loads(request.content)
    assert payload == {"msg_type": "text", "content": {"text": "Hello World"}}


def test_send_with_signature(secure_webhook_config, httpx_mock: HTTPXMock):
    """Test that messages sent with a secret include timestamp and sign."""
    httpx_mock.add_response(json={"code": 0, "msg": "success"})
    client = FeishuWebhookClient(secure_webhook_config)
    client.send_text("secure message")

    request = httpx_mock.get_requests()[0]
    payload = json.loads(request.content)
    assert "timestamp" in payload
    assert "sign" in payload


def test_send_card(webhook_config, httpx_mock: HTTPXMock):
    """Test sending an interactive card message."""
    httpx_mock.add_response(json={"code": 0, "msg": "success"})
    card_dict = {"header": {"title": {"content": "Test Card"}}}
    client = FeishuWebhookClient(webhook_config)
    client.send_card(card_dict)

    request = httpx_mock.get_requests()[0]
    payload = json.loads(request.content)
    assert payload["msg_type"] == "interactive"
    assert payload["card"] == card_dict


def test_send_image(webhook_config, httpx_mock: HTTPXMock):
    """Test sending an image message."""
    httpx_mock.add_response(json={"code": 0, "msg": "success"})
    client = FeishuWebhookClient(webhook_config)
    client.send_image("img_key_123")

    request = httpx_mock.get_requests()[0]
    payload = json.loads(request.content)
    assert payload == {"msg_type": "image", "content": {"image_key": "img_key_123"}}


def test_api_error_handling(webhook_config, httpx_mock: HTTPXMock):
    """Test that Feishu API errors (non-zero code) are handled."""
    error_response = {"code": 9499, "msg": "some api error"}
    httpx_mock.add_response(json=error_response)
    client = FeishuWebhookClient(webhook_config)

    with pytest.raises(ValueError, match="Feishu API error: some api error"):
        client.send_text("test")


def test_http_error_handling(webhook_config, httpx_mock: HTTPXMock):
    """Test that HTTP errors (e.g., 500) are handled."""
    httpx_mock.add_response(status_code=500)
    client = FeishuWebhookClient(webhook_config)

    with pytest.raises(pytest.httpx.HTTPStatusError):
        client.send_text("test")


class TestCardBuilder:
    """Tests for the CardBuilder helper class."""

    def test_card_builder_structure(self):
        """Test the basic structure and chaining of the CardBuilder."""
        card = (
            CardBuilder()
            .set_config(wide_screen_mode=True)
            .set_header("Test Title", template="blue", subtitle="Subtitle")
            .add_markdown("**Bold** text")
            .add_text("Plain text")
            .add_divider()
            .add_note("Footer note")
            .build()
        )

        assert card["schema"] == "2.0"
        assert card["config"]["wide_screen_mode"] is True
        assert card["header"]["title"]["content"] == "Test Title"
        assert card["header"]["template"] == "blue"
        assert card["header"]["subtitle"]["content"] == "Subtitle"
        assert len(card["elements"]) == 4  # markdown, text, divider, note

    def test_card_builder_single_button(self):
        """Test that a single button is added correctly."""
        card = CardBuilder().add_button("Click Me", url="https://a.com").build()
        assert len(card["elements"]) == 1
        action_block = card["elements"][0]
        assert action_block["tag"] == "action"
        assert len(action_block["actions"]) == 1
        assert action_block["actions"][0]["text"]["content"] == "Click Me"

    def test_card_builder_multiple_buttons(self):
        """Test that multiple consecutive buttons are added to the same action block."""
        card = (
            CardBuilder()
            .add_button("Button 1", url="https://a.com")
            .add_button("Button 2", url="https://b.com")
            .build()
        )

        assert len(card["elements"]) == 1, "Should create only one action block"
        action_block = card["elements"][0]
        assert action_block["tag"] == "action"
        assert len(action_block["actions"]) == 2, "Should contain two buttons"
        assert action_block["actions"][0]["text"]["content"] == "Button 1"
        assert action_block["actions"][1]["text"]["content"] == "Button 2"

    def test_card_builder_buttons_separated_by_other_element(self):
        """Test that buttons separated by another element create separate action blocks."""
        card = CardBuilder().add_button("Button 1").add_divider().add_button("Button 2").build()

        assert len(card["elements"]) == 3, "Should have three elements: action, hr, action"
        assert card["elements"][0]["tag"] == "action"
        assert len(card["elements"][0]["actions"]) == 1
        assert card["elements"][1]["tag"] == "hr"
        assert card["elements"][2]["tag"] == "action"
        assert len(card["elements"][2]["actions"]) == 1
