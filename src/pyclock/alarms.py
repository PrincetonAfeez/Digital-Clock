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

