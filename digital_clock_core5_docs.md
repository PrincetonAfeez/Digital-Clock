# Architecture Decision Record

## App 34 — Digital Clock
**Terminal Utilities Group | Document 1 of 5**

### ADR-001: Use immutable domain state as the center of the clock application

**Status:** Accepted  
**Date:** 2026-05-09

### Context

PyClock is not only a program that prints the current time. It is a terminal application with several related modes: live clock, stopwatch, countdown timer, world clock, alarm list, and Pomodoro. Each mode needs to share the same event loop, renderer pipeline, keyboard command system, configuration defaults, and terminal display boundary. The project therefore needed a central representation of "what the application currently knows" that could be passed between the loop, command handlers, renderers, and tests without letting every module mutate unrelated fields.

The implementation uses immutable dataclasses in `domain.py`, including `Time`, `Duration`, `Alarm`, `TimerState`, `StopwatchState`, `PomodoroState`, and the aggregate `ClockState`. State updates are performed by returning new objects, usually through `dataclasses.replace`, instead of mutating state in place.

### Decision Drivers

- Keep clock, stopwatch, timer, alarm, and Pomodoro logic testable without terminal I/O.
- Make the display layer depend on a snapshot rather than live mutable objects.
- Avoid hidden mutation across keyboard commands.
- Preserve beginner-readable Python structure while still showing architectural maturity.
- Support deterministic tests by allowing states to be built directly.

### Options Considered

1. **Mutable global state dictionary**  
   This would be quick to write and easy to pass around, but it would make command behavior less explicit and increase the chance that unrelated fields change accidentally.

2. **Separate mutable classes for each feature**  
   This would create object-oriented boundaries, but the terminal loop would still need a unified view of all active features.

3. **Immutable dataclasses plus a single `ClockState` aggregate**  
   This makes every UI frame a snapshot. Each command receives a state and returns a new state. Renderers receive the same state without owning behavior.

### Decision

Use immutable dataclasses as the application’s domain model, with `ClockState` as the single state snapshot passed to renderers and updated by the loop and command registry.

### Rationale

This approach matches the app’s architectural shape. A digital clock is stateful, but most of its state changes are small and predictable: toggle the time format, add a timer, tick a stopwatch, update the current time, show or hide help, or record a notification. Immutable dataclasses make those changes visible as state transitions instead of side effects.

The design also works well with testing. Tests can construct a `ClockState` at a known datetime and render it without a live terminal. They can execute commands and assert that the returned state changed correctly while the original state remains intact.

### Trade-offs Accepted

- Updating state requires creating replacement objects, which is more verbose than mutating fields.
- Nested state updates such as stopwatch and Pomodoro changes require careful use of `replace`.
- The application is not optimized for extremely high-frequency state mutation, but a terminal clock does not need that level of performance.
- Some imperative behavior remains in the loop, display, and input modules because those modules operate at system boundaries.

### Consequences

- Renderers can remain pure: they convert `ClockState` into strings.
- Commands can be modeled as small classes that transform state.
- Tests can validate command and rendering behavior without needing a terminal.
- State snapshots provide a clear boundary between domain logic and I/O.
- Future features should be added as new fields or domain objects rather than hidden globals.

### Superseded By

Not superseded.

---

### ADR-002: Use injectable time sources instead of calling `datetime.now()` everywhere

**Status:** Accepted  
**Date:** 2026-05-09

### Context

A clock application naturally depends on the current time. If every module called `datetime.now()` directly, the app would be difficult to test, especially for alarms, timer countdowns, stopwatch ticks, world-clock conversion, and one-shot timer behavior. The project also needed timezone support and a way to simulate time advancement in tests.

The implementation defines a `TimeSource` protocol and concrete implementations: `SystemTimeSource`, `FrozenTimeSource`, and `AcceleratedTimeSource`.

### Decision Drivers

- Make time-dependent behavior deterministic in tests.
- Keep timezone loading and validation in one place.
- Avoid sleeping in tests.
- Allow future simulation/demo behavior.
- Keep the runtime implementation simple for the CLI.

### Options Considered

1. **Direct calls to `datetime.now()`**  
   This is the simplest implementation, but it tightly couples domain logic to wall-clock time.

2. **Pass raw datetimes through every function manually**  
   This improves testability but creates noisy APIs and does not solve the live app’s need to get current time each tick.

3. **Inject a `TimeSource` abstraction**  
   This keeps the loop simple while allowing tests and special modes to control time.

### Decision

Use a `TimeSource` protocol with concrete time providers. The main CLI uses `SystemTimeSource`, while tests and controlled flows can use `FrozenTimeSource` or other deterministic sources.

### Rationale

This choice is especially important for an app whose correctness depends on time crossing boundaries. Alarms must fire when the clock crosses a target time, timers must count down by elapsed seconds, and the one-shot timer must be testable without forcing real sleeps. An injectable time source isolates those behaviors from the operating system clock.

### Trade-offs Accepted

- More concepts must be explained than in a basic clock script.
- The loop has to compute deltas between previous and current time source values.
- Incorrect time source implementations could create surprising behavior, so protocol expectations must stay simple.

### Consequences

- Tests can advance time intentionally.
- Timer and alarm behavior can be verified at boundary cases such as midnight crossing.
- The CLI can still use real system time without extra user configuration.
- Future features such as demo mode, accelerated time, or replayed time traces are easier to add.

### Superseded By

Not superseded.

---

### ADR-003: Separate pure renderers from terminal display and keyboard input

**Status:** Accepted  
**Date:** 2026-05-09

### Context

PyClock needs to render a live terminal UI with ANSI control sequences, big ASCII digits, compact output, minimal command output, notifications, world clocks, timers, alarms, stopwatch laps, and Pomodoro state. At the same time, rendering should be testable and should not require an actual terminal.

The implementation separates renderer strategies from terminal display. `BigDigitRenderer`, `CompactRenderer`, and `MinimalRenderer` accept `ClockState` and return strings. `Display` owns terminal writing, clear-screen behavior, cursor hiding/showing, and redundant redraw avoidance.

### Decision Drivers

- Keep rendering deterministic.
- Support both interactive and pipe-friendly output.
- Avoid mixing string formatting with stdout writes.
- Allow tests to assert rendered output.
- Keep terminal control isolated.

### Options Considered

1. **Print directly inside render methods**  
   Simple but hard to test and impossible to reuse for different output modes.

2. **One renderer with conditionals for all output types**  
   Centralizes formatting but creates a large, brittle function.

3. **Renderer strategy classes plus separate `Display` I/O boundary**  
   Keeps output generation pure while allowing the display object to handle terminal mechanics.

### Decision

Use renderer strategy classes that return strings, and keep all stdout/ANSI behavior inside `Display` and ANSI helper functions.

