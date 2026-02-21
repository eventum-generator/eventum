from datetime import datetime

from numpy import datetime64
from zoneinfo import ZoneInfo

from eventum.plugins.input.plugins.timer.config import TimerInputPluginConfig
from eventum.plugins.input.plugins.timer.plugin import TimerInputPlugin


def test_plugin():
    start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))

    plugin = TimerInputPlugin(
        config=TimerInputPluginConfig(
            start=start, seconds=1.0, count=3, repeat=86400
        ),
        params={'id': 1, 'timezone': ZoneInfo('UTC')},
    )

    timestamps = []
    for batch in plugin.generate(skip_past=False, size=100):
        timestamps.extend(batch)

    assert len(timestamps) == (86400 * 3)
    assert timestamps[0] == datetime64('2024-01-01T00:00:01')
    assert timestamps[-1] == datetime64('2024-01-02T00:00:00')
