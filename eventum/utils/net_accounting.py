"""In-process network byte accounting.

psutil reports network counters only system-wide (``net_io_counters``),
never per process, and the operating system exposes no portable
per-process network byte counter. To report how much traffic *this
application* moves, this module wraps the send and receive methods of
``socket.socket`` so every byte the process passes through a Python
socket is counted.

Eventum's network output plugins (tcp, udp, http and opensearch via
httpx, kafka via aiokafka, clickhouse) all run on asyncio and route
through Python sockets, so the counters reflect the application's real
network I/O - including TLS, whose encrypted bytes reach the raw socket.
Counts are cumulative since ``install`` was called.

Bytes are counted per thread name, so a caller can read the traffic of
one part of the application - the threads a single generator runs, for
one - instead of the process total. Counters of a name outlive the
threads that carried it, which keeps the traffic of a thread pool that
is recreated over the lifetime of the application.
"""

import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class NetUsage:
    """Bytes passed through sockets.

    Attributes
    ----------
    sent_bytes : int
        Number of bytes sent.

    received_bytes : int
        Number of bytes received.

    """

    sent_bytes: int
    received_bytes: int


class _Bucket:
    """Byte counters shared by the threads carrying one name.

    Threads with the same name share their counters, so the increments
    are taken under a lock. It is held for a single addition, which is
    negligible next to the syscall the addition accompanies.
    """

    __slots__ = ('_lock', 'received', 'sent')

    def __init__(self) -> None:
        self.sent = 0
        self.received = 0
        self._lock = threading.Lock()

    def add_sent(self, count: int) -> None:
        with self._lock:
            self.sent += count

    def add_received(self, count: int) -> None:
        with self._lock:
            self.received += count


_registry_lock = threading.Lock()
_buckets: dict[str, _Bucket] = {}
_local = threading.local()
_installed = False


def usage_of(matches: Callable[[str], bool]) -> NetUsage:
    """Get bytes passed through sockets by a part of the application.

    Parameters
    ----------
    matches : Callable[[str], bool]
        Predicate telling whether a thread with this name belongs to the
        part in question.

    Returns
    -------
    NetUsage
        Bytes sent and received by the matching threads.

    """
    with _registry_lock:
        buckets = [
            bucket for name, bucket in _buckets.items() if matches(name)
        ]

    return NetUsage(
        sent_bytes=sum(bucket.sent for bucket in buckets),
        received_bytes=sum(bucket.received for bucket in buckets),
    )


def bytes_sent() -> int:
    """Return total bytes sent by this process since ``install``."""
    return _total().sent_bytes


def bytes_received() -> int:
    """Return total bytes received by this process since ``install``."""
    return _total().received_bytes


def _total() -> NetUsage:
    """Get bytes passed through sockets by the whole process."""
    with _registry_lock:
        buckets = list(_buckets.values())

    return NetUsage(
        sent_bytes=sum(bucket.sent for bucket in buckets),
        received_bytes=sum(bucket.received for bucket in buckets),
    )


def _bucket() -> _Bucket:
    """Get the counters of the calling thread, registering them if the
    thread is counting for the first time.
    """
    try:
        return _local.bucket  # type: ignore[no-any-return]
    except AttributeError:
        pass

    name = threading.current_thread().name

    with _registry_lock:
        bucket = _buckets.get(name)

        if bucket is None:
            bucket = _Bucket()
            _buckets[name] = bucket

    _local.bucket = bucket

    return bucket


def _buflen(data: object) -> int:
    """Return the number of bytes in a bytes-like object."""
    return memoryview(data).nbytes  # type: ignore[arg-type]


def _add_sent(count: int) -> None:
    if count:
        _bucket().add_sent(count)


def _add_received(count: int) -> None:
    if count:
        _bucket().add_received(count)


def install() -> None:
    """Wrap socket send/recv methods to count bytes.

    Idempotent - later calls are no-ops. Wraps the ``socket.socket``
    class, so it affects every socket in the process; call it once
    during startup before the application opens its sockets.

    The counter increments run on every socket operation, but the work
    is a thread-local lookup and a single integer addition, negligible
    next to the syscall it accompanies.
    """
    global _installed  # noqa: PLW0603
    if _installed:
        return
    _installed = True

    orig_send = socket.socket.send
    orig_sendall = socket.socket.sendall
    orig_sendto = socket.socket.sendto
    orig_recv = socket.socket.recv
    orig_recv_into = socket.socket.recv_into
    orig_recvfrom = socket.socket.recvfrom

    def send(self, data, *args, **kwargs):  # noqa: ANN001, ANN202, ANN002, ANN003
        count = orig_send(self, data, *args, **kwargs)
        _add_sent(count)
        return count

    def sendall(self, data, *args, **kwargs):  # noqa: ANN001, ANN202, ANN002, ANN003
        orig_sendall(self, data, *args, **kwargs)
        _add_sent(_buflen(data))

    def sendto(self, data, *args, **kwargs):  # noqa: ANN001, ANN202, ANN002, ANN003
        count = orig_sendto(self, data, *args, **kwargs)
        _add_sent(count)
        return count

    def recv(self, *args, **kwargs):  # noqa: ANN001, ANN202, ANN002, ANN003
        data = orig_recv(self, *args, **kwargs)
        _add_received(len(data))
        return data

    def recv_into(self, *args, **kwargs):  # noqa: ANN001, ANN202, ANN002, ANN003
        count = orig_recv_into(self, *args, **kwargs)
        _add_received(count)
        return count

    def recvfrom(self, *args, **kwargs):  # noqa: ANN001, ANN202, ANN002, ANN003
        data, address = orig_recvfrom(self, *args, **kwargs)
        _add_received(len(data))
        return data, address

    socket.socket.send = send  # type: ignore[method-assign]
    socket.socket.sendall = sendall  # type: ignore[method-assign]
    socket.socket.sendto = sendto  # type: ignore[method-assign]
    socket.socket.recv = recv  # type: ignore[method-assign]
    socket.socket.recv_into = recv_into  # type: ignore[method-assign]
    socket.socket.recvfrom = recvfrom  # type: ignore[method-assign]
