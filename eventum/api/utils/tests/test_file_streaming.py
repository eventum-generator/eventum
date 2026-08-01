"""Tests for file streaming utils."""

import asyncio
from pathlib import Path

import aiofiles

from eventum.api.utils.file_streaming import (
    _SNAPSHOT_CHUNK_SIZE,
    stream_file,
    stream_snapshot,
)


async def test_snapshot_streams_whole_file(tmp_path: Path) -> None:
    """Content of the file is streamed and the file is closed."""
    target = tmp_path / 'data.txt'
    target.write_bytes(b'hello world')
    file = await aiofiles.open(target, 'rb')

    chunks = [chunk async for chunk in stream_snapshot(file)]

    assert b''.join(chunks) == b'hello world'
    assert file.closed


async def test_snapshot_streams_empty_file(tmp_path: Path) -> None:
    """An empty file yields nothing."""
    target = tmp_path / 'data.txt'
    target.write_bytes(b'')
    file = await aiofiles.open(target, 'rb')

    chunks = [chunk async for chunk in stream_snapshot(file)]

    assert chunks == []
    assert file.closed


async def test_snapshot_excludes_appended_content(tmp_path: Path) -> None:
    """Content appended while streaming is left out of the stream.

    This is the regression guard: the response used to declare the file
    size up front and then stream everything the file held, so a
    generator appending to the file broke the response in the middle of
    the body.
    """
    target = tmp_path / 'data.txt'
    original = b'a' * (_SNAPSHOT_CHUNK_SIZE * 2)
    target.write_bytes(original)
    file = await aiofiles.open(target, 'rb')

    stream = stream_snapshot(file)
    chunks = [await anext(stream)]

    with target.open('ab') as f:
        f.write(b'b' * _SNAPSHOT_CHUNK_SIZE)

    chunks.extend([chunk async for chunk in stream])

    assert b''.join(chunks) == original


async def test_snapshot_ends_on_truncated_file(tmp_path: Path) -> None:
    """Truncation while streaming ends the stream on the read content.

    How much of the file is already read at the moment of truncation
    depends on the buffering, so only the invariant is asserted: the
    stream ends, and what it yields is a prefix of the original content.
    """
    target = tmp_path / 'data.txt'
    original = bytes(range(256)) * (_SNAPSHOT_CHUNK_SIZE * 3 // 256)
    target.write_bytes(original)
    file = await aiofiles.open(target, 'rb')

    stream = stream_snapshot(file)
    chunks = [await anext(stream)]

    target.write_bytes(b'')

    chunks.extend([chunk async for chunk in stream])

    assert original.startswith(b''.join(chunks))
    assert file.closed


async def test_snapshot_closes_abandoned_file(tmp_path: Path) -> None:
    """An abandoned stream closes the file it owns."""
    target = tmp_path / 'data.txt'
    target.write_bytes(b'a' * (_SNAPSHOT_CHUNK_SIZE * 2))
    file = await aiofiles.open(target, 'rb')

    stream = stream_snapshot(file)
    await anext(stream)
    await stream.aclose()

    assert file.closed


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
