"""Tests for plugins.manifest module."""

from __future__ import annotations

from unittest.mock import MagicMock

from feishu_webhook_bot.plugins.manifest import (
    PackageDependency,
    PermissionRequest,
    PermissionType,
    PluginDependency,
    PluginManifest,
)


class TestPermissionType:
    """Tests for PermissionType enum."""

    def test_permission_values(self) -> None:
        """Test permission type values."""
        assert PermissionType.NETWORK_ACCESS.value == "network"
        assert PermissionType.FILE_READ.value == "file_read"
        assert PermissionType.FILE_WRITE.value == "file_write"
        assert PermissionType.SCHEDULE_JOBS.value == "schedule"
        assert PermissionType.SEND_MESSAGES.value == "send_messages"
        assert PermissionType.ACCESS_CONFIG.value == "access_config"
        assert PermissionType.EXTERNAL_API.value == "external_api"
        assert PermissionType.DATABASE_ACCESS.value == "database"
        assert PermissionType.SYSTEM_INFO.value == "system_info"
        assert PermissionType.EXECUTE_CODE.value == "execute_code"


class TestPackageDependency:
    """Tests for PackageDependency dataclass."""

    def test_create_basic_dependency(self) -> None:
        """Test creating a basic package dependency."""
        dep = PackageDependency("httpx")

        assert dep.name == "httpx"
        assert dep.version is None
        assert dep.optional is False
        assert dep.feature is None
        assert dep.install_hint is None

    def test_create_dependency_with_version(self) -> None:
        """Test creating dependency with version."""
        dep = PackageDependency("httpx", ">=0.27.0")

        assert dep.name == "httpx"
        assert dep.version == ">=0.27.0"

    def test_create_optional_dependency(self) -> None:
        """Test creating optional dependency."""
        dep = PackageDependency("redis", ">=5.0.0", optional=True, feature="caching")

        assert dep.optional is True
        assert dep.feature == "caching"

    def test_get_pip_spec_with_version(self) -> None:
        """Test get_pip_spec with version."""
        dep = PackageDependency("httpx", ">=0.27.0")

        assert dep.get_pip_spec() == "httpx>=0.27.0"

    def test_get_pip_spec_without_version(self) -> None:
        """Test get_pip_spec without version."""
        dep = PackageDependency("httpx")

        assert dep.get_pip_spec() == "httpx"


class TestPluginDependency:
    """Tests for PluginDependency dataclass."""

    def test_create_basic_dependency(self) -> None:
        """Test creating a basic plugin dependency."""
        dep = PluginDependency("core-plugin")

        assert dep.plugin_name == "core-plugin"
        assert dep.min_version is None
        assert dep.optional is False

    def test_create_dependency_with_version(self) -> None:
        """Test creating dependency with min version."""
        dep = PluginDependency("core-plugin", min_version="1.0.0")

        assert dep.min_version == "1.0.0"

    def test_create_optional_dependency(self) -> None:
        """Test creating optional dependency."""
        dep = PluginDependency("optional-plugin", optional=True)

        assert dep.optional is True


class TestPermissionRequest:
    """Tests for PermissionRequest dataclass."""

    def test_create_basic_permission(self) -> None:
        """Test creating a basic permission request."""
        perm = PermissionRequest(
            permission=PermissionType.NETWORK_ACCESS,
            reason="Access external API",
        )

        assert perm.permission == PermissionType.NETWORK_ACCESS
        assert perm.reason == "Access external API"
        assert perm.scope is None

    def test_create_permission_with_scope(self) -> None:
        """Test creating permission with scope."""
        perm = PermissionRequest(
            permission=PermissionType.NETWORK_ACCESS,
            reason="Access Feishu API",
            scope="open.feishu.cn",
        )

        assert perm.scope == "open.feishu.cn"


