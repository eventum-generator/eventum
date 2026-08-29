import numpy as np
import pytest

from eventum.plugins.input.accumulator import BatchAccumulator
from eventum.plugins.input.protocols import IdentifiedTimestamps


def make_timestamps(count: int, start: int = 0) -> IdentifiedTimestamps:
    array = np.empty(
        count,
        dtype=[('timestamp', 'datetime64[us]'), ('id', 'uint16')],
    )
    array['timestamp'] = np.datetime64(
        '2024-01-01T00:00:00',
        'us',
    ) + np.arange(start, start + count).astype('timedelta64[s]')
    array['id'] = 1

    return array


def test_invalid_max_size():
    with pytest.raises(ValueError):
        BatchAccumulator(max_size=0)


def test_push_incomplete_batch():
    accumulator = BatchAccumulator(max_size=10)

    assert accumulator.push(make_timestamps(4)) == []
    assert accumulator.push(make_timestamps(5)) == []
    assert accumulator.size == 9


def test_push_complete_batch():
    accumulator = BatchAccumulator(max_size=10)

    accumulator.push(make_timestamps(4))
    batches = accumulator.push(make_timestamps(6))

    assert len(batches) == 1
    assert batches[0].size == 10
    assert accumulator.size == 0


def test_push_exceeding_batches():
    accumulator = BatchAccumulator(max_size=10)

    batches = accumulator.push(make_timestamps(25))

    assert [batch.size for batch in batches] == [10, 10]
    assert accumulator.size == 5


def test_push_empty_array():
    accumulator = BatchAccumulator(max_size=10)

    assert accumulator.push(make_timestamps(0)) == []
    assert accumulator.size == 0


def test_push_unlimited_size():
    accumulator = BatchAccumulator(max_size=None)

    assert accumulator.push(make_timestamps(1000)) == []
    assert accumulator.size == 1000

    flushed = accumulator.flush()

    assert [batch.size for batch in flushed] == [1000]


def test_flush_empty():
    accumulator = BatchAccumulator(max_size=10)

    assert accumulator.flush() == []


def test_flush_remainder():
    accumulator = BatchAccumulator(max_size=10)

    accumulator.push(make_timestamps(13))
    flushed = accumulator.flush()

    assert [batch.size for batch in flushed] == [3]
    assert accumulator.size == 0
    assert accumulator.flush() == []


def test_timestamps_order_is_preserved():
    accumulator = BatchAccumulator(max_size=5)

    batches = accumulator.push(make_timestamps(count=12))
    batches.extend(accumulator.flush())

    assert np.array_equal(
        np.concatenate(batches),
        make_timestamps(count=12),
    )


def test_first_timestamp():
    accumulator = BatchAccumulator(max_size=10)

    assert accumulator.first_timestamp is None

    accumulator.push(make_timestamps(count=4, start=100))

    assert (
        accumulator.first_timestamp
        == make_timestamps(1, start=100)[0]['timestamp']
    )


def test_first_timestamp_of_remainder():
    accumulator = BatchAccumulator(max_size=10)

    accumulator.push(make_timestamps(count=12))

    assert (
        accumulator.first_timestamp
        == make_timestamps(count=12)[10]['timestamp']
    )
