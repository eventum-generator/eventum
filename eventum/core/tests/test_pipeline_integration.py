"""Integration tests for the full pipeline (Executor with real queues)."""

import asyncio
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from threading import Thread
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import numpy as np
import pytest
import requests as rq  # type: ignore[import-untyped]
from numpy.typing import NDArray

from eventum.core.executor import ExecutionError, Executor
from eventum.core.parameters import GeneratorParameters
from eventum.plugins.event.exceptions import PluginEventsExhaustedError
from eventum.plugins.input.plugins.http.config import HttpInputPluginConfig
from eventum.plugins.input.plugins.http.plugin import HttpInputPlugin
from eventum.plugins.output.exceptions import PluginOpenError


def _make_params(**overrides) -> GeneratorParameters:
    defaults: dict = {
        'id': 'integ',
        'path': Path('/tmp/config.yml'),
        'live_mode': False,
    }
    defaults.update(overrides)
    return GeneratorParameters(**defaults)


def _make_mock_input_plugin(
    plugin_id: int = 1,
    tags: tuple[str, ...] = ('default',),
    timestamps: list[NDArray[np.datetime64]] | None = None,
):
    """Create a mock InputPlugin that yields given timestamp arrays.

    The mock exposes .id, .config.tags, .is_interactive, and .generate().
    InputStage.configure() wraps this in an adapter + batcher, so
    generate() must yield NDArray[datetime64] batches.
    """
    if timestamps is None:
        base = np.datetime64('2020-01-01T00:00:00', 'us')
        timestamps = [
            np.array(
                [base + np.timedelta64(i * 1_000_000, 'us') for i in range(5)],
                dtype='datetime64[us]',
            ),
        ]

    plugin = MagicMock()
    plugin.id = plugin_id
    plugin.config.tags = tags
    plugin.is_interactive = False

    def generate(size, *, skip_past=True) -> Iterator[NDArray[np.datetime64]]:
        yield from timestamps

    plugin.generate = generate
    return plugin


def _make_mock_event_plugin(events_per_call: int = 1):
    """Create a mock EventPlugin.

    produce() takes a single ProduceParams dict with 'tags' and
    'timestamp' keys.
    """
    plugin = MagicMock()

    def produce(params):
        return [f'event-{params["timestamp"]}' for _ in range(events_per_call)]

    plugin.produce = produce
    return plugin


def _make_mock_output_plugin():
    """Create a mock OutputPlugin with async open/write/close."""
    plugin = MagicMock()
    plugin.open = AsyncMock()
    plugin.close = AsyncMock()
    plugin.write = AsyncMock(return_value=0)
    plugin.__str__ = MagicMock(return_value='<mock output>')
    return plugin


# - Full pipeline ---------------------------------------------------------


def test_full_pipeline():
    """Mock input (5 timestamps) through event and output stages.

    Verify that output.write is called and open/close are invoked.
    """
    base = np.datetime64('2020-01-01T00:00:00', 'us')
    timestamps = [
        np.array(
            [base + np.timedelta64(i * 1_000_000, 'us') for i in range(5)],
            dtype='datetime64[us]',
        ),
    ]

    input_plugin = _make_mock_input_plugin(timestamps=timestamps)
    event_plugin = _make_mock_event_plugin(events_per_call=1)
    output_plugin = _make_mock_output_plugin()

    executor = Executor(
        input=[input_plugin],
        event=event_plugin,
        output=[output_plugin],
        params=_make_params(),
    )

    executor.execute()

    output_plugin.open.assert_awaited_once()
    output_plugin.close.assert_awaited_once()
    assert output_plugin.write.await_count >= 1


def test_full_pipeline_request_stop():
    """Requesting stop during execution causes partial completion."""
    base = np.datetime64('2020-01-01T00:00:00', 'us')
    # Generate many small batches to allow stop to interrupt
    timestamps = [
        np.array(
            [base + np.timedelta64(i * 1_000_000, 'us')],
            dtype='datetime64[us]',
        )
        for i in range(200)
    ]

    input_plugin = _make_mock_input_plugin(timestamps=timestamps)
    event_plugin = _make_mock_event_plugin()
    output_plugin = _make_mock_output_plugin()

    executor = Executor(
        input=[input_plugin],
        event=event_plugin,
        output=[output_plugin],
        params=_make_params(),
    )

    def stop_after_delay():
        time.sleep(0.1)
        executor.request_stop()

    Thread(target=stop_after_delay).start()
    executor.execute()

    # Pipeline completed (possibly partially) without hanging
    output_plugin.open.assert_awaited_once()
    output_plugin.close.assert_awaited_once()


