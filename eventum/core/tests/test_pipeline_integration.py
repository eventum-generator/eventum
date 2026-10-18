"""Integration tests for the full pipeline (Executor with real queues)."""

import asyncio
import os
import socket
import subprocess
import sys
import textwrap
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


# - Bounded stop ----------------------------------------------------------

STOP_TIMEOUT = 1
ABORT_TIMEOUT = 0.5
STOP_BOUND = 4.0
"""Seconds any stop below is expected to end within: the graceful
timeout and the abort window with a margin for slow machines."""

SAFETY_RELEASE = 20.0
"""Seconds after which a plugin made to hang is released anyway, so a
regression shows as a failed test rather than a hung suite."""

no_thread_errors = pytest.mark.filterwarnings(
    'error::pytest.PytestUnhandledThreadExceptionWarning',
)


@pytest.fixture
def short_abort(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('eventum.core.executor.ABORT_TIMEOUT', ABORT_TIMEOUT)
    monkeypatch.setattr(
        'eventum.core.executor.ABORT_CLOSE_TIMEOUT',
        ABORT_TIMEOUT / 2,
    )


def _make_stoppable_params(**overrides) -> GeneratorParameters:
    return _make_params(stop_timeout=STOP_TIMEOUT, **overrides)


def _make_endless_input_plugin():
    """Input plugin yielding one-timestamp batches until stopped."""
    plugin = _make_mock_input_plugin()
    base = np.datetime64('2020-01-01T00:00:00', 'us')

    def generate(size, *, skip_past=True) -> Iterator[NDArray[np.datetime64]]:
        while True:
            yield np.array([base], dtype='datetime64[us]')

    plugin.generate = generate
    return plugin


def _make_hanging_output_plugin(
    *,
    on: str,
) -> tuple[MagicMock, asyncio.Event, threading.Event]:
    """Output plugin whose `on` method waits until cancelled.

    Returns the plugin, a flag set once the method was cancelled and a
    flag set once it was entered.
    """
    plugin = _make_mock_output_plugin()
    cancelled = asyncio.Event()
    entered = threading.Event()

    async def hang(*_args) -> int:
        entered.set()
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return 0

    setattr(plugin, on, AsyncMock(side_effect=hang))
    return plugin, cancelled, entered


def _make_blocking_event_plugin() -> tuple[
    MagicMock,
    threading.Event,
    threading.Event,
]:
    """Event plugin whose produce never returns until released.

    Returns the plugin, its release and a flag set once produce was
    entered. The release is armed after `SAFETY_RELEASE` seconds in any
    case.
    """
    release = threading.Event()
    entered = threading.Event()
    timer = threading.Timer(SAFETY_RELEASE, release.set)
    timer.daemon = True
    timer.start()

    def produce(_params: object) -> list[str]:
        entered.set()
        release.wait()
        return []

    plugin = MagicMock()
    plugin.produce = produce
    return plugin, release, entered


def _wait(event: threading.Event) -> None:
    assert event.wait(EXECUTE_TIMEOUT), 'the plugin was never reached'


def _make_executor(**kwargs) -> Executor:
    defaults: dict = {
        'input': [_make_endless_input_plugin()],
        'event': _make_mock_event_plugin(),
        'output': [_make_mock_output_plugin()],
        'params': _make_stoppable_params(),
    }
    defaults.update(kwargs)
    return Executor(**defaults)


def _stop_and_measure(executor: Executor) -> tuple[bool, float]:
    started = time.monotonic()
    stopped = executor.stop()
    return stopped, time.monotonic() - started


@no_thread_errors
def test_stop_ends_healthy_pipeline_gracefully(short_abort):
    """A pipeline that drains in time is stopped without an abort."""
    output_plugin = _make_mock_output_plugin()
    executor = _make_executor(output=[output_plugin])
    thread, errors = _start_execution(executor)

    stopped, elapsed = _stop_and_measure(executor)
    thread.join(EXECUTE_TIMEOUT)

    assert stopped is True
    assert elapsed < STOP_TIMEOUT
    assert executor._is_aborted is False
    assert executor.discarded_events == 0
    assert not thread.is_alive()
    assert errors == []
    output_plugin.close.assert_awaited_once()


@no_thread_errors
def test_stop_aborts_drain_of_hanging_writes(short_abort):
    """Writes that never complete do not hold back the stop.

    Regression for #308: with ordered writes, the stop waited for
    every queued batch to time out in turn.
    """
    output_plugin, _, entered = _make_hanging_output_plugin(on='write')
    executor = _make_executor(
        output=[output_plugin],
        params=_make_stoppable_params(
            keep_order=True,
            write_timeout=3600,
            batch={'size': 1},
        ),
    )
    thread, errors = _start_execution(executor)
    _wait(entered)

    stopped, elapsed = _stop_and_measure(executor)
    thread.join(EXECUTE_TIMEOUT)

    assert stopped is True
    assert executor._is_aborted is True
    assert elapsed < STOP_BOUND
    assert not thread.is_alive()
    assert errors == []
    output_plugin.close.assert_awaited_once()

    # what waited in the queue behind the stuck write is accounted for
    assert executor.discarded_events > 0


@no_thread_errors
def test_stop_cancels_hanging_writes_without_order(short_abort):
    """Concurrent writes in progress are canceled on abort."""
    output_plugin, cancelled, entered = _make_hanging_output_plugin(
        on='write',
    )
    executor = _make_executor(
        output=[output_plugin],
        params=_make_stoppable_params(write_timeout=3600),
    )
    thread, errors = _start_execution(executor)
    _wait(entered)

    stopped, _ = _stop_and_measure(executor)
    thread.join(EXECUTE_TIMEOUT)

    assert stopped is True
    assert executor._is_aborted is True
    assert cancelled.is_set()
    assert errors == []


@no_thread_errors
def test_stop_aborts_hanging_open(short_abort):
    """An output plugin that never opens is canceled by the abort."""
    output_plugin, cancelled, entered = _make_hanging_output_plugin(
        on='open',
    )
    executor = _make_executor(output=[output_plugin])
    thread, errors = _start_execution(executor)
    _wait(entered)

    stopped, elapsed = _stop_and_measure(executor)
    thread.join(EXECUTE_TIMEOUT)

    assert stopped is True
    assert elapsed < STOP_BOUND
    assert cancelled.is_set()
    assert errors == []


@no_thread_errors
def test_stop_bounds_close_of_aborted_output(short_abort):
    """Closing output plugins of an aborted execution is bounded."""
    output_plugin, cancelled, _ = _make_hanging_output_plugin(on='close')
    writing, _, entered = _make_hanging_output_plugin(on='write')
    output_plugin.write = writing.write
    executor = _make_executor(
        output=[output_plugin],
        params=_make_stoppable_params(keep_order=True, write_timeout=3600),
    )
    thread, errors = _start_execution(executor)
    _wait(entered)

    stopped, elapsed = _stop_and_measure(executor)
    thread.join(EXECUTE_TIMEOUT)

    assert stopped is True
    assert executor._is_aborted is True
    assert elapsed < STOP_BOUND
    assert cancelled.is_set()
    assert errors == []


@no_thread_errors
def test_stop_interrupts_hanging_graceful_close(short_abort):
    """A close that hangs on a graceful stop is canceled by the abort."""
    output_plugin, cancelled, _ = _make_hanging_output_plugin(on='close')
    executor = _make_executor(
        input=[_make_mock_input_plugin()],
        output=[output_plugin],
    )
    thread, errors = _start_execution(executor)

    # The finite input ends on its own and the stage starts closing
    deadline = time.monotonic() + EXECUTE_TIMEOUT
    while not output_plugin.close.await_count:
        assert time.monotonic() < deadline
        time.sleep(0.01)

    stopped, elapsed = _stop_and_measure(executor)
    thread.join(EXECUTE_TIMEOUT)

    assert stopped is True
    assert elapsed < STOP_BOUND
    assert cancelled.is_set()
    assert errors == []


@no_thread_errors
def test_stop_leaves_output_calls_that_never_return(short_abort):
    """Plugin calls stuck in every worker thread do not keep the output
    stage from ending once aborted, nor from logging on its way out.
    """
    release = threading.Event()
    timer = threading.Timer(SAFETY_RELEASE, release.set)
    timer.daemon = True
    timer.start()

    stuck = threading.Semaphore(0)

    def block() -> None:
        stuck.release()
        release.wait()

    async def write(events) -> int:
        await asyncio.to_thread(block)
        return len(events)

    output_plugin = _make_mock_output_plugin()
    output_plugin.write = AsyncMock(side_effect=write)
    executor = _make_executor(
        output=[output_plugin],
        params=_make_stoppable_params(write_timeout=3600),
    )
    thread, errors = _start_execution(executor)

    # every worker the pool may have is taken, the default size of a
    # thread pool
    for _ in range(min(32, (os.cpu_count() or 1) + 4)):
        assert stuck.acquire(timeout=EXECUTE_TIMEOUT)

    try:
        stopped, elapsed = _stop_and_measure(executor)
        thread.join(EXECUTE_TIMEOUT)

        assert stopped is True
        assert executor._is_aborted is True
        assert elapsed < STOP_BOUND
        assert errors == []
    finally:
        release.set()


@no_thread_errors
def test_stop_abandons_stuck_event_plugin(short_abort):
    """A plugin that never returns leaves the stop reporting failure
    within bounded time instead of hanging the caller.
    """
    event_plugin, release, entered = _make_blocking_event_plugin()
    executor = _make_executor(event=event_plugin)
    thread, _ = _start_execution(executor)
    _wait(entered)

    try:
        stopped, elapsed = _stop_and_measure(executor)
        assert stopped is False
        assert elapsed < STOP_BOUND
        assert not executor._done_event.is_set()

        # Already aborted, so the graceful timeout is not waited again
        stopped, elapsed = _stop_and_measure(executor)
        assert stopped is False
        assert elapsed < STOP_TIMEOUT + ABORT_TIMEOUT
    finally:
        release.set()

    thread.join(EXECUTE_TIMEOUT)
    assert not thread.is_alive()
    assert executor._done_event.is_set()


def test_abort_cancels_output_before_shutting_queues(
    monkeypatch: pytest.MonkeyPatch,
):
    """The output stage learns of an abort from the cancellation, so
    it closes its plugins in full rather than having the cancellation
    cut into a close it began on seeing its queue shut down.
    """
    monkeypatch.setattr('eventum.core.executor.ABORT_TIMEOUT', 3)
    event_plugin, release, entered = _make_blocking_event_plugin()
    closed = threading.Event()

    async def close() -> None:
        await asyncio.sleep(0.3)
        closed.set()

    output_plugin = _make_mock_output_plugin()
    output_plugin.close = AsyncMock(side_effect=close)
    executor = _make_executor(event=event_plugin, output=[output_plugin])

    # widens the gap between the queues shutting down and anything
    # scheduled after it
    abort_upstream = executor._abort_upstream

    def slow_abort_upstream() -> None:
        abort_upstream()
        time.sleep(0.1)

    monkeypatch.setattr(executor, '_abort_upstream', slow_abort_upstream)
    thread, _ = _start_execution(executor)
    _wait(entered)

    try:
        executor.abort()
        assert closed.wait(EXECUTE_TIMEOUT)
    finally:
        release.set()

    thread.join(EXECUTE_TIMEOUT)


@no_thread_errors
def test_abort_before_execution_ends_it_at_once(short_abort):
    """An execution aborted before it starts opens no output."""
    output_plugin = _make_mock_output_plugin()
    executor = _make_executor(output=[output_plugin])

    executor.abort()
    executor.abort()  # idempotent
    thread, errors = _start_execution(executor)
    thread.join(EXECUTE_TIMEOUT)

    assert not thread.is_alive()
    assert errors == []
    output_plugin.open.assert_not_awaited()


def test_abort_after_execution_ended_does_not_fail():
    """An abort racing the end of execution meets a closed loop."""
    executor = _make_executor(input=[_make_mock_input_plugin()])
    executor.execute()

    executor.abort()

    assert executor._is_aborted is True


def test_stop_of_ended_execution_returns_at_once():
    """A stop of an execution that has ended does not wait."""
    executor = _make_executor(input=[_make_mock_input_plugin()])
    executor.execute()

    stopped, elapsed = _stop_and_measure(executor)

    assert stopped is True
    assert elapsed < STOP_TIMEOUT


def test_stage_threads_are_daemon():
    """Stage threads do not keep the process from exiting, as a stuck
    one is abandoned rather than joined.
    """
    executor = _make_executor(input=[_make_mock_input_plugin()])

    threads = executor._start_pipeline()
    executor._await_pipeline(threads)

    assert all(t.daemon for t in threads)


def test_abort_counts_events_waiting_in_queue():
    """Events of every batch the abort takes out of the queue are
    counted, each of them once.
    """
    executor = _make_executor()
    for batch in (['a', 'b'], ['c', 'd', 'e'], ['f']):
        executor._events_queue.put(batch)

    executor.abort()
    executor.abort()

    assert executor.discarded_events == 6


def _run_script(path: Path, source: str) -> subprocess.CompletedProcess:
    path.write_text(textwrap.dedent(source))
    return subprocess.run(  # noqa: S603
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        timeout=EXECUTE_TIMEOUT * 2,
        check=False,
    )


def test_abandoned_generator_does_not_keep_process_alive(tmp_path: Path):
    """A process exits although its generator is stuck in plugin code.

    Regression for #308: the threads of a generator were not daemon,
    so the interpreter waited for them at exit and only a kill ended
    it. The generator is driven the way the application drives it,
    from a thread that is not daemon itself.
    """
    entered = tmp_path / 'entered'
    (tmp_path / 'produce.py').write_text(
        'import threading\n'
        'from pathlib import Path\n'
        'def produce(params):\n'
        f'    Path({str(entered)!r}).touch()\n'
        '    threading.Event().wait()\n',
    )
    (tmp_path / 'generator.yml').write_text(
        'input:\n'
        '  - linspace:\n'
        '      start: "2025-01-01 00:00:00"\n'
        '      end: "2025-01-01 01:00:00"\n'
        '      count: 10\n'
        'event:\n'
        '  script:\n'
        '    path: produce.py\n'
        'output:\n'
        '  - stdout:\n'
        '      stream: stderr\n'
    )

    result = _run_script(
        tmp_path / 'stuck.py',
        f"""
        import time
        from pathlib import Path

        import eventum.core.executor as executor_module
        from eventum.core.generator import Generator
        from eventum.core.parameters import GeneratorParameters

        executor_module.ABORT_TIMEOUT = 0.5

        generator = Generator(
            GeneratorParameters(
                id='stuck',
                path=Path({str(tmp_path / 'generator.yml')!r}),
                live_mode=False,
                skip_past=False,
                stop_timeout=1,
            ),
        )
        assert generator.start()

        entered = Path({str(entered)!r})
        deadline = time.monotonic() + 10
        while not entered.exists():
            assert time.monotonic() < deadline
            time.sleep(0.01)

        assert generator.stop() is False
        assert generator.is_abandoned
        print('abandoned', flush=True)
        """,
    )

    assert result.returncode == 0, result.stderr
    assert 'abandoned' in result.stdout
