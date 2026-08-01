"""Server-side shutdown helpers for long-lived SSE streams.

SSE streams served by the MCP transport (via ``sse_starlette``) drain on
shutdown only once the library observes the server stopping. Eventum
runs uvicorn in a background thread, where uvicorn installs no signal
handlers, so ``sse_starlette``'s automatic detection never fires. The
app therefore drives the library's shutdown flag explicitly around the
server lifecycle.
"""


def request_sse_drain() -> None:
    """Signal active SSE streams to drain before the server stops.

    Without this an open MCP SSE stream keeps the connection alive until
    uvicorn's graceful-shutdown timeout expires and tasks are force
    cancelled.
    """
    _set_sse_should_exit(value=True)


def reset_sse_drain() -> None:
    """Clear the SSE drain flag before (re)starting the server.

    The flag is a process-global in ``sse_starlette``; an in-process
    restart (SIGHUP) reuses it, so it must be cleared on start or the
    fresh server would close every SSE stream immediately.
    """
    _set_sse_should_exit(value=False)


def _set_sse_should_exit(*, value: bool) -> None:
    """Set ``sse_starlette``'s shutdown flag if it is installed."""
    try:
        from sse_starlette.sse import AppStatus
    except ImportError:
        return

    AppStatus.should_exit = value
