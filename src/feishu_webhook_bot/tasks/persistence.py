"""Task execution persistence for storing execution history in SQLite."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.logger import get_logger

logger = get_logger("task.persistence")


class TaskExecutionStore:
    """SQLite-based storage for task execution history.

    Provides persistent storage for task execution records with support for:
    - Recording execution results
    - Querying execution history
    - Aggregating statistics
    - Cleanup of old records
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        max_records: int = 10000,
    ):
        """Initialize the task execution store.

        Args:
            db_path: Path to SQLite database file. None for in-memory database.
            max_records: Maximum number of records to keep per task.
        """
        self.db_path = str(db_path) if db_path else ":memory:"
        self.max_records = max_records
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        """Context manager for database cursor."""
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
        """Initialize database schema."""
        with self._cursor() as cursor:
            # Task executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    executed_at TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    duration REAL,
                    error TEXT,
                    actions_executed INTEGER DEFAULT 0,
                    actions_failed INTEGER DEFAULT 0,
                    timed_out INTEGER DEFAULT 0,
                    context_json TEXT,
                    result_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_executions_task_name
                ON task_executions(task_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_executions_executed_at
                ON task_executions(executed_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_executions_success
                ON task_executions(success)
            """)

            # Task status table for tracking current state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_status (
                    task_name TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    last_run_at TEXT,
                    last_success_at TEXT,
                    last_failure_at TEXT,
                    consecutive_failures INTEGER DEFAULT 0,
                    total_runs INTEGER DEFAULT 0,
                    total_successes INTEGER DEFAULT 0,
                    total_failures INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            logger.info(f"Task execution store initialized: {self.db_path}")

    def record_execution(
        self,
        task_name: str,
        result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> int:
        """Record a task execution result.

        Args:
            task_name: Name of the task
            result: Execution result dictionary
            context: Optional execution context

        Returns:
            ID of the inserted record
        """
        executed_at = datetime.now().isoformat()
        success = 1 if result.get("success") else 0

        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO task_executions (
                    task_name, executed_at, success, duration, error,
                    actions_executed, actions_failed, timed_out,
                    context_json, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_name,
                    executed_at,
                    success,
                    result.get("duration"),
                    result.get("error"),
                    result.get("actions_executed", 0),
                    result.get("actions_failed", 0),
                    1 if result.get("timed_out") else 0,
                    json.dumps(context) if context else None,
                    json.dumps(result),
                ),
            )
            record_id = cursor.lastrowid

            # Update task status
            self._update_task_status(cursor, task_name, success, executed_at)

        # Cleanup old records if needed
        self._cleanup_old_records(task_name)

        return record_id or 0

    def _update_task_status(
        self,
        cursor: sqlite3.Cursor,
        task_name: str,
        success: int,
        executed_at: str,
    ) -> None:
        """Update task status after execution."""
        cursor.execute(
            "SELECT * FROM task_status WHERE task_name = ?",
            (task_name,),
        )
        row = cursor.fetchone()

        if row:
            if success:
                cursor.execute(
                    """
                    UPDATE task_status SET
                        status = 'success',
                        last_run_at = ?,
                        last_success_at = ?,
                        consecutive_failures = 0,
                        total_runs = total_runs + 1,
                        total_successes = total_successes + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_name = ?
                    """,
                    (executed_at, executed_at, task_name),
                )
            else:
                cursor.execute(
                    """
                    UPDATE task_status SET
                        status = 'failed',
                        last_run_at = ?,
                        last_failure_at = ?,
                        consecutive_failures = consecutive_failures + 1,
                        total_runs = total_runs + 1,
                        total_failures = total_failures + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_name = ?
                    """,
                    (executed_at, executed_at, task_name),
                )
        else:
            cursor.execute(
                """
                INSERT INTO task_status (
                    task_name, status, last_run_at,
                    last_success_at, last_failure_at,
                    consecutive_failures, total_runs,
                    total_successes, total_failures
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_name,
                    "success" if success else "failed",
                    executed_at,
                    executed_at if success else None,
                    None if success else executed_at,
                    0 if success else 1,
                    1,
                    1 if success else 0,
                    0 if success else 1,
                ),
            )

    def _cleanup_old_records(self, task_name: str) -> None:
        """Remove old execution records exceeding max_records."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM task_executions
                WHERE task_name = ? AND id NOT IN (
                    SELECT id FROM task_executions
                    WHERE task_name = ?
                    ORDER BY executed_at DESC
                    LIMIT ?
                )
                """,
                (task_name, task_name, self.max_records),
            )
            deleted = cursor.rowcount
            if deleted > 0:
                logger.debug(f"Cleaned up {deleted} old records for task {task_name}")

    def get_execution_history(
        self,
        task_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
        success_only: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get task execution history.

        Args:
            task_name: Optional filter by task name
            limit: Maximum number of records to return
            offset: Number of records to skip
            success_only: Filter by success status (True/False/None for all)
            start_date: Filter executions after this date
            end_date: Filter executions before this date

        Returns:
            List of execution records
        """
        query = "SELECT * FROM task_executions WHERE 1=1"
        params: list[Any] = []

        if task_name:
            query += " AND task_name = ?"
            params.append(task_name)

        if success_only is not None:
            query += " AND success = ?"
            params.append(1 if success_only else 0)

        if start_date:
            query += " AND executed_at >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND executed_at <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY executed_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert a database row to a dictionary."""
        result = dict(row)
        # Parse JSON fields
        if result.get("context_json"):
            result["context"] = json.loads(result["context_json"])
            del result["context_json"]
        if result.get("result_json"):
            result["result"] = json.loads(result["result_json"])
            del result["result_json"]
        # Convert success to boolean
        result["success"] = bool(result.get("success"))
        result["timed_out"] = bool(result.get("timed_out"))
        return result

    def get_task_status(self, task_name: str) -> dict[str, Any] | None:
        """Get current status for a task.

        Args:
            task_name: Name of the task

        Returns:
            Task status dictionary or None if not found
        """
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM task_status WHERE task_name = ?",
                (task_name,),
            )
            row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_all_task_statuses(self) -> list[dict[str, Any]]:
        """Get status for all tasks.

        Returns:
            List of task status dictionaries
        """
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM task_status ORDER BY task_name")
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def get_task_statistics(
        self,
        task_name: str | None = None,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get execution statistics for tasks.

        Args:
            task_name: Optional filter by task name
            days: Number of days to include in statistics

        Returns:
            Statistics dictionary
        """
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_str = cutoff.isoformat()

        with self._cursor() as cursor:
            # Base query
            base_where = "WHERE executed_at >= ?"
            params: list[Any] = [cutoff_str]

            if task_name:
                base_where += " AND task_name = ?"
                params.append(task_name)

            # Total executions
            cursor.execute(
                f"SELECT COUNT(*) as total FROM task_executions {base_where}",
                params,
            )
            total = cursor.fetchone()["total"]

            # Successful executions
            cursor.execute(
                f"""
                SELECT COUNT(*) as count FROM task_executions
                {base_where} AND success = 1
                """,
                params,
            )
            successful = cursor.fetchone()["count"]

            # Failed executions
            cursor.execute(
                f"""
                SELECT COUNT(*) as count FROM task_executions
                {base_where} AND success = 0
                """,
                params,
            )
            failed = cursor.fetchone()["count"]

            # Average duration
            cursor.execute(
                f"""
                SELECT AVG(duration) as avg_duration FROM task_executions
                {base_where} AND duration IS NOT NULL
                """,
                params,
            )
            avg_duration = cursor.fetchone()["avg_duration"] or 0

            # Executions by day
            cursor.execute(
                f"""
                SELECT DATE(executed_at) as date, COUNT(*) as count,
                       SUM(success) as successes
                FROM task_executions
                {base_where}
                GROUP BY DATE(executed_at)
                ORDER BY date DESC
                LIMIT ?
                """,
                params + [days],
            )
            daily_stats = [
                {
                    "date": row["date"],
                    "total": row["count"],
                    "successes": row["successes"],
                    "failures": row["count"] - row["successes"],
                }
                for row in cursor.fetchall()
            ]

        success_rate = (successful / total * 100) if total > 0 else 0

        return {
            "period_days": days,
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": round(success_rate, 2),
            "average_duration": round(avg_duration, 3),
            "daily_statistics": daily_stats,
        }

    def get_recent_failures(
        self,
        limit: int = 10,
        task_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent failed executions.

        Args:
            limit: Maximum number of records
            task_name: Optional filter by task name

        Returns:
            List of failed execution records
        """
        query = """
            SELECT * FROM task_executions
            WHERE success = 0
        """
        params: list[Any] = []

        if task_name:
            query += " AND task_name = ?"
            params.append(task_name)

        query += " ORDER BY executed_at DESC LIMIT ?"
        params.append(limit)

        with self._cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [self._row_to_dict(row) for row in rows]

    def clear_history(
        self,
        task_name: str | None = None,
        before_date: datetime | None = None,
    ) -> int:
        """Clear execution history.

        Args:
            task_name: Optional filter by task name
            before_date: Optional filter to only clear records before this date

        Returns:
            Number of records deleted
        """
        query = "DELETE FROM task_executions WHERE 1=1"
        params: list[Any] = []

        if task_name:
            query += " AND task_name = ?"
            params.append(task_name)

        if before_date:
            query += " AND executed_at < ?"
            params.append(before_date.isoformat())

        with self._cursor() as cursor:
            cursor.execute(query, params)
            deleted = cursor.rowcount

        logger.info(f"Cleared {deleted} execution records")
        return deleted

    def close(self) -> None:
        """Close database connections."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            del self._local.connection
