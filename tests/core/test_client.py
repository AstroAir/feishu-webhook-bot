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

        # v1.0 format (default) doesn't have schema field
        assert "schema" not in card
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

    def test_card_builder_v2_format(self):
        """Test Card JSON v2.0 format."""
        card = (
            CardBuilder(version="2.0")
            .set_header("V2 Title", template="green")
            .add_markdown("**Bold** text")
            .build()
        )

        assert card["schema"] == "2.0"
        assert "body" in card
        assert card["body"]["direction"] == "vertical"
        assert len(card["body"]["elements"]) == 1
        assert card["body"]["elements"][0]["tag"] == "markdown"

    def test_card_builder_column_set(self):
        """Test column_set component."""
        card = (
            CardBuilder()
            .add_column_set(
                columns=[
                    {"tag": "column", "width": "weighted", "weight": 1,
                     "elements": [{"tag": "markdown", "content": "Left"}]},
                    {"tag": "column", "width": "weighted", "weight": 1,
                     "elements": [{"tag": "markdown", "content": "Right"}]},
                ],
                flex_mode="bisect",
            )
            .build()
        )

        assert len(card["elements"]) == 1
        col_set = card["elements"][0]
        assert col_set["tag"] == "column_set"
        assert col_set["flex_mode"] == "bisect"
        assert len(col_set["columns"]) == 2

    def test_card_builder_table(self):
        """Test table component."""
        card = (
            CardBuilder()
            .add_table(
                columns=[
                    {"name": "name", "display_name": "Name", "data_type": "text"},
                    {"name": "value", "display_name": "Value", "data_type": "number"},
                ],
                rows=[
                    ["Alice", 100],
                    ["Bob", 200],
                ],
            )
            .build()
        )

        assert len(card["elements"]) == 1
        table = card["elements"][0]
        assert table["tag"] == "table"
        assert len(table["columns"]) == 2
        assert len(table["rows"]) == 2
        assert table["rows"][0]["name"] == "Alice"
        assert table["rows"][1]["value"] == 200

    def test_card_builder_input_and_select(self):
        """Test input and select components."""
        card = (
            CardBuilder()
            .add_input(name="username", placeholder="Enter name", label="Name")
            .add_select(
                name="status",
                options=[{"text": "Active", "value": "1"}, {"text": "Inactive", "value": "0"}],
            )
            .build()
        )

        assert len(card["elements"]) == 2
        assert card["elements"][0]["tag"] == "input"
        assert card["elements"][0]["name"] == "username"
        assert card["elements"][1]["tag"] == "select_static"

    def test_card_builder_collapsible_panel(self):
        """Test collapsible panel component."""
        card = (
            CardBuilder()
            .add_collapsible_panel(
                title="Details",
                elements=[{"tag": "markdown", "content": "Hidden content"}],
                expanded=True,
            )
            .build()
        )

        assert len(card["elements"]) == 1
        panel = card["elements"][0]
        assert panel["tag"] == "collapsible_panel"
        assert panel["expanded"] is True
        assert panel["header"]["title"]["content"] == "Details"
