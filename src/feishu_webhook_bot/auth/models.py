"""Database models for authentication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class User(Base):
    """User model for authentication.

    Attributes:
        id: Primary key
        email: User's email address (unique)
        username: User's username (unique)
        hashed_password: Bcrypt hashed password
        is_active: Whether the user account is active
        is_verified: Whether the user's email is verified
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        failed_login_attempts: Number of consecutive failed login attempts
        locked_until: Timestamp until which the account is locked (None if not locked)
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    def is_locked(self) -> bool:
        """Check if the account is currently locked.

        Returns:
            True if account is locked, False otherwise
        """
        if self.locked_until is None:
            return False
        locked_until = self.locked_until
        # SQLite may return naive datetimes even when timezone=True is set; default to UTC.
        if locked_until.tzinfo is None or locked_until.tzinfo.utcoffset(locked_until) is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < locked_until

    def to_dict(self) -> dict[str, Any]:
        """Convert user to dictionary (excluding sensitive data).

        Returns:
            Dictionary representation of user
        """
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

