"""RSS Subscription Plugin Example with Daily Report.

This example demonstrates how to configure and use the RSS subscription plugin
with AI-powered summarization and daily report generation.

Features demonstrated:
1. Multiple RSS feed configuration
2. AI-powered content summarization and classification
3. Daily report generation with trend analysis
4. Beautiful card templates
5. Command interface usage

Run this example:
    python examples/plugins/rss_subscription_example.py
"""

from feishu_webhook_bot.core.config import PluginSettingsConfig


def get_rss_plugin_config() -> PluginSettingsConfig:
    """Get RSS subscription plugin configuration.

    Returns:
        PluginSettingsConfig for RSS plugin
    """
    return PluginSettingsConfig(
        plugin_name="rss-subscription",
        enabled=True,
        priority=10,
        settings={
            # Feed Management
            "feeds": [
                {
                    "name": "Hacker News",
                    "url": "https://hnrss.org/frontpage",
                    "check_interval_minutes": 30,
                    "enabled": True,
                    "max_entries": 10,
                    "tags": ["tech", "news"],
                },
                {
                    "name": "GitHub Trending",
                    "url": "https://rsshub.app/github/trending/daily/all",
                    "check_interval_minutes": 60,
                    "enabled": True,
                    "max_entries": 10,
                    "tags": ["github", "opensource"],
                },
                {
                    "name": "TechCrunch",
                    "url": "https://techcrunch.com/feed/",
                    "check_interval_minutes": 30,
                    "enabled": True,
                    "max_entries": 8,
                    "tags": ["tech", "startup"],
                },
            ],
            "default_check_interval_minutes": 30,
            # AI Settings
            "ai_enabled": True,
            "ai_summarization": True,
            "ai_classification": True,
            "ai_keyword_extraction": True,
            "ai_max_summary_length": 150,
            # Aggregation Settings
            "aggregation_enabled": True,
            "aggregation_max_entries": 5,
            "aggregation_window_minutes": 5,
            # Notification Settings
            "webhook_name": "default",
            "card_template": "detailed",
            # Storage
            "history_days": 7,
            # Daily Report Settings
            "daily_report_enabled": True,
            "daily_report_time": "09:00",
            "daily_report_ai_summary": True,
            "daily_report_max_entries": 20,
            "daily_report_include_trends": True,
        },
    )


def print_yaml_config() -> None:
    """Print example YAML configuration for RSS plugin."""
    yaml_config = """
# RSS Subscription Plugin Configuration Example
# Add this to your config.yaml under plugins.plugin_settings

plugins:
  enabled: true
  plugin_dir: "./plugins"
  plugin_settings:
    - plugin_name: "rss-subscription"
      enabled: true
      priority: 10
      settings:
        # ========== Feed Management ==========
        feeds:
          - name: "Hacker News"
            url: "https://hnrss.org/frontpage"
            check_interval_minutes: 30
            enabled: true
            max_entries: 10
            tags: ["tech", "news"]

          - name: "GitHub Trending"
            url: "https://rsshub.app/github/trending/daily/all"
            check_interval_minutes: 60
            enabled: true
            max_entries: 10
            tags: ["github", "opensource"]

          - name: "36氪"
            url: "https://rsshub.app/36kr/newsflashes"
            check_interval_minutes: 30
            enabled: true
            max_entries: 10
            tags: ["chinese", "tech"]

        default_check_interval_minutes: 30

        # ========== AI Processing ==========
        ai_enabled: true
        ai_summarization: true
        ai_classification: true
        ai_keyword_extraction: true
        ai_max_summary_length: 150

        # ========== Aggregation ==========
        aggregation_enabled: true
        aggregation_max_entries: 5
        aggregation_window_minutes: 5

        # ========== Notifications ==========
        webhook_name: "default"
        card_template: "detailed"  # minimal, compact, detailed, full

        # ========== Storage ==========
        history_days: 7

        # ========== Daily Report ==========
        daily_report_enabled: true
        daily_report_time: "09:00"
        daily_report_ai_summary: true
        daily_report_max_entries: 20
        daily_report_include_trends: true
"""
    print(yaml_config)


def print_commands_help() -> None:
    """Print RSS plugin commands reference."""
    print("\n" + "=" * 60)
    print("RSS Plugin Commands Reference")
    print("=" * 60)
    print("""
/rss add <url> [name]     - Add a new RSS feed
/rss remove <name|url>    - Remove a feed
/rss list                 - List all feeds
/rss check [name]         - Check for updates
/rss daily [date]         - Generate daily report
/rss status               - Show plugin status
/rss help                 - Show help
""")


def print_card_templates() -> None:
    """Print card template descriptions."""
    print("\n" + "=" * 60)
    print("Card Template Styles")
    print("=" * 60)
    print("""
1. minimal  - Title and link only
2. compact  - Title, link, brief summary
3. detailed - Full summary with categories (default)
4. full     - Everything including keywords

Daily Report Card includes:
- AI-generated summary
- Hot topics tags
- Trend analysis
- Category distribution
- Content grouped by feed
""")


def main() -> None:
    """Run RSS plugin configuration demo."""
    print("=" * 60)
    print("RSS Subscription Plugin - Configuration Example")
    print("=" * 60)

    print("\n1. Example YAML Configuration:")
    print_yaml_config()

    print_commands_help()
    print_card_templates()

    print("\n" + "=" * 60)
    print("To use this plugin:")
    print("1. Add the configuration to your config.yaml")
    print("2. Enable AI if you want summarization features")
    print("3. The plugin will auto-check feeds at configured intervals")
    print("4. Daily reports are sent at the configured time")
    print("=" * 60)


if __name__ == "__main__":
    main()
