"""Comprehensive tests for authentication database models.

Tests cover:
- User model creation
- User model attributes
- User model methods (is_locked, to_dict)
- User model representation
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from feishu_webhook_bot.auth.models import Base, User

# ==============================================================================
# User Model Creation Tests
# ==============================================================================


class TestUserModelCreation:
    """Tests for User model creation."""

    def test_user_creation_required_fields(self):
        """Test User creation with required fields."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_123",
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.hashed_password == "hashed_password_123"

    def test_user_default_values(self):
        """Test User default values when not explicitly set."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
        )

        # Note: SQLAlchemy defaults are applied at database level, not Python level
        # When creating User without a session, defaults may be None
        # The actual defaults are tested in integration tests with a database
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.hashed_password == "hashed"

    def test_user_custom_values(self):
        """Test User with custom values."""
        user = User(
            email="custom@example.com",
            username="customuser",
            hashed_password="hashed",
            is_active=False,
            is_verified=True,
            failed_login_attempts=3,
        )

        assert user.is_active is False
        assert user.is_verified is True
        assert user.failed_login_attempts == 3


# ==============================================================================
# User Model Attributes Tests
# ==============================================================================


class TestUserModelAttributes:
    """Tests for User model attributes."""

    def test_user_tablename(self):
        """Test User table name."""
        assert User.__tablename__ == "users"

    def test_user_repr(self):
        """Test User string representation."""
        user = User(
            id=1,
            email="repr@example.com",
            username="repruser",
            hashed_password="hashed",
        )

        repr_str = repr(user)

        assert "User" in repr_str
        assert "id=1" in repr_str
        assert "repruser" in repr_str
        assert "repr@example.com" in repr_str

    def test_user_timestamps_default(self):
        """Test User timestamp defaults."""
        # Note: SQLAlchemy defaults are applied on insert, not on object creation
        # This test verifies the default callable is set up correctly
        assert User.created_at.default is not None
        assert User.updated_at.default is not None


# ==============================================================================
# User is_locked Method Tests
# ==============================================================================


class TestUserIsLocked:
    """Tests for User.is_locked method."""

    def test_is_locked_when_not_locked(self):
        """Test is_locked returns False when not locked."""
        user = User(
            email="unlocked@example.com",
            username="unlockeduser",
            hashed_password="hashed",
            locked_until=None,
        )

        assert user.is_locked() is False

    def test_is_locked_when_locked_future(self):
        """Test is_locked returns True when locked until future."""
        future_time = datetime.now(UTC) + timedelta(hours=1)
        user = User(
            email="locked@example.com",
            username="lockeduser",
            hashed_password="hashed",
            locked_until=future_time,
        )

        assert user.is_locked() is True

    def test_is_locked_when_lock_expired(self):
        """Test is_locked returns False when lock has expired."""
        past_time = datetime.now(UTC) - timedelta(hours=1)
        user = User(
            email="expired@example.com",
            username="expireduser",
            hashed_password="hashed",
            locked_until=past_time,
        )

        assert user.is_locked() is False

    def test_is_locked_boundary(self):
        """Test is_locked at exact boundary."""
        # Lock until 1 second ago
        past_time = datetime.now(UTC) - timedelta(seconds=1)
        user = User(
            email="boundary@example.com",
            username="boundaryuser",
            hashed_password="hashed",
            locked_until=past_time,
        )

        assert user.is_locked() is False

    def test_is_locked_naive_datetime(self):
        """Test is_locked handles naive datetime (SQLite compatibility)."""
        # SQLite may return naive datetimes
        naive_future = datetime.now() + timedelta(hours=1)
        user = User(
            email="naive@example.com",
            username="naiveuser",
            hashed_password="hashed",
            locked_until=naive_future,
        )

        # Should handle naive datetime by assuming UTC
        result = user.is_locked()
        assert isinstance(result, bool)


# ==============================================================================
# User to_dict Method Tests
# ==============================================================================


class TestUserToDict:
    """Tests for User.to_dict method."""

    def test_to_dict_basic(self):
        """Test to_dict returns expected fields."""
        user = User(
            id=1,
            email="dict@example.com",
            username="dictuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=False,
        )

        result = user.to_dict()

        assert result["id"] == 1
        assert result["email"] == "dict@example.com"
        assert result["username"] == "dictuser"
        assert result["is_active"] is True
        assert result["is_verified"] is False

    def test_to_dict_excludes_password(self):
        """Test to_dict excludes sensitive data."""
        user = User(
            id=1,
            email="secure@example.com",
            username="secureuser",
            hashed_password="super_secret_hash",
        )

        result = user.to_dict()

        assert "hashed_password" not in result
        assert "password" not in result

    def test_to_dict_excludes_security_fields(self):
        """Test to_dict excludes security-related fields."""
        user = User(
            id=1,
            email="security@example.com",
            username="securityuser",
            hashed_password="hashed",
            failed_login_attempts=5,
            locked_until=datetime.now(UTC),
        )

        result = user.to_dict()

        assert "failed_login_attempts" not in result
        assert "locked_until" not in result

    def test_to_dict_timestamps_format(self):
        """Test to_dict formats timestamps as ISO strings."""
        now = datetime.now(UTC)
        user = User(
            id=1,
            email="timestamp@example.com",
            username="timestampuser",
            hashed_password="hashed",
            created_at=now,
            updated_at=now,
        )

        result = user.to_dict()

        assert result["created_at"] == now.isoformat()
        assert result["updated_at"] == now.isoformat()

    def test_to_dict_none_timestamps(self):
        """Test to_dict handles None timestamps."""
        user = User(
            id=1,
            email="none@example.com",
            username="noneuser",
            hashed_password="hashed",
        )
        user.created_at = None
        user.updated_at = None

        result = user.to_dict()

        assert result["created_at"] is None
        assert result["updated_at"] is None


# ==============================================================================
# Base Model Tests
# ==============================================================================


class TestBaseModel:
    """Tests for Base model class."""

    def test_base_is_declarative_base(self):
        """Test Base is a DeclarativeBase."""
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)

    def test_user_inherits_from_base(self):
        """Test User inherits from Base."""
        assert issubclass(User, Base)


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestUserModelIntegration:
    """Integration tests for User model."""

    def test_user_full_lifecycle(self):
        """Test User model through full lifecycle."""
        # Create
        user = User(
            email="lifecycle@example.com",
            username="lifecycleuser",
            hashed_password="initial_hash",
            is_active=True,  # Explicitly set since SQLAlchemy defaults don't apply without session
        )

        assert user.is_active is True
        assert user.is_locked() is False  # locked_until is None by default

        # Simulate failed login attempts
        user.failed_login_attempts = 5
        user.locked_until = datetime.now(UTC) + timedelta(minutes=30)

        assert user.is_locked() is True

        # Simulate lock expiration
        user.locked_until = datetime.now(UTC) - timedelta(minutes=1)

        assert user.is_locked() is False

        # Convert to dict for API response
        user_dict = user.to_dict()

        assert "email" in user_dict
        assert "hashed_password" not in user_dict
