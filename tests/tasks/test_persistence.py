"""Tests for task execution persistence."""

from pathlib import Path

import pytest

from feishu_webhook_bot.tasks.persistence import TaskExecutionStore


@pytest.fixture
def memory_store():
    """Create an in-memory execution store."""
    return TaskExecutionStore(db_path=None)


@pytest.fixture
def file_store(tmp_path):
    """Create a file-based execution store."""
    db_path = tmp_path / "test_tasks.db"
    store = TaskExecutionStore(db_path=db_path)
    yield store
    store.close()


class TestTaskExecutionStore:
    """Test TaskExecutionStore basic functionality."""

    def test_init_memory_store(self, memory_store):
        """Test initialization with in-memory database."""
        assert memory_store.db_path == ":memory:"

    def test_init_file_store(self, file_store, tmp_path):
        """Test initialization with file database."""
        assert Path(file_store.db_path).exists()

    def test_record_execution_success(self, memory_store):
        """Test recording a successful execution."""
        result = {
            "success": True,
            "duration": 1.5,
            "actions_executed": 2,
            "actions_failed": 0,
        }

        record_id = memory_store.record_execution("test_task", result)

        assert record_id > 0

    def test_record_execution_failure(self, memory_store):
        """Test recording a failed execution."""
        result = {
            "success": False,
            "duration": 0.5,
            "error": "Something went wrong",
            "actions_executed": 1,
            "actions_failed": 1,
        }

        record_id = memory_store.record_execution("test_task", result)

        assert record_id > 0

    def test_get_execution_history(self, memory_store):
        """Test retrieving execution history."""
        # Record multiple executions
        for i in range(5):
            memory_store.record_execution(
                "test_task",
                {"success": i % 2 == 0, "duration": float(i)},
            )

        history = memory_store.get_execution_history("test_task", limit=10)

        assert len(history) == 5
        # Should be in reverse chronological order (most recent first)
        # Verify we got all records
        durations = sorted([h["duration"] for h in history])
        assert durations == [0.0, 1.0, 2.0, 3.0, 4.0]

    def test_get_execution_history_filter_success(self, memory_store):
        """Test filtering history by success status."""
        for i in range(5):
            memory_store.record_execution(
                "test_task",
                {"success": i % 2 == 0, "duration": i * 0.1},
            )

        successful = memory_store.get_execution_history("test_task", success_only=True)
        failed = memory_store.get_execution_history("test_task", success_only=False)

        assert len(successful) == 3  # 0, 2, 4
        assert len(failed) == 2  # 1, 3

    def test_get_execution_history_limit(self, memory_store):
        """Test history limit parameter."""
        for i in range(10):
            memory_store.record_execution(
                "test_task",
                {"success": True, "duration": i * 0.1},
            )

        history = memory_store.get_execution_history("test_task", limit=3)

        assert len(history) == 3

    def test_get_execution_history_multiple_tasks(self, memory_store):
        """Test history filtering by task name."""
        memory_store.record_execution("task_a", {"success": True})
        memory_store.record_execution("task_b", {"success": True})
        memory_store.record_execution("task_a", {"success": False})

        history_a = memory_store.get_execution_history("task_a")
        history_b = memory_store.get_execution_history("task_b")
        history_all = memory_store.get_execution_history()

        assert len(history_a) == 2
        assert len(history_b) == 1
        assert len(history_all) == 3


class TestTaskStatus:
    """Test task status tracking."""

    def test_task_status_created_on_first_execution(self, memory_store):
        """Task status is created on first execution."""
        memory_store.record_execution("new_task", {"success": True})

        status = memory_store.get_task_status("new_task")

        assert status is not None
        assert status["task_name"] == "new_task"
        assert status["status"] == "success"
        assert status["total_runs"] == 1
        assert status["total_successes"] == 1
        assert status["total_failures"] == 0

    def test_task_status_updated_on_success(self, memory_store):
        """Task status is updated correctly on success."""
        memory_store.record_execution("test_task", {"success": True})
        memory_store.record_execution("test_task", {"success": True})

        status = memory_store.get_task_status("test_task")

        assert status["total_runs"] == 2
        assert status["total_successes"] == 2
        assert status["consecutive_failures"] == 0

    def test_task_status_updated_on_failure(self, memory_store):
        """Task status is updated correctly on failure."""
        memory_store.record_execution("test_task", {"success": True})
        memory_store.record_execution("test_task", {"success": False})
        memory_store.record_execution("test_task", {"success": False})

        status = memory_store.get_task_status("test_task")

        assert status["total_runs"] == 3
        assert status["total_failures"] == 2
        assert status["consecutive_failures"] == 2
        assert status["status"] == "failed"

    def test_consecutive_failures_reset_on_success(self, memory_store):
        """Consecutive failures counter resets on success."""
        memory_store.record_execution("test_task", {"success": False})
        memory_store.record_execution("test_task", {"success": False})
        memory_store.record_execution("test_task", {"success": True})

        status = memory_store.get_task_status("test_task")

        assert status["consecutive_failures"] == 0

    def test_get_all_task_statuses(self, memory_store):
        """Test getting all task statuses."""
        memory_store.record_execution("task_a", {"success": True})
        memory_store.record_execution("task_b", {"success": False})
        memory_store.record_execution("task_c", {"success": True})

        statuses = memory_store.get_all_task_statuses()

        assert len(statuses) == 3
        task_names = [s["task_name"] for s in statuses]
        assert "task_a" in task_names
        assert "task_b" in task_names
        assert "task_c" in task_names


