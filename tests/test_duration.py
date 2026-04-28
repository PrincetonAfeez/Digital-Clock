"""Tests for the duration."""

from __future__ import annotations

import pytest

from pyclock.domain import Duration, parse_duration
from pyclock.exceptions import InvalidDurationError


@pytest.mark.parametrize(
    ("text", "seconds", "compact"),
    [
        ("5m", 300, "5m"),
        ("1h30m", 5400, "1h30m"),
        ("90s", 90, "1m30s"),
        ("0s", 0, "0s"),
        ("01:02:03", 3723, "1h2m3s"),
    ],
)
def test_parse_duration(text: str, seconds: int, compact: str) -> None:
    duration = parse_duration(text)

    assert duration.seconds == seconds
    assert f"{duration:compact}" == compact


def test_duration_arithmetic_and_formatting() -> None:
    left = Duration.from_hms(minutes=2)
    right = Duration(30)

    assert left + right == Duration(150)
    assert left - right == Duration(90)
    assert right < left
    assert f"{left:hms}" == "00:02:00"
    assert f"{left:ms}" == "2:00"


def test_negative_duration_subtraction_is_rejected() -> None:
    with pytest.raises(InvalidDurationError):
        Duration(5) - Duration(6)


@pytest.mark.parametrize("text", ["", "abc", "1x", "10:99", "-5s"])
def test_invalid_duration_strings(text: str) -> None:
    with pytest.raises(InvalidDurationError):
        parse_duration(text)


def test_compact_format_round_trips_with_parser() -> None:
    hypothesis = pytest.importorskip("hypothesis")
    st = pytest.importorskip("hypothesis.strategies")

    @hypothesis.given(st.integers(min_value=0, max_value=7 * 24 * 3600))
    def round_trip(seconds: int) -> None:
        duration = Duration(seconds)
        assert parse_duration(f"{duration:compact}") == duration

    round_trip()
