"""Tests for plugin permission system."""

import pytest

from feishu_webhook_bot.plugins.permissions import (
    DANGEROUS_PERMISSIONS,
    PERMISSION_LEVELS,
    PermissionLevel,
    PermissionManager,
    PluginPermission,
    PluginPermissionGrant,
    PluginPermissionSet,
    get_permission_manager,
    require_permission,
)


class TestPluginPermission:
    """Tests for PluginPermission enum."""

    def test_all_permissions_defined(self):
        """Verify all expected permissions are defined."""
        expected = [
            "NETWORK_SEND",
            "NETWORK_HTTP",
            "NETWORK_WEBSOCKET",
            "FILE_READ",
            "FILE_WRITE",
            "FILE_PLUGIN_DIR",
            "SYSTEM_INFO",
            "SYSTEM_EXEC",
            "SYSTEM_ENV",
            "SCHEDULER_JOBS",
            "SCHEDULER_MANAGE",
            "CONFIG_READ",
            "CONFIG_WRITE",
            "DATABASE_READ",
            "DATABASE_WRITE",
            "AI_CHAT",
            "AI_TOOLS",
            "EVENT_LISTEN",
            "EVENT_EMIT",
            "PROVIDER_ACCESS",
            "PROVIDER_MANAGE",
        ]
        for perm_name in expected:
            assert hasattr(PluginPermission, perm_name)

    def test_permission_values_unique(self):
        """Verify all permission values are unique."""
        values = [p.value for p in PluginPermission]
        assert len(values) == len(set(values))


class TestPermissionLevel:
    """Tests for PermissionLevel enum."""

    def test_all_levels_defined(self):
        """Verify all permission levels are defined."""
        expected = ["MINIMAL", "STANDARD", "ELEVATED", "FULL"]
        for level_name in expected:
            assert hasattr(PermissionLevel, level_name)

    def test_permission_levels_mapping(self):
        """Verify PERMISSION_LEVELS contains all levels."""
        for level in PermissionLevel:
            assert level in PERMISSION_LEVELS


class TestDangerousPermissions:
    """Tests for DANGEROUS_PERMISSIONS set."""

    def test_dangerous_permissions_defined(self):
        """Verify dangerous permissions are defined."""
        assert PluginPermission.SYSTEM_EXEC in DANGEROUS_PERMISSIONS
        assert PluginPermission.SYSTEM_ENV in DANGEROUS_PERMISSIONS
        assert PluginPermission.CONFIG_WRITE in DANGEROUS_PERMISSIONS
        assert PluginPermission.FILE_WRITE in DANGEROUS_PERMISSIONS
        assert PluginPermission.PROVIDER_MANAGE in DANGEROUS_PERMISSIONS

    def test_safe_permissions_not_dangerous(self):
        """Verify safe permissions are not in dangerous set."""
        assert PluginPermission.NETWORK_SEND not in DANGEROUS_PERMISSIONS
        assert PluginPermission.CONFIG_READ not in DANGEROUS_PERMISSIONS
        assert PluginPermission.EVENT_LISTEN not in DANGEROUS_PERMISSIONS


