"""Application-specific exceptions."""


class ClockError(Exception):
    """Base exception for clock failures."""


class InvalidTimezoneError(ClockError):
    """Raised when a timezone name cannot be loaded."""


class AlarmConflictError(ClockError):
    """Raised when two active alarms target the same time of day."""


class InvalidDurationError(ClockError):
    """Raised when a duration is negative or cannot be parsed."""
