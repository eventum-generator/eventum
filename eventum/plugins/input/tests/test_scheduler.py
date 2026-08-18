import time
from threading import Event, Thread
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from eventum.plugins.input.adapters import IdentifiedTimestampsPluginAdapter
from eventum.plugins.input.batcher import TimestampsBatcher
from eventum.plugins.input.plugins.static.config import StaticInputPluginConfig
from eventum.plugins.input.plugins.static.plugin import StaticInputPlugin
from eventum.plugins.input.plugins.timer.config import TimerInputPluginConfig
from eventum.plugins.input.plugins.timer.plugin import TimerInputPlugin
from eventum.plugins.input.scheduler import BatchScheduler
from eventum.plugins.input.utils.time_utils import now64


def make_batch(count, offset_ms):
    """Make batch of timestamps shifted from the current moment."""
    array = np.empty(
        count,
        dtype=[('timestamp', 'datetime64[us]'), ('id', 'uint16')],
    )
    array['timestamp'] = (
        now64(ZoneInfo('UTC'))
        + np.timedelta64(offset_ms, 'ms')
        + np.arange(count).astype('timedelta64[us]')
    )
    array['id'] = 1

    return array


class FakeSource:
    """Source yielding predefined batches."""

    def __init__(self, batches):
        self.batches = batches

    def iterate(self, *, skip_past=True):
        yield from self.batches


@pytest.fixture
def instant_source():
    return IdentifiedTimestampsPluginAdapter(
        StaticInputPlugin(
            config=StaticInputPluginConfig(count=1000),
            params={'id': 1, 'timezone': ZoneInfo('UTC')},
        )
    )


@pytest.fixture
def delayed_source():
    return IdentifiedTimestampsPluginAdapter(
        TimerInputPlugin(
            config=TimerInputPluginConfig(
                start='now', seconds=0.5, count=1000, repeat=1
            ),
            params={'id': 1, 'timezone': ZoneInfo('UTC')},
        )
    )


def test_scheduler(instant_source):
    scheduler = BatchScheduler(
        source=TimestampsBatcher(
            source=instant_source, batch_size=100, batch_delay=None
        ),
        timezone=ZoneInfo('UTC'),
    )

    t1 = time.time()
    batches = list(scheduler.iterate(skip_past=False))
    t2 = time.time()

    assert len(batches) == 10
    assert (t2 - t1) < 0.5


def test_scheduler_delay(delayed_source):
    scheduler = BatchScheduler(
        source=TimestampsBatcher(
            source=delayed_source, batch_size=100, batch_delay=None
        ),
        timezone=ZoneInfo('UTC'),
    )

    t1 = time.time()
    batches = list(scheduler.iterate(skip_past=False))
    t2 = time.time()

    assert len(batches) == 10
    assert (t2 - t1) >= 0.5


def test_scheduler_stop_event(delayed_source):
    stop_event = Event()

    scheduler = BatchScheduler(
        source=TimestampsBatcher(
            source=delayed_source, batch_size=100, batch_delay=None
        ),
        timezone=ZoneInfo('UTC'),
        stop_event=stop_event,
    )

    batches: list = []

    def iterate():
        for batch in scheduler.iterate(skip_past=False):
            batches.append(batch)

    t = Thread(target=iterate)
    t1 = time.time()
    t.start()

    time.sleep(0.1)
    stop_event.set()
    t.join(timeout=1.0)
    t2 = time.time()

    assert not t.is_alive(), 'Scheduler thread should have stopped'
    assert (t2 - t1) < 0.5, 'Scheduler should exit early on stop'


def test_scheduler_merges_due_batches():
    source = FakeSource([make_batch(10, offset_ms=-1000) for _ in range(25)])
    scheduler = BatchScheduler(
        source=source,
        timezone=ZoneInfo('UTC'),
        max_batch_size=100,
    )

    batches = list(scheduler.iterate(skip_past=False))

    assert [batch.size for batch in batches] == [100, 100, 50]


def test_scheduler_publishes_due_batches_as_is_without_max_size():
    source = FakeSource([make_batch(10, offset_ms=-1000) for _ in range(3)])
    scheduler = BatchScheduler(
        source=source,
        timezone=ZoneInfo('UTC'),
    )

    batches = list(scheduler.iterate(skip_past=False))

    assert [batch.size for batch in batches] == [10, 10, 10]


def test_scheduler_publishes_merged_batch_before_waiting():
    source = FakeSource(
        [
            make_batch(10, offset_ms=-1000),
            make_batch(10, offset_ms=-500),
            make_batch(5, offset_ms=500),
        ]
    )
    scheduler = BatchScheduler(
        source=source,
        timezone=ZoneInfo('UTC'),
        max_batch_size=100,
    )

    t1 = time.time()
    iterator = scheduler.iterate(skip_past=False)
    first_batch = next(iterator)
    t2 = time.time()
    rest = list(iterator)
    t3 = time.time()

    assert first_batch.size == 20
    assert (t2 - t1) < 0.4, 'Due timestamps should not wait for future ones'
    assert [batch.size for batch in rest] == [5]
    assert (t3 - t1) >= 0.4


def test_scheduler_does_not_merge_batches_across_waiting():
    source = FakeSource(
        [
            make_batch(10, offset_ms=-1000),
            make_batch(10, offset_ms=300),
            make_batch(10, offset_ms=-1000),
        ]
    )
    scheduler = BatchScheduler(
        source=source,
        timezone=ZoneInfo('UTC'),
        max_batch_size=100,
    )

    batches = list(scheduler.iterate(skip_past=False))

    assert [batch.size for batch in batches] == [10, 10, 10]