### Rationale

The renderer strategy fits the app’s feature set. The same `ClockState` can be rendered as big ASCII art for the terminal, compact colored output, or minimal machine-friendly text. Tests confirm that the minimal renderer returns a known time string and that the big renderer produces expected content without touching I/O.

### Trade-offs Accepted

- The renderer module is larger because it contains several mode-specific render methods.
- ASCII digit rendering requires static font data.
- Color schemes and terminal support add some presentation complexity.

### Consequences

- Interactive display can redraw only when output changes.
- CLI `now` can use a minimal renderer and exit cleanly.
- World-clock output can be pipe-friendly.
- Rendering behavior is independently testable.

### Superseded By

Not superseded.

---

### ADR-004: Persist alarms and stopwatch sessions in user-scoped files

**Status:** Accepted  
**Date:** 2026-05-09

### Context

A useful clock app should remember alarms between runs and record stopwatch sessions when they are reset. The app does not require a database or server. It only needs small local files under a predictable user directory.

The implementation uses `~/.pyclock` as the runtime directory. Configuration is read from `config.toml`, alarms are persisted in `alarms.json`, and stopwatch reset sessions are appended to `sessions.jsonl`.

### Decision Drivers

- Keep the project standard-library only.
- Make data files inspectable by the user.
- Avoid database setup for a learner CLI project.
- Support persistent alarms without complicated infrastructure.
- Keep session logging append-only and low-risk.

### Options Considered

1. **No persistence**  
   Simpler, but alarms would disappear on exit and the app would feel less complete.

2. **SQLite database**  
   Reliable and structured, but too heavy for the app’s scope and not necessary for small alarm/session data.

3. **JSON/TOML/JSONL files under `~/.pyclock`**  
   Simple, readable, and consistent with the size of the application.

### Decision

Use user-scoped files under `~/.pyclock`: TOML for config, JSON for alarm records, and JSONL for append-only stopwatch sessions.

### Rationale

The file formats align with their use cases. TOML is suitable for human-editable config. JSON is suitable for replacing the full alarm list. JSONL is suitable for appending session records without rewriting the whole log.

### Trade-offs Accepted

- No cross-process locking is implemented.
- JSON alarm writes replace the whole alarm list.
- Badly edited files may raise parsing errors rather than being repaired automatically.
- Session log querying is not yet exposed as a CLI command.

### Consequences

- Alarms survive across application runs.
- Stopwatch resets can create audit-style records.
- The persistence layer remains easy to inspect and test.
- Future maintenance should consider safer writes, backup behavior, and validation for corrupted files.

### Superseded By

Not superseded.

---

### ADR-005: Keep the CLI standard-library only

**Status:** Accepted  
**Date:** 2026-05-09

### Context

The app provides a terminal interface, command-line subcommands, timezone support, configuration loading, keyboard input, ANSI output, persistence, and tests. The implementation could have used third-party libraries for rich terminal rendering, CLI parsing, or scheduling, but the project intentionally keeps runtime dependencies empty.

### Decision Drivers

- Demonstrate Python standard-library competence.
- Keep installation simple.
- Avoid hiding core architecture behind frameworks.
- Preserve project scope for an academic CLI app.
- Make the app portable and easy to review.

### Options Considered

1. **Use rich/textual/click**  
   These would improve UI ergonomics and reduce manual terminal code, but they would obscure the learning value of renderer, input, and CLI boundaries.

2. **Use only the standard library**  
   Requires more custom code but better demonstrates architecture and fundamentals.

### Decision

Implement CLI parsing, rendering, terminal handling, persistence, timezone handling, and threading with the Python standard library.

### Rationale

For an academic CLI portfolio project, the standard-library constraint is a strength. It forces the design to expose real boundaries: `argparse` for CLI, `zoneinfo` for timezones, `threading` and `queue` for input events, `json` and `tomllib` for persistence/config, and dataclasses for state.

### Trade-offs Accepted

- Terminal rendering is less polished than a framework-based TUI.
- Windows and POSIX input handling require separate code paths.
- Some behavior, such as full-screen rendering and PTY testing, is more manual.

### Consequences

- The project remains lightweight and easy to install.
- Architecture is visible and reviewable.
- Future versions could introduce optional UI dependencies only if the standard-library version remains the stable core.

### Superseded By

Not superseded.

---

# Technical Design Document

## App 34 — Digital Clock
**Terminal Utilities Group | Document 2 of 5**

## Purpose & Scope

PyClock is a terminal digital clock package. It displays the current time, supports 12-hour and 24-hour formats, optionally shows seconds and date, supports world-clock views, manages persisted alarms, runs a stopwatch, manages countdown timers, and includes a Pomodoro mode. It can be used interactively through the full-screen terminal UI or through smaller CLI commands such as `pyclock now`, `pyclock timer`, and `pyclock alarm`.

The project scope includes:

- immutable domain objects for time, duration, alarms, timers, stopwatch, Pomodoro, and full application state
- injectable time sources
- terminal renderers
- ANSI display management
- threaded keyboard input
- command pattern for keybindings
- persisted alarms
- append-only stopwatch session log
- CLI subcommands for current time, timer, alarm management, world clock, stopwatch, and Pomodoro startup modes

The project intentionally does not include:

- GUI widgets
- network time synchronization
- recurring calendar rules beyond daily time-of-day alarms
- sound files beyond terminal bell notifications
- database-backed persistence
- multi-process synchronization for config/alarm files

## System Context

PyClock runs as a local Python command-line application. It interacts with:

- the operating system terminal for output and keyboard input
- the user’s home directory for config, alarms, and sessions
- Python’s timezone database through `zoneinfo`
- Python’s current system clock through `datetime.now()` inside `SystemTimeSource`
- standard streams for one-shot timer and minimal output modes

The package exposes `pyclock` as a console script and supports `python -m pyclock` through `__main__.py`.

## Component Breakdown

### `pyclock.domain`

Defines the core immutable model:

- `DisplayMode`: enum for `clock`, `stopwatch`, `timer`, `world`, `alarms`, and `pomodoro`
- `TimeFormat`: enum for 12-hour vs 24-hour display
- `Time`: validated time-of-day value
- `Duration`: non-negative duration in whole seconds
- `parse_duration`: parser for compact and colon duration input
- `Alarm`: persisted alarm definition
- `TimerState`: countdown timer state
- `StopwatchState`: stopwatch elapsed time and laps
- `PomodoroState`: work/break session state
- `ClockState`: aggregate state snapshot used by commands, loop, and renderers

### `pyclock.time_sources`

Defines the time boundary:

