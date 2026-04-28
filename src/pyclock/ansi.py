"""Small ANSI escape helper module."""

from __future__ import annotations

import os
import re

RESET = "\x1b[0m"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
CLEAR_SCREEN = "\x1b[2J"
HOME = "\x1b[H"
BELL = "\a"

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

COLORS = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "default": 39,
}


def supports_ansi() -> bool:
    return os.name != "nt" or "WT_SESSION" in os.environ or "ANSICON" in os.environ


def fg(name: str) -> str:
    return f"\x1b[{COLORS.get(name, COLORS['default'])}m"


def bg(name: str) -> str:
    code = COLORS.get(name, COLORS["default"])
    return f"\x1b[{code + 10 if code != 39 else 49}m"


def bold() -> str:
    return "\x1b[1m"


def dim() -> str:
    return "\x1b[2m"


def colorize(text: str, *, foreground: str = "default", background: str | None = None) -> str:
    prefix = fg(foreground)
    if background:
        prefix += bg(background)
    return f"{prefix}{text}{RESET}"


def strip(text: str) -> str:
    return _ANSI_RE.sub("", text)
