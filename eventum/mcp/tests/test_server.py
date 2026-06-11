"""Tests for the FastMCP server factory."""

from pathlib import Path
from unittest.mock import MagicMock

import anyio
import pytest

from eventum import __version__ as _eventum_version
from eventum.mcp.context import FileAuthoringContext, ServerLiveContext
from eventum.mcp.server import build_server

_EXPECTED_TOOLS = {
    'list_plugins',
    'get_plugin_schema',
    'list_formatters',
    'get_formatter_schema',
    'describe_sample',
    'list_secret_names',
    'list_generators',
    'list_generator_files',
    'read_generator_file',
    'write_generator_file',
    'delete_generator_file',
    'delete_generator',
    'validate_generator',
    'preview_timestamps',
    'preview_events',
    'run_generator',
}

_EXPECTED_PROMPTS = {
    'create_generator',
}

_EXPECTED_RESOURCES = {
    'eventum://templating/reference',
    'eventum://schema/generator',
    'eventum://examples/generators',
    'eventum://workspace/configs',
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


def test_build_server_registers_prompts(
    ctx: FileAuthoringContext,
) -> None:
    """build_server registers the authoring prompts."""
    server = build_server(ctx, transport='stdio')
    prompts = anyio.run(server.list_prompts)
    names = {p.name for p in prompts}
    assert names >= _EXPECTED_PROMPTS


def test_build_server_registers_resources(
    ctx: FileAuthoringContext,
) -> None:
    """build_server registers the grounding resources."""
    server = build_server(ctx, transport='stdio')
    resources = anyio.run(server.list_resources)
    uris = {str(r.uri) for r in resources}
    assert uris >= _EXPECTED_RESOURCES


_EXPECTED_LIVE_TOOLS = {
    'list_generators_live',
    'get_generator_status',
    'get_generator_stats',
    'start_generator',
    'stop_generator',
    'register_generator',
    'unregister_generator',
    'get_generator_logs',
    'list_startup_generators',
}


@pytest.fixture
def live_ctx(tmp_path: Path) -> ServerLiveContext:
    """Return a ServerLiveContext with mock manager/startup."""
    return ServerLiveContext(
        generators_dir=tmp_path,
        read_only=True,
        manager=MagicMock(),
        startup=MagicMock(),
        generation=MagicMock(),
        logs_dir=tmp_path,
        log_format='plain',
    )


def test_stdio_has_no_live_tools(ctx: FileAuthoringContext) -> None:
    """The stdio authoring server registers no live tools."""
    server = build_server(ctx, transport='stdio')
    names = {t.name for t in anyio.run(server.list_tools)}
    assert names == _EXPECTED_TOOLS
    assert names.isdisjoint(_EXPECTED_LIVE_TOOLS)


def test_live_server_registers_live_tools(
    live_ctx: ServerLiveContext,
) -> None:
    """The HTTP live server registers the live-management tools."""
    server = build_server(live_ctx, transport='http', live=True)
    names = {t.name for t in anyio.run(server.list_tools)}
    assert names >= _EXPECTED_LIVE_TOOLS
    assert names >= _EXPECTED_TOOLS


def test_live_requires_live_context(ctx: FileAuthoringContext) -> None:
    """Requesting live tools with a non-live context raises."""
    with pytest.raises(TypeError):
        build_server(ctx, transport='http', live=True)


def test_live_server_registers_live_ops_prompt(
    live_ctx: ServerLiveContext,
) -> None:
    """The HTTP live server adds the live-operations prompt."""
    server = build_server(live_ctx, transport='http', live=True)
    names = {p.name for p in anyio.run(server.list_prompts)}
    assert 'live_ops' in names


def test_stdio_has_no_live_ops_prompt(ctx: FileAuthoringContext) -> None:
    """The stdio server does not expose the live-operations prompt."""
    server = build_server(ctx, transport='stdio')
    names = {p.name for p in anyio.run(server.list_prompts)}
    assert 'live_ops' not in names
