import numpy as np
import pytest
from zoneinfo import ZoneInfo

from eventum.plugins.input.adapters import (
    AsyncIdentifiedTimestampsSyncAdapter,
    IdentifiedTimestampsPluginAdapter,
)
from eventum.plugins.input.batcher import TimestampsBatcher
from eventum.plugins.input.plugins.cron.config import CronInputPluginConfig
from eventum.plugins.input.plugins.cron.plugin import CronInputPlugin


@pytest.fixture
def plugin():
    return CronInputPlugin(
        config=CronInputPluginConfig(
            start='2030-01-01T00:00:00',
            end='2030-01-01T00:01:00',
            expression='* * * * * *',
            count=1,
        ),
        params={'id': 1437, 'timezone': ZoneInfo('UTC')},
    )


def test_identified_timestamps_plugin_adapter(plugin):
    adapted = IdentifiedTimestampsPluginAdapter(plugin=plugin)

    plugin_arrays = []
    for array in plugin.generate(size=1000, skip_past=False):
        plugin_arrays.append(array)

    adapter_arrays = []
    for array in adapted.iterate(size=1000, skip_past=False):
        adapter_arrays.append(array)

    plugin_arr = np.concatenate(plugin_arrays)
    adapter_arr = np.concatenate(adapter_arrays)

    assert np.array_equal(plugin_arr, adapter_arr['timestamp'])

    ids = set(adapter_arr['id'])
    assert len(ids) == 1
    assert ids.pop() == 1437


@pytest.mark.asyncio
async def test_async_identified_timestamps_sync_adapter(plugin):
    source = IdentifiedTimestampsPluginAdapter(plugin=plugin)
    batcher = TimestampsBatcher(source, batch_size=1000)
    adapted = AsyncIdentifiedTimestampsSyncAdapter(target=batcher)

    iterator = adapted.iterate()
    assert hasattr(iterator, '__anext__')
