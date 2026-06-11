"""An active SSE stream drains on graceful shutdown.

Boots a real ``sse_starlette`` EventSourceResponse under uvicorn in a
background thread (App's model) and holds the stream open from a client
thread. ``request_sse_drain()`` must let the server stop well within the
graceful window instead of blocking until it expires - the MCP SSE drain
path the flag-flip unit tests cannot exercise.
"""

import asyncio
import contextlib
import socket
import threading
import time
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from sse_starlette.sse import AppStatus, EventSourceResponse

from eventum.server.shutdown import request_sse_drain, reset_sse_drain

_GRACEFUL_TIMEOUT = 10
_STARTUP_TIMEOUT = 20.0
_POLL = 0.05


@pytest.fixture(autouse=True)
def _restore_sse_flag() -> Iterator[None]:
    """Restore the process-global SSE flag around the test."""
    original = AppStatus.should_exit
    try:
        yield
    finally:
        AppStatus.should_exit = original


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def test_active_sse_stream_drains_on_shutdown() -> None:
    """A held-open SSE stream must not block the graceful window."""
    app = FastAPI()

    @app.get('/sse')
    async def sse() -> EventSourceResponse:
        async def gen() -> AsyncIterator[dict[str, str]]:
            while True:
                yield {'data': 'tick'}
                await asyncio.sleep(0.1)

        return EventSourceResponse(gen())

    port = _free_port()
    reset_sse_drain()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host='127.0.0.1',
            port=port,
            log_level='warning',
            lifespan='on',
            timeout_graceful_shutdown=_GRACEFUL_TIMEOUT,
        ),
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    start = time.monotonic()
    while not server.started:
        if time.monotonic() - start > _STARTUP_TIMEOUT:
            server.should_exit = True
            pytest.fail('server did not start in time')
        time.sleep(_POLL)

    connected = threading.Event()

    def hold() -> None:
        # The server closing the SSE on shutdown surfaces as a read error
        # in the client; that is the expected end of a drained stream.
        with (
            contextlib.suppress(httpx.HTTPError),
            httpx.Client() as client,
            client.stream(
                'GET',
                f'http://127.0.0.1:{port}/sse',
                timeout=_STARTUP_TIMEOUT,
            ) as resp,
        ):
            for _ in resp.iter_lines():
                connected.set()

    client_thread = threading.Thread(target=hold, daemon=True)
    client_thread.start()
    if not connected.wait(timeout=_STARTUP_TIMEOUT):
        server.should_exit = True
        pytest.fail('SSE stream did not connect')

    # Mirror App._stop_server: drain SSE streams, then request shutdown.
    request_sse_drain()
    server.should_exit = True

    shutdown_start = time.monotonic()
    thread.join(timeout=_GRACEFUL_TIMEOUT - 2)
    elapsed = time.monotonic() - shutdown_start

    assert not thread.is_alive(), 'server hung on shutdown with active SSE'
    assert elapsed < _GRACEFUL_TIMEOUT - 3
    client_thread.join(timeout=2.0)
