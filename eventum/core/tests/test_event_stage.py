"""Tests for EventStage."""

import queue as queue_mod
import threading
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from eventum.core.parameters import GeneratorParameters
from eventum.core.queue import PipelineQueue
from eventum.core.stages.event_stage import EventStage
from eventum.plugins.event.exceptions import (
    PluginEventsExhaustedError,
    PluginProduceError,
)
from eventum.plugins.input.protocols import IdentifiedTimestamps


def _make_timestamps(
    count: int = 5,
    plugin_id: int = 1,
) -> IdentifiedTimestamps:
    """Create a test IdentifiedTimestamps array."""
    ts = np.empty(
        count,
        dtype=[('timestamp', 'datetime64[us]'), ('id', 'uint16')],
    )
    ts['timestamp'] = np.datetime64('2025-01-01T00:00:00', 'us')
    ts['id'] = plugin_id
    return ts


def _make_params(**overrides) -> GeneratorParameters:
    defaults: dict = {
        'id': 'test',
        'path': Path('/tmp/config.yml'),
        'live_mode': False,
    }
    defaults.update(overrides)
    return GeneratorParameters(**defaults)


def _make_event_stage(
    plugin=None,
    input_tags=None,
    params=None,
) -> EventStage:
    """Factory for EventStage with sensible defaults."""
    if plugin is None:
        plugin = MagicMock()
        plugin.produce.return_value = ['event1']
    if input_tags is None:
        input_tags = {1: ('tag1',)}
    if params is None:
        params = _make_params()
    return EventStage(
        plugin=plugin,
        input_tags=input_tags,
        params=params,
    )


def _collect_output(output_q: PipelineQueue) -> list:
    """Drain all items from output queue until sentinel."""
    results = []
    while True:
        item = output_q.get()
        if item is None:
            break
        results.append(item)
    return results


def _feed_and_close(input_q: PipelineQueue, batches: list) -> None:
    """Put batches into input queue then close it."""
    for batch in batches:
        input_q.put(batch)
    input_q.close()


# - Normal flow -------------------------------------------------------


def test_execute_normal_flow():
    """Timestamps in, events out, sentinel propagation."""
    plugin = MagicMock()
    plugin.produce.return_value = ['event1']

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    # Feed input from a thread
    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=3, plugin_id=1)]),
    ).start()

    # Run stage in a thread (it blocks on output.close)
    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    # Consume output on main thread
    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 1
    assert batches[0] == ['event1', 'event1', 'event1']


def test_execute_multiple_batches():
    """Multiple timestamp batches produce multiple event batches."""
    plugin = MagicMock()
    plugin.produce.return_value = ['ev']

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=2), _make_timestamps(count=3)]),
    ).start()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 3


def test_execute_plugin_returns_multiple_events():
    """Plugin.produce() returning multiple events per timestamp."""
    plugin = MagicMock()
    plugin.produce.return_value = ['ev1', 'ev2']

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=2)]),
    ).start()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 1
    assert len(batches[0]) == 4  # 2 timestamps * 2 events each


def test_execute_uses_correct_tags():
    """input_tags[id] is passed to plugin.produce as tags."""
    plugin = MagicMock()
    produced_tags: list[tuple[str, ...]] = []

    def capture_produce(params):
        produced_tags.append(params['tags'])
        return ['ev']

    plugin.produce.side_effect = capture_produce

    stage = _make_event_stage(
        plugin=plugin,
        input_tags={1: ('web', 'prod'), 2: ('db',)},
    )
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=1, plugin_id=1)]),
    ).start()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert produced_tags[0] == ('web', 'prod')


# - Error handling ----------------------------------------------------


def test_execute_produce_error_skips_and_continues():
    """PluginProduceError for one timestamp skips it, continues others."""
    plugin = MagicMock()
    call_count = 0

    def produce_with_error(params):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise PluginProduceError(
                'bad event',
                context={'reason': 'test'},
            )
        return ['ev']

    plugin.produce.side_effect = produce_with_error

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=3)]),
    ).start()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 1
    assert len(batches[0]) == 2  # 3 timestamps, 1 errored


def test_execute_unexpected_error_skips_and_continues():
    """Generic exception for one timestamp is handled like ProduceError."""
    plugin = MagicMock()
    call_count = 0

    def produce_with_error(params):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError('unexpected')
        return ['ev']

    plugin.produce.side_effect = produce_with_error

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=3)]),
    ).start()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 1
    assert len(batches[0]) == 2  # first one errored


