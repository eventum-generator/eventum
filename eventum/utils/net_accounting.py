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
"""

import socket
import threading

_lock = threading.Lock()
_sent = 0
_received = 0
_installed = False


def bytes_sent() -> int:
    """Return total bytes sent by this process since ``install``."""
    return _sent


def bytes_received() -> int:
    """Return total bytes received by this process since ``install``."""
    return _received


def _buflen(data: object) -> int:
    """Return the number of bytes in a bytes-like object."""
    return memoryview(data).nbytes  # type: ignore[arg-type]


def _add_sent(count: int) -> None:
    global _sent  # noqa: PLW0603
    if count:
        with _lock:
            _sent += count


def _add_received(count: int) -> None:
    global _received  # noqa: PLW0603
    if count:
        with _lock:
            _received += count


def install() -> None:
    """Wrap socket send/recv methods to count bytes.

    Idempotent - later calls are no-ops. Wraps the ``socket.socket``
    class, so it affects every socket in the process; call it once
    during startup before the application opens its sockets.

    The counter increments hold a lock. This runs on every socket
    operation, but the work is a single integer addition, negligible
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
