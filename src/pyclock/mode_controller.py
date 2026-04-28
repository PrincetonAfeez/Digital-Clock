"""Explicit state machine for display modes."""

from __future__ import annotations

from dataclasses import dataclass

from pyclock.domain import DisplayMode
from pyclock.exceptions import ClockError


class InvalidModeTransitionError(ClockError):
    """Raised when a mode transition is not allowed."""


@dataclass(frozen=True)
class ModeController:
    modes: tuple[DisplayMode, ...] = tuple(DisplayMode)

    def transition(self, current: DisplayMode, target: DisplayMode) -> DisplayMode:
        if current not in self.modes or target not in self.modes:
            msg = f"cannot transition from {current.value} to {target.value}"
            raise InvalidModeTransitionError(msg)
        return target

    def next(self, current: DisplayMode) -> DisplayMode:
        if current not in self.modes:
            msg = f"unknown mode: {current.value}"
            raise InvalidModeTransitionError(msg)
        index = self.modes.index(current)
        return self.modes[(index + 1) % len(self.modes)]
