"""Tests for file streaming utils."""

import asyncio
from pathlib import Path

from eventum.api.utils.file_streaming import stream_file


async def test_streams_existing_tail(tmp_path: Path) -> None:
    """Content within the end offset is yielded from the tail."""
    log = tmp_path / 'log.txt'
    log.write_text('hello world')
    stop = asyncio.Event()

    chunks: list[str] = []
    async for chunk in stream_file(path=log, end_offset=5, stop=stop):
        chunks.append(chunk)
        stop.set()

    assert ''.join(chunks) == 'world'


async def test_stop_already_set_yields_nothing(tmp_path: Path) -> None:
    """A stop set before iteration terminates without yielding."""
    log = tmp_path / 'log.txt'
    log.write_text('data')
    stop = asyncio.Event()
    stop.set()

    chunks = [
        chunk
        async for chunk in stream_file(path=log, end_offset=10, stop=stop)
    ]

    assert chunks == []


async def test_idle_stream_stops_when_stop_set(tmp_path: Path) -> None:
    """An idle tail (no new content) ends promptly once stop is set.

    This is the regression guard: before the cooperative stop the loop
    parked in a fixed sleep and only a forced cancellation could end it.
    """
    log = tmp_path / 'log.txt'
    log.write_text('')
    stop = asyncio.Event()

    async def drain() -> list[str]:
        return [
            chunk
            async for chunk in stream_file(path=log, end_offset=0, stop=stop)
        ]

    task = asyncio.create_task(drain())
    await asyncio.sleep(0.05)
    stop.set()

    chunks = await asyncio.wait_for(task, timeout=1.0)
    assert chunks == []


async def test_new_content_then_stop(tmp_path: Path) -> None:
    """New content appended while idling is streamed before stopping."""
    log = tmp_path / 'log.txt'
    log.write_text('')
    stop = asyncio.Event()
    chunks: asyncio.Queue[str] = asyncio.Queue()

    async def drain() -> None:
        async for chunk in stream_file(path=log, end_offset=0, stop=stop):
            await chunks.put(chunk)

    task = asyncio.create_task(drain())
    await asyncio.sleep(0.05)
    with log.open('a') as f:
        f.write('appended')

    received = await asyncio.wait_for(chunks.get(), timeout=2.0)
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)

    assert received == 'appended'