- `TimeSource`: protocol requiring `now() -> datetime`
- `SystemTimeSource`: real current time in an IANA timezone
- `FrozenTimeSource`: deterministic test source that advances manually
- `AcceleratedTimeSource`: simulated time that moves faster than real time
- `load_zone`: validates timezone names and raises app-specific errors

### `pyclock.renderers`

Defines renderer strategies:

- `Renderer`: abstract base class
- `BigDigitRenderer`: full terminal UI with ASCII digits, mode sections, help text, notifications, timers, world clocks, alarms, and Pomodoro
- `CompactRenderer`: compact single-line style
- `MinimalRenderer`: pipe-friendly output
- `ColorScheme`: terminal color configuration
- `format_datetime`: shared datetime formatting helper

Renderers do not print. They return strings.

### `pyclock.display`

Owns terminal I/O:

- `Display`: writes rendered strings to stdout, avoids redundant redraws, hides/restores cursor, and clears screen when ANSI is enabled
- `raw_terminal`: POSIX raw/cbreak terminal mode context manager
- `InputListener`: background daemon thread that reads keyboard input and pushes keys into a queue

### `pyclock.commands`

Defines the keybinding command pattern:

- `Command`: abstract base class
- `CommandRegistry`: maps keys to command objects
- `CommandContext`: carries stop event, session log, and mode controller
- `QuitCommand`
- `ToggleHelpCommand`
- `ToggleFormatCommand`
- `ToggleSecondsCommand`
- `ToggleDateCommand`
- `NextModeCommand`
- `SetModeCommand`
- `StopwatchToggleCommand`
- `StopwatchResetCommand`
- `StopwatchLapCommand`
- `AddFiveMinuteTimerCommand`
- `ClearDoneTimersCommand`

Each command receives a `ClockState` and returns the next `ClockState`.

### `pyclock.mode_controller`

Defines explicit display-mode transitions:

- `ModeController.next`
- `ModeController.transition`
- `InvalidModeTransitionError`

The current implementation allows transitions among the known display modes, while still centralizing transition validation.

### `pyclock.loop`

Runs the interactive application loop:

- owns the current `ClockState`
- reads current time from `TimeSource`
- computes whole-second deltas
- ticks stopwatch, timers, and Pomodoro
- checks alarms through `AlarmScheduler`
- drains keyboard events from the input queue
- renders via `Renderer`
- writes via `Display`
- installs/restores SIGINT handling
- starts/stops input listener thread

### `pyclock.alarms`

Defines alarm persistence and scheduling:

- `AlarmRepository`: abstract repository interface
- `JSONAlarmRepository`: file-backed alarm repository
- `InMemoryAlarmRepository`: test repository
- `AlarmScheduler`: detects when alarms become due, prevents same-day repeat firing, and supports snooze

### `pyclock.config`

Defines config loading:

- `Config`: immutable configuration dataclass
- `load_config`: reads TOML from either explicit path or default `~/.pyclock/config.toml`

### `pyclock.paths`

Defines runtime file locations:

- `app_dir`
- `default_config_path`
- `default_alarms_path`
- `default_sessions_path`

### `pyclock.sessions`

Defines append-only stopwatch logging:

- `StopwatchSessionLog.append`
- writes JSONL records with `ended_at`, elapsed seconds, and laps

### `pyclock.timer_runner`

Provides one-shot countdown timer behavior for `pyclock timer`.

### `pyclock.ansi`

Defines ANSI constants and helpers for color, cursor visibility, clearing, terminal bell, ANSI stripping, and platform support detection.

### `pyclock.cli`

Builds the command-line interface and composes the runtime:

- parses flags and subcommands with `argparse`
- loads config
- applies CLI overrides
- creates `SystemTimeSource`
- dispatches to `now`, `timer`, `alarm`, or interactive mode
- initializes renderer, display, commands, alarm repository, scheduler, and loop

### `pyclock.exceptions`

Defines app-specific errors:

- `ClockError`
- `InvalidTimezoneError`
- `AlarmConflictError`
- `InvalidDurationError`

## Module Dependency Graph

```text
pyclock.__main__
    -> pyclock.cli

pyclock.cli
    -> pyclock.ansi
    -> pyclock.alarms
    -> pyclock.commands
    -> pyclock.config
    -> pyclock.display
    -> pyclock.domain
    -> pyclock.loop
    -> pyclock.renderers
    -> pyclock.time_sources
    -> pyclock.timer_runner

pyclock.loop
    -> pyclock.ansi
    -> pyclock.alarms
    -> pyclock.commands
    -> pyclock.display
    -> pyclock.domain
    -> pyclock.renderers
    -> pyclock.sessions
    -> pyclock.time_sources

pyclock.commands
    -> pyclock.domain
    -> pyclock.mode_controller
    -> pyclock.sessions

pyclock.renderers
    -> pyclock.ansi
    -> pyclock.domain
    -> zoneinfo

pyclock.alarms
    -> pyclock.domain
    -> pyclock.exceptions
    -> pyclock.paths

pyclock.config
    -> pyclock.domain
    -> pyclock.paths

pyclock.time_sources
    -> pyclock.exceptions
    -> zoneinfo

pyclock.timer_runner
    -> pyclock.ansi
    -> pyclock.config
    -> pyclock.domain
    -> pyclock.time_sources

pyclock.sessions
    -> pyclock.domain
    -> pyclock.paths
```

The dependency direction is generally inward toward domain objects and outward toward I/O modules. `domain.py` does not depend on terminal or persistence code. This keeps the core model reusable.

## Core Algorithms & Logic

### Main interactive loop

1. Load config and CLI flags.
2. Create `SystemTimeSource` for the selected timezone.
3. Build initial `ClockState`.
4. Load persisted alarms into state.
5. Create command registry, renderer, display, alarm scheduler, and `ClockLoop`.
6. Start input listener thread.
7. Start display and install SIGINT handler.
8. On each loop:
   - read current datetime from the time source
   - compute elapsed whole seconds since the previous tick
   - convert elapsed seconds into `Duration`
   - update current time
   - tick stopwatch if running
   - tick each countdown timer
   - tick Pomodoro if running
   - add notifications for newly completed timers
   - check alarm scheduler for due alarms
   - drain queued key events and execute commands
   - render current state
   - sleep until the next tick
9. On exit:
   - set stop event
   - join input listener
   - restore display
   - restore SIGINT handler

### Duration parsing

`parse_duration` accepts:

- colon format: `MM:SS` or `HH:MM:SS`
- numeric seconds: `90`
- compact format: `1h30m`, `5m`, `90s`

Colon formats require minutes and seconds to be in valid ranges. Compact format uses a regular expression with optional hours, minutes, and seconds. Empty or invalid values raise `InvalidDurationError`.

### Stopwatch ticking

