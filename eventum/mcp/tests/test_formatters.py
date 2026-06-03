"""Tests for formatter discovery tools."""

from pathlib import Path

import pytest

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.tools.formatters import get_formatter_schema, list_formatters
from eventum.plugins.output.fields import Format


@pytest.fixture
def ctx(tmp_path: Path) -> FileAuthoringContext:
    """Return a read-only FileAuthoringContext rooted at tmp_path."""
    return FileAuthoringContext(generators_dir=tmp_path, read_only=True)


def test_list_formatters_enumerates_formats(ctx: FileAuthoringContext) -> None:
    """list_formatters returns every known format with a description."""
    result = list_formatters(ctx)
    fmts = {f['format'] for f in result}
    assert fmts == {f.value for f in Format}
    assert all(f.get('description') for f in result)


def test_get_formatter_schema(ctx: FileAuthoringContext) -> None:
    """get_formatter_schema returns a valid JSON Schema for a known format."""
    result = get_formatter_schema(ctx, format='json')
    assert isinstance(result, dict)
    assert result['type'] == 'object'


def test_get_formatter_schema_unknown(ctx: FileAuthoringContext) -> None:
    """get_formatter_schema returns ToolFailure for an unknown format."""
    from eventum.mcp.errors import ToolFailure

    result = get_formatter_schema(ctx, format='nope')
    assert isinstance(result, ToolFailure)
