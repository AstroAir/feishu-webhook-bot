"""Comprehensive tests for authentication service layer.

Tests cover:
- AuthService initialization
- User registration
- User authentication
- Account lockout
- User lookup methods
- Email verification
- Account unlocking
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.auth.database import DatabaseManager
from feishu_webhook_bot.auth.models import User
from feishu_webhook_bot.auth.service import (
    AuthenticationError,
    AuthService,
    RegistrationError,
)

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def db_manager():
    """Create a fresh in-memory database manager."""
    db = DatabaseManager("sqlite:///:memory:")
    db.create_tables()
    return db


@pytest.fixture
def auth_service(db_manager):
    """Create auth service with test database."""
    return AuthService(db_manager)


# ==============================================================================
# AuthService Initialization Tests
# ==============================================================================


class TestAuthServiceInitialization:
    """Tests for AuthService initialization."""

    def test_init_with_db_manager(self, db_manager):
        """Test initialization with provided database manager."""
        service = AuthService(db_manager)
        assert service.db_manager is db_manager

    def test_init_without_db_manager(self):
        """Test initialization creates default database manager."""
        with patch.object(DatabaseManager, "__new__") as mock_new:
            mock_db = MagicMock()
            mock_new.return_value = mock_db
            mock_db._initialized = False

            service = AuthService()
            assert service.db_manager is not None


# ==============================================================================
# User Registration Tests
# ==============================================================================


class TestUserRegistration:
    """Tests for user registration."""

    def test_register_user_success(self, auth_service):
        """Test successful user registration."""
        user = auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_verified is False

    def test_register_user_password_mismatch(self, auth_service):
        """Test registration fails when passwords don't match."""
        with pytest.raises(RegistrationError, match="do not match"):
            auth_service.register_user(
                email="test@example.com",
                username="testuser",
                password="StrongP@ss123",
                password_confirm="DifferentP@ss123",
            )

    def test_register_user_weak_password(self, auth_service):
        """Test registration fails with weak password."""
        with pytest.raises(RegistrationError):
            auth_service.register_user(
                email="test@example.com",
                username="testuser",
                password="weak",
                password_confirm="weak",
            )

    def test_register_user_invalid_email(self, auth_service):
        """Test registration fails with invalid email."""
        with pytest.raises(RegistrationError, match="Invalid email"):
            auth_service.register_user(
                email="not-an-email",
                username="testuser",
                password="StrongP@ss123",
                password_confirm="StrongP@ss123",
            )

    def test_register_user_short_username(self, auth_service):
        """Test registration fails with short username."""
        with pytest.raises(RegistrationError, match="at least 3"):
            auth_service.register_user(
                email="test@example.com",
                username="ab",
                password="StrongP@ss123",
                password_confirm="StrongP@ss123",
            )

    def test_register_user_long_username(self, auth_service):
        """Test registration fails with long username."""
        with pytest.raises(RegistrationError, match="at most 50"):
            auth_service.register_user(
                email="test@example.com",
                username="a" * 51,
                password="StrongP@ss123",
                password_confirm="StrongP@ss123",
            )

    def test_register_user_invalid_username_chars(self, auth_service):
        """Test registration fails with invalid username characters."""
        with pytest.raises(RegistrationError, match="letters, numbers"):
            auth_service.register_user(
                email="test@example.com",
                username="user@name!",
                password="StrongP@ss123",
                password_confirm="StrongP@ss123",
            )

    def test_register_user_duplicate_email(self, auth_service):
        """Test registration fails with duplicate email."""
        auth_service.register_user(
            email="test@example.com",
            username="testuser1",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

        with pytest.raises(RegistrationError, match="already registered"):
            auth_service.register_user(
                email="test@example.com",
                username="testuser2",
                password="StrongP@ss123",
                password_confirm="StrongP@ss123",
            )

    def test_register_user_duplicate_username(self, auth_service):
        """Test registration fails with duplicate username."""
        auth_service.register_user(
            email="test1@example.com",
            username="testuser",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

        with pytest.raises(RegistrationError, match="already taken"):
            auth_service.register_user(
                email="test2@example.com",
                username="testuser",
                password="StrongP@ss123",
                password_confirm="StrongP@ss123",
            )


# ==============================================================================
# User Authentication Tests
# ==============================================================================


class TestUserAuthentication:
    """Tests for user authentication."""

    @pytest.fixture
    def registered_user(self, auth_service):
        """Create a registered user for authentication tests."""
        return auth_service.register_user(
            email="auth@example.com",
            username="authuser",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

    def test_authenticate_with_email(self, auth_service, registered_user):
        """Test authentication with email."""
        user, token = auth_service.authenticate_user(
            login="auth@example.com",
            password="StrongP@ss123",
        )

        assert user.email == "auth@example.com"
        assert token is not None
        assert len(token) > 0

    def test_authenticate_with_username(self, auth_service, registered_user):
        """Test authentication with username."""
        user, token = auth_service.authenticate_user(
            login="authuser",
            password="StrongP@ss123",
        )

        assert user.username == "authuser"
        assert token is not None

    def test_authenticate_wrong_password(self, auth_service, registered_user):
        """Test authentication fails with wrong password."""
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth_service.authenticate_user(
                login="auth@example.com",
                password="WrongP@ss123",
            )

    def test_authenticate_nonexistent_user(self, auth_service):
        """Test authentication fails for nonexistent user."""
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth_service.authenticate_user(
                login="nonexistent@example.com",
                password="AnyP@ss123",
            )

    def test_authenticate_inactive_user(self, auth_service, db_manager):
        """Test authentication fails for inactive user."""
        # Create user and deactivate
        user = auth_service.register_user(
            email="inactive@example.com",
            username="inactiveuser",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

        with db_manager.get_session() as session:
            db_user = session.query(User).filter_by(id=user.id).first()
            db_user.is_active = False
            session.commit()

        with pytest.raises(AuthenticationError, match="inactive"):
            auth_service.authenticate_user(
                login="inactive@example.com",
                password="StrongP@ss123",
            )


# ==============================================================================
# Account Lockout Tests
# ==============================================================================


class TestAccountLockout:
    """Tests for account lockout functionality."""

    @pytest.fixture
    def registered_user(self, auth_service):
        """Create a registered user for lockout tests."""
        return auth_service.register_user(
            email="lockout@example.com",
            username="lockoutuser",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

    def test_failed_attempts_increment(self, auth_service, registered_user, db_manager):
        """Test failed login attempts are tracked."""
        # Fail once
        with pytest.raises(AuthenticationError):
            auth_service.authenticate_user(
                login="lockout@example.com",
                password="WrongP@ss",
            )

        with db_manager.get_session() as session:
            user = session.query(User).filter_by(email="lockout@example.com").first()
            assert user.failed_login_attempts == 1

    def test_account_locks_after_max_attempts(self, auth_service, registered_user, db_manager):
        """Test account locks after max failed attempts."""
        # Fail 5 times (default MAX_FAILED_ATTEMPTS)
        for _ in range(5):
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_user(
                    login="lockout@example.com",
                    password="WrongP@ss",
                )

        with db_manager.get_session() as session:
            user = session.query(User).filter_by(email="lockout@example.com").first()
            assert user.is_locked() is True

    def test_locked_account_rejects_login(self, auth_service, db_manager):
        """Test locked account rejects login even with correct password."""
        user = auth_service.register_user(
            email="locked@example.com",
            username="lockeduser",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

        # Lock the account
        with db_manager.get_session() as session:
            db_user = session.query(User).filter_by(id=user.id).first()
            db_user.locked_until = datetime.now(UTC) + timedelta(hours=1)
            session.commit()

        with pytest.raises(AuthenticationError, match="locked"):
            auth_service.authenticate_user(
                login="locked@example.com",
                password="StrongP@ss123",
            )

    def test_successful_login_resets_attempts(self, auth_service, registered_user, db_manager):
        """Test successful login resets failed attempts."""
        # Fail a few times
        for _ in range(3):
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_user(
                    login="lockout@example.com",
                    password="WrongP@ss",
                )

        # Successful login
        auth_service.authenticate_user(
            login="lockout@example.com",
            password="StrongP@ss123",
        )

        with db_manager.get_session() as session:
            user = session.query(User).filter_by(email="lockout@example.com").first()
            assert user.failed_login_attempts == 0


# ==============================================================================
# User Lookup Tests
# ==============================================================================


class TestUserLookup:
    """Tests for user lookup methods."""

    @pytest.fixture
    def registered_user(self, auth_service):
        """Create a registered user for lookup tests."""
        return auth_service.register_user(
            email="lookup@example.com",
            username="lookupuser",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

    def test_get_user_by_email(self, auth_service, registered_user):
        """Test getting user by email."""
        user = auth_service.get_user_by_email("lookup@example.com")

        assert user is not None
        assert user.email == "lookup@example.com"

    def test_get_user_by_email_not_found(self, auth_service):
        """Test getting nonexistent user by email."""
        user = auth_service.get_user_by_email("nonexistent@example.com")
        assert user is None

    def test_get_user_by_username(self, auth_service, registered_user):
        """Test getting user by username."""
        user = auth_service.get_user_by_username("lookupuser")

        assert user is not None
        assert user.username == "lookupuser"

    def test_get_user_by_username_not_found(self, auth_service):
        """Test getting nonexistent user by username."""
        user = auth_service.get_user_by_username("nonexistent")
        assert user is None

    def test_get_user_by_id(self, auth_service, registered_user):
        """Test getting user by ID."""
        user = auth_service.get_user_by_id(registered_user.id)

        assert user is not None
        assert user.id == registered_user.id

    def test_get_user_by_id_not_found(self, auth_service):
        """Test getting nonexistent user by ID."""
        user = auth_service.get_user_by_id(99999)
        assert user is None


# ==============================================================================
# Email Verification Tests
# ==============================================================================


class TestEmailVerification:
    """Tests for email verification."""

    def test_verify_email_success(self, auth_service):
        """Test successful email verification."""
        user = auth_service.register_user(
            email="verify@example.com",
            username="verifyuser",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

        assert user.is_verified is False

        result = auth_service.verify_email(user.id)

        assert result is True

        # Check user is now verified
        updated_user = auth_service.get_user_by_id(user.id)
        assert updated_user.is_verified is True

    def test_verify_email_nonexistent_user(self, auth_service):
        """Test email verification for nonexistent user."""
        result = auth_service.verify_email(99999)
        assert result is False


# ==============================================================================
# Account Unlocking Tests
# ==============================================================================


class TestAccountUnlocking:
    """Tests for account unlocking."""

    def test_unlock_account_success(self, auth_service, db_manager):
        """Test successful account unlocking."""
        user = auth_service.register_user(
            email="unlock@example.com",
            username="unlockuser",
            password="StrongP@ss123",
            password_confirm="StrongP@ss123",
        )

        # Lock the account
        with db_manager.get_session() as session:
            db_user = session.query(User).filter_by(id=user.id).first()
            db_user.failed_login_attempts = 5
            db_user.locked_until = datetime.now(UTC) + timedelta(hours=1)
            session.commit()

        result = auth_service.unlock_account(user.id)

        assert result is True

        # Check account is unlocked
        with db_manager.get_session() as session:
            db_user = session.query(User).filter_by(id=user.id).first()
            assert db_user.failed_login_attempts == 0
            assert db_user.locked_until is None

    def test_unlock_account_nonexistent_user(self, auth_service):
        """Test unlocking nonexistent user."""
        result = auth_service.unlock_account(99999)
        assert result is False
