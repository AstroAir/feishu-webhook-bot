"""Scheduling expression utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..core.logger import get_logger

logger = get_logger("scheduler.expressions")


class DayOfWeek(str, Enum):
    MONDAY = "mon"
    TUESDAY = "tue"
    WEDNESDAY = "wed"
    THURSDAY = "thu"
    FRIDAY = "fri"
    SATURDAY = "sat"
    SUNDAY = "sun"


@dataclass
class CronField:
    name: str
    min_value: int
    max_value: int
    aliases: dict[str, int] = field(default_factory=dict)


CRON_FIELDS = [
    CronField("minute", 0, 59),
    CronField("hour", 0, 23),
    CronField("day", 1, 31),
    CronField(
        "month",
        1,
        12,
        {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        },
    ),
    CronField(
        "day_of_week", 0, 6, {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}
    ),
]


@dataclass
class CronParseResult:
    valid: bool
    minute: str = "*"
    hour: str = "*"
    day: str = "*"
    month: str = "*"
    day_of_week: str = "*"
    error: str | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "minute": self.minute,
            "hour": self.hour,
            "day": self.day,
            "month": self.month,
            "day_of_week": self.day_of_week,
        }


class CronExpressionParser:
    @classmethod
    def parse(cls, expression: str) -> CronParseResult:
        parts = expression.strip().split()
        if len(parts) != 5:
            return CronParseResult(valid=False, error=f"Expected 5 fields, got {len(parts)}")
        result = CronParseResult(valid=True)
        field_names = ["minute", "hour", "day", "month", "day_of_week"]
        for i, (part, field_def) in enumerate(zip(parts, CRON_FIELDS, strict=True)):
            valid, error = cls._validate_field(part, field_def)
            if not valid:
                return CronParseResult(valid=False, error=f"Invalid {field_names[i]}: {error}")
            setattr(result, field_names[i], part)
        result.description = cls.describe(expression)
        return result

    @classmethod
    def _validate_field(cls, value: str, field_def: CronField) -> tuple[bool, str | None]:
        if value == "*":
            return True, None
        if value.lower() in field_def.aliases:
            return True, None
        if "/" in value:
            base, step = value.split("/", 1)
            if not step.isdigit() or int(step) < 1:
                return False, f"Invalid step: {step}"
            if base == "*":
                return True, None
            value = base
        if "-" in value and not value.startswith("-"):
            try:
                start, end = value.split("-", 1)
                start_val = field_def.aliases.get(
                    start.lower(), int(start) if start.isdigit() else -1
                )
                end_val = field_def.aliases.get(end.lower(), int(end) if end.isdigit() else -1)
                if not (field_def.min_value <= start_val <= field_def.max_value):
                    return False, f"Start {start} out of range"
                if not (field_def.min_value <= end_val <= field_def.max_value):
                    return False, f"End {end} out of range"
                return True, None
            except ValueError:
                return False, f"Invalid range: {value}"
        if "," in value:
            for part in value.split(","):
                valid, error = cls._validate_field(part.strip(), field_def)
                if not valid:
                    return False, error
            return True, None
        try:
            num = int(value)
            if not (field_def.min_value <= num <= field_def.max_value):
                return False, f"Value {num} out of range"
            return True, None
        except ValueError:
            return False, f"Invalid value: {value}"

    @classmethod
    def validate(cls, expression: str) -> tuple[bool, str | None]:
        result = cls.parse(expression)
        return result.valid, result.error

    @classmethod
    def describe(cls, expression: str) -> str:
        parts = expression.strip().split()
        if len(parts) != 5:
            return "Invalid cron expression"
        minute, hour, day, month, dow = parts
        desc = []
        if minute == "*" and hour == "*":
            desc.append("Every minute")
        elif minute == "0" and hour == "*":
            desc.append("Every hour")
        elif hour == "*":
            desc.append(f"At minute {minute} of every hour")
        else:
            desc.append(f"At {hour.zfill(2)}:{minute.zfill(2)}")
        if day != "*":
            desc.append(f"on day {day}")
        if month != "*":
            desc.append(f"in month {month}")
        if dow != "*":
            desc.append(f"on day of week {dow}")
        return " ".join(desc)

    @classmethod
    def get_next_n_runs(
        cls, expression: str, n: int = 5, timezone: str = "Asia/Shanghai"
    ) -> list[datetime]:
        result = cls.parse(expression)
        if not result.valid:
            return []
        try:
            trigger = CronTrigger(
                minute=result.minute,
                hour=result.hour,
                day=result.day,
                month=result.month,
                day_of_week=result.day_of_week,
                timezone=timezone,
            )
            run_times, current = [], datetime.now()
            for _ in range(n):
                next_time = trigger.get_next_fire_time(None, current)
                if not next_time:
                    break
                run_times.append(next_time)
                current = next_time + timedelta(seconds=1)
            return run_times
        except Exception as e:
            logger.error(f"Failed to calculate next runs: {e}")
            return []


class IntervalBuilder:
    def __init__(self) -> None:
        self._weeks = self._days = self._hours = self._minutes = self._seconds = 0
        self._start_date: datetime | None = None
        self._end_date: datetime | None = None
        self._timezone = "Asia/Shanghai"

    def weeks(self, v: int) -> IntervalBuilder:
        self._weeks = v
        return self

    def days(self, v: int) -> IntervalBuilder:
        self._days = v
        return self

    def hours(self, v: int) -> IntervalBuilder:
        self._hours = v
        return self

    def minutes(self, v: int) -> IntervalBuilder:
        self._minutes = v
        return self

    def seconds(self, v: int) -> IntervalBuilder:
        self._seconds = v
        return self

    def build(self) -> IntervalTrigger:
        return IntervalTrigger(
            weeks=self._weeks,
            days=self._days,
            hours=self._hours,
            minutes=self._minutes,
            seconds=self._seconds,
            start_date=self._start_date,
            end_date=self._end_date,
            timezone=self._timezone,
        )


def every(value: int) -> _IntervalChain:
    return _IntervalChain(value)


class _IntervalChain:
    def __init__(self, value: int) -> None:
        self._value = value

    @property
    def seconds(self) -> IntervalBuilder:
        return IntervalBuilder().seconds(self._value)

    @property
    def minutes(self) -> IntervalBuilder:
        return IntervalBuilder().minutes(self._value)

    @property
    def hours(self) -> IntervalBuilder:
        return IntervalBuilder().hours(self._value)

    @property
    def days(self) -> IntervalBuilder:
        return IntervalBuilder().days(self._value)

    @property
    def weeks(self) -> IntervalBuilder:
        return IntervalBuilder().weeks(self._value)


class ScheduleBuilder:
    def __init__(self, timezone: str = "Asia/Shanghai") -> None:
        self._timezone = timezone

    def daily_at(self, hour: int, minute: int = 0) -> CronTrigger:
        return CronTrigger(hour=hour, minute=minute, timezone=self._timezone)

    def weekly_on(self, days: list, hour: int = 0, minute: int = 0) -> CronTrigger:
        day_values = [d.value if isinstance(d, DayOfWeek) else d.lower()[:3] for d in days]
        return CronTrigger(
            day_of_week=",".join(day_values), hour=hour, minute=minute, timezone=self._timezone
        )

    def monthly_on(self, day: int, hour: int = 0, minute: int = 0) -> CronTrigger:
        return CronTrigger(day=day, hour=hour, minute=minute, timezone=self._timezone)

    def every_n_minutes(self, n: int) -> CronTrigger:
        return CronTrigger(minute=f"*/{n}", timezone=self._timezone)

    def every_n_hours(self, n: int, at_minute: int = 0) -> CronTrigger:
        return CronTrigger(hour=f"*/{n}", minute=at_minute, timezone=self._timezone)

    def weekdays_at(self, hour: int, minute: int = 0) -> CronTrigger:
        return CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute, timezone=self._timezone)

    def weekends_at(self, hour: int, minute: int = 0) -> CronTrigger:
        return CronTrigger(day_of_week="sat,sun", hour=hour, minute=minute, timezone=self._timezone)

    def cron(self, expression: str) -> CronTrigger | None:
        result = CronExpressionParser.parse(expression)
        if not result.valid:
            logger.error(f"Invalid cron: {result.error}")
            return None
        return CronTrigger(
            minute=result.minute,
            hour=result.hour,
            day=result.day,
            month=result.month,
            day_of_week=result.day_of_week,
            timezone=self._timezone,
        )


__all__ = [
    "CronExpressionParser",
    "CronField",
    "CronParseResult",
    "DayOfWeek",
    "IntervalBuilder",
    "ScheduleBuilder",
    "every",
]
