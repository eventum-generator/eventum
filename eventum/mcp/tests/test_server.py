"""Tests for the FastMCP server factory."""

from pathlib import Path

import anyio
import pytest

from eventum import __version__ as _eventum_version
from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.server import build_server

_EXPECTED_TOOLS = {
    'list_plugins',
    'get_plugin_schema',
    'list_formatters',
    'get_formatter_schema',
    'describe_sample',
    'list_generators',
    'list_generator_files',
    'read_generator_file',
    'write_generator_file',
    'validate_generator',
    'preview_timestamps',
    'preview_events',
}


@pytest.fixture
def ctx(tmp_path: Path) -> FileAuthoringContext:
    """Return a read-only FileAuthoringContext rooted at tmp_path."""
    return FileAuthoringContext(generators_dir=tmp_path, read_only=True)


def test_build_server_registers_tools(
    ctx: FileAuthoringContext,
) -> None:
    """build_server registers exactly the expected tool set."""
    server = build_server(ctx, transport='stdio')
    tools = anyio.run(server.list_tools)
    names = {t.name for t in tools}
    assert names == _EXPECTED_TOOLS


def test_build_server_version(
    ctx: FileAuthoringContext,
) -> None:
    """build_server sets the advertised version to the package version."""
    server = build_server(ctx, transport='stdio')
    assert server._mcp_server.version == _eventum_version  # noqa: SLF001


def test_get_plugin_schema_input_schema_has_kind_and_name(
    ctx: FileAuthoringContext,
) -> None:
    """get_plugin_schema exposes kind and name but not context."""
    server = build_server(ctx, transport='stdio')
    tools = anyio.run(server.list_tools)
    tool = next(t for t in tools if t.name == 'get_plugin_schema')
    props = tool.inputSchema.get('properties', {})
    assert 'kind' in props
    assert 'name' in props
    assert 'context' not in props


def test_list_plugins_input_schema_has_kind_not_context(
    ctx: FileAuthoringContext,
) -> None:
    """list_plugins exposes kind but hides the injected context."""
    server = build_server(ctx, transport='stdio')
    tools = anyio.run(server.list_tools)
    tool = next(t for t in tools if t.name == 'list_plugins')
    props = tool.inputSchema.get('properties', {})
    assert 'kind' in props
    assert 'context' not in props
