"""Comprehensive demonstration of the Task Manager.

This example demonstrates:
1. Automated task execution
2. Task dependencies and retry logic
3. Task conditions (time, day, environment)
4. Integration with plugins and AI agent
5. Task templates and reusable configurations

Run this example:
    python examples/task_manager_demo.py
"""

import os
import tempfile
import time
from pathlib import Path

from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core.config import (
    BotConfig,
    PluginConfig,
    TaskActionConfig,
    TaskDefinitionConfig,
    WebhookConfig,
)


def get_dummy_webhook() -> list[WebhookConfig]:
    """Get a dummy webhook configuration for demos."""
    return [
        WebhookConfig(
            name="default",
            url="https://httpbin.org/post",
        )
    ]


# ============================================================================
# Demo Functions
# ============================================================================


def demo_basic_task() -> None:
    """Demonstrate basic task execution."""
    print("\n" + "=" * 70)
    print("Demo 1: Basic Task Execution")
    print("=" * 70)

    tasks = [
        TaskDefinitionConfig(
            name="hello-task",
            enabled=True,
            description="Simple task that sends a message",
            schedule={
                "mode": "interval",
                "arguments": {"seconds": 5},
            },
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="👋 Hello from Task Manager!",
                )
            ],
        )
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        tasks=tasks,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with basic task")
    print("   • Task: hello-task")
    print("   • Schedule: Every 5 seconds")

    print("\n⏳ Waiting 15 seconds...")
    time.sleep(15)

    bot.stop()
    print("\n✅ Bot stopped")


def demo_task_with_conditions() -> None:
    """Demonstrate task execution with conditions."""
    print("\n" + "=" * 70)
    print("Demo 2: Task with Conditions")
    print("=" * 70)

    # Set environment variable for condition
    os.environ["TASK_ENV"] = "production"

    tasks = [
        TaskDefinitionConfig(
            name="conditional-task",
            enabled=True,
            description="Task that only runs in production",
            schedule={
                "mode": "interval",
                "arguments": {"seconds": 6},
            },
            conditions={
                "environment": "production",  # Checks TASK_ENV
            },
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="✅ Production task executed!",
                )
            ],
        )
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        tasks=tasks,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with conditional task")
    print("   • Condition: environment=production")
    print(f"   • TASK_ENV={os.environ.get('TASK_ENV')}")

    print("\n⏳ Waiting 15 seconds...")
    time.sleep(15)

    bot.stop()
    print("\n✅ Bot stopped")

    # Clean up
    del os.environ["TASK_ENV"]


def demo_task_with_retry() -> None:
    """Demonstrate task retry logic."""
    print("\n" + "=" * 70)
    print("Demo 3: Task with Retry Logic")
    print("=" * 70)

    tasks = [
        TaskDefinitionConfig(
            name="retry-task",
            enabled=True,
            description="Task with retry on failure",
            schedule={
                "mode": "interval",
                "arguments": {"seconds": 10},
            },
            retry_on_failure=True,
            max_retries=3,
            retry_delay=2,
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="🔄 Task with retry logic",
                )
            ],
        )
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        tasks=tasks,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with retry task")
    print("   • Max retries: 3")
    print("   • Retry delay: 2 seconds")

    print("\n⏳ Waiting 15 seconds...")
    time.sleep(15)

    bot.stop()
    print("\n✅ Bot stopped")


def demo_task_dependencies() -> None:
    """Demonstrate task dependencies."""
    print("\n" + "=" * 70)
    print("Demo 4: Task Dependencies")
    print("=" * 70)

    tasks = [
        TaskDefinitionConfig(
            name="task-1",
            enabled=True,
            description="First task in chain",
            schedule={
                "mode": "interval",
                "arguments": {"seconds": 15},
            },
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="1️⃣ Task 1 executed",
                )
            ],
        ),
        TaskDefinitionConfig(
            name="task-2",
            enabled=True,
            description="Second task (depends on task-1)",
            depends_on=["task-1"],
            schedule={
                "mode": "interval",
                "arguments": {"seconds": 15},
            },
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="2️⃣ Task 2 executed (after task-1)",
                )
            ],
        ),
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        tasks=tasks,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with dependent tasks")
    print("   • task-1: Runs first")
    print("   • task-2: Runs after task-1 completes")

    print("\n⏳ Waiting 20 seconds...")
    time.sleep(20)

    bot.stop()
    print("\n✅ Bot stopped")


