"""Comprehensive tests for auth security utilities.

Tests cover:
- Password hashing with bcrypt
- Password verification
- Password strength validation
- JWT token creation and decoding
- Security configuration
"""

from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest

from feishu_webhook_bot.auth.security import (
    calculate_password_strength,
    create_access_token,
    decode_access_token,
    get_algorithm,
    get_password_hash,
    get_secret_key,
    get_token_expire_minutes,
    update_security_config,
    validate_password_strength,
    verify_password,
)


# ==============================================================================
# Password Hashing Tests
# ==============================================================================


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_get_password_hash_returns_string(self):
        """Test get_password_hash returns a string."""
        hashed = get_password_hash("testpassword")
        assert isinstance(hashed, str)

    def test_get_password_hash_bcrypt_format(self):
        """Test hash is in bcrypt format."""
        hashed = get_password_hash("testpassword")
        # bcrypt hashes start with $2a$, $2b$, or $2y$
        assert hashed.startswith("$2")

    def test_get_password_hash_different_for_same_password(self):
        """Test same password produces different hashes (due to salt)."""
        hash1 = get_password_hash("samepassword")
        hash2 = get_password_hash("samepassword")
        assert hash1 != hash2

    def test_get_password_hash_non_string_raises(self):
        """Test non-string password raises TypeError."""
        with pytest.raises(TypeError):
            get_password_hash(12345)  # type: ignore

    def test_get_password_hash_too_long_raises(self):
        """Test password over 72 bytes raises ValueError."""
        long_password = "a" * 100  # Over 72 bytes
        with pytest.raises(ValueError, match="too long"):
            get_password_hash(long_password)