class TestPluginPermissionSet:
    """Tests for PluginPermissionSet dataclass."""

    def test_empty_permission_set(self):
        """Test empty permission set."""
        perm_set = PluginPermissionSet()
        assert perm_set.required == set()
        assert perm_set.optional == set()
        assert perm_set.level is None

    def test_permission_set_with_required(self):
        """Test permission set with required permissions."""
        perm_set = PluginPermissionSet(
            required={PluginPermission.NETWORK_SEND, PluginPermission.CONFIG_READ}
        )
        assert len(perm_set.required) == 2
        assert PluginPermission.NETWORK_SEND in perm_set.required

    def test_permission_set_with_level(self):
        """Test permission set with level."""
        perm_set = PluginPermissionSet(level=PermissionLevel.STANDARD)
        assert perm_set.level == PermissionLevel.STANDARD

    def test_get_all_permissions(self):
        """Test get_all_permissions method."""
        perm_set = PluginPermissionSet(
            required={PluginPermission.NETWORK_SEND},
            optional={PluginPermission.FILE_READ},
        )
        all_perms = perm_set.get_all_permissions()
        assert PluginPermission.NETWORK_SEND in all_perms
        assert PluginPermission.FILE_READ in all_perms

    def test_get_all_permissions_with_level(self):
        """Test get_all_permissions includes level permissions."""
        perm_set = PluginPermissionSet(level=PermissionLevel.MINIMAL)
        all_perms = perm_set.get_all_permissions()
        assert PluginPermission.NETWORK_SEND in all_perms
        assert PluginPermission.CONFIG_READ in all_perms

    def test_get_required_permissions(self):
        """Test get_required_permissions method."""
        perm_set = PluginPermissionSet(
            required={PluginPermission.NETWORK_SEND},
            level=PermissionLevel.MINIMAL,
        )
        required = perm_set.get_required_permissions()
        assert PluginPermission.NETWORK_SEND in required
        assert PluginPermission.CONFIG_READ in required

    def test_has_dangerous_permissions(self):
        """Test has_dangerous_permissions method."""
        safe_set = PluginPermissionSet(required={PluginPermission.NETWORK_SEND})
        assert safe_set.has_dangerous_permissions() is False

        dangerous_set = PluginPermissionSet(required={PluginPermission.SYSTEM_EXEC})
        assert dangerous_set.has_dangerous_permissions() is True

    def test_get_dangerous_permissions(self):
        """Test get_dangerous_permissions method."""
        perm_set = PluginPermissionSet(
            required={
                PluginPermission.NETWORK_SEND,
                PluginPermission.SYSTEM_EXEC,
                PluginPermission.FILE_WRITE,
            }
        )
        dangerous = perm_set.get_dangerous_permissions()
        assert PluginPermission.SYSTEM_EXEC in dangerous
        assert PluginPermission.FILE_WRITE in dangerous
        assert PluginPermission.NETWORK_SEND not in dangerous

    def test_to_dict(self):
        """Test to_dict method."""
        perm_set = PluginPermissionSet(
            required={PluginPermission.NETWORK_SEND},
            optional={PluginPermission.FILE_READ},
            level=PermissionLevel.STANDARD,
        )
        data = perm_set.to_dict()
        assert "required" in data
        assert "optional" in data
        assert "level" in data
        assert data["level"] == "STANDARD"


class TestPluginPermissionGrant:
    """Tests for PluginPermissionGrant dataclass."""

    def test_empty_grant(self):
        """Test empty permission grant."""
        grant = PluginPermissionGrant(plugin_name="test-plugin")
        assert grant.plugin_name == "test-plugin"
        assert grant.granted == set()
        assert grant.denied == set()
        assert grant.approved_dangerous == set()

    def test_is_granted(self):
        """Test is_granted method."""
        grant = PluginPermissionGrant(
            plugin_name="test",
            granted={PluginPermission.NETWORK_SEND},
        )
        assert grant.is_granted(PluginPermission.NETWORK_SEND) is True
        assert grant.is_granted(PluginPermission.FILE_READ) is False

    def test_is_granted_denied_takes_precedence(self):
        """Test that denied permissions override granted."""
        grant = PluginPermissionGrant(
            plugin_name="test",
            granted={PluginPermission.NETWORK_SEND},
            denied={PluginPermission.NETWORK_SEND},
        )
        assert grant.is_granted(PluginPermission.NETWORK_SEND) is False

    def test_grant_permission(self):
        """Test grant method."""
        grant = PluginPermissionGrant(plugin_name="test")
        grant.grant(PluginPermission.NETWORK_SEND)
        assert PluginPermission.NETWORK_SEND in grant.granted

    def test_grant_removes_from_denied(self):
        """Test that granting removes from denied set."""
        grant = PluginPermissionGrant(
            plugin_name="test",
            denied={PluginPermission.NETWORK_SEND},
        )
        grant.grant(PluginPermission.NETWORK_SEND)
        assert PluginPermission.NETWORK_SEND in grant.granted
        assert PluginPermission.NETWORK_SEND not in grant.denied

    def test_deny_permission(self):
        """Test deny method."""
        grant = PluginPermissionGrant(plugin_name="test")
        grant.deny(PluginPermission.SYSTEM_EXEC)
        assert PluginPermission.SYSTEM_EXEC in grant.denied

    def test_deny_removes_from_granted(self):
        """Test that denying removes from granted set."""
        grant = PluginPermissionGrant(
            plugin_name="test",
            granted={PluginPermission.SYSTEM_EXEC},
        )
        grant.deny(PluginPermission.SYSTEM_EXEC)
        assert PluginPermission.SYSTEM_EXEC in grant.denied
        assert PluginPermission.SYSTEM_EXEC not in grant.granted

    def test_approve_dangerous(self):
        """Test approve_dangerous method."""
        grant = PluginPermissionGrant(plugin_name="test")
        grant.approve_dangerous(PluginPermission.SYSTEM_EXEC)
        assert PluginPermission.SYSTEM_EXEC in grant.approved_dangerous
        assert PluginPermission.SYSTEM_EXEC in grant.granted

    def test_approve_dangerous_non_dangerous(self):
        """Test approve_dangerous with non-dangerous permission."""
        grant = PluginPermissionGrant(plugin_name="test")
        grant.approve_dangerous(PluginPermission.NETWORK_SEND)
        assert PluginPermission.NETWORK_SEND not in grant.approved_dangerous

    def test_to_dict(self):
        """Test to_dict method."""
        grant = PluginPermissionGrant(
            plugin_name="test",
            granted={PluginPermission.NETWORK_SEND},
            denied={PluginPermission.SYSTEM_EXEC},
        )
        data = grant.to_dict()
        assert data["plugin_name"] == "test"
        assert "NETWORK_SEND" in data["granted"]
        assert "SYSTEM_EXEC" in data["denied"]


