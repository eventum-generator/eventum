"""Tests for the live generator-management tools."""

import asyncio
import threading
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from eventum.app.manager import ManagingError
from eventum.app.startup import StartupError, StartupNotFoundError
from eventum.app.startup.models import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
from eventum.core.parameters import GenerationParameters
from eventum.mcp.context import ServerLiveContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.live import (
    get_generator_logs,
    get_generator_stats,
    get_generator_status,
    list_generators_live,
    list_startup_generators,
    register_generator,
    start_generator,
    stop_generator,
    unregister_generator,
)


class _FakeGenerator:
    def __init__(
        self,
        generator_id: str,
        *,
        start_time: datetime | None = None,
        plugins: Any = None,
    ) -> None:
        self.params = SimpleNamespace(
            id=generator_id, path=Path('nonexistent.yml')
        )
        self.is_initializing = False
        self.is_running = True
        self.is_ended_up = False
        self.is_ended_up_successfully = False
        self.is_stopping = False
        self.start_time = start_time
        self._plugins = plugins

    def get_plugins_info(self) -> Any:
        if isinstance(self._plugins, Exception):
            raise self._plugins
        return self._plugins


class _FakeManager:
    def __init__(
        self,
        generators: dict[str, _FakeGenerator] | None = None,
    ) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []
        self.added: list[Any] = []
        self.removed: list[str] = []
        self._generators = (
            {'g1': _FakeGenerator('g1')} if generators is None else generators
        )

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
        self._generators[params.id] = _FakeGenerator(params.id)

    def remove(self, generator_id: str) -> None:
        if generator_id not in self._generators:
            msg = 'Generator is not found'
            raise ManagingError(msg)
        del self._generators[generator_id]
        self.removed.append(generator_id)


class _FakeStartup:
    def __init__(
        self,
        *,
        fail: bool = False,
        present: set[str] | None = None,
        entries: Any = None,
    ) -> None:
        self.added: list[Any] = []
        self.deleted: list[str] = []
        self._fail = fail
        self._present = set() if present is None else set(present)
        self._entries = entries

    def add(self, params: Any) -> None:
        if self._fail:
            msg = 'cannot write startup file'
            raise StartupError(
                msg, context={'file_path': '/abs/secret/startup.yml'}
            )
        self.added.append(params)

    def delete(self, name: str) -> None:
        if self._fail:
            msg = 'cannot write startup file'
            raise StartupError(
                msg, context={'file_path': '/abs/secret/startup.yml'}
            )
        if name not in self._present:
            msg = 'entry not found'
            raise StartupNotFoundError(msg, context={'id': name})
        self._present.discard(name)
        self.deleted.append(name)

    def get_all(self) -> Any:
        if self._entries is None:
            return StartupGeneratorParametersList(root=())
        return self._entries


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
        logs_dir=tmp_path,
        log_format='plain',
    )