def test_full_pipeline_output_open_error():
    """Output plugin failing to open raises ExecutionError."""
    input_plugin = _make_mock_input_plugin()
    event_plugin = _make_mock_event_plugin()
    output_plugin = _make_mock_output_plugin()
    output_plugin.open.side_effect = PluginOpenError(
        'connection refused',
        context={'reason': 'test'},
    )

    executor = Executor(
        input=[input_plugin],
        event=event_plugin,
        output=[output_plugin],
        params=_make_params(),
    )

    with pytest.raises(ExecutionError):
        executor.execute()

    output_plugin.close.assert_awaited_once()


# - Interactive input -----------------------------------------------------

HOST = '127.0.0.1'
EXECUTE_TIMEOUT = 15.0


def _make_http_input_plugin(
    plugin_id: int = 1,
) -> tuple[HttpInputPlugin, int]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        port = sock.getsockname()[1]

    plugin = HttpInputPlugin(
        config=HttpInputPluginConfig(host=HOST, port=port),
        params={'id': plugin_id, 'timezone': ZoneInfo('UTC')},
    )
    return plugin, port


def _start_execution(executor: Executor) -> tuple[Thread, list[Exception]]:
    errors: list[Exception] = []

    def execute() -> None:
        try:
            executor.execute()
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    thread = Thread(target=execute, daemon=True)
    thread.start()
    return thread, errors


def _wait_until_serving(plugin: HttpInputPlugin) -> None:
    deadline = time.monotonic() + EXECUTE_TIMEOUT
    while not plugin._server.started:
        assert time.monotonic() < deadline
        time.sleep(0.01)


@pytest.mark.filterwarnings('ignore:websockets')
def test_interactive_input_stops_on_output_open_error():
    """Output failing to open ends a pipeline fed by an interactive
    input, with no stop requested.
    """
    input_plugin, _ = _make_http_input_plugin()
    output_plugin = _make_mock_output_plugin()
    serving = threading.Event()

    # Fails once the input serves and waits for requests
    async def open_when_serving() -> None:
        await asyncio.to_thread(serving.wait, EXECUTE_TIMEOUT)
        msg = 'connection refused'
        raise PluginOpenError(msg, context={'reason': 'test'})

    output_plugin.open.side_effect = open_when_serving

    executor = Executor(
        input=[input_plugin],
        event=_make_mock_event_plugin(),
        output=[output_plugin],
        params=_make_params(live_mode=True),
    )
    thread, errors = _start_execution(executor)

    try:
        _wait_until_serving(input_plugin)
        serving.set()
        thread.join(timeout=EXECUTE_TIMEOUT)
    finally:
        # Lets a regression fail the test rather than hang the session
        input_plugin.stop_interacting()

    assert not thread.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], ExecutionError)


@pytest.mark.filterwarnings('ignore:websockets')
def test_interactive_input_stops_on_events_exhausted():
    """Exhausted event plugin ends a pipeline fed by an interactive
    input, with no stop requested.
    """
    input_plugin, port = _make_http_input_plugin()
    event_plugin = MagicMock()
    event_plugin.produce = MagicMock(
        side_effect=PluginEventsExhaustedError('exhausted'),
    )

    executor = Executor(
        input=[input_plugin],
        event=event_plugin,
        output=[_make_mock_output_plugin()],
        params=_make_params(live_mode=True),
    )
    thread, errors = _start_execution(executor)

    try:
        _wait_until_serving(input_plugin)
        rq.post(
            f'http://{HOST}:{port}/generate',
            json={'count': 1},
            timeout=EXECUTE_TIMEOUT,
        )
        thread.join(timeout=EXECUTE_TIMEOUT)
    finally:
        # Lets a regression fail the test rather than hang the session
        input_plugin.stop_interacting()

    assert not thread.is_alive()
    assert errors == []


@pytest.mark.filterwarnings('ignore:websockets')
def test_interactive_inputs_serve_independently():
    """Each of several interactive inputs serves its requests at once,
    whether or not the others are ever requested.
    """
    first_plugin, _ = _make_http_input_plugin(plugin_id=1)
    second_plugin, second_port = _make_http_input_plugin(plugin_id=2)
    output_plugin = _make_mock_output_plugin()

    executor = Executor(
        input=[first_plugin, second_plugin],
        event=_make_mock_event_plugin(),
        output=[output_plugin],
        params=_make_params(live_mode=True),
    )
    thread, errors = _start_execution(executor)

    try:
        # The second server is up with no request to the first
        _wait_until_serving(second_plugin)
        rq.post(
            f'http://{HOST}:{second_port}/generate',
            json={'count': 3},
            timeout=EXECUTE_TIMEOUT,
        )

        deadline = time.monotonic() + EXECUTE_TIMEOUT
        while (
            sum(len(c.args[0]) for c in output_plugin.write.await_args_list)
            < 3
        ):
            assert time.monotonic() < deadline
            time.sleep(0.01)

        executor.request_stop()
        thread.join(timeout=EXECUTE_TIMEOUT)
    finally:
        first_plugin.stop_interacting()
        second_plugin.stop_interacting()

    assert not thread.is_alive()
    assert errors == []
