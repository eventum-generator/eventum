---
paths:
  - "eventum/**/*.py"
---

# Exception Rules

`ContextualError` (`eventum/exceptions.py`) - base exception with required `context: dict` kwarg.

## When to inherit from `ContextualError`

Use `ContextualError` (or a subclass) when any of the following is true:

- Structured context must travel with the exception.
- Multiple sources raise the same exception type and callers need to distinguish them (e.g. plugins).

In other cases inherit from plain `Exception` is acceptable.

## Raising

- Pass `context={...}` with fields only from `LOGGING.md`.
- Keep the message a static string - dynamic values go into `context`, not into the message.

## Re-raising

- Catch only when you act on the exception - otherwise let it propagate.
- An exception raised out of a layer must match that layer's abstraction - translate lower-layer types before re-raising.
- When translating into a `ContextualError`, forward the cause through the new `context`: reuse `e.context` for another `ContextualError`, or `prettify_validation_errors(e.errors())` for a Pydantic `ValidationError`.
- Use `from e` when the traceback aids diagnosis (unexpected errors caught via `except Exception`); `from None` when the new exception already subsumes the cause.
- Do not `except` just to log and re-raise - the top handler already has the exception's `context`.
