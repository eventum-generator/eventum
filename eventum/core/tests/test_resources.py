"""Tests for per-generator resource accounting."""

import threading

import pytest

from eventum.core.resources import (
    collect_thread_usage,
    owns_thread,
    sample_thread_cpu_times,
)


def _run_named_thread(name: str) -> tuple[threading.Thread, threading.Event]:
    """Start a daemon thread with the given name that waits to be
    released, returning it along with its release event.
    """
    release = threading.Event()
    started = threading.Event()

    def wait() -> None:
        started.set()
        release.wait(timeout=5)

    thread = threading.Thread(target=wait, name=name, daemon=True)
    thread.start()

    assert started.wait(timeout=5)
    assert thread.native_id is not None

    return thread, release


# - Thread ownership --------------------------------------------------


@pytest.mark.parametrize(
    'name',
    [
        'generator:gen-1',
        'input:gen-1',
        'event:gen-1',
        'output:gen-1',
        'input-source-0:gen-1',
        'input-source-11:gen-1',
        'output-worker:gen-1:_0',
    ],
)
def test_owns_thread_of_generator(name: str):
    """Every thread a generator runs is recognized as its own."""
    assert owns_thread(name, 'gen-1')


@pytest.mark.parametrize(
    'name',
    [
        'MainThread',
        'server',
        'generators-starting:_0',
        'generators-stopping:_0',
        'input:gen-2',
        'output-worker:gen-11:_0',
        'unknown-role:gen-1',
    ],
)
def test_does_not_own_foreign_thread(name: str):
    """Threads of other generators and of the app are not counted."""
    assert not owns_thread(name, 'gen-1')


def test_owns_thread_of_generator_with_colon_in_id():
    """A colon in the generator id does not confuse ownership."""
    assert owns_thread('event:gen:1', 'gen:1')
    assert not owns_thread('event:gen:1', 'gen')


# - Thread usage ------------------------------------------------------


def test_collect_thread_usage_sums_cpu_of_own_threads():
    """CPU time of the generator's own threads is summed."""
    thread, release = _run_named_thread('event:gen-1')
    foreign, foreign_release = _run_named_thread('event:gen-2')

    assert thread.native_id is not None
    assert foreign.native_id is not None

    try:
        usage = collect_thread_usage(
            'gen-1',
            {thread.native_id: 2.5, foreign.native_id: 100.0},
        )
    finally:
        release.set()
        foreign_release.set()
        thread.join(timeout=5)
        foreign.join(timeout=5)

    assert usage.count == 1
    assert usage.cpu_seconds == 2.5


def test_collect_thread_usage_of_unsampled_thread():
    """A thread missing from the sample counts as no CPU time."""
    thread, release = _run_named_thread('output-worker:gen-1:_0')

    try:
        usage = collect_thread_usage('gen-1', {})
    finally:
        release.set()
        thread.join(timeout=5)

    assert usage.count == 1
    assert usage.cpu_seconds == 0.0


def test_collect_thread_usage_without_threads():
    """A generator running no threads occupies none."""
    usage = collect_thread_usage('gen-without-threads', {})

    assert usage.count == 0
    assert usage.cpu_seconds == 0.0


def test_collect_thread_usage_samples_cpu_times_itself():
    """An omitted sample is taken by the collector."""
    thread, release = _run_named_thread('event:gen-1')

    try:
        usage = collect_thread_usage('gen-1')
    finally:
        release.set()
        thread.join(timeout=5)

    assert usage.count == 1
    assert usage.cpu_seconds >= 0


# - CPU sampling ------------------------------------------------------


def test_sample_thread_cpu_times():
    """Sampling reports CPU time of the threads of the process."""
    times = sample_thread_cpu_times()

    assert threading.get_native_id() in times
    assert all(seconds >= 0 for seconds in times.values())
