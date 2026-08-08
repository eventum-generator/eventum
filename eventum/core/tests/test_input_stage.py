"""Tests for InputStage."""

import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import structlog.testing

from eventum.core.parameters import BatchParameters, GeneratorParameters
from eventum.core.queue import PipelineQueue
from eventum.core.stages.input_stage import InputStage
from eventum.plugins.input.batcher import TimestampsBatcher
from eventum.plugins.input.protocols import IdentifiedTimestamps
from eventum.plugins.input.scheduler import BatchScheduler


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


def _make_mock_input_plugin(
    plugin_id: int = 1,
    is_interactive: bool = False,
    tags: tuple[str, ...] = ('default',),
):
    """Create a mock InputPlugin with required attributes."""
    plugin = MagicMock()
    plugin.id = plugin_id
    plugin.is_interactive = is_interactive
    plugin.config.tags = tags
    plugin.guid = f'guid-{plugin_id}'
    return plugin


def _make_mock_source(batches: list[IdentifiedTimestamps]):
    """Create a mock source that yields given batches from iterate()."""
    source = MagicMock()
    source.iterate.return_value = iter(batches)
    return source


def _collect_output(output_q: PipelineQueue) -> list:
    """Drain all items from output queue until sentinel."""
    results = []
    while True:
        item = output_q.get()
        if item is None:
            break
        results.append(item)
    return results


# - Properties --------------------------------------------------------


def test_input_tags_map():
    """Tags map is built from plugin configs."""
    p1 = _make_mock_input_plugin(plugin_id=1, tags=('web',))
    p2 = _make_mock_input_plugin(plugin_id=2, tags=('db', 'prod'))
    stage = InputStage(plugins=[p1, p2], params=_make_params())
    assert stage.input_tags == {1: ('web',), 2: ('db', 'prod')}


def test_plugins_property():
    """Plugins property returns the plugin list."""
    p1 = _make_mock_input_plugin()
    stage = InputStage(plugins=[p1], params=_make_params())
    assert stage.plugins == [p1]


# - Configure ---------------------------------------------------------


def test_configure_single_non_interactive():
    """configure() with one non-interactive plugin sets non-interactive source."""
    p1 = _make_mock_input_plugin(plugin_id=1, is_interactive=False)
    stage = InputStage(plugins=[p1], params=_make_params())
    stop = threading.Event()
    stage.configure(stop_event=stop)

    assert stage._configured_non_interactive is not None
    assert stage._configured_interactive is None


def test_configure_live_mode_gives_batch_size_to_scheduler():
    """Scheduler merges due batches up to the configured batch size."""
    p1 = _make_mock_input_plugin(plugin_id=1, is_interactive=False)
    stage = InputStage(
        plugins=[p1],
        params=_make_params(
            live_mode=True,
            batch=BatchParameters(size=500, delay=1.0),
        ),
    )
    stage.configure(stop_event=threading.Event())

    scheduler = stage._configured_non_interactive

    assert isinstance(scheduler, BatchScheduler)
    assert scheduler._max_batch_size == 500


def test_configure_live_mode_keeps_interactive_batches_unmerged():
    """Interactive plugins publish timestamps as they come."""
    p1 = _make_mock_input_plugin(plugin_id=1, is_interactive=True)
    stage = InputStage(
        plugins=[p1],
        params=_make_params(
            live_mode=True,
            batch=BatchParameters(size=500, delay=1.0),
        ),
    )
    stage.configure(stop_event=threading.Event())

    scheduler = stage._configured_interactive

    assert isinstance(scheduler, BatchScheduler)
    assert scheduler._max_batch_size is None


def test_configure_sample_mode_leaves_batcher_unwrapped():
    """Without live mode there is no scheduler to merge due batches."""
    p1 = _make_mock_input_plugin(plugin_id=1, is_interactive=False)
    stage = InputStage(plugins=[p1], params=_make_params(live_mode=False))
    stage.configure(stop_event=threading.Event())

    assert not isinstance(stage._configured_non_interactive, BatchScheduler)


def test_configure_sample_mode_drops_delay():
    """Sample mode delivers on no schedule, so size forms the batch."""
    p1 = _make_mock_input_plugin(plugin_id=1, is_interactive=False)
    stage = InputStage(
        plugins=[p1],
        params=_make_params(
            live_mode=False,
            batch=BatchParameters(size=500, delay=1.0),
        ),
    )
    stage.configure(stop_event=threading.Event())

    batcher = stage._configured_non_interactive

    assert isinstance(batcher, TimestampsBatcher)
    assert batcher._batch_size == 500
    assert batcher._batch_delay is None


