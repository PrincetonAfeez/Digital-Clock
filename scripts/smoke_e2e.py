"""Smoke e2e check for startup/help/quit via pseudo-terminal."""

from __future__ import annotations

import os
import select
import subprocess
import sys
import time


def _read_until(master_fd: int, text: str, timeout: float) -> str:
    """Read until the text is found."""
    deadline = time.monotonic() + timeout
    chunks: list[str] = []
    while time.monotonic() < deadline:
        readable, _, _ = select.select([master_fd], [], [], 0.1)
        if not readable:
            continue
        data = os.read(master_fd, 4096).decode("utf-8", errors="replace")
        chunks.append(data)
        joined = "".join(chunks)
        if text in joined:
            return joined
    msg = f"timed out waiting for {text!r}\nCaptured output:\n{''.join(chunks)}"
    raise RuntimeError(msg)


def main() -> int:
    """Main entry point."""
    if os.name == "nt":
        print("Smoke PTY script requires a POSIX environment (uses stdlib pty module).")
        return 2

    import pty

    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        [sys.executable, "-m", "pyclock", "--no-color"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    os.close(slave_fd)

    try:
        output = _read_until(master_fd, "PyClock | Clock |", timeout=5.0)
        os.write(master_fd, b"?")
        output = _read_until(master_fd, "Keys", timeout=5.0)
        if "Toggle help" not in output:
            raise RuntimeError("help overlay rendered but expected key descriptions were missing")
        os.write(master_fd, b"q")
        proc.wait(timeout=5.0)
    finally:
        os.close(master_fd)
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=3.0)

    if proc.returncode != 0:
        raise RuntimeError(f"pyclock exited with code {proc.returncode}")
    print("Smoke e2e passed: startup/help/quit flow works.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
