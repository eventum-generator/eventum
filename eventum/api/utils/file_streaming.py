"""File streaming utils."""

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator
from pathlib import Path

import aiofiles

_IDLE_POLL_INTERVAL = 0.5


async def stream_file(
    path: Path,
    end_offset: int,
    stop: asyncio.Event,
) -> AsyncIterator[str]:
    """Stream file from the end until stopped.

    Tails the file from ``end_offset`` bytes before its end, yielding
    new content as it is appended. When no new content is available the
    call idles, waking on the poll interval or as soon as ``stop`` is
    set, so the stream terminates promptly on disconnect or shutdown
    instead of being force-cancelled mid-read.

    Parameters
    ----------
    path : Path
        Path to file to stream.

    end_offset : int
        Offset from the end of file to start streaming from.

    stop : asyncio.Event
        Signals the stream to terminate. Checked before each read and
        interrupts the idle wait.

    Yields
    ------
    str
        File chunk.

    Raises
    ------
    OSError
        If file cannot be read.

    """
    async with aiofiles.open(path) as f:
        await f.seek(0, os.SEEK_END)
        size = await f.tell()
        start_pos = max(0, size - end_offset)
        await f.seek(start_pos, os.SEEK_SET)

        while not stop.is_set():
            content = await f.read(8192)
            if content:
                yield content
            else:
                await _idle_wait(stop)


async def _idle_wait(stop: asyncio.Event) -> None:
    """Idle for the poll interval, returning early once stop is set."""
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=_IDLE_POLL_INTERVAL)
