"""Tests for plugins.dependency_checker module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from feishu_webhook_bot.plugins.dependency_checker import (
    DependencyCheckResult,
    DependencyChecker,
    DependencyStatus,
)
from feishu_webhook_bot.plugins.manifest import (
    PackageDependency,
    PluginDependency,
    PluginManifest,
)


class TestDependencyStatus:
    """Tests for DependencyStatus dataclass."""

    def test_create_satisfied_status(self) -> None:
        """Test creating a satisfied dependency status."""
        status = DependencyStatus(
            satisfied=True,
            name="httpx",
            required_version=">=0.27.0",
            installed_version="0.27.2",
        )

        assert status.satisfied is True
        assert status.name == "httpx"
        assert status.required_version == ">=0.27.0"
        assert status.installed_version == "0.27.2"
        assert status.error is None
        assert status.install_command is None

    def test_create_unsatisfied_status(self) -> None:
        """Test creating an unsatisfied dependency status."""
        status = DependencyStatus(
            satisfied=False,
            name="httpx",
            required_version=">=0.27.0",
            installed_version=None,
            error="Package 'httpx' is not installed",
            install_command="pip install 'httpx>=0.27.0'",
        )

        assert status.satisfied is False
        assert status.error is not None
        assert status.install_command is not None


class TestDependencyCheckResult:
    """Tests for DependencyCheckResult dataclass."""

    def test_create_all_satisfied_result(self) -> None:
        """Test creating result with all dependencies satisfied."""
        result = DependencyCheckResult(
            plugin_name="test-plugin",
            all_satisfied=True,
            python_deps=[
                DependencyStatus(satisfied=True, name="httpx"),
            ],
        )

        assert result.all_satisfied is True
        assert result.missing_packages == []
        assert result.missing_plugins == []

    def test_create_result_with_missing(self) -> None:
        """Test creating result with missing dependencies."""
        result = DependencyCheckResult(
            plugin_name="test-plugin",
            all_satisfied=False,
            missing_packages=["httpx", "redis"],
            missing_plugins=["core-plugin"],
        )

        assert result.all_satisfied is False
        assert "httpx" in result.missing_packages
        assert "core-plugin" in result.missing_plugins


class TestDependencyChecker:
    """Tests for DependencyChecker."""

    def test_init_without_plugins(self) -> None:
        """Test initializing checker without loaded plugins."""
        checker = DependencyChecker()

        assert checker._loaded_plugins == {}

    def test_init_with_plugins(self) -> None:
        """Test initializing checker with loaded plugins."""
        mock_plugin = MagicMock()
        checker = DependencyChecker({"test-plugin": mock_plugin})

        assert "test-plugin" in checker._loaded_plugins

    @patch("feishu_webhook_bot.plugins.dependency_checker.importlib.metadata.version")
    def test_check_python_dependency_satisfied(self, mock_version: MagicMock) -> None:
        """Test checking satisfied Python dependency."""
        mock_version.return_value = "0.27.2"

        checker = DependencyChecker()
        dep = PackageDependency("httpx", ">=0.27.0")
        status = checker.check_python_dependency(dep)

        assert status.satisfied is True
        assert status.installed_version == "0.27.2"

    @patch("feishu_webhook_bot.plugins.dependency_checker.importlib.metadata.version")
    def test_check_python_dependency_not_installed(
        self, mock_version: MagicMock
    ) -> None:
        """Test checking Python dependency that is not installed."""
        import importlib.metadata

        mock_version.side_effect = importlib.metadata.PackageNotFoundError()

        checker = DependencyChecker()
        dep = PackageDependency("nonexistent-package", ">=1.0.0")
        status = checker.check_python_dependency(dep)

        assert status.satisfied is False
        assert status.installed_version is None
        assert "not installed" in status.error
        assert status.install_command is not None

    @patch("feishu_webhook_bot.plugins.dependency_checker.importlib.metadata.version")
    def test_check_python_dependency_version_mismatch(
        self, mock_version: MagicMock
    ) -> None:
        """Test checking Python dependency with version mismatch."""
        mock_version.return_value = "0.20.0"

        checker = DependencyChecker()
        dep = PackageDependency("httpx", ">=0.27.0")
        status = checker.check_python_dependency(dep)

        assert status.satisfied is False
        assert status.installed_version == "0.20.0"
        assert "does not satisfy" in status.error

    @patch("feishu_webhook_bot.plugins.dependency_checker.importlib.metadata.version")
    def test_check_python_dependency_no_version_requirement(
        self, mock_version: MagicMock
    ) -> None:
        """Test checking Python dependency without version requirement."""
        mock_version.return_value = "1.0.0"

        checker = DependencyChecker()
        dep = PackageDependency("httpx")
        status = checker.check_python_dependency(dep)

        assert status.satisfied is True

    def test_check_plugin_dependency_satisfied(self) -> None:
        """Test checking satisfied plugin dependency."""
        mock_plugin = MagicMock()
        mock_plugin.metadata.return_value.version = "2.0.0"

        checker = DependencyChecker({"core-plugin": mock_plugin})
        dep = PluginDependency("core-plugin", min_version="1.0.0")
        status = checker.check_plugin_dependency(dep)

        assert status.satisfied is True
        assert status.installed_version == "2.0.0"

    def test_check_plugin_dependency_not_loaded(self) -> None:
        """Test checking plugin dependency that is not loaded."""
        checker = DependencyChecker()
        dep = PluginDependency("missing-plugin")
        status = checker.check_plugin_dependency(dep)

        assert status.satisfied is False
        assert "not loaded" in status.error

    def test_check_plugin_dependency_version_mismatch(self) -> None:
        """Test checking plugin dependency with version mismatch."""
        mock_plugin = MagicMock()
        mock_plugin.metadata.return_value.version = "0.5.0"

        checker = DependencyChecker({"core-plugin": mock_plugin})
        dep = PluginDependency("core-plugin", min_version="1.0.0")
        status = checker.check_plugin_dependency(dep)

        assert status.satisfied is False
        assert "0.5.0" in status.installed_version

    @patch("feishu_webhook_bot.plugins.dependency_checker.importlib.metadata.version")
    def test_check_manifest(self, mock_version: MagicMock) -> None:
        """Test checking all dependencies in a manifest."""
        mock_version.return_value = "0.27.2"

        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            python_dependencies=[
                PackageDependency("httpx", ">=0.27.0"),
            ],
        )

        checker = DependencyChecker()
        result = checker.check_manifest(manifest)

        assert result.plugin_name == "test-plugin"
        assert result.all_satisfied is True
        assert len(result.python_deps) == 1

    @patch("feishu_webhook_bot.plugins.dependency_checker.importlib.metadata.version")
    def test_check_manifest_with_missing(self, mock_version: MagicMock) -> None:
        """Test checking manifest with missing dependencies."""
        import importlib.metadata

        mock_version.side_effect = importlib.metadata.PackageNotFoundError()

        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            python_dependencies=[
                PackageDependency("missing-package", ">=1.0.0"),
            ],
        )

        checker = DependencyChecker()
        result = checker.check_manifest(manifest)

        assert result.all_satisfied is False
        assert "missing-package" in result.missing_packages

    @patch("feishu_webhook_bot.plugins.dependency_checker.importlib.metadata.version")
    def test_check_manifest_optional_not_counted(
        self, mock_version: MagicMock
    ) -> None:
        """Test that optional dependencies don't affect all_satisfied."""
        import importlib.metadata

        mock_version.side_effect = importlib.metadata.PackageNotFoundError()

        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            python_dependencies=[
                PackageDependency("optional-package", optional=True),
            ],
        )

        checker = DependencyChecker()
        result = checker.check_manifest(manifest)

        assert result.all_satisfied is True
        assert result.missing_packages == []

    def test_get_install_commands(self) -> None:
        """Test getting install commands from result."""
        result = DependencyCheckResult(
            plugin_name="test-plugin",
            all_satisfied=False,
            python_deps=[
                DependencyStatus(
                    satisfied=False,
                    name="httpx",
                    install_command="pip install 'httpx>=0.27.0'",
                ),
                DependencyStatus(
                    satisfied=True,
                    name="pydantic",
                ),
            ],
        )

        checker = DependencyChecker()
        commands = checker.get_install_commands(result)

        assert len(commands) == 1
        assert "httpx" in commands[0]

    def test_get_all_missing_packages(self) -> None:
        """Test getting all missing packages across multiple results."""
        results = {
            "plugin-a": DependencyCheckResult(
                plugin_name="plugin-a",
                all_satisfied=False,
                missing_packages=["httpx", "redis"],
            ),
            "plugin-b": DependencyCheckResult(
                plugin_name="plugin-b",
                all_satisfied=False,
                missing_packages=["httpx", "aiohttp"],
            ),
        }

        checker = DependencyChecker()
        missing = checker.get_all_missing_packages(results)

        assert "httpx" in missing
        assert "redis" in missing
        assert "aiohttp" in missing
        assert len(missing) == 3

    def test_update_loaded_plugins(self) -> None:
        """Test updating loaded plugins."""
        checker = DependencyChecker()
        assert checker._loaded_plugins == {}

        mock_plugin = MagicMock()
        checker.update_loaded_plugins({"new-plugin": mock_plugin})

        assert "new-plugin" in checker._loaded_plugins

    def test_version_satisfies_greater_equal(self) -> None:
        """Test version comparison with >=."""
        assert DependencyChecker._version_satisfies("1.0.0", ">=1.0.0") is True
        assert DependencyChecker._version_satisfies("1.1.0", ">=1.0.0") is True
        assert DependencyChecker._version_satisfies("0.9.0", ">=1.0.0") is False

    def test_version_satisfies_equal(self) -> None:
        """Test version comparison with ==."""
        assert DependencyChecker._version_satisfies("1.0.0", "==1.0.0") is True
        assert DependencyChecker._version_satisfies("1.0.1", "==1.0.0") is False
