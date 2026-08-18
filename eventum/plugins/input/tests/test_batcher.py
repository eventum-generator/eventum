from zoneinfo import ZoneInfo

import numpy as np
import pytest

from eventum.plugins.input.adapters import IdentifiedTimestampsPluginAdapter
from eventum.plugins.input.batcher import TimestampsBatcher
from eventum.plugins.input.merger import InputPluginsMerger
from eventum.plugins.input.plugins.cron.config import CronInputPluginConfig
from eventum.plugins.input.plugins.cron.plugin import CronInputPlugin
from eventum.plugins.input.plugins.static.config import StaticInputPluginConfig
from eventum.plugins.input.plugins.static.plugin import StaticInputPlugin


@pytest.fixture
def source():
    return IdentifiedTimestampsPluginAdapter(
        StaticInputPlugin(
            config=StaticInputPluginConfig(count=1000000),
            params={'id': 1, 'timezone': ZoneInfo('UTC')},
        )
    )


def test_size_batching(source):
    batcher = TimestampsBatcher(
        source=source, batch_size=1000, batch_delay=None
    )

    batches = list(batcher.iterate(skip_past=False))

    assert len(batches) == 1000
    assert all([batch.size == 1000 for batch in batches])


def test_uneven_size_batching(source):
    batcher = TimestampsBatcher(
        source=source, batch_size=333_333, batch_delay=None
    )

    batches = list(batcher.iterate(skip_past=False))

    assert len(batches) == 4
    assert (
        all([batch.size == 333_333 for batch in batches[:-1]])
        and batches[-1].size == 1
    )


@pytest.fixture
def delay_source():
    return IdentifiedTimestampsPluginAdapter(
        CronInputPlugin(
            config=CronInputPluginConfig(
                expression='* * * * *', count=1, start='now', end='+60m'
            ),
            params={'id': 1, 'timezone': ZoneInfo('UTC')},
        )
    )


def test_delay_batching(delay_source):
    batcher = TimestampsBatcher(
        source=delay_source, batch_size=None, batch_delay=600
    )

    batches = list(batcher.iterate(skip_past=False))

    assert len(batches) == 6
    assert all([batch.size == 10 for batch in batches])


@pytest.fixture
def uneven_delay_source():
    return InputPluginsMerger(
        plugins=[
            CronInputPlugin(
                config=CronInputPluginConfig(
                    expression='1-30 * * * *',
                    count=1,
                    start='00:00',
                    end='+60m',
                ),
                params={'id': 1, 'timezone': ZoneInfo('UTC')},
            ),
            CronInputPlugin(
                config=CronInputPluginConfig(
                    expression='50-59 * * * *',
                    count=2,
                    start='00:00',
                    end='+60m',
                ),
                params={'id': 1, 'timezone': ZoneInfo('UTC')},
            ),
        ]
    )


def test_delay_with_size_batching(uneven_delay_source):
    batcher = TimestampsBatcher(
        source=uneven_delay_source, batch_size=15, batch_delay=600
    )

    batches = list(batcher.iterate(skip_past=False))

    assert [batch.size for batch in batches] == [10, 10, 10, 15, 5]


def make_timestamps(count, step_ms=1000, start_ms=0):
    array = np.empty(
        count,
        dtype=[('timestamp', 'datetime64[us]'), ('id', 'uint16')],
    )
    array['timestamp'] = np.datetime64(
        '2024-01-01T00:00:00', 'us'
    ) + np.arange(start_ms, start_ms + count * step_ms, step_ms).astype(
        'timedelta64[ms]'
    )
    array['id'] = 1

    return array


class FakeSource:
    """Source yielding predefined arrays regardless of requested size."""

    def __init__(self, arrays):
        self.arrays = arrays

    def iterate(self, size, *, skip_past=True):
        yield from self.arrays


def test_lax_mode_does_not_accumulate_between_reads():
    source = FakeSource([make_timestamps(3), make_timestamps(4)])
    batcher = TimestampsBatcher(
        source=source, batch_size=10, batch_delay=None, lax=True
    )

    batches = list(batcher.iterate(skip_past=False))

    assert [batch.size for batch in batches] == [3, 4]


def test_lax_mode_chunks_read_by_size():
    source = FakeSource([make_timestamps(5)])
    batcher = TimestampsBatcher(
        source=source, batch_size=2, batch_delay=None, lax=True
    )

    batches = list(batcher.iterate(skip_past=False))

    assert [batch.size for batch in batches] == [2, 2, 1]


def test_delay_window_is_recounted_from_kept_remainder():
    # 25 timestamps within 1.25 seconds, window covers first 20 of them
    source = FakeSource([make_timestamps(25, step_ms=50)])
    batcher = TimestampsBatcher(source=source, batch_size=10, batch_delay=1.0)

    batches = list(batcher.iterate(skip_past=False))

    assert [batch.size for batch in batches] == [10, 10, 5]


def test_delay_window_closes_batch_under_size():
    # 25 timestamps within 2.5 seconds, size is never reached
    source = FakeSource([make_timestamps(25, step_ms=100)])
    batcher = TimestampsBatcher(source=source, batch_size=100, batch_delay=1.0)

    batches = list(batcher.iterate(skip_past=False))

    assert [batch.size for batch in batches] == [10, 10, 5]


def test_delay_window_spans_several_reads():
    source = FakeSource(
        [
            make_timestamps(3, step_ms=100, start_ms=0),
            make_timestamps(3, step_ms=100, start_ms=300),
            make_timestamps(3, step_ms=100, start_ms=1000),
        ]
    )
    batcher = TimestampsBatcher(source=source, batch_size=100, batch_delay=1.0)

    batches = list(batcher.iterate(skip_past=False))

    assert [batch.size for batch in batches] == [6, 3]


def test_no_timestamps_are_lost():
    arrays = [
        make_timestamps(7, step_ms=100, start_ms=0),
        make_timestamps(9, step_ms=100, start_ms=700),
        make_timestamps(4, step_ms=100, start_ms=1600),
    ]
    batcher = TimestampsBatcher(
        source=FakeSource(arrays), batch_size=6, batch_delay=0.5
    )

    batches = list(batcher.iterate(skip_past=False))

    assert np.array_equal(
        np.concatenate(batches),
        np.concatenate(arrays),
    )
