"""Tests for http input plugin."""

import asyncio
import logging
import socket
import time
from collections.abc import Generator, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from http import HTTPStatus
from threading import Event, Thread
from types import SimpleNamespace
from typing import cast
from zoneinfo import ZoneInfo

import pytest
import requests as rq  # type: ignore[import-untyped]
import structlog
from fastapi import HTTPException
from numpy import datetime64
from numpy.typing import NDArray

from eventum.logging.channels import resolve_channel
from eventum.plugins.input.exceptions import PluginGenerationError
from eventum.plugins.input.plugins.http import plugin as http_plugin
from eventum.plugins.input.plugins.http.config import HttpInputPluginConfig
from eventum.plugins.input.plugins.http.plugin import (
    GenerateRequestData,
    HttpInputPlugin,
)

HOST = '127.0.0.1'
STARTUP_TIMEOUT = 15.0
REQUEST_TIMEOUT = 15.0
STOP_TIMEOUT = 15.0
REQUESTS = 5
COUNT_PER_REQUEST = 2


def _make_plugin(
    port: int, max_pending_requests: int = 100
) -> HttpInputPlugin:
    return HttpInputPlugin(
        config=HttpInputPluginConfig(
            host=HOST,
            port=port,
            max_pending_requests=max_pending_requests,
        ),
        params={
            'id': 1,
            'timezone': ZoneInfo('UTC'),
        },
    )


@contextmanager
def _taken_port() -> Iterator[int]:
    """Listen on an ephemeral port and yield it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        sock.listen(1)
        yield sock.getsockname()[1]


def _free_port() -> int:
    """Return a port that is free at the moment of the call."""
    with _taken_port() as port:
        return port


def _wait_until_started(plugin: HttpInputPlugin, future: Future) -> None:
    """Wait until the plugin's own server accepts interaction.

    Raises
    ------
    TimeoutError
        If the server does not start within the timeout.

    """
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while not plugin._server.started:
        if future.done():
            # Re-raises the failure that stopped the server
            future.result()

            msg = 'Http server stopped before it started serving'
            raise TimeoutError(msg)

        if time.monotonic() > deadline:
            msg = 'Http server did not start in time'
            raise TimeoutError(msg)

        time.sleep(0.01)


@pytest.mark.filterwarnings('ignore:websockets')
def test_plugin() -> None:
    """Each request generates the requested number of timestamps."""
    port = _free_port()
    plugin = _make_plugin(port)
    url = f'http://{HOST}:{port}'

    timestamps: list[datetime64] = []

    def generate() -> None:
        for batch in plugin.generate(size=100):
            timestamps.extend(batch)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(generate)

        _wait_until_started(plugin, future)

        for _ in range(REQUESTS):
            res = rq.post(
                f'{url}/generate',
                json={'count': COUNT_PER_REQUEST},
                timeout=REQUEST_TIMEOUT,
            )
            assert res.status_code == HTTPStatus.CREATED

        res = rq.post(f'{url}/stop', timeout=REQUEST_TIMEOUT)

        assert res.status_code == HTTPStatus.OK

        future.result()

    assert len(timestamps) == REQUESTS * COUNT_PER_REQUEST


@pytest.mark.filterwarnings('ignore:websockets')
def test_plugin_logs_belong_to_its_generator() -> None:
    """The plugin's own server logs to the generator that runs it."""
    port = _free_port()
    url = f'http://{HOST}:{port}'
    channels: dict[str, str] = {}

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            channels[record.name] = resolve_channel(record)

    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    root.handlers.clear()
    root.addHandler(Capture())
    root.setLevel(logging.DEBUG)

    # The generator binds its id at the entry of its own thread
    structlog.contextvars.bind_contextvars(generator_id='gen-1')
    plugin = _make_plugin(port)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                lambda: list(plugin.generate(size=100)),
            )
            _wait_until_started(plugin, future)

            rq.post(
                f'{url}/generate',
                json={'count': 1},
                timeout=REQUEST_TIMEOUT,
            )
            rq.post(f'{url}/stop', timeout=REQUEST_TIMEOUT)
            future.result()
    finally:
        root.handlers.clear()
        root.handlers.extend(handlers)
        root.setLevel(level)
        structlog.contextvars.clear_contextvars()

    assert channels['uvicorn.error'] == 'generator_gen-1'
    assert channels['uvicorn.access'] == 'generator_gen-1'


@pytest.mark.filterwarnings('ignore:websockets')
def test_plugin_with_taken_port() -> None:
    """Occupied bind port surfaces as a generation error."""
    with _taken_port() as port:
        plugin = _make_plugin(port)

        with pytest.raises(PluginGenerationError):
            for _ in plugin.generate(size=100):
                pass


