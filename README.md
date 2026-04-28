# PyClock

PyClock is a terminal digital clock built from the architecture described in
`Digital Clock.txt`: immutable domain objects, injectable time sources, renderer
strategies, threaded input, persisted alarms, and a small standard-library CLI.

## Quick Start

```powershell
python -m pip install -e .
pyclock
```

Useful commands:

```powershell
pyclock now
pyclock --timezone America/Los_Angeles --format 12 now
pyclock timer 5m --label tea
pyclock alarm add 07:30 --label "wake up"
pyclock alarm list
pyclock world
```

## Interactive Keys

| Key | Action |
| --- | --- |
| `q` | Quit |
| `?` | Toggle help |
| `f` | Toggle 12/24-hour time |
| `s` | Toggle seconds |
| `d` | Toggle date line |
| `m` | Cycle modes |
| `1` - `6` | Jump to clock, stopwatch, timer, world clock, alarms, Pomodoro |
| `Space` | Start or stop stopwatch/Pomodoro |
| `r` | Reset stopwatch/Pomodoro |
| `l` | Record stopwatch lap |
| `t` | Add a 5-minute timer |
| `c` | Clear completed timers |

## Config

PyClock reads `~/.pyclock/config.toml` when it exists:

```toml
timezone = "America/Los_Angeles"
world_clock_zones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]
color_scheme = "classic"
tick_rate = 10
time_format = "24"
show_seconds = true
show_date = true
```

Alarms are persisted in `~/.pyclock/alarms.json`, and stopwatch reset events are
appended to `~/.pyclock/sessions.jsonl`.

## Development

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m mypy src
python scripts/smoke_e2e.py
```

## Interactive Behavior Testing

Interactive behavior is covered at three levels:

- unit tests for command/domain/renderer logic
- loop integration tests that simulate key events and assert notifications/help output
- a PTY smoke e2e script for startup/help/quit flow in a real terminal session (POSIX):

```powershell
python scripts/smoke_e2e.py
```

The smoke script uses the Python standard-library PTY module, so it runs on
POSIX terminals (Linux/macOS, or WSL/Git Bash environments on Windows).
