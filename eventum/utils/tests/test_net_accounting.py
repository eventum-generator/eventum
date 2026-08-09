"""Tests for in-process network byte accounting."""

import socket
import threading

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


def test_usage_of_counts_bytes_of_matching_threads() -> None:
    """Bytes are attributed to the thread that passed them."""
    net_accounting.install()

    payload = b'eventum' * 500
    done = threading.Event()

    def exchange() -> None:
        sender, receiver = socket.socketpair()
        try:
            sender.sendall(payload)
            receiver.recv(len(payload))
        finally:
            sender.close()
            receiver.close()
            done.set()

    thread = threading.Thread(target=exchange, name='counted', daemon=True)
    thread.start()

    assert done.wait(timeout=5)
    thread.join(timeout=5)

    counted = net_accounting.usage_of(lambda name: name == 'counted')
    others = net_accounting.usage_of(lambda name: name != 'counted')

    assert counted.sent_bytes >= len(payload)
    assert counted.received_bytes >= len(payload)
    assert (
        others.sent_bytes + counted.sent_bytes == net_accounting.bytes_sent()
    )


def test_usage_of_without_matching_threads() -> None:
    """A part of the application that opened no socket moved no bytes."""
    usage = net_accounting.usage_of(lambda name: name == 'never-counted')

    assert usage.sent_bytes == 0
    assert usage.received_bytes == 0


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