class TestPluginManifest:
    """Tests for PluginManifest dataclass."""

    def test_create_basic_manifest(self) -> None:
        """Test creating a basic manifest."""
        manifest = PluginManifest(name="test-plugin")

        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == ""
        assert manifest.author == ""
        assert manifest.python_dependencies == []
        assert manifest.plugin_dependencies == []
        assert manifest.permissions == []
        assert manifest.supports_hot_reload is True
        assert manifest.supports_multi_provider is True

    def test_create_full_manifest(self) -> None:
        """Test creating a manifest with all fields."""
        manifest = PluginManifest(
            name="feishu-calendar",
            version="2.0.0",
            description="Calendar integration",
            author="Bot Team",
            homepage="https://github.com/example/plugin",
            license="MIT",
            python_dependencies=[
                PackageDependency("httpx", ">=0.27.0"),
            ],
            plugin_dependencies=[
                PluginDependency("core-plugin"),
            ],
            permissions=[
                PermissionRequest(PermissionType.NETWORK_ACCESS, "API calls"),
            ],
            tags=["calendar", "reminders"],
            min_bot_version="1.0.0",
        )

        assert manifest.name == "feishu-calendar"
        assert manifest.version == "2.0.0"
        assert len(manifest.python_dependencies) == 1
        assert len(manifest.plugin_dependencies) == 1
        assert len(manifest.permissions) == 1
        assert "calendar" in manifest.tags

    def test_get_required_python_packages(self) -> None:
        """Test getting required Python packages."""
        manifest = PluginManifest(
            name="test-plugin",
            python_dependencies=[
                PackageDependency("httpx", optional=False),
                PackageDependency("redis", optional=True),
                PackageDependency("pydantic", optional=False),
            ],
        )

        required = manifest.get_required_python_packages()

        assert len(required) == 2
        names = [d.name for d in required]
        assert "httpx" in names
        assert "pydantic" in names
        assert "redis" not in names

    def test_get_optional_python_packages(self) -> None:
        """Test getting optional Python packages."""
        manifest = PluginManifest(
            name="test-plugin",
            python_dependencies=[
                PackageDependency("httpx", optional=False),
                PackageDependency("redis", optional=True),
            ],
        )

        optional = manifest.get_optional_python_packages()

        assert len(optional) == 1
        assert optional[0].name == "redis"

    def test_get_required_plugins(self) -> None:
        """Test getting required plugins."""
        manifest = PluginManifest(
            name="test-plugin",
            plugin_dependencies=[
                PluginDependency("core-plugin", optional=False),
                PluginDependency("optional-plugin", optional=True),
            ],
        )

        required = manifest.get_required_plugins()

        assert len(required) == 1
        assert required[0].plugin_name == "core-plugin"

    def test_get_pip_install_command(self) -> None:
        """Test generating pip install command."""
        manifest = PluginManifest(
            name="test-plugin",
            python_dependencies=[
                PackageDependency("httpx", ">=0.27.0"),
                PackageDependency("pydantic", ">=2.0.0"),
                PackageDependency("redis", optional=True),
            ],
        )

        command = manifest.get_pip_install_command()

        assert command is not None
        assert "pip install" in command
        assert "httpx>=0.27.0" in command
        assert "pydantic>=2.0.0" in command
        assert "redis" not in command

    def test_get_pip_install_command_no_deps(self) -> None:
        """Test pip install command with no dependencies."""
        manifest = PluginManifest(name="test-plugin")

        command = manifest.get_pip_install_command()

        assert command is None

    def test_to_dict(self) -> None:
        """Test converting manifest to dictionary."""
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            python_dependencies=[
                PackageDependency("httpx", ">=0.27.0"),
            ],
            permissions=[
                PermissionRequest(PermissionType.NETWORK_ACCESS, "API calls"),
            ],
            tags=["test"],
        )

        data = manifest.to_dict()

        assert data["name"] == "test-plugin"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Test plugin"
        assert data["author"] == "Test Author"
        assert len(data["python_dependencies"]) == 1
        assert data["python_dependencies"][0]["name"] == "httpx"
        assert len(data["permissions"]) == 1
        assert data["permissions"][0]["permission"] == "network"
        assert "test" in data["tags"]

    def test_from_plugin_basic(self) -> None:
        """Test creating manifest from plugin instance."""
        mock_plugin = MagicMock()
        mock_metadata = MagicMock()
        mock_metadata.name = "test-plugin"
        mock_metadata.version = "1.0.0"
        mock_metadata.description = "Test description"
        mock_metadata.author = "Test Author"
        mock_plugin.metadata.return_value = mock_metadata
        mock_plugin.__class__ = type("MockPlugin", (), {})

        manifest = PluginManifest.from_plugin(mock_plugin)

        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == "Test description"
        assert manifest.author == "Test Author"

    def test_from_plugin_with_dependencies(self) -> None:
        """Test creating manifest from plugin with dependencies."""

        class PluginWithDeps:
            PYTHON_DEPENDENCIES = [
                PackageDependency("httpx", ">=0.27.0"),
            ]
            PLUGIN_DEPENDENCIES = [
                PluginDependency("core-plugin"),
            ]
            PERMISSIONS = [
                PermissionRequest(PermissionType.NETWORK_ACCESS, "API"),
            ]
            TAGS = ["test"]
            HOMEPAGE = "https://example.com"
            LICENSE = "MIT"

            def metadata(self) -> MagicMock:
                mock = MagicMock()
                mock.name = "test-plugin"
                mock.version = "1.0.0"
                mock.description = ""
                mock.author = ""
                return mock

        plugin = PluginWithDeps()
        manifest = PluginManifest.from_plugin(plugin)

        assert len(manifest.python_dependencies) == 1
        assert manifest.python_dependencies[0].name == "httpx"
        assert len(manifest.plugin_dependencies) == 1
        assert len(manifest.permissions) == 1
        assert "test" in manifest.tags
        assert manifest.homepage == "https://example.com"
        assert manifest.license == "MIT"

    def test_from_plugin_with_manifest_method(self) -> None:
        """Test creating manifest from plugin with manifest() method."""
        expected_manifest = PluginManifest(
            name="custom-plugin",
            version="2.0.0",
            description="Custom manifest",
        )

        class PluginWithManifestMethod:
            def metadata(self) -> MagicMock:
                mock = MagicMock()
                mock.name = "test-plugin"
                mock.version = "1.0.0"
                mock.description = ""
                mock.author = ""
                return mock

            def manifest(self) -> PluginManifest:
                return expected_manifest

        plugin = PluginWithManifestMethod()
        manifest = PluginManifest.from_plugin(plugin)

        assert manifest.name == "custom-plugin"
        assert manifest.version == "2.0.0"
