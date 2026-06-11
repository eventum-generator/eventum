"""Tests for timestamps aggregation logic."""

from datetime import timedelta

import numpy as np

from eventum.api.routers.preview.timestamps_aggregation import (
    aggregate_timestamps,
)

# --- aggregate_timestamps ---


def test_aggregate_timestamps_empty():
    ts = np.array([], dtype=[('timestamp', 'datetime64[us]'), ('id', 'i4')])
    result = aggregate_timestamps(ts, span=None)
    assert result.total == 0
    assert result.span_edges == []
    assert result.span_counts == {}


def test_aggregate_timestamps_small_sample():
    data = [
        (np.datetime64('2024-01-01T00:00:00', 'us'), 1),
        (np.datetime64('2024-01-01T00:00:01', 'us'), 1),
        (np.datetime64('2024-01-01T00:00:02', 'us'), 1),
    ]
    ts = np.array(data, dtype=[('timestamp', 'datetime64[us]'), ('id', 'i4')])

    result = aggregate_timestamps(ts, span=timedelta(seconds=1))
    assert result.total == 3
    assert result.timestamps is not None
    assert result.first_timestamps is None
    assert result.last_timestamps is None


def test_aggregate_timestamps_large_sample():
    n = 200
    base = np.datetime64('2024-01-01T00:00:00', 'us')
    times = [base + np.timedelta64(i, 's') for i in range(n)]
    data = [(t, 1) for t in times]
    ts = np.array(data, dtype=[('timestamp', 'datetime64[us]'), ('id', 'i4')])

    result = aggregate_timestamps(ts, span=timedelta(seconds=10))
    assert result.total == n
    assert result.timestamps is None
    assert result.first_timestamps is not None
    assert result.last_timestamps is not None
    assert len(result.first_timestamps) == 50
    assert len(result.last_timestamps) == 50