def _suspend_after_first_request(
    plugin: HttpInputPlugin,
    url: str,
) -> Generator[NDArray[datetime64]]:
    """Start generating and leave the generator suspended after the
    batch of its first request, as a consumer that stopped reading.
    """
    generator = cast(
        'Generator[NDArray[datetime64]]',
        plugin.generate(size=100),
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(next, generator)
        _wait_until_started(plugin, first)

        res = rq.post(url, json={'count': 1}, timeout=REQUEST_TIMEOUT)
        assert res.status_code == HTTPStatus.CREATED
        first.result(timeout=REQUEST_TIMEOUT)

    return generator


def _drain(generator: Iterator[NDArray[datetime64]]) -> list[datetime64]:
    """Read the generator to its end, failing if it never ends."""
    timestamps: list[datetime64] = []

    def drain() -> None:
        for batch in generator:
            timestamps.extend(batch)

    thread = Thread(target=drain, daemon=True)
    thread.start()
    thread.join(timeout=STOP_TIMEOUT)

    assert not thread.is_alive()
    return timestamps


@pytest.mark.filterwarnings('ignore:websockets')
def test_plugin_refuses_requests_over_pending_limit() -> None:
    """Requests beyond the pending limit are refused."""
    port = _free_port()
    plugin = _make_plugin(port, max_pending_requests=1)
    url = f'http://{HOST}:{port}/generate'
    generator = _suspend_after_first_request(plugin, url)

    try:
        with ThreadPoolExecutor(max_workers=REQUESTS * 4) as executor:
            statuses = list(
                executor.map(
                    lambda _: (
                        rq.post(
                            url,
                            json={'count': 1},
                            timeout=REQUEST_TIMEOUT,
                        ).status_code
                    ),
                    range(REQUESTS * 4),
                ),
            )
    finally:
        plugin.stop_interacting()

    assert statuses.count(HTTPStatus.CREATED) == 1
    assert statuses.count(HTTPStatus.TOO_MANY_REQUESTS) == REQUESTS * 4 - 1
    assert len(_drain(generator)) == 1


def test_plugin_limit_holds_for_concurrent_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent requests cannot all pass the pending limit, though
    logging hands control back to the event loop.
    """
    plugin = _make_plugin(_free_port(), max_pending_requests=1)

    async def log(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(0)

    monkeypatch.setattr(
        plugin,
        '_logger',
        SimpleNamespace(adebug=log, awarning=log, ainfo=log),
    )

    async def handle() -> int:
        try:
            await plugin._handle_generate(GenerateRequestData(count=1))
        except HTTPException as e:
            return e.status_code

        return HTTPStatus.CREATED

    async def handle_together() -> tuple[int, int]:
        return await asyncio.gather(handle(), handle())

    statuses = asyncio.run(handle_together())

    assert sorted(statuses) == [
        HTTPStatus.CREATED,
        HTTPStatus.TOO_MANY_REQUESTS,
    ]


@pytest.mark.filterwarnings('ignore:websockets')
def test_plugin_serves_pending_requests_after_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requests accepted before a stop are generated, then the
    generator ends.
    """
    port = _free_port()
    plugin = _make_plugin(port, max_pending_requests=1)
    url = f'http://{HOST}:{port}/generate'

    # The closing sentinel must arrive while the limit is still reached
    server_ended = Event()
    watch_server = plugin._watch_server

    def watch(future: Future) -> None:
        watch_server(future)
        server_ended.set()

    monkeypatch.setattr(plugin, '_watch_server', watch)
    generator = _suspend_after_first_request(plugin, url)

    try:
        res = rq.post(url, json={'count': 2}, timeout=REQUEST_TIMEOUT)
        assert res.status_code == HTTPStatus.CREATED
    finally:
        plugin.stop_interacting()

    assert server_ended.wait(timeout=STOP_TIMEOUT)
    assert len(_drain(generator)) == 2  # noqa: PLR2004


@pytest.mark.filterwarnings('ignore:websockets')
def test_plugin_closes_with_pending_limit_reached() -> None:
    """Closing an abandoned generator with the pending limit reached
    ends its server.
    """
    port = _free_port()
    plugin = _make_plugin(port, max_pending_requests=1)
    url = f'http://{HOST}:{port}/generate'
    generator = _suspend_after_first_request(plugin, url)

    res = rq.post(url, json={'count': 1}, timeout=REQUEST_TIMEOUT)
    assert res.status_code == HTTPStatus.CREATED

    # Leaving the generator waits for its server to exit
    closing = Thread(target=generator.close, daemon=True)
    closing.start()

    try:
        closing.join(timeout=STOP_TIMEOUT)
        assert not closing.is_alive()
    finally:
        # Lets a regression fail the test rather than hang the session
        plugin.stop_interacting()


@pytest.mark.filterwarnings('ignore:websockets')
def test_plugin_stopped_before_start_leaves_port_alone() -> None:
    """A plugin stopped before it generates starts no server."""
    with _taken_port() as port:
        plugin = _make_plugin(port)
        plugin.stop_interacting()

        assert list(plugin.generate(size=100)) == []


@pytest.mark.filterwarnings('ignore:websockets')
def test_plugin_stops_with_unfinished_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A client that never finishes its request does not hold the
    plugin running after a stop.
    """
    monkeypatch.setattr(http_plugin, '_SHUTDOWN_TIMEOUT', 1)
    port = _free_port()
    plugin = _make_plugin(port)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: list(plugin.generate(size=100)))
        _wait_until_started(plugin, future)

        with socket.create_connection((HOST, port)) as client:
            client.sendall(
                b'POST /generate HTTP/1.1\r\n'
                b'Host: localhost\r\n'
                b'Content-Type: application/json\r\n'
                b'Content-Length: 50\r\n\r\n'
                b'{"count"',
            )
            time.sleep(0.2)

            plugin.stop_interacting()

            assert future.result(timeout=STOP_TIMEOUT) == []