async def test_list_generators_live(tmp_path: Path) -> None:
    """Listing returns one status dict per managed generator."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    statuses = await list_generators_live(ctx)
    assert [s['id'] for s in statuses] == ['g1']
    assert statuses[0]['is_running'] is True


async def test_list_generators_live_skips_vanished_id(
    tmp_path: Path,
) -> None:
    """An id that vanishes between listing and lookup is skipped."""

    class _VanishingManager(_FakeManager):
        @property
        def generator_ids(self) -> list[str]:
            return [*self._generators, 'vanished']

    ctx = _ctx(tmp_path, _VanishingManager(), _FakeStartup())
    statuses = await list_generators_live(ctx)
    assert [s['id'] for s in statuses] == ['g1']


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
    (tmp_path / 'newgen').mkdir()
    (tmp_path / 'newgen' / 'generator.yml').write_text(
        'input: []\n', encoding='utf-8'
    )
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
    (tmp_path / 'newgen').mkdir()
    (tmp_path / 'newgen' / 'generator.yml').write_text(
        'input: []\n', encoding='utf-8'
    )
    result = await register_generator(ctx, 'newgen')
    assert isinstance(result, ToolFailure)
    assert manager.removed == ['newgen']
    assert '/abs/secret' not in result.error
    assert '/abs/secret' not in repr(result.details)


async def test_register_generator_missing_config(tmp_path: Path) -> None:
    """Registering a generator with no config file fails cleanly.

    The failure keys the identifier as 'id', like every other
    register_generator response, not as the workspace-level 'name'.
    """
    manager = _FakeManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    result = await register_generator(ctx, 'ghost')
    assert isinstance(result, ToolFailure)
    assert result.details == {'id': 'ghost'}
    assert manager.added == []


class _BlockingManager(_FakeManager):
    def __init__(self) -> None:
        super().__init__()
        self._barrier = threading.Barrier(2, timeout=5)

    def start(self, generator_id: str) -> bool:
        # Both calls must be in-flight on worker threads at once;
        # this only releases if start_generator offloaded each via
        # asyncio.to_thread rather than running on the event loop.
        self._barrier.wait()
        return super().start(generator_id)


async def test_concurrent_start_dispatches_off_loop(
    tmp_path: Path,
) -> None:
    """Concurrent start calls run on worker threads, not the loop.

    Double-spawn prevention lives in GeneratorManager (RLock), covered
    by app/tests/test_manager.py. Here the manager blocks on a 2-party
    barrier, so the pair only completes if the tool layer dispatched
    each call via asyncio.to_thread; a synchronous on-loop call would
    deadlock and time out.
    """
    manager = _BlockingManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    results = await asyncio.gather(
        start_generator(ctx, 'g1'), start_generator(ctx, 'g1')
    )
    assert all(r == {'id': 'g1', 'started': True} for r in results)
    assert manager.started == ['g1', 'g1']


async def test_unregister_removes_from_both(tmp_path: Path) -> None:
    """Unregister drops the generator from runtime and startup."""
    manager = _FakeManager()
    startup = _FakeStartup(present={'g1'})
    ctx = _ctx(tmp_path, manager, startup)
    result = await unregister_generator(ctx, 'g1')
    assert result == {'id': 'g1', 'unregistered': True}
    assert manager.removed == ['g1']
    assert startup.deleted == ['g1']


async def test_unregister_gates_on_read_only(tmp_path: Path) -> None:
    """Read-only mode refuses unregister without touching state."""
    manager = _FakeManager()
    startup = _FakeStartup(present={'g1'})
    ctx = _ctx(tmp_path, manager, startup, read_only=True)
    result = await unregister_generator(ctx, 'g1')
    assert isinstance(result, ToolFailure)
    assert manager.removed == []
    assert startup.deleted == []


async def test_unregister_missing_everywhere_fails(tmp_path: Path) -> None:
    """A generator absent from runtime and startup yields a failure."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    result = await unregister_generator(ctx, 'ghost')
    assert isinstance(result, ToolFailure)


async def test_unregister_startup_write_error(tmp_path: Path) -> None:
    """A startup write failure after runtime removal returns a failure.

    The runtime removal stands; the path in the error is scrubbed.
    """
    manager = _FakeManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup(fail=True))
    result = await unregister_generator(ctx, 'g1')
    assert isinstance(result, ToolFailure)
    assert manager.removed == ['g1']
    assert '/abs/secret' not in result.error
    assert '/abs/secret' not in repr(result.details)


async def test_unregister_startup_only(tmp_path: Path) -> None:
    """A persisted-but-not-running generator is still unregistered."""
    manager = _FakeManager()
    startup = _FakeStartup(present={'persisted'})
    ctx = _ctx(tmp_path, manager, startup)
    result = await unregister_generator(ctx, 'persisted')
    assert result == {'id': 'persisted', 'unregistered': True}
    assert manager.removed == []
    assert startup.deleted == ['persisted']


async def test_get_generator_logs_returns_tail(tmp_path: Path) -> None:
    """The tail of a managed generator's log is returned."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    (tmp_path / 'generator_g1.log').write_text('line one\nline two\n')
    result = await get_generator_logs(ctx, 'g1')
    assert result == {'id': 'g1', 'lines': ['line one', 'line two']}


async def test_get_generator_logs_unknown_is_failure(tmp_path: Path) -> None:
    """Logs for an unmanaged id yield a ToolFailure, not a file read."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    result = await get_generator_logs(ctx, 'ghost')
    assert isinstance(result, ToolFailure)


