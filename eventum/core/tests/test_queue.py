"""Tests for PipelineQueue."""

import queue as queue_mod
import threading
from sys import getsizeof

import pytest

from eventum.core.queue import PipelineQueue, estimate_events_bytes

# - Basic operations --------------------------------------------------


def test_put_and_get():
    """Put an item, get it back."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    q.put('hello')
    assert q.get().item == 'hello'


def test_put_and_get_multiple():
    """Multiple items come back in FIFO order."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)
    q.put('a')
    q.put('b')
    q.put('c')
    assert q.get().item == 'a'
    assert q.get().item == 'b'
    assert q.get().item == 'c'


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


def test_maxsize_reports_configured_capacity():
    """Queue reports the capacity it was created with."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=3)
    assert q.maxsize == 3


def test_size_follows_waiting_items():
    """Queue size counts the items waiting to be consumed."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=3)
    assert q.size == 0

    q.put('a')
    q.put('b')
    assert q.size == 2

    q.get()
    assert q.size == 1


# - Sentinel-based close ---------------------------------------------


def test_close_returns_none_on_get():
    """After close(), get() returns None (sentinel)."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10)

    t = threading.Thread(target=q.close)
    t.start()

    result = q.get().item
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

    assert q.get().item == 'a'
    assert q.get().item == 'b'
    assert q.get().item is None  # sentinel
    t.join(timeout=2)
    assert not t.is_alive()


# - Shutdown ----------------------------------------------------------


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


# - Thread safety -----------------------------------------------------


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
            item = q.get().item
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


# - Size estimation ---------------------------------------------------


def test_estimate_events_bytes_of_uniform_batch():
    """Estimate of events of one size is their exact size."""
    events = ['x' * 100] * 1000

    estimated = estimate_events_bytes(events)
    exact = sum(getsizeof(event) for event in events) + getsizeof(events)

    assert estimated == exact


def test_estimate_events_bytes_of_varying_batch():
    """Estimate of events cycling in size does not drift off it.

    The tolerance covers the spread of a ten-event sample, not the
    accuracy of the estimate - checking a budget does not need more.
    """
    events = ['x' * (100 + i % 50) for i in range(10_000)]

    estimated = estimate_events_bytes(events)
    exact = sum(getsizeof(event) for event in events) + getsizeof(events)

    assert estimated == pytest.approx(exact, rel=0.15)


def test_estimate_events_bytes_of_empty_batch():
    """An empty batch is the size of the list holding nothing."""
    assert estimate_events_bytes([]) == getsizeof([])


# - Byte limit --------------------------------------------------------


def _sizer(item: str) -> int:
    return len(item)


def _limited(max_bytes: int) -> PipelineQueue[str]:
    return PipelineQueue(maxsize=10, sizer=_sizer, max_bytes=max_bytes)


def test_byte_limit_requires_sizer():
    """A byte limit without a way to measure items is refused."""
    with pytest.raises(ValueError, match='measurable'):
        PipelineQueue(maxsize=10, max_bytes=100)


def test_size_bytes_follows_held_items():
    """Queue counts the bytes of the items it handed out as well."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10, sizer=_sizer)
    assert q.size_bytes == 0
    assert q.max_bytes is None

    q.put('a' * 30)
    q.put('b' * 12)
    assert q.size_bytes == 42

    held = q.get()
    # Out of the queue, still occupying memory.
    assert q.size == 1
    assert q.size_bytes == 42

    held.release()
    assert q.size_bytes == 12


def test_release_is_idempotent():
    """Releasing a hold twice gives its room back once."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10, sizer=_sizer)
    q.put('a' * 10)
    q.put('b' * 10)

    held = q.get()
    held.release()
    held.release()

    assert q.size_bytes == 10


def test_holds_are_released_in_any_order():
    """Each item gives back what it took, not what came first."""
    q: PipelineQueue[str] = PipelineQueue(maxsize=10, sizer=_sizer)
    q.put('a' * 30)
    q.put('b' * 12)

    first = q.get()
    second = q.get()
    assert q.size_bytes == 42

    second.release()
    assert q.size_bytes == 30

    first.release()
    assert q.size_bytes == 0


def test_is_full_at_byte_limit():
    """Queue holding as many bytes as it may reports full."""
    q = _limited(10)
    q.put('a' * 10)

    assert q.size == 1
    assert q.is_full is True


def test_blocking_put_at_byte_limit():
    """put() blocks on the byte limit until a hold is released."""
    q = _limited(10)
    q.put('a' * 8)

    put_completed = threading.Event()

    def slow_put():
        q.put('b' * 8)
        put_completed.set()

    t = threading.Thread(target=slow_put)
    t.start()

    # Room for the item is not there, although the queue holds one of ten
    assert not put_completed.wait(timeout=0.3)
    assert q.size == 1

    held = q.get()
    # Taking it out is not enough - it is still being worked on
    assert not put_completed.wait(timeout=0.3)

    held.release()
    assert put_completed.wait(timeout=2)
    assert q.get().item == 'b' * 8
    t.join(timeout=2)
    assert not t.is_alive()


def test_item_larger_than_byte_limit_passes_alone():
    """An item over the whole limit is admitted into an empty queue."""
    q = _limited(10)

    q.put('a' * 100)

    assert q.size == 1
    assert q.size_bytes == 100
    assert q.get().item == 'a' * 100


def test_shutdown_releases_producer_held_by_byte_limit():
    """Shutdown wakes a producer waiting for room in the queue."""
    q = _limited(10)
    q.put('a' * 10)

    interrupted = threading.Event()

    def blocked_put():
        try:
            q.put('b' * 10)
        except queue_mod.ShutDown:
            interrupted.set()

    t = threading.Thread(target=blocked_put)
    t.start()

    assert not interrupted.wait(timeout=0.3)

    q.shutdown()

    assert interrupted.wait(timeout=2)
    t.join(timeout=2)
    assert not t.is_alive()


def test_release_after_shutdown_keeps_the_count_sane():
    """A hold released after shutdown does not drive the count below 0."""
    q = _limited(100)
    q.put('a' * 10)
    held = q.get()

    q.shutdown()
    held.release()

    assert q.size_bytes == 0


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
    assert q.get().item == 'second'
    t.join(timeout=2)
    assert not t.is_alive()