def demo_task_with_plugin() -> None:
    """Demonstrate task integration with plugins."""
    print("\n" + "=" * 70)
    print("Demo 5: Task with Plugin Integration")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir)

        # Create a plugin
        plugin_file = plugin_dir / "task_plugin.py"
        plugin_code = '''
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class TaskPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="task-plugin", version="1.0.0")

    def process_task(self, task_name):
        """Method called by task."""
        self.logger.info(f"Processing task: {task_name}")
        self.client.send_text(f"🔧 Plugin processed task: {task_name}")
        return {"status": "success"}
'''
        plugin_file.write_text(plugin_code)

        tasks = [
            TaskDefinitionConfig(
                name="plugin-task",
                enabled=True,
                description="Task that calls plugin method",
                schedule={
                    "mode": "interval",
                    "arguments": {"seconds": 8},
                },
                actions=[
                    TaskActionConfig(
                        type="plugin_method",
                        plugin="task-plugin",
                        method="process_task",
                        args=["plugin-task"],
                    )
                ],
            )
        ]

        config = BotConfig(
            webhooks=get_dummy_webhook(),
            plugins=PluginConfig(
                enabled=True,
                plugin_dir=str(plugin_dir),
            ),
            tasks=tasks,
        )

        bot = FeishuBot(config)
        bot.start()
        print("\n✅ Bot started with plugin-integrated task")
        print("   • Task calls: task-plugin.process_task()")

        print("\n⏳ Waiting 20 seconds...")
        time.sleep(20)

        bot.stop()
        print("\n✅ Bot stopped")


def demo_cron_based_task() -> None:
    """Demonstrate cron-based task scheduling."""
    print("\n" + "=" * 70)
    print("Demo 6: Cron-Based Task")
    print("=" * 70)

    tasks = [
        TaskDefinitionConfig(
            name="cron-task",
            enabled=True,
            description="Task scheduled with cron expression",
            cron="* * * * *",  # Every minute
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="📅 Cron task executed (every minute)",
                )
            ],
        )
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        tasks=tasks,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with cron-based task")
    print("   • Cron: * * * * * (every minute)")

    print("\n⏳ Waiting 65 seconds to see execution...")
    time.sleep(65)

    bot.stop()
    print("\n✅ Bot stopped")


def demo_multiple_actions() -> None:
    """Demonstrate task with multiple actions."""
    print("\n" + "=" * 70)
    print("Demo 7: Task with Multiple Actions")
    print("=" * 70)

    tasks = [
        TaskDefinitionConfig(
            name="multi-action-task",
            enabled=True,
            description="Task with multiple sequential actions",
            schedule={
                "mode": "interval",
                "arguments": {"seconds": 12},
            },
            actions=[
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="1️⃣ First action",
                ),
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="2️⃣ Second action",
                ),
                TaskActionConfig(
                    type="send_message",
                    webhook="default",
                    message="3️⃣ Third action",
                ),
            ],
        )
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        tasks=tasks,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with multi-action task")
    print("   • 3 actions will execute sequentially")

    print("\n⏳ Waiting 15 seconds...")
    time.sleep(15)

    bot.stop()
    print("\n✅ Bot stopped")


# ============================================================================
# Main Demo Runner
# ============================================================================


def main() -> None:
    """Run all task manager demonstrations."""
    print("\n" + "=" * 70)
    print("FEISHU WEBHOOK BOT - TASK MANAGER DEMONSTRATION")
    print("=" * 70)

    demos = [
        ("Basic Task", demo_basic_task),
        ("Task with Conditions", demo_task_with_conditions),
        ("Task with Retry", demo_task_with_retry),
        ("Task Dependencies", demo_task_dependencies),
        ("Task with Plugin", demo_task_with_plugin),
        ("Cron-Based Task", demo_cron_based_task),
        ("Multiple Actions", demo_multiple_actions),
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
    print("• Tasks automate recurring workflows")
    print("• Tasks support both interval and cron scheduling")
    print("• Conditions control when tasks execute")
    print("• Retry logic handles transient failures")
    print("• Task dependencies ensure proper execution order")
    print("• Tasks integrate with plugins for extended functionality")
    print("• Multiple actions can be chained in a single task")


if __name__ == "__main__":
    main()