def test_configure_sample_mode_keeps_delay_without_size():
    """Delay is the only limit of the batch when size is not set."""
    p1 = _make_mock_input_plugin(plugin_id=1, is_interactive=False)
    stage = InputStage(
        plugins=[p1],
        params=_make_params(
            live_mode=False,
            batch=BatchParameters(delay=1.0),
        ),
    )
    stage.configure(stop_event=threading.Event())

    batcher = stage._configured_non_interactive

    assert isinstance(batcher, TimestampsBatcher)
    assert batcher._batch_size is None
    assert batcher._batch_delay == 1.0


def test_configure_live_mode_keeps_delay():
    """Live mode delivers on a schedule, so delay bounds the lag."""
    p1 = _make_mock_input_plugin(plugin_id=1, is_interactive=False)
    stage = InputStage(
        plugins=[p1],
        params=_make_params(
            live_mode=True,
            batch=BatchParameters(size=500, delay=1.0),
        ),
    )
    stage.configure(stop_event=threading.Event())

    scheduler = stage._configured_non_interactive

    assert isinstance(scheduler, BatchScheduler)
    assert isinstance(scheduler._source, TimestampsBatcher)
    assert scheduler._source._batch_delay == 1.0


def test_configure_zero_plugins():
    """configure() with no plugins sets both sources to None."""
    stage = InputStage(plugins=[], params=_make_params())
    stop = threading.Event()
    stage.configure(stop_event=stop)

    assert stage._configured_non_interactive is None
    assert stage._configured_interactive is None


# - Execute: no sources -----------------------------------------------


def test_execute_no_sources_closes_output():
    """When both configured sources are None, output is closed immediately."""
    stage = InputStage(plugins=[], params=_make_params())
    stage._configured_non_interactive = None
    stage._configured_interactive = None
    stage._stop_event = threading.Event()

    output_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'output': output_q, 'skip_past': False},
    )
    stage_thread.start()

    result = output_q.get()
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert result is None  # sentinel


# - Execute: single source --------------------------------------------


def test_execute_single_source():
    """Single source produces batches to output queue."""
    ts1 = _make_timestamps(count=3)
    ts2 = _make_timestamps(count=2)
    source = _make_mock_source([ts1, ts2])

    p1 = _make_mock_input_plugin()
    stage = InputStage(plugins=[p1], params=_make_params())
    stage._configured_non_interactive = source
    stage._configured_interactive = None
    stage._stop_event = threading.Event()

    output_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'output': output_q, 'skip_past': False},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 2
    assert len(batches[0]) == 3
    assert len(batches[1]) == 2


def test_execute_single_source_stop_event():
    """Setting stop_event mid-iteration breaks the loop."""
    stop = threading.Event()
    call_count = 0

    def blocking_iterate(*, skip_past):
        nonlocal call_count
        for _ in range(100):
            call_count += 1
            if call_count == 3:
                stop.set()
            yield _make_timestamps(count=1)

    source = MagicMock()
    source.iterate = blocking_iterate

    p1 = _make_mock_input_plugin()
    stage = InputStage(plugins=[p1], params=_make_params())
    stage._configured_non_interactive = source
    stage._configured_interactive = None
    stage._stop_event = stop

    output_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'output': output_q, 'skip_past': False},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    # Should have produced approximately 3 batches before stop
    assert len(batches) <= 4


def test_execute_always_closes_output_on_error():
    """Output queue is closed even if iteration raises an error."""

    def failing_iterate(*, skip_past):
        yield _make_timestamps(count=1)
        raise RuntimeError('iteration failed')

    source = MagicMock()
    source.iterate = failing_iterate

    p1 = _make_mock_input_plugin()
    stage = InputStage(plugins=[p1], params=_make_params())
    stage._configured_non_interactive = source
    stage._configured_interactive = None
    stage._stop_event = threading.Event()

    output_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'output': output_q, 'skip_past': False},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert len(batches) == 1  # one batch before error
    # Output was closed (we got sentinel via _collect_output)


