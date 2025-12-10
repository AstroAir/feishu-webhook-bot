"""Feishu Calendar Subscription Plugin.

This plugin provides comprehensive calendar integration with Feishu:
- Periodically checking Feishu calendar events
- Sending reminders for upcoming events
- Supporting multiple calendars and reminder times
- Beautiful card-based event display
- Calendar list retrieval
- Event details fetching
- Daily/weekly agenda summaries
- Using Feishu Open Platform API for calendar access
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from enum import Enum
from typing import Any

import httpx

from ..core.client import CardBuilder
from ..core.logger import get_logger
from .base import BasePlugin, PluginMetadata
from .config_schema import (
    ConfigSchemaBuilder,
    FieldType,
    PluginConfigSchema,
)
from .manifest import (
    PackageDependency,
    PermissionRequest,
    PermissionType,
    PluginManifest,
)

logger = get_logger("plugin.feishu-calendar")


# ========== Configuration Schema for Feishu Calendar Plugin ==========


class FeishuCalendarConfigSchema(PluginConfigSchema):
    """Configuration schema for the Feishu Calendar plugin.

    This schema defines all configurable options for the calendar plugin,
    including credentials, calendars to monitor, reminder settings, etc.
    """

    @classmethod
    def get_schema_fields(cls) -> dict[str, Any]:
        """Return all field definitions."""
        builder = ConfigSchemaBuilder()

        # Authentication fields (required)
        builder.add_field(
            name="app_id",
            field_type=FieldType.SECRET,
            description="Feishu application ID",
            required=True,
            env_var="FEISHU_APP_ID",
            example="cli_xxxxxxxxxxxxx",
            help_url="https://open.feishu.cn/app",
        )

        builder.add_field(
            name="app_secret",
            field_type=FieldType.SECRET,
            description="Feishu application secret",
            required=True,
            sensitive=True,
            env_var="FEISHU_APP_SECRET",
            example="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            help_url="https://open.feishu.cn/app",
        )

        # Calendar configuration
        builder.add_field(
            name="calendar_ids",
            field_type=FieldType.LIST,
            description="Calendar IDs to monitor (use 'primary' for default calendar)",
            required=False,
            default=["primary"],
            example="primary, cal_xxxxxxxxx",
        )

        builder.add_field(
            name="check_interval_minutes",
            field_type=FieldType.INT,
            description="How often to check for events (in minutes)",
            required=False,
            default=5,
            min_value=1,
            max_value=60,
        )

        # Reminder configuration
        builder.add_field(
            name="reminder_minutes",
            field_type=FieldType.LIST,
            description="When to send reminders before events (minutes)",
            required=False,
            default=[15, 5],
            example="30, 15, 5",
        )

        # Webhook configuration
        builder.add_field(
            name="webhook_name",
            field_type=FieldType.STRING,
            description="Webhook to use for sending notifications",
            required=False,
            default="default",
        )

        # Timezone configuration
        builder.add_field(
            name="timezone_offset",
            field_type=FieldType.INT,
            description="Timezone offset from UTC (in hours)",
            required=False,
            default=8,
            min_value=-12,
            max_value=14,
            example="8",
        )

        # Daily summary configuration
        builder.add_field(
            name="daily_summary_enabled",
            field_type=FieldType.BOOL,
            description="Enable daily event summary notification",
            required=False,
            default=False,
        )

        builder.add_field(
            name="daily_summary_hour",
            field_type=FieldType.INT,
            description="Hour to send daily summary (0-23)",
            required=False,
            default=8,
            min_value=0,
            max_value=23,
            depends_on="daily_summary_enabled",
        )

        return builder.build()

    @classmethod
    def get_field_groups(cls) -> dict[str, list[str]]:
        """Return field groups for organized display."""
        return {
            "Authentication": ["app_id", "app_secret"],
            "Calendars": ["calendar_ids", "check_interval_minutes"],
            "Reminders": ["reminder_minutes"],
            "Notifications": ["webhook_name"],
            "Timezone": ["timezone_offset"],
            "Daily Summary": ["daily_summary_enabled", "daily_summary_hour"],
        }


class EventStatus(Enum):
    """Event status enumeration."""

    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class EventVisibility(Enum):
    """Event visibility enumeration."""

    DEFAULT = "default"
    PUBLIC = "public"
    PRIVATE = "private"


class AttendeeStatus(Enum):
    """Attendee response status."""

    NEEDS_ACTION = "needs_action"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    REMOVED = "removed"


@dataclass
class CalendarInfo:
    """Calendar information structure."""

    calendar_id: str
    summary: str = ""
    description: str = ""
    color: str = ""
    type: str = ""  # primary, shared, resource, etc.
    role: str = ""  # owner, writer, reader
    is_primary: bool = False

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "CalendarInfo":
        """Create from Feishu API response."""
        return cls(
            calendar_id=data.get("calendar_id", ""),
            summary=data.get("summary", ""),
            description=data.get("description", ""),
            color=data.get("color", ""),
            type=data.get("type", ""),
            role=data.get("role", ""),
            is_primary=data.get("calendar_id") == "primary",
        )


@dataclass
class EventAttendee:
    """Event attendee information."""

    user_id: str = ""
    display_name: str = ""
    email: str = ""
    status: AttendeeStatus = AttendeeStatus.NEEDS_ACTION
    is_optional: bool = False
    is_organizer: bool = False
    is_external: bool = False

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "EventAttendee":
        """Create from Feishu API response."""
        status_str = data.get("rsvp_status", "needs_action")
        try:
            status = AttendeeStatus(status_str)
        except ValueError:
            status = AttendeeStatus.NEEDS_ACTION

        return cls(
            user_id=data.get("user_id", ""),
            display_name=data.get("display_name", ""),
            email=data.get("email", ""),
            status=status,
            is_optional=data.get("is_optional", False),
            is_organizer=data.get("is_organizer", False),
            is_external=data.get("is_external", False),
        )


@dataclass
class EventLocation:
    """Event location information."""

    name: str = ""
    address: str = ""
    latitude: float | None = None
    longitude: float | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any] | str | None) -> "EventLocation":
        """Create from Feishu API response."""
        if data is None:
            return cls()
        if isinstance(data, str):
            return cls(name=data)
        return cls(
            name=data.get("name", "") or data.get("display_name", ""),
            address=data.get("address", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
        )


@dataclass
class EventVChat:
    """Video conference information."""

    vc_type: str = ""  # vc (Feishu Meeting), third_party, no_meeting
    meeting_url: str = ""
    meeting_settings: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: dict[str, Any] | None) -> "EventVChat":
        """Create from Feishu API response."""
        if data is None:
            return cls()
        return cls(
            vc_type=data.get("vc_type", ""),
            meeting_url=data.get("meeting_url", ""),
            meeting_settings=data.get("meeting_settings", {}),
        )


@dataclass
class CalendarEvent:
    """Calendar event information with full details."""

    event_id: str
    summary: str = ""
    description: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_all_day: bool = False
    timezone: str = "Asia/Shanghai"

    # Status and visibility
    status: EventStatus = EventStatus.CONFIRMED
    visibility: EventVisibility = EventVisibility.DEFAULT

    # Organizer
    organizer_id: str = ""
    organizer_name: str = ""

    # Location and meeting
    location: EventLocation = field(default_factory=EventLocation)
    vchat: EventVChat = field(default_factory=EventVChat)

    # Attendees
    attendees: list[EventAttendee] = field(default_factory=list)

    # Recurrence
    recurrence: str = ""  # RRULE string
    recurring_event_id: str = ""

    # Colors and UI
    color: str = ""

    # Reminders
    reminders: list[int] = field(default_factory=list)  # minutes before event

    # Additional metadata
    create_time: datetime | None = None
    update_time: datetime | None = None
    calendar_id: str = ""

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], calendar_id: str = ""
    ) -> "CalendarEvent":
        """Create from Feishu API response."""
        # Parse start time
        start_time_data = data.get("start_time", {})
        start_time = None
        is_all_day = False
        tz_str = "Asia/Shanghai"

        if isinstance(start_time_data, dict):
            if start_time_data.get("date"):
                # All-day event
                is_all_day = True
                try:
                    start_time = datetime.strptime(
                        start_time_data["date"], "%Y-%m-%d"
                    ).replace(tzinfo=UTC)
                except ValueError:
                    pass
            elif start_time_data.get("timestamp"):
                start_time = datetime.fromtimestamp(
                    int(start_time_data["timestamp"]), tz=UTC
                )
            tz_str = start_time_data.get("timezone", "Asia/Shanghai")
        elif start_time_data:
            try:
                start_time = datetime.fromtimestamp(int(start_time_data), tz=UTC)
            except (ValueError, TypeError):
                pass

        # Parse end time
        end_time_data = data.get("end_time", {})
        end_time = None
        if isinstance(end_time_data, dict):
            if end_time_data.get("date"):
                try:
                    end_time = datetime.strptime(
                        end_time_data["date"], "%Y-%m-%d"
                    ).replace(tzinfo=UTC)
                except ValueError:
                    pass
            elif end_time_data.get("timestamp"):
                end_time = datetime.fromtimestamp(
                    int(end_time_data["timestamp"]), tz=UTC
                )
        elif end_time_data:
            try:
                end_time = datetime.fromtimestamp(int(end_time_data), tz=UTC)
            except (ValueError, TypeError):
                pass

        # Parse status
        status_str = data.get("status", "confirmed")
        try:
            status = EventStatus(status_str)
        except ValueError:
            status = EventStatus.CONFIRMED

        # Parse visibility
        visibility_str = data.get("visibility", "default")
        try:
            visibility = EventVisibility(visibility_str)
        except ValueError:
            visibility = EventVisibility.DEFAULT

        # Parse organizer
        organizer_data = data.get("organizer", {})
        organizer_id = organizer_data.get("user_id", "")
        organizer_name = organizer_data.get("display_name", "")

        # Parse attendees
        attendees_data = data.get("attendees", [])
        attendees = [EventAttendee.from_api_response(a) for a in attendees_data]

        # Parse reminders
        reminders_data = data.get("reminders", [])
        reminders = []
        for r in reminders_data:
            if isinstance(r, dict):
                minutes = r.get("minutes", 0)
            else:
                minutes = int(r) if r else 0
            if minutes:
                reminders.append(minutes)

        # Parse timestamps
        create_time = None
        if data.get("create_time"):
            try:
                create_time = datetime.fromtimestamp(
                    int(data["create_time"]), tz=UTC
                )
            except (ValueError, TypeError):
                pass

        update_time = None
        if data.get("update_time"):
            try:
                update_time = datetime.fromtimestamp(
                    int(data["update_time"]), tz=UTC
                )
            except (ValueError, TypeError):
                pass

        return cls(
            event_id=data.get("event_id", ""),
            summary=data.get("summary", ""),
            description=data.get("description", ""),
            start_time=start_time,
            end_time=end_time,
            is_all_day=is_all_day,
            timezone=tz_str,
            status=status,
            visibility=visibility,
            organizer_id=organizer_id,
            organizer_name=organizer_name,
            location=EventLocation.from_api_response(data.get("location")),
            vchat=EventVChat.from_api_response(data.get("vchat")),
            attendees=attendees,
            recurrence=data.get("recurrence", ""),
            recurring_event_id=data.get("recurring_event_id", ""),
            color=data.get("color", ""),
            reminders=reminders,
            create_time=create_time,
            update_time=update_time,
            calendar_id=calendar_id,
        )

    def get_duration_str(self) -> str:
        """Get formatted duration string."""
        if not self.start_time or not self.end_time:
            return ""
        duration = self.end_time - self.start_time
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes = remainder // 60
        if hours > 0:
            return f"{hours}小时{minutes}分钟" if minutes > 0 else f"{hours}小时"
        return f"{minutes}分钟"

    def get_time_range_str(self, tz: timezone | None = None) -> str:
        """Get formatted time range string."""
        if not self.start_time:
            return "未知时间"

        # Use local timezone if not specified
        if tz is None:
            tz = timezone(timedelta(hours=8))  # Default to Asia/Shanghai

        start = self.start_time.astimezone(tz)

        if self.is_all_day:
            if self.end_time:
                end = self.end_time.astimezone(tz)
                if start.date() == end.date():
                    return start.strftime("%Y-%m-%d") + " (全天)"
                return f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')} (全天)"
            return start.strftime("%Y-%m-%d") + " (全天)"

        if self.end_time:
            end = self.end_time.astimezone(tz)
            if start.date() == end.date():
                return f"{start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%H:%M')}"
            return f"{start.strftime('%Y-%m-%d %H:%M')} ~ {end.strftime('%m-%d %H:%M')}"

        return start.strftime("%Y-%m-%d %H:%M")

    def get_attendee_summary(self) -> str:
        """Get attendee summary string."""
        if not self.attendees:
            return ""

        total = len(self.attendees)
        accepted = sum(1 for a in self.attendees if a.status == AttendeeStatus.ACCEPTED)
        declined = sum(1 for a in self.attendees if a.status == AttendeeStatus.DECLINED)
        pending = total - accepted - declined

        parts = []
        if accepted:
            parts.append(f"{accepted}人已接受")
        if declined:
            parts.append(f"{declined}人已拒绝")
        if pending:
            parts.append(f"{pending}人待回复")

        return "，".join(parts) if parts else f"共{total}人"


class FeishuCalendarPlugin(BasePlugin):
    """Plugin for monitoring Feishu calendar events and sending reminders.

    This plugin provides comprehensive calendar integration:
    - Fetches tenant_access_token using app_id and app_secret
    - Retrieves events from configured calendars
    - Tracks already-reminded events to avoid duplicates
    - Sends beautiful reminder cards for upcoming events
    - Supports multiple reminder times per event
    - Calendar list management
    - Event details fetching
    - Daily/weekly agenda summaries
    - Beautiful card-based display

    Configuration in config.yaml:
        ```yaml
        plugins:
          plugin_settings:
            - plugin_name: "feishu-calendar"
              enabled: true
              settings:
                app_id: "${FEISHU_APP_ID}"
                app_secret: "${FEISHU_APP_SECRET}"
                calendar_ids:
                  - "primary"
                check_interval_minutes: 5
                reminder_minutes:
                  - 15
                  - 5
                webhook_name: "default"
                timezone: "Asia/Shanghai"
                daily_summary_hour: 8
                daily_summary_enabled: false
        ```

    Run `feishu-webhook-bot plugin setup feishu-calendar` for interactive configuration.
    """

    # Configuration schema for this plugin
    config_schema = FeishuCalendarConfigSchema

    # Python dependencies required by this plugin
    PYTHON_DEPENDENCIES = [
        PackageDependency(name="httpx", version=">=0.27.0"),
    ]

    # Permissions required by this plugin
    PERMISSIONS = [
        PermissionRequest(
            permission=PermissionType.NETWORK_ACCESS,
            reason="Access Feishu Calendar API to fetch events and send reminders",
            scope="https://open.feishu.cn",
        ),
        PermissionRequest(
            permission=PermissionType.SCHEDULE_JOBS,
            reason="Schedule periodic calendar checks and daily summaries",
        ),
    ]

    # Feishu Open Platform API base URL
    FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

    # Token cache: (token, expiry_timestamp)
    _token_cache: tuple[str, float] | None = None

    # Color mapping for card templates
    COLOR_MAP = {
        "blue": "blue",
        "turquoise": "turquoise",
        "green": "green",
        "yellow": "yellow",
        "orange": "orange",
        "red": "red",
        "carmine": "carmine",
        "violet": "violet",
        "purple": "purple",
        "indigo": "indigo",
        "grey": "grey",
    }

    # Status icons
    STATUS_ICONS = {
        EventStatus.CONFIRMED: "✅",
        EventStatus.TENTATIVE: "⏳",
        EventStatus.CANCELLED: "❌",
    }

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="feishu-calendar",
            version="2.0.0",
            description="Comprehensive Feishu calendar integration with reminders and beautiful cards",
            author="Feishu Bot",
            enabled=True,
        )

    def on_load(self) -> None:
        """Initialize plugin configuration and state."""
        logger.info("Loading Feishu Calendar plugin v2.0")

        # Validate configuration using schema
        is_valid, errors = self.validate_config()
        if not is_valid:
            missing = self.get_missing_config()
            if missing:
                logger.warning(
                    "Plugin 'feishu-calendar' has missing required configuration: %s. "
                    "Run 'feishu-webhook-bot plugin setup feishu-calendar' to configure.",
                    ", ".join(missing),
                )
            for error in errors:
                logger.warning("Configuration error: %s", error)

        # Get configuration
        app_id = self.get_config_value("app_id")
        app_secret = self.get_config_value("app_secret")

        if not app_id or not app_secret:
            logger.error(
                "Missing required configuration: app_id and app_secret. "
                "Run 'feishu-webhook-bot plugin setup feishu-calendar' to configure, "
                "or set FEISHU_APP_ID and FEISHU_APP_SECRET environment variables."
            )
            self._app_id = None
            self._app_secret = None
            return

        self._app_id = app_id
        self._app_secret = app_secret

        # Get calendar configuration
        calendar_ids = self.get_config_value("calendar_ids", ["primary"])
        if isinstance(calendar_ids, str):
            calendar_ids = [calendar_ids]
        self._calendar_ids = calendar_ids

        # Get reminder configuration
        reminder_minutes = self.get_config_value("reminder_minutes", [15, 5])
        if isinstance(reminder_minutes, (int, float)):
            reminder_minutes = [reminder_minutes]
        self._reminder_minutes = sorted(reminder_minutes, reverse=True)

        # Get webhook configuration
        self._webhook_name = self.get_config_value("webhook_name", "default")

        # Get timezone configuration
        tz_offset = self.get_config_value("timezone_offset", 8)
        self._timezone = timezone(timedelta(hours=tz_offset))

        # Daily summary configuration
        self._daily_summary_enabled = self.get_config_value("daily_summary_enabled", False)
        self._daily_summary_hour = self.get_config_value("daily_summary_hour", 8)

        # State tracking for sent reminders: {event_id: {reminder_time_minutes: True}}
        self._reminded_events: dict[str, dict[int, bool]] = {}

        # Cache for calendar info
        self._calendar_cache: dict[str, CalendarInfo] = {}

        logger.info(
            "Feishu Calendar plugin initialized with %d calendars, reminder times: %s minutes",
            len(self._calendar_ids),
            self._reminder_minutes,
        )

    def on_enable(self) -> None:
        """Register the scheduled job for checking events."""
        if not self._app_id or not self._app_secret:
            logger.warning("Feishu Calendar plugin not enabled: missing app_id or app_secret")
            return

        check_interval = self.get_config_value("check_interval_minutes", 5)

        # Register the job to check events periodically
        job_id = f"feishu_calendar_check_{id(self)}"
        try:
            self.register_job(
                self.check_events,
                trigger="interval",
                minutes=check_interval,
                job_id=job_id,
                max_instances=1,
            )
            logger.info("Registered calendar check job every %d minutes", check_interval)
        except Exception as e:
            logger.error("Failed to register calendar check job: %s", e, exc_info=True)

        # Register daily summary job if enabled
        if self._daily_summary_enabled:
            summary_job_id = f"feishu_calendar_daily_summary_{id(self)}"
            try:
                self.register_job(
                    self.send_daily_summary,
                    trigger="cron",
                    hour=self._daily_summary_hour,
                    minute=0,
                    job_id=summary_job_id,
                    max_instances=1,
                )
                logger.info("Registered daily summary job at %d:00", self._daily_summary_hour)
            except Exception as e:
                logger.error("Failed to register daily summary job: %s", e, exc_info=True)

    def on_disable(self) -> None:
        """Clean up when plugin is disabled."""
        self._reminded_events.clear()
        logger.info("Feishu Calendar plugin disabled")

    def _get_tenant_access_token(self) -> str | None:
        """Get tenant_access_token from Feishu API.

        Uses caching to avoid unnecessary API calls (tokens typically valid for 2 hours).

        Returns:
            Tenant access token or None if failed
        """
        # Check cache first
        if self._token_cache is not None:
            token, expiry = self._token_cache
            if time.time() < expiry - 300:  # Refresh 5 minutes before expiry
                return token

        if not self._app_id or not self._app_secret:
            logger.error("app_id or app_secret not configured")
            return None

        try:
            url = f"{self.FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
            payload = {"app_id": self._app_id, "app_secret": self._app_secret}

            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()

            data = response.json()
            if data.get("code") != 0:
                logger.error("Failed to get tenant access token: %s", data.get("msg"))
                return None

            token = data.get("tenant_access_token")
            expires_in = data.get("expire", 7200)

            # Cache the token
            expiry = time.time() + expires_in
            self._token_cache = (token, expiry)

            logger.debug("Got new tenant access token, expires in %d seconds", expires_in)
            return token

        except httpx.HTTPError as e:
            logger.error("HTTP error getting tenant access token: %s", e, exc_info=True)
            return None
        except Exception as e:
            logger.error("Error getting tenant access token: %s", e, exc_info=True)
            return None

    def _get_calendar_events(
        self, calendar_id: str, access_token: str, days_ahead: int = 7
    ) -> list[dict[str, Any]]:
        """Fetch events from a calendar.

        Args:
            calendar_id: Calendar ID to fetch from
            access_token: Tenant access token
            days_ahead: Number of days to look ahead for events

        Returns:
            List of event dictionaries
        """
        try:
            # Calculate time range
            now = datetime.now(tz=UTC)
            start_time = int(now.timestamp())
            end_time = int((now + timedelta(days=days_ahead)).timestamp())

            url = f"{self.FEISHU_API_BASE}/calendar/v4/calendars/{calendar_id}/events"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            params: dict[str, str] = {
                "start_time": str(start_time),
                "end_time": str(end_time),
                "page_size": "100",
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()

            data = response.json()
            if data.get("code") != 0:
                logger.warning(
                    "Failed to get events from calendar %s: %s",
                    calendar_id,
                    data.get("msg"),
                )
                return []

            events = data.get("data", {}).get("items", [])
            logger.debug("Retrieved %d events from calendar %s", len(events), calendar_id)
            return events

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error fetching events from calendar %s: %s",
                calendar_id,
                e,
                exc_info=True,
            )
            return []
        except Exception as e:
            logger.error(
                "Error fetching events from calendar %s: %s",
                calendar_id,
                e,
                exc_info=True,
            )
            return []

    def _should_send_reminder(self, event: dict[str, Any], reminder_minutes: int) -> bool:
        """Check if a reminder should be sent for an event.

        Args:
            event: Event dictionary
            reminder_minutes: Minutes before event to send reminder

        Returns:
            True if reminder should be sent
        """
        event_id = event.get("event_id")
        if not event_id:
            return False

        # Get event start time
        start_time_data = event.get("start_time", {})
        if isinstance(start_time_data, dict):
            start_timestamp = int(start_time_data.get("timestamp", 0))
        else:
            # Handle string timestamp
            try:
                start_timestamp = int(start_time_data)
            except (ValueError, TypeError):
                logger.warning("Invalid start_time format: %s", start_time_data)
                return False

        if start_timestamp == 0:
            return False

        # Calculate time until event
        now = datetime.now(tz=UTC)
        event_time = datetime.fromtimestamp(start_timestamp, tz=UTC)
        time_until_event = (event_time - now).total_seconds() / 60

        # Check if we're in the reminder window
        if time_until_event <= 0:
            # Event has started or passed
            return False

        if time_until_event > reminder_minutes + 2:  # +2 minute buffer
            # Not yet in reminder window
            return False

        # Check if we already sent this reminder
        if event_id not in self._reminded_events:
            self._reminded_events[event_id] = {}

        return not self._reminded_events[event_id].get(reminder_minutes, False)

    def _mark_reminder_sent(self, event_id: str, reminder_minutes: int) -> None:
        """Mark that a reminder has been sent for an event.

        Args:
            event_id: Event ID
            reminder_minutes: Reminder time in minutes
        """
        if event_id not in self._reminded_events:
            self._reminded_events[event_id] = {}
        self._reminded_events[event_id][reminder_minutes] = True

    def _build_reminder_card(self, event: dict[str, Any], reminder_minutes: int) -> dict[str, Any]:
        """Build a beautiful reminder card for an event.

        Args:
            event: Event dictionary from API
            reminder_minutes: Minutes until event

        Returns:
            Card JSON structure
        """
        cal_event = CalendarEvent.from_api_response(event)
        return self.build_event_reminder_card(cal_event, reminder_minutes)

    # ========== New Calendar API Methods ==========

    def get_calendar_list(self, access_token: str | None = None) -> list[CalendarInfo]:
        """Fetch list of calendars for the current user.

        Args:
            access_token: Optional access token (will fetch if not provided)

        Returns:
            List of CalendarInfo objects
        """
        if access_token is None:
            access_token = self._get_tenant_access_token()
        if not access_token:
            logger.error("Cannot get calendar list: no access token")
            return []

        try:
            url = f"{self.FEISHU_API_BASE}/calendar/v4/calendars"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            params = {"page_size": "50"}

            calendars: list[CalendarInfo] = []

            with httpx.Client(timeout=10.0) as client:
                while True:
                    response = client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("code") != 0:
                        logger.warning("Failed to get calendar list: %s", data.get("msg"))
                        break

                    items = data.get("data", {}).get("calendar_list", [])
                    for item in items:
                        cal_info = CalendarInfo.from_api_response(item)
                        calendars.append(cal_info)
                        self._calendar_cache[cal_info.calendar_id] = cal_info

                    # Check for pagination
                    page_token = data.get("data", {}).get("page_token")
                    if not page_token:
                        break
                    params["page_token"] = page_token

            logger.info("Retrieved %d calendars", len(calendars))
            return calendars

        except httpx.HTTPError as e:
            logger.error("HTTP error fetching calendar list: %s", e, exc_info=True)
            return []
        except Exception as e:
            logger.error("Error fetching calendar list: %s", e, exc_info=True)
            return []

    def get_events(
        self,
        calendar_id: str = "primary",
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        days_ahead: int = 7,
        access_token: str | None = None,
    ) -> list[CalendarEvent]:
        """Fetch events from a calendar with full details.

        Args:
            calendar_id: Calendar ID (default "primary")
            start_time: Start of time range (default: now)
            end_time: End of time range (default: start + days_ahead)
            days_ahead: Days to look ahead if end_time not specified
            access_token: Optional access token

        Returns:
            List of CalendarEvent objects
        """
        if access_token is None:
            access_token = self._get_tenant_access_token()
        if not access_token:
            logger.error("Cannot get events: no access token")
            return []

        try:
            now = datetime.now(tz=UTC)
            if start_time is None:
                start_time = now
            if end_time is None:
                end_time = start_time + timedelta(days=days_ahead)

            url = f"{self.FEISHU_API_BASE}/calendar/v4/calendars/{calendar_id}/events"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            params: dict[str, str] = {
                "start_time": str(int(start_time.timestamp())),
                "end_time": str(int(end_time.timestamp())),
                "page_size": "100",
            }

            events: list[CalendarEvent] = []

            with httpx.Client(timeout=10.0) as client:
                while True:
                    response = client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("code") != 0:
                        logger.warning(
                            "Failed to get events from calendar %s: %s",
                            calendar_id,
                            data.get("msg"),
                        )
                        break

                    items = data.get("data", {}).get("items", [])
                    for item in items:
                        event = CalendarEvent.from_api_response(item, calendar_id)
                        events.append(event)

                    # Check for pagination
                    page_token = data.get("data", {}).get("page_token")
                    if not page_token:
                        break
                    params["page_token"] = page_token

            # Sort by start time
            events.sort(key=lambda e: e.start_time or datetime.min.replace(tzinfo=UTC))
            logger.debug("Retrieved %d events from calendar %s", len(events), calendar_id)
            return events

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error fetching events from calendar %s: %s",
                calendar_id,
                e,
                exc_info=True,
            )
            return []
        except Exception as e:
            logger.error(
                "Error fetching events from calendar %s: %s",
                calendar_id,
                e,
                exc_info=True,
            )
            return []

    def get_event_detail(
        self,
        calendar_id: str,
        event_id: str,
        access_token: str | None = None,
    ) -> CalendarEvent | None:
        """Fetch detailed information for a single event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            access_token: Optional access token

        Returns:
            CalendarEvent object or None if not found
        """
        if access_token is None:
            access_token = self._get_tenant_access_token()
        if not access_token:
            logger.error("Cannot get event detail: no access token")
            return None

        try:
            url = f"{self.FEISHU_API_BASE}/calendar/v4/calendars/{calendar_id}/events/{event_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()

            data = response.json()
            if data.get("code") != 0:
                logger.warning(
                    "Failed to get event %s from calendar %s: %s",
                    event_id,
                    calendar_id,
                    data.get("msg"),
                )
                return None

            event_data = data.get("data", {}).get("event")
            if not event_data:
                return None

            return CalendarEvent.from_api_response(event_data, calendar_id)

        except httpx.HTTPError as e:
            logger.error(
                "HTTP error fetching event %s: %s", event_id, e, exc_info=True
            )
            return None
        except Exception as e:
            logger.error("Error fetching event %s: %s", event_id, e, exc_info=True)
            return None

    def get_today_events(
        self, calendar_id: str = "primary", access_token: str | None = None
    ) -> list[CalendarEvent]:
        """Get all events for today.

        Args:
            calendar_id: Calendar ID
            access_token: Optional access token

        Returns:
            List of today's events
        """
        now = datetime.now(self._timezone)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return self.get_events(
            calendar_id=calendar_id,
            start_time=start_of_day.astimezone(UTC),
            end_time=end_of_day.astimezone(UTC),
            access_token=access_token,
        )

    def get_upcoming_events(
        self,
        calendar_id: str = "primary",
        hours_ahead: int = 24,
        access_token: str | None = None,
    ) -> list[CalendarEvent]:
        """Get upcoming events within specified hours.

        Args:
            calendar_id: Calendar ID
            hours_ahead: Hours to look ahead
            access_token: Optional access token

        Returns:
            List of upcoming events
        """
        now = datetime.now(tz=UTC)
        end_time = now + timedelta(hours=hours_ahead)

        return self.get_events(
            calendar_id=calendar_id,
            start_time=now,
            end_time=end_time,
            access_token=access_token,
        )

    # ========== Beautiful Card Builders ==========

    def build_event_reminder_card(
        self, event: CalendarEvent, reminder_minutes: int
    ) -> dict[str, Any]:
        """Build a beautiful reminder card for an event.

        Args:
            event: CalendarEvent object
            reminder_minutes: Minutes until event

        Returns:
            Card JSON structure
        """
        # Determine header color based on urgency
        if reminder_minutes <= 5:
            template = "red"
            urgency_text = "即将开始"
        elif reminder_minutes <= 15:
            template = "orange"
            urgency_text = f"{reminder_minutes} 分钟后开始"
        else:
            template = "blue"
            urgency_text = f"{reminder_minutes} 分钟后开始"

        card = (
            CardBuilder()
            .set_config(wide_screen_mode=True)
            .set_header("日程提醒", template=template, subtitle=urgency_text)
        )

        # Event title with status icon
        status_icon = self.STATUS_ICONS.get(event.status, "")
        card.add_markdown(f"### {status_icon} {event.summary or '无标题'}")

        # Two-column layout for time and location
        time_info = event.get_time_range_str(self._timezone)
        duration = event.get_duration_str()

        columns = [
            {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {"tag": "markdown", "content": f"**时间**\n{time_info}"},
                ],
            },
        ]

        if duration:
            columns.append(
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {"tag": "markdown", "content": f"**时长**\n{duration}"},
                    ],
                }
            )

        card.add_column_set(columns=columns, flex_mode="bisect")

        # Location info
        if event.location.name:
            location_text = event.location.name
            if event.location.address:
                location_text += f"\n{event.location.address}"
            card.add_markdown(f"**地点**\n{location_text}")

        # Video meeting info
        if event.vchat.meeting_url:
            vc_type_text = "飞书会议" if event.vchat.vc_type == "vc" else "视频会议"
            card.add_markdown(f"**{vc_type_text}**")
            card.add_button(
                "加入会议",
                url=event.vchat.meeting_url,
                button_type="primary",
                size="small",
            )

        # Organizer info
        if event.organizer_name:
            card.add_markdown(f"**组织者**: {event.organizer_name}")

        # Attendees summary
        if event.attendees:
            attendee_summary = event.get_attendee_summary()
            card.add_markdown(f"**参与者**: {attendee_summary}")

        # Description (collapsible if long)
        if event.description:
            desc = event.description
            if len(desc) > 100:
                card.add_collapsible_panel(
                    title="详细描述",
                    elements=[{"tag": "markdown", "content": desc}],
                    expanded=False,
                )
            else:
                card.add_divider()
                card.add_markdown(desc)

        # Footer note
        card.add_note(content=f"日程ID: {event.event_id[:8]}...")

        return card.build()

    def build_event_detail_card(self, event: CalendarEvent) -> dict[str, Any]:
        """Build a detailed event information card.

        Args:
            event: CalendarEvent object

        Returns:
            Card JSON structure
        """
        # Determine header color based on status
        if event.status == EventStatus.CANCELLED:
            template = "grey"
        elif event.status == EventStatus.TENTATIVE:
            template = "yellow"
        else:
            template = "blue"

        status_icon = self.STATUS_ICONS.get(event.status, "")
        card = (
            CardBuilder()
            .set_config(wide_screen_mode=True)
            .set_header(
                f"{status_icon} {event.summary or '无标题'}",
                template=template,
                subtitle="日程详情",
            )
        )

        # Time information section
        time_info = event.get_time_range_str(self._timezone)
        duration = event.get_duration_str()

        time_content = f"**时间**: {time_info}"
        if duration:
            time_content += f"\n**时长**: {duration}"
        if event.is_all_day:
            time_content += "\n*(全天日程)*"

        card.add_markdown(time_content)
        card.add_divider()

        # Location section
        if event.location.name or event.location.address:
            location_parts = []
            if event.location.name:
                location_parts.append(f"**地点**: {event.location.name}")
            if event.location.address:
                location_parts.append(f"**地址**: {event.location.address}")
            card.add_markdown("\n".join(location_parts))

        # Video meeting section
        if event.vchat.meeting_url:
            vc_type_names = {
                "vc": "飞书会议",
                "third_party": "第三方会议",
                "no_meeting": "无会议",
            }
            vc_name = vc_type_names.get(event.vchat.vc_type, "视频会议")
            card.add_markdown(f"**会议类型**: {vc_name}")
            card.add_button(
                "加入会议",
                url=event.vchat.meeting_url,
                button_type="primary",
            )
            card.add_divider()

        # Organizer and attendees section
        people_section = []
        if event.organizer_name:
            people_section.append(f"**组织者**: {event.organizer_name}")

        if event.attendees:
            attendee_names = [
                f"{a.display_name or a.email}" + (" (可选)" if a.is_optional else "")
                for a in event.attendees[:5]
            ]
            if len(event.attendees) > 5:
                attendee_names.append(f"...及其他 {len(event.attendees) - 5} 人")

            people_section.append(f"**参与者** ({event.get_attendee_summary()}):")
            for name in attendee_names:
                people_section.append(f"  • {name}")

        if people_section:
            card.add_markdown("\n".join(people_section))
            card.add_divider()

        # Description section
        if event.description:
            card.add_collapsible_panel(
                title="描述",
                elements=[{"tag": "markdown", "content": event.description}],
                expanded=True,
            )

        # Recurrence info
        if event.recurrence:
            card.add_note(content=f"重复规则: {event.recurrence}")

        # Metadata footer
        meta_parts = [f"日程ID: {event.event_id[:12]}"]
        if event.create_time:
            meta_parts.append(
                f"创建于: {event.create_time.astimezone(self._timezone).strftime('%Y-%m-%d')}"
            )
        card.add_note(content=" | ".join(meta_parts))

        return card.build()

    def build_events_list_card(
        self,
        events: list[CalendarEvent],
        title: str = "日程列表",
        subtitle: str | None = None,
        show_details: bool = True,
    ) -> dict[str, Any]:
        """Build a card showing a list of events.

        Args:
            events: List of CalendarEvent objects
            title: Card title
            subtitle: Optional subtitle
            show_details: Whether to show event details

        Returns:
            Card JSON structure
        """
        card = (
            CardBuilder()
            .set_config(wide_screen_mode=True)
            .set_header(title, template="blue", subtitle=subtitle)
        )

        if not events:
            card.add_markdown("*暂无日程*")
            return card.build()

        card.add_markdown(f"共 **{len(events)}** 个日程")
        card.add_divider()

        # Group events by date
        events_by_date: dict[str, list[CalendarEvent]] = {}
        for event in events:
            if event.start_time:
                date_key = event.start_time.astimezone(self._timezone).strftime("%Y-%m-%d")
            else:
                date_key = "未知日期"

            if date_key not in events_by_date:
                events_by_date[date_key] = []
            events_by_date[date_key].append(event)

        # Build each date section
        for date_str, date_events in events_by_date.items():
            # Format date header
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                weekday = weekday_names[date_obj.weekday()]
                date_header = f"**{date_str} {weekday}**"
            except ValueError:
                date_header = f"**{date_str}**"

            card.add_markdown(date_header)

            # Add each event
            for event in date_events:
                status_icon = self.STATUS_ICONS.get(event.status, "")

                if event.is_all_day:
                    time_str = "全天"
                elif event.start_time:
                    time_str = event.start_time.astimezone(self._timezone).strftime("%H:%M")
                else:
                    time_str = "--:--"

                event_line = f"{status_icon} **{time_str}** {event.summary or '无标题'}"

                if show_details:
                    extra_info = []
                    if event.location.name:
                        extra_info.append(f"📍 {event.location.name}")
                    if event.vchat.meeting_url:
                        extra_info.append("💻 有会议")
                    if event.attendees:
                        extra_info.append(f"👥 {len(event.attendees)}人")

                    if extra_info:
                        event_line += f"\n  {' | '.join(extra_info)}"

                card.add_markdown(event_line)

            card.add_divider()

        return card.build()

    def build_daily_summary_card(
        self, events: list[CalendarEvent], date: datetime | None = None
    ) -> dict[str, Any]:
        """Build a daily summary card.

        Args:
            events: List of events for the day
            date: Date for the summary (default: today)

        Returns:
            Card JSON structure
        """
        if date is None:
            date = datetime.now(self._timezone)

        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        date_str = date.strftime("%Y年%m月%d日")
        weekday = weekday_names[date.weekday()]

        card = (
            CardBuilder()
            .set_config(wide_screen_mode=True)
            .set_header(
                "今日日程",
                template="green",
                subtitle=f"{date_str} {weekday}",
            )
        )

        if not events:
            card.add_markdown("### 今天没有日程安排")
            card.add_markdown("享受美好的一天！")
            return card.build()

        # Summary stats
        total = len(events)
        meetings = sum(1 for e in events if e.vchat.meeting_url)
        all_day = sum(1 for e in events if e.is_all_day)

        stats_columns = [
            {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {"tag": "markdown", "content": f"**{total}**\n日程总数", "text_align": "center"}
                ],
            },
            {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {"tag": "markdown", "content": f"**{meetings}**\n会议", "text_align": "center"}
                ],
            },
            {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {"tag": "markdown", "content": f"**{all_day}**\n全天日程", "text_align": "center"}
                ],
            },
        ]
        card.add_column_set(columns=stats_columns, flex_mode="trisect", background_style="grey")
        card.add_divider()

        # Timeline view
        for event in events:
            status_icon = self.STATUS_ICONS.get(event.status, "")

            if event.is_all_day:
                time_str = "全天"
            elif event.start_time:
                start = event.start_time.astimezone(self._timezone)
                if event.end_time:
                    end = event.end_time.astimezone(self._timezone)
                    time_str = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
                else:
                    time_str = start.strftime("%H:%M")
            else:
                time_str = "--:--"

            # Event row with two columns
            event_columns = [
                {
                    "tag": "column",
                    "width": "auto",
                    "elements": [
                        {"tag": "markdown", "content": f"**{time_str}**"}
                    ],
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {"tag": "markdown", "content": f"{status_icon} {event.summary or '无标题'}"}
                    ],
                },
            ]

            card.add_column_set(columns=event_columns, flex_mode="none")

            # Extra info row
            extras = []
            if event.location.name:
                extras.append(f"📍 {event.location.name}")
            if event.vchat.meeting_url:
                extras.append("💻 有会议链接")

            if extras:
                card.add_markdown(f"  *{' | '.join(extras)}*")

        return card.build()

    def build_calendar_list_card(
        self, calendars: list[CalendarInfo]
    ) -> dict[str, Any]:
        """Build a card showing available calendars.

        Args:
            calendars: List of CalendarInfo objects

        Returns:
            Card JSON structure
        """
        card = (
            CardBuilder()
            .set_config(wide_screen_mode=True)
            .set_header("日历列表", template="purple", subtitle=f"共 {len(calendars)} 个日历")
        )

        if not calendars:
            card.add_markdown("*暂无可用日历*")
            return card.build()

        # Group by type
        primary = [c for c in calendars if c.is_primary]
        shared = [c for c in calendars if c.type == "shared" and not c.is_primary]
        others = [c for c in calendars if c not in primary and c not in shared]

        role_icons = {
            "owner": "👑",
            "writer": "✏️",
            "reader": "👁️",
        }

        for group_name, group_calendars in [
            ("主日历", primary),
            ("共享日历", shared),
            ("其他日历", others),
        ]:
            if not group_calendars:
                continue

            card.add_markdown(f"**{group_name}**")

            for cal in group_calendars:
                role_icon = role_icons.get(cal.role, "📅")
                cal_line = f"{role_icon} **{cal.summary or cal.calendar_id}**"
                if cal.description:
                    cal_line += f"\n  {cal.description}"
                card.add_markdown(cal_line)

            card.add_divider()

        return card.build()

    # ========== Scheduled Tasks ==========

    def send_daily_summary(self) -> None:
        """Send daily summary of events.

        This method is called by the scheduler each morning.
        """
        try:
            logger.info("Generating daily summary...")

            access_token = self._get_tenant_access_token()
            if not access_token:
                logger.warning("Could not get access token for daily summary")
                return

            all_events: list[CalendarEvent] = []

            for calendar_id in self._calendar_ids:
                events = self.get_today_events(calendar_id, access_token)
                all_events.extend(events)

            # Sort by start time
            all_events.sort(key=lambda e: e.start_time or datetime.min.replace(tzinfo=UTC))

            # Build and send the card
            card = self.build_daily_summary_card(all_events)
            self._send_card(card)

            logger.info("Daily summary sent with %d events", len(all_events))

        except Exception as e:
            logger.error("Error sending daily summary: %s", e, exc_info=True)

    def _send_card(self, card: dict[str, Any]) -> bool:
        """Send a card message.

        Args:
            card: Card JSON structure

        Returns:
            True if successfully sent
        """
        try:
            if not self.client:
                logger.error("Client not available for sending card")
                return False

            from ..core.client import FeishuWebhookClient

            if isinstance(self.client, FeishuWebhookClient):
                self.client.send_card(card)
            else:
                self.client.send_card(card, "")

            return True

        except Exception as e:
            logger.error("Failed to send card: %s", e, exc_info=True)
            return False

    # ========== Public API Methods ==========

    def send_event_card(
        self, calendar_id: str = "primary", event_id: str = ""
    ) -> bool:
        """Send a detailed card for a specific event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID

        Returns:
            True if successfully sent
        """
        event = self.get_event_detail(calendar_id, event_id)
        if not event:
            logger.warning("Event not found: %s/%s", calendar_id, event_id)
            return False

        card = self.build_event_detail_card(event)
        return self._send_card(card)

    def send_upcoming_events_card(
        self,
        calendar_id: str = "primary",
        hours_ahead: int = 24,
    ) -> bool:
        """Send a card with upcoming events.

        Args:
            calendar_id: Calendar ID
            hours_ahead: Hours to look ahead

        Returns:
            True if successfully sent
        """
        events = self.get_upcoming_events(calendar_id, hours_ahead)

        now = datetime.now(self._timezone)
        end_time = now + timedelta(hours=hours_ahead)
        subtitle = f"{now.strftime('%H:%M')} - {end_time.strftime('%m/%d %H:%M')}"

        card = self.build_events_list_card(
            events,
            title="即将到来的日程",
            subtitle=subtitle,
        )
        return self._send_card(card)

    def send_today_events_card(self, calendar_id: str = "primary") -> bool:
        """Send a card with today's events.

        Args:
            calendar_id: Calendar ID

        Returns:
            True if successfully sent
        """
        events = self.get_today_events(calendar_id)
        card = self.build_daily_summary_card(events)
        return self._send_card(card)

    def send_calendar_list_card(self) -> bool:
        """Send a card with available calendars.

        Returns:
            True if successfully sent
        """
        calendars = self.get_calendar_list()
        card = self.build_calendar_list_card(calendars)
        return self._send_card(card)

    def _send_reminder(self, event: dict[str, Any], reminder_minutes: int) -> bool:
        """Send a reminder card for an event.

        Args:
            event: Event dictionary
            reminder_minutes: Minutes until event

        Returns:
            True if successfully sent
        """
        try:
            if not self.client:
                logger.error("Client not available for sending reminder")
                return False

            card = self._build_reminder_card(event, reminder_minutes)

            # Send the card - handle both legacy client and new provider
            # Legacy FeishuWebhookClient.send_card(card) vs BaseProvider.send_card(card, target)
            from ..core.client import FeishuWebhookClient

            if isinstance(self.client, FeishuWebhookClient):
                self.client.send_card(card)
            else:
                # For BaseProvider, target is empty as webhook URL is in config
                self.client.send_card(card, "")

            event_id = event.get("event_id", "unknown")
            event_title = event.get("summary", "Event")
            logger.info(
                "Sent reminder for event '%s' (ID: %s) - %d minutes before start",
                event_title,
                event_id,
                reminder_minutes,
            )
            return True

        except Exception as e:
            event_id = event.get("event_id", "unknown")
            logger.error(
                "Failed to send reminder for event %s: %s",
                event_id,
                e,
                exc_info=True,
            )
            return False

    def check_events(self) -> None:
        """Main task: Check calendar events and send reminders.

        This method is called periodically by the scheduler.
        """
        try:
            logger.debug("Checking calendar events...")

            # Get access token
            access_token = self._get_tenant_access_token()
            if not access_token:
                logger.warning("Could not get access token, skipping event check")
                return

            # Check each calendar
            for calendar_id in self._calendar_ids:
                try:
                    events = self._get_calendar_events(calendar_id, access_token)

                    # Check each event for reminders
                    for event in events:
                        event_id = event.get("event_id")
                        if not event_id:
                            continue
                        for reminder_minutes in self._reminder_minutes:
                            if self._should_send_reminder(
                                event, reminder_minutes
                            ) and self._send_reminder(event, reminder_minutes):
                                self._mark_reminder_sent(event_id, reminder_minutes)

                except Exception as e:
                    logger.error(
                        "Error processing calendar %s: %s",
                        calendar_id,
                        e,
                        exc_info=True,
                    )
                    continue

            logger.debug("Calendar event check completed")

        except Exception as e:
            logger.error("Error in check_events: %s", e, exc_info=True)