async def test_get_generator_logs_missing_file_is_empty(
    tmp_path: Path,
) -> None:
    """A managed generator with no log file yet returns no lines."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    result = await get_generator_logs(ctx, 'g1')
    assert result == {'id': 'g1', 'lines': []}


async def test_get_generator_logs_scrubs_paths(tmp_path: Path) -> None:
    """Absolute paths under the generators dir are relativized."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    leaked = tmp_path / 'g1' / 'templates' / 'evt.jinja'
    (tmp_path / 'generator_g1.log').write_text(f'error rendering {leaked}\n')
    result = await get_generator_logs(ctx, 'g1')
    assert not isinstance(result, ToolFailure)
    joined = '\n'.join(result['lines'])
    assert str(tmp_path) not in joined
    assert 'g1/templates/evt.jinja' in joined


async def test_get_generator_logs_redacts_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured secret values are redacted from log lines."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    monkeypatch.setattr(
        'eventum.mcp.tools.live.read_config_secret_values',
        lambda _path: ['s3cr3t-token'],
    )
    (tmp_path / 'generator_g1.log').write_text(
        'connecting with token s3cr3t-token failed\n'
    )
    result = await get_generator_logs(ctx, 'g1')
    assert not isinstance(result, ToolFailure)
    joined = '\n'.join(result['lines'])
    assert 's3cr3t-token' not in joined
    assert '[redacted]' in joined


async def test_get_generator_logs_caps_lines(tmp_path: Path) -> None:
    """The lines parameter caps how many trailing lines come back."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    body = ''.join(f'line {i}\n' for i in range(50))
    (tmp_path / 'generator_g1.log').write_text(body)
    result = await get_generator_logs(ctx, 'g1', lines=5)
    assert not isinstance(result, ToolFailure)
    assert result['lines'] == [f'line {i}' for i in range(45, 50)]


_MAX_LOG_LINES = 1000


async def test_get_generator_logs_clamps_lines_floor(
    tmp_path: Path,
) -> None:
    """A non-positive lines value is clamped to one trailing line."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    (tmp_path / 'generator_g1.log').write_text('first\nlast\n')
    result = await get_generator_logs(ctx, 'g1', lines=0)
    assert not isinstance(result, ToolFailure)
    assert result['lines'] == ['last']


async def test_get_generator_logs_clamps_lines_ceiling(
    tmp_path: Path,
) -> None:
    """A lines value above the maximum returns at most 1000 lines."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    total = _MAX_LOG_LINES + 100
    body = ''.join(f'line {i}\n' for i in range(total))
    (tmp_path / 'generator_g1.log').write_text(body)
    result = await get_generator_logs(ctx, 'g1', lines=5 * _MAX_LOG_LINES)
    assert not isinstance(result, ToolFailure)
    assert len(result['lines']) == _MAX_LOG_LINES
    assert result['lines'][0] == f'line {total - _MAX_LOG_LINES}'
    assert result['lines'][-1] == f'line {total - 1}'


async def test_get_generator_logs_rejects_escaping_id(tmp_path: Path) -> None:
    """A managed id whose log path escapes the logs dir is rejected."""
    evil = '../../../../etc/passwd'
    manager = _FakeManager(generators={evil: _FakeGenerator(evil)})
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    result = await get_generator_logs(ctx, evil)
    assert isinstance(result, ToolFailure)


async def test_get_generator_logs_scrubs_foreign_abs_paths(
    tmp_path: Path,
) -> None:
    """Absolute paths outside the workspace are reduced to basenames."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    (tmp_path / 'generator_g1.log').write_text(
        'Traceback File "/home/u/.venv/site-packages/kafka/client.py"\n'
    )
    result = await get_generator_logs(ctx, 'g1')
    assert not isinstance(result, ToolFailure)
    joined = '\n'.join(result['lines'])
    assert '/home/u/.venv' not in joined
    assert 'client.py' in joined


