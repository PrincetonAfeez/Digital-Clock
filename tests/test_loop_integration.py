"""Tests for the clock loop integration."""

from __future__ import annotations

import queue
import threading
from datetime import datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pytest

from pyclock.alarms import AlarmScheduler, InMemoryAlarmRepository
from pyclock.commands import default_registry
from pyclock.display import Display
from pyclock.domain import Alarm, ClockState, Duration, Time, TimerState
from pyclock.loop import ClockLoop
from pyclock.renderers import BigDigitRenderer, ColorScheme


def test_clock_loop_processes_input_and_renders_help_overlay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StepTimeSource:
        def __init__(self, current: datetime) -> None:
            self.current = current

        def now(self) -> datetime:
            value = self.current
            self.current = value + timedelta(seconds=1)
            return value

    class FakeInputListener:
        def __init__(self, events: queue.Queue[str], stop_event: threading.Event) -> None:
            self.events = events
            self.stop_event = stop_event

        def start(self) -> None:
            # Simulate an interactive session: open help, then quit.
            self.events.put("?")
            self.events.put("q")

        def join(self, timeout: float | None = None) -> None:
            return

    monkeypatch.setattr("pyclock.loop.InputListener", FakeInputListener)
    monkeypatch.setattr("pyclock.loop.time.sleep", lambda _: None)

    source = StepTimeSource(datetime(2026, 4, 21, 10, 0, 0, tzinfo=ZoneInfo("UTC")))
    stream = StringIO()
    display = Display(stream=stream, use_ansi=False)
    state = ClockState(current=source.now(), timezone="UTC")
    renderer = BigDigitRenderer(
        ColorScheme("test", use_color=False),
        command_help=default_registry().help_lines(),
    )
    loop = ClockLoop(
        state=state,
        time_source=source,
        display=display,
        renderer=renderer,
        commands=default_registry(),
        tick_rate=10.0,
    )

    exit_code = loop.run()

    assert exit_code == 0
    assert loop.stop_event.is_set()
    written = stream.getvalue()
    assert "Keys" in written
    assert "Toggle help" in written


def test_clock_loop_notifies_when_timer_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    class StepTimeSource:
        def __init__(self, current: datetime) -> None:
            self.current = current

        def now(self) -> datetime:
            value = self.current
            self.current = value + timedelta(seconds=1)
            return value

    class FakeInputListener:
        def __init__(self, events: queue.Queue[str], stop_event: threading.Event) -> None:
            self.events = events
            self.stop_event = stop_event

        def start(self) -> None:
            # Let the loop run a couple ticks, then quit.
            self.events.put("")
            self.events.put("")
            self.events.put("q")

        def join(self, timeout: float | None = None) -> None:
            return

    monkeypatch.setattr("pyclock.loop.InputListener", FakeInputListener)
    monkeypatch.setattr("pyclock.loop.time.sleep", lambda _: None)

    source = StepTimeSource(datetime(2026, 4, 21, 10, 0, 0, tzinfo=ZoneInfo("UTC")))
    stream = StringIO()
    display = Display(stream=stream, use_ansi=False)
    state = ClockState(
        current=source.now(),
        timezone="UTC",
        timers=(
            TimerState(
                id="timer-1",
                duration=Duration(1),
                remaining=Duration(1),
                label="tea",
            ),
        ),
    )
    renderer = BigDigitRenderer(
        ColorScheme("test", use_color=False),
        command_help=default_registry().help_lines(),
    )
    loop = ClockLoop(
        state=state,
        time_source=source,
        display=display,
        renderer=renderer,
        commands=default_registry(),
        tick_rate=10.0,
    )

    exit_code = loop.run()

    assert exit_code == 0
    assert any("Timer complete: tea" in note for note in loop.state.notifications)


def test_clock_loop_notifies_when_alarm_becomes_due(monkeypatch: pytest.MonkeyPatch) -> None:
    class StepTimeSource:
        def __init__(self, current: datetime) -> None:
            self.current = current

        def now(self) -> datetime:
            value = self.current
            self.current = value + timedelta(seconds=1)
            return value

    class FakeInputListener:
        def __init__(self, events: queue.Queue[str], stop_event: threading.Event) -> None:
            self.events = events
            self.stop_event = stop_event

        def start(self) -> None:
            self.events.put("")
            self.events.put("")
            self.events.put("q")

        def join(self, timeout: float | None = None) -> None:
            return

    monkeypatch.setattr("pyclock.loop.InputListener", FakeInputListener)
    monkeypatch.setattr("pyclock.loop.time.sleep", lambda _: None)

    source = StepTimeSource(datetime(2026, 4, 21, 10, 0, 0, tzinfo=ZoneInfo("UTC")))
    stream = StringIO()
    display = Display(stream=stream, use_ansi=False)
    repository = InMemoryAlarmRepository((Alarm("wake", Time(10, 0, 1), "wake up"),))
    loop = ClockLoop(
        state=ClockState(current=source.now(), timezone="UTC"),
        time_source=source,
        display=display,
        renderer=BigDigitRenderer(
            ColorScheme("test", use_color=False),
            command_help=default_registry().help_lines(),
        ),
        commands=default_registry(),
        scheduler=AlarmScheduler(repository),
        tick_rate=10.0,
    )

    exit_code = loop.run()

    assert exit_code == 0
    assert any("Alarm: wake up at 10:00" in note for note in loop.state.notifications)
