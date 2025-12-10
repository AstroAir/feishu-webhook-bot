"""Comprehensive tests for AI configuration module.

Tests cover:
- ModelProviderConfig validation
- MCPConfig validation
- MultiAgentConfig validation
- StreamingConfig validation
- AIConfig validation and defaults
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.ai.config import (
    AIConfig,
    MCPConfig,
    ModelProviderConfig,
    MultiAgentConfig,
    StreamingConfig,
)


# ==============================================================================
# ModelProviderConfig Tests
# ==============================================================================


class TestModelProviderConfig:
    """Tests for ModelProviderConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ModelProviderConfig()

        assert config.provider is None
        assert config.base_url is None
        assert config.api_version is None
        assert config.organization_id is None
        assert config.timeout == 60.0
        assert config.max_retries == 2
        assert config.additional_headers == {}
        assert config.additional_params == {}

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ModelProviderConfig(
            provider="openai",
            base_url="https://api.example.com",
            api_version="v1",
            organization_id="org-123",
            timeout=120.0,
            max_retries=5,
            additional_headers={"X-Custom": "value"},
            additional_params={"top_p": 0.9},
        )

        assert config.provider == "openai"
        assert config.base_url == "https://api.example.com"
        assert config.timeout == 120.0
        assert config.max_retries == 5

    def test_provider_validation(self):
        """Test provider must be valid literal."""
        # Valid providers
        for provider in ["openai", "anthropic", "google", "groq", "cohere", "ollama"]:
            config = ModelProviderConfig(provider=provider)
            assert config.provider == provider

    def test_timeout_validation(self):
        """Test timeout must be >= 1.0."""
        with pytest.raises(ValueError):
            ModelProviderConfig(timeout=0.5)

    def test_max_retries_validation(self):
        """Test max_retries must be 0-10."""
        with pytest.raises(ValueError):
            ModelProviderConfig(max_retries=-1)

        with pytest.raises(ValueError):
            ModelProviderConfig(max_retries=11)


# ==============================================================================
# MCPConfig Tests
# ==============================================================================


class TestMCPConfig:
    """Tests for MCPConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MCPConfig()

        assert config.enabled is False
        assert config.servers == []
        assert config.timeout_seconds == 30

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MCPConfig(
            enabled=True,
            servers=[{"name": "server1", "command": "python", "args": ["-m", "mcp"]}],
            timeout_seconds=60,
        )

        assert config.enabled is True
        assert len(config.servers) == 1
        assert config.timeout_seconds == 60

    def test_timeout_validation(self):
        """Test timeout_seconds must be >= 1."""
        with pytest.raises(ValueError):
            MCPConfig(timeout_seconds=0)


# ==============================================================================
# MultiAgentConfig Tests
# ==============================================================================


class TestMultiAgentConfig:
    """Tests for MultiAgentConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MultiAgentConfig()

        assert config.enabled is False
        assert config.orchestration_mode == "sequential"
        assert config.max_agents == 3

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MultiAgentConfig(
            enabled=True,
            orchestration_mode="concurrent",
            max_agents=5,
        )

        assert config.enabled is True
        assert config.orchestration_mode == "concurrent"
        assert config.max_agents == 5

    def test_orchestration_mode_validation(self):
        """Test orchestration_mode must be valid literal."""
        for mode in ["sequential", "concurrent", "hierarchical"]:
            config = MultiAgentConfig(orchestration_mode=mode)
            assert config.orchestration_mode == mode

    def test_max_agents_validation(self):
        """Test max_agents must be 1-10."""
        with pytest.raises(ValueError):
            MultiAgentConfig(max_agents=0)

        with pytest.raises(ValueError):
            MultiAgentConfig(max_agents=11)


# ==============================================================================
# StreamingConfig Tests
# ==============================================================================


