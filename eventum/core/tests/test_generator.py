"""Tests for Generator lifecycle."""

import time
from pathlib import Path
from threading import Event, Timer
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
    gen.stop()  # should not raise


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


def test_join_when_no_thread():
    gen = Generator(params=_make_params())
    gen.join()  # should not raise
