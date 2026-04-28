from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from pyclock.domain import Alarm, Time
from pyclock.exceptions import AlarmConflictError
from pyclock.paths import default_alarms_path

class AlarmRepository(ABC):
    @abstractmethod
    def list(self) -> tuple[Alarm, ...]:

    @abstractmethod
    def save_all(self, alarms: tuple[Alarm, ...]) -> None:

    def add(self, at: Time, label: str = "", snooze_minutes: int = 5) -> Alarm:
        alarms = self.list()
        if any(alarm.enabled and alarm.at == at for alarm in alarms):
            msg = f"an enabled alarm already exists for {at:hm}"
            raise AlarmConflictError(msg)
        alarm = Alarm(uuid.uuid4().hex[:8], at, label=label, snooze_minutes=snooze_minutes)
        self.save_all((*alarms, alarm))
        return alarm

    def remove(self, alarm_id: str) -> bool:
        alarms = self.list()
        remaining = tuple(alarm for alarm in alarms if alarm.id != alarm_id)
        self.save_all(remaining)
        return len(remaining) != len(alarms)

class JSONAlarmRepository(AlarmRepository):
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_alarms_path()

    def list(self) -> tuple[Alarm, ...]:
        if not self.path.exists():
            return ()
        with self.path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return tuple(_alarm_from_json(item) for item in raw)

    def save_all(self, alarms: tuple[Alarm, ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                **asdict(alarm),
                "at": {
                    "hours": alarm.at.hours,
                    "minutes": alarm.at.minutes,
                    "seconds": alarm.at.seconds,
                },
            }
            for alarm in alarms
        ]
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

class InMemoryAlarmRepository(AlarmRepository):
    def __init__(self, alarms: tuple[Alarm, ...] = ()) -> None:
        self._alarms = alarms

    def list(self) -> tuple[Alarm, ...]:
        return self._alarms

    def save_all(self, alarms: tuple[Alarm, ...]) -> None:
        self._alarms = alarms

class AlarmScheduler:
    def __init__(self, repository: AlarmRepository) -> None:
        self.repository = repository

    def due(self, previous: datetime, current: datetime) -> tuple[Alarm, ...]:
        alarms = self.repository.list()
        due: list[Alarm] = []
        updated: list[Alarm] = []

        for alarm in alarms:
            if not alarm.enabled:
                updated.append(alarm)
                continue

            triggered_date = self._crossed_date(alarm, previous, current)
            if triggered_date is not None:
                due.append(alarm)
                updated.append(replace(alarm, last_triggered_date=triggered_date))
                continue
            updated.append(alarm)

        if due:
            self.repository.save_all(tuple(updated))
        return tuple(due)

    def _crossed_date(self, alarm: Alarm, previous: datetime, current: datetime) -> str | None:
        day_count = (current.date() - previous.date()).days
        for offset in range(day_count + 1):
            day = previous.date() + timedelta(days=offset)
            target = current.replace(
                year=day.year,
                month=day.month,
                day=day.day,
                hour=alarm.at.hours,
                minute=alarm.at.minutes,
                second=alarm.at.seconds,
                microsecond=0,
            )
            target_date = target.date().isoformat()
            if alarm.last_triggered_date == target_date:
                continue
            if previous <= target <= current:
                return target_date
        return None

