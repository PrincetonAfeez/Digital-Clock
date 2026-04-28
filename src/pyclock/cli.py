"""Command-line entry point."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from pyclock import ansi
from pyclock.alarms import AlarmScheduler, JSONAlarmRepository
from pyclock.commands import default_registry
from pyclock.config import Config, load_config
from pyclock.display import Display
from pyclock.domain import (
    ClockState,
    DisplayMode,
    Duration,
    PomodoroState,
    Time,
    TimeFormat,
)
from pyclock.loop import ClockLoop
from pyclock.renderers import SCHEMES, BigDigitRenderer, MinimalRenderer
from pyclock.time_sources import SystemTimeSource
from pyclock.timer_runner import run_one_shot_timer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyclock", description="Terminal digital clock")
    parser.add_argument("--config", type=Path, help="Path to config TOML")
    parser.add_argument("--timezone", help="IANA timezone, e.g. America/Los_Angeles")
    parser.add_argument("--format", choices=("12", "24"), dest="time_format", help="Time format")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--tick-rate", type=float, help="Loop ticks per second")

    subcommands = parser.add_subparsers(dest="command")
    subcommands.add_parser("now", help="Print current time and exit")

    timer = subcommands.add_parser("timer", help="Run a one-shot countdown timer")
    timer.add_argument("duration", help="Duration such as 5m, 1h30m, or 90s")
    timer.add_argument("--label", default="timer", help="Timer label")

    alarm = subcommands.add_parser("alarm", help="Manage persisted alarms")
    alarm_subcommands = alarm.add_subparsers(dest="alarm_command", required=True)
    add = alarm_subcommands.add_parser("add", help="Add alarm")
    add.add_argument("time", help="Time of day HH:MM or HH:MM:SS")
    add.add_argument("--label", default="", help="Alarm label")
    add.add_argument("--snooze", type=int, default=5, help="Snooze minutes")
    alarm_subcommands.add_parser("list", help="List alarms")
    remove = alarm_subcommands.add_parser("remove", help="Remove alarm")
    remove.add_argument("id", help="Alarm id")

    subcommands.add_parser("world", help="Start directly in world-clock mode")
    subcommands.add_parser("stopwatch", help="Start directly in stopwatch mode")
    subcommands.add_parser("pomodoro", help="Start directly in Pomodoro mode")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    config = _apply_flags(config, args)
    time_source = SystemTimeSource(config.timezone)

    if args.command == "now":
        state = _initial_state(config, time_source.now())
        print(MinimalRenderer().render(state))
        return 0
    if args.command == "timer":
        return run_one_shot_timer(args.duration, args.label, config, time_source)
    if args.command == "alarm":
        return _run_alarm_command(args)

    mode = {
        "world": DisplayMode.WORLD_CLOCK,
        "stopwatch": DisplayMode.STOPWATCH,
        "pomodoro": DisplayMode.POMODORO,
    }.get(args.command, DisplayMode.CLOCK)
    state = replace(_initial_state(config, time_source.now()), display_mode=mode)
    scheme = SCHEMES.get(config.color_scheme, SCHEMES["classic"])
    scheme = replace(
        scheme,
        use_color=scheme.use_color and not args.no_color and ansi.supports_ansi(),
    )
    registry = default_registry()
    renderer = BigDigitRenderer(scheme=scheme, command_help=registry.help_lines())
    repository = JSONAlarmRepository()
    state = replace(state, active_alarms=repository.list())
    loop = ClockLoop(
        state=state,
        time_source=time_source,
        display=Display(use_ansi=not args.no_color),
        renderer=renderer,
        commands=registry,
        scheduler=AlarmScheduler(repository),
        tick_rate=config.tick_rate,
    )
    return loop.run()


def _apply_flags(config: Config, args: argparse.Namespace) -> Config:
    values = {}
    if args.timezone:
        values["timezone"] = args.timezone
    if args.time_format:
        values["time_format"] = TimeFormat.parse(args.time_format)
    if args.tick_rate:
        values["tick_rate"] = args.tick_rate
    return replace(config, **values)


def _initial_state(config: Config, now: datetime) -> ClockState:
    work_duration = Duration.from_hms(minutes=config.pomodoro_work_minutes)
    break_duration = Duration.from_hms(minutes=config.pomodoro_break_minutes)
    return ClockState(
        current=now,
        timezone=config.timezone,
        time_format=config.time_format,
        show_seconds=config.show_seconds,
        show_date=config.show_date,
        world_clock_zones=config.world_clock_zones,
        pomodoro=PomodoroState(
            work_duration=work_duration,
            break_duration=break_duration,
            remaining=work_duration,
        ),
    )


def _run_alarm_command(args: argparse.Namespace) -> int:
    repository = JSONAlarmRepository()
    if args.alarm_command == "add":
        alarm = repository.add(Time.parse(args.time), label=args.label, snooze_minutes=args.snooze)
        print(f"Added {alarm.id} at {alarm.at:hm} {alarm.display_label()}")
        return 0
    if args.alarm_command == "list":
        alarms = repository.list()
        if not alarms:
            print("No alarms.")
            return 0
        for alarm in alarms:
            status = "on" if alarm.enabled else "off"
            print(f"{alarm.id}\t{alarm.at:hm}\t{status}\t{alarm.display_label()}")
        return 0
    if args.alarm_command == "remove":
        removed = repository.remove(args.id)
        print("Removed." if removed else "No matching alarm.")
        return 0 if removed else 1
    return 2
