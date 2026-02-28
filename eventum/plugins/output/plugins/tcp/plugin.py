"""Definition of tcp output plugin."""

import asyncio
import contextlib
import ssl
from collections.abc import Sequence
from typing import override

from eventum.plugins.exceptions import PluginConfigurationError
from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.plugins.output.plugins.tcp.config import TcpOutputPluginConfig
from eventum.plugins.output.ssl import create_ssl_context


class TcpOutputPlugin(
    OutputPlugin[TcpOutputPluginConfig, OutputPluginParams],
):
    """Output plugin for sending events over TCP connection."""

    @override
    def __init__(
        self,
        config: TcpOutputPluginConfig,
        params: OutputPluginParams,
    ) -> None:
        super().__init__(config, params)

        self._ssl_context: ssl.SSLContext | None = None

        if config.ssl:
            try:
                self._ssl_context = create_ssl_context(
                    verify=config.verify,
                    ca_cert=(
                        self.resolve_path(config.ca_cert)
                        if config.ca_cert
                        else None
                    ),
                    client_cert=(
                        self.resolve_path(config.client_cert)
                        if config.client_cert
                        else None
                    ),
                    client_key=(
                        self.resolve_path(
                            config.client_cert_key,
                        )
                        if config.client_cert_key
                        else None
                    ),
                )
            except OSError as e:
                msg = 'Failed to create SSL context'
                raise PluginConfigurationError(
                    msg,
                    context={'reason': str(e)},
                ) from e

        self._writer: asyncio.StreamWriter

    @override
    async def _open(self) -> None:
        try:
            _, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host=self._config.host,
                    port=self._config.port,
                    ssl=self._ssl_context,
                ),
                timeout=self._config.connect_timeout,
            )
        except TimeoutError as e:
            msg = 'Connection timed out'
            raise PluginOpenError(
                msg,
                context={
                    'host': self._config.host,
                    'port': self._config.port,
                    'timeout': self._config.connect_timeout,
                },
            ) from e
        except OSError as e:
            msg = 'Failed to connect'
            raise PluginOpenError(
                msg,
                context={
                    'reason': str(e),
                    'host': self._config.host,
                    'port': self._config.port,
                },
            ) from e

        await self._logger.adebug(
            'TCP connection established',
            host=self._config.host,
            port=self._config.port,
            ssl=self._config.ssl,
        )

    @override
    async def _close(self) -> None:
        self._writer.close()
        try:
            await self._writer.wait_closed()
        except OSError as e:
            await self._logger.aerror(
                'Error while closing TCP connection',
                reason=str(e),
            )

    async def _reconnect(self) -> None:
        """Reconnect to TCP server after connection loss."""
        self._writer.close()
        with contextlib.suppress(OSError):
            await self._writer.wait_closed()

        try:
            _, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host=self._config.host,
                    port=self._config.port,
                    ssl=self._ssl_context,
                ),
                timeout=self._config.connect_timeout,
            )
        except (TimeoutError, OSError) as e:
            msg = 'Failed to reconnect'
            raise PluginWriteError(
                msg,
                context={
                    'reason': str(e),
                    'host': self._config.host,
                    'port': self._config.port,
                },
            ) from e

        await self._logger.adebug(
            'TCP connection re-established',
            host=self._config.host,
            port=self._config.port,
        )

    @override
    async def _write(self, events: Sequence[str]) -> int:
        if self._writer.is_closing():
            await self._reconnect()

        try:
            data = b''.join(
                f'{event}{self._config.separator}'.encode(
                    encoding=self._config.encoding,
                )
                for event in events
            )
        except UnicodeEncodeError as e:
            msg = 'Cannot encode events'
            raise PluginWriteError(
                msg,
                context={'reason': str(e)},
            ) from e

        try:
            self._writer.write(data)
            await self._writer.drain()
        except OSError as e:
            msg = 'Failed to send events'
            raise PluginWriteError(
                msg,
                context={
                    'reason': str(e),
                    'host': self._config.host,
                    'port': self._config.port,
                },
            ) from e

        return len(events)