`StopwatchState.tick(delta)` returns the same object when stopped. When running, it returns a replacement with elapsed duration increased by `delta`.

### Timer ticking

`TimerState.tick(delta)` returns the same object when not running or already completed. Otherwise it clamps remaining time downward and marks the timer completed when remaining reaches zero.

### Pomodoro ticking

`PomodoroState.tick(delta)` only advances when running. If remaining time does not reach zero, it simply reduces remaining. If it reaches zero during work, it switches to break duration. If it reaches zero during break, it switches back to work duration and increments completed sessions.

### Alarm due detection

`AlarmScheduler.due(previous, current)` checks all enabled alarms. For each alarm, it determines whether the previous-to-current time interval crossed the alarm’s target time on any date in that interval. If so, it returns the alarm and updates `last_triggered_date` so the same alarm does not repeatedly fire on the same day.

This design handles midnight crossing by iterating dates between the previous and current timestamps.

### Command execution

`CommandRegistry.execute(key, state, context)` looks up the command by key. Unknown keys leave state unchanged. Known commands return a modified copy of the state or set a stop event for quit behavior.

Examples:

- `f` toggles `TimeFormat.H12` / `TimeFormat.H24`
- `s` toggles seconds
- `d` toggles date line
- `m` cycles display mode through `ModeController`
- `Space` toggles stopwatch or Pomodoro depending on mode
- `r` resets stopwatch/Pomodoro and logs stopwatch session when applicable
- `t` adds a 5-minute timer
- `c` removes completed timers

### One-shot timer

`run_one_shot_timer` parses a duration, builds a timer state, prints countdown updates with carriage returns, sleeps one second per tick, subtracts duration by one second, and prints a terminal bell at completion. It returns `130` on `KeyboardInterrupt`.

## Data Structures

### `ClockState`

```python
ClockState(
    current: datetime,
    timezone: str,
    display_mode: DisplayMode,
    time_format: TimeFormat,
    show_seconds: bool,
    show_date: bool,
    active_alarms: tuple[Alarm, ...],
    timers: tuple[TimerState, ...],
    stopwatch: StopwatchState,
    world_clock_zones: tuple[str, ...],
    pomodoro: PomodoroState,
    help_visible: bool,
    notifications: tuple[str, ...],
)
```

Purpose: single source of truth for rendering and interactive behavior.

### `Duration`

```python
Duration(seconds: int)
```

Purpose: validated non-negative duration with arithmetic, formatting, and clamp subtraction.

### `Time`

```python
Time(hours: int, minutes: int, seconds: int = 0)
```

Purpose: validated time-of-day used by alarms.

### `Alarm`

```python
Alarm(
    id: str,
    at: Time,
    label: str,
    enabled: bool,
    snooze_minutes: int,
    last_triggered_date: str | None,
)
```

Purpose: persisted daily alarm definition.

### `TimerState`

```python
TimerState(
    id: str,
    duration: Duration,
    remaining: Duration,
    label: str,
    running: bool,
    completed: bool,
)
```

Purpose: active countdown timer state.

### `StopwatchState`

```python
StopwatchState(
    elapsed: Duration,
    running: bool,
    laps: tuple[Duration, ...],
)
```

Purpose: stopwatch elapsed time and lap records.

### `PomodoroState`

```python
PomodoroState(
    work_duration: Duration,
    break_duration: Duration,
    remaining: Duration,
    in_break: bool,
    running: bool,
    sessions_completed: int,
)
```

Purpose: Pomodoro work/break cycle state.

### `Config`

```python
Config(
    timezone: str,
    world_clock_zones: tuple[str, ...],
    color_scheme: str,
    tick_rate: float,
    time_format: TimeFormat,
    show_seconds: bool,
    show_date: bool,
    pomodoro_work_minutes: int,
    pomodoro_break_minutes: int,
)
```

Purpose: runtime defaults loaded from TOML and modified by CLI flags.

## State Management

State is managed in three categories:

1. **In-memory immutable state**
   - `ClockState`
   - `TimerState`
   - `StopwatchState`
   - `PomodoroState`
   - `Alarm`

2. **Runtime mutable infrastructure**
   - `ClockLoop.state`
   - `threading.Event` stop flag
   - input queue
   - display’s last-rendered string cache
   - time source internal current time for test sources

3. **Persistent files**
   - `~/.pyclock/config.toml`
   - `~/.pyclock/alarms.json`
   - `~/.pyclock/sessions.jsonl`

The app intentionally keeps feature state immutable but allows infrastructure objects to be mutable where mutation models real I/O.

## Error Handling Strategy

Expected application errors use custom exception classes:

- invalid timezones raise `InvalidTimezoneError`
- duplicate enabled alarm time raises `AlarmConflictError`
- invalid durations raise `InvalidDurationError`
- invalid mode transitions raise `InvalidModeTransitionError`

The CLI currently handles normal command flows but does not wrap every possible runtime error in polished user-facing messages. Duration and alarm command errors may surface through the CLI path depending on the subcommand. The interactive loop focuses on graceful terminal cleanup through `finally` blocks.

Terminal and signal cleanup is handled by:

- restoring cursor display
- restoring signal handlers
- setting stop event
- joining the input thread with a timeout

## External Dependencies

Runtime dependencies: none.

Development dependencies:

- `pytest`
- `hypothesis`
- `mypy`
- `ruff`

Standard-library modules used include:

- `argparse`
- `dataclasses`
- `datetime`
- `enum`
- `json`
- `pathlib`
- `queue`
- `signal`
- `threading`
- `time`
- `tomllib`
- `zoneinfo`

## Concurrency Model

The app uses a simple threaded input model:

- main thread runs the clock loop
- background daemon thread reads keyboard input
- `queue.Queue[str]` transfers key events to the main loop
- `threading.Event` signals shutdown

Only the main loop mutates `ClockLoop.state`. The input thread does not directly mutate state; it only enqueues key strings. This reduces race risk.

The one-shot timer command is synchronous and does not use the input thread.

## Known Limitations

- No config save command is implemented.
- Alarm persistence writes the full JSON file without file locking.
- Alarm CLI supports add/list/remove but not enable/disable editing.
- Stopwatch session log is append-only, but no CLI command lists sessions.
- One-shot timer uses a simple one-second sleep loop rather than the full renderer loop.
- `Duration` stores whole seconds, so sub-second timing is intentionally omitted.
- Terminal rendering is basic compared with framework-based TUIs.
- Input handling uses separate POSIX and Windows branches and may vary by terminal.
- Error messages for some CLI failures could be more consistently caught and formatted.

## Design Patterns Used

### Immutable Snapshot Pattern

`ClockState` represents the entire renderable application state. Commands return modified copies.

### Strategy Pattern

