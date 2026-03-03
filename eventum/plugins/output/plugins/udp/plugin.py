"""Definition of udp output plugin."""

import asyncio
from collections.abc import Sequence
from typing import override

import structlog

from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.plugins.output.plugins.udp.config import UdpOutputPluginConfig


class _ErrorProtocol(asyncio.DatagramProtocol):
    """Datagram protocol that captures ICMP errors on connected sockets."""

    def __init__(self, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger

    @override
    def error_received(self, exc: Exception) -> None:
        self._logger.error(
            'UDP socket error received',
            reason=str(exc),
        )


class UdpOutputPlugin(
    OutputPlugin[UdpOutputPluginConfig, OutputPluginParams],
):
    """Output plugin for sending events over UDP datagrams."""

    @override
    def __init__(
        self,
        config: UdpOutputPluginConfig,
        params: OutputPluginParams,
    ) -> None:
        super().__init__(config, params)
        self._transport: asyncio.DatagramTransport

    @override
    async def _open(self) -> None:
        loop = asyncio.get_running_loop()

        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _ErrorProtocol(self._logger),
                remote_addr=(self._config.host, self._config.port),
            )
        except OSError as e:
            msg = 'Failed to create UDP socket'
            raise PluginOpenError(
                msg,
                context={
                    'reason': str(e),
                    'host': self._config.host,
                    'port': self._config.port,
                },
            ) from e

        self._transport = transport  # type: ignore[assignment]

        await self._logger.adebug(
            'UDP socket opened',
            host=self._config.host,
            port=self._config.port,
        )

    @override
    async def _close(self) -> None:
        self._transport.close()

    @override
    async def _write(self, events: Sequence[str]) -> int:
        written = 0

        for event in events:
            try:
                data = f'{event}{self._config.separator}'.encode(
                    encoding=self._config.encoding,
                )
            except UnicodeEncodeError as e:
                await self._logger.aerror(
                    'Cannot encode event',
                    reason=str(e),
                )
                continue

            try:
                self._transport.sendto(data)
            except OSError as e:
                msg = 'Failed to send datagram'
                raise PluginWriteError(
                    msg,
                    context={
                        'reason': str(e),
                        'host': self._config.host,
                        'port': self._config.port,
                    },
                ) from e

            written += 1

        return written
