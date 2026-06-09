"""Tests for the one-shot run tool."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.run import run_generator

_CAP = 5


class _FakeGen:
    """Controllable Generator stand-in with no real threads."""

    def __init__(
        self,
        *,
        start_ok: bool = True,
        finishes: bool = True,
        success: bool = True,
        written: int = 0,
    ) -> None:
        self._start_ok = start_ok
        self._finishes = finishes
        self._success = success
        self._written = written
        self._running = False
        self.stopped = False

    def start(self) -> bool:
        # A finite generator finishes during start: not running after.
        self._running = self._start_ok and not self._finishes
        return self._start_ok

    @property
    def is_initializing(self) -> bool:
        return False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_ended_up_successfully(self) -> bool:
        return self._success and not self._running

    def get_plugins_info(self) -> Any:
        return SimpleNamespace(
            output=[
                SimpleNamespace(
                    written=self._written, write_failed=0, format_failed=0
                )
            ]
        )

    def stop(self) -> None:
        self._running = False
        self.stopped = True

    def join(self) -> None:
        self._running = False


class _LiveManagedCtx:
    """Authoring context that reports the generator as live-managed."""

    def __init__(self, generators_dir: Path) -> None:
        self.generators_dir = generators_dir
        self.read_only = False

    def is_live_managed(self, generator_id: str) -> bool:  # noqa: ARG002
        return True


def _ctx(tmp_path: Path, *, read_only: bool = False) -> FileAuthoringContext:
    return FileAuthoringContext(generators_dir=tmp_path, read_only=read_only)


def _make_gen(tmp_path: Path, name: str) -> None:
    (tmp_path / name).mkdir()
    (tmp_path / name / 'generator.yml').write_text(
        'input: []\n', encoding='utf-8'
    )


async def test_run_gated_on_read_only(tmp_path: Path) -> None:
    """Read-only mode refuses to run a generator."""
    result = await run_generator(_ctx(tmp_path, read_only=True), 'g')
    assert isinstance(result, ToolFailure)


async def test_run_missing_generator(tmp_path: Path) -> None:
    """An unknown generator name yields a ToolFailure."""
    result = await run_generator(_ctx(tmp_path), 'ghost')
    assert isinstance(result, ToolFailure)


async def test_run_completes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A finite generator finishes naturally."""
    _make_gen(tmp_path, 'g')
    monkeypatch.setattr(
        'eventum.mcp.tools.run.Generator',
        lambda _p: _FakeGen(finishes=True, success=True),
    )
    result = await run_generator(_ctx(tmp_path), 'g')
    assert result == {
        'id': 'g',
        'reason': 'completed',
        'events_written': 0,
        'events_failed': 0,
    }


async def test_run_reports_event_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed run reports how many events were written."""
    _make_gen(tmp_path, 'g')
    monkeypatch.setattr(
        'eventum.mcp.tools.run.Generator',
        lambda _p: _FakeGen(finishes=True, success=True, written=42),
    )
    result = await run_generator(_ctx(tmp_path), 'g')
    assert result == {
        'id': 'g',
        'reason': 'completed',
        'events_written': 42,
        'events_failed': 0,
    }


async def test_run_times_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An open-ended generator is stopped at the timeout."""
    _make_gen(tmp_path, 'g')
    gen = _FakeGen(finishes=False)
    monkeypatch.setattr('eventum.mcp.tools.run.Generator', lambda _p: gen)
    result = await run_generator(_ctx(tmp_path), 'g', timeout_seconds=0.2)
    assert result == {
        'id': 'g',
        'reason': 'timeout',
        'events_written': 0,
        'events_failed': 0,
    }
    assert gen.stopped is True


async def test_run_caps_on_max_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The run stops once max_events is reached."""
    _make_gen(tmp_path, 'g')
    gen = _FakeGen(finishes=False, written=_CAP)
    monkeypatch.setattr('eventum.mcp.tools.run.Generator', lambda _p: gen)
    result = await run_generator(
        _ctx(tmp_path), 'g', timeout_seconds=5.0, max_events=_CAP
    )
    assert result == {
        'id': 'g',
        'reason': 'max_events',
        'events_written': _CAP,
        'events_failed': 0,
    }
    assert gen.stopped is True


async def test_run_start_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A start failure (initialization error) yields a ToolFailure."""
    _make_gen(tmp_path, 'g')
    monkeypatch.setattr(
        'eventum.mcp.tools.run.Generator',
        lambda _p: _FakeGen(start_ok=False),
    )
    result = await run_generator(_ctx(tmp_path), 'g')
    assert isinstance(result, ToolFailure)


async def test_run_ignores_nonpositive_max_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Treat max_events below 1 as no cap, not an instant stop."""
    _make_gen(tmp_path, 'g')
    gen = _FakeGen(finishes=False)
    monkeypatch.setattr('eventum.mcp.tools.run.Generator', lambda _p: gen)
    result = await run_generator(
        _ctx(tmp_path), 'g', timeout_seconds=0.2, max_events=0
    )
    assert result == {
        'id': 'g',
        'reason': 'timeout',
        'events_written': 0,
        'events_failed': 0,
    }


async def test_run_rejects_live_managed_generator(tmp_path: Path) -> None:
    """A generator already managed live is not run standalone."""
    _make_gen(tmp_path, 'g')
    result = await run_generator(_LiveManagedCtx(tmp_path), 'g')
    assert isinstance(result, ToolFailure)


async def test_run_passes_skip_past(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The skip_past flag reaches the generator parameters."""
    _make_gen(tmp_path, 'g')
    captured: dict[str, bool] = {}

    def _make(params: Any) -> _FakeGen:
        captured['skip_past'] = params.skip_past
        return _FakeGen(finishes=True)

    monkeypatch.setattr('eventum.mcp.tools.run.Generator', _make)
    await run_generator(_ctx(tmp_path), 'g', skip_past=False)
    assert captured['skip_past'] is False
