"""Integration tests for the full pipeline (Executor with real queues)."""

import time
from collections.abc import Iterator
from pathlib import Path
from threading import Thread
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from numpy.typing import NDArray

from eventum.core.executor import ExecutionError, Executor
from eventum.core.parameters import GeneratorParameters
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
