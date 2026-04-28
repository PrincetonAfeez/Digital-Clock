"""Filesystem locations used by PyClock."""

from __future__ import annotations

from pathlib import Path


def app_dir() -> Path:
    path = Path.home() / ".pyclock"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_config_path() -> Path:
    return app_dir() / "config.toml"


def default_alarms_path() -> Path:
    return app_dir() / "alarms.json"


def default_sessions_path() -> Path:
    return app_dir() / "sessions.jsonl"
