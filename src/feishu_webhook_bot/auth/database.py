"""Database connection and session management for authentication."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.logger import get_logger
from .models import Base

logger = get_logger("auth.database")


class DatabaseManager:
    """Manages database connections and sessions for authentication.

    Default usage is a singleton (when no database_url is provided).
    When a database_url is explicitly provided (e.g., for tests with
    'sqlite:///:memory:'), a fresh instance with its own engine is created.
    """

    _instance: DatabaseManager | None = None

    def __new__(cls, database_url: str | None = None) -> DatabaseManager:
        """Create or return the singleton instance.

        - If database_url is None, return the shared singleton instance.
        - If database_url is provided, return a new independent instance.
        """
        if database_url is None:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
        # Explicit URL -> new instance (useful for tests / isolation)
        return super().__new__(cls)

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize the database manager.

        Args:
            database_url: SQLAlchemy database URL
        """
        # Avoid re-initializing the singleton instance
        if getattr(self, "_initialized", False):
            return

        if database_url is None:
            # Default to SQLite in the project root
            database_url = "sqlite:///./auth.db"

        logger.info(f"Initializing database with URL: {database_url}")

        # Create engine with appropriate settings
        if database_url.startswith("sqlite"):
            # SQLite-specific settings
            self._engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},  # Allow multi-threading
                echo=False,  # Set to True for SQL debugging
            )
        else:
            self._engine = create_engine(database_url, echo=False)

        # Create session factory (keep instances usable after commit)
        self._session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            bind=self._engine,
        )

        self._initialized = True

    def create_tables(self) -> None:
        """Create all database tables if they don't exist."""
        if self._engine is None:
            raise RuntimeError("Database not initialized")

        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self._engine)
        logger.info("Database tables created successfully")

    def drop_tables(self) -> None:
        """Drop all database tables. Use with caution!"""
        if self._engine is None:
            raise RuntimeError("Database not initialized")

        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self._engine)
        logger.info("Database tables dropped")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup.

        Yields:
            SQLAlchemy Session object

        Example:
            ```python
            db = DatabaseManager()
            with db.get_session() as session:
                user = session.query(User).first()
            ```
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session_factory(self) -> sessionmaker:
        """Get the session factory for manual session management.

        Returns:
            SQLAlchemy sessionmaker

        Raises:
            RuntimeError: If database is not initialized
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")
        return self._session_factory


def init_database(database_url: str | None = None) -> DatabaseManager:
    """Initialize the database and create tables.

    Args:
        database_url: SQLAlchemy database URL (defaults to sqlite:///./auth.db)

    Returns:
        DatabaseManager instance

    Example:
        ```python
        db = init_database("sqlite:///./my_auth.db")
        ```
    """
    db = DatabaseManager(database_url)
    db.create_tables()
    return db


def get_db() -> Generator[Session, None, None]:
    """Dependency function for FastAPI to get database sessions.

    Yields:
        SQLAlchemy Session

    Example:
        ```python
        @app.post("/users")
        def create_user(db: Session = Depends(get_db)):
            # Use db session here
            pass
        ```
    """
    db_manager = DatabaseManager()
    with db_manager.get_session() as session:
        yield session

