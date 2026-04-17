---
paths:
  - "eventum/plugins/event/**/*.py"
---

# Event Plugin Rules

Event plugins turn a timestamp into zero or more event strings. Pipeline executor calls `_produce` per timestamp and forwards the returned list to the output stage.

## Interface

- Inherit `EventPlugin[FooConfig, FooParams]`; config inherits `EventPluginConfig`, params inherits `EventPluginParams`.
- Implement `_produce` - returns a `list[str]` (empty list means "drop this timestamp").
- `ProduceParams` is the `TypedDict` passed to `_produce`, carrying `timestamp` and `tags`.

## Signals vs errors

`_produce` distinguishes control-flow signals from actual errors. Raise signals for expected flow control; raise the error type for unexpected failures.

- `PluginEventDroppedError` signals an intentional drop; the framework silently increments the dropped counter.
- `PluginExhaustedError` signals no more events are available; stops the pipeline stage.
- `PluginProduceError` is the runtime-failure type - raise it for anything unexpected.
