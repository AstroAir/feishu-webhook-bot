"""Tests for plugin sandbox execution environment."""

import os
import tempfile
import time
from pathlib import Path

import pytest

from feishu_webhook_bot.plugins.permissions import PermissionManager, PluginPermission
from feishu_webhook_bot.plugins.sandbox import (
    PluginSandbox,
    SandboxConfig,
    SandboxViolation,
    configure_sandbox,
    get_sandbox,
)


class TestSandboxConfig:
    """Tests for SandboxConfig dataclass."""

    def test_default_config(self):
        """Test default sandbox configuration."""
        config = SandboxConfig()
        assert config.enabled is True
        assert config.max_execution_time == 30.0
        assert config.max_memory_mb == 0
        assert config.allowed_paths == []
        assert "subprocess" in config.blocked_modules
        assert config.network_whitelist == []

    def test_custom_config(self):
        """Test custom sandbox configuration."""
        config = SandboxConfig(
            enabled=False,
            max_execution_time=60.0,
            max_memory_mb=512,
            allowed_paths=["/tmp", "/data"],
            blocked_modules=["os", "sys"],
            network_whitelist=["api.example.com"],
        )
        assert config.enabled is False
        assert config.max_execution_time == 60.0
        assert config.max_memory_mb == 512
        assert "/tmp" in config.allowed_paths
        assert "api.example.com" in config.network_whitelist


class TestSandboxViolation:
    """Tests for SandboxViolation dataclass."""

    def test_violation_creation(self):
        """Test creating a sandbox violation."""
        violation = SandboxViolation(
            plugin_name="test-plugin",
            violation_type="file_access_denied",
            details="Attempted to read /etc/passwd",
        )
        assert violation.plugin_name == "test-plugin"
        assert violation.violation_type == "file_access_denied"
        assert violation.details == "Attempted to read /etc/passwd"
        assert violation.timestamp > 0

    def test_violation_to_dict(self):
        """Test violation to_dict method."""
        violation = SandboxViolation(
            plugin_name="test-plugin",
            violation_type="network_blocked",
            details="Host not in whitelist",
        )
        data = violation.to_dict()
        assert data["plugin_name"] == "test-plugin"
        assert data["violation_type"] == "network_blocked"
        assert data["details"] == "Host not in whitelist"
        assert "timestamp" in data


