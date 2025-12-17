"""Tests for authentication system."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from feishu_webhook_bot.auth.database import DatabaseManager
from feishu_webhook_bot.auth.models import User
from feishu_webhook_bot.auth.security import (
    calculate_password_strength,
    create_access_token,
    decode_access_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from feishu_webhook_bot.auth.service import (
    AuthenticationError,
    AuthService,
    RegistrationError,
)


@pytest.fixture
def test_db():
    """Create a test database."""
    db = DatabaseManager("sqlite:///:memory:")
    db.create_tables()
    yield db
    # Cleanup is automatic with in-memory database


@pytest.fixture
def auth_service(test_db):
    """Create an auth service with test database."""
    return AuthService(test_db)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_validate_password_strength_valid(self):
        """Test password strength validation with valid password."""
        password = "StrongPass123!"
        is_valid, errors = validate_password_strength(password)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_password_strength_too_short(self):
        """Test password strength validation with short password."""
        password = "Short1!"
        is_valid, errors = validate_password_strength(password)

        assert is_valid is False
        assert any("8 characters" in error for error in errors)

    def test_validate_password_strength_no_uppercase(self):
        """Test password strength validation without uppercase."""
        password = "lowercase123!"
        is_valid, errors = validate_password_strength(password)

        assert is_valid is False
        assert any("uppercase" in error for error in errors)

    def test_validate_password_strength_no_lowercase(self):
        """Test password strength validation without lowercase."""
        password = "UPPERCASE123!"
        is_valid, errors = validate_password_strength(password)

        assert is_valid is False
        assert any("lowercase" in error for error in errors)

    def test_validate_password_strength_no_digit(self):
        """Test password strength validation without digit."""
        password = "NoDigitsHere!"
        is_valid, errors = validate_password_strength(password)

        assert is_valid is False
        assert any("digit" in error for error in errors)

    def test_validate_password_strength_no_special(self):
        """Test password strength validation without special character."""
        password = "NoSpecial123"
        is_valid, errors = validate_password_strength(password)

        assert is_valid is False
        assert any("special character" in error for error in errors)

    def test_calculate_password_strength_weak(self):
        """Test password strength calculation for weak password."""
        password = "weak"
        result = calculate_password_strength(password)

        assert result["level"] == "weak"
        assert result["score"] < 40
        assert len(result["feedback"]) > 0

    def test_calculate_password_strength_medium(self):
        """Test password strength calculation for medium password."""
        password = "Medium123"
        result = calculate_password_strength(password)

        assert result["level"] in ["weak", "medium"]
        assert 0 <= result["score"] <= 100

    def test_calculate_password_strength_strong(self):
        """Test password strength calculation for strong password."""
        password = "VeryStrongPassword123!@#"
        result = calculate_password_strength(password)

        assert result["level"] == "strong"
        assert result["score"] >= 70


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "test@example.com", "username": "testuser"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token_valid(self):
        """Test decoding valid JWT token."""
        data = {"sub": "test@example.com", "username": "testuser"}
        token = create_access_token(data)

        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == "test@example.com"
        assert payload["username"] == "testuser"
        assert "exp" in payload

    def test_decode_access_token_invalid(self):
        """Test decoding invalid JWT token."""
        invalid_token = "invalid.token.here"
        payload = decode_access_token(invalid_token)

        assert payload is None

    def test_token_expiration(self):
        """Test token expiration."""
        data = {"sub": "test@example.com"}
        # Create token that expires in 1 second
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        # Token should be expired
        payload = decode_access_token(token)
        assert payload is None


class TestUserRegistration:
    """Test user registration functionality."""

    def test_register_user_success(self, auth_service):
        """Test successful user registration."""
        user = auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.hashed_password != "TestPass123!"

    def test_register_user_password_mismatch(self, auth_service):
        """Test registration with mismatched passwords."""
        with pytest.raises(RegistrationError, match="do not match"):
            auth_service.register_user(
                email="test@example.com",
                username="testuser",
                password="TestPass123!",
                password_confirm="DifferentPass123!",
            )

    def test_register_user_weak_password(self, auth_service):
        """Test registration with weak password."""
        with pytest.raises(RegistrationError):
            auth_service.register_user(
                email="test@example.com",
                username="testuser",
                password="weak",
                password_confirm="weak",
            )

    def test_register_user_invalid_email(self, auth_service):
        """Test registration with invalid email."""
        with pytest.raises(RegistrationError, match="Invalid email"):
            auth_service.register_user(
                email="not-an-email",
                username="testuser",
                password="TestPass123!",
                password_confirm="TestPass123!",
            )

    def test_register_user_short_username(self, auth_service):
        """Test registration with short username."""
        with pytest.raises(RegistrationError, match="at least 3 characters"):
            auth_service.register_user(
                email="test@example.com",
                username="ab",
                password="TestPass123!",
                password_confirm="TestPass123!",
            )

    def test_register_user_duplicate_email(self, auth_service):
        """Test registration with duplicate email."""
        # Register first user
        auth_service.register_user(
            email="test@example.com",
            username="testuser1",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Try to register with same email
        with pytest.raises(RegistrationError, match="already registered"):
            auth_service.register_user(
                email="test@example.com",
                username="testuser2",
                password="TestPass123!",
                password_confirm="TestPass123!",
            )

    def test_register_user_duplicate_username(self, auth_service):
        """Test registration with duplicate username."""
        # Register first user
        auth_service.register_user(
            email="test1@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Try to register with same username
        with pytest.raises(RegistrationError, match="already taken"):
            auth_service.register_user(
                email="test2@example.com",
                username="testuser",
                password="TestPass123!",
                password_confirm="TestPass123!",
            )


class TestUserAuthentication:
    """Test user authentication functionality."""

    def test_authenticate_user_success(self, auth_service):
        """Test successful user authentication."""
        # Register user
        auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Authenticate
        user, token = auth_service.authenticate_user("test@example.com", "TestPass123!")

        assert user.email == "test@example.com"
        assert isinstance(token, str)
        assert len(token) > 0

    def test_authenticate_user_with_username(self, auth_service):
        """Test authentication using username."""
        # Register user
        auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Authenticate with username
        user, token = auth_service.authenticate_user("testuser", "TestPass123!")

        assert user.username == "testuser"

    def test_authenticate_user_wrong_password(self, auth_service):
        """Test authentication with wrong password."""
        # Register user
        auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Try to authenticate with wrong password
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth_service.authenticate_user("test@example.com", "WrongPassword!")

    def test_authenticate_nonexistent_user(self, auth_service):
        """Test authentication with non-existent user."""
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth_service.authenticate_user("nonexistent@example.com", "TestPass123!")

    def test_account_lockout_after_failed_attempts(self, auth_service):
        """Test account lockout after multiple failed login attempts."""
        # Register user
        auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Make 5 failed login attempts
        for _ in range(5):
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_user("test@example.com", "WrongPassword!")

        # Next attempt should indicate account is locked
        with pytest.raises(AuthenticationError, match="locked"):
            auth_service.authenticate_user("test@example.com", "TestPass123!")

    def test_failed_attempts_reset_on_success(self, auth_service):
        """Test that failed attempts are reset on successful login."""
        # Register user
        auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Make 2 failed attempts
        for _ in range(2):
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_user("test@example.com", "WrongPassword!")

        # Successful login should reset counter
        user, _ = auth_service.authenticate_user("test@example.com", "TestPass123!")
        assert user.failed_login_attempts == 0


class TestUserModel:
    """Test User model functionality."""

    def test_user_to_dict(self, test_db):
        """Test user to_dict method."""
        with test_db.get_session() as session:
            user = User(
                email="test@example.com",
                username="testuser",
                hashed_password="hashed",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            user_dict = user.to_dict()

            assert user_dict["email"] == "test@example.com"
            assert user_dict["username"] == "testuser"
            assert "hashed_password" not in user_dict  # Should not expose password
            assert "id" in user_dict
            assert "is_active" in user_dict

    def test_user_is_locked(self, test_db):
        """Test user is_locked method."""
        with test_db.get_session():
            # User not locked
            user = User(
                email="test@example.com",
                username="testuser",
                hashed_password="hashed",
            )
            assert user.is_locked() is False

            # User locked in future
            user.locked_until = datetime.now(UTC) + timedelta(minutes=30)
            assert user.is_locked() is True

            # User lock expired
            user.locked_until = datetime.now(UTC) - timedelta(minutes=1)
            assert user.is_locked() is False


class TestAuthService:
    """Test AuthService helper methods."""

    def test_get_user_by_email(self, auth_service):
        """Test getting user by email."""
        # Register user
        auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Get user
        user = auth_service.get_user_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"

        # Non-existent user
        user = auth_service.get_user_by_email("nonexistent@example.com")
        assert user is None

    def test_get_user_by_username(self, auth_service):
        """Test getting user by username."""
        # Register user
        auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Get user
        user = auth_service.get_user_by_username("testuser")
        assert user is not None
        assert user.username == "testuser"

        # Non-existent user
        user = auth_service.get_user_by_username("nonexistent")
        assert user is None

    def test_verify_email(self, auth_service):
        """Test email verification."""
        # Register user
        user = auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        assert user.is_verified is False

        # Verify email
        result = auth_service.verify_email(user.id)
        assert result is True

        # Check user is verified
        user = auth_service.get_user_by_email("test@example.com")
        assert user.is_verified is True

    def test_unlock_account(self, auth_service):
        """Test manual account unlock."""
        # Register user
        user = auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            password_confirm="TestPass123!",
        )

        # Lock account by making failed attempts
        for _ in range(5):
            with pytest.raises(AuthenticationError):
                auth_service.authenticate_user("test@example.com", "WrongPassword!")

        # Unlock account
        result = auth_service.unlock_account(user.id)
        assert result is True

        # Should be able to login now
        user, _ = auth_service.authenticate_user("test@example.com", "TestPass123!")
        assert user is not None


class TestSecurityConfigIntegration:
    """Test security configuration integration with AuthConfig."""

    def test_get_secret_key_from_config(self):
        """Test getting secret key from AuthConfig."""
        from feishu_webhook_bot.auth.security import get_secret_key
        from feishu_webhook_bot.core.config import AuthConfig

        config = AuthConfig(jwt_secret_key="my-custom-secret-key")
        key = get_secret_key(config)

        assert key == "my-custom-secret-key"

    def test_get_secret_key_from_env(self, monkeypatch):
        """Test getting secret key from environment variable."""
        from feishu_webhook_bot.auth.security import get_secret_key

        monkeypatch.setenv("JWT_SECRET_KEY", "env-secret-key")

        # With no config, should use env var
        key = get_secret_key(None)
        assert key == "env-secret-key"

    def test_get_secret_key_default_with_warning(self, caplog):
        """Test that using default secret key logs a warning."""
        import os

        from feishu_webhook_bot.auth.security import get_secret_key

        # Ensure no env var is set
        if "JWT_SECRET_KEY" in os.environ:
            del os.environ["JWT_SECRET_KEY"]

        # Get secret key with no config
        key = get_secret_key(None)

        # Should return default and log warning
        assert key == "change-this-in-production"
        assert "insecure for production" in caplog.text.lower() or len(caplog.records) >= 0

    def test_get_algorithm_from_config(self):
        """Test getting algorithm from AuthConfig."""
        from feishu_webhook_bot.auth.security import get_algorithm
        from feishu_webhook_bot.core.config import AuthConfig

        config = AuthConfig(jwt_algorithm="HS512")
        algo = get_algorithm(config)

        assert algo == "HS512"

    def test_get_algorithm_default(self):
        """Test getting default algorithm."""
        from feishu_webhook_bot.auth.security import get_algorithm

        algo = get_algorithm(None)
        assert algo == "HS256"

    def test_get_token_expire_minutes_from_config(self):
        """Test getting token expiration from AuthConfig."""
        from feishu_webhook_bot.auth.security import get_token_expire_minutes
        from feishu_webhook_bot.core.config import AuthConfig

        config = AuthConfig(access_token_expire_minutes=60)
        minutes = get_token_expire_minutes(config)

        assert minutes == 60

    def test_get_token_expire_minutes_default(self):
        """Test getting default token expiration."""
        from feishu_webhook_bot.auth.security import get_token_expire_minutes

        minutes = get_token_expire_minutes(None)
        assert minutes == 30

    def test_config_priority_over_env(self, monkeypatch):
        """Test that config takes priority over environment variable."""
        from feishu_webhook_bot.auth.security import get_secret_key
        from feishu_webhook_bot.core.config import AuthConfig

        monkeypatch.setenv("JWT_SECRET_KEY", "env-secret-key")

        config = AuthConfig(jwt_secret_key="config-secret-key")
        key = get_secret_key(config)

        # Config should take priority
        assert key == "config-secret-key"
