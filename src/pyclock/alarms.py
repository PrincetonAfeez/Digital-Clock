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
