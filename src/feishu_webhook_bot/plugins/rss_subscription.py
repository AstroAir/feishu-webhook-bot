"""RSS Subscription Plugin with AI enhancement.

This plugin provides RSS feed monitoring with:
- Multiple feed support with per-feed configuration
- AI-powered summarization, classification, and keyword extraction
- Intelligent aggregation for batch notifications
- Beautiful card-based display
- Command interface for managing subscriptions
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import feedparser
import httpx
from pydantic import Field

from ..core.client import CardBuilder
from ..core.logger import get_logger
from .base import BasePlugin, PluginMetadata
from .config_schema import FieldType, PluginConfigSchema
from .manifest import PackageDependency, PermissionRequest, PermissionType

if TYPE_CHECKING:
    from ..ai.agent import AIAgent
    from ..ai.commands import CommandHandler, CommandResult
    from ..core.message_handler import IncomingMessage

logger = get_logger(__name__)

# Try to import html2text for better text extraction
try:
    import html2text

    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RSSFeed:
    """RSS feed configuration."""

    name: str
    url: str
    check_interval_minutes: int = 30
    enabled: bool = True
    max_entries: int = 10
    tags: list[str] = field(default_factory=list)
    webhook_target: str = "default"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RSSFeed:
        """Create RSSFeed from dictionary."""
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            check_interval_minutes=data.get("check_interval_minutes", 30),
            enabled=data.get("enabled", True),
            max_entries=data.get("max_entries", 10),
            tags=data.get("tags", []),
            webhook_target=data.get("webhook_target", "default"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "check_interval_minutes": self.check_interval_minutes,
            "enabled": self.enabled,
            "max_entries": self.max_entries,
            "tags": self.tags,
            "webhook_target": self.webhook_target,
        }


@dataclass
class RSSEntry:
    """Parsed RSS entry with metadata."""

    id: str
    title: str
    link: str
    description: str = ""
    published: datetime | None = None
    author: str = ""
    feed_name: str = ""
    feed_url: str = ""

    # AI-generated fields
    summary: str = ""
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def get_display_time(self) -> str:
        """Get formatted display time."""
        if self.published:
            return self.published.strftime("%m-%d %H:%M")
        return ""


@dataclass
class FeedCheckResult:
    """Result of a feed check operation."""

    feed: RSSFeed
    entries: list[RSSEntry] = field(default_factory=list)
    new_count: int = 0
    error: str | None = None
    check_time: datetime = field(default_factory=lambda: datetime.now(UTC))


# =============================================================================
# Configuration Schema
# =============================================================================


class RSSConfigSchema(PluginConfigSchema):
    """Configuration schema for RSS subscription plugin."""

    # Feed Management
    feeds: list[dict[str, Any]] = Field(
        default=[],
        description="List of RSS feed configurations",
        json_schema_extra={
            "example": "[{name: 'Tech News', url: 'https://...', check_interval_minutes: 30}]"
        },
    )

    default_check_interval_minutes: int = Field(
        default=30,
        description="Default check interval for feeds (minutes)",
        ge=5,
        le=1440,
    )

    # AI Settings
    ai_enabled: bool = Field(
        default=False,
        description="Enable AI processing for entries",
    )

    ai_summarization: bool = Field(
        default=True,
        description="Generate AI summaries for entries",
        json_schema_extra={"depends_on": "ai_enabled"},
    )

    ai_classification: bool = Field(
        default=True,
        description="AI-based content classification",
        json_schema_extra={"depends_on": "ai_enabled"},
    )

    ai_keyword_extraction: bool = Field(
        default=False,
        description="Extract keywords using AI",
        json_schema_extra={"depends_on": "ai_enabled"},
    )

    ai_max_summary_length: int = Field(
        default=150,
        description="Maximum length for AI summaries",
        ge=50,
        le=500,
        json_schema_extra={"depends_on": "ai_enabled"},
    )

    # Aggregation Settings
    aggregation_enabled: bool = Field(
        default=True,
        description="Aggregate multiple updates into single card",
    )

    aggregation_max_entries: int = Field(
        default=5,
        description="Maximum entries per aggregated card",
        ge=1,
        le=20,
    )

    aggregation_window_minutes: int = Field(
        default=5,
        description="Time window for aggregation (minutes)",
        ge=1,
        le=60,
    )

    # Notification Settings
    webhook_name: str = Field(
        default="default",
        description="Default webhook for notifications",
    )

    card_template: str = Field(
        default="detailed",
        description="Card display style",
        json_schema_extra={"choices": ["minimal", "compact", "detailed", "full"]},
    )

    # Storage
    history_days: int = Field(
        default=7,
        description="Days to keep entry history for deduplication",
        ge=1,
        le=30,
    )

    _field_groups = {
        "Feed Management": ["feeds", "default_check_interval_minutes"],
        "AI Processing": [
            "ai_enabled",
            "ai_summarization",
            "ai_classification",
            "ai_keyword_extraction",
            "ai_max_summary_length",
        ],
        "Aggregation": [
            "aggregation_enabled",
            "aggregation_max_entries",
            "aggregation_window_minutes",
        ],
        "Notifications": ["webhook_name", "card_template"],
        "Storage": ["history_days"],
    }


# =============================================================================
# AI Prompts
# =============================================================================

SUMMARY_PROMPT = """请用中文简洁地总结以下文章内容，不超过{max_length}个字。
重点提取关键信息和主要观点。