class TestPermissionManager:
    """Tests for PermissionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh PermissionManager."""
        return PermissionManager()

    def test_register_plugin_permissions(self, manager):
        """Test registering plugin permissions."""
        perm_set = PluginPermissionSet(required={PluginPermission.NETWORK_SEND})
        manager.register_plugin_permissions("test-plugin", perm_set)

        retrieved = manager.get_plugin_permissions("test-plugin")
        assert retrieved is not None
        assert PluginPermission.NETWORK_SEND in retrieved.required

    def test_grant_permissions_auto(self, manager):
        """Test auto-granting non-dangerous permissions."""
        perm_set = PluginPermissionSet(
            required={PluginPermission.NETWORK_SEND, PluginPermission.CONFIG_READ}
        )
        manager.register_plugin_permissions("test-plugin", perm_set)
        grant = manager.grant_permissions("test-plugin", auto_grant=True)

        assert grant.is_granted(PluginPermission.NETWORK_SEND)
        assert grant.is_granted(PluginPermission.CONFIG_READ)

    def test_grant_permissions_auto_skips_dangerous(self, manager):
        """Test that auto-grant skips dangerous permissions."""
        perm_set = PluginPermissionSet(
            required={PluginPermission.NETWORK_SEND, PluginPermission.SYSTEM_EXEC}
        )
        manager.register_plugin_permissions("test-plugin", perm_set)
        grant = manager.grant_permissions("test-plugin", auto_grant=True)

        assert grant.is_granted(PluginPermission.NETWORK_SEND)
        assert not grant.is_granted(PluginPermission.SYSTEM_EXEC)

    def test_grant_permissions_explicit(self, manager):
        """Test explicitly granting permissions."""
        grant = manager.grant_permissions(
            "test-plugin",
            permissions={PluginPermission.SYSTEM_EXEC},
        )
        assert grant.is_granted(PluginPermission.SYSTEM_EXEC)
        assert PluginPermission.SYSTEM_EXEC in grant.approved_dangerous

    def test_get_grant(self, manager):
        """Test get_grant method."""
        assert manager.get_grant("nonexistent") is None

        manager.grant_permissions("test-plugin", permissions={PluginPermission.NETWORK_SEND})
        grant = manager.get_grant("test-plugin")
        assert grant is not None
        assert grant.plugin_name == "test-plugin"

    def test_check_permission(self, manager):
        """Test check_permission method."""
        manager.grant_permissions("test-plugin", permissions={PluginPermission.NETWORK_SEND})

        assert manager.check_permission("test-plugin", PluginPermission.NETWORK_SEND) is True
        assert manager.check_permission("test-plugin", PluginPermission.FILE_READ) is False
        assert manager.check_permission("nonexistent", PluginPermission.NETWORK_SEND) is False

    def test_require_permission_granted(self, manager):
        """Test require_permission with granted permission."""
        manager.grant_permissions("test-plugin", permissions={PluginPermission.NETWORK_SEND})
        manager.require_permission("test-plugin", PluginPermission.NETWORK_SEND)

    def test_require_permission_not_granted(self, manager):
        """Test require_permission raises error when not granted."""
        with pytest.raises(PermissionError):
            manager.require_permission("test-plugin", PluginPermission.NETWORK_SEND)

    def test_validate_plugin_permissions_all_granted(self, manager):
        """Test validate_plugin_permissions when all granted."""
        perm_set = PluginPermissionSet(required={PluginPermission.NETWORK_SEND})
        manager.register_plugin_permissions("test-plugin", perm_set)
        manager.grant_permissions("test-plugin", auto_grant=True)

        is_valid, missing = manager.validate_plugin_permissions("test-plugin")
        assert is_valid is True
        assert missing == []

    def test_validate_plugin_permissions_missing(self, manager):
        """Test validate_plugin_permissions with missing permissions."""
        perm_set = PluginPermissionSet(
            required={PluginPermission.NETWORK_SEND, PluginPermission.SYSTEM_EXEC}
        )
        manager.register_plugin_permissions("test-plugin", perm_set)
        manager.grant_permissions("test-plugin", auto_grant=True)

        is_valid, missing = manager.validate_plugin_permissions("test-plugin")
        assert is_valid is False
        assert "SYSTEM_EXEC" in missing

    def test_get_pending_dangerous_approvals(self, manager):
        """Test get_pending_dangerous_approvals method."""
        perm_set = PluginPermissionSet(
            required={PluginPermission.SYSTEM_EXEC, PluginPermission.FILE_WRITE}
        )
        manager.register_plugin_permissions("test-plugin", perm_set)
        manager.grant_permissions("test-plugin", auto_grant=True)

        pending = manager.get_pending_dangerous_approvals("test-plugin")
        assert PluginPermission.SYSTEM_EXEC in pending
        assert PluginPermission.FILE_WRITE in pending

    def test_revoke_permission(self, manager):
        """Test revoke_permission method."""
        manager.grant_permissions("test-plugin", permissions={PluginPermission.NETWORK_SEND})
        assert manager.check_permission("test-plugin", PluginPermission.NETWORK_SEND)

        manager.revoke_permission("test-plugin", PluginPermission.NETWORK_SEND)
        assert not manager.check_permission("test-plugin", PluginPermission.NETWORK_SEND)

    def test_revoke_all(self, manager):
        """Test revoke_all method."""
        manager.grant_permissions(
            "test-plugin",
            permissions={PluginPermission.NETWORK_SEND, PluginPermission.FILE_READ},
        )
        manager.revoke_all("test-plugin")
        assert manager.get_grant("test-plugin") is None

    def test_get_all_grants(self, manager):
        """Test get_all_grants method."""
        manager.grant_permissions("plugin1", permissions={PluginPermission.NETWORK_SEND})
        manager.grant_permissions("plugin2", permissions={PluginPermission.FILE_READ})

        all_grants = manager.get_all_grants()
        assert "plugin1" in all_grants
        assert "plugin2" in all_grants

    def test_clear(self, manager):
        """Test clear method."""
        perm_set = PluginPermissionSet(required={PluginPermission.NETWORK_SEND})
        manager.register_plugin_permissions("test-plugin", perm_set)
        manager.grant_permissions("test-plugin", auto_grant=True)

        manager.clear()
        assert manager.get_grant("test-plugin") is None
        assert manager.get_plugin_permissions("test-plugin") is None


