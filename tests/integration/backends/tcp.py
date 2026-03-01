"""TCP backend consumer for integration tests.

Runs an in-process asyncio TCP server that collects events sent
by the TCP output plugin.
"""

import asyncio

from tests.integration.backends.base import BackendConsumer


class TcpConsumer(BackendConsumer):
    """In-process TCP server that buffers incoming events.

    Listens on a configurable host and port (default ``port=0``
    for OS-assigned ephemeral port). Splits incoming data by the
    configured separator to extract individual event messages.
    """

    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 0,
        separator: str = '\n',
    ) -> None:
        self._host = host
        self._requested_port = port
        self._separator = separator
        self._actual_port: int | None = None
        self._messages: list[str] = []
        self._server: asyncio.Server | None = None
        self._buffers: dict[
            asyncio.StreamWriter, str
        ] = {}

    @property
    def host(self) -> str:
        """Bound host address."""
        return self._host

    @property
    def port(self) -> int:
        """Actual bound port (resolved after ``setup()``)."""
        if self._actual_port is None:
            msg = (
                'Port is not available until setup() is called'
            )
            raise RuntimeError(msg)
        return self._actual_port

    async def setup(self) -> None:
        """Start the TCP server and begin accepting connections."""
        self._server = await asyncio.start_server(
            self._handle_client,
            host=self._host,
            port=self._requested_port,
        )

        # Resolve the actual bound port
        sockets = self._server.sockets
        assert sockets, 'Server has no bound sockets'
        self._actual_port = sockets[0].getsockname()[1]

    async def teardown(self) -> None:
        """Stop the server and close all client connections."""
        if self._server is None:
            return

        self._server.close()
        await self._server.wait_closed()
        self._server = None
        self._actual_port = None
        self._buffers.clear()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Read data from a connected client.

        Incoming bytes are decoded and split by the separator.
        Incomplete trailing fragments are buffered until more
        data arrives or the connection closes.

        Parameters
        ----------
        reader : asyncio.StreamReader
            Stream to read incoming data from.
        writer : asyncio.StreamWriter
            Stream writer for the connection (kept for tracking).

        """
        self._buffers[writer] = ''

        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break

                text = self._buffers[writer] + data.decode(
                    'utf-8',
                )
                parts = text.split(self._separator)

                # Last element is either empty (if data ended with
                # separator) or an incomplete fragment to buffer
                self._buffers[writer] = parts[-1]

                for part in parts[:-1]:
                    if part:
                        self._messages.append(part)
        finally:
            # Flush any remaining buffered data
            remaining = self._buffers.pop(writer, '')
            if remaining:
                self._messages.append(remaining)

            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def consume_all(
        self,
        timeout: float = 10.0,
    ) -> list[str]:
        """Return a copy of all received messages.

        Parameters
        ----------
        timeout : float
            Not directly used for TCP but kept for interface
            consistency.

        Returns
        -------
        list[str]
            Copy of the internal message list.

        """
        return list(self._messages)

    async def count(self) -> int:
        """Return the number of received messages.

        Returns
        -------
        int
            Message count.

        """
        return len(self._messages)

    def clear(self) -> None:
        """Clear the internal message list.

        Useful for resetting state between test phases without
        restarting the server.
        """
        self._messages.clear()
