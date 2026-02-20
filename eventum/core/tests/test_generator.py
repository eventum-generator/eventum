"""Tests for Generator lifecycle."""

import time
from pathlib import Path
from threading import Event
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
        'bad config', context={'reason': 'test'},
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
        'init failed', context={'reason': 'test'},
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
        'bad executor', context={'reason': 'test'},
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


def test_join_when_no_thread():
    gen = Generator(params=_make_params())
    gen.join()  # should not raise