class TestPasswordVerification:
    """Tests for password verification."""

    def test_verify_password_correct(self):
        """Test correct password verification."""
        password = "correctpassword"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test incorrect password verification."""
        hashed = get_password_hash("correctpassword")

        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_non_string_plain(self):
        """Test non-string plain password returns False."""
        hashed = get_password_hash("test")
        assert verify_password(12345, hashed) is False  # type: ignore

    def test_verify_password_non_string_hash(self):
        """Test non-string hash returns False."""
        assert verify_password("test", 12345) is False  # type: ignore

    def test_verify_password_malformed_hash(self):
        """Test malformed hash returns False."""
        assert verify_password("test", "not-a-valid-hash") is False

    def test_verify_password_too_long_plain(self):
        """Test password over 72 bytes returns False."""
        hashed = get_password_hash("short")
        long_password = "a" * 100
        assert verify_password(long_password, hashed) is False


# ==============================================================================
# Password Strength Validation Tests
# ==============================================================================


class TestPasswordStrengthValidation:
    """Tests for password strength validation."""

    def test_validate_strong_password(self):
        """Test strong password passes validation."""
        is_valid, errors = validate_password_strength("StrongP@ss123")
        assert is_valid is True
        assert errors == []

    def test_validate_too_short(self):
        """Test password too short fails."""
        is_valid, errors = validate_password_strength("Sh0rt!")
        assert is_valid is False
        assert any("8 characters" in e for e in errors)

    def test_validate_missing_uppercase(self):
        """Test missing uppercase fails."""
        is_valid, errors = validate_password_strength("lowercase123!")
        assert is_valid is False
        assert any("uppercase" in e for e in errors)

    def test_validate_missing_lowercase(self):
        """Test missing lowercase fails."""
        is_valid, errors = validate_password_strength("UPPERCASE123!")
        assert is_valid is False
        assert any("lowercase" in e for e in errors)

    def test_validate_missing_digit(self):
        """Test missing digit fails."""
        is_valid, errors = validate_password_strength("NoDigits!@#")
        assert is_valid is False
        assert any("digit" in e for e in errors)

    def test_validate_missing_special(self):
        """Test missing special character fails."""
        is_valid, errors = validate_password_strength("NoSpecial123")
        assert is_valid is False
        assert any("special" in e for e in errors)

    def test_validate_multiple_failures(self):
        """Test multiple validation failures."""
        is_valid, errors = validate_password_strength("weak")
        assert is_valid is False
        assert len(errors) >= 3


class TestPasswordStrengthCalculation:
    """Tests for password strength calculation."""

    def test_calculate_weak_password(self):
        """Test weak password gets low score."""
        result = calculate_password_strength("weak")
        assert result["level"] == "weak"
        assert result["score"] < 40

    def test_calculate_medium_password(self):
        """Test medium password gets medium score."""
        result = calculate_password_strength("Medium123")
        assert result["level"] in ["weak", "medium"]

    def test_calculate_strong_password(self):
        """Test strong password gets high score."""
        result = calculate_password_strength("VeryStr0ng!Pass")
        assert result["level"] == "strong"
        assert result["score"] >= 70

    def test_calculate_provides_feedback(self):
        """Test calculation provides improvement feedback."""
        result = calculate_password_strength("onlylowercase")
        assert "feedback" in result
        assert len(result["feedback"]) > 0

    def test_calculate_score_capped_at_100(self):
        """Test score is capped at 100."""
        result = calculate_password_strength("VeryVeryStr0ng!Password123")
        assert result["score"] <= 100


# ==============================================================================
# JWT Token Tests
# ==============================================================================


class TestJWTTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token_returns_string(self):
        """Test create_access_token returns a string."""
        token = create_access_token({"sub": "user@example.com"})
        assert isinstance(token, str)

    def test_create_access_token_with_data(self):
        """Test token contains encoded data."""
        data = {"sub": "user@example.com", "role": "admin"}
        token = create_access_token(data)

        # Decode and verify
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user@example.com"
        assert decoded["role"] == "admin"

    def test_create_access_token_has_expiration(self):
        """Test token has expiration claim."""
        token = create_access_token({"sub": "user"})
        decoded = decode_access_token(token)

        assert decoded is not None
        assert "exp" in decoded

    def test_create_access_token_custom_expiration(self):
        """Test token with custom expiration."""
        token = create_access_token(
            {"sub": "user"},
            expires_delta=timedelta(hours=2),
        )
        decoded = decode_access_token(token)

        assert decoded is not None
        assert "exp" in decoded


class TestJWTTokenDecoding:
    """Tests for JWT token decoding."""

    def test_decode_valid_token(self):
        """Test decoding valid token."""
        token = create_access_token({"sub": "user123"})
        decoded = decode_access_token(token)

        assert decoded is not None
        assert decoded["sub"] == "user123"

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        decoded = decode_access_token("invalid.token.here")
        assert decoded is None

    def test_decode_tampered_token(self):
        """Test decoding tampered token returns None."""
        token = create_access_token({"sub": "user"})
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"

        decoded = decode_access_token(tampered)
        assert decoded is None


# ==============================================================================
# Security Configuration Tests
# ==============================================================================


class TestSecurityConfiguration:
    """Tests for security configuration functions."""

    def test_get_secret_key_from_env(self):
        """Test get_secret_key reads from environment."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "env-secret-key"}):
            key = get_secret_key(None)
            assert key == "env-secret-key"

    def test_get_secret_key_default(self):
        """Test get_secret_key returns default when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove JWT_SECRET_KEY if present
            os.environ.pop("JWT_SECRET_KEY", None)
            key = get_secret_key(None)
            assert key is not None

    def test_get_algorithm_default(self):
        """Test get_algorithm returns default."""
        algo = get_algorithm(None)
        assert algo == "HS256"

    def test_get_token_expire_minutes_default(self):
        """Test get_token_expire_minutes returns default."""
        minutes = get_token_expire_minutes(None)
        assert minutes == 30

    def test_update_security_config(self):
        """Test update_security_config updates module variables."""
        # Save original values
        from feishu_webhook_bot.auth import security
        original_key = security.SECRET_KEY
        original_algo = security.ALGORITHM
        original_expire = security.ACCESS_TOKEN_EXPIRE_MINUTES

        try:
            update_security_config(
                secret_key="new-secret",
                algorithm="HS512",
                token_expire_minutes=60,
            )

            assert security.SECRET_KEY == "new-secret"
            assert security.ALGORITHM == "HS512"
            assert security.ACCESS_TOKEN_EXPIRE_MINUTES == 60
        finally:
            # Restore original values
            security.SECRET_KEY = original_key
            security.ALGORITHM = original_algo
            security.ACCESS_TOKEN_EXPIRE_MINUTES = original_expire


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestSecurityIntegration:
    """Integration tests for security module."""

    def test_full_password_flow(self):
        """Test complete password hash and verify flow."""
        password = "MySecure@Pass123"

        # Validate strength
        is_valid, errors = validate_password_strength(password)
        assert is_valid is True

        # Hash password
        hashed = get_password_hash(password)

        # Verify correct password
        assert verify_password(password, hashed) is True

        # Verify wrong password
        assert verify_password("wrong", hashed) is False

    def test_full_token_flow(self):
        """Test complete token creation and validation flow."""
        user_data = {
            "sub": "user@example.com",
            "user_id": 123,
            "roles": ["admin", "user"],
        }

        # Create token
        token = create_access_token(user_data)

        # Decode and verify
        decoded = decode_access_token(token)

        assert decoded is not None
        assert decoded["sub"] == user_data["sub"]
        assert decoded["user_id"] == user_data["user_id"]
        assert decoded["roles"] == user_data["roles"]
