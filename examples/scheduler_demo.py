"""Comprehensive demonstration of the Task Scheduler.

This example demonstrates:
1. Scheduling tasks with cron expressions
2. Interval-based scheduling
3. Job management (add, remove, pause, resume)
4. Persistent vs in-memory job stores
5. Timezone-aware scheduling
6. Job decorators
7. Error handling and retry logic

Run this example:
    python examples/scheduler_demo.py
"""

import tempfile
import time
from datetime import datetime
from pathlib import Path

from feishu_webhook_bot.core.config import SchedulerConfig
from feishu_webhook_bot.scheduler import TaskScheduler, job

# ============================================================================
# Example Task Functions
# ============================================================================


def simple_task() -> None:
    """A simple task that prints a message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏰ Simple task executed!")


def task_with_args(name: str, count: int) -> None:
    """A task that accepts arguments."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Task '{name}' executed {count} times")


@job(trigger="interval", seconds=5)
def decorated_interval_task() -> None:
    """Task decorated with @job for interval scheduling."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 Decorated interval task!")


@job(trigger="cron", minute="*", second="0")
def decorated_cron_task() -> None:
    """Task decorated with @job for cron scheduling."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📅 Decorated cron task!")


def failing_task() -> None:
    """A task that raises an exception."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Task about to fail...")
    raise ValueError("Intentional error for demonstration")


# ============================================================================
# Demo Functions
# ============================================================================


def demo_basic_scheduling() -> None:
    """Demonstrate basic task scheduling."""
    print("\n" + "=" * 70)
    print("Demo 1: Basic Task Scheduling")
    print("=" * 70)

    # Create scheduler with in-memory job store
    config = SchedulerConfig(
        enabled=True,
        job_store_type="memory",
        timezone="UTC",
    )
    scheduler = TaskScheduler(config)
    scheduler.start()

    print("\n✅ Scheduler started with in-memory job store")

    # Add interval-based job
    job_id = scheduler.add_job(
        simple_task,
        trigger="interval",
        seconds=3,
        job_id="simple-task",
    )
    print(f"✅ Added interval job: {job_id} (runs every 3 seconds)")

    # Wait to see some executions
    print("\n⏳ Waiting 10 seconds to see task executions...")
    time.sleep(10)

    # Remove the job
    scheduler.remove_job(job_id)
    print(f"\n✅ Removed job: {job_id}")

    scheduler.shutdown()
    print("✅ Scheduler stopped")


def demo_cron_scheduling() -> None:
    """Demonstrate cron-based scheduling."""
    print("\n" + "=" * 70)
    print("Demo 2: Cron-Based Scheduling")
    print("=" * 70)

    config = SchedulerConfig(enabled=True, timezone="UTC")
    scheduler = TaskScheduler(config)
    scheduler.start()

    print("\n✅ Scheduler started")

    # Add cron job (every minute at :00 seconds)
    job_id = scheduler.add_job(
        simple_task,
        trigger="cron",
        minute="*",
        second="0",
        job_id="cron-task",
    )
    print(f"✅ Added cron job: {job_id} (runs every minute at :00 seconds)")

    # Add another cron job (every 30 seconds)
    job_id2 = scheduler.add_job(
        simple_task,
        trigger="cron",
        second="0,30",
        job_id="cron-task-30s",
    )
    print(f"✅ Added cron job: {job_id2} (runs at :00 and :30 seconds)")

    print("\n⏳ Waiting 65 seconds to see cron executions...")
    time.sleep(65)

    scheduler.shutdown()
    print("\n✅ Scheduler stopped")


def demo_job_with_arguments() -> None:
    """Demonstrate scheduling jobs with arguments."""
    print("\n" + "=" * 70)
    print("Demo 3: Jobs with Arguments")
    print("=" * 70)

    config = SchedulerConfig(enabled=True)
    scheduler = TaskScheduler(config)
    scheduler.start()

    print("\n✅ Scheduler started")

    # Track execution count
    execution_count = {"count": 0}

    def counting_task():
        execution_count["count"] += 1
        task_with_args("CountingTask", execution_count["count"])

    # Add job
    job_id = scheduler.add_job(
        counting_task,
        trigger="interval",
        seconds=2,
        job_id="counting-task",
    )
    print(f"✅ Added counting job: {job_id}")

    print("\n⏳ Waiting 10 seconds...")
    time.sleep(10)

    print(f"\n✅ Task executed {execution_count['count']} times")

    scheduler.shutdown()
    print("✅ Scheduler stopped")


def demo_job_decorator() -> None:
    """Demonstrate using the @job decorator."""
    print("\n" + "=" * 70)
    print("Demo 4: Job Decorator")
    print("=" * 70)

    config = SchedulerConfig(enabled=True)
    scheduler = TaskScheduler(config)
    scheduler.start()

    print("\n✅ Scheduler started")

    # Register decorated jobs
    scheduler.register_job(decorated_interval_task)
    print("✅ Registered decorated interval task (every 5 seconds)")

    scheduler.register_job(decorated_cron_task)
    print("✅ Registered decorated cron task (every minute)")

    print("\n⏳ Waiting 12 seconds to see executions...")
    time.sleep(12)

    scheduler.shutdown()
    print("\n✅ Scheduler stopped")


def demo_persistent_job_store() -> None:
    """Demonstrate persistent job store with SQLite."""
    print("\n" + "=" * 70)
    print("Demo 5: Persistent Job Store")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "scheduler.db"

        # Create scheduler with SQLite job store
        config = SchedulerConfig(
            enabled=True,
            job_store_type="sqlite",
            job_store_path=str(db_path),
        )
        scheduler = TaskScheduler(config)
        scheduler.start()

        print(f"\n✅ Scheduler started with SQLite job store: {db_path}")

        # Add a job
        job_id = scheduler.add_job(
            simple_task,
            trigger="interval",
            seconds=5,
            job_id="persistent-task",
        )
        print(f"✅ Added job: {job_id}")

        # Wait for one execution
        time.sleep(6)

        # Stop scheduler
        scheduler.shutdown()
        print("\n✅ Scheduler stopped (job persisted to database)")

        # Restart scheduler (job should be restored)
        print("\n🔄 Restarting scheduler...")
        scheduler2 = TaskScheduler(config)
        scheduler2.start()

        print("✅ Scheduler restarted")
        print("✅ Jobs restored from database:")
        for job in scheduler2.get_jobs():
            print(f"   • {job.id}")

        time.sleep(6)

        scheduler2.shutdown()
        print("\n✅ Scheduler stopped")

        # Explicitly delete scheduler objects to release database locks
        del scheduler
        del scheduler2
        # Give Windows time to release file locks
        time.sleep(0.5)


def demo_job_management() -> None:
    """Demonstrate job management operations."""
    print("\n" + "=" * 70)
    print("Demo 6: Job Management")
    print("=" * 70)

    config = SchedulerConfig(enabled=True)
    scheduler = TaskScheduler(config)
    scheduler.start()

    print("\n✅ Scheduler started")

    # Add multiple jobs
    job_ids = []
    for i in range(1, 4):
        job_id = scheduler.add_job(
            simple_task,
            trigger="interval",
            seconds=5,
            job_id=f"task-{i}",
        )
        job_ids.append(job_id)
        print(f"✅ Added job: {job_id}")

    # List all jobs
    print("\n📋 All jobs:")
    for scheduled_job in scheduler.get_jobs():
        print(f"   • {scheduled_job.id} - Next run: {scheduled_job.next_run_time}")

    # Pause a job
    print(f"\n⏸️  Pausing job: {job_ids[0]}")
    scheduler.pause_job(job_ids[0])

    # Resume a job
    time.sleep(2)
    print(f"▶️  Resuming job: {job_ids[0]}")
    scheduler.resume_job(job_ids[0])

    # Wait for some executions
    time.sleep(8)

    # Remove all jobs
    print("\n🗑️  Removing all jobs...")
    for job_id in job_ids:
        scheduler.remove_job(job_id)
        print(f"   ✅ Removed: {job_id}")

    scheduler.shutdown()
    print("\n✅ Scheduler stopped")


def demo_timezone_aware() -> None:
    """Demonstrate timezone-aware scheduling."""
    print("\n" + "=" * 70)
    print("Demo 7: Timezone-Aware Scheduling")
    print("=" * 70)

    # Create scheduler with specific timezone
    config = SchedulerConfig(
        enabled=True,
        timezone="America/New_York",
    )
    scheduler = TaskScheduler(config)
    scheduler.start()

    print("\n✅ Scheduler started with timezone: America/New_York")

    def timezone_task():
        now = datetime.now()
        print(f"[{now.strftime('%H:%M:%S')}] 🌍 Task executed (local time)")

    # Add job
    job_id = scheduler.add_job(
        timezone_task,
        trigger="interval",
        seconds=5,
        job_id="timezone-task",
    )
    print(f"✅ Added job: {job_id}")

    print("\n⏳ Waiting 12 seconds...")
    time.sleep(12)

    scheduler.shutdown()
    print("\n✅ Scheduler stopped")


def demo_error_handling() -> None:
    """Demonstrate error handling in scheduled jobs."""
    print("\n" + "=" * 70)
    print("Demo 8: Error Handling")
    print("=" * 70)

    config = SchedulerConfig(enabled=True)
    scheduler = TaskScheduler(config)
    scheduler.start()

    print("\n✅ Scheduler started")

    # Add a job that will fail
    job_id = scheduler.add_job(
        failing_task,
        trigger="interval",
        seconds=3,
        job_id="failing-task",
    )
    print(f"✅ Added failing job: {job_id}")
    print("   (This job will raise an exception)")

    print("\n⏳ Waiting 10 seconds to see error handling...")
    time.sleep(10)

    print("\n✅ Scheduler continues running despite job failures")

    scheduler.shutdown()
    print("✅ Scheduler stopped")


# ============================================================================
# Main Demo Runner
# ============================================================================


def main() -> None:
    """Run all scheduler demonstrations."""
    print("\n" + "=" * 70)
    print("FEISHU WEBHOOK BOT - TASK SCHEDULER DEMONSTRATION")
    print("=" * 70)

    demos = [
        ("Basic Scheduling", demo_basic_scheduling),
        ("Cron Scheduling", demo_cron_scheduling),
        ("Jobs with Arguments", demo_job_with_arguments),
        ("Job Decorator", demo_job_decorator),
        ("Persistent Job Store", demo_persistent_job_store),
        ("Job Management", demo_job_management),
        ("Timezone-Aware", demo_timezone_aware),
        ("Error Handling", demo_error_handling),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            import traceback

            traceback.print_exc()

        if i < len(demos):
            print("\n" + "-" * 70)
            input("Press Enter to continue to next demo...")

    print("\n" + "=" * 70)
    print("ALL DEMONSTRATIONS COMPLETED!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("• Scheduler supports both interval and cron-based scheduling")
    print("• Jobs can be added, removed, paused, and resumed dynamically")
    print("• @job decorator simplifies job registration")
    print("• Persistent job store (SQLite) survives restarts")
    print("• Timezone-aware scheduling for global deployments")
    print("• Robust error handling keeps scheduler running")
    print("• Jobs can accept arguments and maintain state")


if __name__ == "__main__":
    main()
