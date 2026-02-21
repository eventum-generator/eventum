from datetime import datetime
from zoneinfo import ZoneInfo

from eventum.plugins.input.plugins.static.config import StaticInputPluginConfig
from eventum.plugins.input.plugins.static.plugin import StaticInputPlugin


def test_plugin():
    config = StaticInputPluginConfig(count=100)
    plugin = StaticInputPlugin(
        config=config, params={'id': 1, 'timezone': ZoneInfo('UTC')}
    )

    now = datetime.now().astimezone(ZoneInfo('UTC'))
    timestamps = []
    for batch in plugin.generate(size=100):
        timestamps.extend(batch)

    assert len(timestamps) == 100
    assert len(set(timestamps)) == 1

    ts = datetime.fromisoformat(str(timestamps[0])).replace(
        tzinfo=ZoneInfo('UTC')
    )
    assert abs((ts - now).total_seconds()) < 1
