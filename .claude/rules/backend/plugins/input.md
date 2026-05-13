---
paths:
  - "eventum/plugins/input/**/*.py"
---

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
- Interactive plugins also implement `has_interaction`, `can_interact`, `stop_interacting()`.
