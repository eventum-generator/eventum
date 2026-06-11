"""Tests for validate and preview MCP tools."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

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

# Validates and initialises fine, but the timer end time overflows at
# generation time, raising PluginGenerationError from the input plugin.
_OVERFLOW_TIMER_CONFIG = (
    'input:\n'
    '  - timer:\n'
    '      start: "9999-01-01 00:00:00"\n'
    '      seconds: 100000\n'
    '      count: 1\n'
    '      repeat: 1000000\n'
    'event:\n'
    '  script:\n'
    '    path: produce.py\n'
    'output:\n'
    '  - stdout:\n'
    '      stream: stderr\n'
)


@pytest.fixture
def gen_dir(tmp_path: Path) -> Path:
    """Create a minimal valid generator directory."""
    g = tmp_path / 'gen'
    g.mkdir()
    (g / 'generator.yml').write_text(_LINSPACE_CONFIG)
    (g / 'produce.py').write_text(_PRODUCE_PY)
    return tmp_path


@pytest.fixture
def failing_gen_dir(tmp_path: Path) -> Path:
    """Create a generator that fails only at generation time."""
    g = tmp_path / 'gen'
    g.mkdir()
    (g / 'generator.yml').write_text(_OVERFLOW_TIMER_CONFIG)
    (g / 'produce.py').write_text(_PRODUCE_PY)
    return tmp_path


@pytest.fixture
def ctx(gen_dir: Path) -> FileAuthoringContext:
    """AuthoringContext rooted at the tmp generators dir."""
    return FileAuthoringContext(generators_dir=gen_dir, read_only=True)


async def test_validate_generator_valid(
    ctx: FileAuthoringContext,
) -> None:
    """validate_generator returns {'valid': True} for a correct config."""
    from eventum.mcp.tools.preview import validate_generator

    result: Any = await validate_generator(ctx, 'gen')
    assert result == {'valid': True}


async def test_validate_generator_unknown_plugin(
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
    result = await validate_generator(ctx, 'bad')

    assert isinstance(result, ToolFailure)
    assert result.error


async def test_validate_generator_honors_custom_config_filename(
    tmp_path: Path,
) -> None:
    """The context's config filename selects the loaded config file."""
    from eventum.mcp.tools.preview import validate_generator

    g = tmp_path / 'gen'
    g.mkdir()
    (g / 'custom.yml').write_text(_LINSPACE_CONFIG)
    (g / 'produce.py').write_text(_PRODUCE_PY)

    ctx = FileAuthoringContext(
        generators_dir=tmp_path,
        read_only=True,
        config_filename='custom.yml',
    )
    result: Any = await validate_generator(ctx, 'gen')
    assert result == {'valid': True}

    # Sanity: with the default filename the same generator is invisible.
    default_ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=True)
    missing = await validate_generator(default_ctx, 'gen')
    assert isinstance(missing, ToolFailure)


async def test_validate_generator_missing_dir(
    tmp_path: Path,
) -> None:
    """validate_generator returns ToolFailure when generator is missing."""
    from eventum.mcp.tools.preview import validate_generator

    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=True)
    result = await validate_generator(ctx, 'nonexistent')

    assert isinstance(result, ToolFailure)


async def test_preview_timestamps_returns_aggregate(
    ctx: FileAuthoringContext,
) -> None:
    """preview_timestamps returns dict with total and span_counts."""
    from eventum.mcp.tools.preview import preview_timestamps

    result: Any = await preview_timestamps(ctx, 'gen', 50, skip_past=False)

    assert isinstance(result, dict)
    assert 'total' in result
    assert 'span_counts' in result
    assert result['total'] >= 1


async def test_preview_events_returns_sample(
    ctx: FileAuthoringContext,
) -> None:
    """preview_events returns dict with events, errors, exhausted."""
    from eventum.mcp.tools.preview import preview_events

    result: Any = await preview_events(
        ctx, 'gen', _SAMPLE_COUNT, skip_past=False
    )

    assert isinstance(result, dict)
    assert 'events' in result
    assert 'errors' in result
    assert 'exhausted' in result
    assert isinstance(result['events'], list)
    assert len(result['events']) <= _SAMPLE_COUNT
    assert result['events']
    assert all(isinstance(e, str) for e in result['events'])


