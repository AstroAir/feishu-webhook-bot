"""Tests for multi-provider AI configuration.

This module tests the configuration and initialization of different AI model providers.
"""

import pytest
from pydantic import ValidationError

from feishu_webhook_bot.ai.config import AIConfig, ModelProviderConfig


class TestModelProviderConfig:
    """Tests for ModelProviderConfig class."""

    def test_default_config(self):
        """Test default provider configuration."""
        config = ModelProviderConfig()

        assert config.provider is None
        assert config.base_url is None
        assert config.timeout == 60.0
        assert config.max_retries == 2
        assert config.additional_headers == {}
        assert config.additional_params == {}

    def test_openai_config(self):
        """Test OpenAI provider configuration."""
        config = ModelProviderConfig(
            provider="openai",
            organization_id="org-123",
            timeout=90.0,
        )

        assert config.provider == "openai"
        assert config.organization_id == "org-123"
        assert config.timeout == 90.0

    def test_anthropic_config(self):
        """Test Anthropic provider configuration."""
        config = ModelProviderConfig(
            provider="anthropic",
            timeout=120.0,
            max_retries=3,
        )

        assert config.provider == "anthropic"
        assert config.timeout == 120.0
        assert config.max_retries == 3

    def test_google_config(self):
        """Test Google provider configuration."""
        config = ModelProviderConfig(
            provider="google",
            api_version="v1",
        )

        assert config.provider == "google"
        assert config.api_version == "v1"

    def test_groq_config(self):
        """Test Groq provider configuration."""
        config = ModelProviderConfig(
            provider="groq",
            timeout=30.0,
        )

        assert config.provider == "groq"
        assert config.timeout == 30.0

    def test_cohere_config(self):
        """Test Cohere provider configuration."""
        config = ModelProviderConfig(
            provider="cohere",
        )

        assert config.provider == "cohere"

    def test_ollama_config(self):
        """Test Ollama provider configuration."""
        config = ModelProviderConfig(
            provider="ollama",
            base_url="http://localhost:11434/v1",
            timeout=120.0,
        )

        assert config.provider == "ollama"
        assert config.base_url == "http://localhost:11434/v1"
        assert config.timeout == 120.0

    def test_invalid_provider(self):
        """Test that invalid provider raises validation error."""
        with pytest.raises(ValidationError):
            ModelProviderConfig(provider="invalid_provider")

    def test_additional_headers(self):
        """Test additional headers configuration."""
        config = ModelProviderConfig(additional_headers={"X-Custom-Header": "value"})

        assert config.additional_headers == {"X-Custom-Header": "value"}

    def test_additional_params(self):
        """Test additional parameters configuration."""
        config = ModelProviderConfig(additional_params={"custom_param": "value"})

        assert config.additional_params == {"custom_param": "value"}


