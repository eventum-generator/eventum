"""Tests for Generator lifecycle."""

import time
from pathlib import Path
from threading import Event, Thread, Timer
from unittest.mock import MagicMock, patch

import pytest

from eventum.core.config_loader import ConfigurationLoadError
from eventum.core.executor import ImproperlyConfiguredError
from eventum.core.generator import Generator
from eventum.core.parameters import GeneratorParameters
from eventum.core.plugins_initializer import InitializationError


def _make_params(**overrides):
    defaults = {'id': 'test-gen', 'path': Path('/tmp/config.yml')}
    defaults.update(overrides)
    return GeneratorParameters(**defaults)


# --- Initial state ---


def test_initial_state():
    gen = Generator(params=_make_params())
    assert gen.is_running is False
    assert gen.is_initializing is False
    assert gen.is_ended_up is False
    assert gen.is_stopping is False
    assert gen.start_time is None


def test_params_property():
    params = _make_params()
    gen = Generator(params=params)
    assert gen.params is params


def test_get_plugins_info_before_start():
    gen = Generator(params=_make_params())
    with pytest.raises(RuntimeError, match='No information about plugins'):
        gen.get_plugins_info()


def test_get_config_before_start():
    gen = Generator(params=_make_params())
    with pytest.raises(RuntimeError, match='No information about config'):
        gen.get_config()


# --- start failure cases ---


@patch('eventum.core.generator.load')
def test_start_config_load_error(mock_load):
    mock_load.side_effect = ConfigurationLoadError(
        'bad config',
        context={'reason': 'test'},
    )
    gen = Generator(params=_make_params())
    result = gen.start()
    assert result is False
    assert gen.is_running is False


@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_start_init_plugins_error(mock_load, mock_init):
    mock_load.return_value = MagicMock()
    mock_init.side_effect = InitializationError(
        'init failed',
        context={'reason': 'test'},
    )
    gen = Generator(params=_make_params())
    result = gen.start()
    assert result is False
    assert gen.is_running is False


@patch('eventum.core.generator.Executor')
@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_start_executor_init_error(mock_load, mock_init, mock_executor_cls):
    mock_load.return_value = MagicMock()
    mock_init.return_value = MagicMock()
    mock_executor_cls.side_effect = ImproperlyConfiguredError(
        'bad executor',
        context={'reason': 'test'},
    )
    gen = Generator(params=_make_params())
    result = gen.start()
    assert result is False
    assert gen.is_running is False


# --- successful start ---


@patch('eventum.core.generator.Executor')
@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_start_success(mock_load, mock_init, mock_executor_cls):
    mock_load.return_value = MagicMock()
    mock_init.return_value = MagicMock()

    block_event = Event()
    mock_executor = MagicMock()
    mock_executor.execute.side_effect = lambda: block_event.wait()
    mock_executor_cls.return_value = mock_executor

    gen = Generator(params=_make_params())
    result = gen.start()
    assert result is True
    assert gen.is_running is True
    assert gen.start_time is not None

    block_event.set()
    gen.join()
    assert gen.is_ended_up is True
    assert gen.is_ended_up_successfully is True


# --- stop / join edge cases ---


def test_stop_when_not_running():
    gen = Generator(params=_make_params())
    assert gen.stop() is True


@patch('eventum.core.generator.Executor')
@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_stop_while_execution_ends(mock_load, mock_init, mock_executor_cls):
    """Stop does not fail on an executor the ending thread released."""
    mock_load.return_value = MagicMock()
    mock_init.return_value = MagicMock()

    block_event = Event()
    mock_executor = MagicMock()
    mock_executor.execute.side_effect = lambda: block_event.wait()
    mock_executor_cls.return_value = mock_executor

    gen = Generator(params=_make_params())
    gen.start()

    # The thread has released its runtime and is about to end
    gen._executor = None
    Timer(0.1, block_event.set).start()

    gen.stop()

    assert gen.is_ended_up is True


