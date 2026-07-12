"""Tests for in-process network byte accounting."""

import socket

from eventum.utils import net_accounting


def test_counts_sent_and_received_bytes() -> None:
    """Wrapped sockets count bytes sent and received."""
    net_accounting.install()
    sender, receiver = socket.socketpair()
    try:
        before_sent = net_accounting.bytes_sent()
        before_received = net_accounting.bytes_received()

        payload = b'eventum' * 1000
        sender.sendall(payload)

        received = b''
        while len(received) < len(payload):
            chunk = receiver.recv(4096)
            if not chunk:
                break
            received += chunk

        assert received == payload
        assert net_accounting.bytes_sent() - before_sent >= len(payload)
        assert net_accounting.bytes_received() - before_received >= len(
            payload
        )
    finally:
        sender.close()
        receiver.close()


def test_install_is_idempotent() -> None:
    """A second install does not double-count bytes."""
    net_accounting.install()
    net_accounting.install()

    sender, receiver = socket.socketpair()
    try:
        before = net_accounting.bytes_sent()
        sent = sender.send(b'x' * 64)
        receiver.recv(sent)

        # Counted once despite the double install (not double-wrapped).
        assert net_accounting.bytes_sent() - before == sent
    finally:
        sender.close()
        receiver.close()
