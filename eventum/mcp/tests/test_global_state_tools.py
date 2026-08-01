"""Tests for the MCP global-state tools."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from eventum.core.parameters import GenerationParameters
from eventum.mcp.context import ServerLiveContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.global_state import (
    clear_global_state,
    delete_global_state_key,
    get_global_state,
    get_global_state_key,
    set_global_state,
)
from eventum.plugins.event.plugins.template.plugin import TemplateEventPlugin


@pytest.fixture(autouse=True)
def _clean_state() -> Iterator[None]:
    """Isolate each test from the process-wide global state."""
    TemplateEventPlugin.GLOBAL_STATE.clear()
    yield
    TemplateEventPlugin.GLOBAL_STATE.clear()


def _ctx(tmp_path: Path, *, read_only: bool = False) -> ServerLiveContext:
    return ServerLiveContext(
        generators_dir=tmp_path,
        read_only=read_only,
        manager=MagicMock(),
        startup=MagicMock(),
        generation=GenerationParameters(),
        logs_dir=tmp_path,
        log_format='plain',
        settings=MagicMock(),
        hooks=MagicMock(),
    )


async def test_get_global_state_empty() -> None:
    """An untouched global state is an empty dict."""
    assert await get_global_state() == {}


async def test_set_then_get_global_state(tmp_path: Path) -> None:
    """Values set through the tool are read back."""
    ctx = _ctx(tmp_path)

    await set_global_state(ctx, {'a': 1, 'b': 'x'})

    assert await get_global_state() == {'a': 1, 'b': 'x'}


async def test_set_global_state_returns_updated_keys(tmp_path: Path) -> None:
    """Setting reports the affected keys, sorted."""
    ctx = _ctx(tmp_path)

    result = await set_global_state(ctx, {'b': 2, 'a': 1})

    assert result == {'updated': ['a', 'b']}


async def test_set_global_state_read_only_blocked(tmp_path: Path) -> None:
    """A read-only server refuses to set global state."""
    ctx = _ctx(tmp_path, read_only=True)

    result = await set_global_state(ctx, {'a': 1})

    assert isinstance(result, ToolFailure)
    assert await get_global_state() == {}


async def test_get_global_state_key(tmp_path: Path) -> None:
    """A present key is returned by value."""
    ctx = _ctx(tmp_path)
    await set_global_state(ctx, {'a': 1})

    assert await get_global_state_key('a') == 1


async def test_get_global_state_key_missing_is_failure() -> None:
    """An absent key returns a structured failure."""
    result = await get_global_state_key('missing')

    assert isinstance(result, ToolFailure)
    assert result.details == {'key': 'missing'}


async def test_delete_global_state_key(tmp_path: Path) -> None:
    """Deleting a key removes only that key."""
    ctx = _ctx(tmp_path)
    await set_global_state(ctx, {'a': 1, 'b': 2})

    result = await delete_global_state_key(ctx, 'a')

    assert result == {'deleted': 'a'}
    assert await get_global_state() == {'b': 2}


async def test_delete_global_state_key_read_only_blocked(
    tmp_path: Path,
) -> None:
    """A read-only server refuses to delete a key."""
    ctx = _ctx(tmp_path, read_only=True)
    TemplateEventPlugin.GLOBAL_STATE.update({'a': 1})

    result = await delete_global_state_key(ctx, 'a')

    assert isinstance(result, ToolFailure)
    assert await get_global_state() == {'a': 1}


async def test_clear_global_state(tmp_path: Path) -> None:
    """Clearing empties the global state."""
    ctx = _ctx(tmp_path)
    await set_global_state(ctx, {'a': 1})

    result = await clear_global_state(ctx)

    assert result == {'cleared': True}
    assert await get_global_state() == {}


async def test_clear_global_state_read_only_blocked(tmp_path: Path) -> None:
    """A read-only server refuses to clear global state."""
    ctx = _ctx(tmp_path, read_only=True)
    TemplateEventPlugin.GLOBAL_STATE.update({'a': 1})

    result = await clear_global_state(ctx)

    assert isinstance(result, ToolFailure)
    assert await get_global_state() == {'a': 1}
