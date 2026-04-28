"""TOML configuration loading."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from pyclock.domain import TimeFormat
from pyclock.paths import default_config_path


@dataclass(frozen=True)
class Config:
    """Configuration for the clock."""

    timezone: str = "UTC"
    world_clock_zones: tuple[str, ...] = ("UTC", "America/New_York", "Europe/London", "Asia/Tokyo")
    color_scheme: str = "classic"
    tick_rate: float = 10.0
    time_format: TimeFormat = TimeFormat.H24
    show_seconds: bool = True
    show_date: bool = True
    pomodoro_work_minutes: int = 25
    pomodoro_break_minutes: int = 5


def load_config(path: Path | None = None) -> Config:
    """Load the configuration from a file."""
    config_path = path or default_config_path()
    if not config_path.exists():
        return Config()
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return Config(
        timezone=str(raw.get("timezone", "UTC")),
        world_clock_zones=tuple(raw.get("world_clock_zones", Config.world_clock_zones)),
        color_scheme=str(raw.get("color_scheme", "classic")),
        tick_rate=float(raw.get("tick_rate", 10.0)),
        time_format=TimeFormat.parse(raw.get("time_format", "24")),
        show_seconds=bool(raw.get("show_seconds", True)),
        show_date=bool(raw.get("show_date", True)),
        pomodoro_work_minutes=int(raw.get("pomodoro_work_minutes", 25)),
        pomodoro_break_minutes=int(raw.get("pomodoro_break_minutes", 5)),
    )
