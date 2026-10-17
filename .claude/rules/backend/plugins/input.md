# Input Plugin Rules

Input plugins generate timestamps that drive event generation. The framework pulls chunks from the plugin by requesting a size, and the plugin yields numpy arrays until it exhausts.

## Interface

- Inherit `InputPlugin[FooConfig, FooParams]`; config inherits `InputPluginConfig`, params inherits `InputPluginParams`.
- Implement `_generate` - the sync iterator that yields chunks.

## Timestamps

All timestamps flowing through the pipeline are naive UTC numpy `datetime64`.

- Use helpers from `eventum.plugins.input.utils` if needed.
- Apply `skip_past` filtering inside the plugin if requested.

## Chunking

- Accumulate timestamps in `self._buffer` and yield chunks via `self._buffer.read(size, partial=...)`.
- Yield full-size chunks, a chunk yield may be partial if it's final or plugin is interactive.

## Errors

- Raise `PluginGenerationError` (from `eventum.plugins.input.exceptions`) for runtime failures during generation.

## Interactive plugins

Interactive plugins produce timestamps in response to external events (e.g. HTTP requests) rather than on a schedule.

- Opt in via the class declaration: `class FooPlugin(InputPlugin[...], interactive=True):`.
- Interactive plugins also implement `stop_interacting()` - idempotent and callable from any thread, as the pipeline calls it on every stop, abort and abandonment of the input.
- `_generate` of an interactive plugin may wait for an interaction indefinitely, but ends once `stop_interacting()` is called, including when that comes before it starts.
- Each interactive plugin is consumed as a source of its own; `InputPluginsMerger` rejects them, as their timestamps have nothing to be ordered against.

## Cross-cutting updates

A new input plugin, or a change to a config field, default or timestamp semantics of an existing one, is mirrored in the generator API reference of the `content-design` plugin (`github.com/eventum-generator/ai-plugins`, `skills/create-generator/references/eventum-api.md`), with the Eventum version it was verified against.
