"""Tests for RSS subscription plugin."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("feedparser")

from feishu_webhook_bot.core.config import BotConfig
from feishu_webhook_bot.plugins.rss_subscription import (
    RSSConfigSchema,
    RSSEntry,
    RSSFeed,
    RSSSubscriptionPlugin,
)

# Use anyio for async tests
pytestmark = pytest.mark.anyio


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_feed() -> RSSFeed:
    """Create sample RSS feed."""
    return RSSFeed(
        name="Test Feed",
        url="https://example.com/rss",
        check_interval_minutes=30,
        enabled=True,
        max_entries=10,
        tags=["test"],
    )


@pytest.fixture
def sample_entry() -> RSSEntry:
    """Create sample RSS entry."""
    return RSSEntry(
        id="test-entry-123",
        title="Test Article Title",
        link="https://example.com/article/1",
        description="This is a test article description with some content.",
        published=datetime.now(UTC),
        author="Test Author",
        feed_name="Test Feed",
        feed_url="https://example.com/rss",
    )


@pytest.fixture
def mock_config() -> BotConfig:
    """Create mock bot config."""
    config = MagicMock(spec=BotConfig)
    config.plugins = MagicMock()
    config.plugins.get_plugin_settings = MagicMock(
        return_value={
            "feeds": [
                {
                    "name": "Test Feed",
                    "url": "https://example.com/rss",
                    "check_interval_minutes": 30,
                }
            ],
            "default_check_interval_minutes": 30,
            "ai_enabled": False,
            "aggregation_enabled": True,
            "aggregation_max_entries": 5,
            "aggregation_window_minutes": 5,
            "card_template": "detailed",
            "history_days": 7,
        }
    )
    return config


@pytest.fixture
def plugin(mock_config: BotConfig) -> RSSSubscriptionPlugin:
    """Create RSS subscription plugin instance."""
    plugin = RSSSubscriptionPlugin(config=mock_config)
    return plugin


# =============================================================================
# RSSFeed Tests
# =============================================================================


class TestRSSFeed:
    """Tests for RSSFeed dataclass."""

    def test_from_dict(self) -> None:
        """Test creating RSSFeed from dictionary."""
        data = {
            "name": "My Feed",
            "url": "https://example.com/feed.xml",
            "check_interval_minutes": 60,
            "enabled": True,
            "max_entries": 5,
            "tags": ["news", "tech"],
        }
        feed = RSSFeed.from_dict(data)

        assert feed.name == "My Feed"
        assert feed.url == "https://example.com/feed.xml"
        assert feed.check_interval_minutes == 60
        assert feed.enabled is True
        assert feed.max_entries == 5
        assert feed.tags == ["news", "tech"]

    def test_from_dict_defaults(self) -> None:
        """Test RSSFeed defaults from minimal dictionary."""
        data = {
            "name": "Minimal",
            "url": "https://example.com/rss",
        }
        feed = RSSFeed.from_dict(data)

        assert feed.name == "Minimal"
        assert feed.url == "https://example.com/rss"
        assert feed.check_interval_minutes == 30
        assert feed.enabled is True
        assert feed.max_entries == 10
        assert feed.tags == []

    def test_to_dict(self, sample_feed: RSSFeed) -> None:
        """Test converting RSSFeed to dictionary."""
        data = sample_feed.to_dict()

        assert data["name"] == "Test Feed"
        assert data["url"] == "https://example.com/rss"
        assert data["check_interval_minutes"] == 30
        assert data["enabled"] is True


# =============================================================================
# RSSEntry Tests
# =============================================================================


class TestRSSEntry:
    """Tests for RSSEntry dataclass."""

    def test_get_display_time(self, sample_entry: RSSEntry) -> None:
        """Test display time formatting."""
        time_str = sample_entry.get_display_time()
        assert time_str  # Should not be empty
        assert "-" in time_str  # Format: MM-DD HH:MM

    def test_get_display_time_no_published(self) -> None:
        """Test display time when no published date."""
        entry = RSSEntry(
            id="test",
            title="Test",
            link="https://example.com",
            published=None,
        )
        assert entry.get_display_time() == ""


# =============================================================================
# RSSConfigSchema Tests
# =============================================================================


class TestRSSConfigSchema:
    """Tests for RSSConfigSchema."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        schema = RSSConfigSchema()

        assert schema.feeds == []
        assert schema.default_check_interval_minutes == 30
        assert schema.ai_enabled is False
        assert schema.aggregation_enabled is True
        assert schema.aggregation_max_entries == 5
        assert schema.card_template == "detailed"
        assert schema.history_days == 7

    def test_validation(self) -> None:
        """Test configuration validation."""
        # Valid config
        config = {
            "feeds": [],
            "default_check_interval_minutes": 60,
            "ai_enabled": True,
        }
        is_valid, errors = RSSConfigSchema.validate_config(config)
        assert is_valid
        assert errors == []

    def test_field_groups(self) -> None:
        """Test field groups are defined."""
        groups = RSSConfigSchema.get_field_groups()
        assert "Feed Management" in groups
        assert "AI Processing" in groups
        assert "Aggregation" in groups


