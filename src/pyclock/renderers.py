"""Renderer strategies for terminal output."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pyclock import ansi
from pyclock.domain import ClockState, DisplayMode, TimeFormat, TimerState

ASCII_FONT: dict[str, tuple[str, ...]] = {
    "0": (" ### ", "#   #", "#   #", "#   #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "   # ", "  #  ", "#####"),
    "3": ("#### ", "    #", " ### ", "    #", "#### "),
    "4": ("#  # ", "#  # ", "#####", "   # ", "   # "),
    "5": ("#####", "#    ", "#### ", "    #", "#### "),
    "6": (" ### ", "#    ", "#### ", "#   #", " ### "),
    "7": ("#####", "   # ", "  #  ", " #   ", "#    "),
    "8": (" ### ", "#   #", " ### ", "#   #", " ### "),
    "9": (" ### ", "#   #", " ####", "    #", " ### "),
    ":": ("     ", "  #  ", "     ", "  #  ", "     "),
    " ": ("     ", "     ", "     ", "     ", "     "),
    "A": (" ### ", "#   #", "#####", "#   #", "#   #"),
    "P": ("#### ", "#   #", "#### ", "#    ", "#    "),
    "M": ("#   #", "## ##", "# # #", "#   #", "#   #"),
    "-": ("     ", "     ", "#####", "     ", "     "),
}


@dataclass(frozen=True)
class ColorScheme:
    """Color scheme class."""
    name: str
    foreground: str = "green"
    background: str = "black"
    accent: str = "cyan"
    muted: str = "white"
    use_color: bool = True
    rainbow_seconds: bool = False

    def paint(self, text: str, color: str | None = None) -> str:
        if not self.use_color:
            return text
        return ansi.colorize(text, foreground=color or self.foreground, background=self.background)


SCHEMES: dict[str, ColorScheme] = {
    "classic": ColorScheme("classic", foreground="green", background="black", accent="cyan"),
    "amber": ColorScheme("amber", foreground="yellow", background="black", accent="red"),
    "mono": ColorScheme("mono", foreground="white", background="black", accent="white"),
    "rainbow-seconds": ColorScheme(
        "rainbow-seconds",
        foreground="green",
        background="black",
        accent="magenta",
        rainbow_seconds=True,
    ),
}


class Renderer(ABC):
    @abstractmethod
    def render(self, state: ClockState) -> str:
        """Render a state snapshot without touching I/O."""


def format_datetime(value: datetime, time_format: TimeFormat, show_seconds: bool = True) -> str:
    if time_format is TimeFormat.H24:
        return value.strftime("%H:%M:%S" if show_seconds else "%H:%M")
    return value.strftime("%I:%M:%S %p" if show_seconds else "%I:%M %p")


def _big_text(text: str) -> str:
    glyphs = [ASCII_FONT.get(char.upper(), ASCII_FONT[" "]) for char in text]
    lines = []
    for row in range(5):
        lines.append(" ".join(glyph[row] for glyph in glyphs).rstrip())
    return "\n".join(lines)


def _mode_title(state: ClockState) -> str:
    mode = state.display_mode.value.replace("_", " ").title()
    return f"PyClock | {mode} | {state.timezone}"


def _timer_line(index: int, timer: TimerState) -> str:
    label = timer.label or f"timer {index}"
    remaining = timer.remaining
    status = "done" if timer.completed else "running"
    return f"{index:>2}. {label:<18} {remaining:hms} {status}"


class BigDigitRenderer(Renderer):
    def __init__(
        self,
        scheme: ColorScheme | None = None,
        command_help: list[str] | None = None,
    ) -> None:
        self.scheme = scheme or SCHEMES["classic"]
        self.command_help = command_help or []

    def render(self, state: ClockState) -> str:
        body = {
            DisplayMode.CLOCK: self._clock,
            DisplayMode.STOPWATCH: self._stopwatch,
            DisplayMode.TIMER: self._timer,
            DisplayMode.WORLD_CLOCK: self._world_clock,
            DisplayMode.ALARM_LIST: self._alarms,
            DisplayMode.POMODORO: self._pomodoro,
        }[state.display_mode](state)

        parts = [self.scheme.paint(_mode_title(state), self.scheme.accent), body]
        if state.notifications:
            parts.append(self.scheme.paint("\n".join(state.notifications[:3]), self.scheme.muted))
        if state.help_visible:
            parts.append(self._help())
        else:
            parts.append(self.scheme.paint("Press ? for keys, q to quit.", self.scheme.muted))
        return "\n\n".join(part for part in parts if part)

    def _clock(self, state: ClockState) -> str:
        text = format_datetime(state.current, state.time_format, state.show_seconds)
        rendered = self.scheme.paint(_big_text(text))
        if state.show_date:
            return f"{rendered}\n\n{state.current.strftime('%A, %B %d, %Y')}"
        return rendered

    def _stopwatch(self, state: ClockState) -> str:
        lines = [self.scheme.paint(_big_text(format(state.stopwatch.elapsed, "hms")))]
        state_label = "running" if state.stopwatch.running else "stopped"
        lines.append(f"Stopwatch {state_label}")
        if state.stopwatch.laps:
            lines.append("Laps")
            for index, lap in enumerate(state.stopwatch.laps[:8], start=1):
                lines.append(f"{index:>2}. {lap:hms}")
        return "\n".join(lines)

    def _timer(self, state: ClockState) -> str:
        if not state.timers:
            return "No timers. Use `pyclock timer 5m` for a one-shot timer."
        lines = [self.scheme.paint(_big_text(format(state.timers[0].remaining, "hms")))]
        lines.extend(_timer_line(index, timer) for index, timer in enumerate(state.timers, start=1))
        return "\n".join(lines)

    def _world_clock(self, state: ClockState) -> str:
        lines = []
        for zone_name in state.world_clock_zones:
            try:
                local = state.current.astimezone(ZoneInfo(zone_name))
            except ZoneInfoNotFoundError:
                local = state.current
            rendered_time = format_datetime(local, state.time_format, state.show_seconds)
            lines.append(f"{zone_name:<24} {rendered_time}")
        return "\n".join(lines)

    def _alarms(self, state: ClockState) -> str:
        if not state.active_alarms:
            return "No alarms saved."
        lines = ["ID       Time      Label"]
        for alarm in state.active_alarms:
            marker = "" if alarm.enabled else "off"
            line = f"{alarm.id:<8} {alarm.at:hm}    {alarm.display_label()} {marker}"
            lines.append(line.rstrip())
        return "\n".join(lines)

    def _pomodoro(self, state: ClockState) -> str:
        phase = "Break" if state.pomodoro.in_break else "Work"
        running = "running" if state.pomodoro.running else "paused"
        return "\n".join(
            [
                self.scheme.paint(_big_text(format(state.pomodoro.remaining, "hms"))),
                f"{phase} session | {running} | completed: {state.pomodoro.sessions_completed}",
            ]
        )

    def _help(self) -> str:
        if not self.command_help:
            return "No keys registered."
        return "Keys\n" + "\n".join(self.command_help)


class CompactRenderer(Renderer):
    def __init__(self, scheme: ColorScheme | None = None) -> None:
        self.scheme = scheme or SCHEMES["mono"]

    def render(self, state: ClockState) -> str:
        if state.display_mode is DisplayMode.WORLD_CLOCK:
            return " | ".join(_compact_zone_line(state, zone) for zone in state.world_clock_zones)
        rendered_time = format_datetime(state.current, state.time_format, state.show_seconds)
        return self.scheme.paint(rendered_time)


class MinimalRenderer(Renderer):
    def render(self, state: ClockState) -> str:
        if state.display_mode is DisplayMode.WORLD_CLOCK:
            return "\n".join(_minimal_zone_line(state, zone) for zone in state.world_clock_zones)
        return format_datetime(state.current, state.time_format, state.show_seconds)


def _zone_time(state: ClockState, zone: str) -> str:
    try:
        local = state.current.astimezone(ZoneInfo(zone))
    except ZoneInfoNotFoundError:
        local = state.current
    return format_datetime(local, state.time_format, state.show_seconds)


def _compact_zone_line(state: ClockState, zone: str) -> str:
    """Return the compact zone line."""
    return f"{zone}: {_zone_time(state, zone)}"


def _minimal_zone_line(state: ClockState, zone: str) -> str:
    """Return the minimal zone line."""
    return f"{zone}\t{_zone_time(state, zone)}"
