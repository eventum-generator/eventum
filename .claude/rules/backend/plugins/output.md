---
paths:
  - "eventum/plugins/output/**/*.py"
---

# Output Plugin Rules

Output plugins deliver event strings to a destination (file, socket, broker, etc.). Output plugins have an explicit async lifecycle: `_open` to acquire the destination, `_write` to push batches, `_close` to release.

## Interface

- Inherit `OutputPlugin[FooConfig, FooParams]`; config inherits `OutputPluginConfig`, params inherits `OutputPluginParams`.
- Implement async `_open`, `_close`, `_write`.
- `_write` receives a batch of events and returns the number actually written (not blindly `len(events)`).

## Config

- Output configs carry a `formatter` field - a discriminated union on `format`.

## Lifecycle

- Acquiring runtime resources (open files, sockets, clients) happens in `_open`, not in `__init__`.
- Releasing them happens in `_close`.

## Errors

- Raise `PluginOpenError` for failures in `_open`.
- Raise `PluginWriteError` for failures in `_write`.
- `FormatError` raised by the formatter is logged by the base class with the offending event - don't catch it in `_write`.

## Async context

- `_write` runs on the event loop. Offload CPU-bound work via `asyncio.to_thread` to keep the loop free.
