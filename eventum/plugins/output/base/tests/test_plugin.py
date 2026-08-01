from collections.abc import Sequence
from typing import override

import pytest

from eventum.plugins.output.base.config import OutputPluginConfig
from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginWriteError
from eventum.plugins.output.fields import (
    Format,
    FormatterConfigT,
    JsonFormatterConfig,
    TemplateFormatterConfig,
)


class DummyOutputPluginConfig(OutputPluginConfig, frozen=True):
    """Config of dummy output plugin."""


class DummyOutputPlugin(
    OutputPlugin[DummyOutputPluginConfig, OutputPluginParams],
    register=False,
):
    """Output plugin that keeps written events in memory.

    Parameters
    ----------
    written : int | None, default=None
        Number of events to report as written, all provided events are
        reported as written if not specified.

    error : Exception | None, default=None
        Error to raise instead of writing events.

    """

    @override
    def __init__(
        self,
        config: DummyOutputPluginConfig,
        params: OutputPluginParams,
        written: int | None = None,
        error: Exception | None = None,
    ) -> None:
        super().__init__(config, params)

        self.written_events: list[str] = []

        self._reported_written = written
        self._error = error

    @override
    async def _open(self) -> None: ...

    @override
    async def _close(self) -> None: ...

    @override
    async def _write(self, events: Sequence[str]) -> int:
        if self._error is not None:
            raise self._error

        self.written_events.extend(events)

        if self._reported_written is None:
            return len(events)

        return self._reported_written


def create_plugin(
    formatter_config: FormatterConfigT,
    written: int | None = None,
    error: Exception | None = None,
) -> DummyOutputPlugin:
    return DummyOutputPlugin(
        config=DummyOutputPluginConfig(formatter=formatter_config),
        params={'id': 1},
        written=written,
        error=error,
    )


@pytest.mark.asyncio
async def test_format_failed_counts_rejected_events():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON))

    await plugin.open()
    written = await plugin.write(['{"a": 1}', 'not a json', '{"b": 2}'])
    await plugin.close()

    assert written == 2
    assert plugin.written == 2
    assert plugin.format_failed == 1
    assert plugin.write_failed == 0
    assert plugin.written_events == ['{"a": 1}', '{"b": 2}']


@pytest.mark.asyncio
async def test_format_failed_is_zero_for_valid_events():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON))

    await plugin.open()
    written = await plugin.write(['{"a": 1}', '{"b": 2}'])
    await plugin.close()

    assert written == 2
    assert plugin.format_failed == 0


@pytest.mark.asyncio
async def test_format_failed_counts_events_of_rejected_batch():
    plugin = create_plugin(
        TemplateFormatterConfig(
            format=Format.TEMPLATE_BATCH,
            template='{{ 1 / 0 }}',
        ),
    )

    await plugin.open()
    written = await plugin.write(['event1', 'event2', 'event3'])
    await plugin.close()

    assert written == 0
    assert plugin.written == 0
    assert plugin.format_failed == 3
    assert plugin.written_events == []


@pytest.mark.asyncio
async def test_nothing_is_written_when_all_aggregated_events_rejected():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON_BATCH))

    await plugin.open()
    written = await plugin.write(['not a json', 'also not a json'])
    await plugin.close()

    assert written == 0
    assert plugin.format_failed == 2
    assert plugin.written_events == []


@pytest.mark.asyncio
async def test_format_failed_counts_all_events_on_formatter_error():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON))

    def raise_error(_events: Sequence[str]) -> None:
        msg = 'Formatter is broken'
        raise RuntimeError(msg)

    plugin._formatter.format_events = raise_error

    await plugin.open()

    with pytest.raises(RuntimeError):
        await plugin.write(['{"a": 1}', '{"b": 2}'])

    await plugin.close()

    assert plugin.format_failed == 2
    assert plugin.written == 0


@pytest.mark.asyncio
async def test_format_failed_is_reset_on_open():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON))

    await plugin.open()
    await plugin.write(['not a json'])
    await plugin.close()

    assert plugin.format_failed == 1

    await plugin.open()

    assert plugin.format_failed == 0


@pytest.mark.asyncio
async def test_write_failed_is_zero_for_written_events():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON))

    await plugin.open()
    written = await plugin.write(['{"a": 1}', '{"a": 2}', '{"a": 3}'])
    await plugin.close()

    assert written == 3
    assert plugin.written == 3
    assert plugin.write_failed == 0


@pytest.mark.asyncio
async def test_write_failed_counts_unwritten_events():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON), written=2)

    await plugin.open()
    written = await plugin.write(['{"a": 1}', '{"a": 2}', '{"a": 3}'])
    await plugin.close()

    assert written == 2
    assert plugin.written == 2
    assert plugin.write_failed == 1


@pytest.mark.asyncio
async def test_write_failed_excludes_unformatted_events():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON), written=1)

    await plugin.open()
    written = await plugin.write(['{"a": 1}', '{"a": 2}', 'not a json'])
    await plugin.close()

    assert written == 1
    assert plugin.written == 1
    assert plugin.format_failed == 1
    assert plugin.write_failed == 1


@pytest.mark.asyncio
async def test_write_failed_counts_all_events_on_write_error():
    plugin = create_plugin(
        JsonFormatterConfig(format=Format.JSON),
        error=PluginWriteError('Plugin is broken', context={}),
    )

    await plugin.open()

    with pytest.raises(PluginWriteError):
        await plugin.write(['{"a": 1}', '{"a": 2}', '{"a": 3}'])

    await plugin.close()

    assert plugin.written == 0
    assert plugin.write_failed == 3


@pytest.mark.asyncio
async def test_write_failed_is_zero_for_written_aggregated_events():
    plugin = create_plugin(
        JsonFormatterConfig(format=Format.JSON_BATCH),
        written=1,
    )

    await plugin.open()
    written = await plugin.write(['{"a": 1}', '{"a": 2}', '{"a": 3}'])
    await plugin.close()

    assert written == 3
    assert plugin.written == 3
    assert plugin.write_failed == 0


@pytest.mark.asyncio
async def test_write_failed_counts_events_of_unwritten_aggregated_event():
    plugin = create_plugin(
        JsonFormatterConfig(format=Format.JSON_BATCH),
        written=0,
    )

    await plugin.open()
    written = await plugin.write(['{"a": 1}', '{"a": 2}', '{"a": 3}'])
    await plugin.close()

    assert written == 0
    assert plugin.written == 0
    assert plugin.write_failed == 3


@pytest.mark.asyncio
async def test_write_failed_is_zero_for_excess_written_events():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON), written=5)

    await plugin.open()
    written = await plugin.write(['{"a": 1}', '{"a": 2}', '{"a": 3}'])
    await plugin.close()

    assert written == 5
    assert plugin.write_failed == 0


@pytest.mark.asyncio
async def test_write_failed_is_reset_on_open():
    plugin = create_plugin(JsonFormatterConfig(format=Format.JSON), written=0)

    await plugin.open()
    await plugin.write(['{"a": 1}'])
    await plugin.close()

    assert plugin.write_failed == 1

    await plugin.open()

    assert plugin.write_failed == 0
