"""Accounting of runtime resources occupied by a single generator.

Generators run as threads of one process, which bounds what can be
attributed to a single generator. Processor time, scheduling delay, file
system and network bytes can: every thread a generator runs is named
after it, and all four are accounted per thread. Memory cannot - the
process heap is shared, so a generator's share of it is not observable
from inside. Queue fill levels stand in for it, since the queues hold the
bulk of what a generator keeps in flight.

Reading scheduling delay and file system bytes goes through `/proc`, so
both are reported on Linux only and count as zero elsewhere.
"""

import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import psutil

from eventum.utils.net_accounting import NetUsage, usage_of

_PROCESS = psutil.Process()

_PROC_TASK = Path('/proc/self/task')
"""Directory holding a subdirectory per thread of this process."""

_NS_PER_SECOND = 1e9

_STAGE_ROLES = frozenset({'generator', 'input', 'event', 'output'})
"""Thread roles a generator runs exactly one of."""

_INPUT_SOURCE_ROLE_PREFIX = 'input-source-'
"""Role prefix of per-source threads of the input stage."""

_OUTPUT_WORKER_ROLE = 'output-worker'
"""Role of the worker threads the output stage offloads work to."""

type ThreadCpuTimes = Mapping[int, float]
"""CPU seconds consumed by each thread of the process, keyed by its OS
level thread id."""


@dataclass(frozen=True)
class QueueUsage:
    """Fill level of a single pipeline queue.

    Attributes
    ----------
    size : int
        Number of batches waiting in the queue.

    maxsize : int
        Maximum number of batches the queue holds.

    size_bytes : int
        Number of bytes the batches waiting in the queue occupy.

    max_bytes : int | None
        Maximum number of bytes the queue holds, `None` if their size is
        not limited.

    """

    size: int
    maxsize: int
    size_bytes: int
    max_bytes: int | None


@dataclass(frozen=True)
class QueuesUsage:
    """Fill levels of the queues connecting the pipeline stages.

    Attributes
    ----------
    timestamps : QueueUsage
        Queue between the input and the event stage.

    events : QueueUsage
        Queue between the event and the output stage.

    """

    timestamps: QueueUsage
    events: QueueUsage


@dataclass(frozen=True)
class GeneratorResources:
    """Runtime resources a generator occupies in the process.

    Attributes
    ----------
    thread_count : int
        Number of threads the generator runs.

    cpu_seconds : float
        CPU time consumed by those threads since the generator started.

    run_delay_seconds : float
        Time those threads spent ready to run while waiting for a
        processor since the generator started.

    disk_read_bytes : int
        Number of bytes those threads read through the file system.

    disk_written_bytes : int
        Number of bytes those threads wrote through the file system.

    network_sent_bytes : int
        Number of bytes those threads sent over the network.

    network_received_bytes : int
        Number of bytes those threads received over the network.

    queues : QueuesUsage
        Fill levels of the queues between the pipeline stages.

    """

    thread_count: int
    cpu_seconds: float
    run_delay_seconds: float
    disk_read_bytes: int
    disk_written_bytes: int
    network_sent_bytes: int
    network_received_bytes: int
    queues: QueuesUsage


@dataclass(frozen=True)
class ThreadUsage:
    """Threads of a generator and the resources they consumed.

    Attributes
    ----------
    count : int
        Number of threads.

    cpu_seconds : float
        CPU time consumed by the threads.

    run_delay_seconds : float
        Time the threads spent ready to run while waiting for a
        processor.

    disk_read_bytes : int
        Number of bytes the threads read through the file system.

    disk_written_bytes : int
        Number of bytes the threads wrote through the file system.

    """

    count: int
    cpu_seconds: float
    run_delay_seconds: float
    disk_read_bytes: int
    disk_written_bytes: int


def sample_thread_cpu_times() -> ThreadCpuTimes:
    """Read CPU time consumed by every thread of the process.

    Returns
    -------
    ThreadCpuTimes
        CPU seconds per thread id, empty if the process cannot be
        inspected.

    Notes
    -----
    Reads through the OS, so the call blocks and its cost grows with the
    number of threads. Sample once and share the result when accounting
    for several generators.

    """
    try:
        threads = _PROCESS.threads()
    except psutil.Error, OSError:
        return {}

    return {
        thread.id: thread.user_time + thread.system_time for thread in threads
    }


