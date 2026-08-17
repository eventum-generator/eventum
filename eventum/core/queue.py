"""Typed pipeline queue for inter-stage communication."""

import queue
import threading
from collections import deque
from collections.abc import Callable
from random import sample
from sys import getsizeof
from typing import Generic, TypeVar

T = TypeVar('T')

_SAMPLE_SIZE = 10
"""Number of events measured to estimate the size of a batch."""


def estimate_events_bytes(events: list[str]) -> int:
    """Estimate how much memory a batch of events occupies.

    Parameters
    ----------
    events : list[str]
        Batch of events.

    Returns
    -------
    int
        Number of bytes the batch occupies.

    Notes
    -----
    Measures a fixed number of events drawn at random and scales their
    average, since measuring every event of a batch of ten thousand
    costs more than the answer is worth. Events of one generator come
    from the same templates, so they vary little in size, and the error
    stays within a few percent. The events are drawn at random rather
    than at a fixed step, which would land on the same template every
    time whenever the batch cycles through them.

    """
    count = len(events)

    if count == 0:
        return getsizeof(events)

    sampled = sample(events, _SAMPLE_SIZE) if count > _SAMPLE_SIZE else events
    average = sum(getsizeof(event) for event in sampled) / len(sampled)

    return int(average * count) + getsizeof(events)


class PipelineQueue(Generic[T]):
    """Typed wrapper over stdlib queue with sentinel-based closing.

    Stages receive queues as constructor parameters and communicate
    exclusively through them.

    Parameters
    ----------
    maxsize : int
        Maximum number of items in the queue.

    sizer : Callable[[T], int] | None, default=None
        Function measuring the size of an item in bytes. Without it the
        queue does not account for the memory of what it holds.

    max_bytes : int | None, default=None
        Maximum number of bytes the items waiting in the queue may
        occupy together. Requires `sizer`; without it the queue is
        bounded by the number of items alone.

    Raises
    ------
    ValueError
        If a byte limit is set without a way to measure items.

    Notes
    -----
    The byte limit holds back the producer the same way the item limit
    does. An item larger than the whole limit is admitted once the queue
    drains, since refusing it would stall the pipeline for good.

    """

    def __init__(
        self,
        maxsize: int,
        sizer: Callable[[T], int] | None = None,
        max_bytes: int | None = None,
    ) -> None:
        """Initialize pipeline queue."""
        if max_bytes is not None and sizer is None:
            msg = 'Byte limit requires items to be measurable'
            raise ValueError(msg)

        self._maxsize = maxsize
        self._sizer = sizer
        self._max_bytes = max_bytes
        self._queue: queue.Queue[T | None] = queue.Queue(maxsize=maxsize)

        self._condition = threading.Condition()
        self._sizes: deque[int] = deque()
        self._bytes = 0
        self._is_shut_down = False

    def put(self, item: T) -> None:
        """Put an item into the queue.

        Blocks while the queue holds as many items or as many bytes as
        it may.

        Parameters
        ----------
        item : T
            Item to put.

        Raises
        ------
        queue.ShutDown
            If the queue has been shut down.

        """
        if self._sizer is not None:
            self._admit(self._sizer(item))

        self._queue.put(item)

    def get(self) -> T | None:
        """Get an item from the queue.

        Returns
        -------
        T | None
            Item from the queue, or ``None`` if the queue has been
            closed via sentinel.

        Raises
        ------
        queue.ShutDown
            If the queue has been shut down.

        """
        item = self._queue.get()
        self._queue.task_done()

        if item is not None and self._sizer is not None:
            self._release()

        return item

    def close(self) -> None:
        """Close the queue by sending sentinel and waiting for it
        to be consumed.

        Safe to call even if the queue has already been shut down.
        """
        try:
            self._queue.put(None)
            self._queue.join()
        except queue.ShutDown:
            pass

    def shutdown(self) -> None:
        """Shut down the queue immediately without sending sentinel.

        Useful for stopping upstream producers when downstream has
        exhausted. Producers held back by the byte limit are released.
        """
        self._queue.shutdown(immediate=True)

        with self._condition:
            self._is_shut_down = True
            self._sizes.clear()
            self._bytes = 0
            self._condition.notify_all()

    def _admit(self, size: int) -> None:
        """Wait until the queue has room for an item of this size."""
        with self._condition:
            while (
                not self._is_shut_down
                and self._max_bytes is not None
                and self._bytes > 0
                and self._bytes + size > self._max_bytes
            ):
                self._condition.wait()

            self._sizes.append(size)
            self._bytes += size

    def _release(self) -> None:
        """Give back the room the item taken out of the queue held."""
        with self._condition:
            if self._sizes:
                self._bytes -= self._sizes.popleft()

            self._condition.notify_all()

    @property
    def is_full(self) -> bool:
        """Whether the queue holds as much as it may."""
        if self._queue.full():
            return True

        if self._max_bytes is None:
            return False

        with self._condition:
            return self._bytes >= self._max_bytes

    @property
    def size(self) -> int:
        """Number of items waiting in the queue."""
        return self._queue.qsize()

    @property
    def maxsize(self) -> int:
        """Maximum number of items the queue holds."""
        return self._maxsize

    @property
    def size_bytes(self) -> int:
        """Number of bytes the items waiting in the queue occupy."""
        with self._condition:
            return self._bytes

    @property
    def max_bytes(self) -> int | None:
        """Maximum number of bytes the queue holds, if it is limited."""
        return self._max_bytes
