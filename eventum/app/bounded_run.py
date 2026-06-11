"""Bounded one-shot execution of a generator to its outputs.

Loads a generator configuration, initializes its plugins, and runs
the full pipeline while holding the plugin instances for the whole
call, so the final output counts stay readable however fast the run
ends. The run always terminates: naturally for a finite generator,
or stopped at a timeout or written-events cap for an open-ended one.
"""

import time
from dataclasses import dataclass
from threading import Thread
from typing import Literal

import structlog

from eventum.core.config_loader import load
from eventum.core.executor import ExecutionError, Executor
from eventum.core.parameters import GeneratorParameters
from eventum.core.plugins_initializer import (
    InitializedPlugins,
    init_plugins,
)

logger = structlog.stdlib.get_logger()

RunOutcome = Literal['completed', 'timeout', 'max_events', 'error']
"""How a bounded run ended: naturally ('completed' or 'error') or
stopped at a bound ('timeout' or 'max_events')."""

_MAX_TIMEOUT = 300.0
_POLL_INTERVAL = 0.05


@dataclass(frozen=True)
class RunSummary:
    """Result of a bounded generator run.

    Attributes
    ----------
    outcome : RunOutcome
        How the run ended: 'completed' or 'error' for a natural
        finish, 'timeout' or 'max_events' for a run stopped at a
        bound.

    events_written : int
        Events successfully written across all output plugins.

    events_failed : int
        Events that failed formatting or writing across all output
        plugins.

    """

    outcome: RunOutcome
    events_written: int
    events_failed: int


def _clamp_timeout(timeout_seconds: float) -> float:
    """Clamp a timeout to [poll interval, max timeout] seconds."""
    return max(_POLL_INTERVAL, min(timeout_seconds, _MAX_TIMEOUT))


def _output_counts(plugins: InitializedPlugins) -> tuple[int, int]:
    """Return (written, failed) summed across the output plugins."""
    written = sum(p.written for p in plugins.output)
    failed = sum(p.write_failed + p.format_failed for p in plugins.output)
    return written, failed


def run_bounded(
    params: GeneratorParameters,
    *,
    timeout_seconds: float,
    max_events: int | None = None,
) -> RunSummary:
    """Run a generator pipeline to its outputs within bounds.

    Loads the configuration, initializes the plugins, and executes
    the full pipeline, blocking until the run ends. The run always
    terminates: naturally for a finite generator, or stopped once
    the timeout or the written-events cap is reached. The plugin
    instances are held for the whole call, so the returned counts
    reflect the final state of the output plugins even when the run
    ends faster than the first poll.

    Parameters
    ----------
    params : GeneratorParameters
        Parameters of the generator to run.

    timeout_seconds : float
        Maximum seconds to run before requesting a stop. Clamped to
        at most 300 seconds and at least the poll interval.

    max_events : int | None, default=None
        Stop after at least this many events are written, if set.
        Values below 1 are treated as no cap.

    Returns
    -------
    RunSummary
        Outcome and final output counts.

    Raises
    ------
    ConfigurationLoadError
        If the config cannot be loaded, parsed, or name-validated.

    InitializationError
        If any plugin's nested config is invalid.

    ImproperlyConfiguredError
        If the plugins cannot be executed with the given parameters.

    Notes
    -----
    Errors raised after execution has started do not propagate: they
    are logged and classified as the 'error' outcome, since events
    may already have been written by then.

    """
    config = load(params.path, params.params)
    plugins = init_plugins(
        input=config.input,
        event=config.event,
        output=config.output,
        params=params,
    )
    executor = Executor(
        input=plugins.input,
        event=plugins.event,
        output=plugins.output,
        params=params,
    )

    if max_events is not None and max_events < 1:
        max_events = None

    failures: list[Exception] = []

    def _execute() -> None:
        structlog.contextvars.bind_contextvars(generator_id=params.id)
        try:
            executor.execute()
        except ExecutionError as e:
            logger.error(str(e), **e.context)
            failures.append(e)
        except Exception as e:
            logger.exception(
                'Unexpected error occurred during execution',
                reason=str(e),
            )
            failures.append(e)

    thread = Thread(target=_execute, name=f'generator:{params.id}')
    thread.start()

    deadline = time.monotonic() + _clamp_timeout(timeout_seconds)
    bound: RunOutcome | None = None

    while thread.is_alive():
        if max_events is not None:
            written, _ = _output_counts(plugins)
            if written >= max_events:
                bound = 'max_events'
                break

        if time.monotonic() >= deadline:
            bound = 'timeout'
            break

        time.sleep(_POLL_INTERVAL)

    if bound is not None and thread.is_alive():
        executor.request_stop()
        thread.join()
        outcome: RunOutcome = bound
    else:
        # A natural finish at the same moment as a bound hit is
        # classified as the natural outcome.
        thread.join()
        outcome = 'error' if failures else 'completed'

    written, failed = _output_counts(plugins)

    return RunSummary(
        outcome=outcome,
        events_written=written,
        events_failed=failed,
    )
