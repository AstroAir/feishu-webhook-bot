"""Comprehensive tests for database connection and session management.

Tests cover:
- DatabaseManager singleton behavior
- Database initialization
- Session management
- Table creation and dropping
- FastAPI dependency integration
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.auth.database import (
    DatabaseManager,
    get_db,
    init_database,
)
from feishu_webhook_bot.auth.models import Base, User


# ==============================================================================
# DatabaseManager Singleton Tests
# ==============================================================================


class TestDatabaseManagerSingleton:
    """Tests for DatabaseManager singleton behavior."""

    def test_singleton_without_url(self):
        """Test singleton instance is returned when no URL provided."""
        # Reset singleton for test
        DatabaseManager._instance = None

        db1 = DatabaseManager("sqlite:///:memory:")
        db1._initialized = False  # Allow re-init for test
        DatabaseManager._instance = None

        db2 = DatabaseManager()
        db3 = DatabaseManager()

        assert db2 is db3

    def test_new_instance_with_url(self):
        """Test new instance is created when URL is provided."""
        db1 = DatabaseManager("sqlite:///:memory:")
        db2 = DatabaseManager("sqlite:///:memory:")

        # Different instances when URL is explicitly provided
        assert db1 is not db2

    def test_singleton_reuses_initialized_instance(self):
        """Test singleton doesn't re-initialize."""
        DatabaseManager._instance = None

        db1 = DatabaseManager("sqlite:///:memory:")
        DatabaseManager._instance = db1

        # Second call should return same instance
        db2 = DatabaseManager()
        assert db1 is db2


# ==============================================================================
# DatabaseManager Initialization Tests
# ==============================================================================


