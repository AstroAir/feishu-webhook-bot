"""Security utilities for password hashing and JWT token management."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from ..core.logger import get_logger

logger = get_logger("auth.security")

# JWT settings (these should be configurable via config)
SECRET_KEY = "your-secret-key-change-this-in-production"  # TODO: Move to config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt (direct backend), avoiding passlib compatibility issues.

    Args:
        password: Plain text password

    Returns:
        Hashed password string (bcrypt, typically starting with "$2b$")
    """
    if not isinstance(password, str):  # defensive
        raise TypeError("password must be a string")

    encoded_password = password.encode("utf-8")
    # bcrypt enforces a 72-byte limit; guard here so callers can surface a friendly error.
    if len(encoded_password) > 72:
        raise ValueError("Password is too long for bcrypt hashing (max 72 UTF-8 bytes)")

    salt = bcrypt.gensalt()  # default rounds=12
    hashed = bcrypt.hashpw(encoded_password, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    try:
        encoded_plain = plain_password.encode("utf-8")
        if len(encoded_plain) > 72:
            return False
        return bcrypt.checkpw(encoded_plain, hashed_password.encode("utf-8"))
    except ValueError:
        # covers malformed hashes
        return False


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """Validate password strength according to security requirements.

    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, list_of_errors)

    Example:
        ```python
        is_valid, errors = validate_password_strength("weak")
        if not is_valid:
            print("Password errors:", errors)
        ```
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


def calculate_password_strength(password: str) -> dict[str, Any]:
    """Calculate password strength score and provide feedback.

    Args:
        password: Password to evaluate

    Returns:
        Dictionary with strength score (0-100) and feedback

    Example:
        ```python
        result = calculate_password_strength("MyPass123!")
        print(f"Strength: {result['score']}% - {result['level']}")
        ```
    """
    score = 0
    feedback = []

    # Length scoring
    length = len(password)
    if length >= 8:
        score += 20
    if length >= 12:
        score += 10
    if length >= 16:
        score += 10

    # Character variety scoring
    if re.search(r"[a-z]", password):
        score += 15
    else:
        feedback.append("Add lowercase letters")

    if re.search(r"[A-Z]", password):
        score += 15
    else:
        feedback.append("Add uppercase letters")

    if re.search(r"\d", password):
        score += 15
    else:
        feedback.append("Add numbers")

    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 15
    else:
        feedback.append("Add special characters")

    # Determine strength level
    if score < 40:
        level = "weak"
    elif score < 70:
        level = "medium"
    else:
        level = "strong"

    return {"score": min(score, 100), "level": level, "feedback": feedback}


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token (typically user_id, username, etc.)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        ```python
        token = create_access_token({"sub": "user@example.com"})
        ```
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload if valid, None otherwise

    Example:
        ```python
        payload = decode_access_token(token)
        if payload:
            user_email = payload.get("sub")
        ```
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def update_security_config(
    secret_key: str, algorithm: str = "HS256", token_expire_minutes: int = 30
) -> None:
    """Update JWT security configuration.

    This should be called during application initialization with values from config.

    Args:
        secret_key: Secret key for JWT encoding
        algorithm: JWT algorithm (default: HS256)
        token_expire_minutes: Token expiration time in minutes

    Example:
        ```python
        update_security_config(
            secret_key="my-super-secret-key",
            token_expire_minutes=60
        )
        ```
    """
    global SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
    SECRET_KEY = secret_key
    ALGORITHM = algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES = token_expire_minutes
    logger.info(
        f"Security config updated: algorithm={algorithm}, token_expire={token_expire_minutes}min"
    )