class TestGetPermissionManager:
    """Tests for get_permission_manager function."""

    def test_returns_singleton(self):
        """Test that get_permission_manager returns a singleton."""
        pm1 = get_permission_manager()
        pm2 = get_permission_manager()
        assert pm1 is pm2

    def test_returns_permission_manager(self):
        """Test that get_permission_manager returns PermissionManager."""
        pm = get_permission_manager()
        assert isinstance(pm, PermissionManager)


class TestRequirePermissionDecorator:
    """Tests for require_permission decorator."""

    def test_decorator_with_permission_granted(self):
        """Test decorator allows execution when permission granted."""
        from feishu_webhook_bot.plugins.base import BasePlugin, PluginMetadata

        class TestPlugin(BasePlugin):
            def metadata(self):
                return PluginMetadata(name="decorator-test")

            @require_permission(PluginPermission.NETWORK_SEND)
            def send_message(self):
                return "sent"

        pm = get_permission_manager()
        pm.grant_permissions("decorator-test", permissions={PluginPermission.NETWORK_SEND})

        from feishu_webhook_bot.core import BotConfig

        plugin = TestPlugin(BotConfig(), None, None)
        result = plugin.send_message()
        assert result == "sent"

    def test_decorator_without_permission(self):
        """Test decorator raises error when permission not granted."""
        from feishu_webhook_bot.plugins.base import BasePlugin, PluginMetadata

        class TestPlugin(BasePlugin):
            def metadata(self):
                return PluginMetadata(name="decorator-test-fail")

            @require_permission(PluginPermission.SYSTEM_EXEC)
            def execute_command(self):
                return "executed"

        from feishu_webhook_bot.core import BotConfig

        plugin = TestPlugin(BotConfig(), None, None)
        with pytest.raises(PermissionError):
            plugin.execute_command()
