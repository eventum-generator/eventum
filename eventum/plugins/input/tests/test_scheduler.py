import time
from threading import Event, Thread

import pytest
from zoneinfo import ZoneInfo

from eventum.plugins.input.adapters import IdentifiedTimestampsPluginAdapter
from eventum.plugins.input.batcher import TimestampsBatcher
from eventum.plugins.input.plugins.static.config import StaticInputPluginConfig
from eventum.plugins.input.plugins.static.plugin import StaticInputPlugin
from eventum.plugins.input.plugins.timer.config import TimerInputPluginConfig
from eventum.plugins.input.plugins.timer.plugin import TimerInputPlugin
from eventum.plugins.input.scheduler import BatchScheduler


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