Renderers implement a shared renderer abstraction:

- `BigDigitRenderer`
- `CompactRenderer`
- `MinimalRenderer`

Time providers also follow a strategy-like protocol:

- `SystemTimeSource`
- `FrozenTimeSource`
- `AcceleratedTimeSource`

### Command Pattern

Each keybinding is represented as a command object with an `execute` method.

### Repository Pattern

Alarm persistence is hidden behind `AlarmRepository`, with JSON and in-memory implementations.

### State Machine Pattern

Display modes are enumerated and managed through `ModeController`. Timers, stopwatch, and Pomodoro also encode their own state transitions through methods such as `tick`, `toggle`, and `reset`.

### Boundary / Adapter Pattern

`Display`, `InputListener`, `SystemTimeSource`, `JSONAlarmRepository`, and `StopwatchSessionLog` adapt external systems to the domain model.

## Constitution Alignment

This project demonstrates Python fundamentals and architectural thinking appropriate for a medium terminal utility. It shows separation of concerns, immutable modeling, I/O boundaries, state transitions, injected time, persistence, and tests. The biggest complexity risk is that PyClock combines multiple related tools in one terminal application; however, the code uses modules and abstractions to keep that complexity understandable.

---

# Interface Design Specification

## App 34 — Digital Clock
**Terminal Utilities Group | Document 3 of 5**

## Invocation Syntax

Canonical installed command:

```powershell
pyclock [GLOBAL OPTIONS] [COMMAND] [COMMAND OPTIONS]
```

Module invocation:

```powershell
python -m pyclock [GLOBAL OPTIONS] [COMMAND] [COMMAND OPTIONS]
```

Editable install:

```powershell
python -m pip install -e .
```

## Global Argument Reference Table

| Name | Type | Required | Default | Valid Values | Description |
|---|---:|---:|---|---|---|
| `--config` | path | no | `~/.pyclock/config.toml` | readable TOML path | Load configuration from a custom path. |
| `--timezone` | str | no | config value or `UTC` | IANA timezone name | Sets the primary clock timezone. |
| `--format` | choice | no | config value or `24` | `12`, `24` | Selects 12-hour or 24-hour display. |
| `--no-color` | bool flag | no | false | present/absent | Disables ANSI color output. |
| `--tick-rate` | float | no | config value or `10.0` | positive float expected | Sets loop ticks per second. |
| `--help` | bool flag | no | false | present/absent | Prints command help. |

## Command Reference

### Default interactive clock

```powershell
pyclock
```

Starts the interactive terminal UI in clock mode.

### `now`

```powershell
pyclock now
pyclock --timezone America/Los_Angeles --format 12 now
```

Prints the current time using the minimal renderer and exits.

### `timer`

```powershell
pyclock timer <duration> [--label LABEL]
```

Runs a synchronous one-shot countdown timer.

| Name | Type | Required | Default | Valid Values | Description |
|---|---:|---:|---|---|---|
| `duration` | duration string | yes | none | `5m`, `1h30m`, `90s`, `05:00`, `01:30:00`, digits as seconds | Countdown duration. |
| `--label` | str | no | `timer` | any string | Label printed with timer output. |

### `alarm add`

```powershell
pyclock alarm add <time> [--label LABEL] [--snooze MINUTES]
```

Adds a persisted alarm.

| Name | Type | Required | Default | Valid Values | Description |
|---|---:|---:|---|---|---|
| `time` | time string | yes | none | `HH:MM`, `HH:MM:SS` | Alarm time of day. |
| `--label` | str | no | empty string | any string | Human-readable alarm label. |
| `--snooze` | int | no | `5` | integer minutes | Snooze interval stored on alarm. |

### `alarm list`

```powershell
pyclock alarm list
```

Lists persisted alarms.

### `alarm remove`

```powershell
pyclock alarm remove <id>
```

Removes a persisted alarm by ID.

### `world`

```powershell
pyclock world
```

Starts the interactive UI directly in world-clock mode.

### `stopwatch`

```powershell
pyclock stopwatch
```

Starts the interactive UI directly in stopwatch mode.

### `pomodoro`

```powershell
pyclock pomodoro
```

Starts the interactive UI directly in Pomodoro mode.

## Interactive Key Reference

| Key | Description |
|---|---|
| `q` | Quit the application. |
| `?` | Toggle help overlay. |
| `f` | Toggle 12-hour / 24-hour display. |
| `s` | Toggle seconds. |
| `d` | Toggle date line. |
| `m` | Cycle to the next display mode. |
| `1` | Clock mode. |
| `2` | Stopwatch mode. |
| `3` | Timer mode. |
| `4` | World clock mode. |
| `5` | Alarm list mode. |
| `6` | Pomodoro mode. |
| `Space` | Start/stop stopwatch or Pomodoro. |
| `r` | Reset stopwatch or Pomodoro. |
| `l` | Record stopwatch lap. |
| `t` | Add a 5-minute timer. |
| `c` | Clear completed timers. |

## Input Contract

### Time values

Alarm times must be:

```text
HH:MM
HH:MM:SS
```

Rules:

- hours must be `0..23`
- minutes must be `0..59`
- seconds must be `0..59`

### Duration values

Timer durations may be:

```text
5m
1h30m
90s
01:30:00
05:00
90
```

Rules:

- compact format can include hours, minutes, and seconds
- colon format must be `MM:SS` or `HH:MM:SS`
- numeric-only input is interpreted as seconds
- negative durations are rejected
- invalid colon minute/second ranges are rejected

### Timezone values

Timezone values must be valid IANA timezone names supported by Python’s `zoneinfo`, such as:

```text
UTC
America/Los_Angeles
America/New_York
Europe/London
Asia/Tokyo
```

### Config file

Default config path:

```text
~/.pyclock/config.toml
```

Supported keys:

```toml
timezone = "America/Los_Angeles"
world_clock_zones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]
color_scheme = "classic"
tick_rate = 10
time_format = "24"
show_seconds = true
show_date = true
pomodoro_work_minutes = 25
pomodoro_break_minutes = 5
```

CLI flags override loaded config values for timezone, format, and tick rate.

## Output Contract

### `pyclock now`

Prints a single minimal time string, for example:

```text
13:04:05
```

With `--format 12`, output includes AM/PM when seconds are shown:

```text
01:04:05 PM
```

### `pyclock timer`

Writes in-place countdown output with carriage returns:

```text
tea: 00:00:03
tea: 00:00:02
tea: 00:00:01
tea: 00:00:00
```

Actual output uses `\r` to update the same line and includes a terminal bell at completion.

### `pyclock alarm add`

Prints confirmation:

```text
Added <id> at 07:30 wake up
```

### `pyclock alarm list`

When no alarms exist:

