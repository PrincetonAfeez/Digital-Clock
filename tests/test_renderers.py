"""Tests for the renderers."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pyclock.domain import ClockState, DisplayMode, TimeFormat
from pyclock.renderers import BigDigitRenderer, ColorScheme, MinimalRenderer


def test_minimal_renderer_outputs_known_time() -> None:
    state = ClockState(
        current=datetime(2026, 4, 21, 13, 4, 5, tzinfo=ZoneInfo("UTC")),
        timezone="UTC",
        time_format=TimeFormat.H24,
    )

    assert MinimalRenderer().render(state) == "13:04:05"


def test_minimal_renderer_world_clock_is_pipe_friendly() -> None:
    state = ClockState(
        current=datetime(2026, 4, 21, 13, 4, 5, tzinfo=ZoneInfo("UTC")),
        timezone="UTC",
        display_mode=DisplayMode.WORLD_CLOCK,
        world_clock_zones=("UTC", "America/New_York"),
    )

    rendered = MinimalRenderer().render(state)

    assert "UTC\t13:04:05" in rendered
    assert "America/New_York\t09:04:05" in rendered


def test_big_digit_renderer_does_not_touch_io() -> None:
    state = ClockState(
        current=datetime(2026, 4, 21, 13, 4, 5, tzinfo=ZoneInfo("UTC")),
        timezone="UTC",
        time_format=TimeFormat.H12,
    )
    renderer = BigDigitRenderer(ColorScheme("test", use_color=False))

    rendered = renderer.render(state)

    assert "PyClock | Clock | UTC" in rendered
    assert "Tuesday, April 21, 2026" in rendered
    assert "#### " in rendered
