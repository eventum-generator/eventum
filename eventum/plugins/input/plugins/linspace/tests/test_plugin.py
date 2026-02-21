from datetime import datetime

import pytest
from numpy import datetime64
from zoneinfo import ZoneInfo

from eventum.plugins.input.plugins.linspace.config import (
    LinspaceInputPluginConfig,
)
from eventum.plugins.input.plugins.linspace.plugin import LinspaceInputPlugin


@pytest.mark.parametrize(
    ('start', 'end', 'count', 'endpoint', 'expected'),
    [
        (
            '2024-01-01T00:00:00.000Z',
            '2024-01-01T00:00:03.000Z',
            3,
            False,
            [
                datetime64('2024-01-01T00:00:00.000'),
                datetime64('2024-01-01T00:00:01.000'),
                datetime64('2024-01-01T00:00:02.000'),
            ],
        ),
        (
            '2024-01-01T00:00:00.000Z',
            '2024-01-01T00:00:01.000Z',
            5,
            True,
            [
                datetime64('2024-01-01T00:00:00.000'),
                datetime64('2024-01-01T00:00:00.250'),
                datetime64('2024-01-01T00:00:00.500'),
                datetime64('2024-01-01T00:00:00.750'),
                datetime64('2024-01-01T00:00:01.000'),
            ],
        ),
    ],
)
def test_plugin(start, end, count, endpoint, expected):
    config = LinspaceInputPluginConfig(
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
        count=count,
        endpoint=endpoint,
    )

    plugin = LinspaceInputPlugin(
        config=config, params={'id': 1, 'timezone': ZoneInfo('UTC')}
    )

    timestamps = []
    for batch in plugin.generate(size=100, skip_past=False):
        timestamps.extend(batch)

    assert timestamps == expected
