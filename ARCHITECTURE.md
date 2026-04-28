# Architecture

PyClock is organized around three decisions that keep time-based code testable.

## Time Is Injected

Anything that needs the current time receives a `TimeSource`. Production uses
`SystemTimeSource`, tests use `FrozenTimeSource`, and demos can use
`AcceleratedTimeSource`. This avoids hidden calls to `datetime.now()` inside
business logic.

## Rendering Has No I/O

Renderers implement `Renderer.render(state) -> str`. They receive a full
`ClockState` snapshot and return text. The `Display` class owns stdout, ANSI
screen clearing, cursor state, and diff-based redraws. That split lets tests
assert renderer output without a terminal.

## Input Is Commands

Keybindings are registered as `Command` objects in a `CommandRegistry`. The help
overlay is generated from that registry, so the UI and input handling share one
source of truth. Mode switching is explicit through `DisplayMode`, and commands
return new immutable state snapshots instead of mutating global state.
