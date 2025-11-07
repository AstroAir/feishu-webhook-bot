"""Template registry and rendering helpers for Feishu Webhook Bot."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from string import Template
from typing import Any

from .config import TemplateConfig
from .logger import get_logger

logger = get_logger("templates")


@dataclass(slots=True)
class RenderedTemplate:
    """Represents a rendered template ready to be dispatched."""

    type: str
    content: Any


class TemplateRenderError(RuntimeError):
    """Raised when a template cannot be rendered."""


class TemplateRegistry:
    """Registry that manages configured templates and renders them on demand."""

    def __init__(self, templates: list[TemplateConfig]):
        self._templates: dict[str, TemplateConfig] = {t.name: t for t in templates}

    def list(self) -> list[str]:
        """Return the names of all registered templates."""

        return sorted(self._templates)

    def get(self, name: str) -> TemplateConfig:
        """Retrieve a raw template configuration."""

        try:
            return self._templates[name]
        except KeyError as exc:  # pragma: no cover - guard clause
            raise KeyError(f"Template not found: {name}") from exc

    def render(self, name: str, context: Mapping[str, Any] | None = None) -> RenderedTemplate:
        """Render a template with the provided context."""

        template = self.get(name)
        ctx = dict(context or {})

        try:
            rendered = self._render_content(template, ctx)
        except Exception as exc:  # pragma: no cover - logged for diagnostics
            logger.error("Failed to render template '%s': %s", name, exc, exc_info=True)
            raise TemplateRenderError(str(exc)) from exc

        return RenderedTemplate(type=template.type, content=rendered)

    def _render_content(self, template: TemplateConfig, context: Mapping[str, Any]) -> Any:
        """Render content for a template using the configured engine."""

        if template.engine == "format":
            rendered = template.content.format(**context)
        else:
            rendered = Template(template.content).safe_substitute(**context)

        if template.type in {"card", "interactive", "json"}:
            return json.loads(rendered)
        if template.type == "post":
            # For post/rich text messages we expect valid JSON structure as well.
            return json.loads(rendered)

        return rendered
