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

_CLOSE_TIMEOUT = 5.0
"""Seconds a closing connection is given to deliver what it buffered."""


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
        await self._drop_connection()

    async def _drop_connection(self) -> None:
        """Close the connection, giving up on what it cannot flush.

        Notes
        -----
        Closing a connection waits for the data still buffered in it to
        reach the target, which a target that stopped reading never
        lets happen. The wait is therefore bounded, and what is left
        after it is discarded along with the connection.

        """
        buffered = self._writer.transport.get_write_buffer_size()
        self._writer.close()

        try:
            await asyncio.wait_for(
                self._writer.wait_closed(),
                timeout=_CLOSE_TIMEOUT,
            )
        except TimeoutError:
            self._writer.transport.abort()
            await self._logger.awarning(
                'Connection dropped with data still awaiting delivery',
                host=self._config.host,
                port=self._config.port,
                size=buffered,
            )
        except OSError as e:
            await self._logger.aerror(
                'Error while closing TCP connection',
                reason=str(e),
            )

    async def _reconnect(self) -> None:
        """Reconnect to TCP server after connection loss."""
        with contextlib.suppress(OSError):
            await self._drop_connection()

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

    def _check_target_keeps_up(self) -> None:
        """Check the connection is not backed up with undelivered data.

        Raises
        ------
        PluginWriteError
            If the data awaiting delivery is over what the connection
            buffers before it asks to be drained.

        Notes
        -----
        Handing data to a connection never blocks and is bounded by
        nothing, so a target that stopped reading would have the events
        of every batch pile up in the buffer. Refusing to add to a
        buffer that is already over its mark bounds it at that mark plus
        one batch, and the events are reported as failed - which they
        are, nothing delivered them.

        """
        transport = self._writer.transport
        buffered = transport.get_write_buffer_size()
        _, high_water_mark = transport.get_write_buffer_limits()

        if buffered > high_water_mark:
            msg = 'Target is not accepting data fast enough'
            raise PluginWriteError(
                msg,
                context={
                    'host': self._config.host,
                    'port': self._config.port,
                    'size': buffered,
                },
            )

    @override
    async def _write(self, events: Sequence[str]) -> int:
        if self._writer.is_closing():
            await self._reconnect()

        self._check_target_keeps_up()

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
        except asyncio.CancelledError:
            # The batch sits in the buffer of the connection already and
            # nothing is going to flush it now that the write is given
            # up on, so the connection goes with it.
            self._writer.transport.abort()
            raise
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
