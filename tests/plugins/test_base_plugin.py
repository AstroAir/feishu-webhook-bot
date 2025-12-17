"""Tests for BasePlugin class and PluginMetadata."""

from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.core import BotConfig
from feishu_webhook_bot.core.config import PluginConfig, PluginSettingsConfig
from feishu_webhook_bot.plugins.base import BasePlugin, PluginMetadata


class ConcretePlugin(BasePlugin):
    """Concrete implementation of BasePlugin for testing."""

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
        )


class PluginWithPermissions(BasePlugin):
    """Plugin with permissions for testing."""

    PERMISSIONS = ["NETWORK_SEND", "FILE_READ"]
    PYTHON_DEPENDENCIES = ["httpx>=0.27.0"]
    PLUGIN_DEPENDENCIES = ["base-plugin"]

    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="permission-plugin",
            version="2.0.0",
            description="Plugin with permissions",
            author="Test",
        )


class TestPluginMetadata:
    """Tests for PluginMetadata dataclass."""

    def test_metadata_defaults(self):
        """Test default values for PluginMetadata."""
        meta = PluginMetadata(name="test")
        assert meta.name == "test"
        assert meta.version == "1.0.0"
        assert meta.description == ""
        assert meta.author == ""
        assert meta.enabled is True

    def test_metadata_full(self):
        """Test PluginMetadata with all fields."""
        meta = PluginMetadata(
            name="full-plugin",
            version="2.1.0",
            description="Full description",
            author="Author Name",
            enabled=False,
        )
        assert meta.name == "full-plugin"
        assert meta.version == "2.1.0"
        assert meta.description == "Full description"
        assert meta.author == "Author Name"
        assert meta.enabled is False


class TestBasePlugin:
    """Tests for BasePlugin class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock BotConfig."""
        return BotConfig(
            plugins=PluginConfig(
                enabled=True,
                plugin_dir="./plugins",
                plugin_settings=[
                    PluginSettingsConfig(
                        plugin_name="test-plugin",
                        enabled=True,
                        settings={
                            "api_key": "secret123",
                            "timeout": 30,
                            "features": ["a", "b"],
                        },
                    )
                ],
            )
        )

    @pytest.fixture
    def mock_client(self):
        """Create a mock client."""
        return MagicMock()

    @pytest.fixture
    def mock_providers(self):
        """Create mock providers."""
        return {
            "feishu": MagicMock(),
            "qq": MagicMock(),
        }

    @pytest.fixture
    def plugin(self, mock_config, mock_client, mock_providers):
        """Create a ConcretePlugin instance."""
        return ConcretePlugin(mock_config, mock_client, mock_providers)

    def test_plugin_initialization(self, plugin, mock_config, mock_client, mock_providers):
        """Test plugin initialization."""
        assert plugin.config == mock_config
        assert plugin.client == mock_client
        assert plugin.providers == mock_providers
        assert plugin._job_ids == []

    def test_plugin_metadata(self, plugin):
        """Test plugin metadata method."""
        meta = plugin.metadata()
        assert meta.name == "test-plugin"
        assert meta.version == "1.0.0"

    def test_client_property(self, plugin, mock_client):
        """Test client property getter and setter."""
        assert plugin.client == mock_client
        new_client = MagicMock()
        plugin.client = new_client
        assert plugin.client == new_client

    def test_providers_property(self, plugin, mock_providers):
        """Test providers property getter and setter."""
        assert plugin.providers == mock_providers
        new_providers = {"telegram": MagicMock()}
        plugin.providers = new_providers
        assert plugin.providers == new_providers

    def test_get_provider(self, plugin):
        """Test get_provider method."""
        feishu = plugin.get_provider("feishu")
        assert feishu is not None

        nonexistent = plugin.get_provider("nonexistent")
        assert nonexistent is None

    def test_lifecycle_methods(self, plugin):
        """Test lifecycle methods don't raise errors."""
        plugin.on_load()
        plugin.on_enable()
        plugin.on_disable()
        plugin.on_unload()

    def test_register_job(self, plugin):
        """Test register_job method."""
        job_id = plugin.register_job(lambda: None, trigger="interval", job_id="test-job")
        assert job_id == "test-job"
        assert "test-job" in plugin._job_ids

    def test_cleanup_jobs(self, plugin):
        """Test cleanup_jobs method."""
        plugin._job_ids = ["job1", "job2", "job3"]
        plugin.cleanup_jobs()
        assert plugin._job_ids == []

    def test_get_config_value(self, plugin):
        """Test get_config_value method."""
        api_key = plugin.get_config_value("api_key", "default")
        assert api_key == "secret123"

        timeout = plugin.get_config_value("timeout", 60)
        assert timeout == 30

        nonexistent = plugin.get_config_value("nonexistent", "default")
        assert nonexistent == "default"

    def test_get_all_config(self, plugin):
        """Test get_all_config method."""
        config = plugin.get_all_config()
        assert config["api_key"] == "secret123"
        assert config["timeout"] == 30
        assert config["features"] == ["a", "b"]

    def test_handle_event_default(self, plugin):
        """Test default handle_event implementation."""
        result = plugin.handle_event({"type": "message"}, {"user": "test"})
        assert result is None