```text
No alarms.
```

With alarms:

```text
<id>    <HH:MM>    <on|off>    <label>
```

### Interactive mode

Interactive mode renders full-screen terminal output containing:

- title line
- mode-specific body
- optional date
- optional notifications
- help prompt or keybinding help

Big digit clock output is not designed as a stable machine-readable API.

### Minimal world-clock rendering

Minimal renderer uses tab-separated lines:

```text
UTC	13:04:05
America/New_York	09:04:05
```

## Exit Code Reference

| Exit Code | Meaning |
|---:|---|
| `0` | Successful command or normal interactive exit. |
| `1` | `alarm remove` did not find a matching alarm. |
| `2` | Reserved/general parser or unsupported command failure path. |
| `130` | One-shot timer cancelled by keyboard interrupt. |

## Error Output Behavior

`argparse` errors are printed by Python’s argument parser to stderr and exit through parser behavior. Domain exceptions may surface depending on command path. The implementation defines app-specific exceptions for invalid timezone, alarm conflict, invalid duration, and invalid mode transition.

Recommended future interface improvement: catch all `ClockError` instances in `cli.main` and print a consistent `pyclock: error: ...` message to stderr.

## Environment Variables

No app-specific environment variables are read.

The terminal and operating system environment affect:

- ANSI support detection
- POSIX vs Windows keyboard input branch
- availability of timezone data through Python/OS

## Configuration Files

### `~/.pyclock/config.toml`

Human-editable settings.

Lookup order:

1. explicit `--config PATH`
2. default `~/.pyclock/config.toml`
3. hardcoded `Config()` defaults

### `~/.pyclock/alarms.json`

JSON array of alarm objects. Written by `JSONAlarmRepository`.

### `~/.pyclock/sessions.jsonl`

Append-only stopwatch session log written when stopwatch reset occurs after elapsed time exists.

## Side Effects

| Command / Mode | Side Effect |
|---|---|
| `pyclock` interactive | Reads terminal keys, writes full-screen terminal output, may ring terminal bell. |
| `pyclock now` | Writes current time to stdout only. |
| `pyclock timer` | Writes countdown to stdout, sleeps between ticks, rings terminal bell at completion. |
| `pyclock alarm add` | Creates/updates `~/.pyclock/alarms.json`. |
| `pyclock alarm remove` | Updates `~/.pyclock/alarms.json`. |
| Stopwatch reset | Appends to `~/.pyclock/sessions.jsonl` when elapsed time exists. |
| Alarm due in interactive loop | Updates alarm `last_triggered_date` in persisted alarms file. |

## Usage Examples

### Basic current time

```powershell
pyclock now
```

### 12-hour time in Los Angeles

```powershell
pyclock --timezone America/Los_Angeles --format 12 now
```

### Start full-screen interactive clock

```powershell
pyclock
```

### Start directly in world-clock mode

```powershell
pyclock world
```

### One-shot timer

```powershell
pyclock timer 5m --label tea
```

### Add an alarm

```powershell
pyclock alarm add 07:30 --label "wake up"
```

### List alarms

```powershell
pyclock alarm list
```

### Remove alarm

```powershell
pyclock alarm remove abc12345
```

### Intentional failure: invalid duration

```powershell
pyclock timer 1:99
```

Expected: duration validation fails because colon-format seconds must be in range.

### Intentional failure: duplicate active alarm time

```powershell
pyclock alarm add 07:30 --label first
pyclock alarm add 07:30 --label second
```

Expected: duplicate enabled alarm time is rejected by the alarm repository.

---

# Runbook

## App 34 — Digital Clock
**Terminal Utilities Group | Document 4 of 5**

## Prerequisites

- Python 3.11 or newer
- Terminal capable of running Python CLI commands
- `zoneinfo` timezone data available through the Python installation / operating system
- POSIX terminal for PTY smoke script
- No runtime third-party dependencies

For development:

- `pytest`
- `hypothesis`
- `ruff`
- `mypy`

## Installation Procedure

From a clean checkout:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

For development tools:

```powershell
python -m pip install -e ".[dev]"
```

Verify console script:

```powershell
pyclock --help
```

Verify module entrypoint:

```powershell
python -m pyclock --help
```

## Configuration Steps

Create the config directory if needed:

```powershell
mkdir ~/.pyclock
```

Create or edit:

```text
~/.pyclock/config.toml
```

Example:

```toml
timezone = "America/Los_Angeles"
world_clock_zones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]
color_scheme = "classic"
tick_rate = 10
time_format = "24"
show_seconds = true
show_date = true
pomodoro_work_minutes = 25
pomodoro_break_minutes = 5
```

If the config file is missing, PyClock uses built-in defaults.

## Standard Operating Procedures

### Show the current time and exit

```powershell
pyclock now
```

### Show current time in a specific timezone

```powershell
pyclock --timezone America/Los_Angeles now
```

### Use 12-hour display

```powershell
pyclock --format 12 now
```

### Start the interactive clock

```powershell
pyclock
```

Then use:

```text
?  show help
f  toggle 12/24-hour
s  toggle seconds
d  toggle date
q  quit
```

### Start in stopwatch mode

```powershell
pyclock stopwatch
```

Useful keys:

```text
Space  start/stop
l      lap
r      reset
q      quit
```

### Start in world-clock mode

```powershell
pyclock world
```

### Start in Pomodoro mode

```powershell
pyclock pomodoro
```

Useful keys:

```text
Space  start/stop Pomodoro
r      reset
q      quit
```

### Run a one-shot countdown timer

```powershell
pyclock timer 5m --label tea
```

### Add an alarm

```powershell
pyclock alarm add 07:30 --label "wake up"
```

### List alarms

```powershell
pyclock alarm list
```

### Remove an alarm

```powershell
pyclock alarm remove <alarm-id>
```

## Health Checks

### Import check

```powershell
python -c "import pyclock; print(pyclock.TimeFormat.H24)"
```

Expected:

```text
24-hour
```

### Current time check

```powershell
pyclock now
```

Expected: a single time string.

### Timezone check

```powershell
pyclock --timezone America/Los_Angeles now
```

Expected: a time string without timezone loading error.

### Renderer test from CLI

```powershell
pyclock world
```

Expected: interactive UI starts in world-clock mode.

### Alarm persistence check

```powershell
pyclock alarm add 07:30 --label test
pyclock alarm list
```

Expected: the new alarm appears.

### Test suite

```powershell
python -m pytest
```

### Lint/type checks

```powershell
python -m ruff check .
python -m mypy src
```

### PTY smoke test

```powershell
python scripts/smoke_e2e.py
```

Expected on POSIX: startup/help/quit flow works in a real terminal session.

## Expected Output Samples

### `pyclock now`

