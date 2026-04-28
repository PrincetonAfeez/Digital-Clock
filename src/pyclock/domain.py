"""Core immutable domain objects for PyClock."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timedelta
from enum import Enum
from functools import total_ordering
from typing import Self

from pyclock.exceptions import InvalidDurationError


class DisplayMode(Enum):
    CLOCK = "clock"
    STOPWATCH = "stopwatch"
    TIMER = "timer"
    WORLD_CLOCK = "world"
    ALARM_LIST = "alarms"
    POMODORO = "pomodoro"


class TimeFormat(Enum):
    H12 = "12"
    H24 = "24"

    def __str__(self) -> str:
        return "12-hour" if self is TimeFormat.H12 else "24-hour"

    @classmethod
    def parse(cls, value: str | int | None) -> Self:
        if value in (12, "12", "h12", "H12"):
            return cls.H12
        if value in (24, "24", "h24", "H24", None):
            return cls.H24
        msg = f"unsupported time format: {value!r}"
        raise ValueError(msg)


@dataclass(frozen=True, order=True)
class Time:
    """Time-of-day without a date."""

    hours: int
    minutes: int
    seconds: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.hours <= 23:
            msg = "hours must be in 0..23"
            raise ValueError(msg)
        if not 0 <= self.minutes <= 59:
            msg = "minutes must be in 0..59"
            raise ValueError(msg)
        if not 0 <= self.seconds <= 59:
            msg = "seconds must be in 0..59"
            raise ValueError(msg)

    @classmethod
    def from_datetime(cls, value: datetime) -> Self:
        return cls(value.hour, value.minute, value.second)

    @classmethod
    def parse(cls, value: str) -> Self:
        match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*", value)
        if not match:
            msg = "time must look like HH:MM or HH:MM:SS"
            raise ValueError(msg)
        hours, minutes, seconds = match.groups(default="0")
        return cls(int(hours), int(minutes), int(seconds))

    def to_time(self) -> time:
        return time(self.hours, self.minutes, self.seconds)

    def total_seconds(self) -> int:
        return self.hours * 3600 + self.minutes * 60 + self.seconds

    def __format__(self, spec: str) -> str:
        if spec in ("", "24"):
            return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}"
        if spec == "hm":
            return f"{self.hours:02d}:{self.minutes:02d}"
        if spec == "12":
            suffix = "AM" if self.hours < 12 else "PM"
            hour = self.hours % 12 or 12
            return f"{hour:02d}:{self.minutes:02d}:{self.seconds:02d} {suffix}"
        msg = f"unknown Time format specifier: {spec}"
        raise ValueError(msg)


_DURATION_RE = re.compile(
    r"^\s*(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?\s*$",
    re.IGNORECASE,
)


@total_ordering
@dataclass(frozen=True)
class Duration:
    """Non-negative duration with arithmetic and format helpers."""

    seconds: int

    def __post_init__(self) -> None:
        if self.seconds < 0:
            msg = "duration cannot be negative"
            raise InvalidDurationError(msg)

    @classmethod
    def from_hms(cls, hours: int = 0, minutes: int = 0, seconds: int = 0) -> Self:
        return cls(hours * 3600 + minutes * 60 + seconds)

    @classmethod
    def from_timedelta(cls, value: timedelta) -> Self:
        total = int(value.total_seconds())
        return cls(max(total, 0))

    def to_timedelta(self) -> timedelta:
        return timedelta(seconds=self.seconds)

    def clamp_subtract(self, other: Duration) -> Duration:
        return Duration(max(self.seconds - other.seconds, 0))

    def __add__(self, other: object) -> Duration:
        if isinstance(other, Duration):
            return Duration(self.seconds + other.seconds)
        if isinstance(other, timedelta):
            return Duration.from_timedelta(self.to_timedelta() + other)
        return NotImplemented

    def __sub__(self, other: object) -> Duration:
        if isinstance(other, Duration):
            result = self.seconds - other.seconds
        elif isinstance(other, timedelta):
            result = int((self.to_timedelta() - other).total_seconds())
        else:
            return NotImplemented
        if result < 0:
            msg = "duration subtraction would be negative"
            raise InvalidDurationError(msg)
        return Duration(result)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.seconds < other.seconds

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return False
        return self.seconds == other.seconds

    def __int__(self) -> int:
        return self.seconds

    def __bool__(self) -> bool:
        return self.seconds > 0

    def __format__(self, spec: str) -> str:
        hours, remainder = divmod(self.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if spec in ("", "hms"):
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        if spec == "ms":
            total_minutes = self.seconds // 60
            return f"{total_minutes}:{seconds:02d}"
        if spec == "compact":
            parts: list[str] = []
            if hours:
                parts.append(f"{hours}h")
            if minutes:
                parts.append(f"{minutes}m")
            if seconds or not parts:
                parts.append(f"{seconds}s")
            return "".join(parts)
        msg = f"unknown Duration format specifier: {spec}"
        raise ValueError(msg)

    def __str__(self) -> str:
        return format(self, "compact")


def parse_duration(value: str) -> Duration:
    """Parse strings such as 5m, 1h30m, 90s, and 01:02:03."""

    text = value.strip()
    if not text:
        msg = "duration cannot be empty"
        raise InvalidDurationError(msg)

    if ":" in text:
        parts = text.split(":")
        if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
            msg = f"invalid duration: {value!r}"
            raise InvalidDurationError(msg)
        numbers = [int(part) for part in parts]
        if len(numbers) == 2:
            minutes, seconds = numbers
            hours = 0
        else:
            hours, minutes, seconds = numbers
        if minutes > 59 or seconds > 59:
            msg = "duration minutes and seconds must be in 0..59 for colon format"
            raise InvalidDurationError(msg)
        return Duration.from_hms(hours, minutes, seconds)

    if text.isdigit():
        return Duration(int(text))

    match = _DURATION_RE.fullmatch(text)
    if not match or not any(match.groupdict().values()):
        msg = f"invalid duration: {value!r}"
        raise InvalidDurationError(msg)
    return Duration.from_hms(
        int(match.group("hours") or 0),
        int(match.group("minutes") or 0),
        int(match.group("seconds") or 0),
    )


@dataclass(frozen=True)
class Alarm:
    id: str
    at: Time
    label: str = ""
    enabled: bool = True
    snooze_minutes: int = 5
    last_triggered_date: str | None = None

    def display_label(self) -> str:
        return self.label or "alarm"


@dataclass(frozen=True)
class TimerState:
    id: str
    duration: Duration
    remaining: Duration
    label: str = ""
    running: bool = True
    completed: bool = False

    def tick(self, delta: Duration) -> TimerState:
        if not self.running or self.completed:
            return self
        remaining = self.remaining.clamp_subtract(delta)
        return replace(self, remaining=remaining, completed=remaining.seconds == 0)


@dataclass(frozen=True)
class StopwatchState:
    elapsed: Duration = field(default_factory=lambda: Duration(0))
    running: bool = False
    laps: tuple[Duration, ...] = ()

    def tick(self, delta: Duration) -> StopwatchState:
        if not self.running:
            return self
        return replace(self, elapsed=self.elapsed + delta)

    def lap(self) -> StopwatchState:
        return replace(self, laps=(self.elapsed, *self.laps))


@dataclass(frozen=True)
class PomodoroState:
    work_duration: Duration = field(default_factory=lambda: Duration.from_hms(minutes=25))
    break_duration: Duration = field(default_factory=lambda: Duration.from_hms(minutes=5))
    remaining: Duration = field(default_factory=lambda: Duration.from_hms(minutes=25))
    in_break: bool = False
    running: bool = False
    sessions_completed: int = 0

    def tick(self, delta: Duration) -> PomodoroState:
        if not self.running:
            return self
        remaining = self.remaining.clamp_subtract(delta)
        if remaining.seconds > 0:
            return replace(self, remaining=remaining)
        if self.in_break:
            return replace(
                self,
                remaining=self.work_duration,
                in_break=False,
                sessions_completed=self.sessions_completed + 1,
            )
        return replace(self, remaining=self.break_duration, in_break=True)

    def toggle(self) -> PomodoroState:
        return replace(self, running=not self.running)

    def reset(self) -> PomodoroState:
        return replace(self, remaining=self.work_duration, in_break=False, running=False)


@dataclass(frozen=True)
class ClockState:
    """Single source of truth passed to renderers."""

    current: datetime
    timezone: str
    display_mode: DisplayMode = DisplayMode.CLOCK
    time_format: TimeFormat = TimeFormat.H24
    show_seconds: bool = True
    show_date: bool = True
    active_alarms: tuple[Alarm, ...] = ()
    timers: tuple[TimerState, ...] = ()
    stopwatch: StopwatchState = field(default_factory=StopwatchState)
    world_clock_zones: tuple[str, ...] = ("UTC", "America/New_York", "Europe/London", "Asia/Tokyo")
    pomodoro: PomodoroState = field(default_factory=PomodoroState)
    help_visible: bool = False
    notifications: tuple[str, ...] = ()

    @property
    def current_time(self) -> Time:
        return Time.from_datetime(self.current)

    def with_notification(self, message: str) -> ClockState:
        return replace(self, notifications=(message, *self.notifications[:3]))
