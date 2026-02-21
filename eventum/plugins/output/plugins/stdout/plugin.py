"""Definition of stdout output plugin."""

import asyncio
from collections.abc import Sequence
from typing import assert_never, override

from aioconsole import get_standard_streams  # type: ignore[import-untyped]

from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginWriteError
from eventum.plugins.output.plugins.stdout.config import (
    StdoutOutputPluginConfig,
)


class StdoutOutputPlugin(
    OutputPlugin[StdoutOutputPluginConfig, OutputPluginParams],
):
    """Output plugin for writing events to stdout."""

    @override
    def __init__(
        self,
        config: StdoutOutputPluginConfig,
        params: OutputPluginParams,
    ) -> None:
        super().__init__(config, params)

        self._writer: asyncio.StreamWriter
        self._flushing_task: asyncio.Task

    async def _start_flushing(self) -> None:
        """Start flushing cycle based on specified flush interval."""
        if self._config.flush_interval == 0:
            return

        while True:
            await asyncio.sleep(self._config.flush_interval)
            await self._writer.drain()

    @override
    async def _open(self) -> None:
        match self._config.stream:
            case 'stdout':
                use_stderr = False
            case 'stderr':
                use_stderr = True
            case val:
                assert_never(val)

        _, self._writer = await get_standard_streams(use_stderr=use_stderr)
        self._flushing_task = self._loop.create_task(self._start_flushing())

    @override
    async def _close(self) -> None:
        self._flushing_task.cancel()
        await self._writer.drain()

    @override
    async def _write(self, events: Sequence[str]) -> int:
        try:
            lines = [
                f'{event}{self._config.separator}'.encode(
                    encoding=self._config.encoding,
                )
                for event in events
            ]
        except UnicodeEncodeError as e:
            msg = 'Cannot encode events'
            raise PluginWriteError(
                msg,
                context={'reason': str(e)},
            ) from e

        for line in lines:
            self._writer.write(line)

        if self._config.flush_interval == 0:
            await self._writer.drain()

        return len(events)
