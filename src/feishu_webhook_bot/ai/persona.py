from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PersonaConfig(BaseModel):
    display_name: str | None = None
    description: str | None = None
    prompt: str = ""
    prompt_mode: Literal["append", "replace"] = "append"
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)


class PersonaManager:
    def __init__(
        self,
        personas: dict[str, PersonaConfig] | None = None,
        default_persona: str | None = None,
    ) -> None:
        self._personas = personas or {}
        self._default_persona = default_persona

    @property
    def personas(self) -> dict[str, PersonaConfig]:
        return self._personas.copy()

    @property
    def default_persona(self) -> str | None:
        if self._default_persona and self._default_persona in self._personas:
            return self._default_persona
        if "default" in self._personas:
            return "default"
        return next(iter(self._personas), None)

    def get_persona(self, persona_id: str | None) -> PersonaConfig | None:
        if persona_id and persona_id in self._personas:
            return self._personas[persona_id]

        default_id = self.default_persona
        if default_id is None:
            return None

        return self._personas.get(default_id)

    def list_personas(self) -> list[str]:
        return sorted(self._personas.keys())

    def build_system_prompt(self, base_prompt: str, persona_id: str | None) -> str:
        persona = self.get_persona(persona_id)
        if persona is None:
            return base_prompt

        if persona.prompt_mode == "replace":
            return persona.prompt or base_prompt

        if not persona.prompt:
            return base_prompt

        return f"{base_prompt}\n\n{persona.prompt}"
