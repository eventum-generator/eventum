"""Stream a log file to a WebSocket until disconnect or shutdown."""

import asyncio
import contextlib
from pathlib import Path

from fastapi import (
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)

from eventum.api.utils.file_streaming import stream_file


async def stream_log_file_to_websocket(
    websocket: WebSocket,
    path: Path,
    end_offset: int,
) -> None:
    """Tail a log file to the websocket until disconnect or shutdown.

    A concurrent watcher reads from the socket so a peer disconnect or a
    server-initiated close is noticed even while the tail idles between
    reads. The stream then ends cooperatively and the file closes
    cleanly, instead of being force-cancelled mid-read on shutdown.

    Parameters
    ----------
    websocket : WebSocket
        Accepted websocket to stream chunks to.

    path : Path
        Path to the log file to tail.

    end_offset : int
        Offset from the end of the file to start streaming from.

    Raises
    ------
    WebSocketException
        With ``WS_1011_INTERNAL_ERROR`` if the log file cannot be read
        while the peer is still connected.

    """
    stop = asyncio.Event()
    watcher = asyncio.create_task(_watch_disconnect(websocket, stop))
    try:
        async for content in stream_file(path, end_offset, stop):
            try:
                await websocket.send_text(content)
            except WebSocketDisconnect, RuntimeError:
                # A send failing here means the peer is already gone:
                # WebSocketDisconnect on a clean close, or a RuntimeError
                # from the ASGI server when the disconnect the watcher
                # observed raced ahead of this send.
                break
    except OSError as e:
        if websocket.client_state.name == 'CONNECTED':
            raise WebSocketException(
                code=status.WS_1011_INTERNAL_ERROR,
                reason=f'Failed to read log file due to OS error: {e}',
            ) from None
    finally:
        stop.set()
        watcher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watcher


async def _watch_disconnect(
    websocket: WebSocket,
    stop: asyncio.Event,
) -> None:
    """Set ``stop`` as soon as the websocket peer disconnects."""
    try:
        while True:
            message = await websocket.receive()
            if message['type'] == 'websocket.disconnect':
                return
    finally:
        stop.set()
