"""Comprehensive tests for template registry and rendering.

Tests cover:
- RenderedTemplate dataclass
- TemplateRegistry initialization
- Template listing and retrieval
- Template rendering with different engines
- Error handling
"""

from __future__ import annotations

import json

import pytest

from feishu_webhook_bot.core.config import TemplateConfig
from feishu_webhook_bot.core.templates import (
    RenderedTemplate,
    TemplateRegistry,
    TemplateRenderError,
)

# ==============================================================================
# RenderedTemplate Tests
# ==============================================================================


class TestRenderedTemplate:
    """Tests for RenderedTemplate dataclass."""

    def test_rendered_template_creation(self):
        """Test RenderedTemplate creation."""
        template = RenderedTemplate(type="text", content="Hello World")
        assert template.type == "text"
        assert template.content == "Hello World"

    def test_rendered_template_with_dict_content(self):
        """Test RenderedTemplate with dict content."""
        content = {"header": {"title": "Test"}, "elements": []}
        template = RenderedTemplate(type="card", content=content)
        assert template.type == "card"
        assert template.content == content

    def test_rendered_template_slots(self):
        """Test RenderedTemplate uses slots for memory efficiency."""
        template = RenderedTemplate(type="text", content="test")
        # slots classes don't have __dict__
        assert not hasattr(template, "__dict__")


# ==============================================================================
# TemplateRegistry Initialization Tests
# ==============================================================================


class TestTemplateRegistryInitialization:
    """Tests for TemplateRegistry initialization."""

    def test_registry_empty(self):
        """Test registry with no templates."""
        registry = TemplateRegistry([])
        assert registry.list() == []

    def test_registry_with_templates(self):
        """Test registry with templates."""
        templates = [
            TemplateConfig(name="greeting", type="text", content="Hello $name"),
            TemplateConfig(name="alert", type="text", content="Alert: $message"),
        ]
        registry = TemplateRegistry(templates)

        assert len(registry.list()) == 2
        assert "greeting" in registry.list()
        assert "alert" in registry.list()

    def test_registry_list_sorted(self):
        """Test registry list is sorted alphabetically."""
        templates = [
            TemplateConfig(name="zebra", type="text", content="z"),
            TemplateConfig(name="alpha", type="text", content="a"),
            TemplateConfig(name="beta", type="text", content="b"),
        ]
        registry = TemplateRegistry(templates)

        assert registry.list() == ["alpha", "beta", "zebra"]


# ==============================================================================
# Template Retrieval Tests
# ==============================================================================


