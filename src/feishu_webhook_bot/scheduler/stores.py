"""Enhanced job stores for the scheduler."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from apscheduler.jobstores.base import BaseJobStore
from apscheduler.jobstores.memory import MemoryJobStore

from ..core.logger import get_logger

logger = get_logger("scheduler.stores")

try:
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

    HAS_SQLALCHEMY = True
except ImportError:
    SQLAlchemyJobStore = None
    HAS_SQLALCHEMY = False


class ExecutionRecord:
    """Represents a single job execution record."""

    def __init__(
        self,
        job_id: str,
        executed_at: datetime,
        success: bool,
        duration: float,
        error: str | None = None,
    ) -> None:
        self.job_id = job_id
        self.executed_at = executed_at
        self.success = success
        self.duration = duration
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "executed_at": self.executed_at.isoformat(),
            "success": self.success,
            "duration": self.duration,
            "error": self.error,
        }


class ExecutionHistoryStore:
    """SQLite-based store for job execution history."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @contextmanager
    def _get_cursor(self) -> Iterator[sqlite3.Cursor]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_db(self) -> None:
        with self._get_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    executed_at TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    duration REAL NOT NULL,
                    error TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_id ON job_executions(job_id)")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_statistics (
                    job_id TEXT PRIMARY KEY,
                    total_runs INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    total_duration REAL DEFAULT 0,
                    last_run TEXT
                )
            """)

    def record_execution(
        self, job_id: str, success: bool, duration: float, error: str | None = None
    ) -> None:
        now = datetime.now()
        with self._get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO job_executions (job_id, executed_at, success, duration, error) VALUES (?, ?, ?, ?, ?)",
                (job_id, now.isoformat(), int(success), duration, error),
            )
            cursor.execute(
                """
                INSERT INTO job_statistics (job_id, total_runs, success_count, failure_count, total_duration, last_run)
                VALUES (?, 1, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    total_runs = total_runs + 1,
                    success_count = success_count + excluded.success_count,
                    failure_count = failure_count + excluded.failure_count,
                    total_duration = total_duration + excluded.total_duration,
                    last_run = excluded.last_run
            """,
                (job_id, int(success), int(not success), duration, now.isoformat()),
            )

    def get_executions(self, job_id: str | None = None, limit: int = 100) -> list[ExecutionRecord]:
        query = "SELECT * FROM job_executions"
        params: list[Any] = []
        if job_id:
            query += " WHERE job_id = ?"
            params.append(job_id)
        query += " ORDER BY executed_at DESC LIMIT ?"
        params.append(limit)

        with self._get_cursor() as cursor:
            cursor.execute(query, params)
            return [
                ExecutionRecord(
                    job_id=r["job_id"],
                    executed_at=datetime.fromisoformat(r["executed_at"]),
                    success=bool(r["success"]),
                    duration=r["duration"],
                    error=r["error"],
                )
                for r in cursor.fetchall()
            ]

    def get_statistics(self, job_id: str) -> dict[str, Any] | None:
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM job_statistics WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
        if not row:
            return None
        total = row["total_runs"]
        return {
            "job_id": row["job_id"],
            "total_runs": total,
            "success_rate": (row["success_count"] / total * 100) if total > 0 else 0,
            "average_duration": row["total_duration"] / total if total > 0 else 0,
        }

    def get_all_statistics(self) -> list[dict[str, Any]]:
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM job_statistics ORDER BY total_runs DESC")
            return [
                {
                    "job_id": r["job_id"],
                    "total_runs": r["total_runs"],
                    "success_rate": (r["success_count"] / r["total_runs"] * 100)
                    if r["total_runs"] > 0
                    else 0,
                }
                for r in cursor.fetchall()
            ]

    def cleanup_old_records(self, days: int = 30) -> int:
        cutoff = datetime.now() - timedelta(days=days)
        with self._get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM job_executions WHERE executed_at < ?", (cutoff.isoformat(),)
            )
            return cursor.rowcount


class JobStoreFactory:
    """Factory for creating job stores."""

    @staticmethod
    def create(store_type: str, store_path: str | None = None) -> BaseJobStore:
        if store_type == "memory":
            return MemoryJobStore()
        if store_type == "sqlite":
            if not store_path:
                raise ValueError("store_path required for sqlite")
            if not HAS_SQLALCHEMY:
                logger.warning("SQLAlchemy not installed, using memory store")
                return MemoryJobStore()
            return SQLAlchemyJobStore(url=f"sqlite:///{store_path}")
        raise ValueError(f"Unknown store type: {store_type}")


__all__ = ["ExecutionHistoryStore", "ExecutionRecord", "JobStoreFactory"]
