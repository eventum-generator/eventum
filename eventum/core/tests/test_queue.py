"""Tests for PipelineQueue."""

import queue as queue_mod
import threading

import pytest

from eventum.core.queue import PipelineQueue


# -- Basic operations --------------------------------------------------


def test_put_and_get():
    """Put an item, get it back."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    q.put('hello')
    assert q.get() == 'hello'


def test_put_and_get_multiple():
    """Multiple items come back in FIFO order."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    q.put('a')
    q.put('b')
    q.put('c')
    assert q.get() == 'a'
    assert q.get() == 'b'
    assert q.get() == 'c'


def test_is_full_below_capacity():
    """Queue with spare capacity reports not full."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=2)
    q.put('a')
    assert q.is_full is False


def test_is_full_at_capacity():
    """Queue at maxsize reports full."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=1)
    q.put('a')
    assert q.is_full is True


def test_is_full_after_get():
    """Queue is not full after an item is consumed."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=1)
    q.put('a')
    q.get()
    assert q.is_full is False


# -- Sentinel-based close ---------------------------------------------


def test_close_returns_none_on_get():
    """After close(), get() returns None (sentinel)."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)

    t = threading.Thread(target=q.close)
    t.start()

    result = q.get()
    t.join(timeout=2)

    assert result is None
    assert not t.is_alive()


def test_close_blocks_until_sentinel_consumed():
    """close() blocks until the sentinel None is consumed via get()."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    close_returned = threading.Event()

    def closer():
        q.close()
        close_returned.set()

    t = threading.Thread(target=closer)
    t.start()

    # close_returned should NOT be set yet (no one called get)
    assert not close_returned.wait(timeout=0.3)

    # Now consume the sentinel
    q.get()
    assert close_returned.wait(timeout=2)
    t.join(timeout=2)
    assert not t.is_alive()


def test_items_before_close_are_preserved():
    """Items put before close() are available before the sentinel."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    q.put('a')
    q.put('b')

    t = threading.Thread(target=q.close)
    t.start()

    assert q.get() == 'a'
    assert q.get() == 'b'
    assert q.get() is None  # sentinel
    t.join(timeout=2)
    assert not t.is_alive()


# -- Shutdown ----------------------------------------------------------


def test_shutdown_causes_shutdown_on_put():
    """After shutdown(), put() raises queue.ShutDown."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    q.shutdown()
    with pytest.raises(queue_mod.ShutDown):
        q.put('x')


def test_shutdown_causes_shutdown_on_get():
    """After shutdown(), get() raises queue.ShutDown on empty queue."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    q.shutdown()
    with pytest.raises(queue_mod.ShutDown):
        q.get()


def test_shutdown_discards_remaining_items():
    """With immediate=True, remaining items are discarded."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    q.put('a')
    q.shutdown()
    with pytest.raises(queue_mod.ShutDown):
        q.get()


def test_close_after_shutdown_is_safe():
    """close() after shutdown() does not raise (ShutDown is swallowed)."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    q.shutdown()
    q.close()  # should not raise


# -- Thread safety -----------------------------------------------------


def test_concurrent_put_and_get():
    """Concurrent producers and consumers don't lose items."""
    q: PipelineQueue[int] = PipelineQueue(maxsize=5)
    results: list[int] = []
    count = 100

    def producer():
        for i in range(count):
            q.put(i)

    def consumer():
        while True:
            item = q.get()
            if item is None:
                break
            results.append(item)

    prod = threading.Thread(target=producer)
    cons = threading.Thread(target=consumer)
    cons.start()
    prod.start()
    prod.join(timeout=5)
    q.close()
    cons.join(timeout=5)

    assert not prod.is_alive()
    assert not cons.is_alive()
    assert sorted(results) == list(range(count))


def test_blocking_put_at_maxsize():
    """put() blocks when queue is full, unblocks when consumer drains."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=1)
    q.put('first')

    put_completed = threading.Event()

    def slow_put():
        q.put('second')
        put_completed.set()

    t = threading.Thread(target=slow_put)
    t.start()

    # put should be blocked
    assert not put_completed.wait(timeout=0.3)

    # drain one item to unblock
    q.get()
    assert put_completed.wait(timeout=2)
    assert q.get() == 'second'
    t.join(timeout=2)
    assert not t.is_alive()