class TestTemplateRetrieval:
    """Tests for template retrieval."""

    @pytest.fixture
    def registry(self):
        """Create registry with test templates."""
        templates = [
            TemplateConfig(name="simple", type="text", content="Hello $name"),
            TemplateConfig(name="card", type="card", content='{"title": "$title"}'),
        ]
        return TemplateRegistry(templates)

    def test_get_existing_template(self, registry):
        """Test getting existing template."""
        template = registry.get("simple")
        assert template.name == "simple"
        assert template.type == "text"

    def test_get_nonexistent_template(self, registry):
        """Test getting nonexistent template raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")


# ==============================================================================
# Template Rendering Tests
# ==============================================================================


class TestTemplateRendering:
    """Tests for template rendering."""

    def test_render_text_template_string(self):
        """Test rendering text template with string engine (safe_substitute)."""
        templates = [
            TemplateConfig(
                name="greeting",
                type="text",
                content="Hello $name, welcome to $place!",
                engine="string",
            ),
        ]
        registry = TemplateRegistry(templates)

        result = registry.render("greeting", {"name": "Alice", "place": "Wonderland"})

        assert result.type == "text"
        assert result.content == "Hello Alice, welcome to Wonderland!"

    def test_render_text_template_format(self):
        """Test rendering text template with format engine."""
        templates = [
            TemplateConfig(
                name="greeting",
                type="text",
                content="Hello {name}, welcome to {place}!",
                engine="format",
            ),
        ]
        registry = TemplateRegistry(templates)

        result = registry.render("greeting", {"name": "Bob", "place": "Earth"})

        assert result.type == "text"
        assert result.content == "Hello Bob, welcome to Earth!"

    def test_render_card_template(self):
        """Test rendering card template returns dict."""
        templates = [
            TemplateConfig(
                name="alert_card",
                type="card",
                content='{"header": {"title": "$title"}, "elements": []}',
                engine="string",
            ),
        ]
        registry = TemplateRegistry(templates)

        result = registry.render("alert_card", {"title": "Warning"})

        assert result.type == "card"
        assert isinstance(result.content, dict)
        assert result.content["header"]["title"] == "Warning"

    def test_render_json_template(self):
        """Test rendering json template returns dict."""
        templates = [
            TemplateConfig(
                name="data",
                type="json",
                content='{"key": "$value", "count": 42}',
                engine="string",
            ),
        ]
        registry = TemplateRegistry(templates)

        result = registry.render("data", {"value": "test"})

        assert result.type == "json"
        assert isinstance(result.content, dict)
        assert result.content["key"] == "test"
        assert result.content["count"] == 42

    def test_render_post_template(self):
        """Test rendering post (rich text) template."""
        templates = [
            TemplateConfig(
                name="rich",
                type="post",
                content='{"zh_cn": {"title": "$title", "content": []}}',
                engine="string",
            ),
        ]
        registry = TemplateRegistry(templates)

        result = registry.render("rich", {"title": "Post Title"})

        assert result.type == "post"
        assert isinstance(result.content, dict)
        assert result.content["zh_cn"]["title"] == "Post Title"

    def test_render_with_empty_context(self):
        """Test rendering with empty context."""
        templates = [
            TemplateConfig(
                name="static",
                type="text",
                content="No variables here",
                engine="string",
            ),
        ]
        registry = TemplateRegistry(templates)

        result = registry.render("static", {})

        assert result.content == "No variables here"

    def test_render_with_none_context(self):
        """Test rendering with None context."""
        templates = [
            TemplateConfig(
                name="static",
                type="text",
                content="Static content",
                engine="string",
            ),
        ]
        registry = TemplateRegistry(templates)

        result = registry.render("static", None)

        assert result.content == "Static content"

    def test_render_substitute_missing_variable(self):
        """Test substitute engine handles missing variables gracefully."""
        templates = [
            TemplateConfig(
                name="partial",
                type="text",
                content="Hello $name, your id is $id",
                engine="string",
            ),
        ]
        registry = TemplateRegistry(templates)

        # safe_substitute keeps missing variables as-is
        result = registry.render("partial", {"name": "Alice"})

        assert "Alice" in result.content
        assert "$id" in result.content  # Missing variable preserved


class TestTemplateRenderingErrors:
    """Tests for template rendering error handling."""

    def test_render_nonexistent_template(self):
        """Test rendering nonexistent template raises error."""
        registry = TemplateRegistry([])

        with pytest.raises(KeyError):
            registry.render("nonexistent", {})

    def test_render_invalid_json_card(self):
        """Test rendering card with invalid JSON raises error."""
        templates = [
            TemplateConfig(
                name="bad_card",
                type="card",
                content="not valid json $var",
                engine="string",
            ),
        ]
        registry = TemplateRegistry(templates)

        with pytest.raises(TemplateRenderError):
            registry.render("bad_card", {"var": "value"})

    def test_render_format_missing_key(self):
        """Test format engine with missing key raises error."""
        templates = [
            TemplateConfig(
                name="strict",
                type="text",
                content="Hello {name}, id: {id}",
                engine="format",
            ),
        ]
        registry = TemplateRegistry(templates)

        with pytest.raises(TemplateRenderError):
            registry.render("strict", {"name": "Alice"})  # Missing 'id'


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestTemplateIntegration:
    """Integration tests for template system."""

    def test_multiple_templates_same_registry(self):
        """Test registry handles multiple templates correctly."""
        templates = [
            TemplateConfig(name="text1", type="text", content="Text: $msg"),
            TemplateConfig(name="text2", type="text", content="Other: $msg"),
            TemplateConfig(name="card1", type="card", content='{"msg": "$msg"}'),
        ]
        registry = TemplateRegistry(templates)

        result1 = registry.render("text1", {"msg": "hello"})
        result2 = registry.render("text2", {"msg": "world"})
        result3 = registry.render("card1", {"msg": "card"})

        assert result1.content == "Text: hello"
        assert result2.content == "Other: world"
        assert result3.content == {"msg": "card"}

    def test_complex_card_template(self):
        """Test rendering complex card template."""
        card_content = json.dumps(
            {
                "header": {
                    "title": {"tag": "plain_text", "content": "$title"},
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "plain_text", "content": "$body"},
                    },
                ],
            }
        )

        templates = [
            TemplateConfig(
                name="complex_card",
                type="card",
                content=card_content,
                engine="string",
            ),
        ]
        registry = TemplateRegistry(templates)

        result = registry.render("complex_card", {"title": "Alert", "body": "Message"})

        assert result.type == "card"
        assert result.content["header"]["title"]["content"] == "Alert"
        assert result.content["elements"][0]["text"]["content"] == "Message"
