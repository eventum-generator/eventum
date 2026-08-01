"""Tests for http input plugin."""

import socket
import time
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from http import HTTPStatus
from zoneinfo import ZoneInfo

import pytest
import requests as rq  # type: ignore[import-untyped]
from numpy import datetime64

from eventum.plugins.input.exceptions import PluginGenerationError
from eventum.plugins.input.plugins.http.config import HttpInputPluginConfig
from eventum.plugins.input.plugins.http.plugin import HttpInputPlugin

HOST = '127.0.0.1'
STARTUP_TIMEOUT = 15.0
REQUEST_TIMEOUT = 15.0
REQUESTS = 5
COUNT_PER_REQUEST = 2


def _make_plugin(port: int) -> HttpInputPlugin:
    return HttpInputPlugin(
        config=HttpInputPluginConfig(host=HOST, port=port),
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
    while not plugin.can_interact:
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
def test_plugin_with_taken_port() -> None:
    """Occupied bind port surfaces as a generation error."""
    with _taken_port() as port:
        plugin = _make_plugin(port)

        with pytest.raises(PluginGenerationError):
            for _ in plugin.generate(size=100):
                pass
