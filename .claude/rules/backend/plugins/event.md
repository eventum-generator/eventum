# Event Plugin Rules

Event plugins turn a timestamp into zero or more event strings. Pipeline executor calls `_produce` per timestamp and forwards the returned list to the output stage.

## Interface

- Inherit `EventPlugin[FooConfig, FooParams]`; config inherits `EventPluginConfig`, params inherits `EventPluginParams`.
- Implement `_produce` - returns a `list[str]` (empty list means "drop this timestamp").
- `ProduceParams` is the `TypedDict` passed to `_produce`, carrying `timestamp` and `tags`. It doubles as the request body model of the preview `produce` endpoint, so every field of it must be JSON-serializable - a runtime object handed to a plugin belongs in a subclass owned by that plugin.

## Signals vs errors

`_produce` distinguishes control-flow signals from actual errors. Raise signals for expected flow control; raise the error type for unexpected failures.

- `PluginEventDroppedError` signals an intentional drop; the framework silently increments the dropped counter.
- `PluginEventsExhaustedError` signals no more events are available; stops the pipeline stage.
- `PluginProduceError` is the runtime-failure type - raise it for anything unexpected.

## Global state

`GLOBAL_STATE` (`eventum/plugins/event/state.py`) is the process-wide thread-safe state every generator in the process shares. `EventPlugin` connects to it, so a plugin reaches it as `self._global_state` and never owns an instance of its own. The scenario API routes and the MCP global-state tools read and write that same instance.

- `EventPlugin.produce` drops every hold the plugin left on the state lock once the event is over - `_produce` may acquire it without a `finally` of its own.
- A plugin that exposes the state to user-provided code hands it over itself - in the params of that code (`ScriptProduceParams` of the `script` plugin) or in its render context (the template plugin) - rather than letting the code import it.

## Cross-cutting updates

Adding a new context variable or module function to the template plugin requires syncing:

- `globals.ts` under `ui/src/pages/ProjectPage/common/EditorTab/FileEditor/completions/` - Jinja autocomplete.
- `../docs/content/docs/plugins/event/template/` - user-facing docs.

A **new top-level module namespace** (a new file under `modules/`) must be surfaced in `eventum/plugins/event/plugins/template/reference.py`, which the MCP `eventum://templating/reference` resource introspects. New helpers added to an *existing* namespace appear there automatically.
