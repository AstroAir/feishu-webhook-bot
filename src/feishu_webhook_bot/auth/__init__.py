"""Authentication module for Feishu Webhook Bot.

This module provides user authentication and authorization functionality including:
- User registration and login
- Password hashing and verification
- JWT token management
- Session management
- Rate limiting for security
"""

from .models import User
from .security import (
    create_access_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from .service import AuthService

__all__ = [
    "User",
    "AuthService",
    "get_password_hash",
    "verify_password",
    "validate_password_strength",
    "create_access_token",
]
