---
paths:
  - "eventum/**/*.py"
---

# Logging Rules

Eventum logs through `structlog` over stdlib. Output is split into streams:

- `main.log` - app-wide events.
- `generator_<id>.log` - per-generator log, routed by the `generator_id` contextvar.
- `server_access.log` / `server_error.log` - HTTP server.

Output format is `plain` or `json`, selected by the `log.format` setting.

## Field names

- Kwargs on log calls MUST use names from `LOGGING.md`.
- To introduce a new field, add it to `LOGGING.md` first (name, type, description), then use it in code.

## Message style

- Keep the event (first positional arg) a static string - dynamic values go into kwargs, not into the message.

## Serializing kwargs

- Kwargs must be flat primitives: `Path` as `str(path)`, Pydantic models as `model.model_dump(mode='json')`, etc.

## Thread boundaries

- To route a thread's logs to `generator_<id>.log`, call `structlog.contextvars.bind_contextvars(generator_id=...)` at its entry.

## Logging caught exceptions

- `ContextualError`: `logger.error(str(e), **e.context)` - spreads the context into structured fields.
- Unknown `Exception` (from a broad `except Exception`): `logger.exception(msg, reason=str(e))` - adds the traceback.

## Hot paths

- Avoid excessive per-event logging in hot paths.
