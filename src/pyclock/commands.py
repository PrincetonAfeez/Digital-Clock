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


class QuitCommand(Command):
    key = "q"
    description = "Quit"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        context.stop_event.set()
        return state

class ToggleHelpCommand(Command):
    key = "?"
    description = "Toggle help"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        return replace(state, help_visible=not state.help_visible)


class ToggleFormatCommand(Command):
    key = "f"
    description = "Toggle 12/24-hour time"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        next_format = TimeFormat.H12 if state.time_format is TimeFormat.H24 else TimeFormat.H24
        return replace(state, time_format=next_format)

class ToggleSecondsCommand(Command):
    key = "s"
    description = "Toggle seconds"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        return replace(state, show_seconds=not state.show_seconds)


class ToggleDateCommand(Command):
    key = "d"
    description = "Toggle date line"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        return replace(state, show_date=not state.show_date)

class NextModeCommand(Command):
    key = "m"
    description = "Next mode"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        return replace(
            state,
            display_mode=context.mode_controller.next(state.display_mode),
        )

class SetModeCommand(Command):
    def __init__(self, key: str, mode: DisplayMode, description: str) -> None:
        self.key = key
        self.mode = mode
        self.description = description

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        return replace(
            state,
            display_mode=context.mode_controller.transition(state.display_mode, self.mode),
        )

class StopwatchToggleCommand(Command):
    key = " "
    description = "Start/stop stopwatch or Pomodoro"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        if state.display_mode is DisplayMode.POMODORO:
            return replace(state, pomodoro=state.pomodoro.toggle())
        stopwatch = replace(state.stopwatch, running=not state.stopwatch.running)
        return replace(state, stopwatch=stopwatch)

class StopwatchResetCommand(Command):
    key = "r"
    description = "Reset stopwatch/Pomodoro"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        if state.display_mode is DisplayMode.POMODORO:
            return replace(state, pomodoro=state.pomodoro.reset())
        if context.session_log and state.stopwatch.elapsed.seconds:
            context.session_log.append(state.stopwatch, state.current)
        return replace(state, stopwatch=type(state.stopwatch)())

class StopwatchLapCommand(Command):
    key = "l"
    description = "Record stopwatch lap"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        return replace(state, stopwatch=state.stopwatch.lap())


class AddFiveMinuteTimerCommand(Command):
    key = "t"
    description = "Add a 5-minute timer"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        duration = Duration.from_hms(minutes=5)
        timer = TimerState(
            id=f"timer-{len(state.timers) + 1}",
            duration=duration,
            remaining=duration,
            label="quick timer",
        )
        return replace(state, display_mode=DisplayMode.TIMER, timers=(*state.timers, timer))


class ClearDoneTimersCommand(Command):
    key = "c"
    description = "Clear completed timers"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        return replace(state, timers=tuple(timer for timer in state.timers if not timer.completed))
