import pytest
from zoneinfo import ZoneInfo

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
