from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from threading import Event

from pyclock.domain import ClockState, DisplayMode, Duration, TimeFormat, TimerState
from pyclock.mode_controller import ModeController
from pyclock.sessions import StopwatchSessionLog



@dataclass
class CommandContext:
    stop_event: Event
    session_log: StopwatchSessionLog | None = None
    mode_controller: ModeController = ModeController()

class Command(ABC):
    key: str
    description: str

    @abstractmethod
    def execute(self, state: ClockState, context: CommandContext) -> ClockState:


