"""Tests for describe_sample tool."""

import asyncio
import threading
from pathlib import Path
from typing import Any

import pytest

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.samples import describe_sample
from eventum.plugins.event.plugins.template.sample_reader import (
    SamplesReader,
)

_EXAMPLE_ROWS_LIMIT = 5


@pytest.fixture
def ctx(tmp_path: Path) -> FileAuthoringContext:
    """Return a read-only FileAuthoringContext rooted at tmp_path."""
    return FileAuthoringContext(generators_dir=tmp_path, read_only=True)


def _make_gen(
    ctx: FileAuthoringContext,
    text: str,
    relative_path: str = 'samples/data.csv',
) -> str:
    gen = ctx.generators_dir / 'g'
    sample = gen / relative_path
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text(text)
    return 'g'


async def test_describe_sample_csv(ctx: FileAuthoringContext) -> None:
    """describe_sample returns correct metadata for a CSV sample."""
    name = _make_gen(ctx, 'city,country\nParis,FR\nLyon,FR\n')
    result = await describe_sample(
        ctx, name=name, relative_path='samples/data.csv'
    )
    assert not isinstance(result, ToolFailure)
    assert result['type'] == 'csv'
    assert result['columns'] == ['city', 'country']
    assert result['row_count'] == len(['Paris,FR', 'Lyon,FR'])
    assert len(result['example_rows']) <= _EXAMPLE_ROWS_LIMIT
    assert result['example_rows'] == [['Paris', 'FR'], ['Lyon', 'FR']]


async def test_describe_sample_traversal_rejected(
    ctx: FileAuthoringContext,
) -> None:
    """describe_sample rejects parent directory traversal."""
    _make_gen(ctx, 'a\n1\n')
    result = await describe_sample(
        ctx, name='g', relative_path='../../etc/passwd'
    )
    assert isinstance(result, ToolFailure)


async def test_describe_sample_missing_file(
    ctx: FileAuthoringContext,
) -> None:
    """describe_sample returns ToolFailure for a non-existent file."""
    _make_gen(ctx, 'a\n1\n')
    result = await describe_sample(
        ctx, name='g', relative_path='samples/nope.csv'
    )
    assert isinstance(result, ToolFailure)


async def test_describe_sample_unsupported_type(
    ctx: FileAuthoringContext,
) -> None:
    """describe_sample returns ToolFailure for unsupported file types."""
    _make_gen(ctx, 'hello\n', relative_path='samples/data.txt')
    result = await describe_sample(
        ctx, name='g', relative_path='samples/data.txt'
    )
    assert isinstance(result, ToolFailure)


async def test_describe_sample_uppercase_suffix_unsupported(
    ctx: FileAuthoringContext,
) -> None:
    """An uppercase suffix is an unsupported-type failure, not a raise.

    The sample config source validators accept only lowercase
    '.csv'/'.json'; an uppercase suffix must not reach them and
    escape as a raised ValidationError carrying the absolute path.
    """
    _make_gen(ctx, 'a,b\n1,2\n', relative_path='samples/data.CSV')
    result = await describe_sample(
        ctx, name='g', relative_path='samples/data.CSV'
    )
    assert isinstance(result, ToolFailure)
    assert result.error == 'Unsupported sample type'
    abs_dir = str(ctx.generators_dir.resolve())
    assert abs_dir not in result.error
    assert abs_dir not in repr(result.details)


async def test_describe_sample_symlink_suffix_mismatch(
    ctx: FileAuthoringContext,
) -> None:
    """A symlink resolving to another suffix fails cleanly.

    The resolved source then carries a non-matching suffix, so config
    validation rejects it; that must surface as a ToolFailure, not a
    raised ValidationError carrying the absolute resolved path.
    """
    _make_gen(ctx, 'plain text\n', relative_path='samples/data.txt')
    link = ctx.generators_dir / 'g' / 'samples' / 'data.csv'
    link.symlink_to(ctx.generators_dir / 'g' / 'samples' / 'data.txt')
    result = await describe_sample(
        ctx, name='g', relative_path='samples/data.csv'
    )
    assert isinstance(result, ToolFailure)
    abs_dir = str(ctx.generators_dir.resolve())
    assert abs_dir not in result.error
    assert abs_dir not in repr(result.details)


async def test_describe_sample_load_failure_hides_absolute_path(
    ctx: FileAuthoringContext,
) -> None:
    """A sample-load failure must not leak the absolute file path.

    A malformed CSV raises a SampleLoadError carrying the absolute
    resolved path in its context; the tool must relativize it so no
    absolute path string reaches the agent.
    """
    # Inconsistent column counts trigger a load error.
    _make_gen(ctx, 'a,b,c\n1,2\n3,4,5,6\n')
    result = await describe_sample(
        ctx, name='g', relative_path='samples/data.csv'
    )
    assert isinstance(result, ToolFailure)

    abs_dir = str(ctx.generators_dir.resolve())
    assert abs_dir not in repr(result.details)
    assert abs_dir not in result.error


async def test_describe_sample_json(ctx: FileAuthoringContext) -> None:
    """describe_sample returns correct metadata for a JSON sample."""
    _make_gen(
        ctx,
        '[{"city": "Paris", "country": "FR"},'
        ' {"city": "Lyon", "country": "FR"}]',
        relative_path='samples/data.json',
    )
    result = await describe_sample(
        ctx, name='g', relative_path='samples/data.json'
    )
    assert not isinstance(result, ToolFailure)
    assert result['type'] == 'json'
    assert set(result['columns']) == {'city', 'country'}
    assert result['row_count'] == len(['Paris', 'Lyon'])
    cols = result['columns']
    rows_by_col = [
        dict(zip(cols, r, strict=True)) for r in result['example_rows']
    ]
    assert rows_by_col == [
        {'city': 'Paris', 'country': 'FR'},
        {'city': 'Lyon', 'country': 'FR'},
    ]


async def test_describe_sample_parses_off_event_loop(
    ctx: FileAuthoringContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent describe_sample calls parse on worker threads.

    Reader construction blocks on a 2-party barrier, so the pair only
    completes if each call was offloaded via asyncio.to_thread; a call
    parsing inline on the event loop would block it and time out.
    """
    name = _make_gen(ctx, 'a,b\n1,2\n')
    barrier = threading.Barrier(2, timeout=5)

    class _BlockingReader(SamplesReader):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            barrier.wait()
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(
        'eventum.mcp.tools.samples.SamplesReader', _BlockingReader
    )
    results = await asyncio.gather(
        describe_sample(ctx, name=name, relative_path='samples/data.csv'),
        describe_sample(ctx, name=name, relative_path='samples/data.csv'),
    )
    for result in results:
        assert not isinstance(result, ToolFailure)
        assert result['columns'] == ['a', 'b']