async def test_preview_events_exhausted_is_bool(
    ctx: FileAuthoringContext,
) -> None:
    """preview_events exhausted field is always a bool."""
    from eventum.mcp.tools.preview import preview_events

    result: Any = await preview_events(
        ctx, 'gen', _SAMPLE_COUNT, skip_past=False
    )

    assert isinstance(result['exhausted'], bool)


async def test_preview_timestamps_generation_error_in_band(
    failing_gen_dir: Path,
) -> None:
    """A generation-time plugin error returns ToolFailure, not raises."""
    from eventum.mcp.tools.preview import (
        preview_timestamps,
        validate_generator,
    )

    ctx = FileAuthoringContext(generators_dir=failing_gen_dir, read_only=True)

    # Sanity: the config passes validation, so the failure below can
    # only come from generation time.
    assert await validate_generator(ctx, 'gen') == {'valid': True}

    result = await preview_timestamps(ctx, 'gen', 10, skip_past=False)

    assert isinstance(result, ToolFailure)
    assert 'overflowed' in result.error


async def test_preview_events_generation_error_in_band(
    failing_gen_dir: Path,
) -> None:
    """A generation-time plugin error returns ToolFailure, not raises."""
    from eventum.mcp.tools.preview import preview_events

    ctx = FileAuthoringContext(generators_dir=failing_gen_dir, read_only=True)
    result = await preview_events(ctx, 'gen', _SAMPLE_COUNT, skip_past=False)

    assert isinstance(result, ToolFailure)
    assert 'overflowed' in result.error


@pytest.mark.parametrize(
    'tool_name',
    ['validate_generator', 'preview_timestamps', 'preview_events'],
)
async def test_preview_tools_reject_traversal_name(
    tmp_path: Path,
    tool_name: str,
) -> None:
    """A traversal name yields a path-safe ToolFailure from each tool."""
    from eventum.mcp.tools import preview

    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=True)
    tool = getattr(preview, tool_name)

    result = await tool(ctx, '../escape')

    assert isinstance(result, ToolFailure)
    failure_text = str(result.error) + str(result.details)
    assert str(tmp_path) not in failure_text
    assert result.details.get('name') == '../escape'


async def test_preview_timestamps_size_below_one_fails_in_band(
    ctx: FileAuthoringContext,
) -> None:
    """Size < 1 returns ToolFailure instead of raising ValueError."""
    from eventum.mcp.tools.preview import preview_timestamps

    result = await preview_timestamps(ctx, 'gen', 0, skip_past=False)

    assert isinstance(result, ToolFailure)
    assert '`size`' in result.error
    assert result.details == {'value': 0}


async def test_preview_events_count_below_one_fails_in_band(
    ctx: FileAuthoringContext,
) -> None:
    """Count < 1 returns ToolFailure instead of raising ValueError."""
    from eventum.mcp.tools.preview import preview_events

    result = await preview_events(ctx, 'gen', 0, skip_past=False)

    assert isinstance(result, ToolFailure)
    assert '`count`' in result.error
    assert result.details == {'value': 0}


async def test_validate_generator_redacts_secret_in_error(
    tmp_path: Path,
) -> None:
    """A resolved secret value never reaches the returned ToolFailure.

    The config references ``${secrets.DB_PASS}`` in an integer field as a
    quoted string, so the resolved value is substituted verbatim and then
    surfaces in the integer-parsing validation error. ``get_secret`` is
    patched at both lookup sites (``config_loader`` resolves the token,
    ``redaction`` collects the value for redaction) so no real keyring is
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
            'eventum.mcp.redaction.get_secret',
            return_value=plaintext,
        ),
    ):
        result = await validate_generator(ctx, 'sec')

        # Sanity: with redaction bypassed the secret WOULD leak. This
        # guards against the test passing because the value never
        # reached the error in the first place.
        with patch(
            'eventum.mcp.tools.preview.read_config_secret_values',
            return_value=[],
        ):
            leaked = await validate_generator(ctx, 'sec')

    assert isinstance(leaked, ToolFailure)
    assert plaintext in (str(leaked.error) + str(leaked.details))

    assert isinstance(result, ToolFailure)
    failure_text = str(result.error) + str(result.details)
    assert plaintext not in failure_text
