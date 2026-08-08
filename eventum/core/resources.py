"""Accounting of runtime resources occupied by a single generator.

Generators run as threads of one process, which bounds what can be
attributed to a single generator. CPU time can: every thread a generator
runs is named after it, and the OS accounts CPU time per thread. Memory
cannot - the process heap is shared, so a generator's share of it is not
observable from inside. Queue fill levels stand in for it, since the
queues hold the bulk of what a generator keeps in flight.
"""

import threading
from collections.abc import Mapping
from dataclasses import dataclass

import psutil

_PROCESS = psutil.Process()

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

    """

    size: int
    maxsize: int


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

    queues : QueuesUsage
        Fill levels of the queues between the pipeline stages.

    """

    thread_count: int
    cpu_seconds: float
    queues: QueuesUsage


@dataclass(frozen=True)
class ThreadUsage:
    """Threads of a generator and the CPU time they consumed.

    Attributes
    ----------
    count : int
        Number of threads.

    cpu_seconds : float
        CPU time consumed by the threads.

    """

    count: int
    cpu_seconds: float


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
    """Collect threads of a generator and their CPU time.

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
        Number of threads and the CPU time they consumed. CPU time of a
        thread that is missing from the sample counts as zero, which
        happens for a thread that started after it was taken.

    """
    times = sample_thread_cpu_times() if cpu_times is None else cpu_times

    count = 0
    cpu_seconds = 0.0

    for thread in threading.enumerate():
        if not owns_thread(thread.name, generator_id):
            continue

        count += 1

        if thread.native_id is not None:
            cpu_seconds += times.get(thread.native_id, 0.0)

    return ThreadUsage(count=count, cpu_seconds=cpu_seconds)
