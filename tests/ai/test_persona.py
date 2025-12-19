"""Comprehensive tests for persona management module.

Tests cover:
- PersonaConfig model validation
- PersonaManager initialization
- Persona retrieval and listing
- System prompt building with different modes
- Default persona handling
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.ai.persona import PersonaConfig, PersonaManager

# ==============================================================================
# PersonaConfig Tests
# ==============================================================================


class TestPersonaConfig:
    """Tests for PersonaConfig model."""

    def test_default_values(self):
        """Test PersonaConfig with default values."""
        config = PersonaConfig()

        assert config.display_name is None
        assert config.description is None
        assert config.prompt == ""
        assert config.prompt_mode == "append"
        assert config.model is None
        assert config.temperature is None
        assert config.max_tokens is None

    def test_custom_values(self):
        """Test PersonaConfig with custom values."""
        config = PersonaConfig(
            display_name="Tech Expert",
            description="A technical expert persona",
            prompt="You are an expert in technology.",
            prompt_mode="replace",
            model="openai:gpt-4o",
            temperature=0.5,
            max_tokens=2048,
        )

        assert config.display_name == "Tech Expert"
        assert config.description == "A technical expert persona"
        assert config.prompt == "You are an expert in technology."
        assert config.prompt_mode == "replace"
        assert config.model == "openai:gpt-4o"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048

    def test_prompt_mode_append(self):
        """Test prompt_mode can be 'append'."""
        config = PersonaConfig(prompt_mode="append")
        assert config.prompt_mode == "append"

    def test_prompt_mode_replace(self):
        """Test prompt_mode can be 'replace'."""
        config = PersonaConfig(prompt_mode="replace")
        assert config.prompt_mode == "replace"

    def test_temperature_validation(self):
        """Test temperature must be 0.0-2.0."""
        # Valid temperatures
        config_low = PersonaConfig(temperature=0.0)
        config_high = PersonaConfig(temperature=2.0)

        assert config_low.temperature == 0.0
        assert config_high.temperature == 2.0

        # Invalid temperatures
        with pytest.raises(ValueError):
            PersonaConfig(temperature=-0.1)

        with pytest.raises(ValueError):
            PersonaConfig(temperature=2.1)

    def test_max_tokens_validation(self):
        """Test max_tokens must be >= 1."""
        config = PersonaConfig(max_tokens=1)
        assert config.max_tokens == 1

        with pytest.raises(ValueError):
            PersonaConfig(max_tokens=0)

    def test_serialization(self):
        """Test PersonaConfig can be serialized."""
        config = PersonaConfig(
            display_name="Test",
            prompt="Test prompt",
        )

        data = config.model_dump()

        assert data["display_name"] == "Test"
        assert data["prompt"] == "Test prompt"
        assert data["prompt_mode"] == "append"


# ==============================================================================
# PersonaManager Initialization Tests
# ==============================================================================


class TestPersonaManagerInitialization:
    """Tests for PersonaManager initialization."""

    def test_empty_initialization(self):
        """Test PersonaManager with no personas."""
        manager = PersonaManager()

        assert manager.personas == {}
        assert manager.default_persona is None

    def test_initialization_with_personas(self):
        """Test PersonaManager with personas."""
        personas = {
            "default": PersonaConfig(prompt="Default prompt"),
            "expert": PersonaConfig(prompt="Expert prompt"),
        }

        manager = PersonaManager(personas=personas)

        assert len(manager.personas) == 2
        assert "default" in manager.personas
        assert "expert" in manager.personas

    def test_initialization_with_default_persona(self):
        """Test PersonaManager with explicit default persona."""
        personas = {
            "main": PersonaConfig(prompt="Main prompt"),
            "alt": PersonaConfig(prompt="Alt prompt"),
        }

        manager = PersonaManager(personas=personas, default_persona="main")

        assert manager.default_persona == "main"

    def test_default_persona_fallback_to_default_key(self):
        """Test default_persona falls back to 'default' key if exists."""
        personas = {
            "default": PersonaConfig(prompt="Default prompt"),
            "other": PersonaConfig(prompt="Other prompt"),
        }

        manager = PersonaManager(personas=personas)

        assert manager.default_persona == "default"

    def test_default_persona_fallback_to_first(self):
        """Test default_persona falls back to first persona if no 'default'."""
        personas = {
            "alpha": PersonaConfig(prompt="Alpha prompt"),
            "beta": PersonaConfig(prompt="Beta prompt"),
        }

        manager = PersonaManager(personas=personas)

        # Should return one of the personas (first in iteration)
        assert manager.default_persona in personas


# ==============================================================================
# PersonaManager Retrieval Tests
# ==============================================================================


class TestPersonaManagerRetrieval:
    """Tests for persona retrieval methods."""

    @pytest.fixture
    def manager(self):
        """Create a manager with test personas."""
        personas = {
            "default": PersonaConfig(
                display_name="Default",
                prompt="You are helpful.",
            ),
            "coder": PersonaConfig(
                display_name="Coder",
                prompt="You are an expert coder.",
            ),
            "writer": PersonaConfig(
                display_name="Writer",
                prompt="You are a creative writer.",
            ),
        }
        return PersonaManager(personas=personas, default_persona="default")

    def test_get_persona_by_id(self, manager):
        """Test getting persona by ID."""
        persona = manager.get_persona("coder")

        assert persona is not None
        assert persona.display_name == "Coder"
        assert persona.prompt == "You are an expert coder."

    def test_get_persona_nonexistent(self, manager):
        """Test getting nonexistent persona returns default."""
        persona = manager.get_persona("nonexistent")

        # Should fall back to default persona
        assert persona is not None
        assert persona.display_name == "Default"

    def test_get_persona_none_returns_default(self, manager):
        """Test getting persona with None returns default."""
        persona = manager.get_persona(None)

        assert persona is not None
        assert persona.display_name == "Default"

    def test_get_persona_no_default(self):
        """Test getting persona when no default exists."""
        manager = PersonaManager()

        persona = manager.get_persona(None)

        assert persona is None

    def test_list_personas(self, manager):
        """Test listing all persona IDs."""
        persona_ids = manager.list_personas()

        assert len(persona_ids) == 3
        assert "default" in persona_ids
        assert "coder" in persona_ids
        assert "writer" in persona_ids

    def test_list_personas_sorted(self, manager):
        """Test persona IDs are sorted."""
        persona_ids = manager.list_personas()

        assert persona_ids == sorted(persona_ids)

    def test_list_personas_empty(self):
        """Test listing personas when empty."""
        manager = PersonaManager()

        persona_ids = manager.list_personas()

        assert persona_ids == []


# ==============================================================================
# PersonaManager System Prompt Tests
# ==============================================================================


class TestPersonaManagerSystemPrompt:
    """Tests for system prompt building."""

    def test_build_system_prompt_append_mode(self):
        """Test building system prompt in append mode."""
        personas = {
            "test": PersonaConfig(
                prompt="Additional instructions.",
                prompt_mode="append",
            ),
        }
        manager = PersonaManager(personas=personas)
        base_prompt = "You are a helpful assistant."

        result = manager.build_system_prompt(base_prompt, "test")

        assert "You are a helpful assistant." in result
        assert "Additional instructions." in result
        # In append mode, both should be present
        assert base_prompt in result

    def test_build_system_prompt_replace_mode(self):
        """Test building system prompt in replace mode."""
        personas = {
            "test": PersonaConfig(
                prompt="Completely new prompt.",
                prompt_mode="replace",
            ),
        }
        manager = PersonaManager(personas=personas)
        base_prompt = "You are a helpful assistant."

        result = manager.build_system_prompt(base_prompt, "test")

        assert result == "Completely new prompt."
        assert base_prompt not in result

    def test_build_system_prompt_empty_persona_prompt(self):
        """Test building prompt when persona has empty prompt."""
        personas = {
            "test": PersonaConfig(
                prompt="",
                prompt_mode="append",
            ),
        }
        manager = PersonaManager(personas=personas)
        base_prompt = "Base prompt."

        result = manager.build_system_prompt(base_prompt, "test")

        assert result == "Base prompt."

    def test_build_system_prompt_no_persona(self):
        """Test building prompt when no persona exists."""
        manager = PersonaManager()
        base_prompt = "Base prompt."

        result = manager.build_system_prompt(base_prompt, None)

        assert result == "Base prompt."

    def test_build_system_prompt_replace_with_empty(self):
        """Test replace mode with empty prompt uses base prompt."""
        personas = {
            "test": PersonaConfig(
                prompt="",
                prompt_mode="replace",
            ),
        }
        manager = PersonaManager(personas=personas)
        base_prompt = "Base prompt."

        result = manager.build_system_prompt(base_prompt, "test")

        assert result == "Base prompt."

    def test_build_system_prompt_nonexistent_persona(self):
        """Test building prompt for nonexistent persona uses default."""
        personas = {
            "default": PersonaConfig(
                prompt="Default addition.",
                prompt_mode="append",
            ),
        }
        manager = PersonaManager(personas=personas, default_persona="default")
        base_prompt = "Base."

        result = manager.build_system_prompt(base_prompt, "nonexistent")

        assert "Base." in result
        assert "Default addition." in result


# ==============================================================================
# PersonaManager Properties Tests
# ==============================================================================


class TestPersonaManagerProperties:
    """Tests for PersonaManager properties."""

    def test_personas_property_returns_copy(self):
        """Test personas property returns a copy."""
        personas = {
            "test": PersonaConfig(prompt="Test"),
        }
        manager = PersonaManager(personas=personas)

        # Get personas and modify
        returned_personas = manager.personas
        returned_personas["new"] = PersonaConfig(prompt="New")

        # Original should be unchanged
        assert "new" not in manager.personas
        assert len(manager.personas) == 1

    def test_default_persona_with_invalid_reference(self):
        """Test default_persona when reference is invalid."""
        personas = {
            "only": PersonaConfig(prompt="Only"),
        }

        manager = PersonaManager(personas=personas, default_persona="nonexistent")

        # Should fall back since nonexistent doesn't exist
        # But "default" key also doesn't exist, so should return first
        assert manager.default_persona == "only"


# ==============================================================================
# Edge Cases Tests
# ==============================================================================


class TestPersonaEdgeCases:
    """Tests for edge cases."""

    def test_persona_with_unicode_prompt(self):
        """Test persona with unicode characters in prompt."""
        config = PersonaConfig(
            display_name="中文助手",
            prompt="你是一个有帮助的助手。",
        )

        assert config.display_name == "中文助手"
        assert config.prompt == "你是一个有帮助的助手。"

    def test_persona_with_multiline_prompt(self):
        """Test persona with multiline prompt."""
        prompt = """You are an expert assistant.