async def test_get_generator_logs_does_not_raise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An OS error while reading the log becomes a ToolFailure."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    (tmp_path / 'generator_g1.log').write_text('x\n')

    def _boom(*_args: object, **_kwargs: object) -> list[str]:
        msg = 'disk gone'
        raise OSError(msg)

    monkeypatch.setattr('eventum.mcp.tools.live._tail_lines', _boom)
    result = await get_generator_logs(ctx, 'g1')
    assert isinstance(result, ToolFailure)
    assert result.error == 'Failed to read logs'


async def test_get_generator_logs_tail_drops_partial_first_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A truncated tail drops the partial leading line."""
    monkeypatch.setattr('eventum.mcp.tools.live._TAIL_MAX_BYTES', 12)
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    (tmp_path / 'generator_g1.log').write_text('AAAAAAAA\nBBBB\nCCCC\n')
    result = await get_generator_logs(ctx, 'g1')
    assert not isinstance(result, ToolFailure)
    assert result['lines'] == ['BBBB', 'CCCC']


async def test_get_generator_logs_keeps_single_oversized_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single line larger than the tail window is still returned."""
    monkeypatch.setattr('eventum.mcp.tools.live._TAIL_MAX_BYTES', 8)
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    (tmp_path / 'generator_g1.log').write_text('X' * 40)
    result = await get_generator_logs(ctx, 'g1')
    assert not isinstance(result, ToolFailure)
    assert result['lines'] == ['X' * 8]


async def test_unregister_runtime_only(tmp_path: Path) -> None:
    """A running-but-not-persisted generator is still unregistered."""
    manager = _FakeManager()
    startup = _FakeStartup()
    ctx = _ctx(tmp_path, manager, startup)
    result = await unregister_generator(ctx, 'g1')
    assert result == {'id': 'g1', 'unregistered': True}
    assert manager.removed == ['g1']
    assert startup.deleted == []


async def test_get_generator_logs_json_format(tmp_path: Path) -> None:
    """The json log format reads the .json log file."""
    ctx = ServerLiveContext(
        generators_dir=tmp_path,
        read_only=False,
        manager=_FakeManager(),  # type: ignore[arg-type]
        startup=_FakeStartup(),  # type: ignore[arg-type]
        generation=GenerationParameters(),
        logs_dir=tmp_path,
        log_format='json',
    )
    (tmp_path / 'generator_g1.json').write_text('{"e":"hi"}\n')
    result = await get_generator_logs(ctx, 'g1')
    assert result == {'id': 'g1', 'lines': ['{"e":"hi"}']}


_GENERATED = 100
_PRODUCED = 100
_WRITTEN = 99


def _fake_plugins() -> SimpleNamespace:
    """Return a plugins-info stand-in with non-zero counters."""
    return SimpleNamespace(
        input=[SimpleNamespace(name='cron', id=0, generated=_GENERATED)],
        event=SimpleNamespace(
            name='template',
            id=0,
            produced=_PRODUCED,
            produce_failed=1,
            dropped=0,
        ),
        output=[
            SimpleNamespace(
                name='stdout',
                id=0,
                written=_WRITTEN,
                write_failed=0,
                format_failed=0,
            )
        ],
    )


async def test_get_generator_stats_running(tmp_path: Path) -> None:
    """Stats for a running generator include totals and throughput."""
    gen = _FakeGenerator(
        'g1',
        start_time=datetime(2020, 1, 1, tzinfo=ZoneInfo('UTC')),
        plugins=_fake_plugins(),
    )
    manager = _FakeManager(generators={'g1': gen})
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    result = await get_generator_stats(ctx, 'g1')
    assert not isinstance(result, ToolFailure)
    assert result['id'] == 'g1'
    assert result['total_generated'] == _GENERATED
    assert result['total_written'] == _WRITTEN
    assert result['event']['produced'] == _PRODUCED
    assert result['input_eps'] >= 0


