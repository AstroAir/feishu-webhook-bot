"""Provider initialization mixin for FeishuBot."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...core import get_logger
from ...core.circuit_breaker import CircuitBreakerConfig
from ...core.config import ProviderConfigBase, WebhookConfig
from ...core.provider import BaseProvider

if TYPE_CHECKING:
    from ..base import BotBase

logger = get_logger("bot.init.provider")


class ProviderInitializerMixin:
    """Mixin for provider initialization."""

    def _convert_circuit_breaker_config(
        self: BotBase, policy_config: Any
    ) -> CircuitBreakerConfig | None:
        """Convert CircuitBreakerPolicyConfig to CircuitBreakerConfig.

        Args:
            policy_config: CircuitBreakerPolicyConfig or dict

        Returns:
            CircuitBreakerConfig or None
        """
        if not policy_config:
            return None

        try:
            failure_threshold = getattr(policy_config, "failure_threshold", 5)
            reset_timeout = getattr(policy_config, "reset_timeout", 30.0)
            half_open_max = getattr(policy_config, "half_open_max_calls", 3)

            return CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                success_threshold=half_open_max,
                timeout_seconds=reset_timeout,
            )
        except Exception as exc:
            logger.warning("Failed to convert circuit breaker config: %s", exc)
            return None

    def _init_providers(self: BotBase) -> None:
        """Initialize message providers from configuration.

        Supports both new provider configuration and backward compatibility
        with legacy webhooks configuration.
        """
        provider_configs = self.config.providers or []

        # If no providers configured but webhooks exist, create FeishuProviders from webhooks
        if not provider_configs and self.config.webhooks:
            logger.info(
                "No providers configured, creating FeishuProviders from %d webhook(s)",
                len(self.config.webhooks),
            )
            for webhook in self.config.webhooks:
                try:
                    provider = self._create_provider_from_webhook(webhook)
                    if provider:
                        self.providers[provider.name] = provider
                        logger.info("Created provider from webhook: %s", provider.name)
                except Exception as exc:
                    logger.error(
                        "Failed to create provider from webhook '%s': %s",
                        webhook.name,
                        exc,
                        exc_info=True,
                    )
        else:
            # Initialize from provider configurations
            for provider_config in provider_configs:
                if not provider_config.enabled:
                    logger.info("Provider '%s' is disabled, skipping", provider_config.name)
                    continue

                try:
                    provider = self._create_provider(provider_config)
                    if provider:
                        self.providers[provider.name] = provider
                        logger.info(
                            "Initialized provider: %s (%s)",
                            provider.name,
                            provider_config.provider_type,
                        )
                except Exception as exc:
                    logger.error(
                        "Failed to initialize provider '%s': %s",
                        provider_config.name,
                        exc,
                        exc_info=True,
                    )

        # Set default provider
        if self.providers:
            default_name = self.config.default_provider
            if default_name and default_name in self.providers:
                self.default_provider = self.providers[default_name]
            else:
                # Use first provider as default
                first_name = next(iter(self.providers))
                self.default_provider = self.providers[first_name]
                if default_name:
                    logger.warning(
                        "Default provider '%s' not found, using '%s'",
                        default_name,
                        first_name,
                    )
            logger.info("Default provider set to: %s", self.default_provider.name)
        else:
            logger.info("No providers initialized")

    def _create_provider_from_webhook(self: BotBase, webhook: WebhookConfig) -> BaseProvider | None:
        """Create a FeishuProvider from a legacy WebhookConfig.

        Args:
            webhook: Legacy webhook configuration

        Returns:
            FeishuProvider instance or None if creation failed
        """
        try:
            from ...providers.feishu import FeishuProvider, FeishuProviderConfig

            config = FeishuProviderConfig(
                provider_type="feishu",
                name=webhook.name,
                url=webhook.url,
                secret=webhook.secret,
                timeout=webhook.timeout or self.config.http.timeout,
                retry=webhook.retry or self.config.http.retry,
                headers=webhook.headers,
            )
            return FeishuProvider(
                config,
                message_tracker=self.message_tracker,
                circuit_breaker_config=None,  # No circuit breaker config in legacy webhooks
            )
        except ImportError:
            logger.warning("FeishuProvider not available, skipping webhook conversion")
            return None
        except Exception as exc:
            logger.error("Failed to create FeishuProvider: %s", exc, exc_info=True)
            return None

    def _create_provider(self: BotBase, config: ProviderConfigBase) -> BaseProvider | None:
        """Create a provider instance from configuration.

        Args:
            config: Provider configuration

        Returns:
            Provider instance or None if creation failed
        """
        provider_type = config.provider_type

        # Extract and convert circuit breaker config
        cb_config = self._convert_circuit_breaker_config(config.circuit_breaker)

        if provider_type == "feishu":
            try:
                from ...providers.feishu import FeishuProvider, FeishuProviderConfig

                feishu_config = FeishuProviderConfig(
                    provider_type="feishu",
                    name=config.name,
                    url=config.webhook_url or "",
                    secret=config.secret,
                    timeout=config.timeout or self.config.http.timeout,
                    retry=config.retry or self.config.http.retry,
                    headers=config.headers,
                )
                return FeishuProvider(
                    feishu_config,
                    message_tracker=self.message_tracker,
                    circuit_breaker_config=cb_config,
                )
            except ImportError as exc:
                logger.error("FeishuProvider not available: %s", exc)
                return None

        elif provider_type == "napcat":
            try:
                from ...providers.qq_napcat import NapcatProvider, NapcatProviderConfig

                napcat_config = NapcatProviderConfig(
                    provider_type="napcat",
                    name=config.name,
                    http_url=config.http_url,
                    access_token=config.access_token,
                    default_target=config.default_target,
                    timeout=config.timeout or self.config.http.timeout,
                    retry=config.retry,
                    circuit_breaker=config.circuit_breaker,
                    message_tracking=config.message_tracking,
                    # QQ-specific configurations
                    bot_qq=getattr(config, "bot_qq", None),
                    enable_ai_voice=getattr(config, "enable_ai_voice", False),
                )
                provider = NapcatProvider(
                    napcat_config,
                    message_tracker=self.message_tracker,
                    circuit_breaker_config=cb_config,
                )
                logger.info(
                    "NapcatProvider initialized: name=%s, bot_qq=%s",
                    config.name,
                    napcat_config.bot_qq,
                )
                return provider
            except ImportError as exc:
                logger.error("NapcatProvider not available: %s", exc)
                return None

        else:
            logger.warning("Unknown provider type: %s", provider_type)
            return None

    def get_provider(self: BotBase, name: str | None = None) -> BaseProvider | None:
        """Get a provider by name.

        Args:
            name: Provider name. If None, returns the default provider.

        Returns:
            Provider instance or None if not found.
        """
        if name is None:
            return self.default_provider
        return self.providers.get(name)
