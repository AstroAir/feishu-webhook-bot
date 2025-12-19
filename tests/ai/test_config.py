"""Comprehensive tests for AI configuration module.

Tests cover:
- ModelProviderConfig validation
- MCPConfig validation
- MultiAgentConfig validation
- ModelRouterConfig validation
- BudgetTrackingConfig validation
- HealthCheckConfig validation
- ABTestConfig validation
- WebSearchConfig validation
- SearchProviderConfig validation
- ConversationPersistenceConfig validation
- StreamingConfig validation
- AIConfig validation and defaults
"""

from __future__ import annotations

import pytest

from feishu_webhook_bot.ai.config import (
    ABTestConfig,
    AIConfig,
    BudgetTrackingConfig,
    ConversationPersistenceConfig,
    HealthCheckConfig,
    MCPConfig,
    ModelProviderConfig,
    ModelRouterConfig,
    MultiAgentConfig,
    SearchProviderConfig,
    StreamingConfig,
    WebSearchConfig,
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
        assert config.max_agents == 10
        assert config.auto_decompose is True
        assert config.decompose_threshold == 7

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MultiAgentConfig(
            enabled=True,
            orchestration_mode="concurrent",
            max_agents=5,
            auto_decompose=False,
            decompose_threshold=5,
        )

        assert config.enabled is True
        assert config.orchestration_mode == "concurrent"
        assert config.max_agents == 5
        assert config.auto_decompose is False
        assert config.decompose_threshold == 5

    def test_orchestration_mode_validation(self):
        """Test orchestration_mode must be valid literal."""
        for mode in ["sequential", "concurrent", "hierarchical", "dynamic", "pipeline"]:
            config = MultiAgentConfig(orchestration_mode=mode)
            assert config.orchestration_mode == mode

    def test_max_agents_validation(self):
        """Test max_agents must be 1-20."""
        with pytest.raises(ValueError):
            MultiAgentConfig(max_agents=0)

        with pytest.raises(ValueError):
            MultiAgentConfig(max_agents=21)

    def test_decompose_threshold_validation(self):
        """Test decompose_threshold must be 1-10."""
        with pytest.raises(ValueError):
            MultiAgentConfig(decompose_threshold=0)

        with pytest.raises(ValueError):
            MultiAgentConfig(decompose_threshold=11)

    def test_default_agents(self):
        """Test default_agents list."""
        config = MultiAgentConfig()

        assert "search" in config.default_agents
        assert "analysis" in config.default_agents
        assert "response" in config.default_agents
        assert "code" in config.default_agents

    def test_nested_router_config(self):
        """Test nested ModelRouterConfig."""
        config = MultiAgentConfig(
            enabled=True,
            router=ModelRouterConfig(
                strategy="cost_optimized",
                cost_threshold=0.02,
            ),
        )

        assert config.router.strategy == "cost_optimized"
        assert config.router.cost_threshold == 0.02


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


# ==============================================================================
# WebSearchConfig Tests
# ==============================================================================


class TestWebSearchConfig:
    """Tests for WebSearchConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = WebSearchConfig()

        assert config.enabled is True
        assert config.default_provider == "duckduckgo"
        assert config.max_results == 5
        assert config.cache_enabled is True
        assert config.cache_ttl_minutes == 60
        assert config.enable_failover is True
        assert config.concurrent_search is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = WebSearchConfig(
            enabled=False,
            default_provider="tavily",
            max_results=10,
            cache_enabled=False,
            cache_ttl_minutes=30,
            enable_failover=False,
            concurrent_search=True,
        )

        assert config.enabled is False
        assert config.default_provider == "tavily"
        assert config.max_results == 10
        assert config.cache_enabled is False
        assert config.concurrent_search is True

    def test_max_results_validation(self):
        """Test max_results must be 1-50."""
        with pytest.raises(ValueError):
            WebSearchConfig(max_results=0)

        with pytest.raises(ValueError):
            WebSearchConfig(max_results=51)

    def test_cache_ttl_validation(self):
        """Test cache_ttl_minutes must be 1-1440."""
        with pytest.raises(ValueError):
            WebSearchConfig(cache_ttl_minutes=0)

        with pytest.raises(ValueError):
            WebSearchConfig(cache_ttl_minutes=1441)

    def test_with_providers(self):
        """Test WebSearchConfig with provider list."""
        config = WebSearchConfig(
            providers=[
                SearchProviderConfig(provider="duckduckgo", priority=0),
                SearchProviderConfig(provider="tavily", api_key="key", priority=10),
            ]
        )

        assert len(config.providers) == 2
        assert config.providers[0].provider == "duckduckgo"
        assert config.providers[1].provider == "tavily"


# ==============================================================================
# SearchProviderConfig Tests
# ==============================================================================


class TestSearchProviderConfig:
    """Tests for SearchProviderConfig."""

    def test_required_provider(self):
        """Test provider is required."""
        config = SearchProviderConfig(provider="duckduckgo")
        assert config.provider == "duckduckgo"

    def test_default_values(self):
        """Test default configuration values."""
        config = SearchProviderConfig(provider="tavily")

        assert config.enabled is True
        assert config.api_key is None
        assert config.priority == 100
        assert config.options == {}

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SearchProviderConfig(
            provider="brave",
            enabled=False,
            api_key="test-api-key",
            priority=5,
            options={"country": "us", "safe_search": True},
        )

        assert config.provider == "brave"
        assert config.enabled is False
        assert config.api_key == "test-api-key"
        assert config.priority == 5
        assert config.options["country"] == "us"

    def test_priority_validation(self):
        """Test priority must be >= 0."""
        with pytest.raises(ValueError):
            SearchProviderConfig(provider="test", priority=-1)


# ==============================================================================
# ModelRouterConfig Tests
# ==============================================================================


class TestModelRouterConfig:
    """Tests for ModelRouterConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ModelRouterConfig()

        assert config.enabled is True
        assert config.strategy == "balanced"
        assert config.default_model == "openai:gpt-4o"
        assert config.cost_threshold == 0.01
        assert config.min_speed_rating == 7
        assert config.min_quality_rating == 8
        assert config.language_routing is True
        assert config.adaptive_learning is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ModelRouterConfig(
            enabled=False,
            strategy="cost_optimized",
            default_model="anthropic:claude-3-5-sonnet-20241022",
            cost_threshold=0.02,
            min_speed_rating=5,
            min_quality_rating=9,
        )

        assert config.enabled is False
        assert config.strategy == "cost_optimized"
        assert config.default_model == "anthropic:claude-3-5-sonnet-20241022"
        assert config.cost_threshold == 0.02

    def test_all_strategies(self):
        """Test all routing strategies are valid."""
        strategies = [
            "cost_optimized",
            "speed_optimized",
            "quality_optimized",
            "balanced",
            "round_robin",
            "capability_based",
            "context_aware",
            "adaptive",
            "budget_aware",
            "latency_optimized",
        ]

        for strategy in strategies:
            config = ModelRouterConfig(strategy=strategy)
            assert config.strategy == strategy

    def test_speed_rating_validation(self):
        """Test min_speed_rating must be 1-10."""
        with pytest.raises(ValueError):
            ModelRouterConfig(min_speed_rating=0)

        with pytest.raises(ValueError):
            ModelRouterConfig(min_speed_rating=11)

    def test_quality_rating_validation(self):
        """Test min_quality_rating must be 1-10."""
        with pytest.raises(ValueError):
            ModelRouterConfig(min_quality_rating=0)

        with pytest.raises(ValueError):
            ModelRouterConfig(min_quality_rating=11)

    def test_nested_budget_config(self):
        """Test nested BudgetTrackingConfig."""
        config = ModelRouterConfig(
            budget=BudgetTrackingConfig(
                enabled=True,
                limit=50.0,
                warning_threshold=0.9,
            )
        )

        assert config.budget.enabled is True
        assert config.budget.limit == 50.0
        assert config.budget.warning_threshold == 0.9

    def test_nested_health_check_config(self):
        """Test nested HealthCheckConfig."""
        config = ModelRouterConfig(
            health_check=HealthCheckConfig(
                enabled=False,
                check_interval_seconds=600,
            )
        )

        assert config.health_check.enabled is False
        assert config.health_check.check_interval_seconds == 600

    def test_nested_ab_test_config(self):
        """Test nested ABTestConfig."""
        config = ModelRouterConfig(
            ab_test=ABTestConfig(
                enabled=True,
                test_ratio=0.2,
                test_models=["openai:gpt-4o", "anthropic:claude-3-5-sonnet-20241022"],
            )
        )

        assert config.ab_test.enabled is True
        assert config.ab_test.test_ratio == 0.2
        assert len(config.ab_test.test_models) == 2


# ==============================================================================
# BudgetTrackingConfig Tests
# ==============================================================================


class TestBudgetTrackingConfig:
    """Tests for BudgetTrackingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = BudgetTrackingConfig()

        assert config.enabled is False
        assert config.period == "daily"
        assert config.limit == 10.0
        assert config.warning_threshold == 0.8
        assert config.hard_limit is False
        assert config.notify_on_warning is True
        assert config.notify_on_exceeded is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = BudgetTrackingConfig(
            enabled=True,
            period="monthly",
            limit=100.0,
            warning_threshold=0.7,
            hard_limit=True,
            notify_on_warning=False,
        )

        assert config.enabled is True
        assert config.period == "monthly"
        assert config.limit == 100.0
        assert config.warning_threshold == 0.7
        assert config.hard_limit is True

    def test_all_periods(self):
        """Test all budget periods are valid."""
        for period in ["hourly", "daily", "weekly", "monthly"]:
            config = BudgetTrackingConfig(period=period)
            assert config.period == period

    def test_limit_validation(self):
        """Test limit must be >= 0."""
        with pytest.raises(ValueError):
            BudgetTrackingConfig(limit=-1.0)

    def test_warning_threshold_validation(self):
        """Test warning_threshold must be 0.0-1.0."""
        with pytest.raises(ValueError):
            BudgetTrackingConfig(warning_threshold=-0.1)

        with pytest.raises(ValueError):
            BudgetTrackingConfig(warning_threshold=1.1)


# ==============================================================================
# HealthCheckConfig Tests
# ==============================================================================


class TestHealthCheckConfig:
    """Tests for HealthCheckConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HealthCheckConfig()

        assert config.enabled is True
        assert config.check_interval_seconds == 300
        assert config.unhealthy_threshold == 3
        assert config.recovery_threshold == 2
        assert config.auto_disable_unhealthy is False
        assert config.failover_enabled is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HealthCheckConfig(
            enabled=False,
            check_interval_seconds=600,
            unhealthy_threshold=5,
            recovery_threshold=3,
            auto_disable_unhealthy=True,
            failover_enabled=False,
        )

        assert config.enabled is False
        assert config.check_interval_seconds == 600
        assert config.unhealthy_threshold == 5
        assert config.recovery_threshold == 3

    def test_check_interval_validation(self):
        """Test check_interval_seconds must be 60-3600."""
        with pytest.raises(ValueError):
            HealthCheckConfig(check_interval_seconds=30)

        with pytest.raises(ValueError):
            HealthCheckConfig(check_interval_seconds=4000)

    def test_threshold_validation(self):
        """Test threshold values must be 1-10."""
        with pytest.raises(ValueError):
            HealthCheckConfig(unhealthy_threshold=0)

        with pytest.raises(ValueError):
            HealthCheckConfig(unhealthy_threshold=11)

        with pytest.raises(ValueError):
            HealthCheckConfig(recovery_threshold=0)

        with pytest.raises(ValueError):
            HealthCheckConfig(recovery_threshold=11)


# ==============================================================================
# ABTestConfig Tests
# ==============================================================================


class TestABTestConfig:
    """Tests for ABTestConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ABTestConfig()

        assert config.enabled is False
        assert config.test_ratio == 0.1
        assert config.test_models == []
        assert config.min_samples == 100
        assert config.auto_promote is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ABTestConfig(
            enabled=True,
            test_ratio=0.3,
            test_models=["model1", "model2"],
            min_samples=50,
            auto_promote=True,
        )

        assert config.enabled is True
        assert config.test_ratio == 0.3
        assert len(config.test_models) == 2
        assert config.min_samples == 50
        assert config.auto_promote is True

    def test_test_ratio_validation(self):
        """Test test_ratio must be 0.0-0.5."""
        with pytest.raises(ValueError):
            ABTestConfig(test_ratio=-0.1)

        with pytest.raises(ValueError):
            ABTestConfig(test_ratio=0.6)

    def test_min_samples_validation(self):
        """Test min_samples must be >= 10."""
        with pytest.raises(ValueError):
            ABTestConfig(min_samples=5)


# ==============================================================================
# ConversationPersistenceConfig Tests
# ==============================================================================


class TestConversationPersistenceConfig:
    """Tests for ConversationPersistenceConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ConversationPersistenceConfig()

        assert config.enabled is False
        assert config.database_url == "sqlite:///data/conversations.db"
        assert config.max_history_days == 30
        assert config.auto_cleanup is True
        assert config.cleanup_interval_hours == 24

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ConversationPersistenceConfig(
            enabled=True,
            database_url="postgresql://localhost/conversations",
            max_history_days=90,
            auto_cleanup=False,
            cleanup_interval_hours=12,
        )

        assert config.enabled is True
        assert config.database_url == "postgresql://localhost/conversations"
        assert config.max_history_days == 90
        assert config.auto_cleanup is False
        assert config.cleanup_interval_hours == 12

    def test_max_history_days_validation(self):
        """Test max_history_days must be 1-365."""
        with pytest.raises(ValueError):
            ConversationPersistenceConfig(max_history_days=0)

        with pytest.raises(ValueError):
            ConversationPersistenceConfig(max_history_days=366)

    def test_cleanup_interval_validation(self):
        """Test cleanup_interval_hours must be 1-168."""
        with pytest.raises(ValueError):
            ConversationPersistenceConfig(cleanup_interval_hours=0)

        with pytest.raises(ValueError):
            ConversationPersistenceConfig(cleanup_interval_hours=169)


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