@patch('eventum.core.generator.collect_network_usage')
@patch('eventum.core.generator.collect_thread_usage')
def test_get_resources_while_execution_ends(mock_usage, mock_network):
    """Resources are reported for an executor released meanwhile."""
    gen = Generator(params=_make_params())
    executor = MagicMock()
    gen._executor = executor
    gen._network_baseline = MagicMock(sent_bytes=0, received_bytes=0)
    mock_network.return_value = gen._network_baseline

    def release(*args):
        gen._executor = None
        return MagicMock(
            count=1,
            cpu_seconds=0.0,
            run_delay_seconds=0.0,
            disk_read_bytes=0,
            disk_written_bytes=0,
        )

    mock_usage.side_effect = release

    gen.get_resources()

    executor.queue_usage.assert_called_once()


@patch('eventum.core.generator.Executor')
@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_stop_joins_once_execution_ends(
    mock_load,
    mock_init,
    mock_executor_cls,
):
    """Stop leaves bounding to the executor and joins once the
    execution has ended.
    """
    mock_load.return_value = MagicMock()
    mock_init.return_value = MagicMock()

    block_event = Event()
    mock_executor = MagicMock()
    mock_executor.execute.side_effect = lambda: block_event.wait()

    def stop():
        block_event.set()
        return True

    mock_executor.stop.side_effect = stop
    mock_executor_cls.return_value = mock_executor

    gen = Generator(params=_make_params())
    gen.start()

    assert gen.stop() is True
    mock_executor.stop.assert_called_once_with()
    assert gen.is_ended_up is True
    assert gen.is_stopping is False
    assert gen.is_abandoned is False


@patch('eventum.core.generator.Executor')
@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_stop_abandons_execution_that_does_not_stop(
    mock_load,
    mock_init,
    mock_executor_cls,
):
    """A stop that the execution does not obey returns instead of
    hanging, and leaves the generator usable for another attempt.
    """
    mock_load.return_value = MagicMock()
    mock_init.return_value = MagicMock()

    block_event = Event()
    safety = Timer(20, block_event.set)
    safety.daemon = True
    safety.start()

    mock_executor = MagicMock()
    mock_executor.execute.side_effect = lambda: block_event.wait()
    mock_executor.stop.return_value = False
    mock_executor_cls.return_value = mock_executor

    gen = Generator(params=_make_params())
    gen.start()

    try:
        assert gen.stop() is False
        assert gen.is_abandoned is True
        assert gen.is_running is True
        assert gen.is_stopping is False

        # a stuck generator keeps reporting what its threads consume
        assert gen._thread.name == 'generator:test-gen'

        # the lock is released, so another stop is not blocked
        assert gen._lock.acquire(blocking=False) is True
        gen._lock.release()
        assert gen.stop() is False

        # an abandoned execution is not reported as running fine
        assert gen.start() is False
        mock_executor.execute.assert_called_once()
    finally:
        block_event.set()
        gen.join()

    # once the execution does end, the generator can start again, and
    # the new execution is not taken for the abandoned one
    assert gen.is_abandoned is False
    second_execution = Event()
    mock_executor.execute.side_effect = lambda: second_execution.wait()

    try:
        assert gen.start() is True
        assert gen.is_running is True
        assert gen.is_abandoned is False
        assert gen.start() is True
    finally:
        second_execution.set()
        gen.join()


@patch('eventum.core.generator.Executor')
@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_generator_thread_is_daemon(mock_load, mock_init, mock_executor_cls):
    """An abandoned generator thread does not keep the process alive."""
    mock_load.return_value = MagicMock()
    mock_init.return_value = MagicMock()
    mock_executor_cls.return_value = MagicMock()

    gen = Generator(params=_make_params())
    gen.start()
    gen.join()

    assert gen._thread is not None
    assert gen._thread.daemon is True