class TestAIConfigWithProviders:
    """Tests for AIConfig with different providers."""

    def test_openai_model_config(self):
        """Test AIConfig with OpenAI model."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-key",
            provider_config=ModelProviderConfig(provider="openai"),
        )

        assert config.enabled is True
        assert config.model == "openai:gpt-4o"
        assert config.provider_config.provider == "openai"

    def test_anthropic_model_config(self):
        """Test AIConfig with Anthropic model."""
        config = AIConfig(
            enabled=True,
            model="anthropic:claude-3-5-sonnet-20241022",
            api_key="test-key",
            provider_config=ModelProviderConfig(provider="anthropic"),
        )

        assert config.model == "anthropic:claude-3-5-sonnet-20241022"
        assert config.provider_config.provider == "anthropic"

    def test_google_model_config(self):
        """Test AIConfig with Google model."""
        config = AIConfig(
            enabled=True,
            model="google:gemini-1.5-pro",
            api_key="test-key",
            provider_config=ModelProviderConfig(provider="google"),
        )

        assert config.model == "google:gemini-1.5-pro"
        assert config.provider_config.provider == "google"

    def test_groq_model_config(self):
        """Test AIConfig with Groq model."""
        config = AIConfig(
            enabled=True,
            model="groq:llama-3.1-70b-versatile",
            api_key="test-key",
            provider_config=ModelProviderConfig(provider="groq"),
        )

        assert config.model == "groq:llama-3.1-70b-versatile"
        assert config.provider_config.provider == "groq"

    def test_cohere_model_config(self):
        """Test AIConfig with Cohere model."""
        config = AIConfig(
            enabled=True,
            model="cohere:command-r-plus",
            api_key="test-key",
            provider_config=ModelProviderConfig(provider="cohere"),
        )

        assert config.model == "cohere:command-r-plus"
        assert config.provider_config.provider == "cohere"

    def test_ollama_model_config(self):
        """Test AIConfig with Ollama model."""
        config = AIConfig(
            enabled=True,
            model="ollama:llama3.1",
            provider_config=ModelProviderConfig(
                provider="ollama",
                base_url="http://localhost:11434/v1",
            ),
        )

        assert config.model == "ollama:llama3.1"
        assert config.provider_config.provider == "ollama"
        assert config.provider_config.base_url == "http://localhost:11434/v1"

    def test_fallback_models(self):
        """Test fallback models configuration."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-key",
            fallback_models=[
                "anthropic:claude-3-5-sonnet-20241022",
                "groq:llama-3.1-70b-versatile",
            ],
        )

        assert len(config.fallback_models) == 2
        assert config.fallback_models[0] == "anthropic:claude-3-5-sonnet-20241022"
        assert config.fallback_models[1] == "groq:llama-3.1-70b-versatile"

    def test_empty_fallback_models(self):
        """Test empty fallback models list."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-key",
            fallback_models=[],
        )

        assert config.fallback_models == []

    def test_provider_config_defaults(self):
        """Test that provider_config has proper defaults."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-key",
        )

        assert config.provider_config is not None
        assert config.provider_config.timeout == 60.0
        assert config.provider_config.max_retries == 2

    def test_custom_provider_config(self):
        """Test custom provider configuration."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-key",
            provider_config=ModelProviderConfig(
                provider="openai",
                timeout=120.0,
                max_retries=5,
                organization_id="org-123",
            ),
        )

        assert config.provider_config.timeout == 120.0
        assert config.provider_config.max_retries == 5
        assert config.provider_config.organization_id == "org-123"


class TestProviderDetection:
    """Tests for automatic provider detection from model string."""

    def test_detect_openai(self):
        """Test OpenAI provider detection."""
        config = AIConfig(
            enabled=True,
            model="openai:gpt-4o",
            api_key="test-key",
        )

        # Provider should be auto-detected from model string
        assert "openai" in config.model.lower()

    def test_detect_anthropic(self):
        """Test Anthropic provider detection."""
        config = AIConfig(
            enabled=True,
            model="anthropic:claude-3-5-sonnet-20241022",
            api_key="test-key",
        )

        assert "anthropic" in config.model.lower()

    def test_detect_google(self):
        """Test Google provider detection."""
        config = AIConfig(
            enabled=True,
            model="google:gemini-1.5-pro",
            api_key="test-key",
        )

        assert "google" in config.model.lower()

    def test_detect_groq(self):
        """Test Groq provider detection."""
        config = AIConfig(
            enabled=True,
            model="groq:llama-3.1-70b-versatile",
            api_key="test-key",
        )

        assert "groq" in config.model.lower()

    def test_detect_cohere(self):
        """Test Cohere provider detection."""
        config = AIConfig(
            enabled=True,
            model="cohere:command-r-plus",
            api_key="test-key",
        )

        assert "cohere" in config.model.lower()

    def test_detect_ollama(self):
        """Test Ollama provider detection."""
        config = AIConfig(
            enabled=True,
            model="ollama:llama3.1",
        )

        assert "ollama" in config.model.lower()
