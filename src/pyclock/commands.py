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


class CommandRegistry:
    def __init__(self, commands: list[Command] | None = None) -> None:
        self._commands: dict[str, Command] = {}
        for command in commands or []:
            self.register(command)

    def register(self, command: Command) -> None:
        self._commands[command.key] = command

    def execute(self, key: str, state: ClockState, context: CommandContext) -> ClockState:
        command = self._commands.get(key)
        if command is None:
            return state
        return command.execute(state, context)

    def help_lines(self) -> list[str]:
        return [f"{key:<4} {cmd.description}" for key, cmd in sorted(self._commands.items())]

