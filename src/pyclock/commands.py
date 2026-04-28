from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from threading import Event

from pyclock.domain import ClockState, DisplayMode, Duration, TimeFormat, TimerState
from pyclock.mode_controller import ModeController
from pyclock.sessions import StopwatchSessionLog

