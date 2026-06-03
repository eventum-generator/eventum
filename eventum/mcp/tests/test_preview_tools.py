"""Tests for validate and preview MCP tools."""

import functools
from pathlib import Path
from typing import Any
from unittest.mock import patch

import anyio
import pytest

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure

_LINSPACE_CONFIG = (
    'input:\n'
    '  - linspace:\n'
    '      start: "2025-01-01 00:00:00"\n'
    '      end: "2025-01-01 01:00:00"\n'
    '      count: 10\n'
    'event:\n'
    '  script:\n'
    '    path: produce.py\n'
    'output:\n'
    '  - stdout:\n'
    '      stream: stderr\n'
)

_PRODUCE_PY = 'def produce(params):\n    return [str(params["timestamp"])]\n'

_SAMPLE_COUNT = 5


@pytest.fixture
def gen_dir(tmp_path: Path) -> Path:
    """Create a minimal valid generator directory."""
    g = tmp_path / 'gen'
    g.mkdir()
    (g / 'generator.yml').write_text(_LINSPACE_CONFIG)
    (g / 'produce.py').write_text(_PRODUCE_PY)
    return tmp_path


@pytest.fixture
def ctx(gen_dir: Path) -> FileAuthoringContext:
    """AuthoringContext rooted at the tmp generators dir."""
    return FileAuthoringContext(generators_dir=gen_dir, read_only=True)


def test_validate_generator_valid(
    ctx: FileAuthoringContext,
) -> None:
    """validate_generator returns {'valid': True} for a correct config."""
    from eventum.mcp.tools.preview import validate_generator

    result: Any = anyio.run(validate_generator, ctx, 'gen')
    assert result == {'valid': True}


def test_validate_generator_unknown_plugin(
    tmp_path: Path,
) -> None:
    """validate_generator returns ToolFailure for an unknown plugin."""
    from eventum.mcp.tools.preview import validate_generator

    g = tmp_path / 'bad'
    g.mkdir()
    bad_config = (
        'input:\n'
        '  - linspace:\n'
        '      start: "2025-01-01 00:00:00"\n'
        '      end: "2025-01-01 01:00:00"\n'
        '      count: 10\n'
        'event:\n'
        '  no_such_plugin:\n'
        '    some_field: value\n'
        'output:\n'
        '  - stdout:\n'
        '      stream: stderr\n'
    )
    (g / 'generator.yml').write_text(bad_config)

    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=True)
    result = anyio.run(validate_generator, ctx, 'bad')

    assert isinstance(result, ToolFailure)
    assert result.error


def test_validate_generator_missing_dir(
    tmp_path: Path,
) -> None:
    """validate_generator returns ToolFailure when generator is missing."""
    from eventum.mcp.tools.preview import validate_generator

    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=True)
    result = anyio.run(validate_generator, ctx, 'nonexistent')

    assert isinstance(result, ToolFailure)


def test_preview_timestamps_returns_aggregate(
    ctx: FileAuthoringContext,
) -> None:
    """preview_timestamps returns dict with total and span_counts."""
    from eventum.mcp.tools.preview import preview_timestamps

    fn = functools.partial(preview_timestamps, ctx, 'gen', 50, skip_past=False)
    result: Any = anyio.run(fn)

    assert isinstance(result, dict)
    assert 'total' in result
    assert 'span_counts' in result
    assert result['total'] >= 1


def test_preview_events_returns_sample(
    ctx: FileAuthoringContext,
) -> None:
    """preview_events returns dict with events, errors, exhausted."""
    from eventum.mcp.tools.preview import preview_events

    fn = functools.partial(
        preview_events, ctx, 'gen', _SAMPLE_COUNT, skip_past=False
    )
    result: Any = anyio.run(fn)

    assert isinstance(result, dict)
    assert 'events' in result
    assert 'errors' in result
    assert 'exhausted' in result
    assert isinstance(result['events'], list)
    assert len(result['events']) <= _SAMPLE_COUNT
    assert result['events']
    assert all(isinstance(e, str) for e in result['events'])


def test_preview_events_exhausted_is_bool(
    ctx: FileAuthoringContext,
) -> None:
    """preview_events exhausted field is always a bool."""
    from eventum.mcp.tools.preview import preview_events

    fn = functools.partial(
        preview_events, ctx, 'gen', _SAMPLE_COUNT, skip_past=False
    )
    result: Any = anyio.run(fn)

    assert isinstance(result['exhausted'], bool)


def test_validate_generator_redacts_secret_in_error(
    tmp_path: Path,
) -> None:
    """A resolved secret value never reaches the returned ToolFailure.

    The config references ``${secrets.DB_PASS}`` in an integer field as a
    quoted string, so the resolved value is substituted verbatim and then
    surfaces in the integer-parsing validation error. ``get_secret`` is
    patched at both lookup sites (``config_loader`` resolves the token,
    ``preview`` collects the value for redaction) so no real keyring is
    needed. The test also asserts the value WOULD leak with redaction
    bypassed, proving the assertion is not vacuous.
    """
    from eventum.mcp.tools.preview import validate_generator

    plaintext = 'NOTANUMBER_x9Kq2mPw7nRv'

    g = tmp_path / 'sec'
    g.mkdir()
    # `count` is quoted so the secret stays a string; integer validation
    # then fails with the value echoed in the error reason.
    gen_yaml = (
        'input:\n'
        '  - linspace:\n'
        '      start: "2025-01-01 00:00:00"\n'
        '      end: "2025-01-01 01:00:00"\n'
        '      count: "${secrets.DB_PASS}"\n'
        'event:\n'
        '  script:\n'
        '    path: produce.py\n'
        'output:\n'
        '  - stdout:\n'
        '      stream: stderr\n'
    )
    (g / 'generator.yml').write_text(gen_yaml)
    (g / 'produce.py').write_text(_PRODUCE_PY)

    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=True)

    with (
        patch(
            'eventum.core.config_loader.get_secret',
            return_value=plaintext,
        ),
        patch(
            'eventum.mcp.tools.preview.get_secret',
            return_value=plaintext,
        ),
    ):
        result = anyio.run(validate_generator, ctx, 'sec')

        # Sanity: with redaction bypassed the secret WOULD leak. This
        # guards against the test passing because the value never
        # reached the error in the first place.
        with patch(
            'eventum.mcp.tools.preview._read_secret_values',
            return_value=[],
        ):
            leaked = anyio.run(validate_generator, ctx, 'sec')

    assert isinstance(leaked, ToolFailure)
    assert plaintext in (str(leaked.error) + str(leaked.details))

    assert isinstance(result, ToolFailure)
    failure_text = str(result.error) + str(result.details)
    assert plaintext not in failure_text