def owns_thread(thread_name: str, generator_id: str) -> bool:
    """Check whether a thread with this name belongs to a generator.

    Parameters
    ----------
    thread_name : str
        Name of the thread.

    generator_id : str
        ID of the generator.

    Returns
    -------
    bool
        `True` if the thread belongs to the generator, `False`
        otherwise.

    Notes
    -----
    Ownership is read from the name, since every thread a generator runs
    is named `<role>:<generator id>`. Worker threads of the output stage
    carry a pool counter of their own after the id.

    """
    role, separator, owner = thread_name.partition(':')

    if not separator:
        return False

    if role == _OUTPUT_WORKER_ROLE:
        return owner.startswith(f'{generator_id}:')

    return owner == generator_id and (
        role in _STAGE_ROLES or role.startswith(_INPUT_SOURCE_ROLE_PREFIX)
    )


def collect_thread_usage(
    generator_id: str,
    cpu_times: ThreadCpuTimes | None = None,
) -> ThreadUsage:
    """Collect threads of a generator and the resources they consumed.

    Parameters
    ----------
    generator_id : str
        ID of the generator.

    cpu_times : ThreadCpuTimes | None, default=None
        Already sampled CPU times to read from instead of sampling
        them.

    Returns
    -------
    ThreadUsage
        Number of threads and the resources they consumed. CPU time of a
        thread that is missing from the sample counts as zero, which
        happens for a thread that started after it was taken.

    """
    times = sample_thread_cpu_times() if cpu_times is None else cpu_times

    count = 0
    cpu_seconds = 0.0
    run_delay_seconds = 0.0
    read_bytes = 0
    written_bytes = 0

    for thread in threading.enumerate():
        if not owns_thread(thread.name, generator_id):
            continue

        count += 1

        if thread.native_id is None:
            continue

        cpu_seconds += times.get(thread.native_id, 0.0)
        run_delay_seconds += _read_run_delay_seconds(thread.native_id)

        thread_read, thread_written = _read_disk_bytes(thread.native_id)
        read_bytes += thread_read
        written_bytes += thread_written

    return ThreadUsage(
        count=count,
        cpu_seconds=cpu_seconds,
        run_delay_seconds=run_delay_seconds,
        disk_read_bytes=read_bytes,
        disk_written_bytes=written_bytes,
    )


def collect_network_usage(generator_id: str) -> NetUsage:
    """Collect bytes a generator passed over the network.

    Parameters
    ----------
    generator_id : str
        ID of the generator.

    Returns
    -------
    NetUsage
        Bytes sent and received by the threads of the generator since
        the application started.

    """
    return usage_of(lambda name: owns_thread(name, generator_id))


def _read_run_delay_seconds(thread_id: int) -> float:
    """Read time a thread spent ready to run without running.

    Returns zero when the counter is unavailable, which is the case
    outside Linux and for a thread that ended in the meantime.
    """
    try:
        stats = (_PROC_TASK / str(thread_id) / 'schedstat').read_text()

        return int(stats.split()[1]) / _NS_PER_SECOND
    except OSError, IndexError, ValueError:
        return 0.0


def _read_disk_bytes(thread_id: int) -> tuple[int, int]:
    """Read bytes a thread read and wrote through the file system.

    Counts the bytes the thread passed to the system calls, not the ones
    that reached the block device, since the latter are accounted to
    whichever thread the kernel happens to flush the page cache from.
    Socket traffic is not part of either counter.

    Returns zeroes when the counters are unavailable, which is the case
    outside Linux and for a thread that ended in the meantime.
    """
    read_bytes = 0
    written_bytes = 0

    try:
        counters = (_PROC_TASK / str(thread_id) / 'io').read_text()

        for line in counters.splitlines():
            field, _, value = line.partition(': ')

            if field == 'rchar':
                read_bytes = int(value)
            elif field == 'wchar':
                written_bytes = int(value)
    except OSError, ValueError:
        return (0, 0)

    return (read_bytes, written_bytes)
