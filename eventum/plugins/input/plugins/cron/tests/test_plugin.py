from datetime import datetime

from numpy import datetime64
from zoneinfo import ZoneInfo

from eventum.plugins.input.plugins.cron.config import CronInputPluginConfig
from eventum.plugins.input.plugins.cron.plugin import CronInputPlugin


def test_plugin():
    plugin = CronInputPlugin(
        config=CronInputPluginConfig(
            expression='* * * * *',
            count=2,
            start=datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC')),
            end=datetime(2024, 1, 1, 23, 59, 59, tzinfo=ZoneInfo('UTC')),
        ),
        params={'id': 1, 'timezone': ZoneInfo('UTC')},
    )

    timestamps = []

    for batch in plugin.generate(size=100, skip_past=False):
        timestamps.extend(batch)

    assert len(timestamps) == (1440 * 2)
    assert len(set(timestamps)) == 1440
    assert timestamps[0] == datetime64('2024-01-01T00:00:00')
    assert timestamps[-1] == datetime64('2024-01-01T23:59:00')
