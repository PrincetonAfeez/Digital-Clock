"""Reusable one-shot timer runtime."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import replace
from typing import TextIO

from pyclock import ansi
from pyclock.config import Config
from pyclock.domain import ClockState, DisplayMode, Duration, TimerState, parse_duration
from pyclock.time_sources import TimeSource


def run_one_shot_timer(
    value: str,
    label: str,
    config: Config,
    time_source: TimeSource,
    *,
    sleep: Callable[[float], None] = time.sleep,
    stream: TextIO = sys.stdout,
) -> int:
    """Run a one-shot timer."""
    duration = parse_duration(value)
    state = ClockState(
        current=time_source.now(),
        timezone=config.timezone,
        display_mode=DisplayMode.TIMER,
        time_format=config.time_format,
        timers=(TimerState("one-shot", duration, duration, label=label),),
    )
    remaining = duration
    try:
        while remaining.seconds > 0:
            state = replace(
                state,
                current=time_source.now(),
                timers=(replace(state.timers[0], remaining=remaining),),
            )
            stream.write(f"\r{label}: {remaining:hms}")
            stream.flush()
            sleep(1)
            remaining = remaining.clamp_subtract(Duration(1))
        stream.write(f"\r{label}: 00:00:00 {ansi.BELL}\n")
        stream.flush()
    except KeyboardInterrupt:
        stream.write("\nTimer cancelled.\n")
        stream.flush()
        return 130
    return 0
