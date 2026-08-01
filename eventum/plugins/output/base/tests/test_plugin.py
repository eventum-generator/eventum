from collections.abc import Sequence
from typing import override

import pytest

from eventum.plugins.output.base.config import OutputPluginConfig
from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
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
    """Output plugin that keeps written events in memory."""

    @override
    def __init__(
        self,
        config: DummyOutputPluginConfig,
        params: OutputPluginParams,
    ) -> None:
        super().__init__(config, params)

        self.written_events: list[str] = []

    @override
    async def _open(self) -> None: ...

    @override
    async def _close(self) -> None: ...

    @override
    async def _write(self, events: Sequence[str]) -> int:
        self.written_events.extend(events)
        return len(events)


def create_plugin(formatter_config: FormatterConfigT) -> DummyOutputPlugin:
    return DummyOutputPlugin(
        config=DummyOutputPluginConfig(formatter=formatter_config),
        params={'id': 1},
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
