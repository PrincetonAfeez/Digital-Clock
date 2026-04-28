from __future__ import annotations

import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from pyclock.commands import CommandContext, default_registry
from pyclock.domain import ClockState, DisplayMode, TimeFormat


def test_command_registry_generates_help_from_commands() -> None:
    registry = default_registry()

    assert any("Toggle 12/24-hour time" in line for line in registry.help_lines())


def test_toggle_format_command_returns_new_state() -> None:
    registry = default_registry()
    state = ClockState(datetime(2026, 4, 21, 10, 0, tzinfo=ZoneInfo("UTC")), "UTC")
    context = CommandContext(threading.Event())

    next_state = registry.execute("f", state, context)

    assert state.time_format is TimeFormat.H24
    assert next_state.time_format is TimeFormat.H12


def test_mode_command_switches_without_io() -> None:
    registry = default_registry()
    state = ClockState(datetime(2026, 4, 21, 10, 0, tzinfo=ZoneInfo("UTC")), "UTC")
    context = CommandContext(threading.Event())

    next_state = registry.execute("4", state, context)

    assert next_state.display_mode is DisplayMode.WORLD_CLOCK


def test_next_mode_uses_mode_controller() -> None:
    registry = default_registry()
    state = ClockState(datetime(2026, 4, 21, 10, 0, tzinfo=ZoneInfo("UTC")), "UTC")
    context = CommandContext(threading.Event())

    next_state = registry.execute("m", state, context)

    assert next_state.display_mode is DisplayMode.STOPWATCH
