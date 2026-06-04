"""Tests for the live generator-management tools."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from eventum.app.manager import ManagingError
from eventum.app.startup import StartupError
from eventum.core.parameters import GenerationParameters
from eventum.mcp.context import ServerLiveContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.live import (
    get_generator_status,
    list_generators_live,
    register_generator,
    start_generator,
    stop_generator,
)


class _FakeGenerator:
    def __init__(self, generator_id: str) -> None:
        self.params = SimpleNamespace(id=generator_id)
        self.is_initializing = False
        self.is_running = True
        self.is_ended_up = False
        self.is_ended_up_successfully = False
        self.is_stopping = False
        self.start_time = None


class _FakeManager:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []
        self.added: list[Any] = []
        self.removed: list[str] = []
        self._generators = {'g1': _FakeGenerator('g1')}

    @property
    def generator_ids(self) -> list[str]:
        return list(self._generators)

    def get_generator(self, generator_id: str) -> _FakeGenerator:
        if generator_id not in self._generators:
            msg = 'Generator is not found'
            raise ManagingError(msg)
        return self._generators[generator_id]

    def start(self, generator_id: str) -> bool:
        self.started.append(generator_id)
        return True

    def stop(self, generator_id: str) -> None:
        self.stopped.append(generator_id)

    def add(self, params: Any) -> None:
        self.added.append(params)

    def remove(self, generator_id: str) -> None:
        self.removed.append(generator_id)


class _FakeStartup:
    def __init__(self, *, fail: bool = False) -> None:
        self.added: list[Any] = []
        self._fail = fail

    def add(self, params: Any) -> None:
        if self._fail:
            msg = 'cannot write startup file'
            raise StartupError(
                msg, context={'file_path': '/abs/secret/startup.yml'}
            )
        self.added.append(params)


def _ctx(
    tmp_path: Path,
    manager: _FakeManager,
    startup: _FakeStartup,
    *,
    read_only: bool = False,
) -> ServerLiveContext:
    return ServerLiveContext(
        generators_dir=tmp_path,
        read_only=read_only,
        manager=manager,  # type: ignore[arg-type]
        startup=startup,  # type: ignore[arg-type]
        generation=GenerationParameters(),
    )


async def test_list_generators_live(tmp_path: Path) -> None:
    """Listing returns one status dict per managed generator."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    statuses = await list_generators_live(ctx)
    assert [s['id'] for s in statuses] == ['g1']
    assert statuses[0]['is_running'] is True


async def test_get_generator_status_unknown_is_failure(
    tmp_path: Path,
) -> None:
    """An unknown id yields a ToolFailure, not an exception."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    result = await get_generator_status(ctx, 'nope')
    assert isinstance(result, ToolFailure)


async def test_start_and_stop_generator(tmp_path: Path) -> None:
    """Start and stop delegate to the manager."""
    manager = _FakeManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    started = await start_generator(ctx, 'g1')
    stopped = await stop_generator(ctx, 'g1')
    assert started == {'id': 'g1', 'started': True}
    assert stopped == {'id': 'g1', 'stopped': True}
    assert manager.started == ['g1']
    assert manager.stopped == ['g1']


async def test_write_tools_gate_on_read_only(tmp_path: Path) -> None:
    """Read-only mode refuses writes without touching the manager."""
    manager = _FakeManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup(), read_only=True)
    assert isinstance(await start_generator(ctx, 'g1'), ToolFailure)
    assert isinstance(await stop_generator(ctx, 'g1'), ToolFailure)
    assert isinstance(await register_generator(ctx, 'new'), ToolFailure)
    assert manager.started == []
    assert manager.stopped == []
    assert manager.added == []


async def test_register_generator_adds_and_persists(
    tmp_path: Path,
) -> None:
    """Register adds the generator live and persists it to startup."""
    manager = _FakeManager()
    startup = _FakeStartup()
    ctx = _ctx(tmp_path, manager, startup)
    result = await register_generator(ctx, 'newgen', {'x': 1})
    assert result == {'id': 'newgen', 'registered': True}
    assert len(manager.added) == 1
    assert len(startup.added) == 1
    added = manager.added[0]
    assert added.id == 'newgen'
    assert added.path == tmp_path / 'newgen' / 'generator.yml'
    assert added.params == {'x': 1}


async def test_register_rolls_back_on_startup_error(
    tmp_path: Path,
) -> None:
    """A startup failure rolls back the live add and scrubs the path."""
    manager = _FakeManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup(fail=True))
    result = await register_generator(ctx, 'newgen')
    assert isinstance(result, ToolFailure)
    assert manager.removed == ['newgen']
    assert '/abs/secret' not in result.error
    assert '/abs/secret' not in repr(result.details)


async def test_concurrent_start_is_safe(tmp_path: Path) -> None:
    """Two concurrent start calls both complete without error.

    Double-spawn prevention itself lives in GeneratorManager (RLock),
    covered by app/tests/test_manager.py; this asserts the tool layer
    dispatches each call independently via asyncio.to_thread.
    """
    manager = _FakeManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    results = await asyncio.gather(
        start_generator(ctx, 'g1'), start_generator(ctx, 'g1')
    )
    assert all(r == {'id': 'g1', 'started': True} for r in results)
    assert manager.started == ['g1', 'g1']
