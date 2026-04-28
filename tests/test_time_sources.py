"""Tests for the time sources."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pyclock.time_sources import FrozenTimeSource, SystemTimeSource


def test_frozen_time_source_advances_manually() -> None:
    source = FrozenTimeSource(datetime(2026, 4, 21, 10, 0, tzinfo=ZoneInfo("UTC")))

    source.advance(timedelta(seconds=30))

    assert source.now().minute == 0
    assert source.now().second == 30


def test_system_time_source_returns_requested_timezone() -> None:
    source = SystemTimeSource("America/Los_Angeles")

    assert source.now().tzinfo is not None
    assert source.now().tzname() in {"PST", "PDT"}
