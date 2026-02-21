from datetime import datetime, timedelta

import numpy as np
import pytest
from zoneinfo import ZoneInfo

from eventum.plugins.input.merger import InputPluginsMerger
from eventum.plugins.input.plugins.http.config import HttpInputPluginConfig
from eventum.plugins.input.plugins.http.plugin import HttpInputPlugin
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
