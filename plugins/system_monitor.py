"""Example plugin: System Status Monitor.

This plugin monitors system status and sends alerts periodically.
Demonstrates plugin configuration schema support.
"""

import platform
from datetime import datetime

import psutil
from pydantic import Field

from feishu_webhook_bot.core.client import CardBuilder
from feishu_webhook_bot.plugins import BasePlugin, PluginMetadata, PluginPermission
from feishu_webhook_bot.plugins.config_schema import PluginConfigSchema


class SystemMonitorConfig(PluginConfigSchema):
    """Configuration schema for System Monitor plugin."""

    cpu_threshold: float = Field(
        default=80.0,
        description="CPU usage alert threshold (%)",
        ge=0,
        le=100,
    )
    memory_threshold: float = Field(
        default=85.0,
        description="Memory usage alert threshold (%)",
        ge=0,
        le=100,
    )
    disk_threshold: float = Field(
        default=90.0,
        description="Disk usage alert threshold (%)",
        ge=0,
        le=100,
    )
    report_interval_minutes: int = Field(
        default=60,
        description="Status report interval in minutes",
        ge=1,
        le=1440,
    )
    alert_interval_minutes: int = Field(
        default=5,
        description="Alert check interval in minutes",
        ge=1,
        le=60,
    )
    enable_reports: bool = Field(
        default=True,
        description="Enable periodic status reports",
    )
    enable_alerts: bool = Field(
        default=True,
        description="Enable system alerts",
    )


class SystemMonitorPlugin(BasePlugin):
    """Plugin that monitors system resources and sends periodic reports."""

    # Link configuration schema
    config_schema = SystemMonitorConfig

    # Declare required permissions
    PERMISSIONS = [
        PluginPermission.NETWORK_SEND,  # Send messages via webhook
        PluginPermission.SYSTEM_INFO,  # Access system information
        PluginPermission.SCHEDULER_JOBS,  # Register scheduled jobs
        PluginPermission.CONFIG_READ,  # Read configuration
    ]

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="system-monitor",
            version="1.1.0",
            description="Monitors system resources (CPU, memory, disk) and sends periodic reports",
            author="Feishu Bot Team",
            enabled=True,
        )

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        self.logger.info("System Monitor plugin loaded")
        # Load thresholds from config or use defaults
        self.alert_threshold_cpu = self.get_config_value("cpu_threshold", 80.0)
        self.alert_threshold_memory = self.get_config_value("memory_threshold", 85.0)
        self.alert_threshold_disk = self.get_config_value("disk_threshold", 90.0)

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        # Get config values
        enable_reports = self.get_config_value("enable_reports", True)
        enable_alerts = self.get_config_value("enable_alerts", True)
        report_interval = self.get_config_value("report_interval_minutes", 60)
        alert_interval = self.get_config_value("alert_interval_minutes", 5)

        # Send status report based on config
        if enable_reports:
            if report_interval == 60:
                # Every hour at :00
                self.register_job(
                    self.send_status_report,
                    trigger="cron",
                    minute="0",
                    job_id="system_monitor_hourly",
                )
            else:
                # Custom interval
                self.register_job(
                    self.send_status_report,
                    trigger="interval",
                    minutes=report_interval,
                    job_id="system_monitor_report",
                )

        # Check for alerts based on config
        if enable_alerts:
            self.register_job(
                self.check_alerts,
                trigger="interval",
                minutes=alert_interval,
                job_id="system_monitor_alerts",
            )

        self.logger.info(
            f"System monitoring scheduled (reports={enable_reports}, alerts={enable_alerts})"
        )

    def get_system_info(self) -> dict:
        """Get current system information.

        Returns:
            Dictionary with system stats
        """
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # Memory
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)

            # Disk
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)

            # System info
            system_info = {
                "hostname": platform.node(),
                "system": f"{platform.system()} {platform.release()}",
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "memory_percent": memory_percent,
                "memory_used_gb": round(memory_used_gb, 2),
                "memory_total_gb": round(memory_total_gb, 2),
                "disk_percent": disk_percent,
                "disk_used_gb": round(disk_used_gb, 2),
                "disk_total_gb": round(disk_total_gb, 2),
            }

            return system_info

        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {}

    def send_status_report(self) -> None:
        """Send periodic status report."""
        try:
            info = self.get_system_info()
            if not info:
                return

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Build status card
            card = (
                CardBuilder()
                .set_config(wide_screen_mode=True)
                .set_header("📊 System Status Report", template="blue")
                .add_markdown(
                    f"**Hostname:** {info['hostname']}\n"
                    f"**System:** {info['system']}\n"
                    f"**Time:** {timestamp}"
                )
                .add_divider()
                .add_markdown(
                    f"**CPU Usage:** {info['cpu_percent']}% ({info['cpu_count']} cores)\n"
                    f"**Memory:** {info['memory_used_gb']} GB / "
                    f"{info['memory_total_gb']} GB ({info['memory_percent']}%)\n"
                    f"**Disk:** {info['disk_used_gb']} GB / "
                    f"{info['disk_total_gb']} GB ({info['disk_percent']}%)"
                )
                .add_note("Hourly system status report")
                .build()
            )

            self.client.send_card(card)
            self.logger.info("Status report sent successfully")

        except Exception as e:
            self.logger.error(f"Failed to send status report: {e}", exc_info=True)

    def check_alerts(self) -> None:
        """Check for system alerts and send notifications."""
        try:
            info = self.get_system_info()
            if not info:
                return

            alerts = []

            # Check CPU
            if info["cpu_percent"] > self.alert_threshold_cpu:
                alerts.append(
                    f"⚠️ **High CPU Usage:** {info['cpu_percent']}% "
                    f"(threshold: {self.alert_threshold_cpu}%)"
                )

            # Check Memory
            if info["memory_percent"] > self.alert_threshold_memory:
                alerts.append(
                    f"⚠️ **High Memory Usage:** {info['memory_percent']}% "
                    f"(threshold: {self.alert_threshold_memory}%)"
                )

            # Check Disk
            if info["disk_percent"] > self.alert_threshold_disk:
                alerts.append(
                    f"⚠️ **High Disk Usage:** {info['disk_percent']}% "
                    f"(threshold: {self.alert_threshold_disk}%)"
                )

            # Send alert if any issues found
            if alerts:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                alert_text = "\n".join(alerts)

                card = (
                    CardBuilder()
                    .set_config(wide_screen_mode=True)
                    .set_header("🚨 System Alert", template="red")
                    .add_markdown(f"**Time:** {timestamp}\n**Host:** {info['hostname']}")
                    .add_divider()
                    .add_markdown(alert_text)
                    .add_note("Please check system resources")
                    .build()
                )

                self.client.send_card(card)
                self.logger.warning(f"System alert sent: {len(alerts)} issues detected")

        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}", exc_info=True)

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        self.logger.info("System Monitor plugin disabled")
