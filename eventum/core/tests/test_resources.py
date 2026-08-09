"""Tests for per-generator resource accounting."""

import socket
import threading
from pathlib import Path

import pytest

from eventum.core.resources import (
    collect_network_usage,
    collect_thread_usage,
    owns_thread,
    sample_thread_cpu_times,
)
from eventum.utils import net_accounting

PROC_TASK_AVAILABLE = Path('/proc/self/task').exists()


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
    assert usage.run_delay_seconds == 0.0
    assert usage.disk_read_bytes == 0
    assert usage.disk_written_bytes == 0


@pytest.mark.skipif(
    not PROC_TASK_AVAILABLE,
    reason='per-thread counters are read from /proc',
)
def test_collect_thread_usage_counts_written_bytes(tmp_path):
    """Bytes a thread of the generator wrote out are counted."""
    payload = b'x' * 4096
    written = threading.Event()
    release = threading.Event()

    def write_and_wait() -> None:
        (tmp_path / 'events.txt').write_bytes(payload)
        written.set()
        release.wait(timeout=5)

    thread = threading.Thread(
        target=write_and_wait,
        name='output:gen-disk',
        daemon=True,
    )
    thread.start()

    try:
        assert written.wait(timeout=5)
        usage = collect_thread_usage('gen-disk', {})
    finally:
        release.set()
        thread.join(timeout=5)

    assert usage.count == 1
    assert usage.disk_written_bytes >= len(payload)
    assert usage.run_delay_seconds >= 0.0


# - Network usage -----------------------------------------------------


def test_collect_network_usage_of_own_threads():
    """Bytes a thread of the generator sent are counted for it alone."""
    net_accounting.install()

    payload = b'eventum' * 100
    sent = threading.Event()

    def send() -> None:
        sender, receiver = socket.socketpair()
        try:
            sender.sendall(payload)
            receiver.recv(len(payload))
        finally:
            sender.close()
            receiver.close()
            sent.set()

    thread = threading.Thread(
        target=send,
        name='output:gen-net',
        daemon=True,
    )
    thread.start()

    assert sent.wait(timeout=5)
    thread.join(timeout=5)

    usage = collect_network_usage('gen-net')

    assert usage.sent_bytes >= len(payload)
    assert usage.received_bytes >= len(payload)


def test_collect_network_usage_without_traffic():
    """A generator that opened no socket moved no bytes."""
    usage = collect_network_usage('gen-without-traffic')

    assert usage.sent_bytes == 0
    assert usage.received_bytes == 0


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
