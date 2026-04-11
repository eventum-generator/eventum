"""Tests for Executor."""

import queue as queue_mod
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from eventum.core.executor import ExecutionError, Executor
from eventum.core.parameters import GeneratorParameters


def _make_params(**overrides) -> GeneratorParameters:
    defaults: dict = {
        'id': 'test',
        'path': Path('/tmp/config.yml'),
        'live_mode': False,
    }
    defaults.update(overrides)
    return GeneratorParameters(**defaults)


def _make_mock_input_plugin(plugin_id=1, tags=('default',)):
    """Create a mock InputPlugin."""
    plugin = MagicMock()
    plugin.id = plugin_id
    plugin.config.tags = tags
    plugin.is_interactive = False
    plugin.generate = MagicMock(return_value=iter([]))
    return plugin


def _make_mock_event_plugin():
    """Create a mock EventPlugin."""
    return MagicMock()


def _make_mock_output_plugin():
    """Create a mock OutputPlugin."""
    plugin = MagicMock()
    plugin.open = AsyncMock()
    plugin.close = AsyncMock()
    plugin.write = AsyncMock(return_value=0)
    plugin.__str__ = MagicMock(return_value='<mock output>')
    return plugin


# - Constructor validation ------------------------------------------------


def test_empty_input_raises():
    """Executor rejects empty input plugin list."""
    with pytest.raises(ValueError, match='input'):
        Executor(
            input=[],
            event=_make_mock_event_plugin(),
            output=[_make_mock_output_plugin()],
            params=_make_params(),
        )


def test_empty_output_raises():
    """Executor rejects empty output plugin list."""
    with pytest.raises(ValueError, match='output'):
        Executor(
            input=[_make_mock_input_plugin()],
            event=_make_mock_event_plugin(),
            output=[],
            params=_make_params(),
        )


def test_valid_construction():
    """Executor constructs successfully with valid arguments."""
    executor = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(),
    )
    assert executor._execution_error is None


# - execute() -------------------------------------------------------------


def test_execute_happy_path():
    """All three stages run and complete without error."""
    executor = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(),
    )

    # Replace stage runners with controlled versions that close queues.
    # PipelineQueue.get() calls task_done() internally, so no manual
    # task_done() calls are needed.
    def mock_input_stage():
        executor._timestamps_queue.close()

    def mock_event_stage():
        while executor._timestamps_queue.get() is not None:
            pass
        executor._events_queue.close()

    def mock_output_stage():
        while executor._events_queue.get() is not None:
            pass

    executor._run_input_stage = mock_input_stage
    executor._run_event_stage = mock_event_stage
    executor._run_output_stage = mock_output_stage

    executor.execute()  # should not raise


def test_execute_output_error_reraised():
    """ExecutionError from output stage is captured and re-raised."""
    executor = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(),
    )

    def mock_input_stage():
        executor._timestamps_queue.close()

    def mock_event_stage():
        while executor._timestamps_queue.get() is not None:
            pass
        executor._events_queue.close()

    def mock_output_stage():
        while executor._events_queue.get() is not None:
            pass
        executor._execution_error = ExecutionError(
            'output failed',
            context={'reason': 'test'},
        )

    executor._run_input_stage = mock_input_stage
    executor._run_event_stage = mock_event_stage
    executor._run_output_stage = mock_output_stage

    with pytest.raises(ExecutionError, match='output failed'):
        executor.execute()


def test_execute_unexpected_output_error_aborts_upstream():
    """Unexpected exception in output stage aborts upstream stages.

    Regression: _run_output_stage only caught ExecutionError, leaving
    upstream stages hanging when an unexpected exception occurred.
    """
    executor = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(),
    )

    def mock_input_stage():
        executor._timestamps_queue.close()

    def mock_event_stage():
        try:
            while executor._timestamps_queue.get() is not None:
                pass
            executor._events_queue.close()
        except queue_mod.ShutDown:
            pass

    # Replace _execute_output_stage with an async function that raises
    # a non-ExecutionError exception. The real _run_output_stage should
    # catch it and call _abort_upstream() to unblock the other stages.
    async def broken_execute():
        raise RuntimeError('unexpected crash')

    executor._run_input_stage = mock_input_stage
    executor._run_event_stage = mock_event_stage
    executor._execute_output_stage = broken_execute

    # Should complete without hanging (abort_upstream cleans up queues)
    executor.execute()
    # No ExecutionError raised (RuntimeError is logged, not re-raised)
    assert executor._execution_error is None


def test_abort_upstream_shuts_down_queues():
    """_abort_upstream shuts down both queues and sets stop event."""
    executor = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(),
    )

    executor._abort_upstream()

    assert executor._stop_event.is_set()

    with pytest.raises(queue_mod.ShutDown):
        executor._events_queue.put(['event'])

    with pytest.raises(queue_mod.ShutDown):
        executor._timestamps_queue.put(MagicMock())


# - request_stop() --------------------------------------------------------


def test_request_stop_sets_event():
    """request_stop() sets the stop event."""
    executor = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(),
    )
    assert not executor._stop_event.is_set()
    executor.request_stop()
    assert executor._stop_event.is_set()


def test_request_stop_idempotent():
    """Calling request_stop() twice does not raise."""
    executor = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(),
    )
    executor.request_stop()
    executor.request_stop()  # second call should not raise
    assert executor._stop_event.is_set()


def test_request_stop_calls_stop_interactive():
    """request_stop() calls stop_interacting() on interactive plugins."""
    p1 = _make_mock_input_plugin()
    p1.is_interactive = True
    p2 = _make_mock_input_plugin(plugin_id=2)
    p2.is_interactive = False

    executor = Executor(
        input=[p1, p2],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(),
    )
    executor.request_stop()

    p1.stop_interacting.assert_called_once()
    p2.stop_interacting.assert_not_called()


# - Configuration ---------------------------------------------------------


def test_queue_sizes_from_params():
    """Queue maxsizes are set from params."""
    params = _make_params(
        queue={'max_timestamp_batches': 5, 'max_event_batches': 3},
    )
    executor = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=params,
    )
    assert executor._timestamps_queue._queue.maxsize == 5
    assert executor._events_queue._queue.maxsize == 3


def test_skip_past_computed():
    """skip_past is True only when live_mode and skip_past are both True."""
    executor_live = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(live_mode=True, skip_past=True),
    )
    assert executor_live._skip_past is True

    executor_sample = Executor(
        input=[_make_mock_input_plugin()],
        event=_make_mock_event_plugin(),
        output=[_make_mock_output_plugin()],
        params=_make_params(live_mode=False, skip_past=True),
    )
    assert executor_sample._skip_past is False