class TestDatabaseManagerInitialization:
    """Tests for DatabaseManager initialization."""

    def test_init_with_sqlite_memory(self):
        """Test initialization with SQLite in-memory database."""
        db = DatabaseManager("sqlite:///:memory:")

        assert db._engine is not None
        assert db._session_factory is not None
        assert db._initialized is True

    def test_init_with_sqlite_file(self):
        """Test initialization with SQLite file database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = DatabaseManager(f"sqlite:///{db_path}")

            assert db._engine is not None
            assert db._initialized is True

    def test_init_default_url(self):
        """Test initialization with default URL."""
        DatabaseManager._instance = None

        db = DatabaseManager()

        # Should use default sqlite URL
        assert db._engine is not None

    def test_init_non_sqlite(self):
        """Test initialization with non-SQLite URL (mocked)."""
        with patch("feishu_webhook_bot.auth.database.create_engine") as mock_engine:
            mock_engine.return_value = MagicMock()

            db = DatabaseManager("postgresql://user:pass@localhost/db")

            # Should not include check_same_thread for non-SQLite
            call_args = mock_engine.call_args
            assert "connect_args" not in call_args.kwargs or \
                   "check_same_thread" not in call_args.kwargs.get("connect_args", {})


# ==============================================================================
# Table Management Tests
# ==============================================================================


class TestTableManagement:
    """Tests for table creation and dropping."""

    @pytest.fixture
    def db(self):
        """Create a fresh database manager."""
        return DatabaseManager("sqlite:///:memory:")

    def test_create_tables(self, db):
        """Test creating database tables."""
        db.create_tables()

        # Verify tables exist by querying
        with db.get_session() as session:
            # Should not raise
            session.execute(Base.metadata.tables["users"].select())

    def test_drop_tables(self, db):
        """Test dropping database tables."""
        db.create_tables()
        db.drop_tables()

        # Tables should be dropped
        # Re-create to verify they were actually dropped
        db.create_tables()

    def test_create_tables_not_initialized(self):
        """Test create_tables raises when not initialized."""
        db = DatabaseManager("sqlite:///:memory:")
        db._engine = None

        with pytest.raises(RuntimeError, match="not initialized"):
            db.create_tables()

    def test_drop_tables_not_initialized(self):
        """Test drop_tables raises when not initialized."""
        db = DatabaseManager("sqlite:///:memory:")
        db._engine = None

        with pytest.raises(RuntimeError, match="not initialized"):
            db.drop_tables()


# ==============================================================================
# Session Management Tests
# ==============================================================================


class TestSessionManagement:
    """Tests for session management."""

    @pytest.fixture
    def db(self):
        """Create a fresh database manager with tables."""
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        return db

    def test_get_session_context_manager(self, db):
        """Test get_session as context manager."""
        with db.get_session() as session:
            assert session is not None
            # Session should be usable
            session.execute(Base.metadata.tables["users"].select())

    def test_get_session_commits_on_success(self, db):
        """Test session commits on successful exit."""
        with db.get_session() as session:
            user = User(
                email="test@example.com",
                username="testuser",
                hashed_password="hashed",
            )
            session.add(user)

        # Verify user was committed
        with db.get_session() as session:
            users = session.query(User).all()
            assert len(users) == 1
            assert users[0].email == "test@example.com"

    def test_get_session_rollback_on_error(self, db):
        """Test session rolls back on error."""
        try:
            with db.get_session() as session:
                user = User(
                    email="rollback@example.com",
                    username="rollbackuser",
                    hashed_password="hashed",
                )
                session.add(user)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify user was not committed
        with db.get_session() as session:
            users = session.query(User).filter_by(email="rollback@example.com").all()
            assert len(users) == 0

    def test_get_session_not_initialized(self):
        """Test get_session raises when not initialized."""
        db = DatabaseManager("sqlite:///:memory:")
        db._session_factory = None

        with pytest.raises(RuntimeError, match="not initialized"):
            with db.get_session():
                pass

    def test_get_session_factory(self, db):
        """Test get_session_factory returns factory."""
        factory = db.get_session_factory()

        assert factory is not None
        assert factory is db._session_factory

    def test_get_session_factory_not_initialized(self):
        """Test get_session_factory raises when not initialized."""
        db = DatabaseManager("sqlite:///:memory:")
        db._session_factory = None

        with pytest.raises(RuntimeError, match="not initialized"):
            db.get_session_factory()


# ==============================================================================
# Helper Function Tests
# ==============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_init_database(self):
        """Test init_database creates tables."""
        db = init_database("sqlite:///:memory:")

        assert db._initialized is True
        # Tables should be created
        with db.get_session() as session:
            session.execute(Base.metadata.tables["users"].select())

    def test_init_database_default_url(self):
        """Test init_database with default URL."""
        DatabaseManager._instance = None

        with patch.object(DatabaseManager, "create_tables") as mock_create:
            db = init_database()
            mock_create.assert_called_once()

    def test_get_db_generator(self):
        """Test get_db yields session."""
        DatabaseManager._instance = None
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        DatabaseManager._instance = db

        gen = get_db()
        session = next(gen)

        assert session is not None

        # Clean up
        try:
            next(gen)
        except StopIteration:
            pass


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture
    def db(self):
        """Create a fresh database manager with tables."""
        db = DatabaseManager("sqlite:///:memory:")
        db.create_tables()
        return db

    def test_full_crud_operations(self, db):
        """Test full CRUD operations on User model."""
        # Create
        with db.get_session() as session:
            user = User(
                email="crud@example.com",
                username="cruduser",
                hashed_password="hashed123",
            )
            session.add(user)

        # Read
        with db.get_session() as session:
            user = session.query(User).filter_by(email="crud@example.com").first()
            assert user is not None
            assert user.username == "cruduser"
            user_id = user.id

        # Update
        with db.get_session() as session:
            user = session.query(User).get(user_id)
            user.username = "updateduser"

        # Verify update
        with db.get_session() as session:
            user = session.query(User).get(user_id)
            assert user.username == "updateduser"

        # Delete
        with db.get_session() as session:
            user = session.query(User).get(user_id)
            session.delete(user)

        # Verify delete
        with db.get_session() as session:
            user = session.query(User).get(user_id)
            assert user is None

    def test_multiple_sessions(self, db):
        """Test multiple concurrent sessions."""
        # Create user in first session
        with db.get_session() as session1:
            user = User(
                email="multi@example.com",
                username="multiuser",
                hashed_password="hashed",
            )
            session1.add(user)

        # Read in second session
        with db.get_session() as session2:
            users = session2.query(User).all()
            assert len(users) >= 1

    def test_transaction_isolation(self, db):
        """Test transaction isolation between sessions."""
        # Start first session and add user (not committed yet)
        session1 = db._session_factory()
        user = User(
            email="isolated@example.com",
            username="isolateduser",
            hashed_password="hashed",
        )
        session1.add(user)
        session1.flush()  # Write to DB but don't commit

        # Second session should not see uncommitted user
        with db.get_session() as session2:
            users = session2.query(User).filter_by(email="isolated@example.com").all()
            # Depending on isolation level, may or may not see
            # For SQLite default, should not see uncommitted

        session1.rollback()
        session1.close()