class TestBasePluginPermissions:
    """Tests for BasePlugin permission-related methods."""

    @pytest.fixture
    def plugin_with_perms(self):
        """Create a plugin with permissions."""
        config = BotConfig(plugins=PluginConfig(enabled=True))
        return PluginWithPermissions(config, None, None)

    def test_get_required_permissions(self, plugin_with_perms):
        """Test get_required_permissions method."""
        perms = plugin_with_perms.get_required_permissions()
        assert len(perms) == 2
        perm_names = {p.name for p in perms}
        assert "NETWORK_SEND" in perm_names
        assert "FILE_READ" in perm_names

    def test_get_permission_set(self, plugin_with_perms):
        """Test get_permission_set method."""
        perm_set = plugin_with_perms.get_permission_set()
        assert perm_set is not None
        all_perms = perm_set.get_all_permissions()
        assert len(all_perms) == 2

    @patch("feishu_webhook_bot.plugins.permissions.get_permission_manager")
    def test_check_permission(self, mock_get_pm, plugin_with_perms):
        """Test check_permission method."""
        mock_pm = MagicMock()
        mock_pm.check_permission.return_value = True
        mock_get_pm.return_value = mock_pm

        from feishu_webhook_bot.plugins.permissions import PluginPermission

        result = plugin_with_perms.check_permission(PluginPermission.NETWORK_SEND)
        assert result is True
        mock_pm.check_permission.assert_called_once_with(
            "permission-plugin", PluginPermission.NETWORK_SEND
        )

    @patch("feishu_webhook_bot.plugins.permissions.get_permission_manager")
    def test_require_permission(self, mock_get_pm, plugin_with_perms):
        """Test require_permission method."""
        mock_pm = MagicMock()
        mock_get_pm.return_value = mock_pm

        from feishu_webhook_bot.plugins.permissions import PluginPermission

        plugin_with_perms.require_permission(PluginPermission.FILE_READ)
        mock_pm.require_permission.assert_called_once_with(
            "permission-plugin", PluginPermission.FILE_READ
        )


class TestBasePluginConfigSchema:
    """Tests for BasePlugin config schema methods."""

    @pytest.fixture
    def plugin_with_schema(self):
        """Create a plugin with config schema."""
        from pydantic import Field

        from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema

        class TestSchema(PluginConfigSchema):
            api_key: str = Field(..., description="API Key")
            timeout: int = Field(default=30, description="Timeout")

        class SchemaPlugin(BasePlugin):
            config_schema = TestSchema

            def metadata(self) -> PluginMetadata:
                return PluginMetadata(name="schema-plugin")

        config = BotConfig(
            plugins=PluginConfig(
                enabled=True,
                plugin_settings=[
                    PluginSettingsConfig(
                        plugin_name="schema-plugin",
                        settings={"api_key": "test123", "timeout": 60},
                    )
                ],
            )
        )
        return SchemaPlugin(config, None, None)

    def test_validate_config_valid(self, plugin_with_schema):
        """Test validate_config with valid config."""
        is_valid, errors = plugin_with_schema.validate_config()
        assert is_valid is True
        assert errors == []

    def test_get_missing_config(self, plugin_with_schema):
        """Test get_missing_config method."""
        missing = plugin_with_schema.get_missing_config()
        assert missing == []

    def test_get_manifest(self, plugin_with_schema):
        """Test get_manifest method."""
        manifest = plugin_with_schema.get_manifest()
        assert manifest.name == "schema-plugin"
        assert manifest.version == "1.0.0"


class TestBasePluginWithoutSchema:
    """Tests for BasePlugin without config schema."""

    @pytest.fixture
    def plugin_no_schema(self):
        """Create a plugin without config schema."""
        config = BotConfig(plugins=PluginConfig(enabled=True))
        return ConcretePlugin(config, None, None)

    def test_validate_config_no_schema(self, plugin_no_schema):
        """Test validate_config returns True when no schema."""
        is_valid, errors = plugin_no_schema.validate_config()
        assert is_valid is True
        assert errors == []

    def test_get_missing_config_no_schema(self, plugin_no_schema):
        """Test get_missing_config returns empty when no schema."""
        missing = plugin_no_schema.get_missing_config()
        assert missing == []