@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_stop_while_start_hangs_in_loading_plugins(
    mock_load,
    mock_init,
    monkeypatch,
):
    """A start stuck in plugin code holds the lock, yet the stop still
    returns once the start gives the loading up.
    """
    monkeypatch.setattr('eventum.core.executor.ABORT_TIMEOUT', 0.5)
    mock_load.return_value = MagicMock()

    release = Event()
    safety = Timer(20, release.set)
    safety.daemon = True
    safety.start()
    mock_init.side_effect = lambda **_: release.wait() and None

    gen = Generator(params=_make_params(stop_timeout=1, init_timeout=1))
    starting = Thread(target=gen.start, daemon=True)
    starting.start()

    try:
        while not gen.is_initializing:
            time.sleep(0.01)

        started = time.monotonic()
        assert gen.stop() is False
        assert time.monotonic() - started < 5  # noqa: PLR2004
        assert gen.is_stopping is False
    finally:
        release.set()
        starting.join(10)


@patch('eventum.core.generator.Executor')
@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_start_abandons_initialization_that_does_not_end(
    mock_load,
    mock_init,
    mock_executor_cls,
):
    """A start returns once the init timeout runs out, and the late
    end of the initialization does not go on to execute.
    """
    mock_load.return_value = MagicMock()
    release = Event()
    safety = Timer(20, release.set)
    safety.daemon = True
    safety.start()
    mock_init.side_effect = lambda **_: release.wait() and MagicMock()

    gen = Generator(params=_make_params(init_timeout=1))

    try:
        started = time.monotonic()
        assert gen.start() is False
        assert time.monotonic() - started < 5  # noqa: PLR2004

        assert gen.is_abandoned is True
        assert gen.is_initializing is True
        assert gen.stop() is False
        assert gen.start() is False
    finally:
        release.set()
        gen.join()

    mock_executor_cls.return_value.execute.assert_not_called()
    assert gen.is_abandoned is False
    assert gen.is_running is False

    # a later start loads in time and goes on to execute
    mock_init.side_effect = None
    mock_init.return_value = MagicMock()
    assert gen.start() is True
    gen.join()
    mock_executor_cls.return_value.execute.assert_called_once()


@patch('eventum.core.generator.Executor')
@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_stop_during_slow_loading_keeps_it_from_executing(
    mock_load,
    mock_init,
    mock_executor_cls,
):
    """A stop asked while the plugins are still loading wins over the
    start: the loading ends, and execution never begins.
    """
    mock_load.return_value = MagicMock()
    loading = Event()
    release = Event()

    def init(**_kwargs):
        loading.set()
        release.wait(20)
        return MagicMock()

    mock_init.side_effect = init

    gen = Generator(params=_make_params())
    starting = Thread(target=gen.start, daemon=True)
    starting.start()
    assert loading.wait(10)

    Timer(0.3, release.set).start()
    assert gen.stop() is True

    starting.join(10)
    gen.join()
    mock_executor_cls.return_value.execute.assert_not_called()
    assert gen.is_abandoned is False


def test_join_when_no_thread():
    gen = Generator(params=_make_params())
    gen.join()  # should not raise


def test_late_initialization_after_abandon_does_not_execute():
    gen = Generator(params=_make_params())

    assert gen._abandon_initialization() is False
    assert gen._mark_initialized(0.0) is False
    assert gen._initialized_event.is_set() is False


def test_abandon_after_initialization_keeps_the_start():
    gen = Generator(params=_make_params())

    assert gen._mark_initialized(0.0) is True
    assert gen._abandon_initialization() is True
    assert gen._is_abandoned is False


@patch('eventum.core.generator.Executor')
@patch('eventum.core.generator.init_plugins')
@patch('eventum.core.generator.load')
def test_start_disowns_threads_earlier_runs_left(
    mock_load,
    mock_init,
    mock_executor_cls,
):
    """A worker an aborted run left behind is not counted for the run
    started next under the same id.
    """
    mock_load.return_value = MagicMock()
    mock_init.return_value = MagicMock()
    mock_executor_cls.return_value = MagicMock()

    release = Event()
    left = Thread(
        target=release.wait,
        args=(20,),
        name='output-worker:test-gen:_0',
        daemon=True,
    )
    left.start()

    try:
        gen = Generator(params=_make_params())
        assert gen.start() is True
        gen.join()
    finally:
        release.set()
        left.join(5)

    assert left.name == 'abandoned:output-worker:test-gen:_0'