def test_execute_exhausted_error_shuts_down_input():
    """PluginEventsExhaustedError shuts down input queue and closes output."""
    plugin = MagicMock()
    call_count = 0

    def produce_exhausting(params):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise PluginEventsExhaustedError()
        return ['ev']

    plugin.produce.side_effect = produce_exhausting

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    # Put data but don't close - stage should shutdown() the input
    input_q.put(_make_timestamps(count=3))

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 1
    assert len(batches[0]) == 1  # only 1st timestamp before exhaustion

    # input_q is shut down so put raises ShutDown
    with pytest.raises(queue_mod.ShutDown):
        input_q.put(_make_timestamps(count=1))


def test_execute_all_produce_fail_empty_batch():
    """If all produce calls fail, no events put to output."""
    plugin = MagicMock()
    plugin.produce.side_effect = PluginProduceError(
        'fail',
        context={'reason': 'test'},
    )

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=3)]),
    ).start()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 0  # no events produced


def test_execute_empty_input():
    """Input queue immediately closed leads to output immediately closed."""
    plugin = MagicMock()
    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(target=input_q.close).start()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 0
    plugin.produce.assert_not_called()


def test_execute_always_closes_output():
    """output.close() is called regardless of execution path."""
    plugin = MagicMock()
    plugin.produce.return_value = ['ev']

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=2)]),
    ).start()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    # Drain events then verify sentinel (proof that close was called)
    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 1  # one batch of events was produced


# - Shutdown resilience -----------------------------------------------


def test_execute_closes_output_on_input_shutdown():
    """output.close() is called even when input queue is shut down.

    Regression: without try-finally, queue.ShutDown from input.get()
    would bypass output.close(), leaving the output stage hanging.
    """
    plugin = MagicMock()
    plugin.produce.return_value = ['ev']

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    # Put data then immediately shutdown (simulates upstream failure)
    input_q.put(_make_timestamps(count=1))
    input_q.shutdown()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    # If output.close() was NOT called, this would hang forever
    result = output_q.get()
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    # Output got sentinel (None) proving close() was called
    assert result is None


def test_execute_closes_output_on_output_queue_shutdown():
    """output.close() is called even when output queue is shut down.

    Regression: output.put() raises queue.ShutDown, but output.close()
    must still be called (which is now safe thanks to close() resilience).
    """
    plugin = MagicMock()
    plugin.produce.return_value = ['ev']

    stage = _make_event_stage(plugin=plugin)
    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    # Feed timestamps from a thread
    feeder = threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=1)]),
    )
    feeder.start()

    # Shut down the output queue before the stage can write
    output_q.shutdown()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    # Stage should finish without hanging (close() handles ShutDown)
    stage_thread.join(timeout=5)
    assert not stage_thread.is_alive()

    # Unblock the feeder thread — stage exited via ShutDown without
    # consuming the sentinel, so _feed_and_close is stuck on join().
    input_q.shutdown()
    feeder.join(timeout=5)
    assert not feeder.is_alive()


def test_execute_fatal_error_shuts_down_input():
    """Fatal error in event loop shuts down input queue.

    Regression: when the event stage crashed with an unexpected exception
    outside the per-timestamp try-except (e.g. in astype or input_tags
    lookup), it closed the output queue but did NOT shut down the input
    queue. If the input stage was blocked on put() (queue full), it would
    hang forever, deadlocking the entire pipeline.
    """
    plugin = MagicMock()
    plugin.produce.return_value = ['ev']

    # Use an input_tags map that is MISSING the plugin id to trigger
    # a KeyError in the outer loop (outside the inner try-except).
    stage = _make_event_stage(plugin=plugin, input_tags={})

    input_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)
    output_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    # Feed timestamps with plugin_id=1, but input_tags has no key 1
    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [_make_timestamps(count=1, plugin_id=1)]),
    ).start()

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'input': input_q, 'output': output_q},
    )
    stage_thread.start()

    # Output should still be closed (sentinel received)
    result = output_q.get()
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert result is None  # sentinel proves output.close() was called

    # Input queue should be shut down so put raises ShutDown
    with pytest.raises(queue_mod.ShutDown):
        input_q.put(_make_timestamps(count=1))