def test_execute_plugin_generation_error():
    """PluginGenerationError is caught and logged, output still closed."""
    from eventum.plugins.input.exceptions import PluginGenerationError

    def failing_iterate(*, skip_past):
        raise PluginGenerationError(
            'gen failed',
            context={'reason': 'test'},
        )

    source = MagicMock()
    source.iterate = failing_iterate

    p1 = _make_mock_input_plugin()
    stage = InputStage(plugins=[p1], params=_make_params())
    stage._configured_non_interactive = source
    stage._configured_interactive = None
    stage._stop_event = threading.Event()

    output_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'output': output_q, 'skip_past': False},
    )
    stage_thread.start()

    result = output_q.get()
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    assert result is None  # closed despite error


# - Execute: two sources (merged, uses sub-threads) -------------------


def test_execute_merged_sources():
    """Two sources produce in sub-threads, both drain into output."""
    ts1 = [_make_timestamps(count=2, plugin_id=1)]
    ts2 = [_make_timestamps(count=3, plugin_id=2)]

    source1 = _make_mock_source(ts1)
    source2 = _make_mock_source(ts2)

    p1 = _make_mock_input_plugin(plugin_id=1)
    p2 = _make_mock_input_plugin(plugin_id=2, is_interactive=True)
    stage = InputStage(plugins=[p1, p2], params=_make_params())
    stage._configured_non_interactive = source1
    stage._configured_interactive = source2
    stage._stop_event = threading.Event()

    output_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=10)

    stage_thread = threading.Thread(
        target=stage.execute,
        kwargs={'output': output_q, 'skip_past': False},
    )
    stage_thread.start()

    batches = _collect_output(output_q)
    stage_thread.join(timeout=5)

    assert not stage_thread.is_alive()
    total = sum(len(b) for b in batches)
    assert total == 5  # 2 + 3


# - stop_interactive_plugins ------------------------------------------


def test_stop_interactive_plugins():
    """stop_interactive_plugins calls stop_interacting on interactive only."""
    p1 = _make_mock_input_plugin(plugin_id=1, is_interactive=False)
    p2 = _make_mock_input_plugin(plugin_id=2, is_interactive=True)
    p3 = _make_mock_input_plugin(plugin_id=3, is_interactive=True)

    stage = InputStage(plugins=[p1, p2, p3], params=_make_params())
    stage.stop_interactive_plugins()

    p1.stop_interacting.assert_not_called()
    p2.stop_interacting.assert_called_once()
    p3.stop_interacting.assert_called_once()


# - Backpressure ------------------------------------------------------


def _run_stage_against_full_queue(
    output_q: PipelineQueue,
    *,
    live_mode: bool,
) -> threading.Thread:
    """Run a stage against an output queue that is already full.

    The queue is never drained, so the stage stays blocked on put right
    after it has checked the queue for fullness. The queue has to be
    shut down by the caller to release the stage.
    """
    source = _make_mock_source([_make_timestamps(count=1)])

    stage = InputStage(
        plugins=[_make_mock_input_plugin()],
        params=_make_params(live_mode=live_mode),
    )
    stage._configured_non_interactive = source
    stage._configured_interactive = None
    stage._stop_event = threading.Event()

    output_q.put(_make_timestamps(count=1))

    thread = threading.Thread(
        target=stage.execute,
        kwargs={'output': output_q, 'skip_past': False},
    )
    thread.start()

    return thread


def _wait_for_warnings(
    logs: Sequence[Mapping],
    timeout: float = 5.0,
) -> list[Mapping]:
    """Wait until at least one warning is captured and return warnings."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        warnings = [e for e in logs if e['log_level'] == 'warning']
        if warnings:
            return warnings
        time.sleep(0.01)

    return []


def test_full_output_queue_warns_in_live_mode():
    """A full timestamps queue is reported as a lag with a hint."""
    output_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=1)

    with structlog.testing.capture_logs() as logs:
        thread = _run_stage_against_full_queue(output_q, live_mode=True)
        warnings = _wait_for_warnings(logs)
        output_q.shutdown()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert len(warnings) == 1
    assert warnings[0]['hint']

    # the stage cannot know the rate is the cause, so it must not claim it
    assert 'EPS' not in warnings[0]['event']


def test_full_output_queue_stays_silent_in_sample_mode():
    """Sample mode has no schedule to lag behind, so a full queue is ok."""
    output_q: PipelineQueue[IdentifiedTimestamps] = PipelineQueue(maxsize=1)

    with structlog.testing.capture_logs() as logs:
        thread = _run_stage_against_full_queue(output_q, live_mode=False)

        # the check precedes the put, so by the time the stage blocks
        # on it the stage has already decided to stay silent
        time.sleep(0.1)
        output_q.shutdown()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert not [entry for entry in logs if entry['log_level'] == 'warning']
