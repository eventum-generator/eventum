import asyncio
import os
from pathlib import Path

import pytest

from eventum.plugins.output.fields import JsonFormatterConfig
from eventum.plugins.output.formatters import Format
from eventum.plugins.output.plugins.file.config import FileOutputPluginConfig
from eventum.plugins.output.plugins.file.plugin import FileOutputPlugin


@pytest.mark.asyncio
async def test_plugin_write(tmp_path):
    filepath = tmp_path / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite'
        ),
        params={'id': 1},
    )

    await plugin.open()

    events = ['event1', 'event2', 'event3']
    await plugin.write(events)

    await plugin.close()

    with open(filepath) as f:
        lines = f.readlines()

    assert events == [line.rstrip(os.linesep) for line in lines]


@pytest.mark.asyncio
async def test_plugin_separator(tmp_path):
    filepath = tmp_path / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite', separator=''
        ),
        params={'id': 1},
    )

    await plugin.open()

    events = ['event1', 'event2', 'event3']
    await plugin.write(events)

    await plugin.close()

    with open(filepath) as f:
        content = f.read()

    assert ''.join(events) == content


@pytest.mark.asyncio
async def test_plugin_write_with_format(tmp_path):
    filepath = tmp_path / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath),
            formatter=JsonFormatterConfig(format=Format.JSON),
            write_mode='overwrite',
        ),
        params={'id': 1},
    )

    await plugin.open()

    events = ['{\n  "a": 1\n}\n']
    await plugin.write(events)

    await plugin.close()

    with open(filepath) as f:
        lines = f.readlines()

    assert [line.rstrip(os.linesep) for line in lines] == ['{"a": 1}']


@pytest.mark.asyncio
async def test_plugin_write_overwrite(tmp_path):
    filepath = tmp_path / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite'
        ),
        params={'id': 1},
    )
    events = ['a']

    await plugin.open()
    await plugin.write(events)
    await plugin.close()

    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite'
        ),
        params={'id': 1},
    )
    events = ['b']

    await plugin.open()
    await plugin.write(events)
    await plugin.close()

    with open(filepath) as f:
        lines = f.readlines()

    assert [line.strip(os.linesep) for line in lines] == ['b']


@pytest.mark.asyncio
async def test_plugin_write_append(tmp_path):
    filepath = tmp_path / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite'
        ),
        params={'id': 1},
    )
    events = ['a']

    await plugin.open()
    await plugin.write(events)
    await plugin.close()

    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='append'
        ),
        params={'id': 1},
    )
    events = ['b']

    await plugin.open()
    await plugin.write(events)
    await plugin.close()

    with open(filepath) as f:
        lines = f.readlines()

    assert [line.strip(os.linesep) for line in lines] == ['a', 'b']


@pytest.mark.asyncio
async def test_plugin_filemode(tmp_path):
    filepath = tmp_path / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite', file_mode=600
        ),
        params={'id': 1},
    )
    events = ['a']

    await plugin.open()
    await plugin.write(events)
    await plugin.close()

    assert oct(os.stat(filepath).st_mode)[-3:] == '600'


@pytest.mark.asyncio
async def test_plugin_flush_every_event(tmp_path):
    filepath = tmp_path / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite', flush_interval=0
        ),
        params={'id': 1},
    )
    events = ['a', 'b', 'c']

    await plugin.open()

    with open(filepath) as f:
        for event in events:
            await plugin.write([event])
            lines = f.readlines()

            assert [line.strip(os.linesep) for line in lines] == [event]

    await plugin.close()


@pytest.mark.asyncio
async def test_plugin_flush_interval(tmp_path):
    filepath = tmp_path / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite', flush_interval=0.1
        ),
        params={'id': 1},
    )
    events = ['a', 'b', 'c']

    await plugin.open()

    with open(filepath) as f:
        for event in events:
            await plugin.write([event])
            lines = f.readlines()

            assert not lines

        await asyncio.sleep(0.5)

        lines = f.readlines()
        assert [line.strip(os.linesep) for line in lines] == events

    await plugin.close()


@pytest.mark.asyncio
async def test_plugin_creates_intermediate_directories(tmp_path):
    filepath = tmp_path / 'a' / 'b' / 'c' / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite'
        ),
        params={'id': 1},
    )

    await plugin.open()

    events = ['event1']
    await plugin.write(events)

    await plugin.close()

    with open(filepath) as f:
        lines = f.readlines()

    assert events == [line.rstrip(os.linesep) for line in lines]


@pytest.mark.asyncio
async def test_plugin_file_recreation(tmp_path):
    filepath = tmp_path / 'test'
    plugin = FileOutputPlugin(
        config=FileOutputPluginConfig(
            path=Path(filepath), write_mode='overwrite', flush_interval=0
        ),
        params={'id': 1},
    )

    await plugin.open()

    for i in range(100):
        if i == 75:
            os.remove(filepath)

        await plugin.write(['a'])

    await plugin.close()

    with open(filepath) as f:
        lines = f.readlines()

    assert len(lines) == 25
