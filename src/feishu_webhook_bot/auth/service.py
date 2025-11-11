"""Authentication service layer for user management and authentication."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.exc import IntegrityError

from ..core.logger import get_logger
from .database import DatabaseManager
from .models import User
from .security import (
    create_access_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)

logger = get_logger("auth.service")

# Account lockout settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


class AuthenticationError(Exception):
    """Base exception for authentication errors."""

    pass


class RegistrationError(Exception):
    """Exception raised during user registration."""

    pass


class AuthService:
    """Service class for authentication operations.

    This class handles user registration, login, password validation,
    and account security features like lockout.
    """

    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        """Initialize the authentication service.

        Args:
            db_manager: Database manager instance (creates default if None)
        """
        self.db_manager = db_manager or DatabaseManager()

    def register_user(
        self, email: str, username: str, password: str, password_confirm: str
    ) -> User:
        """Register a new user.

        Args:
            email: User's email address
            username: Desired username
            password: Plain text password
            password_confirm: Password confirmation

        Returns:
            Created User object

        Raises:
            RegistrationError: If registration fails due to validation or duplicate user
        """
        # Validate passwords match
        if password != password_confirm:
            raise RegistrationError("Passwords do not match")

        # Validate password strength
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            raise RegistrationError("; ".join(errors))

        # Validate email format
        try:
            email_info = validate_email(email, check_deliverability=False)
            email = email_info.normalized
        except EmailNotValidError as e:
            raise RegistrationError(f"Invalid email address: {str(e)}") from e

        # Validate username
        if len(username) < 3:
            raise RegistrationError("Username must be at least 3 characters long")
        if len(username) > 50:
            raise RegistrationError("Username must be at most 50 characters long")
        if not username.replace("_", "").replace("-", "").isalnum():
            raise RegistrationError(
                "Username can only contain letters, numbers, hyphens, and underscores"
            )

        # Hash password
        hashed_password = get_password_hash(password)

        # Create user in database
        with self.db_manager.get_session() as session:
            user = User(
                email=email,
                username=username,
                hashed_password=hashed_password,
                is_active=True,
                is_verified=False,  # Email verification can be implemented later
            )

            try:
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"User registered successfully: {username} ({email})")
                return user
            except IntegrityError as e:
                session.rollback()
                # Check which constraint was violated
                error_msg = str(e.orig).lower()
                if "email" in error_msg:
                    raise RegistrationError("Email address already registered") from e
                elif "username" in error_msg:
                    raise RegistrationError("Username already taken") from e
                else:
                    raise RegistrationError("User already exists") from e

    def authenticate_user(self, login: str, password: str) -> tuple[User, str]:
        """Authenticate a user and return user object with access token.

        Args:
            login: Email or username
            password: Plain text password

        Returns:
            Tuple of (User object, JWT access token)

        Raises:
            AuthenticationError: If authentication fails
        """
        with self.db_manager.get_session() as session:
            # Find user by email or username
            user = (
                session.query(User).filter((User.email == login) | (User.username == login)).first()
            )

            if not user:
                logger.warning(f"Login attempt with non-existent user: {login}")
                raise AuthenticationError("Invalid credentials")

            # Check if account is locked
            if user.is_locked():
                logger.warning(f"Login attempt on locked account: {login}")
                raise AuthenticationError(
                    "Account is locked due to too many failed attempts. " "Please try again later."
                )

            # Check if account is active
            if not user.is_active:
                logger.warning(f"Login attempt on inactive account: {login}")
                raise AuthenticationError("Account is inactive")

            # Verify password
            if not verify_password(password, user.hashed_password):
                # Increment failed attempts
                user.failed_login_attempts += 1

                # Lock account if max attempts reached
                if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                    user.locked_until = datetime.now(UTC) + timedelta(
                        minutes=LOCKOUT_DURATION_MINUTES
                    )
                    logger.warning(
                        f"Account locked due to failed attempts: {login} "
                        f"(locked until {user.locked_until})"
                    )

                session.commit()
                logger.warning(
                    f"Failed login attempt for {login} "
                    f"(attempt {user.failed_login_attempts}/{MAX_FAILED_ATTEMPTS})"
                )
                raise AuthenticationError("Invalid credentials")

            # Successful login - reset failed attempts
            user.failed_login_attempts = 0
            user.locked_until = None
            session.commit()

            # Create access token
            token_data = {"sub": user.email, "username": user.username, "user_id": user.id}
            access_token = create_access_token(token_data)

            logger.info(f"User authenticated successfully: {login}")
            return user, access_token

    def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User's email address

        Returns:
            User object if found, None otherwise
        """
        with self.db_manager.get_session() as session:
            return session.query(User).filter(User.email == email).first()

    def get_user_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username: User's username

        Returns:
            User object if found, None otherwise
        """
        with self.db_manager.get_session() as session:
            return session.query(User).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID.

        Args:
            user_id: User's ID

        Returns:
            User object if found, None otherwise
        """
        with self.db_manager.get_session() as session:
            return session.query(User).filter(User.id == user_id).first()

    def verify_email(self, user_id: int) -> bool:
        """Mark user's email as verified.

        Args:
            user_id: User's ID

        Returns:
            True if successful, False otherwise
        """
        with self.db_manager.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.is_verified = True
                session.commit()
                logger.info(f"Email verified for user: {user.username}")
                return True
            return False

    def unlock_account(self, user_id: int) -> bool:
        """Manually unlock a user account.

        Args:
            user_id: User's ID

        Returns:
            True if successful, False otherwise
        """
        with self.db_manager.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.failed_login_attempts = 0
                user.locked_until = None
                session.commit()
                logger.info(f"Account unlocked: {user.username}")
                return True
            return False