class TestPluginSandbox:
    """Tests for PluginSandbox class."""

    @pytest.fixture
    def permission_manager(self):
        """Create a permission manager with some grants."""
        pm = PermissionManager()
        pm.grant_permissions(
            "test-plugin",
            permissions={
                PluginPermission.FILE_READ,
                PluginPermission.NETWORK_HTTP,
                PluginPermission.SYSTEM_INFO,
            },
        )
        return pm

    @pytest.fixture
    def sandbox(self, permission_manager):
        """Create a sandbox with permission manager."""
        config = SandboxConfig(
            enabled=True,
            allowed_paths=[tempfile.gettempdir()],
            network_whitelist=["api.example.com", "localhost"],
        )
        return PluginSandbox(config=config, permission_manager=permission_manager)

    @pytest.fixture
    def disabled_sandbox(self):
        """Create a disabled sandbox."""
        config = SandboxConfig(enabled=False)
        return PluginSandbox(config=config)

    def test_sandbox_initialization(self, sandbox):
        """Test sandbox initialization."""
        assert sandbox.config.enabled is True
        assert sandbox.permission_manager is not None

    def test_create_context(self, sandbox):
        """Test creating plugin context."""
        context = sandbox.create_context("test-plugin")
        assert context is not None
        assert context.plugin_name == "test-plugin"
        assert context.sandbox is sandbox

    def test_get_context(self, sandbox):
        """Test getting plugin context."""
        sandbox.create_context("test-plugin")
        context = sandbox.get_context("test-plugin")
        assert context is not None
        assert context.plugin_name == "test-plugin"

    def test_get_context_nonexistent(self, sandbox):
        """Test getting nonexistent context."""
        context = sandbox.get_context("nonexistent")
        assert context is None

    def test_remove_context(self, sandbox):
        """Test removing plugin context."""
        sandbox.create_context("test-plugin")
        sandbox.remove_context("test-plugin")
        assert sandbox.get_context("test-plugin") is None

    def test_record_violation(self, sandbox):
        """Test recording a violation."""
        sandbox.record_violation(
            "test-plugin",
            "file_access_denied",
            "Attempted to read /etc/passwd",
        )
        violations = sandbox.get_violations("test-plugin")
        assert len(violations) == 1
        assert violations[0].violation_type == "file_access_denied"

    def test_get_violations_all(self, sandbox):
        """Test getting all violations."""
        sandbox.record_violation("plugin1", "type1", "details1")
        sandbox.record_violation("plugin2", "type2", "details2")

        all_violations = sandbox.get_violations()
        assert len(all_violations) == 2

    def test_get_violations_filtered(self, sandbox):
        """Test getting violations filtered by plugin."""
        sandbox.record_violation("plugin1", "type1", "details1")
        sandbox.record_violation("plugin2", "type2", "details2")

        plugin1_violations = sandbox.get_violations("plugin1")
        assert len(plugin1_violations) == 1
        assert plugin1_violations[0].plugin_name == "plugin1"

    def test_clear_violations_all(self, sandbox):
        """Test clearing all violations."""
        sandbox.record_violation("plugin1", "type1", "details1")
        sandbox.record_violation("plugin2", "type2", "details2")

        sandbox.clear_violations()
        assert len(sandbox.get_violations()) == 0

    def test_clear_violations_filtered(self, sandbox):
        """Test clearing violations for specific plugin."""
        sandbox.record_violation("plugin1", "type1", "details1")
        sandbox.record_violation("plugin2", "type2", "details2")

        sandbox.clear_violations("plugin1")
        violations = sandbox.get_violations()
        assert len(violations) == 1
        assert violations[0].plugin_name == "plugin2"

    def test_check_file_access_allowed(self, sandbox):
        """Test file access check when allowed."""
        temp_path = Path(tempfile.gettempdir()) / "test.txt"
        allowed = sandbox.check_file_access("test-plugin", temp_path, write=False)
        assert allowed is True

    def test_check_file_access_no_permission(self, sandbox, permission_manager):
        """Test file access check without permission."""
        permission_manager.revoke_permission("test-plugin", PluginPermission.FILE_READ)

        allowed = sandbox.check_file_access("test-plugin", "/tmp/test.txt", write=False)
        assert allowed is False

        violations = sandbox.get_violations("test-plugin")
        assert len(violations) == 1
        assert "FILE_READ" in violations[0].details

    def test_check_file_access_path_blocked(self, sandbox):
        """Test file access check with blocked path."""
        allowed = sandbox.check_file_access("test-plugin", "/etc/passwd", write=False)
        assert allowed is False

    def test_check_file_access_disabled_sandbox(self, disabled_sandbox):
        """Test file access check when sandbox disabled."""
        allowed = disabled_sandbox.check_file_access("test-plugin", "/etc/passwd")
        assert allowed is True

    def test_check_network_access_allowed(self, sandbox):
        """Test network access check when allowed."""
        allowed = sandbox.check_network_access("test-plugin", "api.example.com")
        assert allowed is True

    def test_check_network_access_no_permission(self, sandbox, permission_manager):
        """Test network access check without permission."""
        permission_manager.revoke_permission("test-plugin", PluginPermission.NETWORK_HTTP)

        allowed = sandbox.check_network_access("test-plugin", "api.example.com")
        assert allowed is False

    def test_check_network_access_host_blocked(self, sandbox):
        """Test network access check with blocked host."""
        allowed = sandbox.check_network_access("test-plugin", "malicious.com")
        assert allowed is False

        violations = sandbox.get_violations("test-plugin")
        assert any("whitelist" in v.details for v in violations)

    def test_check_network_access_disabled_sandbox(self, disabled_sandbox):
        """Test network access check when sandbox disabled."""
        allowed = disabled_sandbox.check_network_access("test-plugin", "any.host.com")
        assert allowed is True

    def test_check_system_access_info(self, sandbox):
        """Test system info access check."""
        allowed = sandbox.check_system_access("test-plugin", "info")
        assert allowed is True

    def test_check_system_access_exec_no_permission(self, sandbox):
        """Test system exec access check without permission."""
        allowed = sandbox.check_system_access("test-plugin", "exec")
        assert allowed is False

    def test_check_system_access_env_no_permission(self, sandbox):
        """Test system env access check without permission."""
        allowed = sandbox.check_system_access("test-plugin", "env")
        assert allowed is False

    def test_wrap_function(self, sandbox):
        """Test wrapping a function with sandbox protections."""
        call_count = 0

        def test_func():
            nonlocal call_count
            call_count += 1
            return "result"

        sandbox.create_context("test-plugin")
        wrapped = sandbox.wrap_function("test-plugin", test_func)

        result = wrapped()
        assert result == "result"
        assert call_count == 1

    def test_wrap_function_tracks_execution_time(self, sandbox):
        """Test that wrapped function tracks execution time."""

        def slow_func():
            time.sleep(0.1)
            return "done"

        context = sandbox.create_context("test-plugin")
        wrapped = sandbox.wrap_function("test-plugin", slow_func)

        wrapped()
        assert context.total_execution_time >= 0.1

    def test_wrap_function_tracks_call_count(self, sandbox):
        """Test that wrapped function tracks call count."""

        def test_func():
            return "result"

        context = sandbox.create_context("test-plugin")
        wrapped = sandbox.wrap_function("test-plugin", test_func)

        wrapped()
        wrapped()
        wrapped()
        assert context.call_count == 3

    def test_wrap_function_records_errors(self, sandbox):
        """Test that wrapped function records errors."""

        def error_func():
            raise ValueError("Test error")

        sandbox.create_context("test-plugin")
        wrapped = sandbox.wrap_function("test-plugin", error_func)

        with pytest.raises(ValueError):
            wrapped()

        violations = sandbox.get_violations("test-plugin")
        assert any("execution_error" in v.violation_type for v in violations)

    def test_wrap_function_disabled_sandbox(self, disabled_sandbox):
        """Test wrap_function returns original when sandbox disabled."""

        def test_func():
            return "result"

        wrapped = disabled_sandbox.wrap_function("test-plugin", test_func)
        assert wrapped is test_func


