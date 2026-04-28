"""Interactive clock loop."""

from __future__ import annotations

import queue
import signal
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta

from pyclock import ansi
from pyclock.alarms import AlarmScheduler
from pyclock.commands import CommandContext, CommandRegistry, default_registry
from pyclock.display import Display, InputListener
from pyclock.domain import ClockState, Duration
from pyclock.renderers import BigDigitRenderer, Renderer
from pyclock.sessions import StopwatchSessionLog
from pyclock.time_sources import TimeSource


class ClockLoop:
    def __init__(
        self,
        state: ClockState,
        time_source: TimeSource,
        display: Display,
        renderer: Renderer | None = None,
        commands: CommandRegistry | None = None,
        scheduler: AlarmScheduler | None = None,
        tick_rate: float = 10.0,
    ) -> None:
        self.state = state
        self.time_source = time_source
        self.display = display
        self.commands = commands or default_registry()
        if renderer is None:
            renderer = BigDigitRenderer(command_help=self.commands.help_lines())
        self.renderer = renderer
        self.scheduler = scheduler
        self.tick_rate = tick_rate
        self.stop_event = threading.Event()
        self.events: queue.Queue[str] = queue.Queue()
        self.context = CommandContext(self.stop_event, StopwatchSessionLog())

    def run(self) -> int:
        previous_signal = signal.getsignal(signal.SIGINT)

        def handle_sigint(signum: int, frame: object) -> None:
            self.stop_event.set()

        signal.signal(signal.SIGINT, handle_sigint)
        listener = InputListener(self.events, self.stop_event)
        listener.start()
        self.display.start()
        previous_tick_time = self.state.current
        tick_seconds = 1 / max(self.tick_rate, 1)

        try:
            while not self.stop_event.is_set():
                loop_started = time.monotonic()
                now = self.time_source.now()
                delta_seconds = max(int((now - previous_tick_time).total_seconds()), 0)
                if delta_seconds:
                    previous_tick_time += timedelta(seconds=delta_seconds)
                delta = Duration(delta_seconds)
                self.state = self._tick(now, delta)
                self._drain_events()
                self.display.write(self.renderer.render(self.state))
                sleep_for = max(tick_seconds - (time.monotonic() - loop_started), 0)
                time.sleep(sleep_for)
        finally:
            self.stop_event.set()
            listener.join(timeout=0.5)
            self.display.stop()
            signal.signal(signal.SIGINT, previous_signal)
        return 0

    def _tick(self, now: datetime, delta: Duration) -> ClockState:
        previous_timers = {timer.id: timer for timer in self.state.timers}
        state = replace(
            self.state,
            current=now,
            stopwatch=self.state.stopwatch.tick(delta),
            timers=tuple(timer.tick(delta) for timer in self.state.timers),
            pomodoro=self.state.pomodoro.tick(delta),
        )
        for timer in state.timers:
            previous = previous_timers.get(timer.id)
            if previous is not None and not previous.completed and timer.completed:
                label = timer.label or timer.id
                state = state.with_notification(f"{ansi.BELL}Timer complete: {label}")

        if self.scheduler is not None:
            due = self.scheduler.due(self.state.current, state.current)
            for alarm in due:
                message = f"{ansi.BELL}Alarm: {alarm.display_label()} at {alarm.at:hm}"
                state = state.with_notification(message)
        return state

    def _drain_events(self) -> None:
        while True:
            try:
                key = self.events.get_nowait()
            except queue.Empty:
                return
            self.state = self.commands.execute(key, self.state, self.context)