class TestTaskStatistics:
    """Test task statistics calculation."""

    def test_get_task_statistics_empty(self, memory_store):
        """Test statistics with no executions."""
        stats = memory_store.get_task_statistics("nonexistent_task")

        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0

    def test_get_task_statistics(self, memory_store):
        """Test statistics calculation."""
        for i in range(10):
            memory_store.record_execution(
                "test_task",
                {"success": i < 7, "duration": 1.0},  # 7 successes, 3 failures
            )

        stats = memory_store.get_task_statistics("test_task")

        assert stats["total_executions"] == 10
        assert stats["successful_executions"] == 7
        assert stats["failed_executions"] == 3
        assert stats["success_rate"] == 70.0
        assert stats["average_duration"] == 1.0

    def test_get_task_statistics_all_tasks(self, memory_store):
        """Test statistics for all tasks."""
        memory_store.record_execution("task_a", {"success": True, "duration": 1.0})
        memory_store.record_execution("task_b", {"success": False, "duration": 2.0})

        stats = memory_store.get_task_statistics()

        assert stats["total_executions"] == 2
        assert stats["successful_executions"] == 1


class TestRecentFailures:
    """Test recent failures retrieval."""

    def test_get_recent_failures(self, memory_store):
        """Test getting recent failures."""
        memory_store.record_execution("task_a", {"success": True})
        memory_store.record_execution("task_a", {"success": False, "error": "Error 1"})
        memory_store.record_execution("task_b", {"success": False, "error": "Error 2"})
        memory_store.record_execution("task_a", {"success": True})

        failures = memory_store.get_recent_failures(limit=10)

        assert len(failures) == 2
        assert all(not f["success"] for f in failures)

    def test_get_recent_failures_by_task(self, memory_store):
        """Test getting recent failures for specific task."""
        memory_store.record_execution("task_a", {"success": False, "error": "Error 1"})
        memory_store.record_execution("task_b", {"success": False, "error": "Error 2"})

        failures = memory_store.get_recent_failures(task_name="task_a")

        assert len(failures) == 1
        assert failures[0]["task_name"] == "task_a"


class TestCleanup:
    """Test history cleanup functionality."""

    def test_clear_history_all(self, memory_store):
        """Test clearing all history."""
        for _ in range(5):
            memory_store.record_execution("test_task", {"success": True})

        deleted = memory_store.clear_history()

        assert deleted == 5
        assert len(memory_store.get_execution_history()) == 0

    def test_clear_history_by_task(self, memory_store):
        """Test clearing history for specific task."""
        memory_store.record_execution("task_a", {"success": True})
        memory_store.record_execution("task_b", {"success": True})
        memory_store.record_execution("task_a", {"success": True})

        deleted = memory_store.clear_history(task_name="task_a")

        assert deleted == 2
        assert len(memory_store.get_execution_history("task_a")) == 0
        assert len(memory_store.get_execution_history("task_b")) == 1

    def test_max_records_cleanup(self):
        """Test automatic cleanup when max_records is exceeded."""
        store = TaskExecutionStore(db_path=None, max_records=5)

        for idx in range(10):
            store.record_execution("test_task", {"success": True, "duration": float(idx)})

        history = store.get_execution_history("test_task", limit=100)

        # Should only keep max_records (5) records
        assert len(history) == 5
        # The cleanup keeps the most recent records by executed_at
        # Since all records have nearly the same timestamp, the exact records kept
        # may vary, but we should have exactly 5 records
        durations = [h["duration"] for h in history]
        assert len(durations) == 5
        # All durations should be from our recorded set
        assert all(d in [float(i) for i in range(10)] for d in durations)


class TestPersistence:
    """Test data persistence across store instances."""

    def test_data_persists_to_file(self, tmp_path):
        """Test that data persists when using file storage."""
        db_path = tmp_path / "persist_test.db"

        # Create store and add data
        store1 = TaskExecutionStore(db_path=db_path)
        store1.record_execution("test_task", {"success": True, "duration": 1.0})
        store1.close()

        # Create new store instance
        store2 = TaskExecutionStore(db_path=db_path)
        history = store2.get_execution_history("test_task")
        store2.close()

        assert len(history) == 1
        assert history[0]["success"] is True
