"""Append-only stopwatch session logging."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pyclock.domain import StopwatchState
from pyclock.paths import default_sessions_path


@dataclass
class StopwatchSessionLog:

    path: Path | None = None

    def append(self, state: StopwatchState, ended_at: datetime) -> None:
        """Append a session to the log."""
        target = self.path or default_sessions_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ended_at": ended_at.isoformat(),
            "elapsed_seconds": state.elapsed.seconds,
            "laps": [lap.seconds for lap in state.laps],
        }
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
