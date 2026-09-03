# Output Plugin Rules

Output plugins deliver event strings to a destination (file, socket, broker, etc.). Output plugins have an explicit async lifecycle: `_open` to acquire the destination, `_write` to push batches, `_close` to release.

## Interface

- Inherit `OutputPlugin[FooConfig, FooParams]`; config inherits `OutputPluginConfig`, params inherits `OutputPluginParams`.
- Implement async `_open`, `_close`, `_write`.
- `_write` receives a batch of events and returns the number actually written (not blindly `len(events)`).

## Config

- Output configs carry a `formatter` field - choose the most appropriate default format when implementing new plugin.

## Lifecycle

- Acquiring runtime resources (open files, sockets, clients) happens in `_open`, not in `__init__`.
- Releasing them happens in `_close`.

## Errors

- Raise `PluginOpenError` for failures in `_open`.
- Raise `PluginWriteError` for failures in `_write`.
- `FormatError` raised by the formatter is logged by the base class with the offending event - don't catch it in `_write`.

## Async context

- `_write` runs on the event loop. Offload CPU-bound work via `asyncio.to_thread` to keep the loop free.

## Cross-cutting updates

Adding a new formatter requires:

- matching Zod schema under `ui/src/api/routes/generator-configs/schemas/`.
- `FormatterParams.tsx` UI component.
- entry in `../docs/content/docs/plugins/formatters.mdx`.

Adding a new authentication method for http based outputs
(`eventum/plugins/output/http_auth/`) requires:

- config variant in `http_auth/config.py`, listed in `HttpAuthConfigT`.
- authenticator class in `http_auth/authenticators.py`, bound through
  `auth_type=`. One that holds a token it renews builds on
  `TokenHttpAuthenticator` and supplies `_fetch_token` alone - the
  cache, the expiry, the lock and the answer to a rejection are there.
- matching Zod variant in `schemas/plugins/output/auth.ts`, listed in
  `HTTPAuthConfigSchema`.
- branch in the `AuthParams.tsx` form, and a picker on every field
  that holds a credential.
- section in `../docs/content/docs/plugins/output/http.mdx`.