You specialize in:
- Python programming
- Machine learning
- Data analysis"""

        config = PersonaConfig(prompt=prompt)

        assert "Python programming" in config.prompt
        assert "Machine learning" in config.prompt

    def test_persona_with_special_characters(self):
        """Test persona with special characters."""
        config = PersonaConfig(
            display_name='Test <> & "Special"',
            prompt="Use @mentions and #hashtags",
        )

        assert "<>" in config.display_name
        assert "@mentions" in config.prompt

    def test_manager_with_single_persona(self):
        """Test manager with single persona."""
        manager = PersonaManager(
            personas={"solo": PersonaConfig(prompt="Solo prompt")},
        )

        assert manager.default_persona == "solo"
        assert len(manager.list_personas()) == 1

    def test_build_prompt_with_complex_base(self):
        """Test building prompt with complex base prompt."""
        personas = {
            "test": PersonaConfig(
                prompt="Additional rules.",
                prompt_mode="append",
            ),
        }
        manager = PersonaManager(personas=personas, default_persona="test")

        base = """You are an AI assistant.

Rules:
1. Be helpful
2. Be accurate
3. Be safe"""

        result = manager.build_system_prompt(base, "test")

        assert "You are an AI assistant." in result
        assert "Additional rules." in result
        assert "Be helpful" in result
