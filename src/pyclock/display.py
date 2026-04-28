"""Terminal display and input helpers."""

from __future__ import annotations

import contextlib
import os
import queue
import sys
import threading
import time
from collections.abc import Iterator
from typing import TextIO

from pyclock import ansi


class Display:
    """Writes rendered strings to stdout and avoids redundant redraws."""

    def __init__(self, stream: TextIO | None = None, use_ansi: bool = True) -> None:
        self.stream = stream or sys.stdout
        self.use_ansi = use_ansi
        self._last = ""

    def start(self) -> None:
        if self.use_ansi:
            self.stream.write(ansi.HIDE_CURSOR + ansi.CLEAR_SCREEN + ansi.HOME)
            self.stream.flush()

    def stop(self) -> None:
        if self.use_ansi:
            self.stream.write(ansi.RESET + ansi.SHOW_CURSOR + "\n")
            self.stream.flush()

    def write(self, rendered: str) -> bool:
        if rendered == self._last:
            return False
        self._last = rendered
        if self.use_ansi:
            self.stream.write(ansi.HOME + ansi.CLEAR_SCREEN + ansi.HOME + rendered + ansi.RESET)
            self.stream.write("\n")
        else:
            self.stream.write(rendered + "\n")
        self.stream.flush()
        return True


@contextlib.contextmanager
def raw_terminal() -> Iterator[None]:
    """Read single keys on Unix; Windows uses msvcrt and needs no tty switch."""

    if os.name == "nt":
        yield
        return

    import termios
    import tty

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)  # type: ignore[attr-defined]
    try:
        tty.setcbreak(fd)  # type: ignore[attr-defined]
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)  # type: ignore[attr-defined]


class InputListener(threading.Thread):
    """Background key reader that pushes keys into a queue."""

    def __init__(self, events: queue.Queue[str], stop_event: threading.Event) -> None:
        super().__init__(name="pyclock-input", daemon=True)
        self.events = events
        self.stop_event = stop_event

    def run(self) -> None:
        if os.name == "nt":
            self._run_windows()
        else:
            self._run_unix()

    def _run_windows(self) -> None:
        import msvcrt

        while not self.stop_event.is_set():
            if msvcrt.kbhit():
                key = msvcrt.getwch()
                self.events.put(key)
            time.sleep(0.03)

    def _run_unix(self) -> None:
        import select

        with raw_terminal():
            while not self.stop_event.is_set():
                readable, _, _ = select.select([sys.stdin], [], [], 0.05)
                if readable:
                    self.events.put(sys.stdin.read(1))
