"""Comprehensive demonstration of the Automation Engine.

This example demonstrates:
1. Declarative workflow definitions
2. Schedule-based and event-based triggers
3. Action types (send messages, HTTP requests, plugin methods, Python code)
4. Template rendering with variable substitution
5. Condition evaluation
6. Workflow chaining and dependencies

Run this example:
    python examples/automation_demo.py
"""

import tempfile
import time
from pathlib import Path

from feishu_webhook_bot import FeishuBot
from feishu_webhook_bot.core.config import (
    AutomationActionConfig,
    AutomationRule,
    AutomationScheduleConfig,
    AutomationTriggerConfig,
    BotConfig,
    PluginConfig,
    TemplateConfig,
    WebhookConfig,
)


def get_dummy_webhook() -> list[WebhookConfig]:
    """Get a dummy webhook configuration for demos.

    Note: Uses httpbin.org which accepts POST requests, allowing demos
    to run without actual Feishu webhook configuration.
    """
    return [
        WebhookConfig(
            name="default",
            url="https://httpbin.org/post",
        )
    ]


# ============================================================================
# Demo Functions
# ============================================================================


def demo_schedule_based_automation() -> None:
    """Demonstrate schedule-based automation rules."""
    print("\n" + "=" * 70)
    print("Demo 1: Schedule-Based Automation")
    print("=" * 70)

    # Define automation rules
    rules = [
        AutomationRule(
            name="morning-greeting",
            enabled=True,
            trigger=AutomationTriggerConfig(
                type="schedule",
                schedule=AutomationScheduleConfig(
                    mode="interval",
                    arguments={"seconds": 5},
                ),
            ),
            actions=[
                AutomationActionConfig(
                    type="send_text",
                    webhook="default",
                    text="🌅 Good morning! This is an automated message.",
                )
            ],
        ),
        AutomationRule(
            name="status-check",
            enabled=True,
            trigger=AutomationTriggerConfig(
                type="schedule",
                schedule=AutomationScheduleConfig(
                    mode="interval",
                    arguments={"seconds": 10},
                ),
            ),
            actions=[
                AutomationActionConfig(
                    type="send_text",
                    webhook="default",
                    text="✅ System status: All services running normally",
                )
            ],
        ),
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        automations=rules,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with 2 automation rules")
    print("   • morning-greeting: Runs every 5 seconds")
    print("   • status-check: Runs every 10 seconds")

    print("\n⏳ Waiting 25 seconds to see automations...")
    time.sleep(25)

    bot.stop()
    print("\n✅ Bot stopped")


def demo_template_rendering() -> None:
    """Demonstrate template rendering with variable substitution."""
    print("\n" + "=" * 70)
    print("Demo 2: Template Rendering")
    print("=" * 70)

    # Define templates
    templates = [
        TemplateConfig(
            name="daily-report",
            type="text",
            content="📊 Daily Report\nDate: ${date}\nTasks: ${task_count}\nStatus: ${status}",
        ),
        TemplateConfig(
            name="alert",
            type="text",
            content="🚨 ALERT: ${alert_type}\nSeverity: ${severity}\nMessage: ${message}",
        ),
    ]

    # Define automation rule using template
    rules = [
        AutomationRule(
            name="daily-report",
            enabled=True,
            trigger=AutomationTriggerConfig(
                type="schedule",
                schedule=AutomationScheduleConfig(
                    mode="interval",
                    arguments={"seconds": 8},
                ),
            ),
            actions=[
                AutomationActionConfig(
                    type="send_template",
                    webhook="default",
                    template="daily-report",
                    variables={
                        "date": "2024-01-15",
                        "task_count": "42",
                        "status": "Completed",
                    },
                )
            ],
        )
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        templates=templates,
        automations=rules,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with template-based automation")
    print("✅ Templates defined:")
    print("   • daily-report")
    print("   • alert")

    print("\n⏳ Waiting 20 seconds to see template rendering...")
    time.sleep(20)

    bot.stop()
    print("\n✅ Bot stopped")


def demo_http_request_action() -> None:
    """Demonstrate HTTP request actions."""
    print("\n" + "=" * 70)
    print("Demo 3: HTTP Request Actions")
    print("=" * 70)

    rules = [
        AutomationRule(
            name="api-health-check",
            enabled=True,
            trigger=AutomationTriggerConfig(
                type="schedule",
                schedule=AutomationScheduleConfig(
                    mode="interval",
                    arguments={"seconds": 15},
                ),
            ),
            actions=[
                # Make HTTP request
                AutomationActionConfig(
                    type="http_request",
                    http_request={
                        "url": "https://httpbin.org/get",
                        "method": "GET",
                        "timeout": 10,
                    },
                ),
                # Send result notification
                AutomationActionConfig(
                    type="send_text",
                    webhook="default",
                    text="✅ API health check completed",
                ),
            ],
        )
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        automations=rules,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with HTTP request automation")
    print("   • Makes GET request to https://httpbin.org/get")
    print("   • Sends notification after request")

    print("\n⏳ Waiting 20 seconds...")
    time.sleep(20)

    bot.stop()
    print("\n✅ Bot stopped")


def demo_python_code_action() -> None:
    """Demonstrate Python code execution actions."""
    print("\n" + "=" * 70)
    print("Demo 4: Python Code Actions")
    print("=" * 70)

    rules = [
        AutomationRule(
            name="calculate-stats",
            enabled=True,
            trigger=AutomationTriggerConfig(
                type="schedule",
                schedule=AutomationScheduleConfig(
                    mode="interval",
                    arguments={"seconds": 10},
                ),
            ),
            actions=[
                AutomationActionConfig(
                    type="python_code",
                    code="""
import random
result = random.randint(1, 100)
print(f"Generated random number: {result}")
""",
                ),
                AutomationActionConfig(
                    type="send_text",
                    webhook="default",
                    text="🎲 Random number generated (check logs)",
                ),
            ],
        )
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        automations=rules,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with Python code automation")
    print("   • Executes Python code to generate random numbers")

    print("\n⏳ Waiting 25 seconds...")
    time.sleep(25)

    bot.stop()
    print("\n✅ Bot stopped")


def demo_plugin_method_action() -> None:
    """Demonstrate calling plugin methods from automation."""
    print("\n" + "=" * 70)
    print("Demo 5: Plugin Method Actions")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir)

        # Create a plugin with callable methods
        plugin_file = plugin_dir / "automation_plugin.py"
        plugin_code = '''
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata

class AutomationPlugin(BasePlugin):
    def metadata(self):
        return PluginMetadata(name="automation-demo", version="1.0.0")

    def process_data(self):
        """Method that can be called from automation."""
        self.logger.info("Processing data from automation!")
        self.client.send_text("📊 Data processed by plugin!")
        return {"status": "success", "records": 42}

    def send_report(self):
        """Another callable method."""
        self.logger.info("Sending report from automation!")
        self.client.send_text("📈 Report sent by plugin!")
'''
        plugin_file.write_text(plugin_code)

        # Define automation rule that calls plugin method
        rules = [
            AutomationRule(
                name="call-plugin",
                enabled=True,
                trigger=AutomationTriggerConfig(
                    type="schedule",
                    schedule=AutomationScheduleConfig(
                        mode="interval",
                        arguments={"seconds": 8},
                    ),
                ),
                actions=[
                    AutomationActionConfig(
                        type="plugin_method",
                        plugin="automation-demo",
                        method="process_data",
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
            automations=rules,
        )

        bot = FeishuBot(config)
        bot.start()
        print("\n✅ Bot started with plugin method automation")
        print("   • Calls plugin method: automation-demo.process_data()")

        print("\n⏳ Waiting 20 seconds...")
        time.sleep(20)

        bot.stop()
        print("\n✅ Bot stopped")


def demo_conditional_execution() -> None:
    """Demonstrate conditional execution with conditions."""
    print("\n" + "=" * 70)
    print("Demo 6: Conditional Execution")
    print("=" * 70)

    import os

    # Set environment variable for condition
    os.environ["AUTOMATION_ENABLED"] = "true"

    rules = [
        AutomationRule(
            name="conditional-task",
            enabled=True,
            trigger=AutomationTriggerConfig(
                type="schedule",
                schedule=AutomationScheduleConfig(
                    mode="interval",
                    arguments={"seconds": 7},
                ),
            ),
            conditions=[{"type": "env", "variable": "AUTOMATION_ENABLED", "value": "true"}],
            actions=[
                AutomationActionConfig(
                    type="send_text",
                    webhook="default",
                    text="✅ Condition met! Task executed.",
                )
            ],
        )
    ]

    config = BotConfig(
        webhooks=get_dummy_webhook(),
        automations=rules,
    )

    bot = FeishuBot(config)
    bot.start()
    print("\n✅ Bot started with conditional automation")
    print("   • Condition: AUTOMATION_ENABLED=true")
    print("   • Task will only run if condition is met")

    print("\n⏳ Waiting 20 seconds...")
    time.sleep(20)

    bot.stop()
    print("\n✅ Bot stopped")

    # Clean up
    del os.environ["AUTOMATION_ENABLED"]


# ============================================================================
# Main Demo Runner
# ============================================================================


def main() -> None:
    """Run all automation engine demonstrations."""
    print("\n" + "=" * 70)
    print("FEISHU WEBHOOK BOT - AUTOMATION ENGINE DEMONSTRATION")
    print("=" * 70)

    demos = [
        ("Schedule-Based Automation", demo_schedule_based_automation),
        ("Template Rendering", demo_template_rendering),
        ("HTTP Request Actions", demo_http_request_action),
        ("Python Code Actions", demo_python_code_action),
        ("Plugin Method Actions", demo_plugin_method_action),
        ("Conditional Execution", demo_conditional_execution),
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
    print("• Automation rules define declarative workflows")
    print("• Schedule-based triggers run at specified intervals or cron times")
    print("• Actions include: send messages, HTTP requests, Python code, plugin methods")
    print("• Templates support variable substitution for dynamic content")
    print("• Conditions control when automations execute")
    print("• Multiple actions can be chained in a single rule")


if __name__ == "__main__":
    main()
