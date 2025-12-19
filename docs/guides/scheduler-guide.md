# Scheduler Guide

This guide explains how to use the APScheduler-based task scheduling system in the Feishu Webhook Bot framework.

## Table of Contents

- [Overview](#overview)
- [Configuration](#configuration)
- [Scheduling Methods](#scheduling-methods)
- [Job Decorator](#job-decorator)
- [Plugin Scheduling](#plugin-scheduling)
- [Job Management](#job-management)
- [Job Persistence](#job-persistence)
- [Best Practices](#best-practices)

## Overview

The scheduler is built on [APScheduler](https://apscheduler.readthedocs.io/) and provides:

- **Interval Scheduling**: Run jobs at fixed intervals
- **Cron Scheduling**: Run jobs using cron expressions
- **Date Scheduling**: Run jobs at a specific date/time
- **Job Persistence**: Optionally persist jobs to SQLite
- **Timezone Support**: Configure timezone for all jobs

## Configuration

### Basic Configuration

```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  job_store_type: "memory"  # or "sqlite"
```

### Full Configuration

```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  job_store_type: "sqlite"
  job_store_path: "data/jobs.db"
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | true | Enable scheduler |
| `timezone` | string | "Asia/Shanghai" | Timezone for jobs |
| `job_store_type` | string | "memory" | Job store type (memory/sqlite) |
| `job_store_path` | string | None | Path to SQLite database |

## Scheduling Methods

### Interval Scheduling

Run jobs at fixed intervals:

```python
from feishu_webhook_bot.scheduler import TaskScheduler

scheduler = TaskScheduler(config)

# Run every 5 minutes
scheduler.add_job(
    my_function,
    trigger='interval',
    minutes=5,
    id='my-job',
)

# Run every 30 seconds
scheduler.add_job(
    another_function,
    trigger='interval',
    seconds=30,
)

# Run every 2 hours
scheduler.add_job(
    hourly_function,
    trigger='interval',
    hours=2,
)
```

#### Interval Options

| Option | Description |
|--------|-------------|
| `weeks` | Number of weeks |
| `days` | Number of days |
| `hours` | Number of hours |
| `minutes` | Number of minutes |
| `seconds` | Number of seconds |
| `start_date` | Start date for interval |
| `end_date` | End date for interval |

### Cron Scheduling

Run jobs using cron expressions:

```python
# Daily at 9:00 AM
scheduler.add_job(
    daily_task,
    trigger='cron',
    hour=9,
    minute=0,
)

# Every Monday at 10:30 AM
scheduler.add_job(
    weekly_task,
    trigger='cron',
    day_of_week='mon',
    hour=10,
    minute=30,
)

# Weekdays at 6:00 PM
scheduler.add_job(
    evening_task,
    trigger='cron',
    day_of_week='mon-fri',
    hour=18,
    minute=0,
)

# First day of month at midnight
scheduler.add_job(
    monthly_task,
    trigger='cron',
    day=1,
    hour=0,
    minute=0,
)

# Every 15 minutes
scheduler.add_job(
    frequent_task,
    trigger='cron',
    minute='*/15',
)
```

#### Cron Options

| Option | Description | Values |
|--------|-------------|--------|
| `year` | Year | 4-digit year |
| `month` | Month | 1-12 |
| `day` | Day of month | 1-31 |
| `week` | Week of year | 1-53 |
| `day_of_week` | Day of week | 0-6 (mon-sun) or mon,tue,wed,thu,fri,sat,sun |
| `hour` | Hour | 0-23 |
| `minute` | Minute | 0-59 |
| `second` | Second | 0-59 |

#### Cron Expression Examples

| Expression | Description |
|------------|-------------|
| `hour=9, minute=0` | Daily at 9:00 AM |
| `day_of_week='mon-fri', hour=9` | Weekdays at 9:00 AM |
| `day=1, hour=0` | First day of month at midnight |
| `minute='*/15'` | Every 15 minutes |
| `hour='*/2'` | Every 2 hours |
| `day_of_week='mon', hour=10, minute=30` | Monday at 10:30 AM |

### Date Scheduling

Run a job once at a specific date/time:

```python
from datetime import datetime

# Run once at specific time
scheduler.add_job(
    one_time_task,
    trigger='date',
    run_date=datetime(2025, 1, 15, 10, 0, 0),
)

# Run in 1 hour
from datetime import timedelta
scheduler.add_job(
    delayed_task,
    trigger='date',
    run_date=datetime.now() + timedelta(hours=1),
)
```

## Job Decorator

Use the `@job` decorator for cleaner syntax:

```python
from feishu_webhook_bot.scheduler import job

@job(trigger='interval', minutes=5)
def periodic_task():
    """Run every 5 minutes."""
    print("Task executed!")

@job(trigger='cron', hour=9, minute=0)
def daily_task():
    """Run daily at 9 AM."""
    print("Good morning!")

@job(trigger='cron', day_of_week='mon-fri', hour=18)
def evening_task():
    """Run weekdays at 6 PM."""
    print("End of workday!")
```

### Decorator Options

```python
@job(
    trigger='interval',
    minutes=5,
    id='custom-job-id',  # Custom job ID
    name='My Custom Job',  # Job name
    max_instances=1,  # Max concurrent instances
    coalesce=True,  # Coalesce missed runs
    misfire_grace_time=60,  # Grace time for misfires
)
def my_task():
    pass
```

## Plugin Scheduling

Plugins can register scheduled jobs:

```python
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class MyPlugin(BasePlugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
        )

    def on_enable(self) -> None:
        # Register interval job
        self.register_job(
            self.periodic_task,
            trigger='interval',
            minutes=5,
        )

        # Register cron job
        self.register_job(
            self.daily_task,
            trigger='cron',
            hour=9,
            minute=0,
        )

    def periodic_task(self) -> None:
        self.client.send_text("Periodic update!")

    def daily_task(self) -> None:
        self.client.send_text("Good morning!")
```

### Plugin Job Management

```python
class MyPlugin(BasePlugin):
    def on_enable(self) -> None:
        # Register with custom ID
        self.register_job(
            self.my_task,
            trigger='interval',
            minutes=10,
            job_id='my-custom-job',
        )

    def on_disable(self) -> None:
        # Jobs are automatically removed when plugin is disabled
        pass

    def pause_job(self) -> None:
        # Pause a specific job
        self.scheduler.pause_job('my-custom-job')

    def resume_job(self) -> None:
        # Resume a paused job
        self.scheduler.resume_job('my-custom-job')
```

## Job Management

### TaskScheduler API

```python
from feishu_webhook_bot.scheduler import TaskScheduler

scheduler = TaskScheduler(config)

# Start scheduler
scheduler.start()

# Add job
job = scheduler.add_job(
    my_function,
    trigger='interval',
    minutes=5,
    id='my-job',
)

# Get job
job = scheduler.get_job('my-job')

# Get all jobs
jobs = scheduler.get_jobs()

# Pause job
scheduler.pause_job('my-job')

# Resume job
scheduler.resume_job('my-job')

# Remove job
scheduler.remove_job('my-job')

# Reschedule job
scheduler.reschedule_job(
    'my-job',
    trigger='interval',
    minutes=10,
)

# Shutdown scheduler
scheduler.shutdown()
```

### Job Information

```python
job = scheduler.get_job('my-job')

print(f"Job ID: {job.id}")
print(f"Job Name: {job.name}")
print(f"Next Run: {job.next_run_time}")
print(f"Trigger: {job.trigger}")
```

### Listing Jobs

```python
# Get all jobs
for job in scheduler.get_jobs():
    print(f"{job.id}: next run at {job.next_run_time}")

# Get jobs by job store
jobs = scheduler.get_jobs(jobstore='default')
```

## Job Persistence

### SQLite Job Store

Enable job persistence to survive restarts:

```yaml
scheduler:
  enabled: true
  job_store_type: "sqlite"
  job_store_path: "data/jobs.db"
```

### Benefits

- Jobs survive bot restarts
- Missed jobs can be recovered
- Job history is preserved

### Considerations

- Slightly slower than memory store
- Requires write access to database path
- Database file grows over time

## Best Practices

### 1. Use Meaningful Job IDs

```python
# Good
scheduler.add_job(task, id='daily-report-generator')

# Bad
scheduler.add_job(task, id='job1')
```

### 2. Handle Exceptions

```python
def my_task():
    try:
        # Task logic
        do_something()
    except Exception as e:
        logger.error(f"Task failed: {e}")
        # Don't re-raise to prevent job removal
```

### 3. Set Appropriate Intervals

```python
# Too frequent - may cause issues
scheduler.add_job(task, trigger='interval', seconds=1)  # Bad

# Reasonable interval
scheduler.add_job(task, trigger='interval', minutes=5)  # Good
```

### 4. Use Coalescing for Long Tasks

```python
scheduler.add_job(
    long_running_task,
    trigger='interval',
    minutes=5,
    coalesce=True,  # Combine missed runs
    max_instances=1,  # Only one instance at a time
)
```

### 5. Set Misfire Grace Time

```python
scheduler.add_job(
    important_task,
    trigger='cron',
    hour=9,
    misfire_grace_time=300,  # 5 minutes grace
)
```

### 6. Use Job Persistence for Production

```yaml
# Development
scheduler:
  job_store_type: "memory"

# Production
scheduler:
  job_store_type: "sqlite"
  job_store_path: "data/jobs.db"
```

### 7. Monitor Job Execution

```python
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

def job_listener(event):
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    else:
        logger.info(f"Job {event.job_id} completed")

scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
```

## Troubleshooting

### Jobs Not Running

1. Check scheduler is enabled
2. Verify timezone is correct
3. Check job is not paused
4. Review logs for errors

### Missed Jobs

1. Enable job persistence
2. Set appropriate misfire_grace_time
3. Use coalescing for long intervals

### Too Many Instances

1. Set max_instances=1
2. Use coalescing
3. Check if previous job is still running

### Timezone Issues

1. Verify timezone in config
2. Use explicit timezone in job
3. Check system timezone

## See Also

- [Task System Guide](tasks-guide.md) - Advanced task execution
- [Plugin Development](plugin-guide.md) - Plugin scheduling
- [Automation Guide](automation-guide.md) - Declarative workflows
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
