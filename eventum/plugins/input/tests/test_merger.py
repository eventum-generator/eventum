from collections.abc import Iterator
from datetime import datetime, timedelta
from threading import Thread
from unittest.mock import MagicMock

import numpy as np
import pytest
from numpy.typing import NDArray
from zoneinfo import ZoneInfo

from eventum.plugins.input.merger import InputPluginsMerger
from eventum.plugins.input.plugins.linspace.config import (
    LinspaceInputPluginConfig,
)
from eventum.plugins.input.plugins.linspace.plugin import LinspaceInputPlugin


def test_merger():
    start = datetime.now(tz=ZoneInfo('UTC'))

    plugin_1 = LinspaceInputPlugin(
        config=LinspaceInputPluginConfig(
            start=start + timedelta(seconds=0.5),
            end='+1s',
            count=100_000,
        ),
        params={
            'id': 1,
            'timezone': ZoneInfo('UTC'),
        },
    )

    plugin_2 = LinspaceInputPlugin(
        config=LinspaceInputPluginConfig(
            start=start + timedelta(seconds=0.6),
            end='+1s',
            count=100_000,
        ),
        params={
            'id': 2,
            'timezone': ZoneInfo('UTC'),
        },
    )

    plugin_3 = LinspaceInputPlugin(
        config=LinspaceInputPluginConfig(
            start=start + timedelta(seconds=0.7),
            end='+1s',
            count=100_000,
        ),
        params={
            'id': 3,
            'timezone': ZoneInfo('UTC'),
        },
    )

    plugins_lst = [plugin_1, plugin_2, plugin_3]

    merger = InputPluginsMerger(plugins=plugins_lst)

    batches = list(merger.iterate(10000, skip_past=False))

    array = np.concatenate(batches)

    assert array.size == 300_000

    occurrences = dict(zip(*np.unique(array['id'], return_counts=True)))

    assert occurrences[1] == 100_000
    assert occurrences[2] == 100_000
    assert occurrences[3] == 100_000


def test_merger_with_no_provided_plugins():
    with pytest.raises(ValueError):
        InputPluginsMerger(plugins=[])


MERGE_TIMEOUT = 15.0


def _make_mock_plugin(
    plugin_id: int,
    generate: Iterator[NDArray[np.datetime64]],
) -> MagicMock:
    plugin = MagicMock()
    plugin.id = plugin_id
    plugin.guid = f'guid-{plugin_id}'
    plugin.is_interactive = False
    plugin.generate = MagicMock(return_value=generate)
    return plugin


def _arrays(count: int) -> Iterator[NDArray[np.datetime64]]:
    base = np.datetime64('2020-01-01T00:00:00', 'us')
    for i in range(count):
        yield np.array(
            [base + np.timedelta64(i * 1_000_000 + j, 'us') for j in range(3)],
            dtype='datetime64[us]',
        )


def _failing_arrays() -> Iterator[NDArray[np.datetime64]]:
    yield from _arrays(1)
    raise ZeroDivisionError


def test_merger_drops_plugin_failed_with_unexpected_error():
    """A plugin failing with an unexpected error leaves the merge, and
    the merge ends once the remaining plugins are exhausted.
    """
    merger = InputPluginsMerger(
        plugins=[
            _make_mock_plugin(1, _failing_arrays()),
            _make_mock_plugin(2, _arrays(5)),
        ],
    )
    batches: list = []

    thread = Thread(
        target=lambda: batches.extend(merger.iterate(10, skip_past=False)),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=MERGE_TIMEOUT)

    assert not thread.is_alive()

    array = np.concatenate(batches)
    assert (array['id'] == 1).sum() == 3
    assert (array['id'] == 2).sum() == 15


def test_merger_rejects_interactive_plugins():
    plugin = _make_mock_plugin(2, _arrays(1))
    plugin.is_interactive = True

    with pytest.raises(ValueError, match='Interactive'):
        InputPluginsMerger(plugins=[_make_mock_plugin(1, _arrays(1)), plugin])
