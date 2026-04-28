"""Injectable time sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pyclock.exceptions import InvalidTimezoneError


class TimeSource(Protocol):
    def now(self) -> datetime:
        """Return the current aware datetime."""


def load_zone(name: str | None) -> ZoneInfo:
    zone_name = name or "UTC"
    try:
        return ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        msg = f"unknown timezone: {zone_name}"
        raise InvalidTimezoneError(msg) from exc


@dataclass
class SystemTimeSource:
    timezone_name: str = "UTC"

    def __post_init__(self) -> None:
        self._zone = load_zone(self.timezone_name)

    def now(self) -> datetime:
        return datetime.now(self._zone)


@dataclass
class FrozenTimeSource:
    current: datetime

    def __post_init__(self) -> None:
        if self.current.tzinfo is None:
            self.current = self.current.replace(tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


@dataclass
class AcceleratedTimeSource:
    base: datetime
    factor: float = 10.0
    real_start: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.base.tzinfo is None:
            self.base = self.base.replace(tzinfo=UTC)
        if self.real_start.tzinfo is None:
            self.real_start = self.real_start.replace(tzinfo=UTC)

    def now(self) -> datetime:
        real_elapsed = datetime.now(UTC) - self.real_start
        simulated = real_elapsed.total_seconds() * self.factor
        return self.base + timedelta(seconds=simulated)
