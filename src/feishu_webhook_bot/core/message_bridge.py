"""Message Bridge Engine for cross-platform message forwarding.

This module implements the core logic for forwarding messages between
different platforms (e.g., QQ ↔ Feishu).
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

from .config import MessageBridgeConfig, MessageBridgeRuleConfig
from .logger import get_logger

if TYPE_CHECKING:
    from ..chat.models import IncomingMessage

logger = get_logger(__name__)


class MessageProviderProtocol(Protocol):
    """Protocol for message providers."""

    def send_text(self, text: str, target: str | None = None) -> Any:
        """Send a text message."""
        ...


@dataclass
class BridgeStatistics:
    """Statistics for message bridge operations."""

    total_forwarded: int = 0
    total_failed: int = 0
    total_filtered: int = 0
    by_rule: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {
        "forwarded": 0,
        "failed": 0,
        "filtered": 0,
    }))
    last_forward_time: datetime | None = None
    start_time: datetime = field(default_factory=datetime.now)

    def record_forward(self, rule_name: str) -> None:
        """Record a successful forward."""
        self.total_forwarded += 1
        self.by_rule[rule_name]["forwarded"] += 1
        self.last_forward_time = datetime.now()

    def record_failure(self, rule_name: str) -> None:
        """Record a failed forward."""
        self.total_failed += 1
        self.by_rule[rule_name]["failed"] += 1

    def record_filtered(self, rule_name: str) -> None:
        """Record a filtered message."""
        self.total_filtered += 1
        self.by_rule[rule_name]["filtered"] += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            "total_forwarded": self.total_forwarded,
            "total_failed": self.total_failed,
            "total_filtered": self.total_filtered,
            "by_rule": dict(self.by_rule),
            "last_forward_time": (
                self.last_forward_time.isoformat() if self.last_forward_time else None
            ),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
        }


@dataclass
class RateLimiter:
    """Simple rate limiter for message forwarding."""

    max_per_minute: int = 60
    _timestamps: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def is_allowed(self, rule_name: str) -> bool:
        """Check if a message can be forwarded under rate limit."""
        now = time.time()
        window_start = now - 60.0

        # Clean old timestamps
        self._timestamps[rule_name] = [
            ts for ts in self._timestamps[rule_name] if ts > window_start
        ]

        # Check limit
        if len(self._timestamps[rule_name]) >= self.max_per_minute:
            return False

        # Record this attempt
        self._timestamps[rule_name].append(now)
        return True

    def get_remaining(self, rule_name: str) -> int:
        """Get remaining allowed messages for a rule."""
        now = time.time()
        window_start = now - 60.0
        current_count = len([
            ts for ts in self._timestamps[rule_name] if ts > window_start
        ])
        return max(0, self.max_per_minute - current_count)


class MessageBridgeEngine:
    """Engine for cross-platform message forwarding.

    This engine handles:
    - Message routing based on configured rules
    - Message transformation (format, prefix/suffix)
    - Filtering (keywords, senders)
    - Rate limiting
    - Statistics tracking
    """

    def __init__(
        self,
        config: MessageBridgeConfig,
        providers: dict[str, MessageProviderProtocol],
    ) -> None:
        """Initialize the bridge engine.

        Args:
            config: Bridge configuration
            providers: Dictionary of available message providers
        """
        self.config = config
        self.providers = providers
        self.statistics = BridgeStatistics()
        self.rate_limiter = RateLimiter(max_per_minute=config.rate_limit_per_minute)
        self._running = False
        self._rules_by_source: dict[str, list[MessageBridgeRuleConfig]] = defaultdict(list)

        # Index rules by source provider for faster lookup
        self._index_rules()

        logger.info(
            "Message bridge engine initialized with %d rules",
            len(config.rules),
        )

    def _index_rules(self) -> None:
        """Index rules by source provider for efficient lookup."""
        self._rules_by_source.clear()
        for rule in self.config.rules:
            if rule.enabled:
                self._rules_by_source[rule.source_provider].append(rule)

    def start(self) -> None:
        """Start the bridge engine."""
        if not self.config.enabled:
            logger.info("Message bridge is disabled")
            return

        self._running = True
        self.statistics = BridgeStatistics()
        logger.info("Message bridge engine started")

    def stop(self) -> None:
        """Stop the bridge engine."""
        self._running = False
        logger.info("Message bridge engine stopped")

    def is_running(self) -> bool:
        """Check if the engine is running."""
        return self._running and self.config.enabled

    async def handle_message(self, message: IncomingMessage) -> list[dict[str, Any]]:
        """Handle an incoming message and forward if rules match.

        Args:
            message: The incoming message to process

        Returns:
            List of forward results (one per matching rule)
        """
        if not self.is_running():
            return []

        results = []

        # Find matching rules for this message's source
        # Determine source provider from message platform
        source_provider = self._get_source_provider(message)
        if not source_provider:
            return []

        matching_rules = self._rules_by_source.get(source_provider, [])

        for rule in matching_rules:
            result = await self._process_rule(rule, message)
            if result:
                results.append(result)

        return results

    def _get_source_provider(self, message: IncomingMessage) -> str | None:
        """Determine the source provider name from a message."""
        # Try to match by platform
        platform = message.platform.lower()

        # Find a provider that matches this platform
        for name, provider in self.providers.items():
            provider_type = provider.__class__.__name__.lower()
            if platform in provider_type or provider_type in platform:
                return name

            # Check config for provider type
            # This is a simplified matching - in production you'd want more robust matching

        # Fallback: check if any rule's source_provider matches the platform
        for rule in self.config.rules:
            if platform in rule.source_provider.lower():
                return rule.source_provider

        return None

    async def _process_rule(
        self,
        rule: MessageBridgeRuleConfig,
        message: IncomingMessage,
    ) -> dict[str, Any] | None:
        """Process a single rule for a message.

        Args:
            rule: The bridge rule to apply
            message: The incoming message

        Returns:
            Result dictionary or None if filtered/skipped
        """
        # Check chat type filter
        if rule.source_chat_type != "all" and rule.source_chat_type != message.chat_type:
            return None

        # Check chat ID filter
        if rule.source_chat_ids and message.chat_id not in rule.source_chat_ids:
            return None

        # Check sender filters
        if not self._check_sender_filter(rule, message):
            self.statistics.record_filtered(rule.name)
            return {"rule": rule.name, "status": "filtered", "reason": "sender"}

        # Check keyword filters
        if not self._check_keyword_filter(rule, message):
            self.statistics.record_filtered(rule.name)
            return {"rule": rule.name, "status": "filtered", "reason": "keyword"}

        # Check rate limit
        if not self.rate_limiter.is_allowed(rule.name):
            logger.warning("Rate limit exceeded for rule: %s", rule.name)
            return {"rule": rule.name, "status": "rate_limited"}

        # Transform and forward the message
        try:
            transformed = self._transform_message(rule, message)
            success = await self._forward_message(rule, transformed)

            if success:
                self.statistics.record_forward(rule.name)
                return {"rule": rule.name, "status": "forwarded", "target": rule.target_chat_id}
            else:
                self.statistics.record_failure(rule.name)
                return {"rule": rule.name, "status": "failed"}

        except Exception as e:
            logger.error("Error forwarding message for rule %s: %s", rule.name, e)
            self.statistics.record_failure(rule.name)
            return {"rule": rule.name, "status": "error", "error": str(e)}

    def _check_sender_filter(
        self,
        rule: MessageBridgeRuleConfig,
        message: IncomingMessage,
    ) -> bool:
        """Check if message passes sender filters."""
        sender_id = message.sender_id

        # Check blacklist first
        if rule.sender_blacklist and sender_id in rule.sender_blacklist:
            return False

        # Check whitelist (if specified, sender must be in it)
        if rule.sender_whitelist and sender_id not in rule.sender_whitelist:
            return False

        return True

    def _check_keyword_filter(
        self,
        rule: MessageBridgeRuleConfig,
        message: IncomingMessage,
    ) -> bool:
        """Check if message passes keyword filters."""
        content = message.content.lower()

        # Check blacklist first
        for keyword in rule.keyword_blacklist:
            if keyword.lower() in content:
                return False

        # Check whitelist (if specified, at least one keyword must match)
        if rule.keyword_whitelist:
            matched = any(kw.lower() in content for kw in rule.keyword_whitelist)
            if not matched:
                return False

        return True

    def _transform_message(
        self,
        rule: MessageBridgeRuleConfig,
        message: IncomingMessage,
    ) -> str:
        """Transform message content according to rule settings."""
        # Start with the format template
        format_template = self.config.default_format

        # Build the transformed message
        source_name = message.platform.capitalize()
        sender_name = message.sender_name or message.sender_id
        content = message.content
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Apply format template
        if rule.include_sender_info:
            transformed = format_template.format(
                source=source_name,
                sender=sender_name,
                content=content,
                time=timestamp,
            )
        else:
            transformed = content

        # Apply prefix and suffix
        if rule.message_prefix:
            transformed = rule.message_prefix + transformed
        if rule.message_suffix:
            transformed = transformed + rule.message_suffix

        return transformed

    async def _forward_message(
        self,
        rule: MessageBridgeRuleConfig,
        content: str,
    ) -> bool:
        """Forward transformed message to target provider.

        Args:
            rule: The bridge rule
            content: Transformed message content

        Returns:
            True if forwarded successfully
        """
        target_provider = self.providers.get(rule.target_provider)
        if not target_provider:
            logger.error("Target provider not found: %s", rule.target_provider)
            return False

        try:
            # Send the message
            result = target_provider.send_text(content, rule.target_chat_id)

            # Check result
            if hasattr(result, "success"):
                return result.success
            return True

        except Exception as e:
            logger.error(
                "Failed to forward message to %s: %s",
                rule.target_provider,
                e,
            )

            # Retry if configured
            if self.config.retry_on_failure:
                for attempt in range(self.config.max_retries):
                    try:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        result = target_provider.send_text(content, rule.target_chat_id)
                        has_success = hasattr(result, "success")
                        if (has_success and result.success) or not has_success:
                            return True
                    except Exception as retry_error:
                        logger.warning(
                            "Retry %d failed for %s: %s",
                            attempt + 1,
                            rule.target_provider,
                            retry_error,
                        )

            return False

    def get_statistics(self) -> dict[str, Any]:
        """Get bridge statistics."""
        return self.statistics.to_dict()

    def get_rule_status(self, rule_name: str) -> dict[str, Any] | None:
        """Get status for a specific rule."""
        for rule in self.config.rules:
            if rule.name == rule_name:
                stats = self.statistics.by_rule.get(rule_name, {})
                return {
                    "name": rule.name,
                    "enabled": rule.enabled,
                    "source": rule.source_provider,
                    "target": rule.target_provider,
                    "forwarded": stats.get("forwarded", 0),
                    "failed": stats.get("failed", 0),
                    "filtered": stats.get("filtered", 0),
                    "rate_limit_remaining": self.rate_limiter.get_remaining(rule_name),
                }
        return None

    def enable_rule(self, rule_name: str) -> bool:
        """Enable a bridge rule."""
        for rule in self.config.rules:
            if rule.name == rule_name:
                rule.enabled = True
                self._index_rules()
                logger.info("Enabled bridge rule: %s", rule_name)
                return True
        return False

    def disable_rule(self, rule_name: str) -> bool:
        """Disable a bridge rule."""
        for rule in self.config.rules:
            if rule.name == rule_name:
                rule.enabled = False
                self._index_rules()
                logger.info("Disabled bridge rule: %s", rule_name)
                return True
        return False

    def add_rule(self, rule: MessageBridgeRuleConfig) -> None:
        """Add a new bridge rule."""
        self.config.rules.append(rule)
        self._index_rules()
        logger.info("Added bridge rule: %s", rule.name)

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a bridge rule."""
        for i, rule in enumerate(self.config.rules):
            if rule.name == rule_name:
                self.config.rules.pop(i)
                self._index_rules()
                logger.info("Removed bridge rule: %s", rule_name)
                return True
        return False

    def list_rules(self) -> list[dict[str, Any]]:
        """List all bridge rules with their status."""
        return [
            {
                "name": rule.name,
                "enabled": rule.enabled,
                "description": rule.description,
                "source_provider": rule.source_provider,
                "target_provider": rule.target_provider,
                "target_chat_id": rule.target_chat_id,
                "stats": self.statistics.by_rule.get(rule.name, {}),
            }
            for rule in self.config.rules
        ]
