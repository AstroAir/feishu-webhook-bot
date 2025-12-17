"""Tests for Feishu Calendar plugin."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from feishu_webhook_bot.core.config import BotConfig
from feishu_webhook_bot.plugins.feishu_calendar import (
    AttendeeStatus,
    CalendarEvent,
    CalendarInfo,
    EventAttendee,
    EventLocation,
    EventStatus,
    EventVChat,
    EventVisibility,
    FeishuCalendarPlugin,
)


@pytest.fixture
def mock_config():
    """Create a mock bot configuration."""
    config = MagicMock(spec=BotConfig)
    config.plugins = MagicMock()
    config.plugins.get_plugin_settings.return_value = {
        "app_id": "test_app_id",
        "app_secret": "test_app_secret",
        "calendar_ids": ["primary", "secondary"],
        "check_interval_minutes": 5,
        "reminder_minutes": [15, 5],
        "webhook_name": "default",
    }
    return config


@pytest.fixture
def mock_client():
    """Create a mock Feishu webhook client."""
    client = MagicMock()
    client.send_card = MagicMock(return_value={"code": 0})
    client.send_text = MagicMock(return_value={"code": 0})
    return client


@pytest.fixture
def plugin(mock_config, mock_client):
    """Create a plugin instance for testing."""
    plugin = FeishuCalendarPlugin(config=mock_config, client=mock_client)
    plugin.on_load()
    return plugin


class TestFeishuCalendarPluginMetadata:
    """Test plugin metadata."""

    def test_metadata(self, plugin):
        """Test that metadata is correctly configured."""
        metadata = plugin.metadata()
        assert metadata.name == "feishu-calendar"
        assert metadata.version == "2.0.0"
        assert "calendar" in metadata.description.lower()
        assert metadata.enabled is True

    def test_metadata_name_unique(self, plugin):
        """Test that plugin name is unique."""
        metadata = plugin.metadata()
        assert metadata.name != ""
        assert "-" in metadata.name  # Should use kebab-case


class TestFeishuCalendarPluginConfiguration:
    """Test plugin configuration loading."""

    def test_on_load_reads_config(self, mock_config, mock_client):
        """Test that on_load reads configuration correctly."""
        plugin = FeishuCalendarPlugin(config=mock_config, client=mock_client)
        plugin.on_load()

        assert plugin._app_id == "test_app_id"
        assert plugin._app_secret == "test_app_secret"
        assert plugin._calendar_ids == ["primary", "secondary"]
        assert plugin._reminder_minutes == [15, 5]
        assert plugin._webhook_name == "default"

    def test_on_load_missing_credentials(self, mock_config, mock_client):
        """Test handling of missing app credentials."""
        mock_config.plugins.get_plugin_settings.return_value = {
            "calendar_ids": ["primary"],
        }
        plugin = FeishuCalendarPlugin(config=mock_config, client=mock_client)
        plugin.on_load()

        assert plugin._app_id is None
        assert plugin._app_secret is None

    def test_calendar_ids_normalization(self, mock_config, mock_client):
        """Test that calendar_ids are normalized to a list."""
        mock_config.plugins.get_plugin_settings.return_value = {
            "app_id": "test",
            "app_secret": "secret",
            "calendar_ids": "primary",  # Single string
            "reminder_minutes": [15, 5],
        }
        plugin = FeishuCalendarPlugin(config=mock_config, client=mock_client)
        plugin.on_load()

        assert isinstance(plugin._calendar_ids, list)
        assert plugin._calendar_ids == ["primary"]

    def test_reminder_minutes_normalization(self, mock_config, mock_client):
        """Test that reminder_minutes are normalized to a sorted list."""
        mock_config.plugins.get_plugin_settings.return_value = {
            "app_id": "test",
            "app_secret": "secret",
            "calendar_ids": ["primary"],
            "reminder_minutes": 15,  # Single number
        }
        plugin = FeishuCalendarPlugin(config=mock_config, client=mock_client)
        plugin.on_load()

        assert isinstance(plugin._reminder_minutes, list)
        assert plugin._reminder_minutes == [15]

    def test_reminder_minutes_sorted_descending(self, mock_config, mock_client):
        """Test that reminder_minutes are sorted in descending order."""
        mock_config.plugins.get_plugin_settings.return_value = {
            "app_id": "test",
            "app_secret": "secret",
            "calendar_ids": ["primary"],
            "reminder_minutes": [5, 15, 30],
        }
        plugin = FeishuCalendarPlugin(config=mock_config, client=mock_client)
        plugin.on_load()

        assert plugin._reminder_minutes == [30, 15, 5]


class TestAccessTokenManagement:
    """Test tenant access token management."""

    def test_get_token_success(self, plugin):
        """Test successful token retrieval."""
        with patch("feishu_webhook_bot.plugins.feishu_calendar.httpx.Client") as mock_http:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "code": 0,
                "tenant_access_token": "test_token_123",
                "expire": 7200,
            }
            mock_http.return_value.__enter__.return_value.post.return_value = mock_response

            token = plugin._get_tenant_access_token()

            assert token == "test_token_123"
            assert plugin._token_cache is not None
            assert plugin._token_cache[0] == "test_token_123"

    def test_get_token_caching(self, plugin):
        """Test that tokens are cached."""
        with patch("feishu_webhook_bot.plugins.feishu_calendar.httpx.Client") as mock_http:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "code": 0,
                "tenant_access_token": "test_token_123",
                "expire": 7200,
            }
            mock_http.return_value.__enter__.return_value.post.return_value = mock_response

            token1 = plugin._get_tenant_access_token()
            token2 = plugin._get_tenant_access_token()

            assert token1 == token2
            # Should only call API once due to caching
            assert mock_http.return_value.__enter__.return_value.post.call_count == 1

    def test_get_token_api_error(self, plugin):
        """Test handling of API errors when getting token."""
        with patch("feishu_webhook_bot.plugins.feishu_calendar.httpx.Client") as mock_http:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "code": -1,
                "msg": "Invalid credentials",
            }
            mock_http.return_value.__enter__.return_value.post.return_value = mock_response

            token = plugin._get_tenant_access_token()

            assert token is None

    def test_get_token_http_error(self, plugin):
        """Test handling of HTTP errors when getting token."""
        with patch("feishu_webhook_bot.plugins.feishu_calendar.httpx.Client") as mock_http:
            import httpx

            mock_http.return_value.__enter__.return_value.post.side_effect = httpx.HTTPError(
                "Connection failed"
            )

            token = plugin._get_tenant_access_token()

            assert token is None

    def test_missing_credentials(self, plugin):
        """Test handling when credentials are missing."""
        plugin._app_id = None
        plugin._app_secret = None

        token = plugin._get_tenant_access_token()

        assert token is None


class TestEventReminders:
    """Test event reminder functionality."""

    def test_should_send_reminder_within_window(self, plugin):
        """Test reminder window detection."""
        now = datetime.now(tz=UTC)
        start_time = now + timedelta(minutes=10)

        event = {
            "event_id": "event_123",
            "summary": "Test Event",
            "start_time": {"timestamp": str(int(start_time.timestamp()))},
        }

        # Should send reminder 15 minutes before (event is 10 minutes away, within 15-min window)
        assert plugin._should_send_reminder(event, 15) is True

    def test_should_not_send_reminder_too_early(self, plugin):
        """Test that reminders are not sent too early."""
        now = datetime.now(tz=UTC)
        start_time = now + timedelta(minutes=30)

        event = {
            "event_id": "event_123",
            "summary": "Test Event",
            "start_time": {"timestamp": str(int(start_time.timestamp()))},
        }

        # Should not send 15-minute reminder when event is 30 minutes away
        assert plugin._should_send_reminder(event, 15) is False

    def test_should_not_send_reminder_after_start(self, plugin):
        """Test that reminders are not sent after event starts."""
        now = datetime.now(tz=UTC)
        start_time = now - timedelta(minutes=5)  # Event started 5 minutes ago

        event = {
            "event_id": "event_123",
            "summary": "Test Event",
            "start_time": {"timestamp": str(int(start_time.timestamp()))},
        }

        assert plugin._should_send_reminder(event, 15) is False

    def test_should_not_send_duplicate_reminders(self, plugin):
        """Test that duplicate reminders are not sent."""
        now = datetime.now(tz=UTC)
        start_time = now + timedelta(minutes=10)

        event = {
            "event_id": "event_123",
            "summary": "Test Event",
            "start_time": {"timestamp": str(int(start_time.timestamp()))},
        }

        # First reminder should be sent
        assert plugin._should_send_reminder(event, 15) is True

        # Mark as sent
        plugin._mark_reminder_sent("event_123", 15)

        # Second reminder should not be sent
        assert plugin._should_send_reminder(event, 15) is False

    def test_mark_reminder_sent(self, plugin):
        """Test marking a reminder as sent."""
        plugin._mark_reminder_sent("event_123", 15)

        assert "event_123" in plugin._reminded_events
        assert plugin._reminded_events["event_123"][15] is True


class TestReminderCard:
    """Test reminder card building."""

    def test_build_reminder_card_basic(self, plugin):
        """Test building a basic reminder card."""
        now = datetime.now(tz=UTC)
        start_time = now + timedelta(minutes=15)
        end_time = start_time + timedelta(hours=1)

        event = {
            "event_id": "event_123",
            "summary": "Team Meeting",
            "description": "Quarterly review meeting",
            "start_time": {"timestamp": str(int(start_time.timestamp()))},
            "end_time": {"timestamp": str(int(end_time.timestamp()))},
            "organizer": {"display_name": "Alice"},
            "location": {"display_name": "Conference Room A"},
        }

        card = plugin._build_reminder_card(event, 15)

        assert card is not None
        # v1.0 format (default) doesn't have schema field
        assert "elements" in card
        assert "header" in card

    def test_build_reminder_card_minimal(self, plugin):
        """Test building a reminder card with minimal information."""
        now = datetime.now(tz=UTC)
        start_time = now + timedelta(minutes=5)

        event = {
            "event_id": "event_123",
            "summary": "Quick Sync",
            "start_time": {"timestamp": str(int(start_time.timestamp()))},
        }

        card = plugin._build_reminder_card(event, 5)

        assert card is not None
        assert "elements" in card

    def test_build_reminder_card_with_timestamp_string(self, plugin):
        """Test building card with timestamp as string (not dict)."""
        now = datetime.now(tz=UTC)
        start_time = now + timedelta(minutes=10)

        event = {
            "event_id": "event_123",
            "summary": "Event",
            "start_time": str(int(start_time.timestamp())),  # String timestamp
        }

        card = plugin._build_reminder_card(event, 10)

        assert card is not None
        assert "elements" in card


class TestSendReminder:
    """Test reminder sending."""

    def test_send_reminder_success(self, plugin, mock_client):
        """Test successful reminder sending."""
        now = datetime.now(tz=UTC)
        start_time = now + timedelta(minutes=15)

        event = {
            "event_id": "event_123",
            "summary": "Team Meeting",
            "start_time": {"timestamp": str(int(start_time.timestamp()))},
        }

        result = plugin._send_reminder(event, 15)

        assert result is True
        mock_client.send_card.assert_called_once()

    def test_send_reminder_no_client(self, mock_config):
        """Test reminder sending without client."""
        plugin = FeishuCalendarPlugin(config=mock_config, client=None)
        plugin.on_load()

        now = datetime.now(tz=UTC)
        start_time = now + timedelta(minutes=15)

        event = {
            "event_id": "event_123",
            "summary": "Team Meeting",
            "start_time": {"timestamp": str(int(start_time.timestamp()))},
        }

        result = plugin._send_reminder(event, 15)

        assert result is False


class TestCheckEvents:
    """Test the main check_events task."""

    def test_check_events_success(self, plugin):
        """Test successful event checking."""
        with (
            patch.object(plugin, "_get_tenant_access_token") as mock_token,
            patch.object(plugin, "_get_calendar_events") as mock_events,
            patch.object(plugin, "_should_send_reminder") as mock_should,
            patch.object(plugin, "_send_reminder"),
        ):
            mock_token.return_value = "test_token"
            mock_events.return_value = []
            mock_should.return_value = False

            plugin.check_events()

            mock_token.assert_called_once()
            mock_events.assert_called()

    def test_check_events_no_token(self, plugin):
        """Test check_events when token retrieval fails."""
        with (
            patch.object(plugin, "_get_tenant_access_token") as mock_token,
            patch.object(plugin, "_get_calendar_events") as mock_events,
        ):
            mock_token.return_value = None

            plugin.check_events()

            mock_token.assert_called_once()
            mock_events.assert_not_called()

    def test_check_events_with_reminders(self, plugin):
        """Test check_events with reminder sending."""
        now = datetime.now(tz=UTC)
        start_time = now + timedelta(minutes=10)

        event = {
            "event_id": "event_123",
            "summary": "Meeting",
            "start_time": {"timestamp": str(int(start_time.timestamp()))},
        }

        with (
            patch.object(plugin, "_get_tenant_access_token") as mock_token,
            patch.object(plugin, "_get_calendar_events") as mock_events,
            patch.object(plugin, "_send_reminder") as mock_send,
        ):
            mock_token.return_value = "test_token"
            mock_events.return_value = [event]
            mock_send.return_value = True

            plugin.check_events()

            # Should try to send reminders
            assert mock_send.call_count > 0


class TestPluginLifecycle:
    """Test plugin lifecycle methods."""

    def test_on_enable_registers_job(self, plugin):
        """Test that on_enable registers a scheduled job."""
        with patch.object(plugin, "register_job") as mock_register:
            plugin.on_enable()

            mock_register.assert_called_once()
            call_args = mock_register.call_args
            assert call_args[1]["trigger"] == "interval"
            assert call_args[1]["minutes"] == 5

    def test_on_disable_cleans_up(self, plugin):
        """Test that on_disable cleans up state."""
        plugin._reminded_events = {"event_1": {15: True}, "event_2": {5: True}}

        plugin.on_disable()

        assert len(plugin._reminded_events) == 0

    def test_on_enable_skips_if_no_credentials(self, mock_config):
        """Test that on_enable skips job registration without credentials."""
        mock_config.plugins.get_plugin_settings.return_value = {
            "calendar_ids": ["primary"],
        }
        plugin = FeishuCalendarPlugin(config=mock_config, client=MagicMock())
        plugin.on_load()

        with patch.object(plugin, "register_job") as mock_register:
            plugin.on_enable()

            mock_register.assert_not_called()


# ========== New Tests for Data Classes ==========


class TestCalendarInfo:
    """Test CalendarInfo data class."""

    def test_from_api_response(self):
        """Test creating CalendarInfo from API response."""
        data = {
            "calendar_id": "cal_123",
            "summary": "My Calendar",
            "description": "Personal calendar",
            "color": "#FF0000",
            "type": "primary",
            "role": "owner",
        }
        cal_info = CalendarInfo.from_api_response(data)

        assert cal_info.calendar_id == "cal_123"
        assert cal_info.summary == "My Calendar"
        assert cal_info.description == "Personal calendar"
        assert cal_info.color == "#FF0000"
        assert cal_info.type == "primary"
        assert cal_info.role == "owner"

    def test_is_primary_detection(self):
        """Test primary calendar detection."""
        data = {"calendar_id": "primary", "summary": "Primary"}
        cal_info = CalendarInfo.from_api_response(data)
        assert cal_info.is_primary is True

        data = {"calendar_id": "other_cal", "summary": "Other"}
        cal_info = CalendarInfo.from_api_response(data)
        assert cal_info.is_primary is False


class TestEventAttendee:
    """Test EventAttendee data class."""

    def test_from_api_response(self):
        """Test creating EventAttendee from API response."""
        data = {
            "user_id": "user_123",
            "display_name": "Alice",
            "email": "alice@example.com",
            "rsvp_status": "accepted",
            "is_optional": False,
            "is_organizer": True,
            "is_external": False,
        }
        attendee = EventAttendee.from_api_response(data)

        assert attendee.user_id == "user_123"
        assert attendee.display_name == "Alice"
        assert attendee.email == "alice@example.com"
        assert attendee.status == AttendeeStatus.ACCEPTED
        assert attendee.is_optional is False
        assert attendee.is_organizer is True

    def test_from_api_response_unknown_status(self):
        """Test handling of unknown status."""
        data = {"user_id": "user_123", "rsvp_status": "unknown_status"}
        attendee = EventAttendee.from_api_response(data)
        assert attendee.status == AttendeeStatus.NEEDS_ACTION


class TestEventLocation:
    """Test EventLocation data class."""

    def test_from_api_response_dict(self):
        """Test creating EventLocation from dict."""
        data = {
            "name": "Conference Room A",
            "address": "123 Main St",
            "latitude": 37.7749,
            "longitude": -122.4194,
        }
        location = EventLocation.from_api_response(data)

        assert location.name == "Conference Room A"
        assert location.address == "123 Main St"
        assert location.latitude == 37.7749
        assert location.longitude == -122.4194

    def test_from_api_response_string(self):
        """Test creating EventLocation from string."""
        location = EventLocation.from_api_response("Room 101")
        assert location.name == "Room 101"
        assert location.address == ""

    def test_from_api_response_none(self):
        """Test creating EventLocation from None."""
        location = EventLocation.from_api_response(None)
        assert location.name == ""
        assert location.address == ""


class TestEventVChat:
    """Test EventVChat data class."""

    def test_from_api_response(self):
        """Test creating EventVChat from API response."""
        data = {
            "vc_type": "vc",
            "meeting_url": "https://meetings.feishu.cn/xxx",
            "meeting_settings": {"auto_record": True},
        }
        vchat = EventVChat.from_api_response(data)

        assert vchat.vc_type == "vc"
        assert vchat.meeting_url == "https://meetings.feishu.cn/xxx"
        assert vchat.meeting_settings["auto_record"] is True

    def test_from_api_response_none(self):
        """Test creating EventVChat from None."""
        vchat = EventVChat.from_api_response(None)
        assert vchat.vc_type == ""
        assert vchat.meeting_url == ""


class TestCalendarEvent:
    """Test CalendarEvent data class."""

    def test_from_api_response_full(self):
        """Test creating CalendarEvent with full data."""
        now = datetime.now(tz=UTC)
        start_ts = int(now.timestamp())
        end_ts = int((now + timedelta(hours=1)).timestamp())

        data = {
            "event_id": "event_123",
            "summary": "Team Meeting",
            "description": "Weekly sync",
            "start_time": {"timestamp": str(start_ts), "timezone": "Asia/Shanghai"},
            "end_time": {"timestamp": str(end_ts)},
            "status": "confirmed",
            "visibility": "public",
            "organizer": {"user_id": "org_123", "display_name": "Alice"},
            "location": {"name": "Room A"},
            "vchat": {"vc_type": "vc", "meeting_url": "https://meet.example.com"},
            "attendees": [
                {"user_id": "user_1", "display_name": "Bob", "rsvp_status": "accepted"},
                {"user_id": "user_2", "display_name": "Carol", "rsvp_status": "declined"},
            ],
            "recurrence": "RRULE:FREQ=WEEKLY",
            "color": "#0000FF",
        }

        event = CalendarEvent.from_api_response(data, "calendar_123")

        assert event.event_id == "event_123"
        assert event.summary == "Team Meeting"
        assert event.description == "Weekly sync"
        assert event.status == EventStatus.CONFIRMED
        assert event.visibility == EventVisibility.PUBLIC
        assert event.organizer_name == "Alice"
        assert event.location.name == "Room A"
        assert event.vchat.vc_type == "vc"
        assert len(event.attendees) == 2
        assert event.recurrence == "RRULE:FREQ=WEEKLY"
        assert event.calendar_id == "calendar_123"

    def test_from_api_response_all_day(self):
        """Test creating all-day event."""
        data = {
            "event_id": "event_456",
            "summary": "Holiday",
            "start_time": {"date": "2025-12-25"},
            "end_time": {"date": "2025-12-26"},
        }
        event = CalendarEvent.from_api_response(data)

        assert event.is_all_day is True
        assert event.start_time is not None

    def test_from_api_response_minimal(self):
        """Test creating event with minimal data."""
        data = {"event_id": "event_789"}
        event = CalendarEvent.from_api_response(data)

        assert event.event_id == "event_789"
        assert event.summary == ""
        assert event.status == EventStatus.CONFIRMED

    def test_get_duration_str(self):
        """Test duration string generation."""
        now = datetime.now(tz=UTC)
        event = CalendarEvent(
            event_id="test",
            start_time=now,
            end_time=now + timedelta(hours=1, minutes=30),
        )

        duration = event.get_duration_str()
        assert "1小时" in duration
        assert "30分钟" in duration

    def test_get_duration_str_hours_only(self):
        """Test duration string for whole hours."""
        now = datetime.now(tz=UTC)
        event = CalendarEvent(
            event_id="test",
            start_time=now,
            end_time=now + timedelta(hours=2),
        )

        duration = event.get_duration_str()
        assert duration == "2小时"

    def test_get_duration_str_minutes_only(self):
        """Test duration string for minutes only."""
        now = datetime.now(tz=UTC)
        event = CalendarEvent(
            event_id="test",
            start_time=now,
            end_time=now + timedelta(minutes=45),
        )

        duration = event.get_duration_str()
        assert duration == "45分钟"

    def test_get_time_range_str(self):
        """Test time range string generation."""
        tz = timezone(timedelta(hours=8))
        now = datetime(2025, 12, 8, 10, 0, tzinfo=tz)
        event = CalendarEvent(
            event_id="test",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )

        time_range = event.get_time_range_str(tz)
        assert "2025-12-08" in time_range
        assert "10:00" in time_range
        assert "11:00" in time_range

    def test_get_time_range_str_all_day(self):
        """Test time range string for all-day event."""
        tz = timezone(timedelta(hours=8))
        now = datetime(2025, 12, 25, 0, 0, tzinfo=tz)
        event = CalendarEvent(
            event_id="test",
            start_time=now,
            end_time=now + timedelta(days=1),
            is_all_day=True,
        )

        time_range = event.get_time_range_str(tz)
        assert "全天" in time_range

    def test_get_attendee_summary(self):
        """Test attendee summary generation."""
        event = CalendarEvent(
            event_id="test",
            attendees=[
                EventAttendee(user_id="1", status=AttendeeStatus.ACCEPTED),
                EventAttendee(user_id="2", status=AttendeeStatus.ACCEPTED),
                EventAttendee(user_id="3", status=AttendeeStatus.DECLINED),
                EventAttendee(user_id="4", status=AttendeeStatus.NEEDS_ACTION),
            ],
        )

        summary = event.get_attendee_summary()
        assert "2人已接受" in summary
        assert "1人已拒绝" in summary
        assert "1人待回复" in summary

    def test_get_attendee_summary_empty(self):
        """Test attendee summary for empty list."""
        event = CalendarEvent(event_id="test", attendees=[])
        summary = event.get_attendee_summary()
        assert summary == ""


# ========== New Tests for Card Builders ==========


class TestCardBuilders:
    """Test card building methods."""

    def test_build_event_reminder_card(self, plugin):
        """Test building event reminder card."""
        now = datetime.now(tz=UTC)
        event = CalendarEvent(
            event_id="event_123",
            summary="Team Meeting",
            start_time=now + timedelta(minutes=15),
            end_time=now + timedelta(hours=1, minutes=15),
            organizer_name="Alice",
            location=EventLocation(name="Room A"),
        )

        card = plugin.build_event_reminder_card(event, 15)

        assert card is not None
        assert "header" in card
        assert "elements" in card

    def test_build_event_reminder_card_urgent(self, plugin):
        """Test building urgent reminder card (5 min)."""
        now = datetime.now(tz=UTC)
        event = CalendarEvent(
            event_id="event_123",
            summary="Urgent Meeting",
            start_time=now + timedelta(minutes=5),
        )

        card = plugin.build_event_reminder_card(event, 5)

        assert card is not None
        # Should have red header for urgent
        header = card.get("header", {})
        template = header.get("template", "")
        assert template == "red"

    def test_build_event_detail_card(self, plugin):
        """Test building event detail card."""
        now = datetime.now(tz=UTC)
        event = CalendarEvent(
            event_id="event_123",
            summary="Project Review",
            description="Quarterly project review meeting",
            start_time=now,
            end_time=now + timedelta(hours=2),
            organizer_name="Alice",
            location=EventLocation(name="Conference Room", address="Floor 3"),
            vchat=EventVChat(vc_type="vc", meeting_url="https://meet.example.com"),
            attendees=[
                EventAttendee(display_name="Bob", status=AttendeeStatus.ACCEPTED),
                EventAttendee(display_name="Carol", status=AttendeeStatus.TENTATIVE),
            ],
        )

        card = plugin.build_event_detail_card(event)

        assert card is not None
        assert "header" in card
        assert "elements" in card

    def test_build_event_detail_card_cancelled(self, plugin):
        """Test building card for cancelled event."""
        event = CalendarEvent(
            event_id="event_123",
            summary="Cancelled Meeting",
            status=EventStatus.CANCELLED,
        )

        card = plugin.build_event_detail_card(event)

        header = card.get("header", {})
        template = header.get("template", "")
        assert template == "grey"

    def test_build_events_list_card(self, plugin):
        """Test building events list card."""
        now = datetime.now(tz=UTC)
        events = [
            CalendarEvent(
                event_id="event_1",
                summary="Morning Meeting",
                start_time=now + timedelta(hours=1),
            ),
            CalendarEvent(
                event_id="event_2",
                summary="Afternoon Review",
                start_time=now + timedelta(hours=4),
            ),
        ]

        card = plugin.build_events_list_card(events, title="Today's Events")

        assert card is not None
        assert "header" in card

    def test_build_events_list_card_empty(self, plugin):
        """Test building events list card with no events."""
        card = plugin.build_events_list_card([], title="No Events")

        assert card is not None
        # Check that "暂无日程" message is in elements
        elements = card.get("elements", [])
        assert len(elements) > 0

    def test_build_daily_summary_card(self, plugin):
        """Test building daily summary card."""
        now = datetime.now(tz=UTC)
        events = [
            CalendarEvent(
                event_id="event_1",
                summary="Stand-up",
                start_time=now.replace(hour=9, minute=0),
                vchat=EventVChat(meeting_url="https://meet.example.com"),
            ),
            CalendarEvent(
                event_id="event_2",
                summary="All Day Event",
                start_time=now.replace(hour=0, minute=0),
                is_all_day=True,
            ),
        ]

        card = plugin.build_daily_summary_card(events)

        assert card is not None
        assert "header" in card

    def test_build_daily_summary_card_no_events(self, plugin):
        """Test building daily summary card with no events."""
        card = plugin.build_daily_summary_card([])

        assert card is not None
        elements = card.get("elements", [])
        # Should contain "今天没有日程安排" message
        assert len(elements) > 0

    def test_build_calendar_list_card(self, plugin):
        """Test building calendar list card."""
        calendars = [
            CalendarInfo(
                calendar_id="primary",
                summary="Personal",
                role="owner",
                is_primary=True,
            ),
            CalendarInfo(
                calendar_id="shared_1",
                summary="Team Calendar",
                type="shared",
                role="writer",
            ),
        ]

        card = plugin.build_calendar_list_card(calendars)

        assert card is not None
        assert "header" in card

    def test_build_calendar_list_card_empty(self, plugin):
        """Test building calendar list card with no calendars."""
        card = plugin.build_calendar_list_card([])

        assert card is not None


# ========== New Tests for API Methods ==========


class TestCalendarAPIethods:
    """Test calendar API methods."""

    def test_get_calendar_list(self, plugin):
        """Test fetching calendar list."""
        with patch("feishu_webhook_bot.plugins.feishu_calendar.httpx.Client") as mock_http:
            # Mock token response
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {
                "code": 0,
                "tenant_access_token": "test_token",
                "expire": 7200,
            }

            # Mock calendar list response
            mock_list_response = MagicMock()
            mock_list_response.json.return_value = {
                "code": 0,
                "data": {
                    "calendar_list": [
                        {"calendar_id": "cal_1", "summary": "Calendar 1"},
                        {"calendar_id": "cal_2", "summary": "Calendar 2"},
                    ]
                },
            }

            mock_client = MagicMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_list_response
            mock_http.return_value.__enter__.return_value = mock_client

            calendars = plugin.get_calendar_list()

            assert len(calendars) == 2
            assert calendars[0].calendar_id == "cal_1"

    def test_get_events(self, plugin):
        """Test fetching events."""
        now = datetime.now(tz=UTC)

        with patch("feishu_webhook_bot.plugins.feishu_calendar.httpx.Client") as mock_http:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {
                "code": 0,
                "tenant_access_token": "test_token",
                "expire": 7200,
            }

            mock_events_response = MagicMock()
            mock_events_response.json.return_value = {
                "code": 0,
                "data": {
                    "items": [
                        {
                            "event_id": "event_1",
                            "summary": "Event 1",
                            "start_time": {"timestamp": str(int(now.timestamp()))},
                        },
                    ]
                },
            }

            mock_client = MagicMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_events_response
            mock_http.return_value.__enter__.return_value = mock_client

            events = plugin.get_events("primary")

            assert len(events) == 1
            assert events[0].event_id == "event_1"

    def test_get_event_detail(self, plugin):
        """Test fetching event detail."""
        now = datetime.now(tz=UTC)

        with patch("feishu_webhook_bot.plugins.feishu_calendar.httpx.Client") as mock_http:
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {
                "code": 0,
                "tenant_access_token": "test_token",
                "expire": 7200,
            }

            mock_event_response = MagicMock()
            mock_event_response.json.return_value = {
                "code": 0,
                "data": {
                    "event": {
                        "event_id": "event_123",
                        "summary": "Detailed Event",
                        "start_time": {"timestamp": str(int(now.timestamp()))},
                    }
                },
            }

            mock_client = MagicMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_event_response
            mock_http.return_value.__enter__.return_value = mock_client

            event = plugin.get_event_detail("primary", "event_123")

            assert event is not None
            assert event.event_id == "event_123"
            assert event.summary == "Detailed Event"

    def test_get_today_events(self, plugin):
        """Test fetching today's events."""
        with patch.object(plugin, "get_events") as mock_get:
            mock_get.return_value = []

            events = plugin.get_today_events("primary")

            mock_get.assert_called_once()
            assert events == []

    def test_get_upcoming_events(self, plugin):
        """Test fetching upcoming events."""
        with patch.object(plugin, "get_events") as mock_get:
            mock_get.return_value = []

            events = plugin.get_upcoming_events("primary", hours_ahead=24)

            mock_get.assert_called_once()
            assert events == []