标题：{title}
内容：{content}

摘要："""

CLASSIFICATION_PROMPT = """请将这篇文章分类到1-3个类别中，从以下类别选择：
科技、编程、AI/机器学习、云计算、安全、DevOps、开源、商业、科学、教程、新闻、观点、发布

标题：{title}
内容：{content}

类别（用逗号分隔）："""

KEYWORD_PROMPT = """请从这篇文章中提取3-5个关键词或短语，用于快速了解文章主题。

标题：{title}
内容：{content}

关键词（用逗号分隔）："""


# =============================================================================
# Plugin Implementation
# =============================================================================


class RSSSubscriptionPlugin(BasePlugin):
    """RSS Subscription Plugin with AI enhancement.

    Provides comprehensive RSS feed monitoring with:
    - Multiple feed support with per-feed configuration
    - AI-powered summarization, classification, and keyword extraction
    - Intelligent aggregation for batch notifications
    - Beautiful card-based display
    - Command interface for managing subscriptions
    """

    # Configuration schema
    config_schema = RSSConfigSchema

    # Python dependencies
    PYTHON_DEPENDENCIES = [
        PackageDependency("feedparser", ">=6.0.0"),
        PackageDependency("html2text", ">=2024.0.0", optional=True),
    ]

    # Permissions
    PERMISSIONS = [
        PermissionRequest(
            permission=PermissionType.NETWORK_ACCESS,
            reason="抓取 RSS 订阅源",
            scope="*",
        ),
        PermissionRequest(
            permission=PermissionType.SCHEDULE_JOBS,
            reason="定时检查 RSS 更新",
        ),
        PermissionRequest(
            permission=PermissionType.SEND_MESSAGES,
            reason="发送 RSS 更新通知",
        ),
    ]

    TAGS = ["rss", "news", "aggregation", "ai"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize RSS subscription plugin."""
        super().__init__(*args, **kwargs)

        # Feed storage
        self._feeds: dict[str, RSSFeed] = {}

        # Entry history for deduplication
        self._seen_entries: dict[str, datetime] = {}

        # Aggregation buffer: webhook_target -> list of entries
        self._aggregation_buffer: dict[str, list[RSSEntry]] = {}
        self._last_flush_time: datetime = datetime.now(UTC)

        # Storage path for persistence
        self._storage_path: Path | None = None

        # AI agent reference (set by bot)
        self._ai_agent: AIAgent | None = None

        # Command handler reference
        self._command_handler: CommandHandler | None = None

        # HTTP client
        self._http_client: httpx.AsyncClient | None = None

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="rss-subscription",
            version="1.0.0",
            description="RSS 订阅与 AI 增强插件",
            author="Feishu Bot",
            enabled=True,
        )

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        self.logger.info("Loading RSS subscription plugin")

        # Load feeds from configuration
        feeds_config = self.get_config_value("feeds", [])
        for feed_data in feeds_config:
            feed = RSSFeed.from_dict(feed_data)
            if feed.name and feed.url:
                self._feeds[feed.name] = feed
                self.logger.debug("Loaded feed: %s", feed.name)

        # Set up storage path
        storage_dir = Path.home() / ".feishu-bot" / "rss"
        storage_dir.mkdir(parents=True, exist_ok=True)
        self._storage_path = storage_dir / "history.json"

        # Load entry history
        self._load_history()

        self.logger.info("Loaded %d RSS feeds", len(self._feeds))

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        self.logger.info("Enabling RSS subscription plugin")

        # Initialize HTTP client
        self._http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "FeishuBot-RSS/1.0"},
        )

        # Register feed check job
        check_interval = self.get_config_value("default_check_interval_minutes", 30)
        self.register_job(
            self._check_all_feeds_sync,
            trigger="interval",
            job_id="rss_feed_check",
            minutes=check_interval,
        )

        # Register aggregation flush job
        agg_window = self.get_config_value("aggregation_window_minutes", 5)
        if self.get_config_value("aggregation_enabled", True):
            self.register_job(
                self._flush_pending_sync,
                trigger="interval",
                job_id="rss_aggregation_flush",
                minutes=agg_window,
            )

        # Register commands if handler is available
        self._register_commands()

        self.logger.info(
            "RSS plugin enabled with check interval=%d min, aggregation window=%d min",
            check_interval,
            agg_window,
        )

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        self.logger.info("Disabling RSS subscription plugin")

        # Flush pending aggregations
        try:
            asyncio.run(self._flush_all_aggregations())
        except Exception as e:
            self.logger.error("Error flushing aggregations: %s", e)

        # Save history
        self._save_history()

        # Close HTTP client
        if self._http_client:
            try:
                asyncio.run(self._http_client.aclose())
            except Exception:
                pass
            self._http_client = None

        # Cleanup jobs
        self.cleanup_jobs()

        self.logger.info("RSS plugin disabled")

    def on_unload(self) -> None:
        """Called before plugin hot reload."""
        self._save_history()
        self.logger.debug("RSS plugin unloaded")

    # =========================================================================
    # Feed Operations
    # =========================================================================

    async def fetch_feed(self, feed: RSSFeed) -> FeedCheckResult:
        """Fetch and parse an RSS feed.

        Args:
            feed: Feed configuration

        Returns:
            FeedCheckResult with parsed entries
        """
        result = FeedCheckResult(feed=feed)

        try:
            # Fetch feed content
            if not self._http_client:
                self._http_client = httpx.AsyncClient(timeout=30.0)

            response = await self._http_client.get(feed.url)
            response.raise_for_status()
            content = response.text

            # Parse feed
            parsed = feedparser.parse(content)

            if parsed.bozo and not parsed.entries:
                result.error = f"Failed to parse feed: {parsed.bozo_exception}"
                return result

            # Process entries
            entries = []
            for entry_data in parsed.entries[: feed.max_entries]:
                entry = self._parse_entry(entry_data, feed)
                if entry and self._is_new_entry(entry.id):
                    entries.append(entry)

            result.entries = entries
            result.new_count = len(entries)

        except httpx.HTTPStatusError as e:
            result.error = f"HTTP error: {e.response.status_code}"
            self.logger.error("HTTP error fetching %s: %s", feed.url, e)
        except httpx.RequestError as e:
            result.error = f"Request error: {str(e)}"
            self.logger.error("Request error fetching %s: %s", feed.url, e)
        except Exception as e:
            result.error = f"Error: {str(e)}"
            self.logger.error("Error fetching feed %s: %s", feed.name, e, exc_info=True)

        return result

    async def check_feed(self, feed: RSSFeed) -> FeedCheckResult:
        """Check feed for new entries and process them.

        Args:
            feed: Feed to check

        Returns:
            FeedCheckResult
        """
        result = await self.fetch_feed(feed)

        if result.error:
            self.logger.warning("Feed check failed for %s: %s", feed.name, result.error)
            return result

        if not result.entries:
            self.logger.debug("No new entries for feed: %s", feed.name)
            return result

        # Process entries with AI if enabled
        ai_enabled = self.get_config_value("ai_enabled", False)
        if ai_enabled and self._ai_agent:
            for i, entry in enumerate(result.entries):
                try:
                    result.entries[i] = await self._process_with_ai(entry)
                except Exception as e:
                    self.logger.error("AI processing failed for entry: %s", e)

        # Add to aggregation buffer or send immediately
        if self.get_config_value("aggregation_enabled", True):
            for entry in result.entries:
                self._add_to_aggregation_buffer(entry, feed.webhook_target)
                self._store_entry(entry.id)
        else:
            for entry in result.entries:
                await self._send_single_entry(entry, feed.webhook_target)
                self._store_entry(entry.id)

        self.logger.info(
            "Feed %s: %d new entries processed", feed.name, result.new_count
        )

        return result

    def _check_all_feeds_sync(self) -> None:
        """Sync wrapper for feed check (for scheduler)."""
        try:
            asyncio.run(self._check_all_feeds())
        except Exception as e:
            self.logger.error("Error in feed check: %s", e, exc_info=True)

    async def _check_all_feeds(self) -> None:
        """Check all enabled feeds."""
        self.logger.debug("Checking all RSS feeds")

        for feed in self._feeds.values():
            if not feed.enabled:
                continue

            try:
                await self.check_feed(feed)
            except Exception as e:
                self.logger.error(
                    "Error checking feed %s: %s", feed.name, e, exc_info=True
                )

        # Check if aggregation should be flushed
        if self._should_flush_aggregation():
            await self._flush_all_aggregations()

    async def add_feed(
        self, name: str, url: str, **options: Any
    ) -> tuple[bool, str]:
        """Add a new RSS feed subscription.

        Args:
            name: Feed name
            url: Feed URL
            **options: Additional feed options

        Returns:
            Tuple of (success, message)
        """
        if name in self._feeds:
            return False, f"Feed '{name}' already exists"

        # Validate URL by fetching
        try:
            if not self._http_client:
                self._http_client = httpx.AsyncClient(timeout=30.0)
            response = await self._http_client.get(url)
            response.raise_for_status()
            parsed = feedparser.parse(response.text)
            if parsed.bozo and not parsed.entries:
                return False, f"Invalid RSS feed: {parsed.bozo_exception}"
        except Exception as e:
            return False, f"Failed to fetch feed: {e}"

        feed = RSSFeed(
            name=name,
            url=url,
            check_interval_minutes=options.get(
                "check_interval_minutes",
                self.get_config_value("default_check_interval_minutes", 30),
            ),
            enabled=options.get("enabled", True),
            max_entries=options.get("max_entries", 10),
            tags=options.get("tags", []),
            webhook_target=options.get("webhook_target", "default"),
        )

        self._feeds[name] = feed
        return True, f"Feed '{name}' added successfully"

    async def remove_feed(self, name_or_url: str) -> tuple[bool, str]:
        """Remove an RSS feed subscription.

        Args:
            name_or_url: Feed name or URL to remove

        Returns:
            Tuple of (success, message)
        """
        # Try to find by name first
        if name_or_url in self._feeds:
            del self._feeds[name_or_url]
            return True, f"Feed '{name_or_url}' removed"

        # Try to find by URL
        for name, feed in list(self._feeds.items()):
            if feed.url == name_or_url:
                del self._feeds[name]
                return True, f"Feed '{name}' removed"

        return False, f"Feed '{name_or_url}' not found"

    def list_feeds(self) -> list[RSSFeed]:
        """Get list of all configured feeds."""
        return list(self._feeds.values())

    # =========================================================================
    # Entry Processing
    # =========================================================================

    def _parse_entry(self, entry_data: dict, feed: RSSFeed) -> RSSEntry | None:
        """Parse feedparser entry to RSSEntry.

        Args:
            entry_data: feedparser entry dict
            feed: Parent feed

        Returns:
            RSSEntry or None if invalid
        """
        try:
            # Generate entry ID
            entry_id = self._generate_entry_id(entry_data, feed.url)

            # Get published date
            published = None
            if hasattr(entry_data, "published_parsed") and entry_data.published_parsed:
                try:
                    published = datetime(*entry_data.published_parsed[:6], tzinfo=UTC)
                except Exception:
                    pass
            elif hasattr(entry_data, "updated_parsed") and entry_data.updated_parsed:
                try:
                    published = datetime(*entry_data.updated_parsed[:6], tzinfo=UTC)
                except Exception:
                    pass

            # Get description/content
            description = ""
            if hasattr(entry_data, "summary"):
                description = entry_data.summary
            elif hasattr(entry_data, "description"):
                description = entry_data.description
            elif hasattr(entry_data, "content") and entry_data.content:
                description = entry_data.content[0].get("value", "")

            # Convert HTML to text if available
            if description and HTML2TEXT_AVAILABLE:
                h = html2text.HTML2Text()
                h.ignore_links = True
                h.ignore_images = True
                description = h.handle(description).strip()
            elif description:
                # Simple HTML stripping
                import re

                description = re.sub(r"<[^>]+>", "", description).strip()

            return RSSEntry(
                id=entry_id,
                title=entry_data.get("title", "Untitled"),
                link=entry_data.get("link", ""),
                description=description[:1000],  # Limit length
                published=published,
                author=entry_data.get("author", ""),
                feed_name=feed.name,
                feed_url=feed.url,
            )
        except Exception as e:
            self.logger.error("Error parsing entry: %s", e)
            return None

    def _generate_entry_id(self, entry_data: dict, feed_url: str) -> str:
        """Generate unique ID for deduplication.

        Args:
            entry_data: feedparser entry dict
            feed_url: Feed URL for context

        Returns:
            Unique entry ID
        """
        # Try to use guid/id first
        if hasattr(entry_data, "id") and entry_data.id:
            return hashlib.md5(entry_data.id.encode()).hexdigest()

        # Fall back to link
        if hasattr(entry_data, "link") and entry_data.link:
            return hashlib.md5(entry_data.link.encode()).hexdigest()

        # Fall back to title + feed url
        title = entry_data.get("title", "")
        key = f"{feed_url}:{title}"
        return hashlib.md5(key.encode()).hexdigest()

    def _is_new_entry(self, entry_id: str) -> bool:
        """Check if entry has been seen before.

        Args:
            entry_id: Entry ID to check

        Returns:
            True if new, False if seen
        """
        return entry_id not in self._seen_entries

    def _store_entry(self, entry_id: str) -> None:
        """Store entry ID for deduplication.

        Args:
            entry_id: Entry ID to store
        """
        self._seen_entries[entry_id] = datetime.now(UTC)

    def _cleanup_old_entries(self) -> None:
        """Remove entries older than history_days."""
        history_days = self.get_config_value("history_days", 7)
        cutoff = datetime.now(UTC) - timedelta(days=history_days)

        old_keys = [
            key for key, timestamp in self._seen_entries.items() if timestamp < cutoff
        ]

        for key in old_keys:
            del self._seen_entries[key]

        if old_keys:
            self.logger.debug("Cleaned up %d old entries", len(old_keys))

    # =========================================================================
    # AI Processing
    # =========================================================================

    async def _process_with_ai(self, entry: RSSEntry) -> RSSEntry:
        """Apply AI enhancements to entry.

        Args:
            entry: Entry to process

        Returns:
            Processed entry
        """
        if not self._ai_agent:
            return entry

        content = entry.description or entry.title

        # Generate summary
        if self.get_config_value("ai_summarization", True):
            try:
                entry.summary = await self._generate_summary(entry.title, content)
            except Exception as e:
                self.logger.error("Summary generation failed: %s", e)

        # Classify content
        if self.get_config_value("ai_classification", True):
            try:
                entry.categories = await self._classify_content(entry.title, content)
            except Exception as e:
                self.logger.error("Classification failed: %s", e)

        # Extract keywords
        if self.get_config_value("ai_keyword_extraction", False):
            try:
                entry.keywords = await self._extract_keywords(entry.title, content)
            except Exception as e:
                self.logger.error("Keyword extraction failed: %s", e)

        return entry

    async def _generate_summary(self, title: str, content: str) -> str:
        """Generate AI summary of content.

        Args:
            title: Article title
            content: Article content

        Returns:
            Summary text
        """
        if not self._ai_agent:
            return ""

        max_length = self.get_config_value("ai_max_summary_length", 150)
        prompt = SUMMARY_PROMPT.format(
            max_length=max_length,
            title=title,
            content=content[:2000],  # Limit input
        )

        try:
            result = await self._ai_agent.chat(prompt, user_id="rss-plugin")
            return result.strip()
        except Exception as e:
            self.logger.error("AI summary error: %s", e)
            return ""

    async def _classify_content(self, title: str, content: str) -> list[str]:
        """Classify content into categories.

        Args:
            title: Article title
            content: Article content

        Returns:
            List of category names
        """
        if not self._ai_agent:
            return []

        prompt = CLASSIFICATION_PROMPT.format(
            title=title,
            content=content[:2000],
        )

        try:
            result = await self._ai_agent.chat(prompt, user_id="rss-plugin")
            categories = [c.strip() for c in result.split(",")]
            return [c for c in categories if c][:3]
        except Exception as e:
            self.logger.error("AI classification error: %s", e)
            return []

    async def _extract_keywords(self, title: str, content: str) -> list[str]:
        """Extract key terms from content.

        Args:
            title: Article title
            content: Article content

        Returns:
            List of keywords
        """
        if not self._ai_agent:
            return []

        prompt = KEYWORD_PROMPT.format(
            title=title,
            content=content[:2000],
        )

        try:
            result = await self._ai_agent.chat(prompt, user_id="rss-plugin")
            keywords = [k.strip() for k in result.split(",")]
            return [k for k in keywords if k][:5]
        except Exception as e:
            self.logger.error("AI keyword extraction error: %s", e)
            return []

    # =========================================================================
    # Aggregation
    # =========================================================================

    def _add_to_aggregation_buffer(
        self, entry: RSSEntry, webhook_target: str = "default"
    ) -> None:
        """Add entry to aggregation buffer.

        Args:
            entry: Entry to add
            webhook_target: Target webhook name
        """
        if webhook_target not in self._aggregation_buffer:
            self._aggregation_buffer[webhook_target] = []

        self._aggregation_buffer[webhook_target].append(entry)

        # Check if should flush immediately (max entries reached)
        max_entries = self.get_config_value("aggregation_max_entries", 5)
        if len(self._aggregation_buffer[webhook_target]) >= max_entries:
            asyncio.create_task(self._flush_aggregation(webhook_target))

    def _should_flush_aggregation(self) -> bool:
        """Check if aggregation buffer should be flushed.

        Returns:
            True if should flush
        """
        if not self._aggregation_buffer:
            return False

        window_minutes = self.get_config_value("aggregation_window_minutes", 5)
        elapsed = datetime.now(UTC) - self._last_flush_time
        return elapsed.total_seconds() > window_minutes * 60

    def _flush_pending_sync(self) -> None:
        """Sync wrapper for aggregation flush (for scheduler)."""
        try:
            asyncio.run(self._flush_all_aggregations())
        except Exception as e:
            self.logger.error("Error in aggregation flush: %s", e, exc_info=True)

    async def _flush_all_aggregations(self) -> None:
        """Flush all aggregation buffers."""
        for target in list(self._aggregation_buffer.keys()):
            await self._flush_aggregation(target)
        self._last_flush_time = datetime.now(UTC)

    async def _flush_aggregation(self, webhook_target: str) -> None:
        """Send aggregated entries as single card.

        Args:
            webhook_target: Target webhook name
        """
        entries = self._aggregation_buffer.pop(webhook_target, [])
        if not entries:
            return

        # Build and send aggregated card
        card = self.build_aggregated_card(entries)
        await self._send_card(card, webhook_target)

        self.logger.info(
            "Sent aggregated card with %d entries to %s",
            len(entries),
            webhook_target,
        )

    # =========================================================================
    # Card Building
    # =========================================================================

    def build_single_entry_card(self, entry: RSSEntry) -> dict[str, Any]:
        """Build card for single RSS entry.

        Args:
            entry: Entry to display

        Returns:
            Card dict
        """
        template = self.get_config_value("card_template", "detailed")

        builder = CardBuilder()
        builder.set_header(
            f"RSS 更新 - {entry.feed_name}",
            template="blue",
        )

        # Title with link
        builder.add_markdown(f"**[{entry.title}]({entry.link})**")

        if entry.published:
            builder.add_markdown(f"发布时间: {entry.get_display_time()}")

        builder.add_divider()

        # Content based on template
        if template == "minimal":
            pass  # Title only
        elif template == "compact":
            if entry.summary:
                builder.add_markdown(entry.summary[:200])
        elif template in ("detailed", "full"):
            if entry.summary:
                builder.add_markdown(f"**摘要**: {entry.summary}")
            elif entry.description:
                builder.add_markdown(entry.description[:300] + "...")

            if entry.categories:
                builder.add_markdown(f"**分类**: {', '.join(entry.categories)}")

            if template == "full" and entry.keywords:
                builder.add_markdown(f"**关键词**: {', '.join(entry.keywords)}")

        builder.add_divider()
        builder.add_button("阅读原文", url=entry.link, button_type="primary")
        builder.add_markdown(f"来源: {entry.feed_name} | via rss-subscription")

        return builder.build()

    def build_aggregated_card(
        self, entries: list[RSSEntry], title: str = "RSS 更新"
    ) -> dict[str, Any]:
        """Build card for multiple entries.

        Args:
            entries: List of entries
            title: Card title

        Returns:
            Card dict
        """
        if not entries:
            return {}

        # Group entries by feed
        feeds: dict[str, list[RSSEntry]] = {}
        for entry in entries:
            if entry.feed_name not in feeds:
                feeds[entry.feed_name] = []
            feeds[entry.feed_name].append(entry)

        builder = CardBuilder()
        builder.set_header(
            f"{title} - {len(entries)} 条新内容",
            template="green",
            subtitle=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        # Summary line
        feed_count = len(feeds)
        builder.add_markdown(
            f"**{len(entries)}** 条更新来自 **{feed_count}** 个订阅源"
        )

        builder.add_divider()

        # Entries grouped by feed
        for feed_name, feed_entries in feeds.items():
            builder.add_markdown(f"**{feed_name}** - {len(feed_entries)} 条")

            for entry in feed_entries[:5]:  # Limit per feed
                time_str = entry.get_display_time()
                line = f"• [{entry.title}]({entry.link})"
                if time_str:
                    line += f" ({time_str})"
                builder.add_markdown(line)

                # Add categories/summary if available
                meta_parts = []
                if entry.categories:
                    meta_parts.append(", ".join(entry.categories[:2]))
                if entry.summary:
                    meta_parts.append(entry.summary[:100])
                if meta_parts:
                    builder.add_markdown(f"  _{' | '.join(meta_parts)}_")

            builder.add_divider()

        # Footer
        builder.add_markdown("via rss-subscription")

        return builder.build()

    def build_feed_list_card(self, feeds: list[RSSFeed]) -> dict[str, Any]:
        """Build card showing all subscribed feeds.

        Args:
            feeds: List of feeds

        Returns:
            Card dict
        """
        builder = CardBuilder()
        builder.set_header("RSS 订阅列表", template="blue")

        if not feeds:
            builder.add_markdown("暂无订阅源")
        else:
            builder.add_markdown(f"共 **{len(feeds)}** 个订阅源")
            builder.add_divider()

            for feed in feeds:
                status = "启用" if feed.enabled else "禁用"
                builder.add_markdown(
                    f"**{feed.name}** ({status})\n"
                    f"URL: {feed.url}\n"
                    f"检查间隔: {feed.check_interval_minutes} 分钟"
                )
                builder.add_divider()

        return builder.build()

    # =========================================================================
    # Message Sending
    # =========================================================================

    async def _send_card(
        self, card: dict[str, Any], webhook_target: str = "default"
    ) -> bool:
        """Send card to webhook.

        Args:
            card: Card dict
            webhook_target: Target webhook name

        Returns:
            True if sent successfully
        """
        if not self.client:
            self.logger.error("No client available for sending")
            return False

        try:
            self.client.send_card(card)
            return True
        except Exception as e:
            self.logger.error("Error sending card: %s", e, exc_info=True)
            return False

    async def _send_single_entry(
        self, entry: RSSEntry, webhook_target: str = "default"
    ) -> bool:
        """Send single entry card.

        Args:
            entry: Entry to send
            webhook_target: Target webhook

        Returns:
            True if sent successfully
        """
        card = self.build_single_entry_card(entry)
        return await self._send_card(card, webhook_target)

    # =========================================================================
    # Command Handlers
    # =========================================================================

    def _register_commands(self) -> None:
        """Register plugin commands with command handler."""
        # Commands will be registered via the chat controller
        # This is a placeholder for future integration
        pass

    async def handle_rss_command(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
        """Handle /rss commands.

        Args:
            message: Incoming message
            args: Command arguments

        Returns:
            CommandResult
        """
        from ..ai.commands import CommandResult

        if not args:
            return await self._cmd_help(message, [])

        subcommand = args[0].lower()
        sub_args = args[1:]

        handlers = {
            "add": self._cmd_add,
            "remove": self._cmd_remove,
            "list": self._cmd_list,
            "check": self._cmd_check,
            "status": self._cmd_status,
            "help": self._cmd_help,
        }

        handler = handlers.get(subcommand)
        if handler:
            return await handler(message, sub_args)

        return CommandResult(
            success=False,
            response=f"未知子命令: {subcommand}\n使用 /rss help 查看帮助",
        )

    async def _cmd_add(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
        """Handle /rss add <url> [name]."""
        from ..ai.commands import CommandResult

        if not args:
            return CommandResult(
                success=False,
                response="用法: /rss add <url> [name]",
            )

        url = args[0]
        name = args[1] if len(args) > 1 else url.split("/")[2]

        success, msg = await self.add_feed(name, url)
        return CommandResult(success=success, response=msg)

    async def _cmd_remove(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
        """Handle /rss remove <name|url>."""
        from ..ai.commands import CommandResult

        if not args:
            return CommandResult(
                success=False,
                response="用法: /rss remove <name|url>",
            )

        success, msg = await self.remove_feed(args[0])
        return CommandResult(success=success, response=msg)

    async def _cmd_list(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
        """Handle /rss list."""
        from ..ai.commands import CommandResult

        feeds = self.list_feeds()
        if not feeds:
            return CommandResult(
                success=True,
                response="暂无订阅源\n使用 /rss add <url> 添加订阅",
            )

        lines = [f"**RSS 订阅列表** ({len(feeds)} 个)\n"]
        for feed in feeds:
            status = "" if feed.enabled else " (禁用)"
            lines.append(f"• **{feed.name}**{status}")
            lines.append(f"  {feed.url}")
            lines.append(f"  间隔: {feed.check_interval_minutes}分钟")

        return CommandResult(success=True, response="\n".join(lines))

    async def _cmd_check(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
        """Handle /rss check [name]."""
        from ..ai.commands import CommandResult

        if args:
            # Check specific feed
            name = args[0]
            if name not in self._feeds:
                return CommandResult(
                    success=False,
                    response=f"订阅源 '{name}' 不存在",
                )
            feed = self._feeds[name]
            result = await self.check_feed(feed)
            if result.error:
                return CommandResult(
                    success=False,
                    response=f"检查失败: {result.error}",
                )
            return CommandResult(
                success=True,
                response=f"检查完成: {result.new_count} 条新内容",
            )
        else:
            # Check all feeds
            await self._check_all_feeds()
            return CommandResult(
                success=True,
                response="已触发所有订阅源检查",
            )

    async def _cmd_status(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
        """Handle /rss status."""
        from ..ai.commands import CommandResult

        lines = ["**RSS 插件状态**\n"]
        lines.append(f"订阅源数量: {len(self._feeds)}")
        lines.append(f"历史记录: {len(self._seen_entries)} 条")

        buffer_count = sum(len(v) for v in self._aggregation_buffer.values())
        lines.append(f"待发送聚合: {buffer_count} 条")

        ai_status = "启用" if self.get_config_value("ai_enabled", False) else "禁用"
        lines.append(f"AI 处理: {ai_status}")

        return CommandResult(success=True, response="\n".join(lines))

    async def _cmd_help(
        self, message: IncomingMessage, args: list[str]
    ) -> CommandResult:
        """Handle /rss help."""
        from ..ai.commands import CommandResult

        help_text = """**RSS 订阅命令**

`/rss add <url> [name]` - 添加订阅源
`/rss remove <name|url>` - 移除订阅源
`/rss list` - 列出所有订阅
`/rss check [name]` - 立即检查更新
`/rss status` - 查看插件状态
`/rss help` - 显示帮助"""

        return CommandResult(success=True, response=help_text)

    # =========================================================================
    # Persistence
    # =========================================================================

    def _load_history(self) -> None:
        """Load entry history from file."""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, encoding="utf-8") as f:
                data = json.load(f)

            for entry_id, timestamp_str in data.get("seen_entries", {}).items():
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    self._seen_entries[entry_id] = timestamp
                except Exception:
                    pass

            self._cleanup_old_entries()
            self.logger.debug("Loaded %d history entries", len(self._seen_entries))

        except Exception as e:
            self.logger.error("Error loading history: %s", e)

    def _save_history(self) -> None:
        """Save entry history to file."""
        if not self._storage_path:
            return

        try:
            data = {
                "seen_entries": {
                    entry_id: timestamp.isoformat()
                    for entry_id, timestamp in self._seen_entries.items()
                }
            }

            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.debug("Saved %d history entries", len(self._seen_entries))

        except Exception as e:
            self.logger.error("Error saving history: %s", e)

    # =========================================================================
    # External Integration
    # =========================================================================

    def set_ai_agent(self, agent: AIAgent) -> None:
        """Set AI agent reference.

        Args:
            agent: AIAgent instance
        """
        self._ai_agent = agent

    def set_command_handler(self, handler: CommandHandler) -> None:
        """Set command handler reference.

        Args:
            handler: CommandHandler instance
        """
        self._command_handler = handler
