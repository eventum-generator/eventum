"""Tests for bounded one-shot generator runs."""

from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from eventum.app.bounded_run import (
    _MAX_TIMEOUT,
    _POLL_INTERVAL,
    _clamp_timeout,
    run_bounded,
)
from eventum.core.config_loader import ConfigurationLoadError
from eventum.core.executor import ExecutionError
from eventum.core.parameters import GeneratorParameters

_TIMEOUT = 0.2
_CAP = 5
_E2E_COUNT = 10


def _params(tmp_path: Path) -> GeneratorParameters:
    return GeneratorParameters(
        id='g',
        path=tmp_path / 'generator.yml',
        live_mode=False,
        skip_past=False,
    )


class _FakeOutput:
    """Output plugin stand-in with mutable counters."""

    def __init__(self) -> None:
        self.written = 0
        self.write_failed = 0
        self.format_failed = 0


class _FakeExecutor:
    """Executor stand-in driven by the test."""

    def __init__(
        self,
        output: _FakeOutput,
        *,
        writes: int = 0,
        blocks: bool = False,
        error: Exception | None = None,
    ) -> None:
        self._output = output
        self._writes = writes
        self._blocks = blocks
        self._error = error
        self._stop = Event()
        self.stop_requested = False

    def execute(self) -> None:
        """Write counters, then optionally raise or block until stop."""
        self._output.written += self._writes
        if self._error is not None:
            raise self._error
        if self._blocks:
            self._stop.wait()

    def request_stop(self) -> None:
        """Record the stop request and unblock execute()."""
        self.stop_requested = True
        self._stop.set()


def _patch_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    executor: _FakeExecutor,
    output: _FakeOutput,
) -> None:
    """Replace load/init_plugins/Executor with controllable fakes."""
    plugins = SimpleNamespace(input=[], event=None, output=[output])
    monkeypatch.setattr(
        'eventum.app.bounded_run.load',
        lambda _path, _params: SimpleNamespace(
            input=[], event=None, output=[]
        ),
    )
    monkeypatch.setattr(
        'eventum.app.bounded_run.init_plugins',
        lambda **_kwargs: plugins,
    )
    monkeypatch.setattr(
        'eventum.app.bounded_run.Executor',
        lambda **_kwargs: executor,
    )


@pytest.mark.parametrize(
    ('timeout', 'expected'),
    [
        (-1.0, _POLL_INTERVAL),
        (0.0, _POLL_INTERVAL),
        (30.0, 30.0),
        (100_000.0, _MAX_TIMEOUT),
    ],
)
def test_clamp_timeout(timeout: float, expected: float) -> None:
    """Timeouts are clamped to the poll-interval..max-timeout range."""
    assert _clamp_timeout(timeout) == expected


def test_run_bounded_completed_reports_final_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run that finishes naturally reports the final counts."""
    output = _FakeOutput()
    output.write_failed = 2
    executor = _FakeExecutor(output, writes=_CAP)
    _patch_pipeline(monkeypatch, executor, output)

    summary = run_bounded(_params(tmp_path), timeout_seconds=5.0)

    assert summary.outcome == 'completed'
    assert summary.events_written == _CAP
    assert summary.events_failed == 2  # noqa: PLR2004
    assert executor.stop_requested is False


def test_run_bounded_times_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An open-ended run is stopped at the timeout."""
    output = _FakeOutput()
    executor = _FakeExecutor(output, blocks=True)
    _patch_pipeline(monkeypatch, executor, output)

    summary = run_bounded(_params(tmp_path), timeout_seconds=_TIMEOUT)

    assert summary.outcome == 'timeout'
    assert summary.events_written == 0
    assert executor.stop_requested is True


def test_run_bounded_caps_on_max_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An open-ended run is stopped once max_events is written."""
    output = _FakeOutput()
    executor = _FakeExecutor(output, writes=_CAP, blocks=True)
    _patch_pipeline(monkeypatch, executor, output)

    summary = run_bounded(
        _params(tmp_path), timeout_seconds=5.0, max_events=_CAP
    )

    assert summary.outcome == 'max_events'
    assert summary.events_written == _CAP
    assert executor.stop_requested is True


def test_run_bounded_ignores_nonpositive_max_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A max_events below 1 means no cap, not an instant stop."""
    output = _FakeOutput()
    executor = _FakeExecutor(output, blocks=True)
    _patch_pipeline(monkeypatch, executor, output)

    summary = run_bounded(
        _params(tmp_path), timeout_seconds=_TIMEOUT, max_events=0
    )

    assert summary.outcome == 'timeout'


def test_run_bounded_classifies_execution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An execution error yields the error outcome, not an exception."""
    output = _FakeOutput()
    error = ExecutionError('Execution failed', context={'reason': 'test'})
    executor = _FakeExecutor(output, writes=_CAP, error=error)
    _patch_pipeline(monkeypatch, executor, output)

    summary = run_bounded(_params(tmp_path), timeout_seconds=5.0)

    assert summary.outcome == 'error'
    assert summary.events_written == _CAP


def test_run_bounded_classifies_unexpected_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unexpected execution error also yields the error outcome."""
    output = _FakeOutput()
    executor = _FakeExecutor(output, error=RuntimeError('boom'))
    _patch_pipeline(monkeypatch, executor, output)

    summary = run_bounded(_params(tmp_path), timeout_seconds=5.0)

    assert summary.outcome == 'error'


def test_run_bounded_missing_config_raises(tmp_path: Path) -> None:
    """A missing config file raises a configuration load error."""
    with pytest.raises(ConfigurationLoadError):
        run_bounded(_params(tmp_path), timeout_seconds=5.0)


def test_run_bounded_end_to_end_reports_written_events(
    tmp_path: Path,
) -> None:
    """A fast finite generator reports its real written counts.

    Regression: counts must come from plugin instances held by the
    runner itself, not from a reference captured after the run may
    have already completed and released them.
    """
    (tmp_path / 'produce.py').write_text(
        'def produce(params):\n    return [str(params["timestamp"])]\n',
    )
    (tmp_path / 'generator.yml').write_text(
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

    summary = run_bounded(_params(tmp_path), timeout_seconds=30.0)

    assert summary.outcome == 'completed'
    assert summary.events_written == _E2E_COUNT
    assert summary.events_failed == 0
