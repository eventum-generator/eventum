"""Tests for OutputStage."""

import asyncio
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog.testing

from eventum.core.executor import ExecutionError
from eventum.core.parameters import GeneratorParameters
from eventum.core.queue import PipelineQueue
from eventum.core.stages.output_stage import OutputStage
from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError


def _make_params(**overrides) -> GeneratorParameters:
    defaults: dict = {
        'id': 'test',
        'path': Path('/tmp/config.yml'),
        'live_mode': False,
    }
    defaults.update(overrides)
    return GeneratorParameters(**defaults)


def _make_mock_output_plugin(write_return: int = 5):
    """Create a mock OutputPlugin with async methods."""
    plugin = MagicMock()
    plugin.open = AsyncMock()
    plugin.close = AsyncMock()
    plugin.write = AsyncMock(return_value=write_return)
    plugin.__str__ = MagicMock(return_value='<mock output>')  # type: ignore
    return plugin


def _make_output_stage(
    plugins=None,
    params=None,
) -> OutputStage:
    if plugins is None:
        plugins = [_make_mock_output_plugin()]
    if params is None:
        params = _make_params()
    return OutputStage(plugins=plugins, params=params)


def _feed_and_close(input_q: PipelineQueue, batches: list) -> None:
    """Put event batches into queue then close it."""
    for batch in batches:
        input_q.put(batch)
    input_q.close()


async def _slow_write(events) -> int:
    """Write that never completes within the tested write timeout."""
    await asyncio.sleep(10)
    return len(events)


# - open() ------------------------------------------------------------


@pytest.mark.asyncio
async def test_open_all_succeed():
    """open() calls open on all plugins, no error raised."""
    p1 = _make_mock_output_plugin()
    p2 = _make_mock_output_plugin()
    stage = _make_output_stage(plugins=[p1, p2])
    await stage.open()
    p1.open.assert_awaited_once()
    p2.open.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_some_fail_raises_execution_error():
    """open() raises ExecutionError if any plugin fails to open."""
    p1 = _make_mock_output_plugin()
    p2 = _make_mock_output_plugin()
    p2.open.side_effect = PluginOpenError(
        'cannot open',
        context={'reason': 'test'},
    )
    stage = _make_output_stage(plugins=[p1, p2])
    with pytest.raises(ExecutionError):
        await stage.open()


@pytest.mark.asyncio
async def test_open_unexpected_error_raises_execution_error():
    """open() raises ExecutionError on unexpected exceptions."""
    p1 = _make_mock_output_plugin()
    p1.open.side_effect = RuntimeError('kaboom')
    stage = _make_output_stage(plugins=[p1])
    with pytest.raises(ExecutionError):
        await stage.open()


# - close() -----------------------------------------------------------


@pytest.mark.asyncio
async def test_close_all_succeed():
    """close() calls close on all plugins."""
    p1 = _make_mock_output_plugin()
    p2 = _make_mock_output_plugin()
    stage = _make_output_stage(plugins=[p1, p2])
    await stage.close()
    p1.close.assert_awaited_once()
    p2.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_swallows_exceptions():
    """close() does not raise even if plugins raise."""
    p1 = _make_mock_output_plugin()
    p1.close.side_effect = RuntimeError('close failed')
    p2 = _make_mock_output_plugin()
    stage = _make_output_stage(plugins=[p1, p2])
    await stage.close()  # should not raise
    p2.close.assert_awaited_once()


# - execute() ---------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_normal_flow():
    """Events from input queue are written to all plugins."""
    p1 = _make_mock_output_plugin()
    stage = _make_output_stage(plugins=[p1])
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1', 'ev2'], ['ev3']]),
    ).start()

    await stage.execute(input=input_q)

    assert p1.write.await_count == 2


@pytest.mark.asyncio
async def test_execute_sentinel_terminates():
    """Sentinel (None) from input queue terminates the loop."""
    p1 = _make_mock_output_plugin()
    stage = _make_output_stage(plugins=[p1])
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(target=input_q.close).start()

    await stage.execute(input=input_q)
    p1.write.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_multiple_plugins():
    """Each event batch is written to every output plugin."""
    p1 = _make_mock_output_plugin()
    p2 = _make_mock_output_plugin()
    stage = _make_output_stage(plugins=[p1, p2])
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1']]),
    ).start()

    await stage.execute(input=input_q)

    p1.write.assert_awaited_once_with(['ev1'])
    p2.write.assert_awaited_once_with(['ev1'])


@pytest.mark.asyncio
async def test_execute_keep_order_true():
    """With keep_order=True, processes batches sequentially."""
    p1 = _make_mock_output_plugin()
    params = _make_params(keep_order=True)
    stage = _make_output_stage(plugins=[p1], params=params)
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1'], ['ev2']]),
    ).start()

    await stage.execute(input=input_q)
    assert p1.write.await_count == 2