# =============================================================================
# Plugin Lifecycle Tests
# =============================================================================


class TestPluginLifecycle:
    """Tests for plugin lifecycle methods."""

    def test_metadata(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test plugin metadata."""
        meta = plugin.metadata()

        assert meta.name == "rss-subscription"
        assert meta.version == "1.0.0"
        assert "RSS" in meta.description

    def test_on_load(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test plugin loading."""
        with patch.object(plugin, "_load_history"):
            plugin.on_load()

        assert len(plugin._feeds) >= 0

    def test_on_enable(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test plugin enabling."""
        plugin.register_job = MagicMock(return_value="job_id")

        plugin.on_enable()

        # Should register feed check job
        assert plugin.register_job.called

    def test_on_disable(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test plugin disabling."""
        plugin._save_history = MagicMock()
        plugin.cleanup_jobs = MagicMock()

        plugin.on_disable()

        plugin._save_history.assert_called_once()
        plugin.cleanup_jobs.assert_called_once()


# =============================================================================
# Feed Operations Tests
# =============================================================================


class TestFeedOperations:
    """Tests for feed operations."""

    def test_list_feeds(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test listing feeds."""
        plugin._feeds = {
            "feed1": RSSFeed(name="Feed 1", url="https://example.com/1"),
            "feed2": RSSFeed(name="Feed 2", url="https://example.com/2"),
        }

        feeds = plugin.list_feeds()

        assert len(feeds) == 2

    async def test_add_feed_success(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test adding a valid feed."""
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.text = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <item>
                    <title>Test Item</title>
                    <link>https://example.com/item</link>
                </item>
            </channel>
        </rss>"""
        mock_response.raise_for_status = MagicMock()

        plugin._http_client = AsyncMock()
        plugin._http_client.get = AsyncMock(return_value=mock_response)

        success, msg = await plugin.add_feed("New Feed", "https://example.com/rss")

        assert success is True
        assert "New Feed" in plugin._feeds

    async def test_add_feed_duplicate(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test adding duplicate feed."""
        plugin._feeds["Existing"] = RSSFeed(name="Existing", url="https://example.com")

        success, msg = await plugin.add_feed("Existing", "https://other.com")

        assert success is False
        assert "already exists" in msg

    async def test_remove_feed_by_name(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test removing feed by name."""
        plugin._feeds["Test"] = RSSFeed(name="Test", url="https://example.com")

        success, msg = await plugin.remove_feed("Test")

        assert success is True
        assert "Test" not in plugin._feeds

    async def test_remove_feed_not_found(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test removing non-existent feed."""
        success, msg = await plugin.remove_feed("NonExistent")

        assert success is False
        assert "not found" in msg


# =============================================================================
# Entry Processing Tests
# =============================================================================


class TestEntryProcessing:
    """Tests for entry processing."""

    def test_generate_entry_id_with_guid(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test entry ID generation with GUID."""
        entry_data = MagicMock()
        entry_data.id = "unique-guid-123"

        entry_id = plugin._generate_entry_id(entry_data, "https://example.com")

        assert entry_id  # Should not be empty
        assert len(entry_id) == 32  # MD5 hash length

    def test_generate_entry_id_with_link(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test entry ID generation with link."""
        entry_data = MagicMock()
        entry_data.id = None
        entry_data.link = "https://example.com/article/1"

        entry_id = plugin._generate_entry_id(entry_data, "https://example.com")

        assert entry_id
        assert len(entry_id) == 32

    def test_is_new_entry(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test new entry detection."""
        assert plugin._is_new_entry("new-id") is True

        plugin._seen_entries["seen-id"] = datetime.now(UTC)
        assert plugin._is_new_entry("seen-id") is False

    def test_store_entry(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test entry storage."""
        plugin._store_entry("test-id")

        assert "test-id" in plugin._seen_entries
        assert isinstance(plugin._seen_entries["test-id"], datetime)

    def test_cleanup_old_entries(
        self, plugin: RSSSubscriptionPlugin, mock_config: BotConfig
    ) -> None:
        """Test old entry cleanup."""
        from datetime import timedelta

        # Add old and new entries
        old_time = datetime.now(UTC) - timedelta(days=10)
        new_time = datetime.now(UTC)

        plugin._seen_entries = {
            "old-entry": old_time,
            "new-entry": new_time,
        }

        plugin._cleanup_old_entries()

        assert "old-entry" not in plugin._seen_entries
        assert "new-entry" in plugin._seen_entries


# =============================================================================
# Aggregation Tests
# =============================================================================


class TestAggregation:
    """Tests for aggregation functionality."""

    def test_add_to_aggregation_buffer(
        self, plugin: RSSSubscriptionPlugin, sample_entry: RSSEntry
    ) -> None:
        """Test adding entry to aggregation buffer."""
        plugin._add_to_aggregation_buffer(sample_entry, "default")

        assert "default" in plugin._aggregation_buffer
        assert len(plugin._aggregation_buffer["default"]) == 1
        assert plugin._aggregation_buffer["default"][0] == sample_entry

    def test_should_flush_aggregation_empty(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test flush check with empty buffer."""
        assert plugin._should_flush_aggregation() is False

    def test_should_flush_aggregation_time_based(
        self, plugin: RSSSubscriptionPlugin, sample_entry: RSSEntry
    ) -> None:
        """Test time-based flush trigger."""
        from datetime import timedelta

        plugin._aggregation_buffer["default"] = [sample_entry]
        plugin._last_flush_time = datetime.now(UTC) - timedelta(minutes=10)

        assert plugin._should_flush_aggregation() is True


# =============================================================================
# Card Building Tests
# =============================================================================


class TestCardBuilding:
    """Tests for card building."""

    def test_build_single_entry_card(
        self, plugin: RSSSubscriptionPlugin, sample_entry: RSSEntry
    ) -> None:
        """Test building single entry card."""
        card = plugin.build_single_entry_card(sample_entry)

        assert "header" in card
        assert "elements" in card

    def test_build_aggregated_card(
        self, plugin: RSSSubscriptionPlugin, sample_entry: RSSEntry
    ) -> None:
        """Test building aggregated card."""
        entries = [sample_entry, sample_entry]
        card = plugin.build_aggregated_card(entries)

        assert "header" in card
        assert "elements" in card

    def test_build_aggregated_card_empty(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test building aggregated card with no entries."""
        card = plugin.build_aggregated_card([])

        assert card == {}

    def test_build_feed_list_card(
        self, plugin: RSSSubscriptionPlugin, sample_feed: RSSFeed
    ) -> None:
        """Test building feed list card."""
        card = plugin.build_feed_list_card([sample_feed])

        assert "header" in card
        assert "elements" in card


# =============================================================================
# Command Handler Tests
# =============================================================================


class TestCommandHandlers:
    """Tests for command handlers."""

    async def test_cmd_list_empty(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test list command with no feeds."""
        message = MagicMock()
        result = await plugin._cmd_list(message, [])

        assert result.success is True
        assert "暂无" in result.response

    async def test_cmd_list_with_feeds(
        self, plugin: RSSSubscriptionPlugin, sample_feed: RSSFeed
    ) -> None:
        """Test list command with feeds."""
        plugin._feeds["Test"] = sample_feed

        message = MagicMock()
        result = await plugin._cmd_list(message, [])

        assert result.success is True
        assert "Test Feed" in result.response

    async def test_cmd_status(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test status command."""
        message = MagicMock()
        result = await plugin._cmd_status(message, [])

        assert result.success is True
        assert "插件状态" in result.response

    async def test_cmd_help(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test help command."""
        message = MagicMock()
        result = await plugin._cmd_help(message, [])

        assert result.success is True
        assert "/rss add" in result.response
        assert "/rss remove" in result.response

    async def test_handle_rss_command_unknown(self, plugin: RSSSubscriptionPlugin) -> None:
        """Test handling unknown subcommand."""
        message = MagicMock()
        result = await plugin.handle_rss_command(message, ["unknown"])

        assert result.success is False
        assert "未知子命令" in result.response


# =============================================================================
# Persistence Tests
# =============================================================================


class TestPersistence:
    """Tests for persistence functionality."""

    def test_save_and_load_history(self, plugin: RSSSubscriptionPlugin, tmp_path) -> None:
        """Test saving and loading history."""
        plugin._storage_path = tmp_path / "history.json"

        # Add some entries
        plugin._seen_entries = {
            "entry1": datetime.now(UTC),
            "entry2": datetime.now(UTC),
        }

        # Save
        plugin._save_history()
        assert plugin._storage_path.exists()

        # Clear and load
        plugin._seen_entries.clear()
        plugin._load_history()

        assert "entry1" in plugin._seen_entries
        assert "entry2" in plugin._seen_entries


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests."""

    async def test_full_feed_check_flow(
        self, plugin: RSSSubscriptionPlugin, sample_feed: RSSFeed
    ) -> None:
        """Test full feed check flow."""
        # Mock HTTP response
        rss_content = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <item>
                    <guid>unique-item-1</guid>
                    <title>Test Article</title>
                    <link>https://example.com/article</link>
                    <description>Test description</description>
                </item>
            </channel>
        </rss>"""

        mock_response = MagicMock()
        mock_response.text = rss_content
        mock_response.raise_for_status = MagicMock()

        plugin._http_client = AsyncMock()
        plugin._http_client.get = AsyncMock(return_value=mock_response)

        # Mock client for sending
        plugin._client = MagicMock()
        plugin._client.send_card = MagicMock()

        # Run feed check
        result = await plugin.fetch_feed(sample_feed)

        assert result.error is None
        assert len(result.entries) > 0
        assert result.entries[0].title == "Test Article"