async def test_get_generator_stats_not_running(tmp_path: Path) -> None:
    """Stats for a generator with no start time fail cleanly."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    result = await get_generator_stats(ctx, 'g1')
    assert isinstance(result, ToolFailure)
    assert result.error == 'Generator is not running'


async def test_get_generator_stats_unknown(tmp_path: Path) -> None:
    """Stats for an unknown id yield a ToolFailure."""
    ctx = _ctx(tmp_path, _FakeManager(), _FakeStartup())
    result = await get_generator_stats(ctx, 'ghost')
    assert isinstance(result, ToolFailure)


async def test_list_startup_generators_relativizes_path(
    tmp_path: Path,
) -> None:
    """Startup entries return with paths relative to the dir."""
    entry = StartupGeneratorParameters(
        id='g1',
        path=tmp_path / 'g1' / 'generator.yml',
        live_mode=False,
    )
    startup = _FakeStartup(
        entries=StartupGeneratorParametersList(root=(entry,))
    )
    ctx = _ctx(tmp_path, _FakeManager(), startup)
    result = await list_startup_generators(ctx)
    assert not isinstance(result, ToolFailure)
    assert result[0]['id'] == 'g1'
    assert result[0]['path'] == 'g1/generator.yml'
    assert result[0]['live_mode'] is False
    assert str(tmp_path) not in repr(result)


async def test_register_generator_with_execution_params(
    tmp_path: Path,
) -> None:
    """Per-generator execution overrides reach the persisted entry."""
    manager = _FakeManager()
    startup = _FakeStartup()
    ctx = _ctx(tmp_path, manager, startup)
    (tmp_path / 'newgen').mkdir()
    (tmp_path / 'newgen' / 'generator.yml').write_text(
        'input: []\n', encoding='utf-8'
    )
    result = await register_generator(
        ctx,
        'newgen',
        execution={'live_mode': False, 'skip_past': False},
        autostart=False,
    )
    assert result == {'id': 'newgen', 'registered': True}
    persisted = startup.added[0]
    assert persisted.live_mode is False
    assert persisted.skip_past is False
    assert persisted.autostart is False


async def test_register_generator_invalid_execution(tmp_path: Path) -> None:
    """An invalid execution override is rejected as a clean failure."""
    manager = _FakeManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    (tmp_path / 'newgen').mkdir()
    (tmp_path / 'newgen' / 'generator.yml').write_text(
        'input: []\n', encoding='utf-8'
    )
    result = await register_generator(
        ctx, 'newgen', execution={'timezone': 'Not/AZone'}
    )
    assert isinstance(result, ToolFailure)
    assert result.error == 'Invalid execution parameters'
    assert manager.added == []


async def test_register_generator_rejects_reserved_override(
    tmp_path: Path,
) -> None:
    """A reserved key in execution is rejected, not silently applied."""
    manager = _FakeManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    (tmp_path / 'newgen').mkdir()
    (tmp_path / 'newgen' / 'generator.yml').write_text(
        'input: []\n', encoding='utf-8'
    )
    result = await register_generator(ctx, 'newgen', execution={'id': 'evil'})
    assert isinstance(result, ToolFailure)
    assert manager.added == []


async def test_get_generator_stats_release_race(tmp_path: Path) -> None:
    """Return a failure when get_plugins_info raises after release."""
    gen = _FakeGenerator(
        'g1',
        start_time=datetime(2020, 1, 1, tzinfo=ZoneInfo('UTC')),
        plugins=RuntimeError('plugins released'),
    )
    manager = _FakeManager(generators={'g1': gen})
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    result = await get_generator_stats(ctx, 'g1')
    assert isinstance(result, ToolFailure)
    assert result.error == 'Generator is not running'


async def test_register_generator_rejects_traversal(tmp_path: Path) -> None:
    """Reject a name that escapes the generators directory."""
    manager = _FakeManager()
    ctx = _ctx(tmp_path, manager, _FakeStartup())
    result = await register_generator(ctx, '../escape')
    assert isinstance(result, ToolFailure)
    assert result.details == {'id': '../escape'}
    assert manager.added == []
