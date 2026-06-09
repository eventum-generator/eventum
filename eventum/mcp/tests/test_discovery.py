"""Tests for plugin discovery tools."""

from pathlib import Path

import pytest

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools import discovery
from eventum.mcp.tools.discovery import get_plugin_schema, list_plugins
from eventum.plugins.exceptions import PluginLoadError


@pytest.fixture
def ctx(tmp_path: Path) -> FileAuthoringContext:
    """Return a read-only FileAuthoringContext rooted at tmp_path."""
    return FileAuthoringContext(generators_dir=tmp_path, read_only=True)


def test_list_plugins_groups_by_kind(ctx: FileAuthoringContext) -> None:
    """list_plugins returns all three kinds when no filter is given."""
    result = list_plugins(ctx)
    assert set(result) == {'input', 'event', 'output'}
    assert 'template' in result['event']
    assert 'stdout' in result['output']


def test_list_plugins_filter_kind(ctx: FileAuthoringContext) -> None:
    """list_plugins returns only the requested kind when one is given."""
    result = list_plugins(ctx, kind='input')
    assert set(result) == {'input'}


def test_get_plugin_schema_returns_json_schema(
    ctx: FileAuthoringContext,
) -> None:
    """get_plugin_schema returns a valid JSON Schema object dict."""
    schema = get_plugin_schema(ctx, kind='output', name='stdout')
    assert not isinstance(schema, ToolFailure)
    assert schema['type'] == 'object'
    assert 'properties' in schema


def test_get_plugin_schema_unknown_name_fails(
    ctx: FileAuthoringContext,
) -> None:
    """get_plugin_schema returns ToolFailure for an unknown plugin name."""
    result = get_plugin_schema(ctx, kind='output', name='does-not-exist')
    assert isinstance(result, ToolFailure)
    assert {'kind', 'name', 'reason'} <= result.details.keys()
    assert result.details['name'] == 'does-not-exist'


def test_get_plugin_schema_scrubs_path_in_reason(
    ctx: FileAuthoringContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A path in a plugin-load error reason is scrubbed, not leaked."""

    def _boom(_name: str) -> None:
        msg = "import failed at '/abs/secret/plugin.py'"
        raise PluginLoadError(msg, context={})

    monkeypatch.setitem(discovery._LOADERS, 'output', _boom)  # noqa: SLF001
    result = get_plugin_schema(ctx, kind='output', name='kafka')
    assert isinstance(result, ToolFailure)
    assert '/abs/secret' not in result.details['reason']
    assert 'plugin.py' in result.details['reason']
