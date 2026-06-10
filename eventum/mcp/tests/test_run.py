"""Tests for the one-shot run tool."""

from pathlib import Path
from typing import Any

import pytest

from eventum.app.bounded_run import RunOutcome, RunSummary
from eventum.core.config_loader import ConfigurationLoadError
from eventum.core.parameters import GeneratorParameters
from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.run import run_generator

_RUN_BOUNDED = 'eventum.mcp.tools.run.run_bounded'
_TIMEOUT = 7.5
_MAX_EVENTS = 99


def _ctx(tmp_path: Path, *, read_only: bool = False) -> FileAuthoringContext:
    return FileAuthoringContext(generators_dir=tmp_path, read_only=read_only)


def _expected_cfg_path(tmp_path: Path, name: str) -> Path:
    """Config path as the tool resolves it (dir resolved, then file)."""
    return (tmp_path / name).resolve() / 'generator.yml'


def _make_gen(tmp_path: Path, name: str) -> None:
    (tmp_path / name).mkdir()
    (tmp_path / name / 'generator.yml').write_text(
        'input: []\n', encoding='utf-8'
    )


def _failing_run(*_args: Any, **_kwargs: Any) -> RunSummary:
    pytest.fail('run_bounded must not be called')


async def test_run_gated_on_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read-only mode refuses to run a generator."""
    monkeypatch.setattr(_RUN_BOUNDED, _failing_run)
    result = await run_generator(_ctx(tmp_path, read_only=True), 'g')
    assert isinstance(result, ToolFailure)
    assert 'read-only' in result.error


async def test_run_missing_generator(tmp_path: Path) -> None:
    """An unknown generator name yields a ToolFailure."""
    result = await run_generator(_ctx(tmp_path), 'ghost')
    assert isinstance(result, ToolFailure)


@pytest.mark.parametrize(
    'outcome', ['completed', 'timeout', 'max_events', 'error']
)
async def test_run_serializes_outcome_and_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: RunOutcome,
) -> None:
    """Each run outcome and its counts are reported to the agent."""
    _make_gen(tmp_path, 'g')
    monkeypatch.setattr(
        _RUN_BOUNDED,
        lambda *_a, **_k: RunSummary(
            outcome=outcome, events_written=42, events_failed=3
        ),
    )
    result = await run_generator(_ctx(tmp_path), 'g')
    assert result == {
        'id': 'g',
        'reason': outcome,
        'events_written': 42,
        'events_failed': 3,
    }


async def test_run_passes_parameters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run parameters and bounds reach the bounded-run service."""
    _make_gen(tmp_path, 'g')
    captured: dict[str, Any] = {}

    def _fake(
        params: GeneratorParameters,
        *,
        timeout_seconds: float,
        max_events: int | None = None,
    ) -> RunSummary:
        captured['params'] = params
        captured['timeout_seconds'] = timeout_seconds
        captured['max_events'] = max_events
        return RunSummary(
            outcome='completed', events_written=0, events_failed=0
        )

    monkeypatch.setattr(_RUN_BOUNDED, _fake)
    result = await run_generator(
        _ctx(tmp_path),
        'g',
        timeout_seconds=_TIMEOUT,
        max_events=_MAX_EVENTS,
        skip_past=False,
        params={'k': 'v'},
    )

    assert not isinstance(result, ToolFailure)
    run_params = captured['params']
    assert run_params.id == 'g'
    assert run_params.path == _expected_cfg_path(tmp_path, 'g')
    assert run_params.live_mode is False
    assert run_params.skip_past is False
    assert run_params.params == {'k': 'v'}
    assert captured['timeout_seconds'] == _TIMEOUT
    assert captured['max_events'] == _MAX_EVENTS


async def test_run_config_error_returns_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A config or plugin failure surfaces as a structured failure."""
    _make_gen(tmp_path, 'g')

    def _raise(*_args: Any, **_kwargs: Any) -> RunSummary:
        msg = 'Failed to load configuration'
        raise ConfigurationLoadError(msg, context={'reason': 'bad yaml'})

    monkeypatch.setattr(_RUN_BOUNDED, _raise)
    result = await run_generator(_ctx(tmp_path), 'g')

    assert isinstance(result, ToolFailure)
    assert result.error == 'Failed to load configuration'
    assert result.details == {'reason': 'bad yaml'}


async def test_run_rejects_empty_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty name fails run-parameter validation before any run."""
    monkeypatch.setattr(_RUN_BOUNDED, _failing_run)
    result = await run_generator(_ctx(tmp_path), '')
    assert isinstance(result, ToolFailure)
    assert result.error == 'Invalid run parameters'


async def test_run_rejects_traversal_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A name escaping the workspace is refused before any run."""
    monkeypatch.setattr(_RUN_BOUNDED, _failing_run)
    result = await run_generator(_ctx(tmp_path), '../escape')
    assert isinstance(result, ToolFailure)
    assert 'outside generators dir' in result.error


async def test_run_rejects_live_managed_generator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A generator already managed live is not run standalone."""
    _make_gen(tmp_path, 'g')
    monkeypatch.setattr(
        FileAuthoringContext, 'is_live_managed', lambda _self, _id: True
    )
    monkeypatch.setattr(_RUN_BOUNDED, _failing_run)
    result = await run_generator(_ctx(tmp_path), 'g')
    assert isinstance(result, ToolFailure)
    assert 'managed live' in result.error
