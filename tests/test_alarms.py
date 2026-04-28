"""Tests for the alarm scheduler."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pyclock.alarms import AlarmScheduler, InMemoryAlarmRepository
from pyclock.domain import Alarm, Time
from pyclock.exceptions import AlarmConflictError


def test_alarm_scheduler_fires_when_crossing_target() -> None:
    repository = InMemoryAlarmRepository((Alarm("wake", Time(7, 30), "wake up"),))
    scheduler = AlarmScheduler(repository)
    previous = datetime(2026, 4, 21, 7, 29, 59, tzinfo=ZoneInfo("UTC"))
    current = previous + timedelta(seconds=1)

    due = scheduler.due(previous, current)

    assert [alarm.id for alarm in due] == ["wake"]
    assert repository.list()[0].last_triggered_date == "2026-04-21"


def test_alarm_scheduler_does_not_repeat_same_day() -> None:
    repository = InMemoryAlarmRepository((Alarm("wake", Time(7, 30), "wake up"),))
    scheduler = AlarmScheduler(repository)
    previous = datetime(2026, 4, 21, 7, 29, 59, tzinfo=ZoneInfo("UTC"))
    current = previous + timedelta(seconds=1)

    scheduler.due(previous, current)
    assert scheduler.due(previous, current) == ()


def test_alarm_scheduler_handles_midnight_crossing() -> None:
    repository = InMemoryAlarmRepository((Alarm("late", Time(23, 59, 59), "late"),))
    scheduler = AlarmScheduler(repository)
    previous = datetime(2026, 4, 21, 23, 59, 58, tzinfo=ZoneInfo("UTC"))
    current = datetime(2026, 4, 22, 0, 0, 1, tzinfo=ZoneInfo("UTC"))

    due = scheduler.due(previous, current)

    assert [alarm.id for alarm in due] == ["late"]
    assert repository.list()[0].last_triggered_date == "2026-04-21"


def test_repository_rejects_duplicate_active_alarm_time() -> None:
    repository = InMemoryAlarmRepository((Alarm("first", Time(7, 30), "first"),))

    try:
        repository.add(Time(7, 30), "second")
    except AlarmConflictError:
        pass
    else:
        raise AssertionError("duplicate alarm was accepted")
