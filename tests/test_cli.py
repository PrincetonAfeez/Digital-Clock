from __future__ import annotations

from datetime import datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

from pyclock.config import Config
from pyclock.time_sources import FrozenTimeSource
from pyclock.timer_runner import run_one_shot_timer


def test_one_shot_timer_uses_injected_time_source_and_outputs_countdown() -> None:
    source = FrozenTimeSource(datetime(2026, 4, 21, 10, 0, 0, tzinfo=ZoneInfo("UTC")))
    output = StringIO()
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        source.advance(timedelta(seconds=int(seconds)))

    exit_code = run_one_shot_timer(
        "3s",
        "tea",
        Config(),
        source,
        sleep=fake_sleep,
        stream=output,
    )

    assert exit_code == 0
    assert sleeps == [1, 1, 1]
    rendered = output.getvalue()
    assert "\rtea: 00:00:03" in rendered
    assert "\rtea: 00:00:02" in rendered
    assert "\rtea: 00:00:01" in rendered
    assert "00:00:00" in rendered
