import os
import tempfile
from datetime import datetime

import pytest
from numpy import datetime64
from zoneinfo import ZoneInfo

from eventum.plugins.input.plugins.timestamps.config import (
    TimestampsInputPluginConfig,
)
from eventum.plugins.input.plugins.timestamps.plugin import (
    TimestampsInputPlugin,
)


def test_plugin():
    config = TimestampsInputPluginConfig(
        source=[
            datetime.fromisoformat('2024-01-01T00:00:00.000Z'),
            datetime.fromisoformat('2024-01-01T00:00:00.050Z'),
            datetime.fromisoformat('2024-01-01T00:00:00.100Z'),
        ]
    )
    plugin = TimestampsInputPlugin(
        config=config, params={'id': 1, 'timezone': ZoneInfo('UTC')}
    )
    timestamps = []
    for batch in plugin.generate(size=100, skip_past=False):
        timestamps.extend(batch)

    assert timestamps == [
        datetime64('2024-01-01T00:00:00.000'),
        datetime64('2024-01-01T00:00:00.050'),
        datetime64('2024-01-01T00:00:00.100'),
    ]


@pytest.fixture
def timestamps_filename():
    filename = tempfile.mktemp()
    with open(filename, 'w') as f:
        f.write(f'2024-01-01T00:00:00.000Z{os.linesep}')
        f.write(f'2024-01-01T00:00:00.050Z{os.linesep}')
        f.write(f'2024-01-01T00:00:00.100Z{os.linesep}')

    return filename


def test_timestamps_from_file(timestamps_filename):
    config = TimestampsInputPluginConfig(source=timestamps_filename)
    plugin = TimestampsInputPlugin(
        config=config, params={'id': 1, 'timezone': ZoneInfo('Europe/Moscow')}
    )

    timestamps = []
    for batch in plugin.generate(size=100, skip_past=False):
        timestamps.extend(batch)

    assert timestamps == [
        datetime64('2024-01-01T03:00:00.000'),
        datetime64('2024-01-01T03:00:00.050'),
        datetime64('2024-01-01T03:00:00.100'),
    ]
