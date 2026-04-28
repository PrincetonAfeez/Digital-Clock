"""Keybinding command pattern."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from threading import Event

from pyclock.domain import ClockState, DisplayMode, Duration, TimeFormat, TimerState
from pyclock.mode_controller import ModeController
from pyclock.sessions import StopwatchSessionLog


@dataclass
class CommandContext:
    """Command context class."""
    stop_event: Event
    session_log: StopwatchSessionLog | None = None
    mode_controller: ModeController = ModeController()


class Command(ABC):
    """Command class."""
    key: str
    description: str

    @abstractmethod
    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Return the next state."""


class CommandRegistry:
    """Command registry class."""
    def __init__(self, commands: list[Command] | None = None) -> None:
        self._commands: dict[str, Command] = {}
        for command in commands or []:
            self.register(command)

    def register(self, command: Command) -> None:
        """Register the command."""
        self._commands[command.key] = command

    def execute(self, key: str, state: ClockState, context: CommandContext) -> ClockState:
        """Execute the command."""
        command = self._commands.get(key)
        if command is None:
            return state
        return command.execute(state, context)

    def help_lines(self) -> list[str]:
        """Return the help lines."""
        return [f"{key:<4} {cmd.description}" for key, cmd in sorted(self._commands.items())]


class QuitCommand(Command):
    """Quit the clock command."""
    key = "q"
    description = "Quit"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Quit the clock."""
        context.stop_event.set()
        return state


class ToggleHelpCommand(Command):
    """Toggle the help command."""
    key = "?"
    description = "Toggle help"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Toggle the help."""
        return replace(state, help_visible=not state.help_visible)


class ToggleFormatCommand(Command):
    """Toggle the 12/24-hour time command."""
    key = "f"
    description = "Toggle 12/24-hour time"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Toggle the 12/24-hour time."""
        next_format = TimeFormat.H12 if state.time_format is TimeFormat.H24 else TimeFormat.H24
        return replace(state, time_format=next_format)


class ToggleSecondsCommand(Command):
    """Toggle the seconds command."""
    key = "s"
    description = "Toggle seconds"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Toggle the seconds."""
        return replace(state, show_seconds=not state.show_seconds)


class ToggleDateCommand(Command):
    """Toggle the date line command."""
    key = "d"
    description = "Toggle date line"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Toggle the date line."""
        return replace(state, show_date=not state.show_date)


class NextModeCommand(Command):
    """Next mode command."""
    key = "m"
    description = "Next mode"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Next mode."""
        return replace(
            state,
            display_mode=context.mode_controller.next(state.display_mode),
        )


class SetModeCommand(Command):
    """Set the display mode command."""
    def __init__(self, key: str, mode: DisplayMode, description: str) -> None:
        self.key = key
        self.mode = mode
        self.description = description

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Set the display mode."""
        return replace(
            state,
            display_mode=context.mode_controller.transition(state.display_mode, self.mode),
        )


class StopwatchToggleCommand(Command):
    """Start/stop stopwatch or Pomodoro command."""
    key = " "
    description = "Start/stop stopwatch or Pomodoro"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Start/stop stopwatch or Pomodoro."""
        if state.display_mode is DisplayMode.POMODORO:
            return replace(state, pomodoro=state.pomodoro.toggle())
        stopwatch = replace(state.stopwatch, running=not state.stopwatch.running)
        return replace(state, stopwatch=stopwatch)


class StopwatchResetCommand(Command):
    """Reset stopwatch/Pomodoro command."""
    key = "r"
    description = "Reset stopwatch/Pomodoro"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Reset stopwatch/Pomodoro."""
        if state.display_mode is DisplayMode.POMODORO:
            return replace(state, pomodoro=state.pomodoro.reset())
        if context.session_log and state.stopwatch.elapsed.seconds:
            context.session_log.append(state.stopwatch, state.current)
        return replace(state, stopwatch=type(state.stopwatch)())


class StopwatchLapCommand(Command):
    """Record stopwatch lap command."""
    key = "l"
    description = "Record stopwatch lap"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        return replace(state, stopwatch=state.stopwatch.lap())


class AddFiveMinuteTimerCommand(Command):
    """Add a 5-minute timer command."""
    key = "t"
    description = "Add a 5-minute timer"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        """Add a 5-minute timer."""
        duration = Duration.from_hms(minutes=5)
        timer = TimerState(
            id=f"timer-{len(state.timers) + 1}",
            duration=duration,
            remaining=duration,
            label="quick timer",
        )
        return replace(state, display_mode=DisplayMode.TIMER, timers=(*state.timers, timer))


class ClearDoneTimersCommand(Command):
    """Clear completed timers command."""
    key = "c"
    description = "Clear completed timers"

    def execute(self, state: ClockState, context: CommandContext) -> ClockState:
        return replace(state, timers=tuple(timer for timer in state.timers if not timer.completed))


def default_registry() -> CommandRegistry:
    """Return the default command registry."""
    return CommandRegistry(
        [
            QuitCommand(),
            ToggleHelpCommand(),
            ToggleFormatCommand(),
            ToggleSecondsCommand(),
            ToggleDateCommand(),
            NextModeCommand(),
            SetModeCommand("1", DisplayMode.CLOCK, "Clock mode"),
            SetModeCommand("2", DisplayMode.STOPWATCH, "Stopwatch mode"),
            SetModeCommand("3", DisplayMode.TIMER, "Timer mode"),
            SetModeCommand("4", DisplayMode.WORLD_CLOCK, "World clock mode"),
            SetModeCommand("5", DisplayMode.ALARM_LIST, "Alarm list mode"),
            SetModeCommand("6", DisplayMode.POMODORO, "Pomodoro mode"),
            StopwatchToggleCommand(),
            StopwatchResetCommand(),
            StopwatchLapCommand(),
            AddFiveMinuteTimerCommand(),
            ClearDoneTimersCommand(),
        ]
    )