class TestPluginContext:
    """Tests for PluginContext class."""

    @pytest.fixture
    def context(self):
        """Create a plugin context."""
        pm = PermissionManager()
        pm.grant_permissions(
            "test-plugin",
            permissions={
                PluginPermission.FILE_READ,
                PluginPermission.FILE_WRITE,
                PluginPermission.SYSTEM_ENV,
            },
        )
        sandbox = PluginSandbox(
            config=SandboxConfig(allowed_paths=[tempfile.gettempdir()]),
            permission_manager=pm,
        )
        return sandbox.create_context("test-plugin")

    def test_context_initialization(self, context):
        """Test context initialization."""
        assert context.plugin_name == "test-plugin"
        assert context.call_count == 0
        assert context.total_execution_time == 0.0
        assert context.created_at > 0

    def test_check_permission(self, context):
        """Test check_permission method."""
        assert context.check_permission(PluginPermission.FILE_READ) is True
        assert context.check_permission(PluginPermission.NETWORK_HTTP) is False

    def test_require_permission_granted(self, context):
        """Test require_permission with granted permission."""
        context.require_permission(PluginPermission.FILE_READ)

    def test_require_permission_not_granted(self, context):
        """Test require_permission raises error when not granted."""
        with pytest.raises(PermissionError):
            context.require_permission(PluginPermission.NETWORK_HTTP)

    def test_read_file(self, context):
        """Test read_file method."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            content = context.read_file(temp_path)
            assert content == "test content"
        finally:
            os.unlink(temp_path)

    def test_read_file_denied(self, context):
        """Test read_file with denied path."""
        with pytest.raises(PermissionError):
            context.read_file("/etc/passwd")

    def test_write_file(self, context):
        """Test write_file method."""
        temp_path = Path(tempfile.gettempdir()) / "test_write.txt"
        try:
            context.write_file(temp_path, "written content")
            assert temp_path.read_text() == "written content"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_write_file_denied(self, context):
        """Test write_file with denied path."""
        with pytest.raises(PermissionError):
            context.write_file("/etc/test.txt", "content")

    def test_get_env(self, context):
        """Test get_env method."""
        os.environ["TEST_VAR"] = "test_value"
        try:
            value = context.get_env("TEST_VAR")
            assert value == "test_value"
        finally:
            del os.environ["TEST_VAR"]

    def test_get_env_default(self, context):
        """Test get_env with default value."""
        value = context.get_env("NONEXISTENT_VAR", "default")
        assert value == "default"

    def test_get_stats(self, context):
        """Test get_stats method."""
        context.call_count = 5
        context.total_execution_time = 1.5

        stats = context.get_stats()
        assert stats["plugin_name"] == "test-plugin"
        assert stats["call_count"] == 5
        assert stats["total_execution_time"] == 1.5
        assert "created_at" in stats
        assert "uptime" in stats


class TestGlobalSandbox:
    """Tests for global sandbox functions."""

    def test_get_sandbox_returns_singleton(self):
        """Test that get_sandbox returns a singleton."""
        sandbox1 = get_sandbox()
        sandbox2 = get_sandbox()
        assert sandbox1 is sandbox2

    def test_configure_sandbox(self):
        """Test configure_sandbox function."""
        config = SandboxConfig(
            enabled=True,
            max_execution_time=120.0,
        )
        sandbox = configure_sandbox(config)
        assert sandbox.config.max_execution_time == 120.0

    def test_configure_sandbox_replaces_global(self):
        """Test that configure_sandbox replaces global instance."""
        config1 = SandboxConfig(max_execution_time=30.0)
        configure_sandbox(config1)

        config2 = SandboxConfig(max_execution_time=60.0)
        sandbox2 = configure_sandbox(config2)

        assert sandbox2.config.max_execution_time == 60.0
        assert get_sandbox() is sandbox2