```text
13:04:05
```

### `pyclock alarm list`

```text
abc12345	07:30	on	wake up
```

### `pyclock timer 3s --label tea`

```text
tea: 00:00:03
tea: 00:00:02
tea: 00:00:01
tea: 00:00:00
```

Actual timer output uses carriage returns to rewrite the same line.

## Known Failure Modes

| Symptom | Probable Cause | Diagnostic Step | Resolution |
|---|---|---|---|
| `unknown timezone` | Invalid IANA timezone | Try `UTC` | Correct `--timezone` or config timezone. |
| Duplicate alarm rejected | Enabled alarm already exists for same time | Run `pyclock alarm list` | Remove or change one alarm. |
| Timer duration rejected | Bad duration string | Try `5m` or `00:05:00` | Use supported duration format. |
| Interactive screen looks garbled | Terminal does not support ANSI well | Run with `--no-color` | Use compatible terminal or disable color. |
| Keyboard input ignored | Non-interactive shell or terminal issue | Try normal terminal instead of pipe | Run interactively in TTY. |
| World-clock zone wrong/fallback | Invalid zone in config | Inspect `world_clock_zones` | Replace invalid zone names. |
| Alarm does not fire | Alarm disabled, time not crossed, or wrong timezone | Check config timezone and alarm list | Correct timezone or alarm time. |
| Config changes ignored | Wrong config path | Use `--config PATH` | Put config at `~/.pyclock/config.toml`. |
| PTY smoke test fails on Windows | Script uses POSIX PTY | Run in Linux/macOS/WSL | Use POSIX-compatible environment. |

## Troubleshooting Decision Tree

### App will not start

1. Run:
   ```powershell
   python --version
   ```
2. Confirm Python is 3.11+.
3. Run:
   ```powershell
   python -m pyclock --help
   ```
4. If module invocation works but `pyclock` does not, reinstall editable package:
   ```powershell
   python -m pip install -e .
   ```

### Timezone error appears

1. Try:
   ```powershell
   pyclock --timezone UTC now
   ```
2. If UTC works, the configured timezone is invalid.
3. Edit `~/.pyclock/config.toml`.
4. Use a valid IANA name such as `America/Los_Angeles`.

### Alarm was not saved

1. Check the runtime directory:
   ```powershell
   ls ~/.pyclock
   ```
2. Confirm `alarms.json` exists after `alarm add`.
3. Run:
   ```powershell
   pyclock alarm list
   ```
4. If no alarm appears, check for write permissions in the home directory.

### Interactive UI does not restore cursor

1. Quit with `q` if possible.
2. If interrupted, reset terminal manually:
   ```powershell
   reset
   ```
3. Re-run with:
   ```powershell
   pyclock --no-color
   ```

### Stopwatch sessions not logged

1. Use stopwatch mode.
2. Start stopwatch with Space.
3. Let elapsed time increase.
4. Press `r` to reset.
5. Check:
   ```text
   ~/.pyclock/sessions.jsonl
   ```

The log is written on reset only when elapsed time is nonzero.

## Dependency Failure Handling

### Missing timezone data

Some minimal Python/OS installations may lack full timezone data.

Resolution:

- use `UTC`, or
- install the OS timezone database, or
- use an environment where `zoneinfo` has IANA data.

### Terminal limitations

If ANSI or raw key input does not work:

```powershell
pyclock --no-color
```

For non-interactive usage:

```powershell
pyclock now
```

## Recovery Procedures

### Corrupted alarm file

1. Move existing file:
   ```powershell
   mv ~/.pyclock/alarms.json ~/.pyclock/alarms.bad.json
   ```
2. Recreate alarms:
   ```powershell
   pyclock alarm add 07:30 --label "wake up"
   ```

### Bad config file

1. Move config aside:
   ```powershell
   mv ~/.pyclock/config.toml ~/.pyclock/config.bad.toml
   ```
2. Run:
   ```powershell
   pyclock now
   ```
3. Recreate config with known-good keys.

### Terminal cursor hidden

Run:

```powershell
reset
```

Or close and reopen the terminal.

### Stale stopwatch sessions

The sessions file is append-only. Archive it manually:

```powershell
mv ~/.pyclock/sessions.jsonl ~/.pyclock/sessions.archive.jsonl
```

A new file will be created on the next logged stopwatch reset.

## Logging Reference

PyClock does not implement structured application logging. It does persist:

- alarms in `~/.pyclock/alarms.json`
- stopwatch reset sessions in `~/.pyclock/sessions.jsonl`

Stopwatch session JSONL fields:

```json
{"ended_at": "...", "elapsed_seconds": 123, "laps": [60, 90]}
```

## Maintenance Notes

- Keep `ClockState` immutable and avoid introducing global mutable state.
- Add new modes through `DisplayMode`, renderer methods, and command mappings.
- Keep renderers pure; do not print inside renderer methods.
- Keep new time-sensitive tests based on injected time sources.
- Add CLI-level error handling for all `ClockError` subclasses if polishing for wider use.
- Consider atomic writes for alarm persistence if the app grows.
- Consider alarm enable/disable/edit commands as the next interface improvement.

---

# Lessons Learned

## App 34 — Digital Clock
**Terminal Utilities Group | Document 5 of 5**

## Project Summary

PyClock is a terminal digital clock package that grew into a small multi-mode time utility. It displays the current time, runs a stopwatch, supports countdown timers, renders world clocks, manages persisted alarms, and includes a Pomodoro mode. The strongest achievement is that the app does not treat the terminal UI as one giant script. Instead, it separates immutable domain state, injected time sources, command objects, renderers, display I/O, persistence, and CLI composition.

## Original Goals vs. Actual Outcome

The likely original goal was to build a terminal digital clock. The final outcome is broader: it is a multi-mode clock utility with alarms, timers, stopwatch, Pomodoro, config, persistence, keyboard input, and tests. That expansion could have become uncontrolled scope creep, but the project’s module boundaries keep it reasonably disciplined.

Delivered:

- current time display
- timezone support
- 12/24-hour formatting
- seconds/date toggles
- interactive keyboard controls
- stopwatch with laps
- countdown timers
- Pomodoro state
- world-clock mode
- persisted alarms
- JSONL stopwatch sessions
- config file support
- renderer strategies
- injected time sources
- integration tests for loop behavior

Not fully delivered or not yet polished:

- alarm enable/disable/edit command
- CLI log viewing for stopwatch sessions
- fully consistent CLI error formatting
- atomic persistence writes
- advanced terminal layout handling
- sound/desktop notifications beyond terminal bell

## Technical Decisions That Paid Off

### Immutable domain objects