class TestStreamingConfig:
    """Tests for StreamingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = StreamingConfig()

        assert config.enabled is False
        assert config.debounce_ms == 100

    def test_custom_values(self):
        """Test custom configuration values."""
        config = StreamingConfig(
            enabled=True,
            debounce_ms=200,
        )

        assert config.enabled is True
        assert config.debounce_ms == 200

    def test_debounce_validation(self):
        """Test debounce_ms must be >= 0."""
        with pytest.raises(ValueError):
            StreamingConfig(debounce_ms=-1)


# ==============================================================================
# AIConfig Tests
# ==============================================================================


class TestAIConfig:
    """Tests for AIConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AIConfig()

        assert config.enabled is False
        assert config.model == "openai:gpt-4o"
        assert config.api_key is None
        assert config.max_conversation_turns == 10
        assert config.temperature == 0.7
        assert config.max_tokens is None
        assert config.web_search_enabled is True
        assert config.web_search_max_results == 5
        assert config.conversation_timeout_minutes == 30
        assert config.tools_enabled is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AIConfig(
            enabled=True,
            model="anthropic:claude-3-5-sonnet-20241022",
            api_key="sk-test-key",
            temperature=0.5,
            max_tokens=4096,
            max_conversation_turns=20,
        )

        assert config.enabled is True
        assert config.model == "anthropic:claude-3-5-sonnet-20241022"
        assert config.api_key == "sk-test-key"
        assert config.temperature == 0.5
        assert config.max_tokens == 4096

    def test_temperature_validation(self):
        """Test temperature must be 0.0-2.0."""
        with pytest.raises(ValueError):
            AIConfig(temperature=-0.1)

        with pytest.raises(ValueError):
            AIConfig(temperature=2.1)

    def test_max_conversation_turns_validation(self):
        """Test max_conversation_turns must be 1-100."""
        with pytest.raises(ValueError):
            AIConfig(max_conversation_turns=0)

        with pytest.raises(ValueError):
            AIConfig(max_conversation_turns=101)

    def test_web_search_max_results_validation(self):
        """Test web_search_max_results must be 1-20."""
        with pytest.raises(ValueError):
            AIConfig(web_search_max_results=0)

        with pytest.raises(ValueError):
            AIConfig(web_search_max_results=21)

    def test_max_retries_validation(self):
        """Test max_retries must be 1-10."""
        with pytest.raises(ValueError):
            AIConfig(max_retries=0)

        with pytest.raises(ValueError):
            AIConfig(max_retries=11)

    def test_nested_configs(self):
        """Test nested configuration objects."""
        config = AIConfig(
            provider_config=ModelProviderConfig(provider="openai", timeout=120.0),
            mcp=MCPConfig(enabled=True),
            multi_agent=MultiAgentConfig(enabled=True, max_agents=5),
            streaming=StreamingConfig(enabled=True),
        )

        assert config.provider_config.provider == "openai"
        assert config.provider_config.timeout == 120.0
        assert config.mcp.enabled is True
        assert config.multi_agent.enabled is True
        assert config.multi_agent.max_agents == 5
        assert config.streaming.enabled is True

    def test_fallback_models(self):
        """Test fallback models configuration."""
        config = AIConfig(
            model="openai:gpt-4o",
            fallback_models=[
                "openai:gpt-4o-mini",
                "anthropic:claude-3-haiku-20240307",
            ],
        )

        assert len(config.fallback_models) == 2
        assert "openai:gpt-4o-mini" in config.fallback_models

    def test_system_prompt(self):
        """Test custom system prompt."""
        custom_prompt = "You are a specialized assistant."
        config = AIConfig(system_prompt=custom_prompt)

        assert config.system_prompt == custom_prompt

    def test_structured_output_settings(self):
        """Test structured output settings."""
        config = AIConfig(
            structured_output_enabled=True,
            output_validators_enabled=True,
            retry_on_validation_error=False,
        )

        assert config.structured_output_enabled is True
        assert config.output_validators_enabled is True
        assert config.retry_on_validation_error is False


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestConfigIntegration:
    """Integration tests for AI configuration."""

    def test_full_config_creation(self):
        """Test creating a full configuration."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="sk-test",
            provider_config=ModelProviderConfig(
                provider="openai",
                base_url="https://api.openai.com/v1",
                timeout=60.0,
                max_retries=3,
            ),
            fallback_models=["openai:gpt-4o-mini"],
            system_prompt="You are a helpful assistant.",
            max_conversation_turns=15,
            temperature=0.7,
            max_tokens=2048,
            web_search_enabled=True,
            web_search_max_results=5,
            conversation_timeout_minutes=30,
            tools_enabled=True,
            mcp=MCPConfig(
                enabled=True,
                servers=[{"name": "test", "command": "python"}],
            ),
            multi_agent=MultiAgentConfig(
                enabled=False,
                orchestration_mode="sequential",
            ),
            streaming=StreamingConfig(
                enabled=True,
                debounce_ms=100,
            ),
        )

        assert config.enabled is True
        assert config.model == "openai:gpt-4o"
        assert config.provider_config.provider == "openai"
        assert config.mcp.enabled is True
        assert config.streaming.enabled is True

    def test_config_serialization(self):
        """Test configuration can be serialized."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
        )

        # Should be able to dump to dict
        config_dict = config.model_dump()

        assert config_dict["enabled"] is True
        assert config_dict["model"] == "openai:gpt-4o"
        assert "provider_config" in config_dict
        assert "mcp" in config_dict

    def test_config_from_dict(self):
        """Test configuration can be created from dict."""
        config_dict = {
            "enabled": True,
            "model": "anthropic:claude-3-5-sonnet-20241022",
            "temperature": 0.5,
        }

        config = AIConfig(**config_dict)

        assert config.enabled is True
        assert config.model == "anthropic:claude-3-5-sonnet-20241022"
        assert config.temperature == 0.5