@pytest.mark.asyncio
async def test_execute_drains_remaining_tasks():
    """After sentinel, remaining in-flight tasks are awaited."""
    p1 = _make_mock_output_plugin()

    async def slow_write(events):
        await asyncio.sleep(0.1)
        return len(events)

    p1.write.side_effect = slow_write

    params = _make_params(keep_order=False)
    stage = _make_output_stage(plugins=[p1], params=params)
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1']]),
    ).start()

    await stage.execute(input=input_q)
    # If we get here without error, draining worked


# - _handle_write_result errors ---------------------------------------


@pytest.mark.asyncio
async def test_handle_write_result_plugin_write_error():
    """PluginWriteError in write is handled (logged, not re-raised)."""
    p1 = _make_mock_output_plugin()
    p1.write.side_effect = PluginWriteError(
        'write failed',
        context={'reason': 'test'},
    )
    stage = _make_output_stage(plugins=[p1])
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1']]),
    ).start()

    await stage.execute(input=input_q)
    # Should complete without raising


@pytest.mark.asyncio
async def test_handle_write_result_timeout():
    """Write timeout is handled (logged, not re-raised)."""
    p1 = _make_mock_output_plugin()
    p1.write.side_effect = _slow_write

    params = _make_params(write_timeout=1)
    stage = _make_output_stage(plugins=[p1], params=params)
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1']]),
    ).start()

    await stage.execute(input=input_q)
    # Should complete without raising (timeout handled in callback)


@pytest.mark.asyncio
async def test_write_timeout_warning_states_fact_and_hint():
    """Write timeout warning reports the observed fact with a hint."""
    p1 = _make_mock_output_plugin()
    p1.write.side_effect = _slow_write

    params = _make_params(write_timeout=1)
    stage = _make_output_stage(plugins=[p1], params=params)
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1']]),
    ).start()

    with structlog.testing.capture_logs() as logs:
        await stage.execute(input=input_q)

    warnings = [entry for entry in logs if entry['log_level'] == 'warning']
    assert len(warnings) == 1

    entry = warnings[0]
    assert entry['task_name'] == 'Writing with <mock output>'
    assert entry['timeout'] == 1
    assert entry['count'] == 1
    assert entry['hint']

    # the stage cannot know the rate is the cause, so it must not claim it
    assert 'EPS' not in entry['event']


@pytest.mark.asyncio
async def test_write_timeouts_of_one_plugin_are_throttled():
    """Repeated timeouts of one plugin are reported once per period."""
    p1 = _make_mock_output_plugin()
    p1.write.side_effect = _slow_write

    params = _make_params(write_timeout=1)
    stage = _make_output_stage(plugins=[p1], params=params)
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1'], ['ev2'], ['ev3']]),
    ).start()

    with structlog.testing.capture_logs() as logs:
        await stage.execute(input=input_q)

    warnings = [entry for entry in logs if entry['log_level'] == 'warning']
    assert len(warnings) == 1
    assert stage._timed_out_writes['Writing with <mock output>'] == 3  # noqa: SLF001


@pytest.mark.asyncio
async def test_write_timeouts_are_throttled_per_plugin():
    """A saturated plugin does not mute timeouts of another one."""
    p1 = _make_mock_output_plugin()
    p1.write.side_effect = _slow_write
    p1.__str__ = MagicMock(return_value='<mock output 1>')  # type: ignore[method-assign]

    p2 = _make_mock_output_plugin()
    p2.write.side_effect = _slow_write
    p2.__str__ = MagicMock(return_value='<mock output 2>')  # type: ignore[method-assign]

    params = _make_params(write_timeout=1)
    stage = _make_output_stage(plugins=[p1, p2], params=params)
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1']]),
    ).start()

    with structlog.testing.capture_logs() as logs:
        await stage.execute(input=input_q)

    reported = {
        entry['task_name'] for entry in logs if entry['log_level'] == 'warning'
    }
    assert reported == {
        'Writing with <mock output 1>',
        'Writing with <mock output 2>',
    }


@pytest.mark.asyncio
async def test_handle_write_result_unexpected_error():
    """Generic exception in write is handled (logged, not re-raised)."""
    p1 = _make_mock_output_plugin()
    p1.write.side_effect = RuntimeError('kaboom')
    stage = _make_output_stage(plugins=[p1])
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev1']]),
    ).start()

    await stage.execute(input=input_q)
    # Should complete without raising


# - Concurrency -------------------------------------------------------


@pytest.mark.asyncio
async def test_semaphore_limits_concurrency():
    """max_concurrency limits the number of concurrent writes."""
    max_concurrent = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    async def tracked_write(events):
        nonlocal max_concurrent, current_concurrent
        async with lock:
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
        await asyncio.sleep(0.05)
        async with lock:
            current_concurrent -= 1
        return len(events)

    plugins = [_make_mock_output_plugin() for _ in range(3)]
    for p in plugins:
        p.write.side_effect = tracked_write

    params = _make_params(max_concurrency=2, keep_order=False)
    stage = _make_output_stage(plugins=plugins, params=params)
    input_q: PipelineQueue[list[str]] = PipelineQueue(maxsize=10)

    threading.Thread(
        target=_feed_and_close,
        args=(input_q, [['ev'] for _ in range(5)]),
    ).start()

    await stage.execute(input=input_q)
    assert max_concurrent <= 2