Using frozen dataclasses for `ClockState`, `TimerState`, `StopwatchState`, and `PomodoroState` made behavior easier to reason about. Commands can return new states instead of mutating a shared object.

### Injectable time sources

This was one of the best design decisions. Time-sensitive apps are hard to test if they call real time everywhere. `FrozenTimeSource` lets tests advance time manually, and the one-shot timer test can avoid real delays by injecting fake sleep behavior.

### Pure renderers

`BigDigitRenderer` and `MinimalRenderer` return strings instead of printing. This makes renderer tests simple and keeps terminal behavior inside `Display`.

### Command pattern for keybindings

Representing keybindings as command objects made the interactive controls understandable. Adding a new key does not require editing a huge conditional block in the loop.

### Repository abstraction for alarms

The JSON repository handles real persistence, while the in-memory repository supports tests. This is a clean example of using abstraction only where it solves an actual problem.

## Technical Decisions That Created Debt

### Multiple features in one app

Clock, stopwatch, timer, world clock, alarms, and Pomodoro are related, but together they create a lot of surface area. The app remains manageable, but the broad feature set increases documentation and testing requirements.

### One-shot timer separate from main loop

`run_one_shot_timer` is practical and simple, but it does not reuse the full renderer/display stack. That creates a parallel path for timer behavior.

### Minimal CLI error wrapping

The app defines custom exceptions, but the CLI does not yet consistently catch and format every domain error. Wider user-facing polish would need a central `ClockError` handler.

### Whole-second duration model

Whole-second `Duration` values are simple and sufficient for a digital clock, but they limit sub-second precision. This is acceptable for scope, but it should be documented.

### Full-file alarm persistence

Writing the entire alarm list is fine for small data. It would need atomic write behavior if the app were used heavily or by multiple processes.

## What Was Harder Than Expected

### Time crossing logic

Alarm scheduling is more subtle than checking whether `current.time() == alarm.time`. The implementation needs to detect crossing from a previous timestamp to a current timestamp and avoid firing repeatedly on the same day.

### Terminal input

Keyboard input across POSIX and Windows requires platform-specific code. The input thread and queue boundary simplify the main loop, but terminal I/O remains inherently tricky.

### Keeping renderers pure

It is tempting to print directly from the renderer because the output is terminal-specific. Keeping renderers pure required a cleaner mental model: renderer returns text, display writes text.

### Testing interactive behavior

Interactive apps are harder to test than simple CLI commands. The project addresses this by monkeypatching `InputListener`, using fake time sources, disabling ANSI output, and writing to `StringIO`.

## What Was Easier Than Expected

### State toggles

Features like toggling seconds, date, time format, and help visibility became straightforward once the command pattern and immutable state were in place.

### Minimal output

The minimal renderer provides a simple path for `pyclock now` and world-clock output. It avoids needing to parse big terminal output in simple cases.

### Stopwatch and timer ticks

Once `Duration` existed, stopwatch and timer ticking became simple arithmetic over immutable values.

## Python-Specific Learnings

- `dataclasses.replace` is useful for immutable state transitions.
- `Enum` keeps display modes and time formats safer than raw strings.
- `zoneinfo.ZoneInfo` provides standard-library timezone support.
- `tomllib` allows dependency-free TOML config loading in Python 3.11+.
- `queue.Queue` is a clean bridge between an input thread and a main loop.
- `threading.Event` is a simple shutdown signal.
- `argparse` is enough for a small but structured CLI.
- `StringIO` makes output behavior testable.
- `pytest.monkeypatch` helps simulate interactive behavior.
- `jsonl` is easy to append for event/session history.

## Architecture Insights

The most important architecture insight is that a terminal app benefits from the same separation used in larger systems:

- domain state should not know about the terminal
- renderers should not own stdout
- input listeners should not mutate application state
- persistence should be behind repositories
- time should be injected
- commands should transform state predictably

If rebuilt, the next improvement would be to formalize the app as a clearer reducer-style architecture:

```text
ClockState + Event -> ClockState
```

Keyboard events, time ticks, alarm due events, and timer completion notifications could all flow through a common event reducer.

## Testing Gaps

Covered:

- renderer outputs
- alarm scheduling and duplicate rejection
- command state transitions
- time source behavior
- loop integration with fake input and fake time
- one-shot timer output with injected sleep

Gaps:

- config parsing edge cases
- corrupted alarm JSON handling
- `alarm add/list/remove` CLI paths directly
- ANSI-enabled terminal rendering behavior
- Windows keyboard input path
- Pomodoro edge cases across multiple work/break cycles
- stopwatch session JSONL append behavior
- invalid timezone CLI handling
- PTY smoke script behavior in CI environments

## Reusable Patterns Identified

- Immutable `ClockState` snapshot for terminal UI apps
- `TimeSource` protocol for any time-dependent app
- Renderer strategy returning strings
- Background input thread plus queue
- Command registry for keyboard actions
- Repository interface with JSON and in-memory implementations
- Append-only JSONL session logging
- Minimal renderer for tests and machine-friendly output
- Config dataclass loaded from TOML

## If I Built This Again

### 1. Add a central application event reducer

The loop currently performs tick updates and then drains commands. A unified event reducer would make all state transitions more consistent:

```text
Tick(now)
KeyPressed(key)
AlarmDue(alarm)
TimerCompleted(timer)
```

This would also make testing more uniform.

### 2. Improve persistence robustness

Alarm writes should use atomic write behavior:

1. write temporary file
2. flush
3. replace target file

Config and alarm loading should handle malformed files with clearer messages.

### 3. Unify one-shot timer and interactive timer logic

The one-shot timer is simple, but it duplicates timer countdown behavior. A future version could run it through the same `TimerState` and renderer abstractions while still keeping output compact.

## Open Questions

- Should alarms support enable/disable/edit from the CLI?
- Should stopwatch sessions have a `pyclock sessions` command?
- Should Pomodoro sessions be logged like stopwatch sessions?
- Should alarm scheduling support weekdays or one-time dates?
- Should invalid config files fail loudly or fall back to defaults?
- Should color schemes be user-extensible through config?
- Should the terminal UI support resizing or fixed layout constraints?
- Should `Duration` support milliseconds, or are whole seconds the correct clock-level abstraction?

## Constitution Reflection

This project is valid under the Constitution as a medium Python CLI application. It demonstrates authentic architectural thinking through immutable state, injected time, pure renderers, command objects, repository-backed persistence, and deterministic tests. The implementation is more complex than a small single-file clock, but the complexity is justified by the feature set and divided into coherent modules.

The biggest weakness is surface-area growth: PyClock contains several related utilities in one package. The strongest architectural decision is the single immutable `ClockState` passed through commands, renderers, and the loop. The next likely refactor is a unified event reducer and stronger persistence/error-handling boundaries.
