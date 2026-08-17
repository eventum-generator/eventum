# Logging Rules

Eventum logs through `structlog` over stdlib. Every record - ours or a library's - goes to the file of exactly one channel, while stderr receives all of them and stays the combined view.

- `main.log` - process core: `app`, `cli`, and anything not attributed elsewhere.
- `server.log` - `api`, `server`, `uvicorn`.
- `server_access.log` - `uvicorn.access`.
- `mcp.log` - `mcp` adapter and the MCP SDK.
- `generator_<id>.log` - everything carrying a `generator_id`.

Output format is `plain` or `json`, selected by the `log.format` setting; `log.level` applies to Eventum, `log.third_party_level` to every other library.

## Channels

`eventum/logging/channels.py` holds the whole policy: `resolve_channel` picks a channel and `ChannelFilter` writes it onto the record for `RoutingHandler` to route on. Four rules in order:

1. `generator_id`, from the record or from contextvars;
2. `LOGGER_CHANNELS` - logger name prefix, longest wins;
3. `component` from contextvars, bound at an entry point;
4. `main`.

- A new top-level package under `eventum/` is either mapped in `LOGGER_CHANNELS` or listed in `CONTEXT_FOLLOWING_PACKAGES`; a guard test fails otherwise. Leave a package unmapped when its records belong to whoever called it (`core`, `plugins`, `security`).
- A library that configures logging for itself is listed in `CLAIMED_LOGGERS` (`eventum/logging/config.py`), which drops its handlers and levels so its records propagate to ours.

## Field names

- Kwargs on log calls MUST use names from `LOGGING.md`.
- To introduce a new field, add it to `LOGGING.md` first (name, type, description), then use it in code.

## Message style

- Keep the event (first positional arg) a static string - dynamic values go into kwargs, not into the message.

## Serializing kwargs

- Kwargs must be flat primitives: `Path` as `str(path)`, Pydantic models as `model.model_dump(mode='json')`, etc.

## Context boundaries

A context is not inherited by a new thread, and a served request runs in a context of its own.

- To route a thread's logs to `generator_<id>.log`, call `structlog.contextvars.bind_contextvars(generator_id=...)` at its entry.
- To attribute a thread to a component, call `bind_component(...)` at its entry.
- To attribute the requests of an ASGI app, wrap it in `LogContextMiddleware` (`eventum/logging/asgi.py`); binding on the serving thread does not reach them.
- To carry the current attribution into a thread you start yourself, pass `capture_log_context()` over and `bind_log_context(...)` at its entry - a plugin running its own server does both.

## Logging caught exceptions

- `ContextualError`: `logger.error(str(e), **e.context)` - spreads the context into structured fields.
- Unknown `Exception` (from a broad `except Exception`): `logger.exception(msg, reason=str(e))` - adds the traceback.

## Hot paths

- Avoid excessive per-event logging in hot paths.