# ========== New Tests for Public API Methods ==========


class TestPublicAPIMethods:
    """Test public API methods for sending cards."""

    def test_send_event_card(self, plugin):
        """Test sending event detail card."""
        now = datetime.now(tz=UTC)
        event = CalendarEvent(
            event_id="event_123",
            summary="Test Event",
            start_time=now,
        )

        with (
            patch.object(plugin, "get_event_detail") as mock_get,
            patch.object(plugin, "_send_card") as mock_send,
        ):
            mock_get.return_value = event
            mock_send.return_value = True

            result = plugin.send_event_card("primary", "event_123")

            assert result is True
            mock_get.assert_called_once_with("primary", "event_123")
            mock_send.assert_called_once()

    def test_send_event_card_not_found(self, plugin):
        """Test sending card for non-existent event."""
        with patch.object(plugin, "get_event_detail") as mock_get:
            mock_get.return_value = None

            result = plugin.send_event_card("primary", "nonexistent")

            assert result is False

    def test_send_upcoming_events_card(self, plugin):
        """Test sending upcoming events card."""
        with (
            patch.object(plugin, "get_upcoming_events") as mock_get,
            patch.object(plugin, "_send_card") as mock_send,
        ):
            mock_get.return_value = []
            mock_send.return_value = True

            result = plugin.send_upcoming_events_card("primary", 24)

            assert result is True

    def test_send_today_events_card(self, plugin):
        """Test sending today's events card."""
        with (
            patch.object(plugin, "get_today_events") as mock_get,
            patch.object(plugin, "_send_card") as mock_send,
        ):
            mock_get.return_value = []
            mock_send.return_value = True

            result = plugin.send_today_events_card("primary")

            assert result is True

    def test_send_calendar_list_card(self, plugin):
        """Test sending calendar list card."""
        with (
            patch.object(plugin, "get_calendar_list") as mock_get,
            patch.object(plugin, "_send_card") as mock_send,
        ):
            mock_get.return_value = []
            mock_send.return_value = True

            result = plugin.send_calendar_list_card()

            assert result is True

    def test_send_daily_summary(self, plugin):
        """Test sending daily summary."""
        with (
            patch.object(plugin, "_get_tenant_access_token") as mock_token,
            patch.object(plugin, "get_today_events") as mock_events,
            patch.object(plugin, "_send_card") as mock_send,
        ):
            mock_token.return_value = "test_token"
            mock_events.return_value = []
            mock_send.return_value = True

            plugin.send_daily_summary()

            mock_send.assert_called_once()
