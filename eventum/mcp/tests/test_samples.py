"""Tests for describe_sample tool."""

from pathlib import Path

import pytest

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.samples import describe_sample

_EXAMPLE_ROWS_LIMIT = 5


@pytest.fixture
def ctx(tmp_path: Path) -> FileAuthoringContext:
    """Return a read-only FileAuthoringContext rooted at tmp_path."""
    return FileAuthoringContext(generators_dir=tmp_path, read_only=True)


def _make_gen(ctx: FileAuthoringContext, csv_text: str) -> str:
    gen = ctx.generators_dir / 'g'
    (gen / 'samples').mkdir(parents=True)
    (gen / 'generator.yml').write_text('input: []\nevent: {}\noutput: []\n')
    (gen / 'samples' / 'data.csv').write_text(csv_text)
    return 'g'


def test_describe_sample_csv(ctx: FileAuthoringContext) -> None:
    """describe_sample returns correct metadata for a CSV sample."""
    name = _make_gen(ctx, 'city,country\nParis,FR\nLyon,FR\n')
    result = describe_sample(ctx, name=name, relative_path='samples/data.csv')
    assert not isinstance(result, ToolFailure)
    assert result['type'] == 'csv'
    assert result['columns'] == ['city', 'country']
    assert result['row_count'] == len(['Paris,FR', 'Lyon,FR'])
    assert len(result['example_rows']) <= _EXAMPLE_ROWS_LIMIT


def test_describe_sample_traversal_rejected(
    ctx: FileAuthoringContext,
) -> None:
    """describe_sample rejects parent directory traversal."""
    _make_gen(ctx, 'a\n1\n')
    result = describe_sample(ctx, name='g', relative_path='../../etc/passwd')
    assert isinstance(result, ToolFailure)


def test_describe_sample_missing_file(ctx: FileAuthoringContext) -> None:
    """describe_sample returns ToolFailure for a non-existent file."""
    _make_gen(ctx, 'a\n1\n')
    result = describe_sample(ctx, name='g', relative_path='samples/nope.csv')
    assert isinstance(result, ToolFailure)


def test_describe_sample_unsupported_type(
    ctx: FileAuthoringContext,
) -> None:
    """describe_sample returns ToolFailure for unsupported file types."""
    gen = ctx.generators_dir / 'g'
    (gen / 'samples').mkdir(parents=True, exist_ok=True)
    (gen / 'samples' / 'data.txt').write_text('hello\n')
    result = describe_sample(ctx, name='g', relative_path='samples/data.txt')
    assert isinstance(result, ToolFailure)


def test_describe_sample_load_failure_hides_absolute_path(
    ctx: FileAuthoringContext,
) -> None:
    """A sample-load failure must not leak the absolute file path.

    A malformed CSV raises a SampleLoadError carrying the absolute
    resolved path in its context; the tool must relativize it so no
    absolute path string reaches the agent.
    """
    # Inconsistent column counts trigger a load error.
    _make_gen(ctx, 'a,b,c\n1,2\n3,4,5,6\n')
    result = describe_sample(ctx, name='g', relative_path='samples/data.csv')
    assert isinstance(result, ToolFailure)

    abs_dir = str(ctx.generators_dir.resolve())
    assert abs_dir not in repr(result.details)
    assert abs_dir not in result.error


def test_describe_sample_json(ctx: FileAuthoringContext) -> None:
    """describe_sample returns correct metadata for a JSON sample."""
    gen = ctx.generators_dir / 'g'
    (gen / 'samples').mkdir(parents=True, exist_ok=True)
    (gen / 'generator.yml').write_text('input: []\nevent: {}\noutput: []\n')
    (gen / 'samples' / 'data.json').write_text(
        '[{"city": "Paris", "country": "FR"},'
        ' {"city": "Lyon", "country": "FR"}]'
    )
    result = describe_sample(ctx, name='g', relative_path='samples/data.json')
    assert not isinstance(result, ToolFailure)
    assert result['type'] == 'json'
    assert set(result['columns']) == {'city', 'country'}
    assert result['row_count'] == len(['Paris', 'Lyon'])
